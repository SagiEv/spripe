"""
Tests for the HistoryManager and Command classes.
"""

import pytest
from PyQt6.QtWidgets import QApplication
from spripe.core.history import Command, CommandContext, HistoryManager
from spripe.core.settings_manager import SettingsManager
from spripe.core.signal_manager import SignalManager

class DummyCommand(Command):
    """A dummy command for testing."""
    def __init__(self, description: str, context: CommandContext):
        super().__init__(description, context)
        self.executed = False
        self.undone = False
        self.redone = False

    def execute(self):
        self.executed = True
        self.undone = False
        self.redone = False

    def undo(self):
        self.undone = True
        self.redone = False

    def redo(self):
        self.redone = True
        self.undone = False

@pytest.fixture
def qapp():
    """Fixture for QApplication instance."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app

@pytest.fixture
def history_manager(qapp, tmp_path, mocker):
    """Fixture for HistoryManager with a fresh SettingsManager."""
    mocker.patch("spripe.core.signal_manager.SignalManager.get_instance")
    sm = SettingsManager(str(tmp_path))
    sm.set("undo_limit", 3)
    return HistoryManager(sm)

def test_command_execution():
    """Verify basic command execution and states."""
    ctx = CommandContext("proj", "asset", "anim")
    cmd = DummyCommand("Test Command", ctx)

    assert not cmd.executed
    cmd.execute()
    assert cmd.executed

    cmd.undo()
    assert cmd.undone

    cmd.redo()
    assert cmd.redone

def test_history_manager_push_and_undo(history_manager):
    """Verify push and undo mechanics."""
    ctx = CommandContext("proj", "asset", "anim")
    cmd = DummyCommand("Test Command", ctx)

    history_manager.push(cmd)

    assert cmd.executed
    assert history_manager.can_undo()
    assert not history_manager.can_redo()
    assert history_manager.undo_text() == "Undo Test Command"

    history_manager.undo()
    assert cmd.undone
    assert not history_manager.can_undo()
    assert history_manager.can_redo()
    assert history_manager.redo_text() == "Redo Test Command"

def test_history_manager_redo_clearing(history_manager):
    """Verify pushing a new command clears the redo stack."""
    ctx = CommandContext("proj", "asset", "anim")
    cmd1 = DummyCommand("Command 1", ctx)
    cmd2 = DummyCommand("Command 2", ctx)

    history_manager.push(cmd1)
    history_manager.undo()
    assert history_manager.can_redo()

    # Pushing cmd2 should clear cmd1 from the redo stack
    history_manager.push(cmd2)
    assert not history_manager.can_redo()

def test_history_manager_limit(history_manager):
    """Verify undo history limit is enforced."""
    ctx = CommandContext("proj", "asset", "anim")

    cmd1 = DummyCommand("Command 1", ctx)
    cmd2 = DummyCommand("Command 2", ctx)
    cmd3 = DummyCommand("Command 3", ctx)
    cmd4 = DummyCommand("Command 4", ctx)

    history_manager.push(cmd1)
    history_manager.push(cmd2)
    history_manager.push(cmd3)
    # pylint: disable=protected-access
    assert len(history_manager._undo_stack) == 3

    history_manager.push(cmd4)
    assert len(history_manager._undo_stack) == 3
    assert history_manager._undo_stack[0] == cmd2
    # pylint: enable=protected-access
