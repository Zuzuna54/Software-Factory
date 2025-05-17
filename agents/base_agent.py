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

from infra.db.models import Agent, AgentActivity, AgentMessage

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
            **kwargs: Additional agent-specific configuration
        """
        self.agent_id = agent_id or uuid.uuid4()
        self.agent_type = agent_type
        self.agent_name = agent_name
        self.agent_role = agent_role
        self.capabilities = capabilities or []
        self.system_prompt = system_prompt
        self.db_session = db_session
        self.status = "active"
        self.extra_data = kwargs  # Store any additional configuration
        self.created_at = datetime.utcnow()

        # Retry configuration
        self.max_retries = kwargs.get("max_retries", 3)
        self.retry_delay = kwargs.get("retry_delay", 1.0)  # seconds

        # Performance tracking
        self.operation_timings = {}

        # Initialize logger
        self._setup_logging()

        logger.info(f"Agent initialized: {self.agent_name} (ID: {self.agent_id})")

    async def initialize_db(self) -> None:
        """
        Initialize the agent in the database if it doesn't already exist.
        """
        if not self.db_session:
            logger.warning("No database session provided, skipping DB initialization")
            return

        try:
            # Check if agent already exists
            query = select(Agent).where(Agent.agent_id == self.agent_id)
            result = await self.db_session.execute(query)
            existing_agent = result.scalar_one_or_none()

            if existing_agent:
                logger.info(f"Agent {self.agent_id} already exists in database")
                return

            # Create new agent record
            agent_data = {
                "agent_id": self.agent_id,
                "agent_type": self.agent_type,
                "agent_name": self.agent_name,
                "agent_role": self.agent_role,
                "capabilities": self.capabilities,
                "system_prompt": self.system_prompt,
                "status": self.status,
                "extra_data": self.extra_data,
                "created_at": self.created_at,
            }

            stmt = insert(Agent).values(**agent_data)
            await self.db_session.execute(stmt)
            await self.db_session.commit()

            # Log agent creation
            await self.log_activity(
                activity_type="agent_created",
                description=f"Agent {self.agent_name} ({self.agent_type}) created",
                input_data={
                    "agent_id": str(self.agent_id),
                    "agent_type": self.agent_type,
                    "agent_role": self.agent_role,
                },
            )

            logger.info(f"Agent {self.agent_id} created in database")
        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"Error initializing agent in database: {str(e)}")
            raise

    async def think(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Core thinking method to be implemented by specialized agents.
        This base implementation logs the thinking process.

        Args:
            context: Dictionary containing all relevant information needed for thinking

        Returns:
            Dictionary containing the results of the thinking process
        """
        start_time = time.time()

        try:
            # Log the start of thinking
            await self.log_activity(
                activity_type="thinking_started",
                description=f"Started thinking process with context: {context.get('summary', 'No summary')}",
                input_data={
                    "context_size": len(str(context)),
                    "context_type": context.get("type", "unknown"),
                },
            )

            # Implement actual thinking in subclasses
            # This default implementation just echoes the input
            result = {
                "thought_process": "Default thinking process - override in subclass",
                "decision": "No decision made",
                "rationale": "Base agent has no specialized thinking capabilities",
                "input": context,
            }

            # Log completion of thinking
            execution_time = time.time() - start_time
            self._record_timing("think", execution_time)

            await self.log_activity(
                activity_type="thinking_completed",
                description=f"Completed thinking process in {execution_time:.2f}s",
                input_data={
                    "execution_time_ms": int(execution_time * 1000),
                    "decision": result.get("decision"),
                },
            )

            return result
        except Exception as e:
            execution_time = time.time() - start_time
            await self.log_activity(
                activity_type="thinking_error",
                description=f"Error during thinking process: {str(e)}",
                input_data={
                    "error": str(e),
                    "execution_time_ms": int(execution_time * 1000),
                    "traceback": logging.traceback.format_exc(),
                },
            )
            raise

    async def send_message(
        self,
        receiver_id: uuid.UUID,
        content: str,
        message_type: str = "INFORM",
        task_id: Optional[uuid.UUID] = None,
        meeting_id: Optional[uuid.UUID] = None,
        parent_message_id: Optional[uuid.UUID] = None,
        context_vector=None,
        extra_data: Optional[Dict[str, Any]] = None,
    ) -> uuid.UUID:
        """
        Send a message to another agent.

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
            UUID of the created message
        """
        if not self.db_session:
            logger.warning("No database session provided, cannot send message")
            return None

        message_id = uuid.uuid4()

        try:
            # Create message record
            message_data = {
                "message_id": message_id,
                "sender_id": self.agent_id,
                "content": content,
                "message_type": message_type,
                "task_id": task_id,
                "meeting_id": meeting_id,
                "parent_message_id": parent_message_id,
                "context_vector": context_vector,
                "extra_data": extra_data or {},
            }

            stmt = insert(AgentMessage).values(**message_data)
            await self.db_session.execute(stmt)
            await self.db_session.commit()

            # Log the message sending
            await self.log_activity(
                activity_type="message_sent",
                description=f"Sent {message_type} message to agent {receiver_id}",
                input_data={
                    "message_id": str(message_id),
                    "receiver_id": str(receiver_id),
                    "message_type": message_type,
                    "content_summary": (
                        content[:100] + "..." if len(content) > 100 else content
                    ),
                },
            )

            logger.info(
                f"Message sent: {message_id} from {self.agent_id} to {receiver_id}"
            )
            return message_id
        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"Error sending message: {str(e)}")

            # Try recovery
            return await self._with_retry(
                self.send_message,
                receiver_id=receiver_id,
                content=content,
                message_type=message_type,
                task_id=task_id,
                meeting_id=meeting_id,
                parent_message_id=parent_message_id,
                context_vector=context_vector,
                extra_data=extra_data,
            )

    async def receive_message(self, message_id: uuid.UUID) -> Dict[str, Any]:
        """
        Process a received message.

        Args:
            message_id: UUID of the message to process

        Returns:
            Dictionary with processing results
        """
        if not self.db_session:
            logger.warning("No database session provided, cannot receive message")
            return {"success": False, "error": "No database session"}

        try:
            # Fetch the message
            query = select(AgentMessage).where(AgentMessage.message_id == message_id)
            result = await self.db_session.execute(query)
            message = result.scalar_one_or_none()

            if not message:
                logger.warning(f"Message {message_id} not found")
                return {"success": False, "error": "Message not found"}

            # Log message receipt
            await self.log_activity(
                activity_type="message_received",
                description=f"Received {message.message_type} message from agent {message.sender_id}",
                input_data={
                    "message_id": str(message_id),
                    "sender_id": str(message.sender_id),
                    "message_type": message.message_type,
                    "content_summary": (
                        message.content[:100] + "..."
                        if len(message.content) > 100
                        else message.content
                    ),
                },
            )

            # Process message - to be implemented by subclasses
            return {
                "success": True,
                "message": message,
                "response": "Message received by base agent (no processing implemented)",
            }
        except Exception as e:
            logger.error(f"Error receiving message: {str(e)}")

            # Log error
            await self.log_activity(
                activity_type="message_error",
                description=f"Error processing message {message_id}",
                input_data={"error": str(e)},
            )

            return {"success": False, "error": str(e)}

    async def log_activity(
        self,
        activity_type: str,
        description: str,
        input_data: Optional[Dict[str, Any]] = None,
    ) -> uuid.UUID:
        """
        Log an agent activity to the database.

        Args:
            activity_type: Type of activity being logged
            description: Human-readable description of the activity
            input_data: Additional structured details about the activity

        Returns:
            UUID of the created activity record
        """
        if not self.db_session:
            logger.info(f"Activity log (not stored): {activity_type} - {description}")
            return None

        activity_id = uuid.uuid4()
        timestamp = datetime.utcnow()

        try:
            # Create activity record
            activity_data = {
                "activity_id": activity_id,
                "agent_id": self.agent_id,
                "timestamp": timestamp,
                "activity_type": activity_type,
                "description": description,
                "input_data": input_data or {},
            }

            stmt = insert(AgentActivity).values(**activity_data)
            await self.db_session.execute(stmt)
            await self.db_session.commit()

            return activity_id
        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"Error logging activity: {str(e)}")

            # We don't retry activity logging to avoid infinite loops
            return None

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

    def _record_timing(self, operation: str, duration: float) -> None:
        """
        Record timing information for performance tracking.

        Args:
            operation: Name of the operation
            duration: Duration in seconds
        """
        if operation not in self.operation_timings:
            self.operation_timings[operation] = {
                "count": 0,
                "total_time": 0,
                "min_time": float("inf"),
                "max_time": 0,
            }

        stats = self.operation_timings[operation]
        stats["count"] += 1
        stats["total_time"] += duration
        stats["min_time"] = min(stats["min_time"], duration)
        stats["max_time"] = max(stats["max_time"], duration)

    def _setup_logging(self) -> None:
        """Configure logging for the agent."""
        # Add a specific handler for this agent if needed
        pass

    def __repr__(self) -> str:
        """String representation of the agent."""
        return f"{self.agent_name} ({self.agent_type}, ID: {self.agent_id})"
