"""
Module docstring.
"""
import os
from PyQt6.QtWidgets import QMessageBox, QFileDialog, QInputDialog
from spripe.gui.dialogs import (
    SettingsDialog,
    NewProjectDialog,
    NewAssetDialog,
    NewAnimationDialog,
    ExportDialog,
    ImportProjectDialog,
    ImportAssetDialog,
    DeleteConfirmationDialog,
)
from spripe.scripts.normalize_animations import normalize_asset


class ActionController:
    """ActionController class."""
    def __init__(self, main_window):
        """__init__ method."""
        self.mw = main_window

    def placeholder_action(self):
        """placeholder_action method."""
        QMessageBox.information(
            self.mw, "Coming Soon", "This feature is not yet implemented."
        )

    def show_settings(self):
        """show_settings method."""
        dlg = SettingsDialog(self.mw.settings_manager, self.mw)
        if dlg.exec():
            # Update workspace if changed
            new_workspace = self.mw.settings_manager.get("workspace_dir")
            if self.mw.project_manager.workspace_dir != new_workspace:
                self.mw.project_manager.set_workspace(new_workspace)

    def show_new_project(self):
        """show_new_project method."""
        dlg = NewProjectDialog(self.mw)
        if dlg.exec():
            self.mw.project_manager.create_project(dlg.project_name)

    def show_new_asset(self, preselected_proj=None):
        """show_new_asset method."""
        projects = self.mw.project_manager.get_projects()
        current = preselected_proj if preselected_proj else self.mw.current_project
        dlg = NewAssetDialog(projects, current, self.mw)
        if dlg.exec():
            self.mw.project_manager.create_asset(dlg.selected_project, dlg.asset_name)

    def show_new_animation(self, preselected_proj=None, preselected_asset=None):
        """show_new_animation method."""
        projects = self.mw.project_manager.get_projects()
        proj = preselected_proj if preselected_proj else self.mw.current_project
        asset = preselected_asset if preselected_asset else self.mw.current_asset
        dlg = NewAnimationDialog(
            projects, self.mw.project_manager.get_assets, proj, asset, self.mw
        )
        if dlg.exec():
            self.mw.project_manager.create_animation(
                dlg.selected_project, dlg.selected_asset, dlg.animation_name
            )

    def show_import_project(self):
        """show_import_project method."""
        dlg = ImportProjectDialog(self.mw)
        if dlg.exec():
            self.mw.project_manager.create_project(dlg.project_name, dlg.project_path)

    def show_import_asset(self, preselected_proj=None):
        """show_import_asset method."""
        projects = self.mw.project_manager.get_projects()
        current = preselected_proj if preselected_proj else self.mw.current_project
        dlg = ImportAssetDialog(projects, current, self.mw)
        if dlg.exec():
            self.mw.project_manager.create_asset(
                dlg.selected_project, dlg.asset_name, dlg.asset_path
            )

    def show_import_animation_video(
        self, preselected_proj=None, preselected_asset=None
    ):
        """show_import_animation_video method."""
        projects = self.mw.project_manager.get_projects()
        proj = preselected_proj if preselected_proj else self.mw.current_project
        asset = preselected_asset if preselected_asset else self.mw.current_asset
        dlg = NewAnimationDialog(
            projects, self.mw.project_manager.get_assets, proj, asset, self.mw
        )
        dlg.setWindowTitle("Import Animation (Video)")
        if dlg.exec():
            file_path, _ = QFileDialog.getOpenFileName(
                self.mw, "Select Video", "", "Video Files (*.mp4 *.avi *.mkv)"
            )
            if file_path:
                self.mw.project_manager.create_animation_from_video(
                    dlg.selected_project,
                    dlg.selected_asset,
                    dlg.animation_name,
                    file_path,
                )

    def show_import_animation_png(self, preselected_proj=None, preselected_asset=None):
        """show_import_animation_png method."""
        projects = self.mw.project_manager.get_projects()
        proj = preselected_proj if preselected_proj else self.mw.current_project
        asset = preselected_asset if preselected_asset else self.mw.current_asset
        dlg = NewAnimationDialog(
            projects, self.mw.project_manager.get_assets, proj, asset, self.mw
        )
        dlg.setWindowTitle("Import Animation (PNG Sequence)")
        if dlg.exec():
            dir_path = QFileDialog.getExistingDirectory(
                self.mw, "Select PNG Sequence Folder"
            )
            if dir_path:
                self.mw.project_manager.create_animation_from_pngs(
                    dlg.selected_project,
                    dlg.selected_asset,
                    dlg.animation_name,
                    dir_path,
                )

    def show_export(
        self,
        is_animation,
        preselected_proj=None,
        preselected_asset=None,
        preselected_anim=None,
    ):
        """show_export method."""
        proj = preselected_proj if preselected_proj else self.mw.current_project
        asset = preselected_asset if preselected_asset else self.mw.current_asset
        anim = preselected_anim if preselected_anim else self.mw.current_animation

        if is_animation and not anim:
            QMessageBox.warning(
                self.mw, "Warning", "Please select an animation to export."
            )
            return
        if not is_animation and not asset:
            QMessageBox.warning(self.mw, "Warning", "Please select an asset to export.")
            return

        item_name = anim if is_animation else asset
        dlg = ExportDialog(is_animation, item_name, self.mw)
        if dlg.exec():
            try:
                self.mw.project_manager.export_item(
                    proj,
                    asset,
                    anim if is_animation else None,
                    dlg.dest_path,
                    dlg.export_type,
                )
                QMessageBox.information(
                    self.mw, "Success", f"Successfully exported to:\n{dlg.dest_path}"
                )
            except Exception as e:
                QMessageBox.critical(
                    self.mw, "Export Failed", f"An error occurred during export:\n{e}"
                )

    def show_export_project(self, proj_name):
        """show_export_project method."""
        dlg = ExportDialog(False, proj_name, self.mw)
        if dlg.exec():
            try:
                self.mw.project_manager.export_item(
                    proj_name, None, None, dlg.dest_path, dlg.export_type
                )
                QMessageBox.information(
                    self.mw,
                    "Success",
                    f"Exported project {proj_name} successfully to {dlg.dest_path}",
                )
            except Exception as e:
                QMessageBox.critical(
                    self.mw, "Export Failed", f"An error occurred during export:\n{e}"
                )

    def show_create_folder(self, proj_name):
        """show_create_folder method."""
        text, ok = QInputDialog.getText(
            self.mw, "Create Virtual Folder", "Folder Name:"
        )
        if ok and text:
            metadata = self.mw.project_manager.get_project_metadata(proj_name)
            if "folders" not in metadata:
                metadata["folders"] = []
            if text not in metadata["folders"]:
                metadata["folders"].append(text)
                self.mw.project_manager.save_project_metadata(proj_name, metadata)

    def show_move_to_folder(self, proj_name, asset_name):
        """show_move_to_folder method."""
        metadata = self.mw.project_manager.get_project_metadata(proj_name)
        folders = list(set(metadata.get("virtual_folders", {}).values()))
        folders.extend([f for f in metadata.get("folders", []) if f not in folders])
        folders.insert(0, "(Root - Remove from folder)")

        item, ok = QInputDialog.getItem(
            self.mw,
            "Move to Folder",
            f"Select destination for '{asset_name}':",
            folders,
            0,
            True,
        )
        if ok and item:
            if "virtual_folders" not in metadata:
                metadata["virtual_folders"] = {}

            if item.startswith("(Root"):
                if asset_name in metadata["virtual_folders"]:
                    del metadata["virtual_folders"][asset_name]
            else:
                metadata["virtual_folders"][asset_name] = item

            self.mw.project_manager.save_project_metadata(proj_name, metadata)
            if self.mw.current_project == proj_name:
                self.mw.project_dashboard.refresh_view()

    def remove_project(self, proj_name):
        """remove_project method."""
        dlg = DeleteConfirmationDialog(proj_name, is_project=True, parent=self.mw)
        if dlg.exec():
            delete_files = dlg.delete_mode == "delete"
            self.mw.project_manager.delete_project(proj_name, delete_files)

    def remove_asset(self, proj_name, asset_name):
        """remove_asset method."""
        dlg = DeleteConfirmationDialog(asset_name, is_project=False, parent=self.mw)
        if dlg.exec():
            if dlg.delete_mode == "delete":
                self.mw.project_manager.delete_asset(proj_name, asset_name)

    def remove_animation(self, proj, asset, anim):
        """remove_animation method."""
        dlg = DeleteConfirmationDialog(anim, is_project=False, parent=self.mw)
        if dlg.exec():
            if dlg.delete_mode == "delete":
                self.mw.project_manager.delete_animation(proj, asset, anim)

    def renormalize_animation(self, proj, asset, anim):
        """renormalize_animation method."""
        asset_path = os.path.join(self.mw.project_manager.get_project_path(proj), asset)

        if isinstance(anim, list):
            if not anim:
                msg = "Renormalizing all animations..."
                self.mw.pipeline_controls.start_worker(
                    normalize_asset, msg, asset_dir=asset_path, overwrite=True
                )
            else:
                msg = f"Renormalizing {len(anim)} animation(s)..."
                self.mw.pipeline_controls.start_worker(
                    normalize_asset,
                    msg,
                    asset_dir=asset_path,
                    anim_name=anim,
                    overwrite=True,
                )
        else:
            msg = f"Renormalizing {anim}..."
            self.mw.pipeline_controls.start_worker(
                normalize_asset,
                msg,
                asset_dir=asset_path,
                anim_name=[anim],
                overwrite=True,
            )
