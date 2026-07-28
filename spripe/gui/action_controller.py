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
    AboutDialog,
    TutorialsDialog,
    CompressDialog,
    ExportGifDialog,
)
from spripe.gui.generation_dialog import GenerationDialog
from spripe.scripts.normalize_animations import normalize_asset
from spripe.scripts.compress_animations import compress_asset
from spripe.core.history import Command, CommandContext
import uuid
import shutil
import copy
from spripe.gui.pipeline_controls import WorkerThread


class WorkspaceMetadataCommand(Command):
    """Command that caches metadata before and after a change."""

    def __init__(
        self, description: str, context: CommandContext, proj_name, pm, action_cb
    ):
        super().__init__(description, context)
        self.proj_name = proj_name
        self.pm = pm
        self.action_cb = action_cb
        self.before_metadata = copy.deepcopy(pm.get_project_metadata(proj_name))

    def execute(self):
        self.action_cb()
        self.after_metadata = copy.deepcopy(
            self.pm.get_project_metadata(self.proj_name)
        )

    def undo(self):
        self.pm.save_project_metadata(self.proj_name, self.before_metadata)
        from spripe.core.signal_manager import SignalManager

        SignalManager.get_instance().workspace_changed.emit("")

    def redo(self):
        self.pm.save_project_metadata(self.proj_name, self.after_metadata)
        from spripe.core.signal_manager import SignalManager

        SignalManager.get_instance().workspace_changed.emit("")


