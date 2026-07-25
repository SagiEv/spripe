"""
Module docstring.
"""

from typing import List, Optional

from spripe.core.project_services import (
    WorkspaceRegistry,
    ProjectMetadataService,
    FileSystemService,
)


class ProjectManager:
    """
    Facade for the workspace registry, metadata, and filesystem services.
    Provides backward compatibility while delegating to specialized services.
    """

    def __init__(self, workspace_dir: str):
        """__init__ method."""
        self.workspace_dir = workspace_dir
        self.registry = WorkspaceRegistry(workspace_dir)
        self.metadata = ProjectMetadataService(self.registry)
        self.fs = FileSystemService(self.registry, self.metadata)
        self.load_error = self.registry.load_error

    def set_workspace(self, workspace_dir: str) -> None:
        """set_workspace method."""
        self.workspace_dir = workspace_dir
        self.registry.set_workspace(workspace_dir)

    def load_registry(self) -> None:
        """load_registry method."""
        self.registry.load_registry()

    def save_registry(self) -> None:
        """save_registry method."""
        self.registry.save_registry()

    def get_project_path(self, project_name: str) -> str:
        """get_project_path method."""
        return str(self.registry.get_project_path(project_name))

    def get_projects(self) -> List[str]:
        """get_projects method."""
        return self.registry.get_projects()

    def get_assets(self, project_name: str) -> List[str]:
        """get_assets method."""
        return self.fs.get_assets(project_name)

    def get_animations(self, project_name: str, asset_name: str) -> List[str]:
        """get_animations method."""
        return self.fs.get_animations(project_name, asset_name)

    def create_project(
        self, project_name: str, external_path: Optional[str] = None
    ) -> str:
        """create_project method."""
        return self.fs.create_project(project_name, external_path)

    def create_asset(
        self, project_name: str, asset_name: str, external_path: Optional[str] = None
    ):
        """create_asset method."""
        return self.fs.create_asset(project_name, asset_name, external_path)

    def create_animation(
        self, project_name: str, asset_name: str, animation_name: str
    ) -> str:
        """create_animation method."""
        return self.fs.create_animation(project_name, asset_name, animation_name)

    def delete_project(self, project_name: str, delete_files: bool = False):
        """delete_project method."""
        self.fs.delete_project(project_name, delete_files)

    def delete_asset(self, project_name: str, asset_name: str):
        """delete_asset method."""
        self.fs.delete_asset(project_name, asset_name)

    def rename_asset(self, project_name: str, old_name: str, new_name: str) -> bool:
        """rename_asset method."""
        return self.fs.rename_asset(project_name, old_name, new_name)

    def rename_virtual_folder(
        self, project_name: str, old_name: str, new_name: str
    ) -> bool:
        """rename_virtual_folder method."""
        meta = self.get_project_metadata(project_name)
        folders = meta.get("folders", [])
        if new_name in folders:
            return False

        if old_name in folders:
            folders[folders.index(old_name)] = new_name

        vfs = meta.get("virtual_folders", {})
        for asset, folder in list(vfs.items()):
            if folder == old_name:
                vfs[asset] = new_name

        templates = meta.get("folder_templates", {})
        if old_name in templates:
            templates[new_name] = templates.pop(old_name)

        self.save_project_metadata(project_name, meta)
        return True

    def delete_virtual_folder(
        self, project_name: str, folder_name: str, delete_assets: bool = False
    ):
        """delete_virtual_folder method."""
        meta = self.get_project_metadata(project_name)
        folders = meta.get("folders", [])
        if folder_name in folders:
            folders.remove(folder_name)

        templates = meta.get("folder_templates", {})
        if folder_name in templates:
            del templates[folder_name]

        vfs = meta.get("virtual_folders", {})
        assets_to_delete = []
        for asset, folder in list(vfs.items()):
            if folder == folder_name:
                if delete_assets:
                    assets_to_delete.append(asset)
                del vfs[asset]

        self.save_project_metadata(project_name, meta)

        if delete_assets:
            for asset in assets_to_delete:
                self.delete_asset(project_name, asset)

    def delete_animation(self, project_name: str, asset_name: str, animation_name: str):
        """delete_animation method."""
        self.fs.delete_animation(project_name, asset_name, animation_name)

    def create_animation_from_video(
        self, project_name: str, asset_name: str, animation_name: str, video_path: str
    ) -> str:
        """create_animation_from_video method."""
        return self.fs.create_animation_from_video(
            project_name, asset_name, animation_name, video_path
        )

    def create_animation_from_pngs(
        self, project_name: str, asset_name: str, animation_name: str, png_dir_path: str
    ) -> str:
        """create_animation_from_pngs method."""
        return self.fs.create_animation_from_pngs(
            project_name, asset_name, animation_name, png_dir_path
        )

    def export_item(
        self,
        project_name: str,
        asset_name: str,
        animation_name: str,
        dest_path: str,
        export_type: str,
    ):
        """export_item method."""
        self.fs.export_item(
            project_name, asset_name, animation_name, dest_path, export_type
        )

    def get_project_metadata(self, project_name: str) -> dict:
        """get_project_metadata method."""
        return self.metadata.get_metadata(project_name)

    def save_project_metadata(self, project_name: str, metadata: dict) -> None:
        """save_project_metadata method."""
        self.metadata.save_metadata(project_name, metadata)

    def get_folder_template(self, project_name: str, folder_name: str) -> List[str]:
        """get_folder_template method."""
        return self.metadata.get_folder_template(project_name, folder_name)

    def set_folder_template(
        self, project_name: str, folder_name: str, template: List[str]
    ) -> None:
        """set_folder_template method."""
        self.metadata.set_folder_template(project_name, folder_name, template)

    def get_animation_status(
        self, project_name: str, asset_name: str, animation_name: str
    ) -> str:
        """get_animation_status method."""
        return self.fs.get_animation_status(project_name, asset_name, animation_name)
