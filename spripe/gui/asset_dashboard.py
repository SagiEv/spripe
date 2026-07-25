"""
Module docstring.
"""

import json
import os
from typing import List, Optional, Union

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QStyle,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QHeaderView,
    QSplitter,
    QSizePolicy,
)

from spripe.core.config import Config
from spripe.core.project_manager import ProjectManager
from spripe.gui.generated_media_widget import GeneratedMediaWidget


class AssetDashboardWidget(QWidget):
    """Dashboard view showing all animations within a selected asset."""

    animation_selected = pyqtSignal(str, str, str)  # proj, asset, anim
    action_normalize_animation = pyqtSignal(
        str, str, object
    )  # proj, asset, anim (or list of anims)
    action_compress_animation = pyqtSignal(
        str, str, object
    )  # proj, asset, anim (or list of anims)
    action_export_gif = pyqtSignal(str, str, str)  # proj, asset, anim
    action_create_missing = pyqtSignal(str, str, str)  # proj, asset, anim
    action_new_animation = pyqtSignal(str, str)  # proj, asset
    action_regenerate_media = pyqtSignal(dict) # metadata
    action_make_png_sequence = pyqtSignal(str, str, list)

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
        self.btn_compress_all = QPushButton("Compress All")
        self.btn_compress_all.clicked.connect(self.compress_all_animations)
        self.btn_compress_all.setEnabled(False)

        self.btn_new_anim.clicked.connect(self.on_new_anim)
        self.btn_generate_anim.clicked.connect(self.on_generate_anim)
        self.btn_set_template.clicked.connect(self.on_set_template)
        self.btn_normalize_selected.clicked.connect(self.on_normalize_selected)
        self.btn_normalize_all.clicked.connect(self.normalize_all_animations)

        btn_layout.addWidget(self.btn_new_anim)
        btn_layout.addWidget(self.btn_generate_anim)
        btn_layout.addWidget(self.btn_set_template)
        btn_layout.addWidget(self.btn_normalize_selected)
        btn_layout.addWidget(self.btn_normalize_all)
        btn_layout.addWidget(self.btn_compress_all)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Splitter to separate animation table and generated media
        self.splitter = QSplitter(Qt.Orientation.Vertical)
        self.splitter.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.splitter, 1)

        # Top container for animation table
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)

        self.anim_table = QTableWidget()
        self.anim_table.setColumnCount(4)
        self.anim_table.setHorizontalHeaderLabels(
            ["Animation Name", "Status", "Normalized Size", "Compressed Version"]
        )
        self.anim_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.anim_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self.anim_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Interactive
        )
        self.anim_table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.Interactive
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
        top_layout.addWidget(self.anim_table)

        self.splitter.addWidget(top_widget)

        # Bottom container for generated media
        self.generated_media_widget = GeneratedMediaWidget()
        self.generated_media_widget.action_regenerate_media.connect(self.action_regenerate_media.emit)
        self.splitter.addWidget(self.generated_media_widget)

        self.splitter.setStretchFactor(0, 2)
        self.splitter.setStretchFactor(1, 1)

    def load_asset(self, project_name: str, asset_name: str) -> None:
        """Loads and displays the metadata and animations for a specific asset."""
        self.current_project = project_name
        self.current_asset = asset_name
        self.header.setText(f"Asset Dashboard: {asset_name} (in {project_name})")

        project_path = self.project_manager.get_project_path(project_name)
        asset_path = os.path.join(project_path, asset_name)
        self.generated_media_widget.load_asset(asset_path)

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

            def get_dir_size_str(path):
                if not os.path.exists(path):
                    return ""
                total_size = sum(
                    os.path.getsize(os.path.join(path, f))
                    for f in os.listdir(path)
                    if os.path.isfile(os.path.join(path, f))
                )
                if total_size < 1024:
                    return f"{total_size} B"
                if total_size < 1024 * 1024:
                    return f"{total_size / 1024:.1f} KB"
                return f"{total_size / (1024 * 1024):.1f} MB"

            asset_path = (
                self.project_manager.registry.get_project_path(self.current_project)
                / self.current_asset
            )
            norm_dir = (
                asset_path
                / Config.DIR_NORMALIZED_OUTPUT
                / f"{Config.PREFIX_NORMALIZED}{anim}"
            )
            comp_dir = (
                asset_path
                / Config.DIR_COMPRESSED_OUTPUT
                / f"{Config.PREFIX_COMPRESSED}{anim}"
            )

            norm_size_str = get_dir_size_str(norm_dir)
            comp_size_str = get_dir_size_str(comp_dir)

            if os.path.exists(comp_dir):
                meta_path = os.path.join(comp_dir, "compression_meta.json")
                if os.path.exists(meta_path):
                    try:
                        with open(meta_path, "r", encoding="utf-8") as f:
                            meta = json.load(f)
                            colors = meta.get("colors", "?")
                            comp_size_str += f" (Colors: {colors})"
                    except Exception:
                        pass

            def create_size_widget(size_text, dir_path):
                if not size_text:
                    item = QTableWidgetItem("")
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    return item, None

                widget = QWidget()
                layout = QHBoxLayout(widget)
                layout.setContentsMargins(4, 0, 4, 0)
                layout.setSpacing(8)

                label = QLabel(size_text)
                btn = QPushButton()
                btn.setIcon(
                    self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon)
                )
                btn.setFixedSize(24, 24)
                btn.setToolTip("Open Folder Location")
                btn.setStyleSheet(
                    "QPushButton { border: none; background: transparent; font-size: 14px; } QPushButton:hover { background: #333; border-radius: 4px; }"
                )

                # capture current path
                path_to_open = str(dir_path)
                btn.clicked.connect(
                    lambda _, p=path_to_open: (
                        os.startfile(p) if hasattr(os, "startfile") else None
                    )
                )

                layout.addWidget(label)
                layout.addWidget(btn)
                layout.setAlignment(
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                )

                item = QTableWidgetItem(size_text)
                item.setForeground(Qt.GlobalColor.transparent)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                return item, widget

            self.anim_table.setItem(row, 0, name_item)
            self.anim_table.setItem(row, 1, status_item)

            norm_item, norm_widget = create_size_widget(norm_size_str, norm_dir)
            if norm_item:
                self.anim_table.setItem(row, 2, norm_item)
            if norm_widget:
                self.anim_table.setCellWidget(row, 2, norm_widget)

            comp_item, comp_widget = create_size_widget(comp_size_str, comp_dir)
            if comp_item:
                self.anim_table.setItem(row, 3, comp_item)
            if comp_widget:
                self.anim_table.setCellWidget(row, 3, comp_widget)

        self.anim_table.resizeColumnToContents(1)
        self.anim_table.setColumnWidth(2, 140)
        self.anim_table.setColumnWidth(3, 230)

    def show_context_menu(self, position):
        """show_context_menu method."""
        row = self.anim_table.rowAt(position.y())
        if row >= 0:
            anim = self.anim_table.item(row, 0).text()
            status = self.anim_table.item(row, 1).text()

            menu = QMenu()

            # Global actions
            gen_anim_action = menu.addAction("Generate AI Animation...")
            new_anim_action = menu.addAction("New Animation")
            del_anim_action = menu.addAction("Delete Animation")
            menu.addSeparator()

            act_create = None
            act_normalize = None
            act_compress = None
            act_export_gif = None

            if status == "Missing":
                act_create = menu.addAction("Create Missing Animation")
            else:
                action_text = "Renormalize" if status == "Normalized" else "Normalize"
                act_normalize = menu.addAction(action_text)

                if status in ["Normalized", "Compressed"]:
                    act_compress = menu.addAction("Compress Animation")
                    act_export_gif = menu.addAction("Export as GIF")

            act_png_seq = None
            # Handle multiple selections for PNG sequence
            selected_items = self.anim_table.selectedItems()
            selected_rows = list(set(item.row() for item in selected_items))
            video_only_anims = []
            for r in selected_rows:
                if self.anim_table.item(r, 1).text() == "Video Only":
                    video_only_anims.append(self.anim_table.item(r, 0).text())

            if video_only_anims:
                act_png_seq = menu.addAction(f"Make PNG Sequence ({len(video_only_anims)})")

            action = menu.exec(self.anim_table.viewport().mapToGlobal(position))

            if action == gen_anim_action:
                asset_path = str(self.project_manager.registry.get_project_path(self.current_project) / self.current_asset)
                meta = {
                    "type": "Animation Video",
                    "template": "idle_animation",
                    "animation_name": anim,
                    "asset_path": asset_path,
                    "user_input": f"Animation: {anim}"
                }
                self.action_regenerate_media.emit(meta)
            elif action == new_anim_action:
                self.action_new_animation.emit(self.current_project, self.current_asset)
            elif action == del_anim_action:
                self.project_manager.delete_animation(self.current_project, self.current_asset, anim)
                self.refresh_view()
            elif act_create and action == act_create:
                self.create_missing_animation(anim)
            elif act_normalize and action == act_normalize:
                self.action_normalize_animation.emit(
                    self.current_project, self.current_asset, anim
                )
            elif act_compress and action == act_compress:
                self.action_compress_animation.emit(
                    self.current_project, self.current_asset, anim
                )
            elif act_export_gif and action == act_export_gif:
                self.action_export_gif.emit(
                    self.current_project, self.current_asset, anim
                )
            elif act_png_seq and action == act_png_seq:
                self.action_make_png_sequence.emit(
                    self.current_project, self.current_asset, video_only_anims
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

    def on_generate_anim(self):
        """on_generate_anim method."""
        asset_path = str(self.project_manager.registry.get_project_path(self.current_project) / self.current_asset)
        meta = {
            "type": "Animation Video",
            "template": "idle_animation",
            "asset_path": asset_path
        }
        self.action_regenerate_media.emit(meta)

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

    def normalize_all_animations(self):
        """normalize_all_animations method."""
        # Filter out missing
        anims = []
        for row in range(self.anim_table.rowCount()):
            status = self.anim_table.item(row, 1).text()
            if status != "Missing":
                anims.append(self.anim_table.item(row, 0).text())
        if anims:
            self.action_normalize_animation.emit(
                self.current_project, self.current_asset, anims
            )

    def compress_all_animations(self):
        """compress_all_animations method."""
        # Filter out missing
        anims = []
        for row in range(self.anim_table.rowCount()):
            status = self.anim_table.item(row, 1).text()
            if status != "Missing":
                anims.append(self.anim_table.item(row, 0).text())
        if anims:
            self.action_compress_animation.emit(
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
