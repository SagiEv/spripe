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
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtCore import Qt

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
        self.painter_widget = PainterWidget(self.settings_manager)
        self.timeline_widget = TimelineWidget(self.base_dir, self.settings_manager)

        self.action_controller = ActionController(self)

        self.init_menu_bar()

        # Connect signals
        self.asset_browser.item_selected.connect(self.on_item_selected)
        self.pipeline_controls.pipeline_finished.connect(self.on_pipeline_finished)
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

        save_proj_action = QAction("Save Project", self)
        save_proj_action.triggered.connect(self.action_controller.placeholder_action)
        file_menu.addAction(save_proj_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # --- Edit Menu ---
        edit_menu = menubar.addMenu("Edit")

        undo_action = QAction("Undo", self)
        undo_action.triggered.connect(self.action_controller.placeholder_action)
        edit_menu.addAction(undo_action)

        redo_action = QAction("Redo", self)
        redo_action.triggered.connect(self.action_controller.placeholder_action)
        edit_menu.addAction(redo_action)

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

        # --- Help Menu ---
        help_menu = menubar.addMenu("Help")

        about_action = QAction("About", self)
        about_action.triggered.connect(self.action_controller.placeholder_action)
        help_menu.addAction(about_action)

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

    def on_pipeline_finished(self):
        """on_pipeline_finished method."""
        # Refresh timeline when pipeline script (e.g. process or normalize) completes
        if self.current_path and hasattr(self.timeline_widget, "load_path"):
            name = self.current_animation or self.current_asset or self.current_project
            self.timeline_widget.load_path(self.current_path, name)
        elif self.pipeline_controls.current_asset:
            self.timeline_widget.load_asset(self.pipeline_controls.current_asset)


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
