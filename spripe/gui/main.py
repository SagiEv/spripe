"""
Module docstring.
"""

import sys
import os
import shutil
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
    QLabel,
    QToolBar,
    QMessageBox,
    QSplitter,
    QStackedWidget,
)
from PyQt6.QtGui import QAction, QIcon, QKeySequence, QPainter, QPen, QColor
from PyQt6.QtCore import Qt, QTimer

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from spripe.gui.asset_browser import AssetBrowser
from spripe.gui.pipeline_controls import PipelineControls
from spripe.gui.timeline_widget import TimelineWidget
from spripe.gui.painter_widget import PainterWidget
from spripe.gui.project_dashboard import ProjectDashboardWidget
from spripe.gui.asset_dashboard import AssetDashboardWidget
from spripe.gui.action_controller import ActionController

from spripe.core.settings_manager import SettingsManager
from spripe.core.project_manager import ProjectManager
from spripe.core.history import HistoryManager, CommandContext


class RotatingSpinner(QWidget):
    """RotatingSpinner class."""

    def __init__(self, parent=None):
        """__init__ method."""
        super().__init__(parent)
        self.setFixedSize(16, 16)
        self.angle = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.rotate)
        self.timer.start(50)

    def rotate(self):
        """rotate method."""
        self.angle = (self.angle + 30) % 360
        self.update()

    def paintEvent(self, event):
        """paintEvent method."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.translate(self.width() / 2, self.height() / 2)
        painter.rotate(self.angle)
        painter.translate(-self.width() / 2, -self.height() / 2)

        pen = QPen(QColor("#0078D7"))  # Spripe blue
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawArc(2, 2, 12, 12, 0, 270 * 16)
        painter.end()


class BackgroundTaskWidget(QWidget):
    """BackgroundTaskWidget class."""

    def __init__(self, parent=None):
        """__init__ method."""
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 10, 0)
        self.layout.setSpacing(5)

        self.spinner = RotatingSpinner(self)
        self.label = QLabel("", self)

        self.layout.addWidget(self.spinner)
        self.layout.addWidget(self.label)
        self.hide()

    def update_tasks(self, tasks: list):
        """update_tasks method."""
        if not tasks:
            self.hide()
            return

        self.show()
        if len(tasks) > 2:
            self.label.setText(f"{len(tasks)} Tasks Running...")
        else:
            self.label.setText(", ".join(tasks))


class AssetPipelineApp(QMainWindow):
    """AssetPipelineApp class."""

    def __init__(self, base_dir):
        """__init__ method."""
        super().__init__()
        self.setWindowTitle("spripe")
        self.resize(1200, 700)

        # Center the window on the screen
        qr = self.frameGeometry()
        if self.screen():
            cp = self.screen().availableGeometry().center()
            qr.moveCenter(cp)
            self.move(qr.topLeft())

        self.base_dir = base_dir

        # Load Managers
        self.settings_manager = SettingsManager(base_dir)
        if getattr(self.settings_manager, "load_error", None):
            QMessageBox.warning(
                self,
                "Settings Error",
                f"Failed to load settings:\n{self.settings_manager.load_error}\n\nFalling back to defaults.",
            )

        workspace = self.settings_manager.get("workspace_dir")
        self.project_manager = ProjectManager(workspace)
        if getattr(self.project_manager, "load_error", None):
            QMessageBox.warning(
                self,
                "Project Registry Error",
                f"Failed to load project registry:\n{self.project_manager.load_error}\n\nFalling back to empty registry.",
            )

        self.current_project = None
        self.current_asset = None
        self.current_animation = None
        self.current_path = None

        self.history_manager = HistoryManager(self.settings_manager)
        self.history_manager.history_changed.connect(self._update_edit_menu)
        self.history_manager.context_switch_requested.connect(
            self._handle_context_switch
        )

        # Load stylesheet
        stylesheet_path = os.path.join(os.path.dirname(__file__), "styles.qss")
        if os.path.exists(stylesheet_path):
            with open(stylesheet_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())

        # Main layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        self.layout = QHBoxLayout(main_widget)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(10)

        # Initialize components
        self.asset_browser = AssetBrowser(self.project_manager)
        self.pipeline_controls = PipelineControls(self.base_dir)
        self.painter_widget = PainterWidget(
            self.settings_manager, self.history_manager, self.get_current_context
        )
        self.timeline_widget = TimelineWidget(
            self.base_dir,
            self.settings_manager,
            self.history_manager,
            self.get_current_context,
        )

        self.action_controller = ActionController(self)

        self.active_background_tasks = []
        self.bg_task_widget = BackgroundTaskWidget(self)
        self.statusBar().addPermanentWidget(self.bg_task_widget)

        self.init_menu_bar()

        # Connect signals
        self.asset_browser.item_selected.connect(self.on_item_selected)
        self.pipeline_controls.pipeline_finished.connect(self.on_pipeline_finished)
        self.pipeline_controls.task_started.connect(self.add_background_task)
        self.pipeline_controls.task_ended.connect(self.remove_background_task)
        self.timeline_widget.frame_selected.connect(self.painter_widget.load_frame)
        self.timeline_widget.pinned_keyframe_updated.connect(
            self.painter_widget.on_pinned_keyframe_updated
        )
        self.painter_widget.interaction_started.connect(self.timeline_widget.pause_anim)

        # Connect Context Menu Signals
        self.asset_browser.action_new_asset.connect(
            self.action_controller.show_new_asset
        )
        self.asset_browser.action_import_asset.connect(
            self.action_controller.show_import_asset
        )
        self.asset_browser.action_export_project.connect(
            self.action_controller.show_export_project
        )
        self.asset_browser.action_remove_project.connect(
            self.action_controller.remove_project
        )
        self.asset_browser.action_create_folder.connect(
            self.action_controller.show_create_folder
        )
        self.asset_browser.action_remove_folder.connect(
            self.action_controller.remove_folder
        )

        self.asset_browser.action_new_animation.connect(
            self.action_controller.show_new_animation
        )
        self.asset_browser.action_import_animation_video.connect(
            self.action_controller.show_import_animation_video
        )
        self.asset_browser.action_import_animation_png.connect(
            self.action_controller.show_import_animation_png
        )
        self.asset_browser.action_export_asset.connect(
            lambda p, a: self.action_controller.show_export(False, p, a)
        )
        self.asset_browser.action_remove_asset.connect(
            self.action_controller.remove_asset
        )
        self.asset_browser.action_move_to_folder.connect(
            self.action_controller.show_move_to_folder
        )

        self.asset_browser.action_export_animation.connect(
            lambda p, a, an: self.action_controller.show_export(True, p, a, an)
        )
        self.asset_browser.action_renormalize_animation.connect(
            self.action_controller.renormalize_animation
        )
        self.asset_browser.action_remove_animation.connect(
            self.action_controller.remove_animation
        )

        self.asset_browser.action_new_project.connect(
            self.action_controller.show_new_project
        )
        self.asset_browser.action_import_project.connect(
            self.action_controller.show_import_project
        )

        # Layout arrangement with QSplitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.asset_browser)

        editor_widget = QWidget()
        editor_layout = QVBoxLayout(editor_widget)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.addWidget(self.pipeline_controls)
        editor_layout.addWidget(self.painter_widget, 1)
        editor_layout.addWidget(self.timeline_widget)

        self.project_dashboard = ProjectDashboardWidget(self.project_manager)
        self.project_dashboard.metadata_updated.connect(
            self.asset_browser.refresh_assets
        )
        self.project_dashboard.asset_selected.connect(
            self.on_asset_selected_from_dashboard
        )
        self.project_dashboard.action_generate_asset.connect(
            self.action_controller.show_generation_dialog
        )

        self.asset_dashboard = AssetDashboardWidget(self.project_manager)
        self.asset_dashboard.animation_selected.connect(
            self.on_animation_selected_from_dashboard
        )
        self.asset_dashboard.action_new_animation.connect(
            self.action_controller.show_new_animation
        )
        self.asset_dashboard.action_normalize_animation.connect(
            self.action_controller.renormalize_animation
        )
        self.asset_dashboard.action_compress_animation.connect(
            self.action_controller.compress_animation
        )
        self.asset_dashboard.action_export_gif.connect(
            self.action_controller.export_gif_animation
        )
        self.asset_dashboard.action_regenerate_media.connect(
            self.action_controller.show_generation_dialog
        )
        self.asset_dashboard.action_make_png_sequence.connect(
            self.action_controller.make_png_sequence
        )

        self.right_panel = QStackedWidget()
        self.right_panel.addWidget(self.project_dashboard)  # index 0
        self.right_panel.addWidget(self.asset_dashboard)  # index 1
        self.right_panel.addWidget(editor_widget)  # index 2

        splitter.addWidget(self.right_panel)

        # Set stretch factors: browser=1, right_panel=3
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)

        self.layout.addWidget(splitter)

    def init_menu_bar(self):
        """init_menu_bar method."""
        menubar = self.menuBar()

        # --- File Menu ---
        file_menu = menubar.addMenu("File")

        new_proj_action = QAction("New Project", self)
        new_proj_action.triggered.connect(self.action_controller.show_new_project)
        file_menu.addAction(new_proj_action)

        open_proj_action = QAction("Open Project...", self)
        open_proj_action.triggered.connect(self.action_controller.show_open_project)
        file_menu.addAction(open_proj_action)

        self.recent_menu = file_menu.addMenu("Recent Projects")
        self.populate_recent_projects()

        new_asset_action = QAction("New Asset", self)
        new_asset_action.triggered.connect(
            lambda: self.action_controller.show_new_asset()
        )
        file_menu.addAction(new_asset_action)

        new_anim_action = QAction("New Animation", self)
        new_anim_action.triggered.connect(
            lambda: self.action_controller.show_new_animation()
        )
        file_menu.addAction(new_anim_action)

        file_menu.addSeparator()

        save_proj_as_action = QAction("Save Project As...", self)
        save_proj_as_action.triggered.connect(
            self.action_controller.show_save_project_as
        )
        file_menu.addAction(save_proj_as_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # --- Edit Menu ---
        edit_menu = menubar.addMenu("Edit")

        self.undo_action = QAction("Undo", self)
        self.undo_action.setShortcut(QKeySequence("Ctrl+Z"))
        self.undo_action.triggered.connect(self._do_undo)
        edit_menu.addAction(self.undo_action)

        self.redo_action = QAction("Redo", self)
        self.redo_action.setShortcuts(
            [QKeySequence("Ctrl+Shift+Z"), QKeySequence("Ctrl+Y")]
        )
        self.redo_action.triggered.connect(self._do_redo)
        edit_menu.addAction(self.redo_action)

        self._update_edit_menu()

        edit_menu.addSeparator()

        settings_action = QAction("Settings/Preferences", self)
        settings_action.triggered.connect(self.action_controller.show_settings)
        edit_menu.addAction(settings_action)

        # --- Import Menu ---
        import_menu = menubar.addMenu("Import")

        import_proj = QAction("Import Project", self)
        import_proj.triggered.connect(self.action_controller.show_import_project)
        import_menu.addAction(import_proj)

        import_asset = QAction("Import Asset", self)
        import_asset.triggered.connect(
            lambda: self.action_controller.show_import_asset()
        )
        import_menu.addAction(import_asset)

        import_menu.addSeparator()

        import_anim_v = QAction("Import Animation (Video)", self)
        import_anim_v.triggered.connect(
            lambda: self.action_controller.show_import_animation_video()
        )
        import_menu.addAction(import_anim_v)

        import_anim_p = QAction("Import Animation (PNGs)", self)
        import_anim_p.triggered.connect(
            lambda: self.action_controller.show_import_animation_png()
        )
        import_menu.addAction(import_anim_p)

        # --- Export Menu ---
        export_menu = menubar.addMenu("Export")

        export_asset = QAction("Export Asset", self)
        export_asset.triggered.connect(
            lambda: self.action_controller.show_export(False)
        )
        export_menu.addAction(export_asset)

        export_anim = QAction("Export Animation", self)
        export_anim.triggered.connect(lambda: self.action_controller.show_export(True))
        export_menu.addAction(export_anim)

        export_menu.addSeparator()

        export_spritesheet = QAction("Generate Spritesheet", self)
        export_spritesheet.triggered.connect(self.action_controller.placeholder_action)
        export_menu.addAction(export_spritesheet)

        # --- Tools Menu ---
        tools_menu = menubar.addMenu("Tools")

        generate_ai_action = QAction("Generate with AI...", self)
        generate_ai_action.triggered.connect(self.action_controller.show_generation_dialog)
        tools_menu.addAction(generate_ai_action)

        # --- Help Menu ---
        help_menu = menubar.addMenu("Help")

        tutorials_action = QAction("Tutorials / Documentation", self)
        tutorials_action.triggered.connect(self.action_controller.show_tutorials)
        help_menu.addAction(tutorials_action)

        about_action = QAction("About", self)
        about_action.triggered.connect(self.action_controller.show_about)
        help_menu.addAction(about_action)

    def populate_recent_projects(self):
        """populate_recent_projects method."""
        self.recent_menu.clear()
        recent_projects = self.settings_manager.get_recent_projects()

        if not recent_projects:
            empty_action = QAction("No Recent Projects", self)
            empty_action.setEnabled(False)
            self.recent_menu.addAction(empty_action)
            return

        for path in recent_projects:
            action = QAction(os.path.basename(path), self)
            action.setToolTip(path)
            action.triggered.connect(
                lambda checked, p=path: self.open_recent_project(p)
            )
            self.recent_menu.addAction(action)

    def open_recent_project(self, path):
        """open_recent_project method."""
        if not os.path.exists(path):
            QMessageBox.warning(self, "Error", f"Project path does not exist:\n{path}")
            return

        project_name = os.path.basename(path)
        self.project_manager.registry.add_project(project_name, path)
        self.asset_browser.refresh_assets()

        # Select it
        iterator = __import__("PyQt6.QtWidgets").QtWidgets.QTreeWidgetItemIterator(
            self.asset_browser.tree_widget
        )
        while iterator.value():
            item = iterator.value()
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if data and data[0] == "project" and data[1] == project_name:
                self.asset_browser.tree_widget.setCurrentItem(item)
                break
            iterator += 1

    def on_asset_selected_from_dashboard(self, proj, asset):
        """on_asset_selected_from_dashboard method."""
        from PyQt6.QtWidgets import QTreeWidgetItemIterator
        from PyQt6.QtCore import Qt

        iterator = QTreeWidgetItemIterator(self.asset_browser.tree_widget)
        while iterator.value():
            item = iterator.value()
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if data and data[0] == "asset" and data[1] == proj and data[2] == asset:
                self.asset_browser.tree_widget.setCurrentItem(item)
                return
            iterator += 1

    def on_item_selected(self, item_type, proj, asset, anim, full_path):
        """on_item_selected method."""
        self.current_project = proj
        self.current_asset = asset
        self.current_animation = anim
        self.current_path = full_path

        if item_type == "project":
            self.project_dashboard.load_project(proj)
            self.right_panel.setCurrentIndex(0)
        elif item_type == "folder":
            self.project_dashboard.load_folder(
                proj, asset
            )  # folder name passed in asset param
            self.right_panel.setCurrentIndex(0)
        elif item_type == "asset":
            self.asset_dashboard.load_asset(proj, asset)
            self.right_panel.setCurrentIndex(1)
        elif item_type == "animation":
            self.right_panel.setCurrentIndex(2)

            legacy_name = anim if anim else (asset if asset else proj)

            # Determine the root Asset folder path for pipeline execution
            asset_path = ""
            if proj and asset:
                asset_path = os.path.join(
                    self.project_manager.get_project_path(proj), asset
                )
            elif proj:
                asset_path = self.project_manager.get_project_path(proj)

            self.pipeline_controls.set_asset(legacy_name, asset_path)

            # Check for pinned keyframe
            if asset_path:
                pinned_path = os.path.join(asset_path, "pinned_keyframe.png")
                if os.path.exists(pinned_path):
                    self.painter_widget.on_pinned_keyframe_updated(pinned_path)
                else:
                    self.painter_widget.on_pinned_keyframe_updated("")
            else:
                self.painter_widget.on_pinned_keyframe_updated("")

            if hasattr(self.timeline_widget, "load_animation"):
                self.timeline_widget.load_animation(asset_path, legacy_name)
            elif hasattr(self.timeline_widget, "load_path"):
                self.timeline_widget.load_path(full_path, legacy_name)
            else:
                self.timeline_widget.load_asset(legacy_name)

    def on_animation_selected_from_dashboard(self, proj, asset, anim):
        """on_animation_selected_from_dashboard method."""
        full_path = os.path.join(self.project_manager.get_project_path(proj), asset)
        self.on_item_selected("animation", proj, asset, anim, full_path)

    def add_background_task(self, task_name: str):
        """add_background_task method."""
        self.active_background_tasks.append(task_name)
        self.bg_task_widget.update_tasks(self.active_background_tasks)

    def remove_background_task(self, task_name: str):
        """remove_background_task method."""
        if task_name in self.active_background_tasks:
            self.active_background_tasks.remove(task_name)
        self.bg_task_widget.update_tasks(self.active_background_tasks)

    def on_pipeline_finished(self):
        """on_pipeline_finished method."""
        # Refresh timeline when pipeline script (e.g. process or normalize) completes
        if self.current_path and hasattr(self.timeline_widget, "load_path"):
            name = self.current_animation or self.current_asset or self.current_project
            self.timeline_widget.load_path(self.current_path, name)
        elif self.pipeline_controls.current_asset:
            self.timeline_widget.load_asset(self.pipeline_controls.current_asset)

        # Refresh the asset dashboard to update sizes (e.g. after compression)
        if hasattr(self, "asset_dashboard"):
            self.asset_dashboard.refresh_view()

    def _update_edit_menu(self):
        """Update Undo/Redo actions state."""
        self.undo_action.setEnabled(self.history_manager.can_undo())
        self.undo_action.setText(self.history_manager.undo_text())
        self.redo_action.setEnabled(self.history_manager.can_redo())
        self.redo_action.setText(self.history_manager.redo_text())

    def get_current_context(self) -> CommandContext:
        """Get current context for command execution/undo/redo."""
        return CommandContext(
            project_name=self.current_project or "",
            asset_name=self.current_asset or "",
            animation_name=self.current_animation or "",
        )

    def _handle_context_switch(self, context: CommandContext):
        """Handle a context switch requested by the HistoryManager."""
        item_type = "project"
        if context.animation_name:
            item_type = "animation"
        elif context.asset_name:
            item_type = "asset"

        path = ""
        if context.project_name:
            path = self.project_manager.get_project_path(context.project_name)
            if context.asset_name:
                path = os.path.join(path, context.asset_name)

        self.on_item_selected(
            item_type,
            context.project_name,
            context.asset_name,
            context.animation_name,
            path,
        )

    def _do_undo(self):
        """Trigger undo."""
        self.history_manager.undo(self.get_current_context())

    def _do_redo(self):
        """Trigger redo."""
        self.history_manager.redo(self.get_current_context())


def main():
    """main function."""
    if sys.platform == "win32":
        import ctypes

        try:
            myappid = "myproject.assetpipeline.gui.1"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass

    app = QApplication(sys.argv)

    # Set Application Icon
    icon_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "icons", "icon.png"
    )
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    base_dir = os.getcwd()
    window = AssetPipelineApp(base_dir)

    # Set Windows dark title bar
    if sys.platform == "win32":
        try:
            import ctypes

            hwnd = int(window.winId())
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            set_window_attribute = ctypes.windll.dwmapi.DwmSetWindowAttribute
            value = ctypes.c_int(1)
            # Try Windows 11 / new Windows 10 attribute
            res = set_window_attribute(
                hwnd,
                DWMWA_USE_IMMERSIVE_DARK_MODE,
                ctypes.byref(value),
                ctypes.sizeof(value),
            )
            if res != 0:
                # Try older Windows 10 attribute
                set_window_attribute(
                    hwnd, 19, ctypes.byref(value), ctypes.sizeof(value)
                )
        except Exception:
            pass

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
