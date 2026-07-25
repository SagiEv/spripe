"""Module docstring."""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

class BaseGenerator(ABC):
    """Abstract base class for all LLM generation providers (Local & API)."""

    @abstractmethod
    def generate_image(self, prompt: str, init_image: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Generate an image.
        Returns a dictionary containing the output path and any metadata.
        """

    @abstractmethod
    def generate_video(self, prompt: str, init_image: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Generate a video.
        Returns a dictionary containing the output path and any metadata.
        """

    @abstractmethod
    def get_provider_name(self) -> str:
        """Return the name of the provider."""
