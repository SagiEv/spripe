"""
Module docstring.
"""
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QHBoxLayout,
    QMenu,
    QAbstractItemView,
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QColor
from typing import Optional, List, Union
from spripe.core.project_manager import ProjectManager


class AssetDashboardWidget(QWidget):
    """Dashboard view showing all animations within a selected asset."""

    animation_selected = pyqtSignal(str, str, str)  # proj, asset, anim
    action_normalize_animation = pyqtSignal(
        str, str, object
    )  # proj, asset, anim (or list of anims)
    action_new_animation = pyqtSignal(str, str)  # proj, asset

    def __init__(
        self, project_manager: ProjectManager, parent: Optional[QWidget] = None
    ):
        """__init__ method."""
        super().__init__(parent)
        self.project_manager: ProjectManager = project_manager
        self.current_project: Optional[str] = None
        self.current_asset: Optional[str] = None
        self.init_ui()

        from spripe.core.signal_manager import SignalManager

        sm = SignalManager.get_instance()
        sm.animation_created.connect(self._on_state_changed)
        sm.animation_deleted.connect(self._on_state_changed)
        sm.metadata_updated.connect(
            lambda p: self.refresh_view() if p == self.current_project else None
        )

    def _on_state_changed(self, proj, asset, _anim=None):
        """_on_state_changed method."""
        if proj == self.current_project and asset == self.current_asset:
            self.refresh_view()

    def init_ui(self) -> None:
        """Initializes the dashboard UI layout."""
        layout = QVBoxLayout(self)

        self.header = QLabel("Asset Dashboard")
        self.header.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(self.header)

        btn_layout = QHBoxLayout()
        self.btn_new_anim = QPushButton("New Animation")
        self.btn_generate_anim = QPushButton("Generate Animation (AI)")
        self.btn_set_template = QPushButton("Set as Folder Template")
        self.btn_normalize_selected = QPushButton("Normalize Selected")
        self.btn_normalize_all = QPushButton("Normalize All")

        self.btn_new_anim.clicked.connect(self.on_new_anim)
        self.btn_generate_anim.clicked.connect(self.on_generate_anim)
        self.btn_set_template.clicked.connect(self.on_set_template)
        self.btn_normalize_selected.clicked.connect(self.on_normalize_selected)
        self.btn_normalize_all.clicked.connect(self.on_normalize_all)

        btn_layout.addWidget(self.btn_new_anim)
        btn_layout.addWidget(self.btn_generate_anim)
        btn_layout.addWidget(self.btn_set_template)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_normalize_selected)
        btn_layout.addWidget(self.btn_normalize_all)
        layout.addLayout(btn_layout)

        self.anim_table = QTableWidget()
        self.anim_table.setColumnCount(2)
        self.anim_table.setHorizontalHeaderLabels(["Animation Name", "Status"])
        self.anim_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.anim_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self.anim_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.anim_table.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self.anim_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.anim_table.customContextMenuRequested.connect(self.show_context_menu)
        self.anim_table.cellDoubleClicked.connect(self.on_cell_double_clicked)
        layout.addWidget(self.anim_table)

    def load_asset(self, project_name: str, asset_name: str) -> None:
        """Loads and displays the metadata and animations for a specific asset."""
        self.current_project = project_name
        self.current_asset = asset_name
        self.header.setText(f"Asset Dashboard: {asset_name} (in {project_name})")
        self.refresh_view()

    def refresh_view(self):
        """refresh_view method."""
        self.anim_table.setRowCount(0)
        if not self.current_project or not self.current_asset:
            return

        animations = set(
            self.project_manager.get_animations(
                self.current_project, self.current_asset
            )
        )

        metadata = self.project_manager.get_project_metadata(self.current_project)
        virtual_folder = metadata.get("virtual_folders", {}).get(self.current_asset)
        template_anims = set()
        if virtual_folder:
            template_anims = set(
                self.project_manager.get_folder_template(
                    self.current_project, virtual_folder
                )
            )

        all_anims = sorted(list(animations | template_anims))
        self.anim_table.setRowCount(len(all_anims))

        for row, anim in enumerate(all_anims):
            if anim in animations:
                status = self.project_manager.get_animation_status(
                    self.current_project, self.current_asset, anim
                )
            else:
                status = "Missing"

            name_item = QTableWidgetItem(anim)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            status_item = QTableWidgetItem(status)
            status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            if status == "Normalized":
                status_item.setForeground(QColor("#4ADE80"))
            elif status == "Raw":
                status_item.setForeground(QColor("#FBBF24"))
            elif status == "Video Only":
                status_item.setForeground(QColor("#60A5FA"))
            elif status == "Missing":
                status_item.setForeground(QColor("#EF4444"))

            self.anim_table.setItem(row, 0, name_item)
            self.anim_table.setItem(row, 1, status_item)

    def show_context_menu(self, position):
        """show_context_menu method."""
        row = self.anim_table.rowAt(position.y())
        if row >= 0:
            anim = self.anim_table.item(row, 0).text()
            status = self.anim_table.item(row, 1).text()

            menu = QMenu()
            if status == "Missing":
                act_create = menu.addAction("Create Missing Animation")
                action = menu.exec(self.anim_table.viewport().mapToGlobal(position))
                if action == act_create:
                    self.create_missing_animation(anim)
            else:
                action_text = "Renormalize" if status == "Normalized" else "Normalize"
                act_normalize = menu.addAction(action_text)

                action = menu.exec(self.anim_table.viewport().mapToGlobal(position))
                if action == act_normalize:
                    self.action_normalize_animation.emit(
                        self.current_project, self.current_asset, anim
                    )

    def on_cell_double_clicked(self, row, col):
        """on_cell_double_clicked method."""
        anim = self.anim_table.item(row, 0).text()
        status = self.anim_table.item(row, 1).text()
        if status == "Missing":
            self.create_missing_animation(anim)
        else:
            self.animation_selected.emit(self.current_project, self.current_asset, anim)

    def create_missing_animation(self, anim):
        """create_missing_animation method."""
        self.project_manager.create_animation(
            self.current_project, self.current_asset, anim
        )

    def on_new_anim(self):
        """on_new_anim method."""
        self.action_new_animation.emit(self.current_project, self.current_asset)

    def on_normalize_selected(self):
        """on_normalize_selected method."""
        selected_anims = []
        for item in self.anim_table.selectedItems():
            if item.column() == 0:
                # Make sure we don't try to normalize "Missing"
                status = self.anim_table.item(item.row(), 1).text()
                if status != "Missing":
                    selected_anims.append(item.text())
        if selected_anims:
            self.action_normalize_animation.emit(
                self.current_project, self.current_asset, selected_anims
            )

    def on_normalize_all(self):
        """on_normalize_all method."""
        # Filter out missing
        anims = []
        for row in range(self.anim_table.rowCount()):
            status = self.anim_table.item(row, 1).text()
            if status != "Missing":
                anims.append(self.anim_table.item(row, 0).text())
        self.action_normalize_animation.emit(
            self.current_project, self.current_asset, anims
        )

    def on_generate_anim(self):
        """on_generate_anim method."""
        QMessageBox.information(
            self, "Coming Soon", "Prompt to Video generator placeholder."
        )

    def on_set_template(self):
        """on_set_template method."""
        if not self.current_project or not self.current_asset:
            return

        projects = self.project_manager.get_projects()
        folder_options = []
        for p in projects:
            meta = self.project_manager.get_project_metadata(p)
            folders = meta.get("folders", [])
            vfs = set(meta.get("virtual_folders", {}).values())
            all_f = sorted(list(set(folders) | vfs))
            for f in all_f:
                folder_options.append(f"{p} / {f}")

        if not folder_options:
            QMessageBox.warning(
                self, "No Folders", "No virtual folders exist in any project."
            )
            return

        from PyQt6.QtWidgets import QInputDialog

        choice, ok = QInputDialog.getItem(
            self, "Set as Template", "Select target folder:", folder_options, 0, False
        )

        if ok and choice:
            proj, folder = choice.split(" / ")
            current_anims = self.project_manager.get_animations(
                self.current_project, self.current_asset
            )
            existing = self.project_manager.get_folder_template(proj, folder)

            if existing:
                msg = QMessageBox(self)
                msg.setWindowTitle("Existing Template")
                msg.setText(f"Folder '{folder}' already has a template.")
                btn_merge = msg.addButton("Merge", QMessageBox.ButtonRole.AcceptRole)
                btn_overwrite = msg.addButton(
                    "Overwrite", QMessageBox.ButtonRole.DestructiveRole
                )
                msg.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
                msg.exec()

                if msg.clickedButton() == btn_merge:
                    merged = sorted(list(set(existing) | set(current_anims)))
                    self.project_manager.set_folder_template(proj, folder, merged)
                elif msg.clickedButton() == btn_overwrite:
                    self.project_manager.set_folder_template(
                        proj, folder, current_anims
                    )
                else:
                    return
            else:
                self.project_manager.set_folder_template(proj, folder, current_anims)

            QMessageBox.information(
                self, "Success", f"Template applied to folder '{folder}'."
            )
