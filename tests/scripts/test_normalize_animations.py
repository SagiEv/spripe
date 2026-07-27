"""
Tests for spripe.scripts.normalize_animations.
"""

import os
import cv2
import numpy as np
import pytest
from pathlib import Path

from spripe.scripts.normalize_animations import get_bounding_box, normalize_asset


def test_get_bounding_box_empty():
    """Test bounding box on an empty or invalid image."""
    assert get_bounding_box(None) == (0, 0, 0, 0)

    # 3-channel image (missing alpha)
    img = np.zeros((10, 10, 3), dtype=np.uint8)
    assert get_bounding_box(img) == (0, 0, 0, 0)

    # Fully transparent image
    img = np.zeros((10, 10, 4), dtype=np.uint8)
    assert get_bounding_box(img) == (0, 0, 0, 0)


def test_get_bounding_box_valid():
    """Test bounding box on a valid BGRA image."""
    img = np.zeros((100, 100, 4), dtype=np.uint8)
    # Draw a 20x30 rectangle at (10, 20) with full alpha
    img[20:50, 10:30, 3] = 255

    x, y, w, h = get_bounding_box(img)
    assert x == 10
    assert y == 20
    assert w == 20
    assert h == 30


def test_normalize_asset_end_to_end(tmp_path):
    """Test the full normalization logic using a simulated raw output directory."""
    asset_dir = tmp_path / "MyAsset"
    raw_dir = asset_dir / "raw_output" / "out_python_idle"
    raw_dir.mkdir(parents=True)

    # Create a 200x200 simulated input frame
    img = np.zeros((200, 200, 4), dtype=np.uint8)
    # Character is a 50x100 rectangle
    img[50:150, 75:125, :] = [255, 0, 0, 255]  # Blue character, fully opaque

    cv2.imwrite(str(raw_dir / "0000.png"), img)
    cv2.imwrite(str(raw_dir / "0001.png"), img)

    # Run normalization
    # Target character height is 800, canvas is 1920x1080
    normalize_asset(
        asset_dir=str(asset_dir),
        width=1920,
        height=1080,
        char_height=800,
        bottom_padding=100,
    )

    norm_dir = asset_dir / "normalized_output" / "normalized_python_idle"
    assert norm_dir.exists()

    out_files = list(norm_dir.glob("*.png"))
    assert len(out_files) == 2

    # Verify the output image dimensions and character scaling
    out_img = cv2.imread(str(out_files[0]), cv2.IMREAD_UNCHANGED)
    assert out_img is not None
    assert out_img.shape == (1080, 1920, 4)

    # Original char height was 100. Target is 800. Scale factor should be 8.
    # Therefore, new char height is 800, width is 50 * 8 = 400.
    x, y, w, h = get_bounding_box(out_img)
    # Anti-aliasing from INTER_CUBIC interpolation causes the bounding box to expand slightly
    # beyond the exact mathematical bounds (800x400) because edge pixels get partial alpha.
    assert 800 <= h <= 830
    assert 400 <= w <= 430

    # Check bottom alignment (1080 - 100 padding = 980)
    # y + h should equal 980 approximately (due to anti-aliasing expanding h and lowering y)
    assert 970 <= y + h <= 995

    # Check horizontal centering (1920 / 2 = 960)
    # Character center should be at 960.
    center_x = x + (w / 2)
    assert 950 <= center_x <= 970
