"""Module docstring."""
from PyQt6.QtCore import QThread, pyqtSignal
from typing import Dict, Any

class GenerationWorker(QThread):
    """Asynchronous worker for LLM Generation to prevent UI freezing."""

    finished_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)

    def __init__(self, generator, generation_type: str, prompt: str, init_image: str = None):
        """Method docstring."""
        super().__init__()
        self.generator = generator
        self.generation_type = generation_type
        self.prompt = prompt
        self.init_image = init_image

    def run(self):
        """Method docstring."""
        try:
            if self.generation_type == "video":
                result = self.generator.generate_video(self.prompt, self.init_image)
            else:
                result = self.generator.generate_image(self.prompt, self.init_image)

            self.finished_signal.emit(result)
        except ValueError as ve:
            self.error_signal.emit(str(ve))
        except Exception as e:
            self.error_signal.emit(f"An unexpected error occurred: {str(e)}")
