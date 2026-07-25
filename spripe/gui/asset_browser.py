import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem, QPushButton, 
                             QLabel, QLineEdit, QMenu, QMessageBox)
from PyQt6.QtCore import pyqtSignal, Qt, QPoint
from typing import Optional, List, Any
from spripe.core.project_manager import ProjectManager

class DraggableTreeWidget(QTreeWidget):
    itemMoved = pyqtSignal(object, object) # dragged_item, new_parent_item

    def dropEvent(self, event):
        dragged_item = self.currentItem()
        super().dropEvent(event)
        if dragged_item:
            self.itemMoved.emit(dragged_item, dragged_item.parent())

class AssetBrowser(QWidget):
    """A tree widget displaying the workspace projects, virtual folders, assets, and animations."""
    item_selected = pyqtSignal(str, str, str, str, str) # item_type, project, asset, anim, full_path
    
    # Context Menu Signals
    # Projects
    action_new_asset = pyqtSignal(str) # project_name
    action_import_asset = pyqtSignal(str) # project_name
    action_export_project = pyqtSignal(str) # project_name
    action_remove_project = pyqtSignal(str) # project_name
    action_create_folder = pyqtSignal(str) # project_name
    
    # Assets
    action_move_to_folder = pyqtSignal(str, str) # project, asset
    action_new_animation = pyqtSignal(str, str) # project, asset
    action_import_animation_video = pyqtSignal(str, str) # project, asset
    action_import_animation_png = pyqtSignal(str, str) # project, asset
    action_export_asset = pyqtSignal(str, str) # project, asset
    action_remove_asset = pyqtSignal(str, str) # project, asset
    
    # Animations
    action_export_animation = pyqtSignal(str, str, str) # project, asset, anim
    action_renormalize_animation = pyqtSignal(str, str, str) # project, asset, anim
    action_remove_animation = pyqtSignal(str, str, str) # project, asset, anim
    
    # Empty Space
    action_new_project = pyqtSignal()
    action_import_project = pyqtSignal()
    
    def __init__(self, project_manager: ProjectManager, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.project_manager: ProjectManager = project_manager
        self.init_ui()
        self.refresh_assets()
        
        from spripe.core.signal_manager import SignalManager
        sm = SignalManager.get_instance()
        sm.workspace_changed.connect(lambda _: self.refresh_assets())
        sm.project_created.connect(lambda _: self.refresh_assets())
        sm.project_deleted.connect(lambda _: self.refresh_assets())
        sm.asset_created.connect(lambda _, __: self.refresh_assets())
        sm.asset_deleted.connect(lambda _, __: self.refresh_assets())
        sm.animation_created.connect(lambda _, __, ___: self.refresh_assets())
        sm.animation_deleted.connect(lambda _, __, ___: self.refresh_assets())
        sm.metadata_updated.connect(lambda _: self.refresh_assets())
        
    def init_ui(self) -> None:
        """Initializes the browser UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        header = QLabel("Workspace Browser")
        header.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 5px;")
        layout.addWidget(header)
        
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search...")
        self.search_bar.textChanged.connect(self.filter_tree)
        layout.addWidget(self.search_bar)
        
        self.tree_widget = DraggableTreeWidget()
        self.tree_widget.setHeaderHidden(True)
        self.tree_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_widget.customContextMenuRequested.connect(self.show_context_menu)
        self.tree_widget.itemSelectionChanged.connect(self.on_selection_changed)
        
        self.tree_widget.setDragEnabled(True)
        self.tree_widget.setAcceptDrops(True)
        self.tree_widget.setDropIndicatorShown(True)
        self.tree_widget.setDragDropMode(QTreeWidget.DragDropMode.InternalMove)
        self.tree_widget.itemMoved.connect(self.on_item_moved)
        
        layout.addWidget(self.tree_widget)
        
    def filter_tree(self, text: str) -> None:
        """Filters the tree items based on the search query."""
        search_text = text.lower()
        
        def match_item(item):
            # Check if this item matches
            matches = search_text in item.text(0).lower()
            
            # Check if any children match (recursive)
            child_matches = False
            for i in range(item.childCount()):
                if match_item(item.child(i)):
                    child_matches = True
                    
            # If the item or any of its children match, show it
            should_show = matches or child_matches or not search_text
            item.setHidden(not should_show)
            
            # If a child matches but the parent doesn't, we want the parent expanded to see the child
            if child_matches and search_text:
                item.setExpanded(True)
                
            return should_show
            
        for i in range(self.tree_widget.topLevelItemCount()):
            match_item(self.tree_widget.topLevelItem(i))

    def refresh_assets(self):
        self.tree_widget.clear()
        
        projects = self.project_manager.get_projects()
        
        for proj in sorted(projects):
            proj_item = QTreeWidgetItem(self.tree_widget, [proj])
            proj_item.setData(0, Qt.ItemDataRole.UserRole, ("project", proj, None, None, self.project_manager.get_project_path(proj)))
            
            metadata = self.project_manager.get_project_metadata(proj)
            virtual_folders_map = metadata.get("virtual_folders", {})
            explicit_folders = metadata.get("folders", [])
            
            assets = self.project_manager.get_assets(proj)
            folder_items = {}
            
            for folder_name in explicit_folders:
                folder_item = QTreeWidgetItem(proj_item, [folder_name])
                folder_item.setData(0, Qt.ItemDataRole.UserRole, ("folder", proj, folder_name, None, None))
                folder_items[folder_name] = folder_item

            for asset in sorted(assets):
                folder_name = virtual_folders_map.get(asset)
                if folder_name and folder_name not in folder_items:
                    folder_item = QTreeWidgetItem(proj_item, [folder_name])
                    folder_item.setData(0, Qt.ItemDataRole.UserRole, ("folder", proj, folder_name, None, None))
                    folder_items[folder_name] = folder_item

            for asset in sorted(assets):
                folder_name = virtual_folders_map.get(asset)
                parent_item = folder_items.get(folder_name) if folder_name else proj_item
                
                asset_item = QTreeWidgetItem(parent_item, [asset])
                asset_item.setData(0, Qt.ItemDataRole.UserRole, ("asset", proj, asset, None, os.path.join(self.project_manager.get_project_path(proj), asset)))
                
                animations = self.project_manager.get_animations(proj, asset)
                for anim in sorted(animations):
                    anim_item = QTreeWidgetItem(asset_item, [anim])
                    # We pass the asset path to the animation so the timeline loader can resolve it
                    anim_item.setData(0, Qt.ItemDataRole.UserRole, ("animation", proj, asset, anim, os.path.join(self.project_manager.get_project_path(proj), asset)))
                    
        self.tree_widget.expandAll()
        # Re-apply filter if text exists
        if self.search_bar.text():
            self.filter_tree(self.search_bar.text())
            
    def on_selection_changed(self):
        selected = self.tree_widget.selectedItems()
        if selected:
            data = selected[0].data(0, Qt.ItemDataRole.UserRole)
            if data:
                item_type, proj, asset, anim, full_path = data
                self.item_selected.emit(item_type, proj or "", asset or "", anim or "", full_path or "")

    def on_item_moved(self, dragged_item, new_parent_item):
        if not dragged_item: return
        data = dragged_item.data(0, Qt.ItemDataRole.UserRole)
        if not data or data[0] != "asset": return
        
        _, proj, asset, _, _ = data
        
        metadata = self.project_manager.get_project_metadata(proj)
        if "virtual_folders" not in metadata:
            metadata["virtual_folders"] = {}
            
        if new_parent_item:
            parent_data = new_parent_item.data(0, Qt.ItemDataRole.UserRole)
            if parent_data:
                parent_type = parent_data[0]
                if parent_type == "folder":
                    folder_name = parent_data[2]
                    metadata["virtual_folders"][asset] = folder_name
                elif parent_type == "project":
                    if asset in metadata["virtual_folders"]:
                        del metadata["virtual_folders"][asset]
        
        self.project_manager.save_project_metadata(proj, metadata)
        self.refresh_assets()

    def show_context_menu(self, position: QPoint):
        item = self.tree_widget.itemAt(position)
        menu = QMenu()
        
        if not item:
            action_new_proj = menu.addAction("New Project")
            action_import_proj = menu.addAction("Import Project")
            
            action = menu.exec(self.tree_widget.viewport().mapToGlobal(position))
            if action == action_new_proj:
                self.action_new_project.emit()
            elif action == action_import_proj:
                self.action_import_project.emit()
            return
            
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data: return
        item_type, proj, asset, anim, _ = data
        
        if item_type == "project":
            act_create_folder = menu.addAction("Create Folder")
            act_new_asset = menu.addAction("New Asset")
            act_import_asset = menu.addAction("Import Asset")
            menu.addSeparator()
            act_export_proj = menu.addAction("Export Project")
            menu.addSeparator()
            act_remove_proj = menu.addAction("Remove Project")
            
            action = menu.exec(self.tree_widget.viewport().mapToGlobal(position))
            if action == act_create_folder: self.action_create_folder.emit(proj)
            elif action == act_new_asset: self.action_new_asset.emit(proj)
            elif action == act_import_asset: self.action_import_asset.emit(proj)
            elif action == act_export_proj: self.action_export_project.emit(proj)
            elif action == act_remove_proj: self.action_remove_project.emit(proj)
            
        elif item_type == "folder":
            act_remove_folder = menu.addAction("Remove Folder")
            action = menu.exec(self.tree_widget.viewport().mapToGlobal(position))
            if action == act_remove_folder:
                # We can just remove it from metadata, or just ignore for now since it's a virtual folder
                QMessageBox.information(self, "Note", "To remove a folder, move all assets out of it.")
            
        elif item_type == "asset":
            act_move_folder = menu.addAction("Move to Virtual Folder")
            act_new_anim = menu.addAction("New Animation")
            act_import_anim_v = menu.addAction("Import Animation (Video)")
            act_import_anim_p = menu.addAction("Import Animation (PNGs)")
            menu.addSeparator()
            act_export_asset = menu.addAction("Export Asset")
            menu.addSeparator()
            act_remove_asset = menu.addAction("Remove Asset")
            
            action = menu.exec(self.tree_widget.viewport().mapToGlobal(position))
            if action == act_move_folder: self.action_move_to_folder.emit(proj, asset)
            elif action == act_new_anim: self.action_new_animation.emit(proj, asset)
            elif action == act_import_anim_v: self.action_import_animation_video.emit(proj, asset)
            elif action == act_import_anim_p: self.action_import_animation_png.emit(proj, asset)
            elif action == act_export_asset: self.action_export_asset.emit(proj, asset)
            elif action == act_remove_asset: self.action_remove_asset.emit(proj, asset)
            
        elif item_type == "animation":
            act_renormalize_anim = menu.addAction("Renormalize Animation")
            menu.addSeparator()
            act_export_anim = menu.addAction("Export Animation")
            menu.addSeparator()
            act_remove_anim = menu.addAction("Remove Animation")
            
            action = menu.exec(self.tree_widget.viewport().mapToGlobal(position))
            if action == act_renormalize_anim: self.action_renormalize_animation.emit(proj, asset, anim)
            elif action == act_export_anim: self.action_export_animation.emit(proj, asset, anim)
            elif action == act_remove_anim: self.action_remove_animation.emit(proj, asset, anim)
