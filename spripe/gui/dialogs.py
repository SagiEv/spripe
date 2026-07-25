"""
Module docstring.
"""
import os
import shutil
import json
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFileDialog,
    QFormLayout,
    QComboBox,
    QMessageBox,
    QColorDialog,
    QCheckBox,
    QSlider,
    QListWidget,
    QListWidgetItem,
    QWidget,
    QPlainTextEdit,
    QStackedWidget,
)
from PyQt6.QtCore import Qt, QSize


class SettingsDialog(QDialog):
    """SettingsDialog class."""
    def __init__(self, settings_manager, parent=None):
        """__init__ method."""
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.setWindowTitle("Settings")
        self.resize(400, 200)
        self.init_ui()

    def init_ui(self):
        """init_ui method."""
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        # Workspace Dir
        self.workspace_input = QLineEdit(self.settings_manager.get("workspace_dir", ""))
        workspace_btn = QPushButton("Browse...")
        workspace_btn.clicked.connect(self.browse_workspace)

        ws_layout = QHBoxLayout()
        ws_layout.addWidget(self.workspace_input)
        ws_layout.addWidget(workspace_btn)

        form_layout.addRow("Workspace Directory:", ws_layout)

        # Export Dir (Godot etc.)
        self.export_input = QLineEdit(self.settings_manager.get("export_dir", ""))
        export_btn = QPushButton("Browse...")
        export_btn.clicked.connect(self.browse_export)

        exp_layout = QHBoxLayout()
        exp_layout.addWidget(self.export_input)
        exp_layout.addWidget(export_btn)

        form_layout.addRow("Target Engine/Export Path:", exp_layout)

        # Theme
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["dark", "light", "custom"])
        self.theme_combo.setCurrentText(self.settings_manager.get("theme", "dark"))
        form_layout.addRow("Theme:", self.theme_combo)

        # --- Onion Preferences ---
        self.chk_onion_visible = QCheckBox("Show Onion Skin by Default")
        self.chk_onion_visible.setChecked(
            self.settings_manager.get("onion_visible_default", True)
        )

        self.slider_onion_opacity = QSlider(Qt.Orientation.Horizontal)
        self.slider_onion_opacity.setRange(0, 100)
        self.slider_onion_opacity.setValue(
            self.settings_manager.get("onion_opacity_default", 40)
        )
        self.slider_onion_opacity.setEnabled(self.chk_onion_visible.isChecked())

        self.chk_onion_visible.toggled.connect(self.slider_onion_opacity.setEnabled)

        form_layout.addRow("Onion Skin:", self.chk_onion_visible)

        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(self.slider_onion_opacity)
        self.lbl_opacity_val = QLabel(f"{self.slider_onion_opacity.value()}%")
        self.slider_onion_opacity.valueChanged.connect(
            lambda v: self.lbl_opacity_val.setText(f"{v}%")
        )
        opacity_layout.addWidget(self.lbl_opacity_val)

        form_layout.addRow("Default Opacity:", opacity_layout)

        # --- Playback Preferences ---
        play_layout = QHBoxLayout()
        self.chk_loop = QCheckBox("Loop")
        self.chk_loop.setChecked(self.settings_manager.get("play_loop_default", True))
        self.chk_boomerang = QCheckBox("Boomerang")
        self.chk_boomerang.setChecked(
            self.settings_manager.get("play_boomerang_default", False)
        )
        self.chk_autoplay = QCheckBox("Autoplay")
        self.chk_autoplay.setChecked(
            self.settings_manager.get("play_autoplay_default", False)
        )

        play_layout.addWidget(self.chk_loop)
        play_layout.addWidget(self.chk_boomerang)
        play_layout.addWidget(self.chk_autoplay)
        form_layout.addRow("Playback Defaults:", play_layout)

        layout.addLayout(form_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_settings)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

    def browse_workspace(self):
        """browse_workspace method."""
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select Workspace Directory", self.workspace_input.text()
        )
        if dir_path:
            self.workspace_input.setText(dir_path)

    def browse_export(self):
        """browse_export method."""
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select Export Directory", self.export_input.text()
        )
        if dir_path:
            self.export_input.setText(dir_path)

    def save_settings(self):
        """save_settings method."""
        self.settings_manager.set("workspace_dir", self.workspace_input.text())
        self.settings_manager.set("export_dir", self.export_input.text())
        self.settings_manager.set("theme", self.theme_combo.currentText())
        self.settings_manager.set(
            "onion_visible_default", self.chk_onion_visible.isChecked()
        )
        self.settings_manager.set(
            "onion_opacity_default", self.slider_onion_opacity.value()
        )
        self.settings_manager.set("play_loop_default", self.chk_loop.isChecked())
        self.settings_manager.set(
            "play_boomerang_default", self.chk_boomerang.isChecked()
        )
        self.settings_manager.set(
            "play_autoplay_default", self.chk_autoplay.isChecked()
        )
        self.accept()


