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

def test_export_item_zip_compression(fs, mock_signals, mocker, tmp_path):
    """Test exporting as a ZIP file uses correct pathing (compression level is ignored for zip)."""
    fs.create_project("TestProject")
    fs.create_asset("TestProject", "Hero")
    
    # Create mock normalized output so the directory is not empty
    norm_dir = fs.registry.get_project_path("TestProject") / "Hero" / "normalized_output" / "normalized_idle"
    norm_dir.mkdir(parents=True, exist_ok=True)
    (norm_dir / "000.png").touch()
    
    dest_path = tmp_path / "export.zip"
    
    mock_make_archive = mocker.patch("shutil.make_archive")
    
    # Export entire asset
    fs.export_item("TestProject", "Hero", None, str(dest_path), "ZIP Archive", compression_level=9)
    
    mock_make_archive.assert_called_once()
    args, kwargs = mock_make_archive.call_args
    assert str(dest_path).replace(".zip", "") in args[0]
    assert args[1] == "zip"

def test_export_item_gif_fps(fs, mock_signals, mocker, tmp_path):
    """Test GIF export with specific FPS calculations."""
    fs.create_project("TestProject")
    fs.create_asset("TestProject", "Hero")
    
    dest_path = tmp_path / "export.gif"
    
    # Create mock normalized frames
    norm_dir = fs.registry.get_project_path("TestProject") / "Hero" / "normalized_output" / "normalized_idle"
    norm_dir.mkdir(parents=True, exist_ok=True)
    
    import numpy as np
    import cv2
    img = np.zeros((10, 10, 4), dtype=np.uint8)
    cv2.imwrite(str(norm_dir / "000.png"), img)
    cv2.imwrite(str(norm_dir / "001.png"), img)
    
    mock_pil_image = mocker.patch("PIL.Image.Image.save")
    
    fs.export_item("TestProject", "Hero", "idle", str(dest_path), "GIF", gif_fps=12)
    
    mock_pil_image.assert_called_once()
    args, kwargs = mock_pil_image.call_args
    
    # 1000 ms / 12 FPS = 83 ms duration
    assert kwargs.get("duration") == int(1000 / 12)
    assert kwargs.get("save_all") is True
