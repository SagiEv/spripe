"""
Module docstring.
"""

from pathlib import Path


class Config:
    """Config class."""

    # Directory names
    DIR_VIDEOS = "videos"
    DIR_RAW_OUTPUT = "raw_output"
    DIR_NORMALIZED_OUTPUT = "normalized_output"
    DIR_COMPRESSED_OUTPUT = "compressed_output"

    # Prefixes
    PREFIX_RAW = "out_"
    PREFIX_NORMALIZED = "normalized_"
    PREFIX_COMPRESSED = "compressed_"

    # Files
    FILE_REGISTRY = "projects.json"
    FILE_PROJECT_META = "project.json"