class NewProjectDialog(QDialog):
    """NewProjectDialog class."""
    def __init__(self, parent=None):
        """__init__ method."""
        super().__init__(parent)
        self.setWindowTitle("New Project")
        self.project_name = ""
        self.init_ui()

    def init_ui(self):
        """init_ui method."""
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.name_input = QLineEdit()
        form.addRow("Project Name:", self.name_input)
        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        create_btn = QPushButton("Create")
        create_btn.clicked.connect(self.create_project)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(create_btn)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

    def create_project(self):
        """create_project method."""
        if self.name_input.text().strip() == "":
            QMessageBox.warning(self, "Error", "Project name cannot be empty.")
            return
        self.project_name = self.name_input.text().strip()
        self.accept()


class NewAssetDialog(QDialog):
    """NewAssetDialog class."""
    def __init__(self, projects, current_project, parent=None):
        """__init__ method."""
        super().__init__(parent)
        self.setWindowTitle("New Asset")
        self.asset_name = ""
        self.selected_project = current_project
        self.projects = projects
        self.init_ui()

    def init_ui(self):
        """init_ui method."""
        layout = QVBoxLayout(self)

        form = QFormLayout()

        self.project_combo = QComboBox()
        self.project_combo.addItem("None (Standalone)")
        for p in self.projects:
            self.project_combo.addItem(p)

        if self.selected_project in self.projects:
            self.project_combo.setCurrentText(self.selected_project)

        form.addRow("Project:", self.project_combo)

        self.name_input = QLineEdit()
        form.addRow("Asset Name:", self.name_input)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        create_btn = QPushButton("Create")
        create_btn.clicked.connect(self.create_asset)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(create_btn)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

    def create_asset(self):
        """create_asset method."""
        if self.name_input.text().strip() == "":
            QMessageBox.warning(self, "Error", "Asset name cannot be empty.")
            return
        self.asset_name = self.name_input.text().strip()
        proj = self.project_combo.currentText()
        self.selected_project = None if proj == "None (Standalone)" else proj
        self.accept()


class NewAnimationDialog(QDialog):
    """NewAnimationDialog class."""
    def __init__(
        self, projects, get_assets_callback, current_project, current_asset, parent=None
    ):
        """__init__ method."""
        super().__init__(parent)
        self.setWindowTitle("New Animation")
        self.animation_name = ""
        self.selected_project = current_project
        self.selected_asset = current_asset
        self.get_assets_callback = get_assets_callback
        self.projects = projects
        self.init_ui()

    def init_ui(self):
        """init_ui method."""
        layout = QVBoxLayout(self)

        form = QFormLayout()

        self.project_combo = QComboBox()
        self.project_combo.addItem("None (Standalone)")
        for p in self.projects:
            self.project_combo.addItem(p)

        if self.selected_project in self.projects:
            self.project_combo.setCurrentText(self.selected_project)

        self.project_combo.currentTextChanged.connect(self.update_assets)

        self.asset_combo = QComboBox()
        self.update_assets(self.project_combo.currentText())
        if self.selected_asset:
            self.asset_combo.setCurrentText(self.selected_asset)

        form.addRow("Project:", self.project_combo)
        form.addRow("Asset:", self.asset_combo)

        self.name_input = QLineEdit()
        form.addRow("Animation Name (e.g. idle):", self.name_input)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        create_btn = QPushButton("Create")
        create_btn.clicked.connect(self.create_animation)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(create_btn)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

    def update_assets(self, project_name):
        """update_assets method."""
        self.asset_combo.clear()
        proj = None if project_name == "None (Standalone)" else project_name
        if proj is None:
            proj = "Standalone"
        assets = self.get_assets_callback(proj)
        for a in assets:
            self.asset_combo.addItem(a)

    def create_animation(self):
        """create_animation method."""
        if self.name_input.text().strip() == "":
            QMessageBox.warning(self, "Error", "Animation name cannot be empty.")
            return
        if self.asset_combo.count() == 0:
            QMessageBox.warning(
                self, "Error", "No asset selected. Please create an asset first."
            )
            return

        self.animation_name = self.name_input.text().strip()
        proj = self.project_combo.currentText()
        self.selected_project = None if proj == "None (Standalone)" else proj
        self.selected_asset = self.asset_combo.currentText()
        self.accept()


