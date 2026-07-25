"""
Tests for spripe.core.settings_manager.
"""

import json
import os
import pytest
from spripe.core.settings_manager import SettingsManager


@pytest.fixture
def temp_workspace(tmp_path):
    """Fixture providing a temporary directory for settings."""
    return str(tmp_path)


def test_settings_initialization(temp_workspace):
    """Test that default settings are created if no file exists."""
    sm = SettingsManager(temp_workspace)
    assert sm.get("theme") == "dark"
    assert sm.get("workspace_dir") == os.path.join(temp_workspace, "workspace")
    assert sm.load_error is None


def test_settings_save_and_load(temp_workspace, mocker):
    """Test saving and loading settings."""
    # Mock the PyQt6 signal emission which requires a QApplication context
    mocker.patch("spripe.core.signal_manager.SignalManager")

    sm = SettingsManager(temp_workspace)
    sm.set("theme", "light")
    sm.set("export_dir", "C:/exports")

    # Reload settings in a new instance
    sm2 = SettingsManager(temp_workspace)
    assert sm2.get("theme") == "light"
    assert sm2.get("export_dir") == "C:/exports"


def test_settings_corrupted_json(temp_workspace):
    """Test handling of corrupted JSON file."""
    settings_file = os.path.join(temp_workspace, "settings.json")
    with open(settings_file, "w", encoding="utf-8") as f:
        f.write("{invalid_json: true,")

    sm = SettingsManager(temp_workspace)
    assert sm.load_error is not None
    assert "Error:" in sm.load_error
    # Defaults should still be populated
    assert sm.get("theme") == "dark"


def test_settings_get_default(temp_workspace):
    """Test get() with a default fallback."""
    sm = SettingsManager(temp_workspace)
    assert sm.get("non_existent_key", "fallback") == "fallback"
