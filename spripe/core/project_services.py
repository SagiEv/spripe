"""
Module docstring.
"""

import json
import shutil
import tempfile
from pathlib import Path
from typing import List, Dict, Optional, Set, Tuple, Callable

from spripe.core.config import Config
from spripe.core.signal_manager import SignalManager
from spripe.scripts.compress_animations import compress_asset
from spripe.scripts.export_gif import export_gif


class WorkspaceRegistry:
    """WorkspaceRegistry class."""

    def __init__(self, workspace_dir: str):
        """__init__ method."""
        self.workspace_dir = Path(workspace_dir)
        self.registry_file = self.workspace_dir / Config.FILE_REGISTRY
        self.projects: Dict[str, str] = {}
        self.load_error = None

        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        try:
            self.load_registry()
        except RuntimeError as e:
            self.load_error = str(e)

    def set_workspace(self, workspace_dir: str) -> None:
        """set_workspace method."""
        self.workspace_dir = Path(workspace_dir)
        self.registry_file = self.workspace_dir / Config.FILE_REGISTRY
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.load_registry()
        SignalManager.get_instance().workspace_changed.emit(str(self.workspace_dir))

    def load_registry(self) -> None:
        """load_registry method."""
        self.projects = {}
        if self.registry_file.exists():
            try:
                with open(self.registry_file, "r", encoding="utf-8") as f:
                    self.projects = json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                raise RuntimeError(f"Error: {e}") from e

        # Auto-discover
        for item in self.workspace_dir.iterdir():
            if item.is_dir() and item.name != "Standalone" and not item.name.startswith("."):
                self.projects[item.name] = str(item)

    def save_registry(self) -> None:
        """save_registry method."""
        try:
            with open(self.registry_file, "w", encoding="utf-8") as f:
                json.dump(self.projects, f, indent=4)
        except (json.JSONDecodeError, OSError) as e:
            raise RuntimeError(f"Error: {e}") from e

    def get_project_path(self, project_name: str) -> Path:
        """get_project_path method."""
        if project_name == "Standalone":
            return self.workspace_dir / "Standalone"
        return Path(self.projects.get(project_name, self.workspace_dir / project_name))

    def get_projects(self) -> List[str]:
        """get_projects method."""
        return list(set(list(self.projects.keys()) + ["Standalone"]))

    def add_project(self, project_name: str, path: Path):
        """add_project method."""
        self.projects[project_name] = str(path)
        self.save_registry()

    def remove_project(self, project_name: str):
        """remove_project method."""
        self.projects.pop(project_name, None)
        self.save_registry()


class ProjectMetadataService:
    """ProjectMetadataService class."""

    def __init__(self, registry: WorkspaceRegistry):
        """__init__ method."""
        self.registry = registry

    def get_metadata(self, project_name: str) -> dict:
        """get_metadata method."""
        project_path = self.registry.get_project_path(project_name)
        meta_file = project_path / Config.FILE_PROJECT_META
        if meta_file.exists():
            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading project metadata for {project_name}: {e}")
        return {"virtual_folders": {}}

    def save_metadata(self, project_name: str, metadata: dict) -> None:
        """save_metadata method."""
        project_path = self.registry.get_project_path(project_name)
        project_path.mkdir(parents=True, exist_ok=True)
        meta_file = project_path / Config.FILE_PROJECT_META
        try:
            with open(meta_file, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=4)
            SignalManager.get_instance().metadata_updated.emit(project_name)
        except Exception as e:
            print(f"Error saving project metadata for {project_name}: {e}")

    def get_folder_template(self, project_name: str, folder_name: str) -> List[str]:
        """get_folder_template method."""
        metadata = self.get_metadata(project_name)
        return metadata.get("folder_templates", {}).get(folder_name, [])

    def set_folder_template(
        self, project_name: str, folder_name: str, template: List[str]
    ) -> None:
        """set_folder_template method."""
        metadata = self.get_metadata(project_name)
        if "folder_templates" not in metadata:
            metadata["folder_templates"] = {}
        metadata["folder_templates"][folder_name] = template
        self.save_metadata(project_name, metadata)


