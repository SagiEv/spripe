# Architecture Overview

Spripe is built using PyQt6 for the GUI and standard Python libraries for file management and computer vision operations (via OpenCV and numpy).

## High-Level MVC Structure

While not strictly a traditional MVC pattern, Spripe separates concerns into:
- **Models/Services (The Backend):** Housed in the `core/` directory. These services handle reading/writing metadata, manipulating the filesystem, and discovering projects.
- **Controllers:** The `gui/action_controller.py` acts as a bridge for user intent, capturing menu clicks and context actions.
- **Views:** The `gui/` directory contains all visual widgets, such as `timeline_widget.py` and `painter_widget.py`.

## The SignalManager (Event Bus)

To prevent tight coupling between deep UI hierarchies, Spripe utilizes a central Event Bus pattern via the `core.signal_manager.SignalManager` singleton.

Instead of an ActionController directly modifying the checkbox state of a child widget, it updates the `SettingsManager`. The `SettingsManager` then emits a `settings_changed` signal. Any widget that cares about that setting (like the Timeline) listens to the SignalManager and updates itself accordingly.

```python
# Emitting a signal
SignalManager.get_instance().asset_created.emit(project_name, asset_name)

# Listening to a signal
sm = SignalManager.get_instance()
sm.asset_created.connect(lambda proj, asset: self.refresh_view())
```
