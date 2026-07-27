"""
Module docstring.
"""

import os
import traceback
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel, QMessageBox
from PyQt6.QtCore import pyqtSignal, QThread
from typing import Callable, Any, Optional

# Assumes the root directory is in sys.path (handled by main.py)
from spripe.scripts.process_python import process_video
from spripe.scripts.normalize_animations import normalize_asset


class WorkerThread(QThread):
    """A generic QThread worker that runs a target function with kwargs and reports progress."""

    finished_signal = pyqtSignal(bool, str)  # success, output or error message
    progress_signal = pyqtSignal(str)

    def __init__(self, func: Callable, **kwargs: Any):
        """__init__ method."""
        super().__init__()
        self.func = func
        self.kwargs = kwargs

    def run(self):
        """run method."""
        self.kwargs["progress_callback"] = self.progress_signal.emit
        try:
            self.func(**self.kwargs)
            self.finished_signal.emit(True, "Process completed successfully.")
        except Exception as e:
            err = traceback.format_exc()
            self.finished_signal.emit(False, str(err))


class PipelineControls(QWidget):
    """UI widget providing buttons to run background pipeline scripts on selected assets."""

    pipeline_finished = pyqtSignal()  # Emitted when a script finishes to refresh UI

    def __init__(self, base_dir: str, parent: Optional[QWidget] = None):
        """__init__ method."""
        super().__init__(parent)
        self.base_dir: str = base_dir
        self.current_asset: Optional[str] = None
        self.current_asset_path: Optional[str] = None
        self.thread: Optional[WorkerThread] = None

        self.init_ui()

    def init_ui(self):
        """init_ui method."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.status_label = QLabel("Select an asset...")
        layout.addWidget(self.status_label)

        layout.addStretch()

        self.btn_process = QPushButton("Create Transparent BG")
        self.btn_process.clicked.connect(self.run_process)
        self.btn_process.setEnabled(False)
        layout.addWidget(self.btn_process)

        self.btn_normalize = QPushButton("Normalize Animations")
        self.btn_normalize.clicked.connect(self.run_normalize)
        self.btn_normalize.setEnabled(False)
        self.btn_normalize.setToolTip(
            "Normalize scale and position of sprite animations."
        )
        layout.addWidget(self.btn_normalize)

    def set_asset(self, asset_name: str, asset_path: Optional[str] = None) -> None:
        """Sets the active asset target for pipeline operations."""
        self.current_asset = asset_name
        self.current_asset_path = asset_path
        self.status_label.setText(f"Current Target: {asset_name}")
        self.btn_process.setEnabled(True)
        self.btn_normalize.setEnabled(True)

    def run_process(self) -> None:
        """Runs the background removal script on the selected asset."""
        if not self.current_asset or not self.current_asset_path:
            return

        video_path = os.path.join(
            self.current_asset_path, "videos", f"{self.current_asset}.mp4"
        )
        if not os.path.exists(video_path):
            QMessageBox.warning(self, "Warning", f"Video {video_path} not found.")
            return

        self.start_worker(process_video, "Processing video...", video_path=video_path)

    def run_normalize(self) -> None:
        """Runs the animation normalization script on the selected asset."""
        if not self.current_asset_path:
            return
        self.start_worker(
            normalize_asset,
            "Normalizing animations...",
            asset_dir=self.current_asset_path,
            overwrite=True,
        )

    def start_worker(self, func: Callable, status_text: str, **kwargs: Any) -> None:
        """Starts a background worker thread to execute the given pipeline function."""
        if self.thread and self.thread.isRunning():
            QMessageBox.warning(self, "Warning", "A process is already running.")
            return

        self.status_label.setText(status_text)
        self.btn_process.setEnabled(False)
        self.btn_normalize.setEnabled(False)

        self.thread = WorkerThread(func, **kwargs)
        self.thread.progress_signal.connect(self.on_progress)
        self.thread.finished_signal.connect(self.on_finished)
        self.thread.start()

    def on_progress(self, msg):
        """on_progress method."""
        # Update the status label with a short snippet of the output
        snippet = msg[-60:] if len(msg) > 60 else msg
        self.status_label.setText(snippet)

    def on_finished(self, success, output):
        """on_finished method."""
        self.btn_process.setEnabled(True)
        self.btn_normalize.setEnabled(True)

        if success:
            self.status_label.setText(f"Success: {self.current_asset}")
            QMessageBox.information(
                self, "Success", "Pipeline script completed successfully."
            )
            self.pipeline_finished.emit()
        else:
            self.status_label.setText("Error during execution.")
            QMessageBox.critical(self, "Error", f"Script failed:\n{output[-800:]}")
