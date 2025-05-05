# agents/llm/vertex_gemini_provider.py

import os
import json
import logging
from typing import Dict, List, Any, Optional

# Third-party imports - ensure these are in your dependency file (e.g., pyproject.toml)
try:
    from google.cloud import aiplatform

    # Import GenerativeModel directly from vertexai namespace
    from vertexai.generative_models import GenerativeModel

    # Import TextEmbeddingModel
    from vertexai.language_models import TextEmbeddingModel
    from google.auth import default
    from google.auth.exceptions import DefaultCredentialsError
except ImportError:
    raise ImportError(
        "google-cloud-aiplatform library not installed or vertexai namespace unavailable. Please install it: pip install google-cloud-aiplatform"
    )

from .base import LLMProvider

logger = logging.getLogger(__name__)


class VertexGeminiProvider(LLMProvider):
    """Google Vertex AI Gemini LLM provider."""

    def __init__(
        self,
        model_name: str = "gemini-1.5-flash-001",
        project: Optional[str] = None,
        location: Optional[str] = "us-central1",
    ):
        """
        Initializes the Vertex AI Gemini provider.

        Args:
            model_name: The name of the Gemini model to use (e.g., "gemini-1.5-flash-001", "gemini-1.5-pro-001").
            project: Google Cloud project ID. Tries to infer from environment if None.
            location: Google Cloud location. Defaults to "us-central1".
        """
        self.project = project or self._get_project_id()
        self.location = location
        self.model_name = model_name
        if not self.project:
            raise ValueError(
                "Google Cloud project ID could not be determined. Please set GOOGLE_CLOUD_PROJECT environment variable or pass the project parameter."
            )

        try:
            # Initialize Vertex AI client
            aiplatform.init(project=self.project, location=self.location)
            logger.info(
                f"Vertex AI initialized for project '{self.project}' in location '{self.location}'"
            )
        except Exception as e:
            logger.error(f"Failed to initialize Vertex AI: {e}", exc_info=True)
            raise

        # Load the generative model
        try:
            # Instantiate using the direct import
            self.model_instance = GenerativeModel(self.model_name)
            logger.info(f"Loaded Gemini model: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to load model {self.model_name}: {e}", exc_info=True)
            raise

        # Load the embedding model (use a specific, recommended version)
        # Note: Models like text-embedding-004 are generally recommended.
        # Check https://cloud.google.com/vertex-ai/docs/generative-ai/embeddings/get-text-embeddings for latest models
        self.embedding_model_name = "text-embedding-004"
        try:
            # Use the direct import
            self.embedding_model = TextEmbeddingModel.from_pretrained(
                self.embedding_model_name
            )
            logger.info(f"Loaded embedding model: {self.embedding_model_name}")
        except Exception as e:
            logger.error(
                f"Failed to load embedding model {self.embedding_model_name}: {e}",
                exc_info=True,
            )
            # Decide if this is critical - maybe allow operation without embeddings?
            # For now, let's raise it.
            raise

    def _get_project_id(self) -> Optional[str]:
        """Helper to get project ID from environment or ADC."""
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
        if project_id:
            return project_id
        try:
            _, project_id = default()
            if project_id:
                logger.info(f"Inferred Google Cloud project ID: {project_id}")
                return project_id
        except DefaultCredentialsError:
            logger.warning(
                "Could not determine Google Cloud project ID from Application Default Credentials."
            )
        return None

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
        """Generate a text completion using Vertex AI Gemini."""
        # Gemini API prefers combining system message and prompt for non-chat scenarios
        # Or use the system_instruction parameter if available and appropriate for the model version
        full_prompt = f"{system_message}\n\n{prompt}" if system_message else prompt

        generation_config = aiplatform.GenerationConfig(
            max_output_tokens=max_tokens,
            temperature=temperature,
            stop_sequences=stop_sequences if stop_sequences else [],
            top_p=top_p,
            top_k=top_k,
        )

        try:
            logger.debug(
                f"Generating completion for prompt (first 100 chars): {full_prompt[:100]}..."
            )
            response = await self.model_instance.generate_content_async(
                full_prompt, generation_config=generation_config
            )
            logger.debug("Completion generated successfully.")
            # Ensure response.text exists and handle potential errors/empty responses
            return response.text if hasattr(response, "text") else ""
        except Exception as e:
            logger.error(
                f"Error during Gemini completion generation: {e}", exc_info=True
            )
            # Depending on desired behavior, could return empty string or re-raise
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
        """Generate a chat completion using Vertex AI Gemini."""

        # Convert messages to Vertex AI Content format
        history = []
        for msg in messages:
            role = msg.get("role", "user").lower()
            # Gemini uses 'user' and 'model' roles
            if (
                role == "system"
            ):  # Handle system message separately if model supports it or prepend
                if system_message:
                    system_message += "\n" + msg.get("content", "")
                else:
                    system_message = msg.get("content", "")
                continue  # Skip adding system message to history if handled by system_instruction
            if role not in ["user", "model"]:
                logger.warning(
                    f"Unsupported role '{role}' in chat message, defaulting to 'user'."
                )
                role = "user"
            # Use the Content class from vertexai.generative_models if needed
            # Assuming the existing import works for now, might need adjustment
            history.append(
                aiplatform.gapic.Content(  # Keep using aiplatform.gapic for now, might need change
                    role=role,
                    parts=[aiplatform.gapic.Part(text=msg.get("content", ""))],
                )
            )

        generation_config_dict = {
            "max_output_tokens": max_tokens,
            "temperature": temperature,
            "stop_sequences": stop_sequences if stop_sequences else [],
            "top_p": top_p,
            "top_k": top_k,
        }
        # Filter out None values
        generation_config_dict = {
            k: v for k, v in generation_config_dict.items() if v is not None
        }

        # System instruction (check specific model documentation for best usage)
        # Import Content/Part from vertexai.generative_models
        try:
            from vertexai.generative_models import Content, Part
        except ImportError:
            # Fallback or error if direct import fails (shouldn't with 1.91.0)
            logger.error(
                "Failed to import Content/Part from vertexai.generative_models"
            )
            raise

        system_instruction_content = None
        if system_message:
            system_instruction_content = Content(
                role="system", parts=[Part.from_text(system_message)]
            )

        try:
            logger.debug(
                f"Generating chat completion with {len(history)} history messages."
            )
            # Use the new GenerationConfig from vertexai.generative_models
            try:
                from vertexai.generative_models import GenerationConfig
            except ImportError:
                logger.error(
                    "Failed to import GenerationConfig from vertexai.generative_models"
                )
                raise

            generation_config = GenerationConfig(**generation_config_dict)

            # Convert history messages to new Content/Part format if necessary
            converted_history = []
            for msg_content in history:
                # Assuming msg_content is currently aiplatform.gapic.Content
                # Adapt this based on actual type if different
                if hasattr(msg_content, "role") and hasattr(msg_content, "parts"):
                    # Extract text from the first part (assuming simple text messages)
                    text_content = (
                        msg_content.parts[0].text if msg_content.parts else ""
                    )
                    converted_history.append(
                        Content(
                            role=msg_content.role, parts=[Part.from_text(text_content)]
                        )
                    )
                else:
                    logger.warning(
                        f"Skipping conversion of unexpected history item: {type(msg_content)}"
                    )

            response = await self.model_instance.generate_content_async(
                converted_history,  # Send the converted history
                generation_config=generation_config,
                system_instruction=system_instruction_content,  # Pass system instruction here
            )
            logger.debug("Chat completion generated successfully.")
            return response.text if hasattr(response, "text") else ""
        except Exception as e:
            logger.error(
                f"Error during Gemini chat completion generation: {e}", exc_info=True
            )
            return f"Error generating chat completion: {e}"

    async def generate_embeddings(
        self, text: str, task_type: str = "RETRIEVAL_DOCUMENT"
    ) -> List[float]:
        """
        Generate embeddings using Vertex AI Text Embedding Model.

        Args:
            text: The text to embed.
            task_type: The task type for the embedding (e.g., RETRIEVAL_QUERY, RETRIEVAL_DOCUMENT,
                       SEMANTIC_SIMILARITY, CLASSIFICATION, CLUSTERING). Defaults to RETRIEVAL_DOCUMENT.

        Returns:
            A list of floats representing the embedding.
        """
        if not self.embedding_model:
            logger.error("Embedding model not initialized.")
            return []
        try:
            logger.debug(
                f"Generating embedding for text (first 50 chars): {text[:50]}..."
            )
            # The API expects a list of texts
            instances = [{"content": text, "task_type": task_type}]
            embeddings = await self.embedding_model.get_embeddings_async(instances)
            # Return the first (and only) embedding's values
            if embeddings and embeddings[0].values:
                logger.debug("Embedding generated successfully.")
                return embeddings[0].values
            else:
                logger.warning("Embedding generation returned no values.")
                return []
        except Exception as e:
            logger.error(f"Error generating embedding: {e}", exc_info=True)
            return []

    async def function_calling(
        self,
        messages: List[Dict[str, str]],
        functions: List[Dict[str, Any]],
        temperature: float = 0.7,  # Temperature might affect function call quality/determinism
    ) -> Dict[str, Any]:
        """Call functions based on Gemini reasoning."""

        # Convert messages to Vertex AI Content format
        history = []
        for msg in messages:
            role = msg.get("role", "user").lower()
            if role not in ["user", "model"]:
                role = "user"
            history.append(
                aiplatform.gapic.Content(
                    role=role,
                    parts=[aiplatform.gapic.Part(text=msg.get("content", ""))],
                )
            )

        # Convert function definitions to Vertex AI Tool format
        try:
            function_declarations = [
                aiplatform.gapic.FunctionDeclaration(**func) for func in functions
            ]
            tools = [aiplatform.gapic.Tool(function_declarations=function_declarations)]
        except Exception as e:
            logger.error(
                f"Error formatting functions for Vertex AI: {e}", exc_info=True
            )
            return {
                "content": f"Error processing functions: {e}",
                "function_name": None,
                "function_args": None,
            }

        generation_config = aiplatform.GenerationConfig(temperature=temperature)

        try:
            logger.debug(
                f"Attempting function call with {len(functions)} functions available."
            )
            # Send message with tools
            response = await self.model_instance.generate_content_async(
                history, generation_config=generation_config, tools=tools
            )

            # Check for function call in response
            if response.candidates and response.candidates[0].content.parts:
                part = response.candidates[0].content.parts[0]
                if hasattr(part, "function_call") and part.function_call.name:
                    function_call = part.function_call
                    logger.info(f"Gemini requested function call: {function_call.name}")
                    # Convert args Struct to dict
                    args_dict = (
                        type(function_call).to_dict(function_call).get("args", {})
                    )
                    return {
                        "function_name": function_call.name,
                        "function_args": args_dict,
                        "content": "",  # Usually no text content when function is called
                    }

            # If no function call, return the text content
            logger.debug("No function call requested by Gemini.")
            return {
                "content": response.text if hasattr(response, "text") else "",
                "function_name": None,
                "function_args": None,
            }

        except Exception as e:
            logger.error(f"Error during Gemini function calling: {e}", exc_info=True)
            return {
                "content": f"Error during function call attempt: {e}",
                "function_name": None,
                "function_args": None,
            }
