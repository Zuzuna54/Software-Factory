"""
Protocol class for message validation, routing, and persistence.
"""

import asyncio
import logging
import uuid
import json
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set, Type, Union, cast

from sqlalchemy import select, func, desc, insert, text
from sqlalchemy.ext.asyncio import AsyncSession

from infra.db.models import AgentMessage, Agent
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

    def register_agent(
        self, agent_id: str, agent_type: str = "test", agent_name: str = "Test Agent"
    ) -> None:
        """
        Register an agent with the protocol.

        Args:
            agent_id: ID of the agent to register
            agent_type: Type of the agent
            agent_name: Name of the agent
        """
        self.registered_agents.add(agent_id)
        self.logger.info(f"Agent {agent_id} registered with the protocol")

        # Create a record in the agents table using SQLAlchemy ORM
        try:
            from infra.db.models import Agent

            async def _create_agent():
                try:
                    # Create Agent instance with the updated database schema fields
                    agent = Agent(
                        agent_id=uuid.UUID(agent_id),
                        agent_type=agent_type,
                        agent_name=agent_name,
                        agent_role=agent_type,  # Use agent_type as role by default
                        capabilities={
                            "capabilities": []
                        },  # JSONB format for capabilities
                        status="active",
                        system_prompt=f"You are {agent_name}, a {agent_type} agent.",
                        extra_data={},
                    )

                    async with self.db_client.transaction() as session:
                        # Check if agent already exists
                        stmt = select(Agent).where(
                            Agent.agent_id == uuid.UUID(agent_id)
                        )
                        result = await session.execute(stmt)
                        existing_agent = result.scalar_one_or_none()

                        if not existing_agent:
                            session.add(agent)
                            self.logger.info(
                                f"Agent {agent_id} record created in database"
                            )
                        else:
                            self.logger.info(
                                f"Agent {agent_id} already exists in database"
                            )
                except Exception as inner_e:
                    self.logger.error(f"Error in _create_agent: {str(inner_e)}")

            # Since register_agent is not async, we need to create a task to run the async code
            asyncio.create_task(_create_agent())
        except Exception as e:
            self.logger.error(f"Error creating agent {agent_id} in database: {str(e)}")

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

            # Store the conversation_id in the extra_data field
            # so we can retrieve messages by conversation
            metadata = message.metadata.copy() if message.metadata else {}
            metadata["conversation_id"] = message.conversation_id

            # Create a new AgentMessage record - map to existing columns
            # Omit related_task_id to avoid foreign key constraint violation
            agent_message = AgentMessage(
                message_id=uuid.UUID(message.message_id),
                sender_id=uuid.UUID(message.sender_id),
                receiver_id=uuid.UUID(message.recipient_id),  # Use receiver_id field
                message_type=message.message_type.value,
                content=content,
                parent_message_id=(
                    uuid.UUID(message.in_reply_to) if message.in_reply_to else None
                ),
                extra_data=metadata,
            )

            async with self.db_client.transaction() as session:
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
