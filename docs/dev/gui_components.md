# GUI Components

Spripe's graphical interface is built with PyQt6. The primary window is constructed in `spripe/gui/main.py`.

## ActionController
Located in `gui/action_controller.py`, this class handles global menu actions (File > New Project) and context menu actions triggered from the browser. It delegates the heavy lifting to the `ProjectManager` and relies on the `SignalManager` to automatically trigger UI updates for child widgets.

## AssetBrowser
A custom `QTreeWidget` that displays the Workspace hierarchy. It listens to `SignalManager` events to automatically reconstruct the tree whenever projects or assets are modified on disk.

## AssetDashboard
A contextual panel that updates based on the currently selected Asset in the browser. It displays the status of animations (whether they are Raw, Normalized, or Missing) and provides buttons to trigger the normalization process.

## TimelineWidget
Displays the sequence of PNG frames for a selected animation. It manages playback, looping logic, frame deletion, and the logic for pinning a keyframe (to be used as an onion skin).

## PainterWidget
A complex custom widget utilizing a `QGraphicsScene` (`CanvasView`). This is where the user draws masks over raw frames. It supports brush tools, lasso selections, magic wand contiguous selection, and integrates with OpenCV's GrabCut algorithm for smart background removal.
