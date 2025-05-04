# agents/__init__.py
# This file makes Python treat the agents directory as a package.

from .base_agent import BaseAgent

# Import other core components or specialized agents as they are created

__all__ = ["BaseAgent"]
