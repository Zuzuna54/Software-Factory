from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def generate_completion(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        system_message: Optional[str] = None,
    ) -> str:
        """Generate a text completion for the given prompt."""
        pass

    @abstractmethod
    async def generate_chat_completion(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 1000,
        temperature: float = 0.7,
        system_message: Optional[str] = None,
    ) -> str:
        """Generate a chat completion for the given messages."""
        pass

    @abstractmethod
    async def generate_embeddings(
        self, text: str, task_type: str = "RETRIEVAL_DOCUMENT"
    ) -> List[float]:  # Added task_type default
        """Generate embeddings for the given text."""
        pass

    @abstractmethod
    async def function_calling(
        self,
        messages: List[Dict[str, str]],
        functions: List[Dict[str, Any]],
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        """Call functions based on LLM reasoning."""
        pass
