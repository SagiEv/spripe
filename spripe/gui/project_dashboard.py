"""
Module docstring.
"""
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QListWidget,
    QHBoxLayout,
    QInputDialog,
    QMessageBox,
    QListWidgetItem,
    QMenu,
)
from PyQt6.QtCore import pyqtSignal, QSize, Qt
from PyQt6.QtGui import QIcon
import os


class DraggableListWidget(QListWidget):
    """DraggableListWidget class."""
    itemsMoved = pyqtSignal(list, object)

    def dropEvent(self, event):
        """dropEvent method."""
        if event.source() == self:
            selected_items = self.selectedItems()
            target_item = self.itemAt(event.position().toPoint())

            if selected_items and target_item and target_item not in selected_items:
                target_data = target_item.data(Qt.ItemDataRole.UserRole)
                if target_data and target_data[0] == "folder":
                    self.itemsMoved.emit(selected_items, target_item)
                    event.setDropAction(Qt.DropAction.MoveAction)
                    event.accept()
                    return
            event.ignore()
            return
        super().dropEvent(event)


class ProjectDashboardWidget(QWidget):
    """ProjectDashboardWidget class."""
    metadata_updated = pyqtSignal()
    asset_selected = pyqtSignal(str, str)

    def __init__(self, project_manager, parent=None):
        """__init__ method."""
        super().__init__(parent)
        self.project_manager = project_manager
        self.current_project = None
        self.current_folder = None
        self.init_ui()

    def init_ui(self):
        """init_ui method."""
        layout = QVBoxLayout(self)

        self.header = QLabel("Project Dashboard")
        self.header.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(self.header)

        btn_layout = QHBoxLayout()
        self.btn_generate_asset = QPushButton("Generate New Asset (AI Video)")
        self.btn_create_folder = QPushButton("Create Virtual Folder")
        self.btn_edit_template = QPushButton("Edit Folder Template")

        self.btn_generate_asset.clicked.connect(self.on_generate_asset)
        self.btn_create_folder.clicked.connect(self.on_create_folder)
        self.btn_edit_template.clicked.connect(self.on_edit_template_clicked)

        btn_layout.addWidget(self.btn_generate_asset)
        btn_layout.addWidget(self.btn_create_folder)
        btn_layout.addWidget(self.btn_edit_template)
        btn_layout.addStretch()

        layout.addLayout(btn_layout)

        self.file_system_view = DraggableListWidget()
        self.file_system_view.setViewMode(QListWidget.ViewMode.IconMode)
        self.file_system_view.setIconSize(QSize(64, 64))
        self.file_system_view.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.file_system_view.setSpacing(10)
        self.file_system_view.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.file_system_view.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.file_system_view.setSelectionMode(
            QListWidget.SelectionMode.ExtendedSelection
        )
        self.file_system_view.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.file_system_view.customContextMenuRequested.connect(self.show_context_menu)
        self.file_system_view.itemsMoved.connect(self.on_items_moved)
        self.file_system_view.itemDoubleClicked.connect(self.on_item_double_clicked)
        layout.addWidget(self.file_system_view)

    def load_project(self, project_name):
        """load_project method."""
        self.current_project = project_name
        self.current_folder = None

        project_path = self.project_manager.get_project_path(project_name)
        workspace_dir = self.project_manager.workspace_dir

        ext_label = ""
        if str(workspace_dir) not in project_path:
            ext_label = " (External)"

        self.header.setText(f"Project Dashboard: {project_name}{ext_label}")
        self.refresh_view()

    def load_folder(self, project_name, folder_name):
        """load_folder method."""
        self.current_project = project_name
        self.current_folder = folder_name
        self.header.setText(f"Folder: {folder_name} (in {project_name})")
        self.refresh_view(folder_name)

    def on_back_clicked(self):
        """on_back_clicked method."""
        self.load_project(self.current_project)

    def on_item_double_clicked(self, item):
        """on_item_double_clicked method."""
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return
        if data[0] == "folder":
            self.load_folder(self.current_project, data[1])
        elif data[0] == "asset":
            self.asset_selected.emit(self.current_project, data[1])
        elif data[0] == "back":
            self.on_back_clicked()

    def refresh_view(self, filter_folder=None):
        """refresh_view method."""
        self.file_system_view.clear()
        if not self.current_project:
            return

        if filter_folder is None:
            filter_folder = self.current_folder
        else:
            self.current_folder = filter_folder

        self.btn_edit_template.setVisible(self.current_folder is not None)

        metadata = self.project_manager.get_project_metadata(self.current_project)
        virtual_folders = metadata.get("virtual_folders", {})
        explicit_folders = metadata.get("folders", [])

        base_dir = os.path.dirname(os.path.abspath(__file__))
        folder_icon = QIcon(os.path.join(base_dir, "icons", "folder.svg"))
        asset_icon = QIcon(os.path.join(base_dir, "icons", "asset.svg"))
        up_folder_icon = QIcon(os.path.join(base_dir, "icons", "up_folder.svg"))

        if self.current_folder is not None:
            back_item = QListWidgetItem(up_folder_icon, ".. (Back)")
            back_item.setTextAlignment(
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom
            )
            back_item.setData(Qt.ItemDataRole.UserRole, ("back", None))
            self.file_system_view.addItem(back_item)

            assets = self.project_manager.get_assets(self.current_project)
            for asset in assets:
                if virtual_folders.get(asset) == filter_folder:
                    item = QListWidgetItem(asset_icon, asset)
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom
                    )
                    item.setData(Qt.ItemDataRole.UserRole, ("asset", asset))
                    self.file_system_view.addItem(item)
        else:
            folders = set(virtual_folders.values())
            folders.update(explicit_folders)
            for f in sorted(folders):
                item = QListWidgetItem(folder_icon, f)
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom
                )
                item.setData(Qt.ItemDataRole.UserRole, ("folder", f))
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsDropEnabled)
                self.file_system_view.addItem(item)

            assets = self.project_manager.get_assets(self.current_project)
            for asset in assets:
                if asset not in virtual_folders:
                    item = QListWidgetItem(asset_icon, asset)
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom
                    )
                    item.setData(Qt.ItemDataRole.UserRole, ("asset", asset))
                    self.file_system_view.addItem(item)

    def on_generate_asset(self):
        """on_generate_asset method."""
        QMessageBox.information(self, "Coming Soon", "AI Video Generator placeholder.")

    def on_edit_template_clicked(self):
        """on_edit_template_clicked method."""
        if not self.current_folder:
            return
        current_template = self.project_manager.get_folder_template(
            self.current_project, self.current_folder
        )
        from spripe.gui.dialogs import TemplateEditorDialog

        dlg = TemplateEditorDialog(current_template, self)
        if dlg.exec():
            self.project_manager.set_folder_template(
                self.current_project, self.current_folder, dlg.template_lines
            )
            self.metadata_updated.emit()
            QMessageBox.information(
                self, "Success", "Folder template updated successfully."
            )

    def on_create_folder(self):
        """on_create_folder method."""
        if not self.current_project:
            return
        text, ok = QInputDialog.getText(self, "Create Virtual Folder", "Folder Name:")
        if ok and text:
            metadata = self.project_manager.get_project_metadata(self.current_project)
            folders = metadata.get("folders", [])
            if text not in folders:
                folders.append(text)
                metadata["folders"] = folders
                self.project_manager.save_project_metadata(
                    self.current_project, metadata
                )
                self.metadata_updated.emit()
                self.refresh_view()

    def show_context_menu(self, position):
        """show_context_menu method."""
        selected_items = self.file_system_view.selectedItems()
        if not selected_items:
            return

        for item in selected_items:
            data = item.data(Qt.ItemDataRole.UserRole)
            if data and data[0] == "back":
                return

        menu = QMenu()

        if len(selected_items) == 1:
            act_rename = menu.addAction("Rename")
        else:
            act_rename = None

        act_remove = menu.addAction("Remove")

        has_assets = any(
            item.data(Qt.ItemDataRole.UserRole)[0] == "asset" for item in selected_items
        )
        if has_assets:
            menu.addSeparator()
            act_move = menu.addAction("Move to Virtual Folder")
        else:
            act_move = None

        action = menu.exec(self.file_system_view.viewport().mapToGlobal(position))

        if action:
            if action == act_rename:
                self.on_rename_item(selected_items[0])
            elif action == act_remove:
                self.on_remove_items(selected_items)
            elif action == act_move:
                self.on_move_items(selected_items)

    def on_rename_item(self, item):
        """on_rename_item method."""
        data = item.data(Qt.ItemDataRole.UserRole)
        item_type, old_name = data[0], data[1]

        from PyQt6.QtWidgets import QInputDialog

        new_name, ok = QInputDialog.getText(
            self, f"Rename {item_type.capitalize()}", "New Name:", text=old_name
        )

        if ok and new_name and new_name != old_name:
            if item_type == "folder":
                success = self.project_manager.rename_virtual_folder(
                    self.current_project, old_name, new_name
                )
            elif item_type == "asset":
                success = self.project_manager.rename_asset(
                    self.current_project, old_name, new_name
                )

            if success:
                self.metadata_updated.emit()
                self.refresh_view()
            else:
                QMessageBox.warning(
                    self,
                    "Error",
                    f"Could not rename {item_type}. Name may already exist.",
                )

    def on_remove_items(self, items):
        """on_remove_items method."""
        folders = [
            item.data(Qt.ItemDataRole.UserRole)[1]
            for item in items
            if item.data(Qt.ItemDataRole.UserRole)[0] == "folder"
        ]
        assets = [
            item.data(Qt.ItemDataRole.UserRole)[1]
            for item in items
            if item.data(Qt.ItemDataRole.UserRole)[0] == "asset"
        ]

        msg = f"Are you sure you want to remove the selected items?\n"
        if folders:
            msg += f"- {len(folders)} folders\n"
        if assets:
            msg += f"- {len(assets)} assets\n"

        reply = QMessageBox.question(self, "Confirm Deletion", msg)
        if reply != QMessageBox.StandardButton.Yes:
            return

        delete_assets_in_folders = False
        if folders:
            folder_reply = QMessageBox.question(
                self,
                "Folder Deletion",
                "Do you want to delete all assets inside these folders as well?\n\n"
                "Yes: Delete assets from disk.\n"
                "No: Preserve assets (move to root).",
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
                | QMessageBox.StandardButton.Cancel,
            )
            if folder_reply == QMessageBox.StandardButton.Cancel:
                return
            delete_assets_in_folders = folder_reply == QMessageBox.StandardButton.Yes

        for f in folders:
            self.project_manager.delete_virtual_folder(
                self.current_project, f, delete_assets_in_folders
            )

        for a in assets:
            self.project_manager.delete_asset(self.current_project, a)

        self.metadata_updated.emit()
        self.refresh_view()

    def on_move_items(self, items):
        """on_move_items method."""
        assets = [
            item.data(Qt.ItemDataRole.UserRole)[1]
            for item in items
            if item.data(Qt.ItemDataRole.UserRole)[0] == "asset"
        ]
        if not assets:
            return

        metadata = self.project_manager.get_project_metadata(self.current_project)
        folders = metadata.get("folders", [])

        options = ["(Root)"] + sorted(folders)

        from PyQt6.QtWidgets import QInputDialog

        choice, ok = QInputDialog.getItem(
            self, "Move to Folder", "Select target folder:", options, 0, False
        )

        if ok:
            vfs = metadata.get("virtual_folders", {})
            for a in assets:
                if choice == "(Root)":
                    if a in vfs:
                        del vfs[a]
                else:
                    vfs[a] = choice
            metadata["virtual_folders"] = vfs
            self.project_manager.save_project_metadata(self.current_project, metadata)
            self.metadata_updated.emit()
            self.refresh_view()

    def on_items_moved(self, dragged_items, target_item):
        """on_items_moved method."""
        if not self.current_project:
            return

        target_data = target_item.data(Qt.ItemDataRole.UserRole)
        if not target_data or target_data[0] != "folder":
            return
        folder_name = target_data[1]

        metadata = self.project_manager.get_project_metadata(self.current_project)
        if "virtual_folders" not in metadata:
            metadata["virtual_folders"] = {}

        for dragged_item in dragged_items:
            dragged_data = dragged_item.data(Qt.ItemDataRole.UserRole)
            if dragged_data and dragged_data[0] == "asset":
                metadata["virtual_folders"][dragged_data[1]] = folder_name

        self.project_manager.save_project_metadata(self.current_project, metadata)

        self.metadata_updated.emit()
        self.refresh_view()
