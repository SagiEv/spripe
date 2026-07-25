"""
Tests for Prompt Generation Pipeline.
"""

import pytest
from spripe.core.generation.generator import BaseGenerator
from spripe.core.generation.gemini_generator import GeminiGenerator

def test_base_generator_interface():
    """Verify that BaseGenerator enforces abstract methods."""
    class IncompleteGenerator(BaseGenerator):
        pass

    with pytest.raises(TypeError):
        # Cannot instantiate abstract class with abstract methods
        gen = IncompleteGenerator()  # type: ignore

    class CompleteGenerator(BaseGenerator):
        def generate_image(self, prompt, init_image=None, **kwargs):
            return {}
        def generate_video(self, prompt, init_image=None, **kwargs):
            return {}
        def get_provider_name(self):
            return "Test"

    gen = CompleteGenerator()
    assert gen.get_provider_name() == "Test"

def test_gemini_generator_no_api_key():
    """Verify GeminiGenerator raises error when API key is missing."""
    gen = GeminiGenerator(api_key="")
    
    with pytest.raises(ValueError, match="API Key is missing"):
        gen.generate_image("A test prompt")

    with pytest.raises(ValueError, match="API Key is missing"):
        gen.generate_video("A test prompt")

def test_gemini_generator_mock_success():
    """Verify GeminiGenerator returns success structure with API key."""
    gen = GeminiGenerator(api_key="mock_key")
    
    img_res = gen.generate_image("A test prompt")
    assert img_res["status"] == "success"
    assert img_res["mock_output"] is True
    
    vid_res = gen.generate_video("A test prompt")
    assert vid_res["status"] == "success"
    assert vid_res["mock_output"] is True

def test_gemini_generator_provider_name():
    """Verify GeminiGenerator provider name."""
    gen = GeminiGenerator(api_key="mock")
    assert gen.get_provider_name() == "Gemini API"
