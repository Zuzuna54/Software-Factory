"""
LLM Provider Integration Package
"""

from .base import LLMProvider
from .vertex_gemini_provider import VertexGeminiProvider


def get_llm_provider() -> LLMProvider:
    """
    Factory function to get an instance of the default LLM provider.

    Returns:
        An instance of the default LLM provider (VertexGeminiProvider)
    """
    return VertexGeminiProvider()


__all__ = ["LLMProvider", "VertexGeminiProvider", "get_llm_provider"]