class ImportProjectDialog(QDialog):
    """ImportProjectDialog class."""
    def __init__(self, parent=None):
        """__init__ method."""
        super().__init__(parent)
        self.setWindowTitle("Import Project")
        self.project_name = ""
        self.project_path = ""
        self.init_ui()

    def init_ui(self):
        """init_ui method."""
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.name_input = QLineEdit()
        form.addRow("Project Name:", self.name_input)

        self.path_input = QLineEdit()
        path_btn = QPushButton("Browse...")
        path_btn.clicked.connect(self.browse_path)

        path_layout = QHBoxLayout()
        path_layout.addWidget(self.path_input)
        path_layout.addWidget(path_btn)

        form.addRow("Project Folder:", path_layout)
        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        import_btn = QPushButton("Import")
        import_btn.clicked.connect(self.do_import)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(import_btn)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

    def browse_path(self):
        """browse_path method."""
        dir_path = QFileDialog.getExistingDirectory(self, "Select Project Folder")
        if dir_path:
            self.path_input.setText(dir_path)
            if not self.name_input.text():
                self.name_input.setText(os.path.basename(dir_path))

    def do_import(self):
        """do_import method."""
        if not self.name_input.text().strip() or not self.path_input.text().strip():
            QMessageBox.warning(self, "Error", "Name and Path cannot be empty.")
            return
        self.project_name = self.name_input.text().strip()
        self.project_path = self.path_input.text().strip()
        self.accept()


class ImportAssetDialog(QDialog):
    """ImportAssetDialog class."""
    def __init__(self, projects, current_project, parent=None):
        """__init__ method."""
        super().__init__(parent)
        self.setWindowTitle("Import Asset")
        self.asset_name = ""
        self.asset_path = ""
        self.selected_project = current_project
        self.projects = projects
        self.init_ui()

    def init_ui(self):
        """init_ui method."""
        layout = QVBoxLayout(self)

        form = QFormLayout()

        self.project_combo = QComboBox()
        self.project_combo.addItem("None (Standalone)")
        for p in self.projects:
            self.project_combo.addItem(p)

        if self.selected_project in self.projects:
            self.project_combo.setCurrentText(self.selected_project)

        form.addRow("Target Project:", self.project_combo)

        self.name_input = QLineEdit()
        form.addRow("Asset Name:", self.name_input)

        self.path_input = QLineEdit()
        path_btn = QPushButton("Browse...")
        path_btn.clicked.connect(self.browse_path)

        path_layout = QHBoxLayout()
        path_layout.addWidget(self.path_input)
        path_layout.addWidget(path_btn)

        form.addRow("Asset Folder:", path_layout)
        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        import_btn = QPushButton("Import")
        import_btn.clicked.connect(self.do_import)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(import_btn)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

    def browse_path(self):
        """browse_path method."""
        dir_path = QFileDialog.getExistingDirectory(self, "Select Asset Folder")
        if dir_path:
            self.path_input.setText(dir_path)
            if not self.name_input.text():
                self.name_input.setText(os.path.basename(dir_path))

    def do_import(self):
        """do_import method."""
        if not self.name_input.text().strip() or not self.path_input.text().strip():
            QMessageBox.warning(self, "Error", "Name and Path cannot be empty.")
            return
        self.asset_name = self.name_input.text().strip()
        self.asset_path = self.path_input.text().strip()
        proj = self.project_combo.currentText()
        self.selected_project = None if proj == "None (Standalone)" else proj
        self.accept()


