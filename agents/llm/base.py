"""
Abstract base class for LLM provider integration.
"""

import abc
from typing import Dict, List, Any, Optional, Union, Callable, Tuple


class LLMProvider(abc.ABC):
    """
    Abstract base class defining the interface for all LLM providers.
    This class standardizes how agent systems interact with various LLM backends.
    """

    @abc.abstractmethod
    async def generate_text(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        stop_sequences: Optional[List[str]] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Generate text completion for a given prompt.

        Args:
            prompt: The text prompt to complete
            max_tokens: Maximum number of tokens to generate
            temperature: Controls randomness (0.0-1.0, lower is more deterministic)
            top_p: Nucleus sampling parameter
            top_k: Top-k sampling parameter
            stop_sequences: List of strings that will stop generation if encountered

        Returns:
            Tuple of (generated_text, metadata)
        """
        pass

    @abc.abstractmethod
    async def generate_chat_completion(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        stop_sequences: Optional[List[str]] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Generate chat completion for a list of messages.

        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
                     Roles should be one of: 'system', 'user', 'assistant'
            max_tokens: Maximum number of tokens to generate
            temperature: Controls randomness (0.0-1.0, lower is more deterministic)
            top_p: Nucleus sampling parameter
            top_k: Top-k sampling parameter
            stop_sequences: List of strings that will stop generation if encountered

        Returns:
            Tuple of (generated_response, metadata)
        """
        pass

    @abc.abstractmethod
    async def generate_embeddings(
        self,
        texts: List[str],
    ) -> Tuple[List[List[float]], Dict[str, Any]]:
        """
        Generate vector embeddings for a list of texts.

        Args:
            texts: List of text strings to create embeddings for

        Returns:
            Tuple of (embeddings_list, metadata)
            where embeddings_list is a list of embedding vectors (one per input text)
        """
        pass

    @abc.abstractmethod
    async def function_calling(
        self,
        messages: List[Dict[str, str]],
        functions: List[Dict[str, Any]],
        function_call: Optional[str] = "auto",
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Generate text that includes function calls based on the input.

        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            functions: List of function definitions, each with name, description, and parameters
            function_call: Control how functions are called, options:
                          - "auto": Model decides whether to call a function
                          - "none": No function calls
                          - {"name": "function_name"}: Call the specified function
            max_tokens: Maximum number of tokens to generate
            temperature: Controls randomness (0.0-1.0, lower is more deterministic)

        Returns:
            Tuple of (response, metadata)
            where response may include function call information
        """
        pass

    @property
    @abc.abstractmethod
    def provider_name(self) -> str:
        """
        Returns the name of the LLM provider.
        """
        pass

    @property
    @abc.abstractmethod
    def default_model(self) -> str:
        """
        Returns the default model identifier for this provider.
        """
        pass

    @property
    @abc.abstractmethod
    def available_models(self) -> List[str]:
        """
        Returns a list of available model identifiers for this provider.
        """
        pass

    @abc.abstractmethod
    async def is_available(self) -> bool:
        """
        Check if the LLM provider is available and credentials are valid.

        Returns:
            True if provider is available, False otherwise
        """
        pass
