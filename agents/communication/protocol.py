"""
Protocol class for message validation, routing, and persistence.
"""

import asyncio
import logging
import uuid
import json
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set, Type, Union, cast

from sqlalchemy import select, func, desc

from infra.db.models import AgentMessage, Agent, Conversation as ConversationModel
from agents.db import PostgresClient
from .message import Message, MessageType

logger = logging.getLogger(__name__)


class Protocol:
    """
    Protocol for message validation, routing, and persistence.

    Handles:
    - Message validation
    - Message routing to appropriate recipients
    - Conversation threading
    - Message persistence to database
    """

    def __init__(
        self,
        db_client: PostgresClient,
        message_handlers: Optional[Dict[MessageType, Callable]] = None,
        validate_recipients: bool = True,
    ):
        """
        Initialize the protocol.

        Args:
            db_client: Database client for message persistence
            message_handlers: Optional dictionary mapping message types to handler functions
            validate_recipients: Whether to validate message recipients
        """
        self.db_client = db_client
        self.message_handlers = message_handlers or {}
        self.validate_recipients = validate_recipients
        self.registered_agents: Set[str] = set()
        self.logger = logger

    async def register_agent(
        self,
        agent_id: str,
        agent_type: str = "test",
        agent_name: str = "Test Agent",
        agent_role: Optional[str] = None,
        capabilities: Optional[List[str]] = None,
        system_prompt: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Register an agent with the protocol and ensure it exists in the database.

        Args:
            agent_id: ID of the agent to register
            agent_type: Type of the agent
            agent_name: Name of the agent
            agent_role: Role of the agent
            capabilities: List of agent capabilities
            system_prompt: System prompt for the agent
            extra_data: Additional agent-specific configuration
        """
        self.registered_agents.add(agent_id)
        self.logger.info(
            f"Agent {agent_id} ({agent_name}) registered with the protocol instance."
        )

        # Create or verify a record in the agents table using SQLAlchemy ORM
        try:

            # Define the agent creation logic directly or within an awaited async helper
            # For clarity, keeping _create_agent helper but it will be awaited.
            async def _create_agent_in_db():
                try:
                    # Use provided details or sensible defaults
                    db_agent_role = agent_role if agent_role else agent_type
                    db_capabilities = (
                        {"capabilities": capabilities}
                        if capabilities
                        else {"capabilities": []}
                    )
                    db_system_prompt = (
                        system_prompt
                        if system_prompt
                        else f"You are {agent_name}, a {agent_type} agent."
                    )
                    db_extra_data = extra_data if extra_data else {}

                    agent_record = Agent(
                        agent_id=uuid.UUID(agent_id),
                        agent_type=agent_type,
                        agent_name=agent_name,
                        agent_role=db_agent_role,
                        capabilities=db_capabilities,
                        status="active",  # Default status
                        system_prompt=db_system_prompt,
                        extra_data=db_extra_data,
                        # created_at is default now() in model
                        # last_seen_at can be updated separately
                    )

                    async with self.db_client.transaction() as session:  # Use the client's session manager
                        stmt = select(Agent).where(
                            Agent.agent_id == uuid.UUID(agent_id)
                        )
                        result = await session.execute(stmt)
                        existing_agent = result.scalar_one_or_none()

                        if not existing_agent:
                            session.add(agent_record)
                            await session.flush()  # Ensure ID is available if needed, and record is persisted
                            self.logger.info(
                                f"Agent {agent_id} record CREATED in database by protocol."
                            )
                        else:
                            # Optionally update existing agent if details differ
                            # For now, just log that it exists.
                            # Consider adding update logic if agent details can change via registration.
                            self.logger.info(
                                f"Agent {agent_id} ALREADY EXISTS in database. Protocol registration confirmed."
                            )
                except Exception as inner_e:
                    self.logger.error(
                        f"Error in _create_agent_in_db for {agent_id}: {str(inner_e)}",
                        exc_info=True,
                    )
                    raise  # Re-raise to be caught by the outer try-except

            await _create_agent_in_db()  # Await the database operation

        except Exception as e:
            self.logger.error(
                f"Error ensuring agent {agent_id} in database via protocol: {str(e)}",
                exc_info=True,
            )
            # Decide if this failure should prevent agent registration with the protocol instance
            # For now, it registers with the protocol instance first, then attempts DB.
            # If DB fails, agent is still "known" to this protocol instance but not in DB via this call.

    def unregister_agent(self, agent_id: str) -> None:
        """
        Unregister an agent from the protocol.

        Args:
            agent_id: ID of the agent to unregister
        """
        if agent_id in self.registered_agents:
            self.registered_agents.remove(agent_id)
            self.logger.info(f"Agent {agent_id} unregistered from the protocol")

    def register_handler(
        self, message_type: MessageType, handler: Callable[[Message], Any]
    ) -> None:
        """
        Register a handler for a message type.

        Args:
            message_type: Type of message to handle
            handler: Function to call when a message of this type is received
        """
        self.message_handlers[message_type] = handler
        self.logger.info(f"Handler registered for message type {message_type.value}")

    async def validate_message(self, message: Message) -> bool:
        """
        Validate a message.

        Args:
            message: Message to validate

        Returns:
            True if the message is valid, False otherwise
        """
        # Check if sender is registered
        if self.validate_recipients and message.sender_id not in self.registered_agents:
            self.logger.warning(
                f"Message from unregistered sender: {message.sender_id}"
            )
            return False

        # Check if recipient is registered
        if (
            self.validate_recipients
            and message.recipient_id not in self.registered_agents
        ):
            self.logger.warning(
                f"Message to unregistered recipient: {message.recipient_id}"
            )
            return False

        # Check if message type is valid
        if not isinstance(message.message_type, MessageType):
            self.logger.warning(f"Invalid message type: {message.message_type}")
            return False

        # Check if message content is valid
        if not message.content:
            self.logger.warning("Message content is empty")
            return False

        # Check if in_reply_to refers to a valid message
        if message.in_reply_to:
            # Check if the referenced message exists in the database
            exists = await self._message_exists(message.in_reply_to)
            if not exists:
                self.logger.warning(
                    f"Message references non-existent message: {message.in_reply_to}"
                )
                return False

        return True

    async def send_message(self, message: Message) -> bool:
        """
        Send a message through the protocol.

        Args:
            message: Message to send

        Returns:
            True if the message was sent successfully, False otherwise
        """
        # Validate the message
        is_valid = await self.validate_message(message)
        if not is_valid:
            self.logger.error(f"Message validation failed: {message}")
            return False

        # Persist the message to the database
        success = await self._persist_message(message)
        if not success:
            self.logger.error(f"Failed to persist message: {message}")
            return False

        # Call the appropriate handler if registered
        if message.message_type in self.message_handlers:
            try:
                handler = self.message_handlers[message.message_type]
                await self._call_handler(handler, message)
            except Exception as e:
                self.logger.error(f"Error in message handler: {str(e)}")
                # Continue with message delivery even if handler fails

        self.logger.info(
            f"Message sent: {message.message_id} "
            f"({message.message_type.value}) "
            f"from {message.sender_id} to {message.recipient_id}"
        )
        return True

    async def get_message(self, message_id: str) -> Optional[Message]:
        """
        Retrieve a message by its ID.

        Args:
            message_id: ID of the message to retrieve

        Returns:
            The message if found, None otherwise
        """
        try:
            async with self.db_client.session() as session:
                stmt = select(AgentMessage).where(AgentMessage.message_id == message_id)
                result = await session.execute(stmt)
                record = result.scalar_one_or_none()

                if record:
                    return self._record_to_message(record)
                return None
        except Exception as e:
            self.logger.error(f"Error retrieving message {message_id}: {str(e)}")
            return None

    async def get_conversation_messages(
        self, conversation_id: str, limit: int = 100, offset: int = 0
    ) -> List[Message]:
        """
        Retrieve messages in a conversation.

        Args:
            conversation_id: ID of the conversation
            limit: Maximum number of messages to retrieve
            offset: Number of messages to skip

        Returns:
            List of messages in the conversation
        """
        try:
            # Since we're not storing the conversation_id in the database directly,
            # we need to get all messages and filter them by their conversation_id
            # attribute after converting to Message objects
            async with self.db_client.session() as session:
                # Get recent messages (more than we need to allow for filtering)
                expanded_limit = limit * 5  # Get more records to account for filtering
                stmt = (
                    select(AgentMessage)
                    .order_by(desc(AgentMessage.created_at))
                    .limit(expanded_limit)
                )
                result = await session.execute(stmt)
                records = result.scalars().all()

                # Convert to Message objects
                messages = [self._record_to_message(record) for record in records]

                # Filter by conversation_id
                filtered_messages = [
                    msg for msg in messages if msg.conversation_id == conversation_id
                ]

                # Apply limit and offset
                paginated_messages = filtered_messages[offset : offset + limit]

                return paginated_messages
        except Exception as e:
            self.logger.error(
                f"Error retrieving conversation messages {conversation_id}: {str(e)}"
            )
            return []

    async def get_agent_messages(
        self,
        agent_id: str,
        as_sender: bool = True,
        as_recipient: bool = True,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Message]:
        """
        Retrieve messages sent or received by an agent.

        Args:
            agent_id: ID of the agent
            as_sender: Whether to include messages sent by the agent
            as_recipient: Whether to include messages received by the agent
            limit: Maximum number of messages to retrieve
            offset: Number of messages to skip

        Returns:
            List of messages sent or received by the agent
        """
        if not as_sender and not as_recipient:
            return []

        try:
            async with self.db_client.session() as session:
                # Start building the query
                query = select(AgentMessage)

                # Add filters for sender and recipient
                if as_sender and as_recipient:
                    query = query.where(
                        (AgentMessage.sender_id == agent_id)
                        | (AgentMessage.parent_message_id == agent_id)
                    )
                elif as_sender:
                    query = query.where(AgentMessage.sender_id == agent_id)
                elif as_recipient:
                    query = query.where(AgentMessage.parent_message_id == agent_id)

                # Add limit and offset
                query = (
                    query.order_by(desc(AgentMessage.created_at))
                    .limit(limit)
                    .offset(offset)
                )

                # Execute the query
                result = await session.execute(query)
                records = result.scalars().all()

                return [self._record_to_message(record) for record in records]
        except Exception as e:
            self.logger.error(
                f"Error retrieving agent messages for {agent_id}: {str(e)}"
            )
            return []

    async def count_messages(
        self,
        conversation_id: Optional[str] = None,
        sender_id: Optional[str] = None,
        recipient_id: Optional[str] = None,
        message_type: Optional[MessageType] = None,
    ) -> int:
        """
        Count messages matching the given criteria.

        Args:
            conversation_id: Optional conversation ID to filter by
            sender_id: Optional sender ID to filter by
            recipient_id: Optional recipient ID to filter by
            message_type: Optional message type to filter by

        Returns:
            Number of messages matching the criteria
        """
        try:
            async with self.db_client.session() as session:
                # Start building the query
                query = select(AgentMessage)

                # Add filters if provided (except for conversation_id which we'll handle after)
                if sender_id:
                    query = query.where(AgentMessage.sender_id == sender_id)
                if recipient_id:
                    query = query.where(
                        AgentMessage.receiver_id == recipient_id
                    )  # Use receiver_id instead of parent_message_id
                if message_type:
                    query = query.where(AgentMessage.message_type == message_type.value)

                # Execute the query
                result = await session.execute(query)
                records = result.scalars().all()

                # If we need to filter by conversation_id, we'll need to convert to Message objects
                if conversation_id:
                    messages = [self._record_to_message(record) for record in records]
                    filtered_messages = [
                        msg
                        for msg in messages
                        if msg.conversation_id == conversation_id
                    ]
                    return len(filtered_messages)

                # Otherwise just return the count of records
                return len(records)
        except Exception as e:
            self.logger.error(f"Error counting messages: {str(e)}")
            return 0

    # Private methods

    async def _message_exists(self, message_id: str) -> bool:
        """
        Check if a message with the given ID exists.

        Args:
            message_id: ID of the message to check

        Returns:
            True if the message exists, False otherwise
        """
        try:
            async with self.db_client.session() as session:
                stmt = (
                    select(func.count())
                    .select_from(AgentMessage)
                    .where(AgentMessage.message_id == message_id)
                )
                result = await session.execute(stmt)
                count = result.scalar_one()
                return count > 0
        except Exception as e:
            self.logger.error(
                f"Error checking if message exists {message_id}: {str(e)}"
            )
            return False

    async def _persist_message(self, message: Message) -> bool:
        """
        Persist a message to the database.

        Args:
            message: Message to persist

        Returns:
            True if the message was persisted successfully, False otherwise
        """
        try:
            # Convert content to string if it's not already
            content = message.content
            if isinstance(content, dict):
                content = json.dumps(content)

            metadata = message.metadata.copy() if message.metadata else {}
            metadata["conversation_id"] = (
                message.conversation_id
            )  # Ensure it's in metadata for _record_to_message logic

            # Log types of ID fields from Pydantic Message just before SQLAlchemy model instantiation
            self.logger.debug(
                f"Persisting message. ID types before UUID conversion: "
                f"message_id: {type(message.message_id)}, "
                f"sender_id: {type(message.sender_id)}, "
                f"recipient_id: {type(message.recipient_id)}, "
                f"task_id: {type(message.task_id)}, "
                f"meeting_id: {type(message.meeting_id)}, "
                f"in_reply_to: {type(message.in_reply_to)}, "
                f"conversation_id: {type(message.conversation_id)}"
            )

            # Helper to convert string to UUID if not None
            def to_uuid(id_str: Optional[str]) -> Optional[uuid.UUID]:
                if id_str is None:
                    return None
                if isinstance(id_str, uuid.UUID):  # If it's already a UUID, return it
                    return id_str
                if isinstance(id_str, str):
                    try:
                        return uuid.UUID(id_str)
                    except ValueError:
                        self.logger.error(
                            f"Invalid string for UUID conversion: {id_str}"
                        )
                        return None  # Or raise an error, or handle as appropriate
                self.logger.warning(
                    f"Unexpected type for UUID conversion: {type(id_str)}, value: {id_str}"
                )
                return None

            agent_message = AgentMessage(
                message_id=to_uuid(
                    message.message_id
                ),  # Pydantic Message.message_id should be str
                created_at=message.created_at,  # Pydantic Message.created_at is datetime
                sender_id=to_uuid(
                    message.sender_id
                ),  # Pydantic Message.sender_id should be str
                receiver_id=to_uuid(
                    message.recipient_id
                ),  # Pydantic Message.recipient_id should be str
                message_type=message.message_type.value,
                content=content,
                related_task_id=to_uuid(
                    message.task_id
                ),  # Pydantic Message.task_id is Optional[str]
                metadata=metadata,
                parent_message_id=to_uuid(
                    message.in_reply_to
                ),  # Pydantic Message.in_reply_to is Optional[str]
                context_vector=message.context_vector,  # Pydantic Message.context_vector is Optional[List[float]]
                extra_data=metadata,  # Reusing metadata here as AgentMessage.extra_data
                meeting_id=to_uuid(
                    message.meeting_id
                ),  # Pydantic Message.meeting_id is Optional[str]
                conversation_id=to_uuid(
                    message.conversation_id
                ),  # Pydantic Message.conversation_id is Optional[str]
            )

            async with self.db_client.transaction() as session:
                # Ensure Conversation record exists if message.conversation_id is set
                if (
                    agent_message.conversation_id
                ):  # This is now a UUID object from to_uuid
                    conv_stmt = select(ConversationModel).where(
                        ConversationModel.conversation_id
                        == agent_message.conversation_id
                    )
                    existing_conv = (
                        await session.execute(conv_stmt)
                    ).scalar_one_or_none()
                    if not existing_conv:
                        # The import for ConversationModel is now at the top of the file
                        # No need for: from infra.db.models.core import Conversation as ConversationModel
                        new_conv = ConversationModel(
                            conversation_id=agent_message.conversation_id,
                        )
                        session.add(new_conv)
                        self.logger.info(
                            f"Created new Conversation record for ID: {agent_message.conversation_id} during message persistence."
                        )

                session.add(agent_message)

            self.logger.info(f"Message persisted: {message.message_id}")
            return True

        except Exception as e:
            self.logger.error(
                f"Error persisting message {message.message_id}: {str(e)}"
            )
            return False

    def _record_to_message(self, record: AgentMessage) -> Message:
        """
        Convert a database record to a Message object.

        Args:
            record: Database record to convert

        Returns:
            Message object
        """
        try:
            # Parse content field as JSON if possible
            content = record.content
            try:
                content = json.loads(content)
            except (json.JSONDecodeError, TypeError):
                # If not valid JSON, use as is
                pass

            # Extract conversation_id from the Message's metadata if available,
            # otherwise use a deterministic ID based on the message_id
            conversation_id = None
            if record.extra_data and isinstance(record.extra_data, dict):
                conversation_id = record.extra_data.get("conversation_id")

            if not conversation_id and record.related_task_id:
                conversation_id = str(record.related_task_id)

            if not conversation_id:
                # Generate a deterministic UUID from the message_id
                # as a fallback when no conversation_id is available
                conversation_seed = str(record.message_id)
                conversation_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, conversation_seed))

            # Create a Message object using the correct field mappings
            return Message(
                message_id=str(record.message_id),
                conversation_id=conversation_id,
                sender_id=str(record.sender_id),
                recipient_id=(
                    str(record.receiver_id) if record.receiver_id else str(uuid.uuid4())
                ),
                message_type=record.message_type,
                content=content,
                in_reply_to=(
                    str(record.parent_message_id) if record.parent_message_id else None
                ),
                metadata=record.extra_data or {},
                created_at=record.created_at or datetime.utcnow(),
                task_id=str(record.related_task_id) if record.related_task_id else None,
                meeting_id=str(record.meeting_id) if record.meeting_id else None,
                context_vector=record.context_vector,
            )
        except Exception as e:
            self.logger.error(f"Error converting record to message: {str(e)}")
            # Return a minimal Message in case of error
            return Message(
                sender_id=str(uuid.uuid4()),
                recipient_id=str(uuid.uuid4()),
                message_type=MessageType.ALERT,
                content=f"Error retrieving message: {str(e)}",
            )

    async def _call_handler(self, handler: Callable, message: Message) -> None:
        """
        Call a handler function, supporting both async and sync handlers.

        Args:
            handler: Handler function to call
            message: Message to pass to the handler
        """
        if asyncio.iscoroutinefunction(handler):
            await handler(message)
        else:
            handler(message)


# Import needed SQLAlchemy function
from sqlalchemy import or_
