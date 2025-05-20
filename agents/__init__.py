"""
Core agent framework package for the autonomous AI development team.
"""

from .base_agent import BaseAgent
from agents.specialized.product_manager import ProductManagerAgent

__all__ = ["BaseAgent", "ProductManagerAgent"]
