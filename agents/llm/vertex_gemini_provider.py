# agents/llm/gemini_api_provider.py # Renamed file conceptually

import os
import json
import logging
from typing import Dict, List, Any, Optional
import asyncio  # Added for async sleep

# Third-party imports
try:
    # Only import genai now
    import google.generativeai as genai
except ImportError as e:
    raise ImportError(
        f"Required Google library not installed. Please install google-generativeai: {e}"
    )

from .base import LLMProvider

logger = logging.getLogger(__name__)

# Max retries for API calls
MAX_RETRIES = 3
INITIAL_BACKOFF = 1  # seconds


class GeminiApiProvider(LLMProvider):
    """Google Gemini API LLM provider (using API Key)."""

    def __init__(
        self,
        model_name: str = "gemini-1.5-flash-001",
        api_key_env_var: str = "GEMINI_API_KEY",
        # Removed embedding_model_name as Vertex path is removed
    ):
        """
        Initializes the Google Gemini API provider.

        Args:
            model_name: The name of the Gemini model to use (e.g., "gemini-1.5-flash-001").
            api_key_env_var: The environment variable containing the Gemini API key.
        """
        api_key = os.environ.get(api_key_env_var)
        if not api_key:
            raise ValueError(
                f"API key environment variable '{api_key_env_var}' not set."
            )

        try:
            genai.configure(api_key=api_key)
            logger.info("Configured Google Generative AI SDK with API key.")
        except Exception as e:
            logger.error(
                f"Failed to configure Google Generative AI SDK: {e}", exc_info=True
            )
            raise

        self.model_name = model_name

        # Load the generative model via genai
        try:
            self.model_instance = genai.GenerativeModel(self.model_name)
            logger.info(f"Initialized Gemini API model: {self.model_name}")
        except Exception as e:
            logger.error(
                f"Failed to initialize genai model {self.model_name}: {e}",
                exc_info=True,
            )
            raise

        # Removed the Vertex AI embedding model loading section entirely

    async def _generate_with_retry(self, *args, **kwargs):
        """Wrapper for generate_content_async with retry logic."""
        retries = 0
        backoff_time = INITIAL_BACKOFF
        while retries < MAX_RETRIES:
            try:
                response = await self.model_instance.generate_content_async(
                    *args, **kwargs
                )
                # Simple check if response seems valid (can be improved)
                if hasattr(response, "text") or hasattr(response, "candidates"):
                    return response
                else:
                    raise ValueError(
                        "Received unexpected response format from Gemini API"
                    )
            except Exception as e:
                retries += 1
            logger.warning(
                f"Gemini API call failed (attempt {retries}/{MAX_RETRIES}): {e}"
            )
            if retries >= MAX_RETRIES:
                logger.error("Max retries reached for Gemini API call.")
                raise e  # Re-raise the last exception
                # Exponential backoff with jitter
                sleep_time = backoff_time + (os.urandom(1)[0] / 255.0)  # Add jitter
                logger.info(f"Retrying in {sleep_time:.2f} seconds...")
                await asyncio.sleep(sleep_time)
                backoff_time *= 2  # Double the backoff time
        # Should not be reached if MAX_RETRIES > 0
        raise RuntimeError("Retry logic finished without success or final error.")

    async def generate_completion(
        self,
        prompt: str,
        max_tokens: int = 8192,
        temperature: float = 0.7,
        system_message: Optional[str] = None,
        stop_sequences: Optional[List[str]] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
    ) -> str:
        """Generate a text completion using Google Gemini API."""
        full_prompt = f"{system_message}\n\n{prompt}" if system_message else prompt

        generation_config = genai.types.GenerationConfig(
            max_output_tokens=max_tokens,
            temperature=temperature,
            stop_sequences=stop_sequences if stop_sequences else [],
            top_p=top_p,
            top_k=top_k,
        )

        try:
            logger.debug(
                f"Generating completion via Gemini API (first 100 chars): {full_prompt[:100]}..."
            )
            response = await self._generate_with_retry(
                full_prompt, generation_config=generation_config
            )
            logger.debug("Completion generated successfully via Gemini API.")
            # Safely access text, handling potential lack of response or empty text
            return response.text if hasattr(response, "text") and response.text else ""
        except Exception as e:
            logger.error(
                f"Error during Gemini API completion generation: {e}", exc_info=True
            )
            return f"Error generating completion: {e}"

    async def generate_chat_completion(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 8192,
        temperature: float = 0.7,
        system_message: Optional[str] = None,
        stop_sequences: Optional[List[str]] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
    ) -> str:
        """Generate a chat completion using Google Gemini API."""

        # Format messages for google-generativeai
        # It expects a list of {'role': 'user'/'model', 'parts': [textpart]}
        formatted_messages = []
        if system_message:
            # Prepend system message as the first part of the first 'user' message
            # or handle using system_instruction if supported directly by the model/SDK version.
            # For simplicity here, we prepend to the first user message content.
            found_first_user = False
            temp_messages = []
        for msg in messages:
            role = msg.get("role", "user").lower()
            content = msg.get("content", "")
            if role == "system":  # Combine system messages
                system_message += "\n" + content
                continue
            # Map roles (e.g., 'assistant' -> 'model')
            if role == "assistant":
                role = "model"
            if role not in ["user", "model"]:
                logger.warning(f"Unsupported role '{role}', mapping to 'user'.")
                role = "user"
            if role == "user" and not found_first_user:
                content = f"{system_message}\n\n{content}"
                found_first_user = True
            temp_messages.append({"role": role, "parts": [content]})

            if not found_first_user and system_message:
                # If no user message was found, add system message as initial user message
                formatted_messages.append({"role": "user", "parts": [system_message]})

            formatted_messages.extend(temp_messages)

        else:
            # No system message, just format existing messages
            for msg in messages:
                role = msg.get("role", "user").lower()
                content = msg.get("content", "")
                if role == "assistant":
                    role = "model"
                if role == "system":
                    continue  # Skip system if system_message is None
            if role not in ["user", "model"]:
                role = "user"
                formatted_messages.append({"role": role, "parts": [content]})

        # Ensure conversation starts with a 'user' role if needed
        if formatted_messages and formatted_messages[0]["role"] != "user":
            logger.warning(
                "Chat history does not start with user role, prepending empty user message."
            )
            formatted_messages.insert(0, {"role": "user", "parts": [""]})
        # Ensure alternating roles (simple check, might need more robustness)
        for i in range(len(formatted_messages) - 1):
            if formatted_messages[i]["role"] == formatted_messages[i + 1]["role"]:
                logger.warning(
                    f"Consecutive messages with role '{formatted_messages[i]['role']}' found at index {i}. API might error."
                )
                # Consider inserting an empty message of the opposite role if required

        generation_config = genai.types.GenerationConfig(
            max_output_tokens=max_tokens,
            temperature=temperature,
            stop_sequences=stop_sequences if stop_sequences else [],
            top_p=top_p,
            top_k=top_k,
        )

        try:
            logger.debug(
                f"Generating chat completion via Gemini API with {len(formatted_messages)} messages."
            )
            # Use the chat interface implicitly by sending history
            response = await self._generate_with_retry(
                formatted_messages,
                generation_config=generation_config,
            )
            logger.debug("Chat completion generated successfully via Gemini API.")
            return response.text if hasattr(response, "text") and response.text else ""
        except Exception as e:
            # Log the formatted messages for debugging if error occurs
            try:
                logger.error(
                    f"Formatted messages leading to error: {json.dumps(formatted_messages)}"
                )
            except TypeError:
                logger.error("Could not serialize formatted messages for logging.")
            logger.error(
                f"Error during Gemini API chat completion generation: {e}",
                exc_info=True,
            )
            return f"Error generating chat completion: {e}"

    # --- Embedding Generation (Now uses Gemini API) ---
    async def generate_embeddings(
        self, text: str, task_type: str = "RETRIEVAL_DOCUMENT"
    ) -> List[float]:
        """
        Generate embeddings using the Google Gemini API (genai package).

        Args:
            text: The text to embed.
            task_type: The task type for the embedding (e.g., RETRIEVAL_QUERY, RETRIEVAL_DOCUMENT).
                       Supported values depend on the specific model used via genai.

        Returns:
            A list of floats representing the embedding, or empty list on failure.
        """
        # Map task_type to the format expected by google.generativeai (if needed)
        # Based on docs, the TaskType enum strings seem compatible directly
        # Ensure the model selected supports the given task_type
        valid_task_types = [
            "RETRIEVAL_QUERY",
            "RETRIEVAL_DOCUMENT",
            "SEMANTIC_SIMILARITY",
            "CLASSIFICATION",
            "CLUSTERING",
            # Add others if supported by the specific genai model
        ]
        if task_type not in valid_task_types:
            logger.warning(
                f"Unsupported task_type '{task_type}' for embedding model. Defaulting to RETRIEVAL_DOCUMENT. Check genai documentation for supported types."
            )
            task_type = "RETRIEVAL_DOCUMENT"

        embedding_model_name = (
            "models/gemini-embedding-exp-03-07"  # Explicitly use the 3072-dim model
        )

        retries = 0
        backoff_time = INITIAL_BACKOFF
        while retries < MAX_RETRIES:
            try:
                logger.debug(
                    f"Generating Gemini API embedding for text (first 50 chars): {text[:50]}... using model {embedding_model_name}"
                )

                result = await genai.embed_content_async(
                    model=embedding_model_name,
                    content=text,
                    task_type=task_type,
                )

                # Extract the embedding
                if result and "embedding" in result and result["embedding"]:
                    logger.debug(
                        f"Gemini API embedding generated successfully (vector dim: {len(result['embedding'])})"
                    )
                    # Ensure the dimension matches expectation
                    if len(result["embedding"]) != 3072:
                        logger.error(
                            f"CRITICAL: Embedding dimension mismatch! Expected 3072, got {len(result['embedding'])} from {embedding_model_name}"
                        )
                        return []  # Return empty on mismatch
                    return result["embedding"]
                else:
                    logger.warning(
                        f"Gemini API embedding generation returned no embedding for model {embedding_model_name}."
                    )
                    return []  # Return empty list if embedding is missing
            except Exception as e:
                retries += 1
                logger.warning(
                    f"Gemini API embedding call failed (attempt {retries}/{MAX_RETRIES}): {e}"
                )
                if retries >= MAX_RETRIES:
                    logger.error(
                        f"Max retries reached for Gemini API embedding call.",
                        exc_info=True,
                    )
                    return []  # Return empty list on persistent failure

                # Exponential backoff with jitter
                sleep_time = backoff_time + (os.urandom(1)[0] / 255.0)
                logger.info(f"Retrying embedding in {sleep_time:.2f} seconds...")
                await asyncio.sleep(sleep_time)
                backoff_time *= 2

        # Should not be reached if MAX_RETRIES > 0
        logger.error(
            "Embedding retry logic finished unexpectedly without success or error."
        )
        return []

    # --- Function Calling (Still uses Vertex AI path/types) ---
    async def function_calling(
        self,
        messages: List[Dict[str, str]],
        functions: List[Dict[str, Any]],
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        """Attempt function calling using the Gemini model.
        NOTE: This currently still uses the Vertex AI SDK/gapic types for tools.
              It might need significant changes if migrating fully to genai.
        """

        # Convert messages for google-generativeai chat format
        formatted_messages = []
        system_message = None  # Extract system message if needed for genai model later
        for msg in messages:
            role = msg.get("role", "user").lower()
            content = msg.get("content", "")
            if role == "system":
                system_message = (
                    system_message + "\n" if system_message else ""
                ) + content
                continue
            if role == "assistant":
                role = "model"
            if role not in ["user", "model"]:
                role = "user"
            formatted_messages.append({"role": role, "parts": [content]})
        # TODO: Handle system message if genai model needs it differently for tool use

        # Format functions/tools - KEEPING VERTEX/GAPIC FORMAT FOR NOW
        # This will likely need changing for genai's tool format
        try:
            # Convert function definitions to Vertex AI Tool format
            # Ensure aiplatform.gapic types are available if this path is kept
            from google.cloud import aiplatform as vertex_aiplatform_for_tools

            function_declarations = [
                vertex_aiplatform_for_tools.gapic.FunctionDeclaration(**func)
                for func in functions
            ]
            tools_vertex_format = [
                vertex_aiplatform_for_tools.gapic.Tool(
                    function_declarations=function_declarations
                )
            ]
            logger.warning(
                "Using Vertex/GAPIC format for tools - may need update for genai API."
            )
        except Exception as e:
            logger.error(
                f"Error formatting functions for Vertex AI Tool format: {e}",
                exc_info=True,
            )
            # Return error structure
            return {
                "content": f"Error processing functions: {e}",
                "function_name": None,
                "function_args": None,
            }

        generation_config = genai.types.GenerationConfig(temperature=temperature)

        try:
            logger.debug(
                f"Attempting function call via Gemini API with {len(functions)} functions."
            )

            # How genai handles tools might differ significantly. This is a placeholder.
            # We pass the Vertex formatted tools here, which might not work as expected.
            response = await self._generate_with_retry(
                formatted_messages,
                generation_config=generation_config,
                tools=tools_vertex_format,  # <<< Passing Vertex tools to genai API - Likely needs change
            )

            # Process response (check genai's response format for function calls)
            # This parsing logic is based on Vertex and likely needs updating for genai
            if response.candidates and response.candidates[0].content.parts:
                part = response.candidates[0].content.parts[0]
                # Check for function call according to genai's response structure
                if hasattr(part, "function_call") and part.function_call.name:
                    function_call = part.function_call
                    logger.info(
                        f"Gemini API requested function call: {function_call.name}"
                    )
                    # Args parsing might differ too
                    args_dict = (
                        function_call.args if hasattr(function_call, "args") else {}
                    )
                    # Convert args if they are not dict-like (check genai docs) - Placeholder
                    if not isinstance(args_dict, dict):
                        try:
                            # Attempt conversion if needed, this depends heavily on genai's format
                            args_dict = dict(args_dict)
                        except Exception as conv_e:
                            logger.error(
                                f"Could not convert function call args to dict: {conv_e}"
                            )
                            args_dict = {}

                    return {
                        "function_name": function_call.name,
                        "function_args": args_dict,
                        "content": "",
                    }

            # If no function call, return text content
            logger.debug("No function call requested by Gemini API.")
            return {
                "content": response.text if hasattr(response, "text") else "",
                "function_name": None,
                "function_args": None,
            }

        except Exception as e:
            logger.error(
                f"Error during Gemini API function calling attempt: {e}", exc_info=True
            )
            return {
                "content": f"Error during function call attempt: {e}",
                "function_name": None,
                "function_args": None,
            }