class DeleteConfirmationDialog(QDialog):
    """DeleteConfirmationDialog class."""
    def __init__(self, item_name, is_project, parent=None):
        """__init__ method."""
        super().__init__(parent)
        self.setWindowTitle(f"Delete {item_name}?")
        self.item_name = item_name
        self.is_project = is_project
        self.delete_mode = None  # "remove" or "delete"
        self.init_ui()

    def init_ui(self):
        """init_ui method."""
        layout = QVBoxLayout(self)

        lbl = QLabel(f"Are you sure you want to delete '{self.item_name}'?")
        layout.addWidget(lbl)

        btn_layout = QHBoxLayout()

        remove_btn = QPushButton("Remove from Workspace")
        remove_btn.setToolTip("Unregisters the item but keeps the files on disk.")
        remove_btn.clicked.connect(self.do_remove)

        delete_btn = QPushButton("Delete Permanently")
        delete_btn.setToolTip("Deletes the files completely from your disk!")
        delete_btn.setStyleSheet("background-color: #A02020; color: white;")
        delete_btn.clicked.connect(self.do_delete)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)

        if self.is_project:
            btn_layout.addWidget(remove_btn)

        btn_layout.addWidget(delete_btn)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

    def do_remove(self):
        """do_remove method."""
        self.delete_mode = "remove"
        self.accept()

    def do_delete(self):
        """do_delete method."""
        self.delete_mode = "delete"
        self.accept()


class ExportDialog(QDialog):
    """ExportDialog class."""
    def __init__(self, is_animation, item_name, parent=None):
        """__init__ method."""
        super().__init__(parent)
        self.is_animation = is_animation
        self.item_name = item_name
        self.setWindowTitle(
            f"Export {'Animation' if is_animation else 'Asset'}: {item_name}"
        )

        self.export_type = "Folder"
        self.dest_path = ""
        self.init_ui()

    def init_ui(self):
        """init_ui method."""
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.type_combo = QComboBox()
        self.type_combo.addItems(["Folder (Godot/Engine)", "ZIP Archive"])
        form.addRow("Format:", self.type_combo)

        path_layout = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("Select destination directory...")
        path_btn = QPushButton("Browse")
        path_btn.clicked.connect(self.browse_path)
        path_layout.addWidget(self.path_input)
        path_layout.addWidget(path_btn)

        form.addRow("Destination:", path_layout)
        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        export_btn = QPushButton("Export")
        export_btn.clicked.connect(self.do_export)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(export_btn)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

    def browse_path(self):
        """browse_path method."""
        dir_path = QFileDialog.getExistingDirectory(self, "Select Destination Folder")
        if dir_path:
            self.path_input.setText(dir_path)

    def do_export(self):
        """do_export method."""
        if not self.path_input.text().strip():
            QMessageBox.warning(self, "Error", "Please select a destination path.")
            return

        self.dest_path = self.path_input.text().strip()
        self.export_type = (
            "ZIP Archive" if "ZIP" in self.type_combo.currentText() else "Folder"
        )
        self.accept()