class FileSystemService:
    """FileSystemService class."""

    def __init__(
        self, registry: WorkspaceRegistry, metadata_service: ProjectMetadataService
    ):
        """__init__ method."""
        self.registry = registry
        self.metadata = metadata_service

    def get_assets(self, project_name: str) -> List[str]:
        """get_assets method."""
        assets = []
        project_path = self.registry.get_project_path(project_name)
        if not project_path.exists():
            return assets

        for item in project_path.iterdir():
            if item.is_dir():
                assets.append(item.name)
        return assets

    def get_animations(self, project_name: str, asset_name: str) -> List[str]:
        """get_animations method."""
        animations: Set[str] = set()
        asset_path = self.registry.get_project_path(project_name) / asset_name

        videos_dir = asset_path / Config.DIR_VIDEOS
        raw_dir = asset_path / Config.DIR_RAW_OUTPUT
        norm_dir = asset_path / Config.DIR_NORMALIZED_OUTPUT
        comp_dir = asset_path / Config.DIR_COMPRESSED_OUTPUT

        if videos_dir.exists():
            for f in videos_dir.iterdir():
                if f.suffix == ".mp4":
                    animations.add(f.stem)

        if raw_dir.exists():
            for d in raw_dir.iterdir():
                if d.name.startswith(Config.PREFIX_RAW):
                    animations.add(d.name[len(Config.PREFIX_RAW) :])

        if norm_dir.exists():
            for d in norm_dir.iterdir():
                if d.name.startswith(Config.PREFIX_NORMALIZED):
                    animations.add(d.name[len(Config.PREFIX_NORMALIZED) :])

        if comp_dir.exists():
            for d in comp_dir.iterdir():
                if d.name.startswith(Config.PREFIX_COMPRESSED):
                    animations.add(d.name[len(Config.PREFIX_COMPRESSED) :])

        return list(animations)

    def create_project(
        self, project_name: str, external_path: Optional[str] = None
    ) -> str:
        """create_project method."""
        if external_path:
            path = Path(external_path)
            self.registry.add_project(project_name, path)
            SignalManager.get_instance().project_created.emit(project_name)
            return str(path)

        path = self.registry.workspace_dir / project_name
        path.mkdir(parents=True, exist_ok=True)
        self.registry.add_project(project_name, path)
        SignalManager.get_instance().project_created.emit(project_name)
        return str(path)

    def create_asset(
        self, project_name: str, asset_name: str, external_path: Optional[str] = None
    ) -> Tuple[str, str]:
        """create_asset method."""
        if not project_name:
            project_name = "Standalone"

        project_path = self.registry.get_project_path(project_name)
        asset_path = project_path / asset_name

        try:
            if external_path:
                if asset_path.exists():
                    shutil.rmtree(asset_path)
                shutil.copytree(external_path, asset_path)
            else:
                asset_path.mkdir(parents=True, exist_ok=True)

            (asset_path / Config.DIR_VIDEOS).mkdir(parents=True, exist_ok=True)
            (asset_path / Config.DIR_RAW_OUTPUT).mkdir(parents=True, exist_ok=True)
            (asset_path / Config.DIR_NORMALIZED_OUTPUT).mkdir(
                parents=True, exist_ok=True
            )
            (asset_path / Config.DIR_COMPRESSED_OUTPUT).mkdir(
                parents=True, exist_ok=True
            )

            SignalManager.get_instance().asset_created.emit(project_name, asset_name)
        except OSError as e:
            raise Exception(f"Error: {e}") from e

        return project_name, str(asset_path)

    def create_animation(
        self, project_name: str, asset_name: str, animation_name: str
    ) -> str:
        """create_animation method."""
        if not project_name:
            project_name = "Standalone"
        if not asset_name:
            asset_name = "DefaultAsset"

        project_path = self.registry.get_project_path(project_name)
        asset_path = project_path / asset_name

        target_dir = (
            asset_path / Config.DIR_RAW_OUTPUT / f"{Config.PREFIX_RAW}{animation_name}"
        )
        target_dir.mkdir(parents=True, exist_ok=True)
        SignalManager.get_instance().animation_created.emit(
            project_name, asset_name, animation_name
        )
        return str(target_dir)

    def delete_project(self, project_name: str, delete_files: bool = False):
        """delete_project method."""
        if project_name in self.registry.projects:
            if delete_files:
                path = self.registry.get_project_path(project_name)
                try:
                    if path.exists():
                        shutil.rmtree(path)
                except OSError as e:
                    raise Exception(f"Error: {e}") from e
            self.registry.remove_project(project_name)
            SignalManager.get_instance().project_deleted.emit(project_name)

    def delete_asset(self, project_name: str, asset_name: str):
        """delete_asset method."""
        path = self.registry.get_project_path(project_name) / asset_name
        try:
            if path.exists():
                shutil.rmtree(path)
        except OSError as e:
            raise Exception(f"Error: {e}") from e

        meta = self.metadata.get_metadata(project_name)
        if "virtual_folders" in meta and asset_name in meta["virtual_folders"]:
            del meta["virtual_folders"][asset_name]
            self.metadata.save_metadata(project_name, meta)

        SignalManager.get_instance().asset_deleted.emit(project_name, asset_name)

    def rename_asset(self, project_name: str, old_name: str, new_name: str) -> bool:
        """rename_asset method."""
        project_path = self.registry.get_project_path(project_name)
        old_path = project_path / old_name
        new_path = project_path / new_name

        if not old_path.exists() or new_path.exists():
            return False

        try:
            old_path.rename(new_path)
        except OSError:
            return False

        meta = self.metadata.get_metadata(project_name)
        vfs = meta.get("virtual_folders", {})
        if old_name in vfs:
            vfs[new_name] = vfs.pop(old_name)
            self.metadata.save_metadata(project_name, meta)

        return True

    def delete_animation(self, project_name: str, asset_name: str, animation_name: str):
        """delete_animation method."""
        asset_path = self.registry.get_project_path(project_name) / asset_name

        targets = [
            asset_path / Config.DIR_VIDEOS / f"{animation_name}.mp4",
            asset_path / Config.DIR_RAW_OUTPUT / f"{Config.PREFIX_RAW}{animation_name}",
            asset_path
            / Config.DIR_NORMALIZED_OUTPUT
            / f"{Config.PREFIX_NORMALIZED}{animation_name}",
            asset_path
            / Config.DIR_COMPRESSED_OUTPUT
            / f"{Config.PREFIX_COMPRESSED}{animation_name}",
        ]

        try:
            for f_path in targets:
                if f_path.exists():
                    if f_path.is_dir():
                        shutil.rmtree(f_path)
                    else:
                        f_path.unlink()
        except OSError as e:
            raise Exception(f"Error: {e}") from e

        SignalManager.get_instance().animation_deleted.emit(
            project_name, asset_name, animation_name
        )

    def create_animation_from_video(
        self, project_name: str, asset_name: str, animation_name: str, video_path: str
    ) -> str:
        """create_animation_from_video method."""
        if not project_name:
            project_name = "Standalone"
        if not asset_name:
            asset_name = "DefaultAsset"

        asset_path = self.registry.get_project_path(project_name) / asset_name
        videos_dir = asset_path / Config.DIR_VIDEOS
        videos_dir.mkdir(parents=True, exist_ok=True)

        dest_path = videos_dir / f"{animation_name}.mp4"

        if Path(video_path).resolve() == dest_path.resolve():
            return str(dest_path)

        counter = 1
        original_anim_name = animation_name
        while dest_path.exists():
            animation_name = f"{original_anim_name}_{counter}"
            dest_path = videos_dir / f"{animation_name}.mp4"
            counter += 1

        try:
            shutil.copy2(video_path, dest_path)
        except OSError as e:
            raise Exception(f"Error: {e}") from e

        SignalManager.get_instance().animation_created.emit(
            project_name, asset_name, animation_name
        )
        return str(dest_path)

    def create_animation_from_pngs(
        self, project_name: str, asset_name: str, animation_name: str, png_dir_path: str
    ) -> str:
        """create_animation_from_pngs method."""
        if not project_name:
            project_name = "Standalone"
        if not asset_name:
            asset_name = "DefaultAsset"

        asset_path = self.registry.get_project_path(project_name) / asset_name
        png_path = Path(png_dir_path)

        if png_path.name.startswith(Config.PREFIX_NORMALIZED):
            target_dir = (
                asset_path
                / Config.DIR_NORMALIZED_OUTPUT
                / f"{Config.PREFIX_NORMALIZED}{animation_name}"
            )
        else:
            target_dir = (
                asset_path
                / Config.DIR_RAW_OUTPUT
                / f"{Config.PREFIX_RAW}{animation_name}"
            )

        try:
            if target_dir.exists():
                shutil.rmtree(target_dir)
            shutil.copytree(png_path, target_dir)
        except OSError as e:
            raise Exception(f"Error: {e}") from e

        SignalManager.get_instance().animation_created.emit(
            project_name, asset_name, animation_name
        )
        return str(target_dir)

    def import_project(self, archive_path: str, dest_dir: Optional[str] = None) -> str:
        """import_project method."""
        archive = Path(archive_path)
        target_dir = Path(dest_dir) if dest_dir else self.registry.workspace_dir

        project_name = archive.stem
        extract_path = target_dir / project_name

        counter = 1
        while extract_path.exists():
            project_name = f"{archive.stem}_{counter}"
            extract_path = target_dir / project_name
            counter += 1

        shutil.unpack_archive(str(archive), str(extract_path))
        self.registry.add_project(project_name, extract_path)
        SignalManager.get_instance().project_created.emit(project_name)
        return project_name

    def export_item(
        self,
        project_name: str,
        asset_name: str,
        animation_name: str,
        dest_path: str,
        export_type: str,
        compression_level: Optional[int] = None,
        gif_fps: Optional[int] = None,
        progress_callback: Optional[Callable] = None,
    ):
        """export_item method."""
        project_path = self.registry.get_project_path(project_name)
        dest = Path(dest_path)

        try:
            if animation_name and asset_name:
                comp_folder = (
                    project_path
                    / asset_name
                    / Config.DIR_COMPRESSED_OUTPUT
                    / f"{Config.PREFIX_COMPRESSED}{animation_name}"
                )
                norm_folder = (
                    project_path
                    / asset_name
                    / Config.DIR_NORMALIZED_OUTPUT
                    / f"{Config.PREFIX_NORMALIZED}{animation_name}"
                )
                export_name = f"{asset_name}_{animation_name}"

                use_comp = compression_level is not None or (
                    comp_folder.exists() and any(comp_folder.iterdir())
                )
                src_folder = comp_folder if use_comp else norm_folder

                if compression_level is not None:
                    # Apply on the fly compression
                    tmpdir = tempfile.mkdtemp()
                    fake_asset = Path(tmpdir) / asset_name
                    fake_norm = (
                        fake_asset
                        / Config.DIR_NORMALIZED_OUTPUT
                        / f"{Config.PREFIX_NORMALIZED}{animation_name}"
                    )
                    fake_norm.mkdir(parents=True)
                    for f in norm_folder.iterdir():
                        if f.is_file():
                            shutil.copy2(f, fake_norm / f.name)
                    compress_asset(
                        asset_dir=str(fake_asset),
                        colors=compression_level,
                        overwrite=True,
                    )
                    src_folder = (
                        fake_asset
                        / Config.DIR_COMPRESSED_OUTPUT
                        / f"{Config.PREFIX_COMPRESSED}{animation_name}"
                    )
                    if not src_folder.exists() or not any(src_folder.iterdir()):
                        raise Exception("Compression failed during export.")

                if not src_folder.exists() or not any(src_folder.iterdir()):
                    raise Exception(
                        f"No frames found for animation '{animation_name}'."
                    )

                if export_type == "GIF":
                    final_dest = dest / f"{export_name}.gif"
                    success = export_gif(
                        str(src_folder), str(final_dest), fps=gif_fps or 30, progress_callback=progress_callback
                    )
                    if not success:
                        raise Exception("GIF export failed.")
                elif export_type == "ZIP Archive":
                    shutil.make_archive(str(dest / export_name), "zip", src_folder)
                else:
                    final_dest = dest / export_name
                    if final_dest.exists():
                        shutil.rmtree(final_dest)
                    shutil.copytree(src_folder, final_dest)

            elif asset_name:
                export_name = asset_name
                norm_output_dir = (
                    project_path / asset_name / Config.DIR_NORMALIZED_OUTPUT
                )

                if not norm_output_dir.exists() or not any(norm_output_dir.iterdir()):
                    raise Exception(
                        f"No normalized animations found in Asset '{asset_name}'."
                    )

                def get_asset_source(anim):
                    comp = (
                        project_path
                        / asset_name
                        / Config.DIR_COMPRESSED_OUTPUT
                        / f"{Config.PREFIX_COMPRESSED}{anim}"
                    )
                    if comp.exists() and any(comp.iterdir()):
                        return comp, True
                    return norm_output_dir / f"{Config.PREFIX_NORMALIZED}{anim}", False

                if export_type == "ZIP Archive":
                    with tempfile.TemporaryDirectory() as tmpdir:
                        asset_tmp_dir = Path(tmpdir) / asset_name
                        asset_tmp_dir.mkdir()
                        for d in norm_output_dir.iterdir():
                            if d.name.startswith(Config.PREFIX_NORMALIZED):
                                anim = d.name[len(Config.PREFIX_NORMALIZED) :]
                                src, _ = get_asset_source(anim)
                                shutil.copytree(
                                    src,
                                    asset_tmp_dir / anim,
                                )
                        shutil.make_archive(str(dest / export_name), "zip", tmpdir)
                else:
                    final_dest = dest / export_name
                    final_dest.mkdir(parents=True, exist_ok=True)
                    for d in norm_output_dir.iterdir():
                        if d.name.startswith(Config.PREFIX_NORMALIZED):
                            dest_anim_dir = (
                                final_dest / d.name[len(Config.PREFIX_NORMALIZED) :]
                            )
                            if dest_anim_dir.exists():
                                shutil.rmtree(dest_anim_dir)
                            shutil.copytree(d, dest_anim_dir)

            else:
                export_name = project_name
                if export_type == "ZIP Archive":
                    shutil.make_archive(str(dest / export_name), "zip", project_path)
                else:
                    final_dest = dest / export_name
                    if final_dest.exists():
                        shutil.rmtree(final_dest)
                    shutil.copytree(project_path, final_dest)
        except OSError as e:
            raise Exception(f"Error: {e}") from e

    def get_animation_status(
        self, project_name: str, asset_name: str, animation_name: str
    ) -> str:
        """get_animation_status method."""
        asset_path = self.registry.get_project_path(project_name) / asset_name

        norm_dir = (
            asset_path
            / Config.DIR_NORMALIZED_OUTPUT
            / f"{Config.PREFIX_NORMALIZED}{animation_name}"
        )
        raw_dir = (
            asset_path / Config.DIR_RAW_OUTPUT / f"{Config.PREFIX_RAW}{animation_name}"
        )
        video_file = asset_path / Config.DIR_VIDEOS / f"{animation_name}.mp4"

        if norm_dir.exists() and norm_dir.is_dir() and any(norm_dir.iterdir()):
            return "Normalized"
        if raw_dir.exists() and raw_dir.is_dir() and any(raw_dir.iterdir()):
            return "Raw"
        if video_file.exists():
            return "Video Only"
        return "Unknown"
