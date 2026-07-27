"""
Module for background extraction of PNG sequences from videos.
"""

from PyQt6.QtCore import QThread, pyqtSignal
import os

from spripe.scripts.process_python import process_video
from spripe.core.config import Config


class SequenceExtractionWorker(QThread):
    """SequenceExtractionWorker class."""

    progress_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()
    error_signal = pyqtSignal(str)

    def __init__(self, project_path, asset_name, anim_names, fps, use_ai):
        """__init__ method."""
        super().__init__()
        self.project_path = project_path
        self.asset_name = asset_name
        self.anim_names = anim_names
        self.fps = fps
        self.use_ai = use_ai

    def run(self):
        """run method."""
        try:
            asset_path = os.path.join(self.project_path, self.asset_name)
            videos_dir = os.path.join(asset_path, Config.DIR_VIDEOS)

            for anim in self.anim_names:
                video_file = os.path.join(videos_dir, f"{anim}.mp4")
                if not os.path.exists(video_file):
                    self.progress_signal.emit(f"Skipping {anim}, video not found.")
                    continue

                self.progress_signal.emit(f"Extracting {anim} (AI={self.use_ai})...")

                # Define a callback to emit progress logs from the script
                def progress_cb(msg, current_anim=anim):
                    self.progress_signal.emit(f"[{current_anim}] {msg}")

                process_video(video_file, fps=self.fps, use_ai=self.use_ai, progress_callback=progress_cb)

            self.finished_signal.emit()
        except Exception as e:
            self.error_signal.emit(str(e))
