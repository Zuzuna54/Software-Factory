"""
Google Vertex AI Gemini Model Provider Implementation
"""

import os
import json
import time
import asyncio
import logging
from typing import Dict, List, Any, Optional, Union, Tuple

import google.auth
from google.auth.exceptions import GoogleAuthError
from google.cloud import aiplatform
from google.cloud.aiplatform import initializer
from vertexai.generative_models import (
    GenerativeModel,
    GenerationConfig,
    FunctionDeclaration,
    Tool,
    Part,
    Content,
)
import vertexai
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from .base import LLMProvider

logger = logging.getLogger(__name__)

# Default values
DEFAULT_REGION = "us-central1"
DEFAULT_GEMINI_TEXT_MODEL = "gemini-2.0-pro"
DEFAULT_GEMINI_EMBEDDING_MODEL = "textembedding-gecko@latest"
DEFAULT_TASK_TYPE = "RETRIEVAL_DOCUMENT"
DEFAULT_MAX_RETRIES = 3
DEFAULT_MAX_OUTPUT_TOKENS = 1024

# Error types that should trigger retry
RETRIABLE_EXCEPTIONS = (
    ConnectionError,
    TimeoutError,
    GoogleAuthError,
)


class VertexGeminiProvider(LLMProvider):
    """
    Implementation of LLMProvider using Google Vertex AI with Gemini models.
    """

    def __init__(
        self,
        project_id: Optional[str] = None,
        location: Optional[str] = None,
        text_model: Optional[str] = None,
        embedding_model: Optional[str] = None,
        embedding_task_type: Optional[str] = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
        credentials_path: Optional[str] = None,
    ):
        """
        Initialize the Vertex AI Gemini provider.

        Args:
            project_id: Google Cloud Project ID (if None, will try to auto-detect)
            location: Google Cloud region (default: us-central1)
            text_model: Gemini model to use for text generation (default: gemini-1.5-pro)
            embedding_model: Model to use for embeddings (default: textembedding-gecko@latest)
            embedding_task_type: Task type for embedding generation
            max_retries: Maximum number of retry attempts for API calls
            credentials_path: Path to service account key file (if None, will use default credentials)
        """
        # Set up credentials
        if credentials_path:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path

        # Get project ID from environment or auto-detect
        self._project_id = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT")
        if not self._project_id:
            try:
                _, self._project_id = google.auth.default()
            except Exception as e:
                logger.error(f"Could not determine project ID: {str(e)}")
                self._project_id = None

        # Initialize other settings
        self._location = location or os.environ.get("VERTEX_LOCATION", DEFAULT_REGION)
        self._text_model_name = text_model or os.environ.get(
            "GEMINI_MODEL", DEFAULT_GEMINI_TEXT_MODEL
        )
        self._embedding_model_name = embedding_model or os.environ.get(
            "EMBEDDING_MODEL", DEFAULT_GEMINI_EMBEDDING_MODEL
        )
        self._embedding_task_type = embedding_task_type or os.environ.get(
            "EMBEDDING_TASK_TYPE", DEFAULT_TASK_TYPE
        )
        self._max_retries = max_retries
        self._initialized = False

        # Cache for models
        self._text_model = None
        self._embedding_model = None

        logger.info(
            f"Initialized VertexGeminiProvider with project={self._project_id}, location={self._location}"
        )

    async def _ensure_initialized(self) -> bool:
        """
        Ensure the provider is initialized.

        Returns:
            True if initialization successful, False otherwise
        """
        if self._initialized:
            return True

        try:
            if not self._project_id:
                logger.error("Cannot initialize VertexAI: Missing project ID")
                return False

            # Initialize VertexAI
            vertexai.init(project=self._project_id, location=self._location)

            # Initialize aiplatform
            aiplatform.init(project=self._project_id, location=self._location)

            self._initialized = True
            logger.info(
                f"VertexAI initialized for project {self._project_id} in {self._location}"
            )
            return True
        except Exception as e:
            logger.error(f"Error initializing VertexAI: {str(e)}")
            return False

    async def _get_text_model(self) -> GenerativeModel:
        """
        Get the Gemini model for text generation.

        Returns:
            GenerativeModel instance
        """
        if not await self._ensure_initialized():
            raise RuntimeError("VertexAI initialization failed")

        if self._text_model is None:
            self._text_model = GenerativeModel(self._text_model_name)

        return self._text_model

    async def _get_embedding_model(self):
        """
        Get the embedding model.
        This is currently a placeholder as the actual implementation depends
        on the specifics of how embeddings are handled in the current Vertex SDK.
        """
        if not await self._ensure_initialized():
            raise RuntimeError("VertexAI initialization failed")

        # For embeddings we use the aiplatform SDK
        # The model itself is specified in the predict call, not instantiated ahead of time
        return None

    @retry(
        stop=stop_after_attempt(DEFAULT_MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(RETRIABLE_EXCEPTIONS),
        reraise=True,
    )
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
        Generate text completion for a given prompt using Gemini.

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
        start_time = time.time()
        model = await self._get_text_model()

        # Configure generation parameters
        generation_config = GenerationConfig(
            max_output_tokens=max_tokens or DEFAULT_MAX_OUTPUT_TOKENS,
            temperature=temperature if temperature is not None else 0.7,
            top_p=top_p if top_p is not None else 0.95,
            top_k=top_k if top_k is not None else 40,
            stop_sequences=stop_sequences or [],
        )

        try:
            # Since the method is defined as async, we need to run the synchronous API call in a thread pool
            response = await asyncio.to_thread(
                model.generate_content,
                prompt,
                generation_config=generation_config,
            )

            # Extract the generated text
            generated_text = response.text

            # Prepare metadata
            metadata = {
                "model": self._text_model_name,
                "usage": {},  # Vertex API doesn't directly provide token usage
                "latency_ms": int((time.time() - start_time) * 1000),
                "finish_reason": "stop",  # Default, could be refined based on response
            }

            return generated_text, metadata
        except Exception as e:
            logger.error(f"Error in generate_text: {str(e)}")
            raise

    @retry(
        stop=stop_after_attempt(DEFAULT_MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(RETRIABLE_EXCEPTIONS),
        reraise=True,
    )
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
        Generate chat completion for a list of messages using Gemini.

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
        start_time = time.time()
        model = await self._get_text_model()

        # Configure generation parameters
        generation_config = GenerationConfig(
            max_output_tokens=max_tokens or DEFAULT_MAX_OUTPUT_TOKENS,
            temperature=temperature if temperature is not None else 0.7,
            top_p=top_p if top_p is not None else 0.95,
            top_k=top_k if top_k is not None else 40,
            stop_sequences=stop_sequences or [],
        )

        try:
            # Convert messages to Gemini format
            chat = model.start_chat()

            # System message is handled differently in Gemini
            system_message = next(
                (m for m in messages if m.get("role") == "system"), None
            )

            # Process messages
            responses = []
            gemini_messages = []

            for message in messages:
                role = message.get("role", "user")
                content = message.get("content", "")

                # Skip system message for now, it's handled separately
                if role == "system":
                    continue

                # Handle user and assistant messages
                gemini_messages.append(
                    Content(
                        role="user" if role == "user" else "model",
                        parts=[Part.from_text(content)],
                    )
                )

            # If there was a system message, add it as a parameter to the chat
            system_instruction = (
                system_message.get("content") if system_message else None
            )

            # Send all messages
            response = await asyncio.to_thread(
                chat.send_message,
                gemini_messages,
                generation_config=generation_config,
                system_instruction=system_instruction,
            )

            generated_text = response.text

            # Prepare metadata
            metadata = {
                "model": self._text_model_name,
                "usage": {},  # Vertex API doesn't directly provide token usage
                "latency_ms": int((time.time() - start_time) * 1000),
                "finish_reason": "stop",  # Default
            }

            return generated_text, metadata
        except Exception as e:
            logger.error(f"Error in generate_chat_completion: {str(e)}")
            raise

    @retry(
        stop=stop_after_attempt(DEFAULT_MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(RETRIABLE_EXCEPTIONS),
        reraise=True,
    )
    async def generate_embeddings(
        self,
        texts: List[str],
    ) -> Tuple[List[List[float]], Dict[str, Any]]:
        """
        Generate vector embeddings for a list of texts using Vertex AI.

        Args:
            texts: List of text strings to create embeddings for

        Returns:
            Tuple of (embeddings_list, metadata)
            where embeddings_list is a list of embedding vectors (one per input text)
        """
        if not await self._ensure_initialized():
            raise RuntimeError("VertexAI initialization failed")

        start_time = time.time()

        try:
            # Initialize Vertex AI Embeddings for Text endpoint
            endpoint = aiplatform.VertexAI(
                project=self._project_id,
                location=self._location,
            )

            # Get model as a prediction client
            model = aiplatform.TextEmbeddingModel.from_pretrained(
                self._embedding_model_name
            )

            # Batch process the embeddings
            embeddings_response = await asyncio.to_thread(
                model.get_embeddings, texts, task_type=self._embedding_task_type
            )

            # Extract embeddings from response
            embeddings = [emb.values for emb in embeddings_response]

            # Prepare metadata
            metadata = {
                "model": self._embedding_model_name,
                "latency_ms": int((time.time() - start_time) * 1000),
                "dimensions": len(embeddings[0]) if embeddings else 0,
                "count": len(embeddings),
            }

            return embeddings, metadata
        except Exception as e:
            logger.error(f"Error in generate_embeddings: {str(e)}")
            raise

    @retry(
        stop=stop_after_attempt(DEFAULT_MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(RETRIABLE_EXCEPTIONS),
        reraise=True,
    )
    async def function_calling(
        self,
        messages: List[Dict[str, str]],
        functions: List[Dict[str, Any]],
        function_call: Optional[str] = "auto",
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Generate text that includes function calls based on the input using Gemini.

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
        start_time = time.time()
        model = await self._get_text_model()

        # Configure generation parameters
        generation_config = GenerationConfig(
            max_output_tokens=max_tokens or DEFAULT_MAX_OUTPUT_TOKENS,
            temperature=temperature if temperature is not None else 0.7,
        )

        try:
            # Convert functions to Gemini format
            function_declarations = []
            for func in functions:
                function_declarations.append(
                    FunctionDeclaration(
                        name=func.get("name", ""),
                        description=func.get("description", ""),
                        parameters=func.get("parameters", {}),
                    )
                )

            # Create tools
            tools = [Tool(function_declarations=function_declarations)]

            # Convert messages to Gemini format
            chat = model.start_chat()

            # System message is handled differently in Gemini
            system_message = next(
                (m for m in messages if m.get("role") == "system"), None
            )

            # Process messages
            gemini_messages = []

            for message in messages:
                role = message.get("role", "user")
                content = message.get("content", "")

                # Skip system message for now, it's handled separately
                if role == "system":
                    continue

                # Handle user and assistant messages
                gemini_messages.append(
                    Content(
                        role="user" if role == "user" else "model",
                        parts=[Part.from_text(content)],
                    )
                )

            # If there was a system message, add it as a parameter to the chat
            system_instruction = (
                system_message.get("content") if system_message else None
            )

            # Send message with tools
            response = await asyncio.to_thread(
                chat.send_message,
                gemini_messages[-1] if gemini_messages else "",  # Send the last message
                generation_config=generation_config,
                system_instruction=system_instruction,
                tools=tools,
            )

            # Handle response based on whether a function was called
            function_call_info = None
            response_text = None

            # Check if there's a function call in the response
            for part in response.candidates[0].content.parts:
                if hasattr(part, "function_call"):
                    function_call_info = {
                        "name": part.function_call.name,
                        "arguments": json.loads(part.function_call.args),
                    }
                    break
                elif hasattr(part, "text"):
                    response_text = part.text

            result = {
                "content": response_text,
                "function_call": function_call_info,
            }

            # Prepare metadata
            metadata = {
                "model": self._text_model_name,
                "latency_ms": int((time.time() - start_time) * 1000),
            }

            return result, metadata
        except Exception as e:
            logger.error(f"Error in function_calling: {str(e)}")
            raise

    @property
    def provider_name(self) -> str:
        """
        Returns the name of the LLM provider.
        """
        return "Google Vertex AI Gemini"

    @property
    def default_model(self) -> str:
        """
        Returns the default model identifier for this provider.
        """
        return self._text_model_name

    @property
    def available_models(self) -> List[str]:
        """
        Returns a list of available model identifiers for this provider.
        """
        return [
            "gemini-1.0-pro",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
            "text-bison@002",
            "text-bison@001",
        ]

    async def is_available(self) -> bool:
        """
        Check if the LLM provider is available and credentials are valid.

        Returns:
            True if provider is available, False otherwise
        """
        try:
            await self._ensure_initialized()
            model = await self._get_text_model()

            # Simple ping to verify connectivity
            prompt = "Hello"
            response = await asyncio.to_thread(
                model.generate_content,
                prompt,
                generation_config=GenerationConfig(max_output_tokens=10),
            )

            # If we get here, the model is responsive
            return True
        except Exception as e:
            logger.error(f"Provider availability check failed: {str(e)}")
            return False