class WorkspaceDeleteCommand(Command):
    """Command that moves a file or folder to a backup before deletion."""

    def __init__(
        self,
        description: str,
        context: CommandContext,
        src_path,
        workspace_dir,
        action_cb,
    ):
        super().__init__(description, context)
        self.src_path = src_path
        self.workspace_dir = workspace_dir
        self.action_cb = action_cb
        self.backup_path = os.path.join(workspace_dir, ".history", str(uuid.uuid4()))
        os.makedirs(os.path.dirname(self.backup_path), exist_ok=True)
        if os.path.isdir(self.src_path):
            shutil.copytree(self.src_path, self.backup_path)
        else:
            shutil.copy2(self.src_path, self.backup_path)

    def execute(self):
        self.action_cb()

    def undo(self):
        if not os.path.exists(self.src_path):
            if os.path.isdir(self.backup_path):
                shutil.copytree(self.backup_path, self.src_path)
            else:
                shutil.copy2(self.backup_path, self.src_path)
        from spripe.core.signal_manager import SignalManager

        SignalManager.get_instance().workspace_changed.emit("")

    def redo(self):
        self.action_cb()
        from spripe.core.signal_manager import SignalManager

        SignalManager.get_instance().workspace_changed.emit("")


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

    def show_about(self):
        """show_about method."""
        dlg = AboutDialog(self.mw)
        dlg.exec()

    def show_tutorials(self):
        """show_tutorials method."""
        dlg = TutorialsDialog(self.mw)
        dlg.exec()

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
        file_path, _ = QFileDialog.getOpenFileName(
            self.mw,
            "Import Project",
            "",
            "Spripe Pack (*.spripepack *.zip);;Spripe Project (*.spripe)",
        )
        if file_path:
            if file_path.endswith(".spripepack") or file_path.endswith(".zip"):
                try:
                    self.mw.project_manager.fs.import_project(file_path)
                    QMessageBox.information(
                        self.mw, "Success", f"Project imported successfully."
                    )
                except Exception as e:
                    QMessageBox.critical(
                        self.mw, "Error", f"Failed to import project:\n{e}"
                    )
            else:
                QMessageBox.information(
                    self.mw,
                    "Import",
                    "Use File -> Open Project to open a .spripe file directly, or manually copy the folder.",
                )

    def show_open_project(self):
        """show_open_project method."""
        file_path, _ = QFileDialog.getOpenFileName(
            self.mw, "Open Project", "", "Spripe Project (*.spripe *.json)"
        )
        if file_path:
            from PyQt6.QtWidgets import QCheckBox
            from spripe.core.settings_manager import SettingsManager

            project_dir = os.path.dirname(file_path)
            project_name = os.path.basename(project_dir)

            # Ask if they want to copy to workspace
            msg_box = QMessageBox(self.mw)
            msg_box.setWindowTitle("Open Project")
            msg_box.setText(f"Open project '{project_name}'?")
            cb = QCheckBox("Copy to Workspace")
            msg_box.setCheckBox(cb)
            msg_box.setStandardButtons(
                QMessageBox.StandardButton.Open | QMessageBox.StandardButton.Cancel
            )

            if msg_box.exec() == QMessageBox.StandardButton.Open:
                if cb.isChecked():
                    try:
                        import shutil

                        dest = os.path.join(
                            self.mw.project_manager.workspace_dir, project_name
                        )
                        if os.path.exists(dest):
                            QMessageBox.warning(
                                self.mw,
                                "Warning",
                                "Project already exists in workspace.",
                            )
                            return
                        shutil.copytree(project_dir, dest)
                        self.mw.project_manager.registry.add_project(project_name, dest)
                    except Exception as e:
                        QMessageBox.critical(
                            self.mw, "Error", f"Failed to copy project:\n{e}"
                        )
                        return
                else:
                    self.mw.project_manager.registry.add_project(
                        project_name, project_dir
                    )

                self.mw.settings_manager.add_recent_project(project_dir)
                self.mw.asset_browser.refresh_assets()
                QMessageBox.information(self.mw, "Success", f"Project opened.")

    def show_save_project_as(self):
        """show_save_project_as method."""
        if not self.mw.current_project:
            QMessageBox.warning(self.mw, "Warning", "No project selected to save.")
            return

        file_path, selected_filter = QFileDialog.getSaveFileName(
            self.mw,
            "Save Project As",
            self.mw.current_project,
            "Spripe Project Folder (*.spripe);;Spripe Pack Archive (*.spripepack)",
        )
        if file_path:
            try:
                import shutil

                src_path = self.mw.project_manager.get_project_path(
                    self.mw.current_project
                )

                if ".spripepack" in selected_filter:
                    if file_path.endswith(".spripepack"):
                        file_path = file_path[:-11]  # remove extension for make_archive
                    shutil.make_archive(file_path, "zip", src_path)
                    if os.path.exists(file_path + ".zip"):
                        os.rename(file_path + ".zip", file_path + ".spripepack")
                else:
                    if os.path.exists(file_path):
                        QMessageBox.warning(
                            self.mw, "Warning", "Destination already exists."
                        )
                        return
                    shutil.copytree(src_path, file_path)

                QMessageBox.information(
                    self.mw, "Success", "Project saved successfully."
                )
            except Exception as e:
                QMessageBox.critical(self.mw, "Error", f"Failed to save project:\n{e}")

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
            if not hasattr(self, 'active_export_workers'):
                self.active_export_workers = []

            worker = WorkerThread(
                self.mw.project_manager.export_item,
                project_name=proj,
                asset_name=asset,
                animation_name=anim if is_animation else None,
                dest_path=dlg.dest_path,
                export_type=dlg.export_type,
                compression_level=dlg.compression_level,
                gif_fps=getattr(dlg, 'fps', 12)
            )
            worker.progress_signal.connect(lambda msg: self.mw.statusBar().showMessage(msg, 5000))

            task_name = f"Exporting {item_name}..."

            def on_finished(success, output):
                self.mw.remove_background_task(task_name)
                if success:
                    QMessageBox.information(self.mw, "Success", f"Successfully exported to:\n{dlg.dest_path}")
                else:
                    QMessageBox.critical(self.mw, "Export Failed", f"An error occurred during export:\n{output}")
                if worker in self.active_export_workers:
                    self.active_export_workers.remove(worker)

            worker.finished_signal.connect(on_finished)
            self.active_export_workers.append(worker)
            self.mw.statusBar().showMessage(f"Starting export...", 5000)
            self.mw.add_background_task(task_name)
            worker.start()

    def show_export_project(self, proj_name):
        """show_export_project method."""
        dlg = ExportDialog(False, proj_name, self.mw)
        if dlg.exec():
            if not hasattr(self, 'active_export_workers'):
                self.active_export_workers = []

            worker = WorkerThread(
                self.mw.project_manager.export_item,
                project_name=proj_name,
                asset_name=None,
                animation_name=None,
                dest_path=dlg.dest_path,
                export_type=dlg.export_type,
                gif_fps=getattr(dlg, 'fps', 12)
            )
            worker.progress_signal.connect(lambda msg: self.mw.statusBar().showMessage(msg, 5000))

            task_name = f"Exporting Project {proj_name}..."

            def on_finished(success, output):
                self.mw.remove_background_task(task_name)
                if success:
                    QMessageBox.information(self.mw, "Success", f"Exported project {proj_name} successfully to {dlg.dest_path}")
                else:
                    QMessageBox.critical(self.mw, "Export Failed", f"An error occurred during export:\n{output}")
                if worker in self.active_export_workers:
                    self.active_export_workers.remove(worker)

            worker.finished_signal.connect(on_finished)
            self.active_export_workers.append(worker)
            self.mw.statusBar().showMessage(f"Starting project export...", 5000)
            self.mw.add_background_task(task_name)
            worker.start()

    def make_png_sequence(self, proj_name, asset_name, anim_names):
        """make_png_sequence method."""
        fps = self.mw.settings_manager.get("png_sequence_fps", 12)
        use_ai = True

        from spripe.gui.sequence_worker import SequenceExtractionWorker

        # Keep a reference to prevent garbage collection
        if not hasattr(self, 'active_sequence_workers'):
            self.active_sequence_workers = []

        proj_path = self.mw.project_manager.get_project_path(proj_name)
        worker = SequenceExtractionWorker(proj_path, asset_name, anim_names, fps, use_ai)

        worker.progress_signal.connect(lambda msg: self.mw.statusBar().showMessage(msg, 5000))

        task_name = f"Extracting {len(anim_names)} PNG sequence(s)..."

        def on_finished():
            self.mw.remove_background_task(task_name)
            self.mw.statusBar().showMessage(f"PNG sequence extraction finished for {len(anim_names)} animation(s).", 5000)
            self.mw.asset_dashboard.refresh_view()
            if worker in self.active_sequence_workers:
                self.active_sequence_workers.remove(worker)
            QMessageBox.information(self.mw, "Extraction Complete", f"Successfully extracted PNG sequences for {len(anim_names)} animation(s).")

        def on_error(err):
            self.mw.remove_background_task(task_name)
            self.mw.statusBar().showMessage("PNG extraction error.", 5000)
            QMessageBox.critical(self.mw, "Error", f"Failed to extract PNG sequence:\n{err}")
            if worker in self.active_sequence_workers:
                self.active_sequence_workers.remove(worker)

        worker.finished_signal.connect(on_finished)
        worker.error_signal.connect(on_error)

        self.active_sequence_workers.append(worker)
        self.mw.statusBar().showMessage(f"Starting PNG sequence extraction for {len(anim_names)} animation(s)...", 5000)
        self.mw.add_background_task(task_name)
        worker.start()

    def show_create_folder(self, proj_name):
        """show_create_folder method."""
        text, ok = QInputDialog.getText(
            self.mw, "Create Virtual Folder", "Folder Name:"
        )
        if ok and text:

            def action():
                metadata = self.mw.project_manager.get_project_metadata(proj_name)
                if "folders" not in metadata:
                    metadata["folders"] = []
                if text not in metadata["folders"]:
                    metadata["folders"].append(text)
                    self.mw.project_manager.save_project_metadata(proj_name, metadata)
                from spripe.core.signal_manager import SignalManager

                SignalManager.get_instance().workspace_changed.emit("")

            if self.mw.history_manager and self.mw.get_current_context:
                cmd = WorkspaceMetadataCommand(
                    f"Create Folder '{text}'",
                    self.mw.get_current_context(),
                    proj_name,
                    self.mw.project_manager,
                    action,
                )
                self.mw.history_manager.push(cmd)
            else:
                action()

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

            def action():
                m = self.mw.project_manager.get_project_metadata(proj_name)
                if "virtual_folders" not in m:
                    m["virtual_folders"] = {}

                if item.startswith("(Root"):
                    if asset_name in m["virtual_folders"]:
                        del m["virtual_folders"][asset_name]
                else:
                    m["virtual_folders"][asset_name] = item

                self.mw.project_manager.save_project_metadata(proj_name, m)
                from spripe.core.signal_manager import SignalManager

                SignalManager.get_instance().workspace_changed.emit("")
                if self.mw.current_project == proj_name:
                    self.mw.project_dashboard.refresh_view()

            if self.mw.history_manager and self.mw.get_current_context:
                cmd = WorkspaceMetadataCommand(
                    f"Move '{asset_name}'",
                    self.mw.get_current_context(),
                    proj_name,
                    self.mw.project_manager,
                    action,
                )
                self.mw.history_manager.push(cmd)
            else:
                action()

    def remove_folder(self, proj_name, folder_name):
        """remove_folder method."""
        dlg = QMessageBox.question(
            self.mw,
            "Confirm Delete",
            f"Are you sure you want to remove the virtual folder '{folder_name}'?\n\nAssets inside it will be moved to the root.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if dlg == QMessageBox.StandardButton.Yes:

            def action():
                m = self.mw.project_manager.get_project_metadata(proj_name)
                if "folders" in m and folder_name in m["folders"]:
                    m["folders"].remove(folder_name)

                if "virtual_folders" in m:
                    for asset, folder in list(m["virtual_folders"].items()):
                        if folder == folder_name:
                            del m["virtual_folders"][asset]
                self.mw.project_manager.save_project_metadata(proj_name, m)
                from spripe.core.signal_manager import SignalManager

                SignalManager.get_instance().workspace_changed.emit("")

            if self.mw.history_manager and self.mw.get_current_context:
                cmd = WorkspaceMetadataCommand(
                    f"Remove Folder '{folder_name}'",
                    self.mw.get_current_context(),
                    proj_name,
                    self.mw.project_manager,
                    action,
                )
                self.mw.history_manager.push(cmd)
            else:
                action()

    def remove_project(self, proj_name):
        """remove_project method."""
        dlg = DeleteConfirmationDialog(proj_name, is_project=True, parent=self.mw)
        if dlg.exec():
            delete_files = dlg.delete_mode == "delete"

            def action():
                self.mw.project_manager.delete_project(proj_name, delete_files)

            if (
                delete_files
                and self.mw.history_manager
                and self.mw.get_current_context
            ):
                src = self.mw.project_manager.get_project_path(proj_name)
                if os.path.exists(src):
                    cmd = WorkspaceDeleteCommand(
                        f"Delete Project '{proj_name}'",
                        self.mw.get_current_context(),
                        src,
                        self.mw.project_manager.workspace_dir,
                        action,
                    )
                    self.mw.history_manager.push(cmd)
                else:
                    action()
            else:
                action()

    def remove_asset(self, proj_name, asset_name):
        """remove_asset method."""
        dlg = DeleteConfirmationDialog(asset_name, is_project=False, parent=self.mw)
        if dlg.exec():
            if dlg.delete_mode == "delete":

                def action():
                    self.mw.project_manager.delete_asset(proj_name, asset_name)

                if self.mw.history_manager and self.mw.get_current_context:
                    src = os.path.join(
                        self.mw.project_manager.get_project_path(proj_name), asset_name
                    )
                    if os.path.exists(src):
                        cmd = WorkspaceDeleteCommand(
                            f"Delete Asset '{asset_name}'",
                            self.mw.get_current_context(),
                            src,
                            self.mw.project_manager.workspace_dir,
                            action,
                        )
                        self.mw.history_manager.push(cmd)
                    else:
                        action()
                else:
                    action()

    def remove_animation(self, proj, asset, anim):
        """remove_animation method."""
        dlg = DeleteConfirmationDialog(anim, is_project=False, parent=self.mw)
        if dlg.exec():
            if dlg.delete_mode == "delete":

                def action():
                    self.mw.project_manager.delete_animation(proj, asset, anim)

                if self.mw.history_manager and self.mw.get_current_context:
                    src = os.path.join(
                        self.mw.project_manager.get_project_path(proj), asset, anim
                    )
                    if os.path.exists(src):
                        cmd = WorkspaceDeleteCommand(
                            f"Delete Anim '{anim}'",
                            self.mw.get_current_context(),
                            src,
                            self.mw.project_manager.workspace_dir,
                            action,
                        )
                        self.mw.history_manager.push(cmd)
                    else:
                        action()
                else:
                    action()

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
                overwrite=True,
            )

    def compress_animation(self, proj, asset, anim):
        """compress_animation method."""
        asset_path = os.path.join(self.mw.project_manager.get_project_path(proj), asset)
        item_name = f"{len(anim)} animations" if isinstance(anim, list) else anim

        dlg = CompressDialog(item_name, self.mw)
        if dlg.exec():
            if isinstance(anim, list):
                msg = f"Compressing {len(anim)} animation(s)..."
                self.mw.pipeline_controls.start_worker(
                    compress_asset,
                    msg,
                    asset_dir=asset_path,
                    colors=dlg.colors,
                    anim_name=anim,
                    overwrite=True,
                )
            else:
                msg = f"Compressing {anim}..."
                self.mw.pipeline_controls.start_worker(
                    compress_asset,
                    msg,
                    asset_dir=asset_path,
                    colors=dlg.colors,
                    anim_name=[anim],
                    overwrite=True,
                )

    def export_gif_animation(self, proj, asset, anim):
        """export_gif_animation method."""
        dlg = ExportGifDialog(anim, self.mw)
        if dlg.exec():
            if not hasattr(self, 'active_export_workers'):
                self.active_export_workers = []

            worker = WorkerThread(
                self.mw.project_manager.export_item,
                project_name=proj,
                asset_name=asset,
                animation_name=anim,
                dest_path=dlg.dest_path,
                export_type="GIF",
                compression_level=None,
                gif_fps=dlg.fps
            )
            worker.progress_signal.connect(lambda msg: self.mw.statusBar().showMessage(msg, 5000))

            task_name = f"Exporting GIF {anim}..."

            def on_finished(success, output):
                self.mw.remove_background_task(task_name)
                if success:
                    QMessageBox.information(self.mw, "Success", f"Successfully exported GIF to:\n{dlg.dest_path}")
                else:
                    QMessageBox.critical(self.mw, "Export Failed", f"An error occurred during GIF export:\n{output}")
                if worker in self.active_export_workers:
                    self.active_export_workers.remove(worker)

            worker.finished_signal.connect(on_finished)
            self.active_export_workers.append(worker)
            self.mw.statusBar().showMessage(f"Starting GIF export...", 5000)
            self.mw.add_background_task(task_name)
            worker.start()

    def show_generation_dialog(self, metadata=None):
        """show_generation_dialog method."""
        if not self.mw.current_project:
            QMessageBox.warning(self.mw, "No Project", "Please open a project first.")
            return

        proj_path = os.path.join(self.mw.project_manager.workspace_dir, self.mw.current_project)
        workspace_dir = self.mw.project_manager.workspace_dir
        dlg = GenerationDialog(proj_path, metadata, workspace_dir, self.mw)
        dlg.exec()