class TemplateEditorDialog(QDialog):
    """TemplateEditorDialog class."""
    def __init__(self, template_lines, parent=None):
        """__init__ method."""
        super().__init__(parent)
        self.setWindowTitle("Edit Folder Template")
        self.resize(500, 400)

        self.template_lines = [t.strip() for t in template_lines if t.strip()]
        self.init_ui()

    def init_ui(self):
        """init_ui method."""
        main_layout = QVBoxLayout(self)

        # --- Mode Switcher ---
        top_layout = QHBoxLayout()
        self.btn_toggle_mode = QPushButton("Raw JSON Option")
        self.btn_toggle_mode.setCheckable(True)
        self.btn_toggle_mode.toggled.connect(self.toggle_mode)
        top_layout.addStretch()
        top_layout.addWidget(self.btn_toggle_mode)
        main_layout.addLayout(top_layout)

        self.stack = QStackedWidget()

        # --- Tags Mode (Index 0) ---
        self.tags_widget = QWidget()
        tags_layout = QVBoxLayout(self.tags_widget)
        tags_layout.setContentsMargins(0, 0, 0, 0)

        self.list_tags = QListWidget()
        self.list_tags.setViewMode(QListWidget.ViewMode.IconMode)
        self.list_tags.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.list_tags.setSpacing(5)
        self.list_tags.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.list_tags.setStyleSheet(
            "QListWidget::item { background-color: transparent; }"
        )

        for tag in self.template_lines:
            self.add_tag_to_list(tag)

        tags_layout.addWidget(self.list_tags)

        input_layout = QHBoxLayout()
        self.input_new_tag = QLineEdit()
        self.input_new_tag.setPlaceholderText(
            "Type a new animation tag and press Enter..."
        )
        self.input_new_tag.returnPressed.connect(self.add_new_tag)
        btn_add = QPushButton("Add")
        btn_add.clicked.connect(self.add_new_tag)

        input_layout.addWidget(self.input_new_tag)
        input_layout.addWidget(btn_add)
        tags_layout.addLayout(input_layout)

        # --- Raw JSON Mode (Index 1) ---
        self.raw_widget = QWidget()
        raw_layout = QVBoxLayout(self.raw_widget)
        raw_layout.setContentsMargins(0, 0, 0, 0)

        self.text_raw = QPlainTextEdit()
        self.text_raw.setPlainText(json.dumps(self.template_lines, indent=4))
        raw_layout.addWidget(self.text_raw)

        self.stack.addWidget(self.tags_widget)
        self.stack.addWidget(self.raw_widget)

        main_layout.addWidget(self.stack)

        # --- Bottom Buttons ---
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_template)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        main_layout.addLayout(btn_layout)

    def add_tag_to_list(self, text):
        """add_tag_to_list method."""
        item = QListWidgetItem()
        self.list_tags.addItem(item)

        # Create custom widget
        widget = QWidget()
        widget.setStyleSheet("background-color: #333333; border-radius: 12px;")
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(10, 4, 10, 4)

        lbl = QLabel(text)
        lbl.setStyleSheet("color: white;")

        btn_del = QPushButton("✕")
        btn_del.setFixedSize(20, 20)
        btn_del.setStyleSheet(
            "QPushButton { color: white; background-color: transparent; border: none; font-weight: bold; } QPushButton:hover { color: #ff5555; }"
        )
        btn_del.clicked.connect(lambda _, item=item: self.remove_tag(item))

        layout.addWidget(lbl)
        layout.addWidget(btn_del)

        # Size hint needs to match layout
        item.setSizeHint(widget.sizeHint())
        self.list_tags.setItemWidget(item, widget)

    def remove_tag(self, item):
        """remove_tag method."""
        row = self.list_tags.row(item)
        self.list_tags.takeItem(row)

    def add_new_tag(self):
        """add_new_tag method."""
        text = self.input_new_tag.text().strip()
        if text:
            # Check for duplicates
            for i in range(self.list_tags.count()):
                widget = self.list_tags.itemWidget(self.list_tags.item(i))
                if widget and widget.layout().itemAt(0).widget().text() == text:
                    self.input_new_tag.clear()
                    return
            self.add_tag_to_list(text)
            self.input_new_tag.clear()

    def toggle_mode(self, checked):
        """toggle_mode method."""
        if checked:
            # Switching to Raw JSON
            tags = self.get_tags_from_list()
            self.text_raw.setPlainText(json.dumps(tags, indent=4))
            self.stack.setCurrentIndex(1)
            self.btn_toggle_mode.setText("Tags Interface Option")
        else:
            # Switching to Tags Interface
            try:
                data = json.loads(self.text_raw.toPlainText())
                if isinstance(data, list):
                    self.list_tags.clear()
                    for t in data:
                        self.add_tag_to_list(str(t))
                else:
                    QMessageBox.warning(
                        self, "Invalid Format", "JSON must be a list of strings."
                    )
                    self.btn_toggle_mode.setChecked(True)  # Revert
                    return
            except json.JSONDecodeError:
                QMessageBox.warning(self, "Invalid JSON", "Could not parse JSON.")
                self.btn_toggle_mode.setChecked(True)  # Revert
                return

            self.stack.setCurrentIndex(0)
            self.btn_toggle_mode.setText("Raw JSON Option")

    def get_tags_from_list(self):
        """get_tags_from_list method."""
        tags = []
        for i in range(self.list_tags.count()):
            widget = self.list_tags.itemWidget(self.list_tags.item(i))
            if widget:
                lbl = widget.layout().itemAt(0).widget()
                tags.append(lbl.text())
        return tags

    def save_template(self):
        """save_template method."""
        if self.stack.currentIndex() == 0:
            self.template_lines = self.get_tags_from_list()
        else:
            try:
                data = json.loads(self.text_raw.toPlainText())
                if isinstance(data, list):
                    self.template_lines = [str(t) for t in data]
                else:
                    QMessageBox.warning(
                        self, "Invalid Format", "JSON must be a list of strings."
                    )
                    return
            except json.JSONDecodeError:
                QMessageBox.warning(self, "Invalid JSON", "Could not parse JSON.")
                return
        self.accept()
