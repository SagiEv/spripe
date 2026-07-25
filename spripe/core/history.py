"""
Command and History pattern implementation for Undo/Redo support.
"""

from dataclasses import dataclass
from PyQt6.QtCore import QObject, pyqtSignal
from spripe.core.signal_manager import SignalManager
from spripe.core.settings_manager import SettingsManager


@dataclass
class CommandContext:
    """Context identifying where a command was executed."""
    project_name: str
    asset_name: str
    animation_name: str


class Command:
    """
    Abstract base class for all undoable commands.
    """

    def __init__(self, description: str, context: CommandContext):
        self.description = description
        self.context = context

    def execute(self):
        """Executes the command for the first time."""
        raise NotImplementedError

    def undo(self):
        """Reverts the command."""
        raise NotImplementedError

    def redo(self):
        """Reapplies the command."""
        raise NotImplementedError


class HistoryManager(QObject):
    """
    Manages the global undo/redo stacks.
    """

    history_changed = pyqtSignal()
    context_switch_requested = pyqtSignal(CommandContext)

    def __init__(self, settings_manager: SettingsManager):
        super().__init__()
        self.settings_manager = settings_manager
        self._undo_stack = []
        self._redo_stack = []
        self._limit = self.settings_manager.get("undo_limit", 10)

        SignalManager.get_instance().settings_changed.connect(self._on_settings_changed)

    def _on_settings_changed(self, key, value):
        if key == "undo_limit":
            self._limit = value
            self._enforce_limit()

    def _enforce_limit(self):
        changed = False
        while len(self._undo_stack) > self._limit:
            self._undo_stack.pop(0)
            changed = True
        if changed:
            self.history_changed.emit()

    def push(self, command: Command):
        """Executes a command and adds it to the undo stack."""
        command.execute()
        self._undo_stack.append(command)
        self._redo_stack.clear()
        self._enforce_limit()
        self.history_changed.emit()

    def undo(self, current_context: CommandContext = None):
        """Undoes the last command in the stack."""
        if not self._undo_stack:
            return

        cmd = self._undo_stack.pop()

        # Switch context if the command belongs to a different context
        if current_context and cmd.context:
            if (
                cmd.context.project_name != current_context.project_name
                or cmd.context.asset_name != current_context.asset_name
                or cmd.context.animation_name != current_context.animation_name
            ):
                self.context_switch_requested.emit(cmd.context)

        cmd.undo()
        self._redo_stack.append(cmd)
        self.history_changed.emit()

    def redo(self, current_context: CommandContext = None):
        """Redoes the last undone command."""
        if not self._redo_stack:
            return

        cmd = self._redo_stack.pop()

        # Switch context if the command belongs to a different context
        if current_context and cmd.context:
            if (
                cmd.context.project_name != current_context.project_name
                or cmd.context.asset_name != current_context.asset_name
                or cmd.context.animation_name != current_context.animation_name
            ):
                self.context_switch_requested.emit(cmd.context)

        cmd.redo()
        self._undo_stack.append(cmd)
        self.history_changed.emit()

    def can_undo(self) -> bool:
        """Returns True if there are commands to undo."""
        return len(self._undo_stack) > 0

    def can_redo(self) -> bool:
        """Returns True if there are commands to redo."""
        return len(self._redo_stack) > 0

    def undo_text(self) -> str:
        """Returns the text for the Undo action."""
        if self.can_undo():
            return f"Undo {self._undo_stack[-1].description}"
        return "Undo"

    def redo_text(self) -> str:
        """Returns the text for the Redo action."""
        if self.can_redo():
            return f"Redo {self._redo_stack[-1].description}"
        return "Redo"
