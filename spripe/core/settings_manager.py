"""
Module docstring.
"""

import json
import os

SETTINGS_FILE = "settings.json"


class SettingsManager:
    """SettingsManager class."""

    def __init__(self, base_dir):
        """__init__ method."""
        self.settings_path = os.path.join(base_dir, SETTINGS_FILE)
        self.settings = {
            "workspace_dir": os.path.join(base_dir, "workspace"),
            "export_dir": "",
            "theme": "dark",
            "recent_projects": [],
            "undo_limit": 10,
            "png_sequence_fps": 12,
        }
        self.load_error = None
        try:
            self.load()
        except RuntimeError as e:
            self.load_error = str(e)

    def load(self):
        """load method."""
        if os.path.exists(self.settings_path):
            try:
                with open(self.settings_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.settings.update(data)
            except (json.JSONDecodeError, OSError) as e:
                raise RuntimeError(f"Error: {e}") from e

    def save(self):
        """save method."""
        try:
            with open(self.settings_path, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=4)
        except (json.JSONDecodeError, OSError) as e:
            raise RuntimeError(f"Error: {e}") from e

    def get(self, key, default=None):
        """get method."""
        return self.settings.get(key, default)

    def set(self, key, value):
        """set method."""
        self.settings[key] = value
        self.save()
        from spripe.core.signal_manager import SignalManager

        SignalManager.get_instance().settings_changed.emit(key, value)

    def add_recent_project(self, project_path):
        """add_recent_project method."""
        recent = self.get("recent_projects", [])
        if project_path in recent:
            recent.remove(project_path)
        recent.insert(0, project_path)
        # Keep only last 10
        recent = recent[:10]
        self.set("recent_projects", recent)

    def get_recent_projects(self):
        """get_recent_projects method."""
        return self.get("recent_projects", [])
