# agents/base_agent.py

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import time
from collections import deque

# Local imports (ensure correct relative paths)
from .llm.base import LLMProvider
from .memory.vector_memory import EnhancedVectorMemory
from .db.postgres import PostgresClient
from .memory.search import MemorySearch
from .logging.thought_capture import ThoughtCapture
from .communication.protocol import (
    CommunicationProtocol,
    AgentMessage,
    MessageType,
)  # Added communication protocol
from agents.metrics.collector import metrics_collector  # Import metrics collector
from app.events import emit_event  # Import event emitter from new location

logger_agent = logging.getLogger(__name__)  # Renamed logger to avoid conflict


class BaseAgent:
    """Base class for all agent types in the system."""

    def __init__(
        self,
        agent_id: Optional[str] = None,
        agent_type: str = "base",
        agent_name: str = "BaseAgent",
        llm_provider: Optional[LLMProvider] = None,
        db_client: Optional[PostgresClient] = None,
        vector_memory: Optional[EnhancedVectorMemory] = None,
        comm_protocol: Optional[CommunicationProtocol] = None,  # Added comm_protocol
        memory_search: Optional[MemorySearch] = None,
        thought_capture: Optional[ThoughtCapture] = None,
        capabilities: Optional[Dict[str, Any]] = None,
    ):
        self.agent_id = agent_id or str(uuid.uuid4())
        self.agent_type = agent_type
        self.agent_name = agent_name

        # Use agent-specific logger name
        self.logger = logging.getLogger(
            f"agent.{self.agent_type}.{self.agent_id.split('-')[0]}"
        )

        self.llm_provider = llm_provider
        self.db_client = db_client
        self.vector_memory = vector_memory
        self.comm_protocol = (
            comm_protocol or CommunicationProtocol()
        )  # Initialize if not provided

        # Initialize MemorySearch if dependencies are available
        if self.db_client and self.vector_memory and self.llm_provider:
            self.memory_search = memory_search or MemorySearch(
                db_client=self.db_client,
                vector_memory=self.vector_memory,
                llm_provider=self.llm_provider,
            )
        else:
            self.memory_search = None
            self.logger.warning(
                "MemorySearch could not be initialized due to missing dependencies."
            )

        # Initialize ThoughtCapture if dependencies are available
        if self.db_client:
            self.thought_capture = thought_capture or ThoughtCapture(
                db_client=self.db_client,
                vector_memory=self.vector_memory,
                llm_provider=self.llm_provider,
            )
            # Ensure ThoughtCapture is initialized (creates tables/indexes if needed)
            # asyncio.create_task(self.thought_capture.initialize()) # Removed
        else:
            self.thought_capture = None
            self.logger.warning(
                "ThoughtCapture could not be initialized due to missing DB client."
            )

        self.capabilities = capabilities or {}
        # self.logger initialization was MOVED to an earlier point in this __init__ method.

        # Defer agent registration until DB client is confirmed available
        if not self.db_client:  # Check kept for initial warning
            self.logger.warning(
                f"Agent {self.agent_id} ({self.agent_name}) cannot register yet: DB client not provided at __init__."
            )
        # asyncio.create_task(self._register_agent()) # Removed

    async def complete_initialization(self):
        """Completes asynchronous initialization steps."""
        if self.thought_capture:
            try:
                await self.thought_capture.initialize()
                self.logger.info(
                    f"ThoughtCapture initialized for agent {self.agent_id}"
                )
            except Exception as e:
                self.logger.error(
                    f"Error initializing ThoughtCapture for agent {self.agent_id}: {e}",
                    exc_info=True,
                )
        else:
            self.logger.warning(
                f"ThoughtCapture not available for agent {self.agent_id}, skipping initialization."
            )

        if self.db_client:
            try:
                await self._register_agent()
            except Exception as e:
                self.logger.error(
                    f"Error registering agent {self.agent_id}: {e}", exc_info=True
                )
        else:
            self.logger.warning(
                f"Agent {self.agent_id} ({self.agent_name}) cannot register: DB client not provided during complete_initialization."
            )

    async def _register_agent(self) -> None:
        """Register this agent in the database if it doesn't exist."""
        # Add check to ensure db_client exists and is initialized
        if not self.db_client:
            self.logger.error("Attempted to register agent without a database client.")
            return
        # Ensure DB pool is ready
        try:
            await self.db_client._ensure_initialized()
        except Exception as e:
            self.logger.error(
                f"Failed to ensure DB initialization for agent registration: {e}",
                exc_info=True,
            )
            return

        try:
            # Check if agent already exists
            query_check = "SELECT agent_id FROM agents WHERE agent_id = $1"
            result = await self.db_client.fetch_one(query_check, self.agent_id)

            if not result:
                # Agent doesn't exist, create it
                query_insert = """
                INSERT INTO agents (agent_id, agent_type, agent_name, capabilities, active)
                VALUES ($1, $2, $3, $4, $5)
                """
                await self.db_client.execute(
                    query_insert,
                    self.agent_id,
                    self.agent_type,
                    self.agent_name,
                    json.dumps(self.capabilities),
                    True,  # Default to active
                )
                self.logger.info(
                    f"Agent {self.agent_id} ({self.agent_name}) registered in database."
                )
                # Emit event on successful registration
                await emit_event(
                    "agent_registered",
                    {
                        "agent_id": self.agent_id,
                        "agent_type": self.agent_type,
                        "agent_name": self.agent_name,
                        "timestamp": datetime.now().isoformat(),
                    },
                )
            else:
                self.logger.debug(f"Agent {self.agent_id} already registered.")
                # Optionally update capabilities or active status here if needed
        except Exception as e:
            self.logger.error(
                f"Error during agent registration for {self.agent_id}: {e}",
                exc_info=True,
            )

    async def send_message(
        self, message: AgentMessage
    ) -> Optional[str]:  # Takes AgentMessage object
        """Send a structured message to another agent and log it to the database."""
        metrics_collector.increment_counter(
            "agent_messages_sent_total",
            tags={
                "agent_type": self.agent_type,
                "message_type": message.message_type.value,
            },
        )
        metrics_collector.start_timer(
            "agent_send_message_duration_seconds", tags={"agent_type": self.agent_type}
        )
        if not self.db_client:
            self.logger.warning(
                "No database client provided, message cannot be stored."
            )
            return None

        # Ensure DB pool is ready
        try:
            await self.db_client._ensure_initialized()
        except Exception as e:
            self.logger.error(
                f"Failed to ensure DB initialization for sending message: {e}",
                exc_info=True,
            )
            return None

        # Validate message sender matches this agent
        if message.sender != self.agent_id:
            self.logger.error(
                f"Agent {self.agent_id} attempted to send message with incorrect sender ID {message.sender}"
            )
            # Or potentially modify the sender ID? For now, log error.
            # message.sender = self.agent_id
            return None

        # Store message in database
        query = """
        INSERT INTO agent_messages (
            message_id, timestamp, sender_id, receiver_id,
            message_type, content, related_task_id,
            metadata, parent_message_id
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        RETURNING message_id
        """

        # Assuming parent_message_id is not part of AgentMessage dataclass for now
        parent_message_id = None

        try:
            await self.db_client.execute(
                query,
                message.message_id,
                message.created_at,  # Use timestamp from message object
                message.sender,
                message.receiver,
                message.message_type.value,  # Use enum value
                message.content,
                message.related_task,
                json.dumps(message.metadata or {}),
                parent_message_id,
            )

            # Emit event after storing message
            await emit_event(
                "message_sent",
                {
                    "message_id": message.message_id,
                    "sender": message.sender,
                    "receiver": message.receiver,
                    "message_type": message.message_type.value,
                    "timestamp": message.created_at.isoformat(),
                },
            )

            # Store vector embedding for semantic search (if components available)
            if self.vector_memory and self.llm_provider:
                try:
                    embedding = await self.llm_provider.generate_embeddings(
                        message.content
                    )
                    if embedding:
                        await self.vector_memory.store_entity(
                            entity_type="AgentMessage",
                            entity_id=message.message_id,
                            content=message.content,
                            embedding=embedding,
                            metadata={
                                "sender": message.sender,
                                "receiver": message.receiver,
                                "type": message.message_type.value,
                                "task_id": message.related_task,
                                **(message.metadata or {}),
                            },
                            tags=["communication", message.message_type.value.lower()],
                        )
                    else:
                        self.logger.warning(
                            f"Failed to generate embedding for message {message.message_id}"
                        )
                except Exception as e:
                    self.logger.error(
                        f"Error storing embedding for message {message.message_id}: {e}",
                        exc_info=True,
                    )
            else:
                self.logger.debug(
                    "Vector memory or LLM provider not available, skipping embedding storage."
                )

            # Log the activity
            await self.log_activity(
                activity_type="MessageSent",
                description=f"Sent {message.message_type.value} message to {message.receiver}",
                output_data={
                    "message_id": message.message_id,
                    "receiver_id": message.receiver,
                    "type": message.message_type.value,
                    "content_preview": message.content[:100],
                },
            )

            self.logger.info(
                f"Message sent: {message.message_id} to {message.receiver} (type: {message.message_type.value})"
            )
            metrics_collector.stop_timer(
                "agent_send_message_duration_seconds",
                tags={"agent_type": self.agent_type},
            )
            return message.message_id

        except Exception as e:
            metrics_collector.increment_counter(
                "agent_messages_send_errors_total", tags={"agent_type": self.agent_type}
            )
            metrics_collector.stop_timer(
                "agent_send_message_duration_seconds",
                tags={"agent_type": self.agent_type},
            )
            self.logger.error(
                f"Error sending/storing message {message.message_id}: {e}",
                exc_info=True,
            )
            await emit_event(
                "error_occurred",
                {
                    "agent_id": self.agent_id,
                    "action": "send_message",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                },
            )
            return None

    async def receive_messages(
        self,
        since_timestamp: Optional[datetime] = None,
        message_type: Optional[MessageType] = None,
        sender_id: Optional[str] = None,
        related_task_id: Optional[str] = None,
        limit: int = 100,
        mark_as_read: bool = False,  # Optional: Add flag to mark messages as read?
    ) -> List[AgentMessage]:
        """Retrieve messages sent to this agent with optional filters."""
        if not self.db_client:
            self.logger.warning(
                "No database client provided, cannot retrieve messages."
            )
            return []

        # Ensure DB pool is ready
        try:
            await self.db_client._ensure_initialized()
        except Exception as e:
            self.logger.error(
                f"Failed to ensure DB initialization for receiving messages: {e}",
                exc_info=True,
            )
            return []

        conditions = ["receiver_id = $1"]
        params: List[Any] = [self.agent_id]
        param_idx = 2

        if since_timestamp:
            conditions.append(f"timestamp > ${param_idx}")
            params.append(since_timestamp)
            param_idx += 1

        if message_type:
            conditions.append(f"message_type = ${param_idx}")
            params.append(message_type.value)  # Use enum value
            param_idx += 1

        if sender_id:
            conditions.append(f"sender_id = ${param_idx}")
            params.append(sender_id)
            param_idx += 1

        if related_task_id:
            conditions.append(f"related_task_id = ${param_idx}")
            params.append(related_task_id)
            param_idx += 1

        query = f"""
        SELECT
            message_id, timestamp, sender_id, message_type,
            content, related_task_id, metadata, parent_message_id
        FROM agent_messages
        WHERE {" AND ".join(conditions)}
        ORDER BY timestamp DESC
        LIMIT ${param_idx}
        """
        params.append(limit)

        try:
            results = await self.db_client.fetch_all(query, *params)
            messages = []
            for row in results:
                msg_data = {
                    "message_id": str(row["message_id"]),
                    "sender": str(row["sender_id"]),
                    "receiver": self.agent_id,  # We know the receiver is self
                    "message_type": row["message_type"],
                    "content": row["content"],
                    "related_task": (
                        str(row["related_task_id"]) if row["related_task_id"] else None
                    ),
                    "created_at": row["timestamp"],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                    # Parent message ID might be useful context
                    # "parent_message_id": str(row["parent_message_id"]) if row["parent_message_id"] else None
                }
                # Use the protocol parser to create AgentMessage object
                messages.append(self.comm_protocol.parse_message(msg_data))

            await self.log_activity(
                activity_type="MessagesRetrieved",
                description=f"Retrieved {len(messages)} messages",
                input_data={
                    "filters": {
                        "since": str(since_timestamp) if since_timestamp else None,
                        "type": message_type.value if message_type else None,
                        "sender": sender_id,
                        "task": related_task_id,
                    }
                },
                output_data={"count": len(messages)},
            )
            return messages

        except Exception as e:
            self.logger.error(
                f"Error retrieving messages for agent {self.agent_id}: {e}",
                exc_info=True,
            )
            return []

    async def search_messages(
        self, query_text: str, limit: int = 10
    ) -> List[AgentMessage]:
        """Search for messages semantically similar to the query text using MemorySearch."""
        if not self.memory_search:
            self.logger.warning(
                "MemorySearch is not available. Cannot search messages."
            )
            return []

        try:
            # Use MemorySearch to find relevant AgentMessage entities
            search_results = await self.memory_search.search_memory(
                query=query_text,
                entity_types=["AgentMessage"],  # Specify the entity type to search
                limit=limit,
                include_content=True,  # Ensure content is returned for parsing
            )

            messages = []
            for result in search_results:
                # Reconstruct AgentMessage from the search result data
                # Assumes metadata stored in vector store contains necessary fields
                msg_data = {
                    "message_id": result["entity_id"],
                    "sender": result["metadata"].get("sender"),
                    "receiver": result["metadata"].get("receiver"),
                    "message_type": result["metadata"].get("type"),
                    "content": result.get(
                        "content", ""
                    ),  # Use content from search result
                    "related_task": result["metadata"].get("task_id"),
                    "created_at": result["created_at"],
                    "metadata": result["metadata"],
                }
                # Basic validation
                if not all(
                    [msg_data["sender"], msg_data["receiver"], msg_data["message_type"]]
                ):
                    self.logger.warning(
                        f"Skipping search result with incomplete data: {result['entity_id']}"
                    )
                    continue

                try:
                    # Use the protocol parser to create AgentMessage object
                    parsed_message = self.comm_protocol.parse_message(msg_data)
                    if parsed_message:
                        messages.append(parsed_message)
                except Exception as parse_e:
                    self.logger.error(
                        f"Failed to parse search result into AgentMessage: {parse_e}",
                        exc_info=True,
                    )

            await self.log_activity(
                activity_type="MessageSearch",
                description=f"Searched messages similar to: {query_text[:100]}",
                input_data={"query": query_text},
                output_data={"result_count": len(messages)},
            )
            return messages

        except Exception as e:
            self.logger.error(
                f"Error during memory search for query '{query_text[:50]}...': {e}",
                exc_info=True,
            )
            return []

    async def log_activity(
        self,
        activity_type: str,
        description: str,
        thought_process: Optional[str] = None,
        related_files: Optional[List[str]] = None,
        input_data: Optional[Dict[str, Any]] = None,
        output_data: Optional[Dict[str, Any]] = None,
        decisions_made: Optional[Dict[str, Any]] = None,
        execution_time_ms: Optional[int] = None,
        related_task_id: Optional[str] = None,  # Added for better linking
    ) -> Optional[str]:
        """Log an activity performed by this agent to the database."""
        if not self.db_client:
            self.logger.warning(
                "No database client provided, activity will not be logged."
            )
            return None

        # Ensure DB pool is ready
        try:
            await self.db_client._ensure_initialized()
        except Exception as e:
            self.logger.error(
                f"Failed to ensure DB initialization for logging activity: {e}",
                exc_info=True,
            )
            return None

        activity_id = str(uuid.uuid4())
        timestamp = datetime.now()

        query = """
        INSERT INTO agent_activities (
            activity_id, agent_id, timestamp, activity_type,
            description, thought_process, related_files,
            input_data, output_data, decisions_made, execution_time_ms,
            related_task_id -- Added field
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
        RETURNING activity_id
        """

        try:
            await self.db_client.execute(
                query,
                activity_id,
                self.agent_id,
                timestamp,
                activity_type,
                description,
                thought_process,
                related_files or [],
                json.dumps(input_data or {}),
                json.dumps(output_data or {}),
                json.dumps(decisions_made or {}),
                execution_time_ms,
                related_task_id,  # Pass the new parameter
            )

            self.logger.info(
                f"Activity logged: {activity_id} ({activity_type}) for agent {self.agent_id}"
            )
            return activity_id
        except Exception as e:
            self.logger.error(
                f"Error logging activity {activity_type} for agent {self.agent_id}: {e}",
                exc_info=True,
            )
            return None

    async def think(
        self, prompt: str, system_message: Optional[str] = None
    ) -> Tuple[str, str]:
        """Perform internal reasoning using the LLM provider and log the thought process."""
        self.logger.info(f"Entering think method for agent {self.agent_id}")
        metrics_collector.increment_counter(
            "agent_think_requests_total", tags={"agent_type": self.agent_type}
        )
        metrics_collector.start_timer(
            "agent_think_duration_seconds", tags={"agent_type": self.agent_type}
        )
        if not self.llm_provider:
            error_msg = f"No LLM provider available for agent {self.agent_id}"
            self.logger.error(error_msg)
            # Log the error activity
            self.logger.info(
                f"Logging ThinkingError (no LLM provider) for agent {self.agent_id}"
            )
            await self.log_activity(
                activity_type="ThinkingError",
                description=error_msg,
                input_data={"prompt": prompt[:1000]},  # Log truncated prompt
            )
            self.logger.info(
                f"Exiting think method for agent {self.agent_id} (no LLM provider)"
            )
            return (
                "",
                error_msg,
            )  # Return empty string for thought and the error message

        start_time = datetime.now()
        thought = ""
        error_msg = ""

        LLM_TIMEOUT_SECONDS = 60.0  # Added timeout constant

        try:
            self.logger.info(
                f"Agent {self.agent_id} attempting to call LLM provider with {LLM_TIMEOUT_SECONDS}s timeout."
            )
            async with asyncio.timeout(LLM_TIMEOUT_SECONDS):
                # For now, using generate_completion. Could adapt to use generate_chat_completion if needed.
                thought = await self.llm_provider.generate_completion(
                    prompt=prompt,
                    system_message=system_message,
                    # Consider adding other parameters like max_tokens, temperature if needed
                )
            self.logger.info(f"Agent {self.agent_id} LLM provider call successful.")

        except asyncio.TimeoutError:
            self.logger.error(
                f"Agent {self.agent_id} LLM call timed out after {LLM_TIMEOUT_SECONDS} seconds.",
                exc_info=True,
            )
            error_msg = f"LLM call timed out after {LLM_TIMEOUT_SECONDS} seconds."
            metrics_collector.increment_counter(
                "agent_think_errors_total",
                tags={"agent_type": self.agent_type, "error_type": "timeout"},
            )

        except Exception as e:
            self.logger.error(
                f"Agent {self.agent_id} encountered exception during LLM call: {e}",
                exc_info=True,
            )
            error_msg = f"Error during LLM generation: {str(e)}"
            metrics_collector.increment_counter(
                "agent_think_errors_total", tags={"agent_type": self.agent_type}
            )
        finally:
            self.logger.info(
                f"Agent {self.agent_id} entered finally block in think method."
            )
            execution_time = int(
                (datetime.now() - start_time).total_seconds() * 1000
            )  # In milliseconds

            # Log the thinking activity, whether successful or not
            activity_type = "ThinkingError" if error_msg else "Thinking"
            description = (
                f"Internal reasoning error"
                if error_msg
                else f"Internal reasoning on: {prompt[:100]}..."
            )
            output_data = (
                {"error": error_msg}
                if error_msg
                else {"thought_preview": thought[:100] + "..."}
            )

            self.logger.info(
                f"Agent {self.agent_id} attempting to log_activity ({activity_type}) in think's finally block."
            )
            # Log simple activity record
            await self.log_activity(
                activity_type=activity_type,
                description=description,
                thought_process=None,  # Simple thought stored separately now
                input_data={"prompt": prompt, "system_message": system_message},
                output_data=output_data,
                execution_time_ms=execution_time,
            )
            self.logger.info(
                f"Agent {self.agent_id} completed log_activity ({activity_type}) in think's finally block."
            )

            # Capture detailed thought process if ThoughtCapture is available
            if self.thought_capture and not error_msg:
                self.logger.info(
                    f"Agent {self.agent_id} attempting to capture_thought_process."
                )
                try:
                    # Structure thought steps (simplified example)
                    thought_steps = [
                        {
                            "step": 1,
                            "timestamp": time.time(),
                            "action": "Received Prompt",
                            "content": prompt[:500],
                        },
                        {
                            "step": 2,
                            "timestamp": time.time(),
                            "action": "Generated Thought",
                            "content": thought[:500],
                        },
                    ]
                    await self.thought_capture.capture_thought_process(
                        agent_id=self.agent_id,
                        context=prompt,
                        thought_steps=thought_steps,
                        reasoning_path=thought,  # Use full thought as reasoning path for now
                        conclusion=thought.split("\n")[-1][
                            :200
                        ],  # Example conclusion heuristic
                        tags=["reasoning", self.agent_type],
                    )
                    self.logger.info(
                        f"Agent {self.agent_id} completed capture_thought_process."
                    )
                except Exception as capture_e:
                    self.logger.error(
                        f"Failed to capture detailed thought process for agent {self.agent_id}: {capture_e}",
                        exc_info=True,
                    )
            elif self.thought_capture and error_msg:
                self.logger.info(
                    f"Agent {self.agent_id} skipping capture_thought_process due to error: {error_msg}"
                )
            elif not self.thought_capture:
                self.logger.info(
                    f"Agent {self.agent_id} skipping capture_thought_process as it's not available."
                )

            metrics_collector.stop_timer(
                "agent_think_duration_seconds", tags={"agent_type": self.agent_type}
            )
        self.logger.info(
            f"Exiting think method for agent {self.agent_id}. Error: '{error_msg}'"
        )
        return (
            thought,
            error_msg,
        )  # Return thought (empty if error) and error message (empty if success)

    def __str__(self) -> str:
        return f"{self.agent_type}(id={self.agent_id}, name={self.agent_name})"

    # --- Core Agent Processing Loop ---

    async def run_processing_loop(self, interval_seconds: int = 5):
        """Main agent loop to periodically check for tasks and messages."""
        self.logger.info(f"Agent {self.agent_id} starting processing loop...")
        while True:
            try:
                self.logger.debug(
                    f"Agent {self.agent_id} loop: Checking for new tasks..."
                )
                await self.check_for_new_tasks()

                self.logger.debug(
                    f"Agent {self.agent_id} loop: Processing incoming messages..."
                )
                await self.process_incoming_messages()

            except Exception as e:
                self.logger.error(f"Error in agent processing loop: {e}", exc_info=True)
                # Consider adding more robust error handling/recovery

            self.logger.debug(
                f"Agent {self.agent_id} loop: Sleeping for {interval_seconds}s..."
            )
            await asyncio.sleep(interval_seconds)

    async def check_for_new_tasks(self):
        """Queries the DB for new tasks assigned to this agent."""
        if not self.db_client:
            self.logger.warning("No DB client, cannot check for new tasks.")
            return

        try:
            # Ensure the query string is clean
            query = """
            SELECT task_id, title, description, status, metadata, related_artifacts
            FROM tasks
            WHERE assigned_to = $1 AND status = $2
            LIMIT 10
            """
            new_tasks = await self.db_client.fetch_all(query, self.agent_id, "ASSIGNED")

            if not new_tasks:
                self.logger.debug("No new tasks found.")
                return

            self.logger.info(
                f"Found {len(new_tasks)} new tasks assigned via polling."
            )  # Added clarification

            for task_row in new_tasks:
                task_details = dict(task_row)
                task_id = str(task_details["task_id"])
                self.logger.info(
                    f"Polling: Processing newly assigned task: {task_id} - '{task_details.get('title')}'"
                )

                update_query = "UPDATE tasks SET status = $1 WHERE task_id = $2"
                await self.db_client.execute(update_query, "IN_PROGRESS", task_id)
                self.logger.info(
                    f"Polling: Updated task {task_id} status to IN_PROGRESS."
                )

                await self.handle_task(task_details)

        except Exception as e:
            self.logger.error(f"Error checking for new tasks: {e}", exc_info=True)

    async def process_incoming_messages(self, limit: int = 10):
        """Fetches and processes recent incoming messages."""
        # In a more robust system, we'd need a way to track processed messages
        # to avoid reprocessing. This could involve:
        # 1. An in-memory set of processed message IDs (lost on restart)
        # 2. A 'processed_at' timestamp or status field in the agent_messages table
        # For now, we just fetch recent messages and process based on type.

        try:
            # Fetch recent messages addressed to this agent
            messages = await self.receive_messages(limit=limit)

            if not messages:
                self.logger.debug("No new messages to process.")
                return

            self.logger.info(f"Processing {len(messages)} incoming messages.")

            for message in messages:
                self.logger.debug(
                    f"Processing message {message.message_id} (Type: {message.message_type.value})"
                )
                # Route message to appropriate handler based on type
                if message.message_type == MessageType.TASK_ASSIGNMENT:
                    await self.handle_task_assignment_message(message)
                elif message.message_type == MessageType.BUG_REPORT:  # Example
                    await self.handle_bug_report_message(message)
                elif message.message_type == MessageType.CODE_COMMITTED:  # Example
                    await self.handle_code_committed_message(message)
                # Add handlers for other message types as needed
                else:
                    self.logger.warning(
                        f"No handler defined for message type: {message.message_type.value}"
                    )

                # TODO: Implement robust processed message tracking here
                # E.g., update DB: UPDATE agent_messages SET processed_at = NOW() WHERE message_id = $1
                # Or add to self.processed_message_ids set

        except Exception as e:
            self.logger.error(f"Error processing incoming messages: {e}", exc_info=True)

    # --- Task and Message Handlers (Placeholders/Base Implementation) ---

    async def handle_task(self, task_details: Dict[str, Any]):
        """
        Handles a task fetched from the database.
        Intended to be overridden by specialized agents.
        """
        task_id = task_details.get("task_id")
        task_title = task_details.get("title")
        self.logger.info(
            f"BaseAgent received task {task_id} ('{task_title}'). No specific action defined in BaseAgent."
        )
        # Subclasses should implement logic based on task_details
        # E.g., call self.implement_api_endpoint, self.run_tests, etc.
        await asyncio.sleep(1)  # Simulate work

    async def handle_task_assignment_message(self, message: AgentMessage):
        """
        Handles a TASK_ASSIGNMENT message.
        Typically fetches full task details and calls handle_task.
        Intended to be overridden if specific behavior needed on message receipt.
        """
        task_id = message.related_task
        self.logger.info(
            f"Received TASK_ASSIGNMENT message for task {task_id}. Content: {message.content}"
        )
        if task_id and self.db_client:
            try:
                # Fetch full task details from DB
                query = "SELECT * FROM tasks WHERE task_id = $1"
                task_row = await self.db_client.fetch_one(query, task_id)
                if task_row:
                    task_details = dict(task_row)
                    # Ensure status reflects potential immediate update from check_for_new_tasks
                    if task_details.get("status") in ["ASSIGNED", "BACKLOG"]:
                        update_query = "UPDATE tasks SET status = $1 WHERE task_id = $2"
                        await self.db_client.execute(
                            update_query, "IN_PROGRESS", task_id
                        )
                        self.logger.info(
                            f"Updated task {task_id} status to IN_PROGRESS via message handler."
                        )
                        task_details["status"] = "IN_PROGRESS"  # Update local copy

                    await self.handle_task(task_details)
                else:
                    self.logger.error(
                        f"Task details not found in DB for task ID {task_id} from assignment message."
                    )
            except Exception as e:
                self.logger.error(
                    f"Error fetching/handling task details from assignment message {message.message_id}: {e}",
                    exc_info=True,
                )
        else:
            self.logger.warning(
                f"Cannot fetch task details for assignment message {message.message_id}: Missing task_id or db_client."
            )

    async def handle_bug_report_message(self, message: AgentMessage):
        """
        Placeholder handler for BUG_REPORT messages.
        Intended to be overridden by relevant agents (e.g., BackendDeveloperAgent).
        """
        self.logger.info(
            f"Received BUG_REPORT message: {message.message_id}. Content: {message.content}"
        )
        # Developer agent would override this to potentially call self.fix_code_issue
        pass

    async def handle_code_committed_message(self, message: AgentMessage):
        """
        Placeholder handler for CODE_COMMITTED messages.
        Intended to be overridden by relevant agents (e.g., QAAgent).
        """
        self.logger.info(
            f"Received CODE_COMMITTED message: {message.message_id}. Content: {message.content}"
        )
        # QA agent would override this to potentially call self.run_tests
        pass
