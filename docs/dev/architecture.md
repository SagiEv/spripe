# Architecture Overview

spripe is built using PyQt6 for the GUI and standard Python libraries for file management and computer vision operations (via OpenCV and numpy).

## High-Level MVC Structure

While not strictly a traditional MVC pattern, spripe separates concerns into:
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

## Testing & Dependencies

Spripe uses a fully isolated unit testing environment via `pytest` to ensure core services remain stable. 

To keep the final executable size small and prevent normal users from downloading unrelated development tools, all testing dependencies are strictly isolated in `pyproject.toml` using an optional dependency group (`[test]`). 

- **End Users:** Running `pip install .` or using the pre-built `.exe` will **only** install `spripe` and its core dependencies (`PyQt6`, `opencv-python`, `numpy`).
- **Developers/CI:** To run the test suite locally or on GitHub Actions, developers must explicitly install the testing group by running:
  ```bash
  pip install -e .[test]
  ```
  This will fetch `pytest`, `pytest-mock`, and `pytest-cov`.
