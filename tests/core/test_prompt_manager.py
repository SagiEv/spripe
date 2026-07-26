"""
Tests for PromptManager and structured JSON handling.
"""

import os
import json
import pytest
from spripe.core.generation.prompt_manager import PromptManager, DEFAULT_TEMPLATES

def test_prompt_manager_initialization(tmp_path):
    """Verify that PromptManager creates defaults if prompts.json is missing."""
    pm = PromptManager(str(tmp_path))
    assert os.path.exists(pm.prompts_file)

    with open(pm.prompts_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert data == DEFAULT_TEMPLATES

def test_prompt_manager_migration(tmp_path):
    """Verify old string-based prompts are migrated to dictionaries."""
    prompts_file = tmp_path / "prompts.json"
    old_data = {
        "old_key": "Just a string",
        "new_key": {"type": "None", "text": "Already dict"}
    }
    with open(prompts_file, "w", encoding="utf-8") as f:
        json.dump(old_data, f)

    pm = PromptManager(str(tmp_path))

    assert isinstance(pm.templates["old_key"], dict)
    assert pm.templates["old_key"]["type"] == "None"
    assert pm.templates["old_key"]["text"] == "Just a string"
    assert pm.templates["new_key"]["text"] == "Already dict"

def test_prompt_manager_add_and_delete(tmp_path):
    """Verify updating templates saves correctly to disk."""
    pm = PromptManager(str(tmp_path))
    pm.update_template("my_test", "Custom Type", "Custom text")

    assert "my_test" in pm.templates
    assert pm.templates["my_test"]["type"] == "Custom Type"
    assert pm.templates["my_test"]["text"] == "Custom text"

    # Verify disk
    with open(pm.prompts_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert data["my_test"]["type"] == "Custom Type"
        assert data["my_test"]["text"] == "Custom text"

def test_prompt_manager_build_prompt(tmp_path):
    """Test that the build_prompt properly formats the output."""
    pm = PromptManager(str(tmp_path))
    pm.update_template("test_key", "Test Type", "This is the base action.")

    result = pm.build_prompt("test_key", "And this is the user input.")

    assert "### SYSTEM REQUIREMENTS ###" in result
    assert "### STYLE/BASE ACTION ###" in result
    assert "This is the base action." in result
    assert "### USER SPECIFIC INPUT ###" in result
    assert "And this is the user input." in result
