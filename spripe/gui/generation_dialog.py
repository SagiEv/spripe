"""Module docstring."""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QTextEdit, QPushButton, QMessageBox, QProgressBar
)
from PyQt6.QtCore import Qt
import os
import json

from spripe.core.generation import PromptManager, GeminiGenerator
from .generation_worker import GenerationWorker

class GenerationDialog(QDialog):
    """Class docstring."""
    def __init__(self, project_path: str, metadata: dict = None, workspace_dir: str = None, parent=None):
        """Method docstring."""
        super().__init__(parent)
        self.project_path = project_path
        self.workspace_dir = workspace_dir
        self.metadata = metadata or {}
        self.setWindowTitle("Generate AI Assets")
        self.resize(600, 500)

        self.prompt_manager = PromptManager(project_path, workspace_dir)
        self._init_ui()
        # We will retrieve api key from app settings later, for now mock it.
        # It's recommended to pull this from the global configuration system.
        self.api_key = os.environ.get("GEMINI_API_KEY", "")
        self.generator = GeminiGenerator(self.api_key)

        self._connect_signals()
        self.update_preview()

    def _init_ui(self):
        """Method docstring."""
        layout = QVBoxLayout(self)

        # Type Selection
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Asset Type:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Asset Design", "Reference Image", "Animation Video"])
        type_layout.addWidget(self.type_combo)
        layout.addLayout(type_layout)

        if "animation_name" in self.metadata:
            anim_name = self.metadata["animation_name"]
            anim_label = QLabel(f"<b>Target Animation:</b> {anim_name}")
            layout.addWidget(anim_label)

        # Template Selection
        template_layout = QHBoxLayout()
        template_layout.addWidget(QLabel("Template:"))
        self.template_combo = QComboBox()
        self.template_combo.addItems(list(self.prompt_manager.templates.keys()))
        template_layout.addWidget(self.template_combo)
        layout.addLayout(template_layout)

        # User Input
        layout.addWidget(QLabel("User Input (e.g. 'wearing a red jacket'):"))
        self.user_input = QTextEdit()
        self.user_input.setMaximumHeight(80)
        layout.addWidget(self.user_input)

        # Final Prompt Preview
        layout.addWidget(QLabel("Final Prompt Preview:"))
        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        layout.addWidget(self.preview)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        btn_layout = QHBoxLayout()
        self.btn_copy_prompt = QPushButton("Copy Final Prompt")
        self.btn_generate = QPushButton("Generate")
        self.btn_cancel = QPushButton("Cancel")
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_copy_prompt)
        btn_layout.addWidget(self.btn_generate)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

    def _connect_signals(self):
        """Method docstring."""
        self.template_combo.currentTextChanged.connect(self.on_template_changed)
        self.user_input.textChanged.connect(self.update_preview)
        self.btn_generate.clicked.connect(self.start_generation)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_copy_prompt.clicked.connect(self.copy_final_prompt)

        # Pre-fill from metadata if provided
        if self.metadata:
            if "type" in self.metadata:
                idx = self.type_combo.findText(self.metadata["type"])
                if idx >= 0:
                    self.type_combo.setCurrentIndex(idx)
            if "template" in self.metadata:
                idx = self.template_combo.findText(self.metadata["template"])
                if idx >= 0:
                    self.template_combo.setCurrentIndex(idx)
            if "user_input" in self.metadata:
                self.user_input.setPlainText(self.metadata["user_input"])

    def on_template_changed(self, template_name):
        """Method docstring."""
        template_obj = self.prompt_manager.templates.get(template_name, {})
        text = template_obj.get("text", "") if isinstance(template_obj, dict) else template_obj
        # Only overwrite if user hasn't typed anything custom, or if they explicitly selected a new one
        self.user_input.setPlainText(text)
        self.update_preview()

    def copy_final_prompt(self):
        """Method docstring."""
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(self.preview.toPlainText())

    def update_preview(self, *args):
        """Method docstring."""
        template_key = self.template_combo.currentText()
        user_text = self.user_input.toPlainText()
        prompt = self.prompt_manager.build_prompt(template_key, user_text)
        self.preview.setPlainText(prompt)

    def start_generation(self):
        """Method docstring."""
        template_key = self.template_combo.currentText()
        is_video = self.type_combo.currentText() == "Animation Video"
        gen_type = "video" if is_video else "image"
        prompt = self.preview.toPlainText()

        self.btn_generate.setEnabled(False)
        self.progress_bar.setVisible(True)

        self.worker = GenerationWorker(self.generator, gen_type, prompt)
        self.worker.finished_signal.connect(self.on_generation_finished)
        self.worker.error_signal.connect(self.on_generation_error)
        self.worker.start()

    def on_generation_finished(self, result: dict):
        """Method docstring."""
        self.btn_generate.setEnabled(True)
        self.progress_bar.setVisible(False)

        from PyQt6.QtWidgets import QFileDialog
        is_video = self.type_combo.currentText() == "Animation Video"
        filter_str = "Video Files (*.mp4)" if is_video else "Images (*.png *.jpg)"

        default_dir = self.project_path
        default_name = ""

        if "asset_path" in self.metadata:
            default_dir = os.path.join(self.metadata["asset_path"], "generated")
        elif "folder" in self.metadata:
            # New asset in folder
            if self.metadata["folder"] != "(Root)":
                default_dir = os.path.join(self.project_path, self.metadata["folder"])
            default_dir = os.path.join(default_dir, "generated")

        os.makedirs(default_dir, exist_ok=True)

        if "animation_name" in self.metadata:
            anim_name = self.metadata["animation_name"]
            default_name = f"{anim_name}.mp4"

        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Generated Asset",
            os.path.join(default_dir, default_name),
            filter_str
        )

        if save_path:
            # Here we would save the actual data, mocked for now
            try:
                with open(save_path, 'wb') as f:
                    f.write(b"Mock generated content")

                # Save metadata
                meta_path = os.path.join(os.path.dirname(save_path), "metadata.json")
                meta = {
                    "type": self.type_combo.currentText(),
                    "template": self.template_combo.currentText(),
                    "user_input": self.user_input.toPlainText()
                }
                with open(meta_path, 'w', encoding='utf-8') as f:
                    json.dump(meta, f, indent=4)

                QMessageBox.information(
                    self,
                    "Generation Complete",
                    f"Asset saved successfully to:\n{save_path}"
                )
            except Exception as e:
                QMessageBox.critical(self, "Save Error", str(e))

        self.accept()

    def on_generation_error(self, error_msg: str):
        """Method docstring."""
        self.btn_generate.setEnabled(True)
        self.progress_bar.setVisible(False)

        QMessageBox.critical(
            self,
            "Generation Error",
            f"An error occurred during generation:\n{error_msg}\n\nPlease check your API key in settings."
        )
