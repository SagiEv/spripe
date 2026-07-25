"""Module docstring."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QListWidget, QPushButton, QMessageBox, QInputDialog, QDialog, QTextEdit,
    QComboBox, QLineEdit, QApplication, QFormLayout
)
from PyQt6.QtCore import Qt
from spripe.core.generation import PromptManager

class TemplateEditDialog(QDialog):
    """Class docstring."""
    def __init__(self, template_name, initial_type, initial_text, parent=None, is_new=False):
        """Method docstring."""
        super().__init__(parent)
        self.setWindowTitle("New Template" if is_new else f"Edit Template: {template_name}")
        self.resize(500, 400)

        self.new_name = template_name
        self.new_type = initial_type
        self.new_text = initial_text

        layout = QVBoxLayout(self)

        form_layout = QFormLayout()
        self.name_input = QLineEdit()
        self.name_input.setText(template_name)
        if not is_new:
            self.name_input.setReadOnly(True)
        form_layout.addRow("Template Name:", self.name_input)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["None", "Asset Design", "Asset Reference Creation", "Asset Animation Creation"])
        self.type_combo.setCurrentText(initial_type)
        form_layout.addRow("Template Type:", self.type_combo)

        layout.addLayout(form_layout)

        # Clipboard buttons
        cb_layout = QHBoxLayout()
        cb_layout.addWidget(QLabel("Prompt Content:"))
        cb_layout.addStretch()
        btn_copy = QPushButton("Copy")
        btn_paste = QPushButton("Paste")
        btn_copy.clicked.connect(self.on_copy)
        btn_paste.clicked.connect(self.on_paste)
        cb_layout.addWidget(btn_copy)
        cb_layout.addWidget(btn_paste)
        layout.addLayout(cb_layout)

        self.editor = QTextEdit()
        self.editor.setPlainText(initial_text)
        layout.addWidget(self.editor)

        btn_layout = QHBoxLayout()
        btn_save = QPushButton("Save")
        btn_cancel = QPushButton("Cancel")
        btn_save.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

    def on_copy(self):
        """Method docstring."""
        QApplication.clipboard().setText(self.editor.toPlainText())

    def on_paste(self):
        """Method docstring."""
        text = QApplication.clipboard().text()
        if text:
            self.editor.insertPlainText(text)

    def accept(self):
        """Method docstring."""
        self.new_name = self.name_input.text().strip()
        if not self.new_name:
            QMessageBox.warning(self, "Error", "Template name cannot be empty.")
            return
        self.new_type = self.type_combo.currentText()
        self.new_text = self.editor.toPlainText()
        super().accept()

class ProjectPromptsWidget(QWidget):
    """Widget to view project-level AI generation templates."""
    def __init__(self, parent=None):
        """Method docstring."""
        super().__init__(parent)
        self.prompt_manager = None
        self.init_ui()

    def init_ui(self):
        """Method docstring."""
        layout = QVBoxLayout(self)

        header = QLabel("Project Prompts Templates")
        header.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(header)

        self.template_list = QListWidget()
        self.template_list.itemDoubleClicked.connect(self.on_edit_template)
        layout.addWidget(self.template_list)

        btn_layout = QHBoxLayout()
        self.btn_new = QPushButton("New")
        self.btn_edit = QPushButton("Edit")
        self.btn_delete = QPushButton("Delete")

        self.btn_new.clicked.connect(self.on_new_template)
        self.btn_edit.clicked.connect(lambda: self.on_edit_template(self.template_list.currentItem()))
        self.btn_delete.clicked.connect(self.on_delete_template)

        btn_layout.addWidget(self.btn_new)
        btn_layout.addWidget(self.btn_edit)
        btn_layout.addWidget(self.btn_delete)
        layout.addLayout(btn_layout)

    def load_project(self, project_path: str, workspace_dir: str = None):
        """Method docstring."""
        self.prompt_manager = PromptManager(project_path, workspace_dir)
        self._refresh_list()

    def _refresh_list(self):
        """Method docstring."""
        self.template_list.clear()
        if self.prompt_manager:
            self.template_list.addItems(list(self.prompt_manager.templates.keys()))

    def on_new_template(self):
        """Method docstring."""
        if not self.prompt_manager:
            return

        dlg = TemplateEditDialog("new_template", "None", "", self, is_new=True)
        if dlg.exec():
            if dlg.new_name in self.prompt_manager.templates:
                QMessageBox.warning(self, "Warning", "Template already exists.")
                return
            self.prompt_manager.update_template(dlg.new_name, dlg.new_type, dlg.new_text)
            self._refresh_list()

    def on_edit_template(self, item=None):
        """Method docstring."""
        if not self.prompt_manager or not item:
            return
        template_name = item.text()
        template_obj = self.prompt_manager.templates.get(template_name, {})
        initial_type = template_obj.get("type", "None") if isinstance(template_obj, dict) else "None"
        initial_text = template_obj.get("text", "") if isinstance(template_obj, dict) else template_obj

        dlg = TemplateEditDialog(template_name, initial_type, initial_text, self, is_new=False)
        if dlg.exec():
            if dlg.new_name != template_name:
                # rename means delete old and add new
                del self.prompt_manager.templates[template_name]
            self.prompt_manager.update_template(dlg.new_name, dlg.new_type, dlg.new_text)
            self._refresh_list()

    def on_delete_template(self):
        """Method docstring."""
        if not self.prompt_manager:
            return
        item = self.template_list.currentItem()
        if not item:
            return

        current = item.text()
        reply = QMessageBox.question(self, "Delete Template", f"Are you sure you want to delete '{current}'?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            if current in self.prompt_manager.templates:
                self.prompt_manager.templates = {k: v for k, v in self.prompt_manager.templates.items() if k != current}
                self.prompt_manager.save_templates(self.prompt_manager.templates)
                self._refresh_list()
