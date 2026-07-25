import json
import os

SETTINGS_FILE = "settings.json"

class SettingsManager:
    def __init__(self, base_dir):
        self.settings_path = os.path.join(base_dir, SETTINGS_FILE)
        self.settings = {
            "workspace_dir": os.path.join(base_dir, "workspace"),
            "export_dir": "",
            "theme": "dark"
        }
        self.load_error = None
        try:
            self.load()
        except RuntimeError as e:
            self.load_error = str(e)

    def load(self):
        if os.path.exists(self.settings_path):
            try:
                with open(self.settings_path, 'r') as f:
                    data = json.load(f)
                    self.settings.update(data)
            except (json.JSONDecodeError, OSError) as e:
                raise RuntimeError(f"Error loading settings: {e}")

    def save(self):
        try:
            with open(self.settings_path, 'w') as f:
                json.dump(self.settings, f, indent=4)
        except (json.JSONDecodeError, OSError) as e:
            raise RuntimeError(f"Error saving settings: {e}")

    def get(self, key, default=None):
        return self.settings.get(key, default)

    def set(self, key, value):
        self.settings[key] = value
        self.save()
        from spripe.core.signal_manager import SignalManager
        SignalManager.get_instance().settings_changed.emit(key, value)
