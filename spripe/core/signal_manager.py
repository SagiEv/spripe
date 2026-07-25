from PyQt6.QtCore import QObject, pyqtSignal

class SignalManager(QObject):
    """
    Centralized event bus for the application.
    Allows components to communicate without tight coupling.
    """
    
    # Project related signals
    project_created = pyqtSignal(str) # project_name
    project_deleted = pyqtSignal(str) # project_name
    
    # Asset related signals
    asset_created = pyqtSignal(str, str) # project_name, asset_name
    asset_deleted = pyqtSignal(str, str) # project_name, asset_name
    
    # Animation related signals
    animation_created = pyqtSignal(str, str, str) # project, asset, anim
    animation_deleted = pyqtSignal(str, str, str) # project, asset, anim
    
    # Global state signals
    workspace_changed = pyqtSignal(str) # new_workspace_dir
    metadata_updated = pyqtSignal(str) # project_name
    settings_changed = pyqtSignal(str, object) # key, value    
    # We can use a singleton pattern or just instantiate one and pass it around.
    # Instantiating and passing is usually safer for testing, but singleton is easier for legacy refactors.
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
