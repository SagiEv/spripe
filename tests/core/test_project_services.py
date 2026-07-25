"""
Tests for spripe.core.project_services.
"""

import os
import pytest
from pathlib import Path
from spripe.core.project_services import (
    WorkspaceRegistry,
    ProjectMetadataService,
    FileSystemService,
)


@pytest.fixture
def mock_signals(mocker):
    """Mock the SignalManager to avoid PyQt6 QApplication requirement."""
    return mocker.patch("spripe.core.project_services.SignalManager")


@pytest.fixture
def workspace(tmp_path):
    """Fixture providing a temporary workspace directory."""
    return str(tmp_path)


@pytest.fixture
def registry(workspace, mock_signals):
    """Fixture for WorkspaceRegistry."""
    return WorkspaceRegistry(workspace)


@pytest.fixture
def metadata(registry):
    """Fixture for ProjectMetadataService."""
    return ProjectMetadataService(registry)


@pytest.fixture
def fs(registry, metadata):
    """Fixture for FileSystemService."""
    return FileSystemService(registry, metadata)


def test_workspace_registry_creation(workspace, registry):
    """Test registry initialization and workspace setup."""
    assert str(registry.workspace_dir) == workspace
    registry.save_registry()
    assert registry.registry_file.exists()
    assert registry.get_projects() == ["Standalone"]


def test_add_and_remove_project(workspace, registry):
    """Test adding and removing projects from the registry."""
    dummy_path = Path(workspace) / "dummy"
    registry.add_project("MyProject", dummy_path)

    assert "MyProject" in registry.get_projects()
    assert registry.get_project_path("MyProject") == dummy_path

    registry.remove_project("MyProject")
    assert "MyProject" not in registry.get_projects()


def test_create_project(fs, workspace, mock_signals):
    """Test project directory creation."""
    project_path = fs.create_project("TestProject")
    assert os.path.exists(project_path)
    assert Path(project_path) == Path(workspace) / "TestProject"

    # Assert signal was emitted
    mock_signals.get_instance().project_created.emit.assert_called_with("TestProject")


def test_create_asset(fs, metadata, mock_signals):
    """Test asset creation."""
    fs.create_project("TestProject")
    fs.create_asset("TestProject", "Hero")

    # Check directory structure
    asset_path = fs.registry.get_project_path("TestProject") / "Hero"
    assert asset_path.exists()
    assert (asset_path / "videos").exists()


def test_metadata_corrupted_json(metadata, registry, tmp_path):
    """Test handling of corrupted metadata JSON."""
    registry.add_project("TestProject", tmp_path)
    meta_path = tmp_path / "metadata.json"

    with open(meta_path, "w", encoding="utf-8") as f:
        f.write("{invalid: data")

    # Should fall back gracefully
    meta = metadata.get_metadata("TestProject")
    assert meta == {"virtual_folders": {}}
