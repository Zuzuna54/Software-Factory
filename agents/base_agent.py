"""
Base Agent Implementation for the Autonomous AI Development Team
"""

import uuid
import time
import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert

from agents.llm.vertex_gemini_provider import VertexGeminiProvider

# Added imports for VectorMemory integration
from agents.memory.vector_memory import VectorMemory, MemoryItem

# Added imports for ActivityLogger integration
from agents.logging.activity_logger import (
    ActivityLogger,
    ActivityCategory,
    ActivityLevel,
)

# Added imports for Communication integration
from agents.communication.protocol import Protocol
from agents.communication.message import Message, MessageType

# Import for the refactored function
from agents.base_agent_functions.store_memory_item import store_memory_item_logic
from agents.base_agent_functions.retrieve_memories import retrieve_memories_logic
from agents.base_agent_functions.think import think_logic
from agents.base_agent_functions.send_message import send_message_logic
from agents.base_agent_functions.receive_message import receive_message_logic

from agents.db.postgres import PostgresClient

logger = logging.getLogger(__name__)


class BaseAgent:
    """
    Base class for all autonomous agents in the Software Factory.
    Provides core functionality for agent initialization, thinking,
    logging, message handling, and error recovery.
    """

    def __init__(
        self,
        agent_id: Optional[uuid.UUID] = None,
        agent_type: str = "base",
        agent_name: str = "Base Agent",
        agent_role: str = "generic",
        capabilities: List[str] = None,
        system_prompt: Optional[str] = None,
        db_session: Optional[AsyncSession] = None,
        db_client: Optional[PostgresClient] = None,
        llm_provider: Optional[VertexGeminiProvider] = None,
        vector_memory: Optional[VectorMemory] = None,
        min_log_level: Optional[ActivityLevel] = None,
        **kwargs,
    ):
        """
        Initialize a new agent with the given metadata.

        Args:
            agent_id: Unique identifier for the agent (generated if not provided)
            agent_type: Type of agent (e.g., 'product_manager', 'developer', etc.)
            agent_name: Human-readable name for the agent
            agent_role: Role description of the agent
            capabilities: List of agent capabilities
            system_prompt: System prompt for the agent's LLM
            db_session: Database session for persistent operations
            db_client: Database client for communication operations
            llm_provider: LLM provider for generating embeddings and other LLM tasks
            vector_memory: Optional pre-initialized vector memory system
            min_log_level: Minimum log level for ActivityLogger
            **kwargs: Additional agent-specific configuration
        """
        self.agent_id = agent_id or uuid.uuid4()
        self.agent_type = agent_type
        self.agent_name = agent_name
        self.agent_role = agent_role
        self.capabilities = capabilities or []
        self.system_prompt = system_prompt
        self.db_session = db_session
        self.db_client = db_client
        self.llm_provider = llm_provider
        self.status = "active"
        self.extra_data = kwargs  # Store any additional configuration
        self.created_at = datetime.utcnow()

        # Retry configuration
        self.max_retries = kwargs.get("max_retries", 3)
        self.retry_delay = kwargs.get("retry_delay", 1.0)  # seconds

        # Performance tracking - REMOVED, will use ActivityLogger
        # self.operation_timings = {}

        # Initialize VectorMemory if not provided
        if vector_memory:
            self.vector_memory = vector_memory
        elif self.db_session and self.llm_provider:
            self.vector_memory = VectorMemory(
                db_session=self.db_session,
                llm_provider=self.llm_provider,
                agent_id=self.agent_id,
            )
        else:
            self.vector_memory = None
            logger.warning(
                f"VectorMemory could not be initialized for agent {self.agent_id}. "
                f"Missing db_session or llm_provider."
            )

        # Initialize ActivityLogger
        self.activity_logger = ActivityLogger(
            agent_id=self.agent_id,
            agent_name=self.agent_name,
            db_session=self.db_session,
            min_level=min_log_level or ActivityLevel.INFO,
        )

        # Initialize Communication Protocol
        self.protocol = (
            Protocol(db_client=self.db_client, validate_recipients=False)
            if self.db_client
            else None
        )
        # Agent registration with protocol is now handled in async initialize() method

        # Initialize logger (standard python logger setup)
        self._setup_logging()

        # Log basic initialization, but DB registration is separate
        logger.info(
            f"Agent object initialized: {self.agent_name} (ID: {self.agent_id}). Call initialize() for DB registration."
        )

    async def initialize(self):
        """
        Asynchronously initializes the agent, including registering it with the protocol
        (which handles database persistence).
        This method should be called and awaited after agent object creation.
        """
        if self.protocol:
            try:
                await self.protocol.register_agent(
                    agent_id=str(self.agent_id),
                    agent_type=self.agent_type,
                    agent_name=self.agent_name,
                    agent_role=self.agent_role,
                    capabilities=self.capabilities,
                    system_prompt=self.system_prompt,
                    extra_data=self.extra_data,
                )
                # Log agent creation (or existence check) via ActivityLogger AFTER protocol registration attempt
                # The protocol.register_agent now logs if it creates or finds an existing agent.
                # We can add a BaseAgent specific log here confirming its own initialization completion.
                await self.activity_logger.log_activity(
                    activity_type="agent_initialized_and_registered",
                    description=f"Agent {self.agent_name} completed async initialization and protocol registration.",
                    category=ActivityCategory.SYSTEM,
                    level=ActivityLevel.INFO,
                    details={
                        "agent_id": str(self.agent_id),
                        "agent_type": self.agent_type,
                    },
                )
                logger.info(
                    f"Agent {self.agent_name} (ID: {self.agent_id}) async initialization complete and registered with protocol."
                )
            except Exception as e:
                logger.error(
                    f"Error during agent {self.agent_id} async initialization (protocol registration): {str(e)}",
                    exc_info=True,
                )
                await self.activity_logger.log_error(
                    error_type="AgentInitializationError",
                    description=f"Failed during async initialization/protocol registration for agent {self.agent_id}",
                    exception=e,
                    severity=ActivityLevel.CRITICAL,
                )
                raise  # Re-raise the error so the caller knows initialization failed
        else:
            logger.warning(
                f"Agent {self.agent_id} has no Protocol. Skipping protocol registration."
            )

    # --- Start: VectorMemory Integration Methods ---
    async def store_memory_item(self, item: MemoryItem) -> Optional[List[uuid.UUID]]:
        """Store a MemoryItem using the agent's VectorMemory."""
        return await store_memory_item_logic(self, item)

    async def retrieve_memories(
        self,
        query_text: str,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 5,
    ) -> List[MemoryItem]:
        """Retrieve memories using the agent's VectorMemory."""
        return await retrieve_memories_logic(self, query_text, category, tags, limit)

    # --- End: VectorMemory Integration Methods ---

    async def think(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Core thinking method to be implemented by specialized agents.
        This base implementation logs the thinking process.

        Args:
            context: Dictionary containing all relevant information needed for thinking

        Returns:
            Dictionary containing the results of the thinking process
        """
        return await think_logic(self, context)

    async def send_message(
        self,
        receiver_id: uuid.UUID,
        content: str,
        message_type: str = "INFORM",
        task_id: Optional[uuid.UUID] = None,
        meeting_id: Optional[uuid.UUID] = None,
        parent_message_id: Optional[uuid.UUID] = None,
        context_vector=None,
        conversation_id: Optional[uuid.UUID] = None,
        extra_data: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Send a message to another agent using the Communication Protocol.

        Args:
            receiver_id: UUID of the receiving agent
            content: Message content
            message_type: Type of message (REQUEST, INFORM, PROPOSE, CONFIRM, ALERT)
            task_id: Optional ID of related task
            meeting_id: Optional ID of related meeting
            parent_message_id: Optional ID of parent message if this is a reply
            context_vector: Optional vector embedding of message content
            extra_data: Optional additional metadata for the message

        Returns:
            UUID of the created message if successful, None otherwise.
        """
        return await send_message_logic(
            self,
            receiver_id,
            content,
            message_type,
            task_id,
            meeting_id,
            parent_message_id,
            context_vector,
            conversation_id,
            extra_data,
        )

    async def receive_message(self, message_id: uuid.UUID) -> Optional[Message]:
        """
        Process a received message by fetching it via the Communication Protocol.
        TODO: This method currently fetches a message by ID. For a reactive system,
        agents should ideally process messages delivered to them (e.g., via a Celery task queue)
        rather than polling or being explicitly told to fetch by ID.

        Args:
            message_id: UUID of the message to process

        Returns:
            The Message object if found and processed, None otherwise.
        """
        return await receive_message_logic(self, message_id)

    async def _with_retry(self, func, *args, **kwargs) -> Any:
        """
        Execute a function with retry logic in case of failure.

        Args:
            func: Function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            Result of the function execution
        """
        retries = 0
        last_error = None

        while retries < self.max_retries:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                retries += 1
                last_error = e

                # Log retry attempt
                logger.warning(
                    f"Operation failed, attempt {retries}/{self.max_retries}: {str(e)}"
                )

                if retries < self.max_retries:
                    # Exponential backoff
                    wait_time = self.retry_delay * (2 ** (retries - 1))
                    await asyncio.sleep(wait_time)

        # If we get here, all retries failed
        logger.error(f"All {self.max_retries} retry attempts failed: {str(last_error)}")
        raise last_error

    def _setup_logging(self) -> None:
        """Configure logging for the agent."""
        # Add a specific handler for this agent if needed
        pass

    def __repr__(self) -> str:
        """String representation of the agent."""
        return f"{self.agent_name} ({self.agent_type}, ID: {self.agent_id})"
