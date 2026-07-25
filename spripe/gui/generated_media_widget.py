"""Module docstring."""
import os
import json
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QListWidget, QTextEdit, QPushButton, QSplitter
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QPixmap, QIcon

class GeneratedMediaWidget(QWidget):
    """Widget to view and interact with generated AI media."""

    action_regenerate_media = pyqtSignal(dict)

    def __init__(self, parent=None):
        """Method docstring."""
        super().__init__(parent)
        self.current_asset_path = None
        self.init_ui()

    def init_ui(self):
        """Method docstring."""
        layout = QVBoxLayout(self)

        header = QLabel("Generated Media")
        header.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(header)

        # Splitter to separate the list from the preview
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        # Media List
        self.media_list = QListWidget()
        self.media_list.setViewMode(QListWidget.ViewMode.IconMode)
        self.media_list.setIconSize(QSize(64, 64))
        self.media_list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.media_list.setSpacing(10)
        self.media_list.itemSelectionChanged.connect(self.on_media_selected)
        splitter.addWidget(self.media_list)

        # Preview & Metadata Panel
        preview_panel = QWidget()
        preview_layout = QVBoxLayout(preview_panel)
        preview_layout.setContentsMargins(0, 0, 0, 0)

        self.preview_label = QLabel("Select media to preview")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet("background-color: #222; color: #fff;")
        self.preview_label.setMinimumHeight(200)
        preview_layout.addWidget(self.preview_label)

        self.metadata_view = QTextEdit()
        self.metadata_view.setReadOnly(True)
        preview_layout.addWidget(self.metadata_view)

        # Re-generate Button
        self.btn_regenerate = QPushButton("Re-generate (AI)")
        self.btn_regenerate.clicked.connect(self.on_regenerate_clicked)
        self.btn_regenerate.setEnabled(False)
        preview_layout.addWidget(self.btn_regenerate)

        splitter.addWidget(preview_panel)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

    def load_asset(self, asset_path: str):
        """Method docstring."""
        self.current_asset_path = asset_path
        self.media_list.clear()
        self.preview_label.setText("Select media to preview")
        self.metadata_view.clear()
        self.btn_regenerate.setEnabled(False)
        self.media_paths = {}

        if not os.path.exists(asset_path):
            return

        gen_dir = os.path.join(asset_path, "generated")
        if not os.path.exists(gen_dir):
            return

        # Check generated folder for videos/images
        for f in os.listdir(gen_dir):
            if f.lower().endswith(('.png', '.jpg', '.mp4', '.gif')):
                self.media_list.addItem(f)
                self.media_paths[f] = os.path.join(gen_dir, f)

    def on_media_selected(self):
        """Method docstring."""
        selected = self.media_list.selectedItems()
        if not selected:
            self.preview_label.setText("Select media to preview")
            self.metadata_view.clear()
            self.btn_regenerate.setEnabled(False)
            return

        filename = selected[0].text()
        filepath = getattr(self, "media_paths", {}).get(filename)
        if not filepath:
            return

        # Display image preview
        if filename.lower().endswith(('.png', '.jpg')):
            pixmap = QPixmap(filepath)
            self.preview_label.setPixmap(pixmap.scaled(self.preview_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            self.preview_label.setText(f"Video file: {filename}\n(Preview not supported directly)")

        # Load metadata
        meta_path = os.path.join(self.current_asset_path, "generated_assets", "metadata.json")
        if os.path.exists(meta_path):
            try:
                with open(meta_path, 'r', encoding='utf-8') as f:
                    meta = json.load(f)
                    # For simplicity, if we have a single file or a dictionary of files
                    # Let's assume metadata stores a "prompt" key or similar
                    self.metadata_view.setPlainText(json.dumps(meta, indent=4))
                    self.btn_regenerate.setEnabled(True)
            except Exception as e:
                self.metadata_view.setPlainText(f"Error loading metadata: {e}")
                self.btn_regenerate.setEnabled(False)
        else:
            self.metadata_view.setPlainText("No metadata found.")
            self.btn_regenerate.setEnabled(False)

    def on_regenerate_clicked(self):
        """Method docstring."""
        try:
            meta = json.loads(self.metadata_view.toPlainText())
            self.action_regenerate_media.emit(meta)
        except Exception:
            pass
