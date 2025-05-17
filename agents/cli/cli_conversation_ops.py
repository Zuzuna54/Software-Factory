"""
Conversation management operations for the CLI tool.

This module contains functions for creating, selecting, and managing
conversations between agents.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.sql import func

from agents.communication import Conversation
from infra.db.models.core import Conversation as ConversationModel, AgentMessage
from .cli_core import AgentCLI, logger
from .cli_utils import validate_uuid, format_uuid


async def create_conversation(
    cli: AgentCLI,
    conversation_id: Optional[str] = None,
    topic: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Create a new conversation in the database.

    Args:
        cli: The AgentCLI instance
        conversation_id: Optional conversation ID (generated if not provided)
        topic: Optional topic for the conversation
        metadata: Optional additional metadata for the conversation

    Returns:
        Conversation ID
    """
    # Validate conversation_id if provided
    if conversation_id:
        conversation_id = format_uuid(conversation_id)
    else:
        conversation_id = str(uuid.uuid4())

    # Create conversation in database
    async with cli.db_client.session() as session:
        # Check if conversation already exists
        if conversation_id:
            existing = await session.execute(
                select(ConversationModel).where(
                    ConversationModel.conversation_id == uuid.UUID(conversation_id)
                )
            )
            if existing.scalar_one_or_none():
                logger.info(f"Conversation already exists: {conversation_id}")
                # Set as current conversation
                cli.current_conversation_id = conversation_id
                return conversation_id

        # Create new conversation
        new_conversation = ConversationModel(
            conversation_id=uuid.UUID(conversation_id),
            topic=topic,
            extra_data=metadata,
            status="active",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(new_conversation)
        await session.commit()

    # Set as current conversation
    cli.current_conversation_id = conversation_id

    # Also create Communication Conversation object for protocol use
    if cli.protocol:
        conversation = Conversation(
            protocol=cli.protocol,
            conversation_id=conversation_id,
            topic=topic,
            metadata=metadata,
        )

    logger.info(f"Created conversation: {conversation_id}")
    return conversation_id


async def list_conversations(
    cli: AgentCLI, include_inactive: bool = False
) -> List[Dict[str, Any]]:
    """
    List all conversations from the database.

    Args:
        cli: The AgentCLI instance
        include_inactive: Whether to include inactive conversations

    Returns:
        List of conversation details as dictionaries
    """
    async with cli.db_client.session() as session:
        query = select(ConversationModel)
        if not include_inactive:
            query = query.where(ConversationModel.status == "active")

        result = await session.execute(query)
        conversations = result.scalars().all()

        return [
            {
                "conversation_id": str(conv.conversation_id),
                "topic": conv.topic,
                "created_at": conv.created_at.isoformat() if conv.created_at else None,
                "status": conv.status,
            }
            for conv in conversations
        ]


async def select_conversation(cli: AgentCLI, conversation_id: str) -> bool:
    """
    Select a conversation as the current conversation, verifying it exists in the database.

    Args:
        cli: The AgentCLI instance
        conversation_id: ID of the conversation to select

    Returns:
        True if the conversation was selected, False otherwise
    """
    # Validate and format the UUID
    try:
        formatted_id = format_uuid(conversation_id)
    except ValueError:
        logger.error(f"Invalid conversation ID format: {conversation_id}")
        return False

    # Check if conversation exists in database
    async with cli.db_client.session() as session:
        result = await session.execute(
            select(ConversationModel).where(
                ConversationModel.conversation_id == uuid.UUID(formatted_id)
            )
        )
        conversation = result.scalar_one_or_none()

        if not conversation:
            logger.error(f"Conversation not found: {formatted_id}")
            return False

        # Set as current conversation
        cli.current_conversation_id = formatted_id
        logger.info(f"Selected conversation: {formatted_id}")
        return True


async def get_conversation_summary(
    cli: AgentCLI, conversation_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Get a summary of a conversation from the database.

    Args:
        cli: The AgentCLI instance
        conversation_id: Optional conversation ID (current conversation if not provided)

    Returns:
        Dictionary with conversation summary information, or None if not found
    """
    conversation_id = conversation_id or cli.current_conversation_id

    if not conversation_id:
        logger.error("No conversation selected")
        return None

    try:
        formatted_id = format_uuid(conversation_id)
    except ValueError:
        logger.error(f"Invalid conversation ID format: {conversation_id}")
        return None

    async with cli.db_client.session() as session:
        # Get conversation details
        conv_result = await session.execute(
            select(ConversationModel).where(
                ConversationModel.conversation_id == uuid.UUID(formatted_id)
            )
        )
        conversation = conv_result.scalar_one_or_none()

        if not conversation:
            logger.error(f"Conversation not found: {formatted_id}")
            return None

        # Get message count
        msg_count_result = await session.execute(
            select(func.count(AgentMessage.message_id)).where(
                AgentMessage.conversation_id == uuid.UUID(formatted_id)
            )
        )
        message_count = msg_count_result.scalar_one()

        # Get participants info
        participants = []
        if conversation.participant_ids:
            for agent_id in conversation.participant_ids:
                agent_info = await cli.get_agent(str(agent_id))
                if agent_info:
                    participants.append(agent_info["name"])

        return {
            "conversation_id": formatted_id,
            "topic": conversation.topic,
            "created_at": (
                conversation.created_at.isoformat() if conversation.created_at else None
            ),
            "updated_at": (
                conversation.updated_at.isoformat() if conversation.updated_at else None
            ),
            "status": conversation.status,
            "message_count": message_count,
            "participants": participants,
            "extra_data": conversation.extra_data,
        }


async def get_conversation_messages(
    cli: AgentCLI,
    conversation_id: Optional[str] = None,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """
    Get messages in a conversation from the database.

    Args:
        cli: The AgentCLI instance
        conversation_id: Optional conversation ID (current conversation if not provided)
        limit: Maximum number of messages to retrieve

    Returns:
        List of messages in the conversation
    """
    conversation_id = conversation_id or cli.current_conversation_id

    if not conversation_id:
        logger.error("No conversation selected")
        return []

    try:
        formatted_id = format_uuid(conversation_id)
    except ValueError:
        logger.error(f"Invalid conversation ID format: {conversation_id}")
        return []

    # Use protocol to get messages since it handles properly formatting them
    # Protocol now uses the database under the hood
    return await cli.protocol.get_conversation_messages(
        conversation_id=formatted_id,
        limit=limit,
    )


async def update_conversation(
    cli: AgentCLI,
    conversation_id: str,
    topic: Optional[str] = None,
    status: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Update conversation properties in the database.

    Args:
        cli: The AgentCLI instance
        conversation_id: ID of the conversation to update
        topic: New topic for the conversation (if provided)
        status: New status for the conversation (if provided)
        metadata: New or updated metadata (if provided)

    Returns:
        True if the conversation was updated, False otherwise
    """
    try:
        formatted_id = format_uuid(conversation_id)
    except ValueError:
        logger.error(f"Invalid conversation ID format: {conversation_id}")
        return False

    async with cli.db_client.session() as session:
        result = await session.execute(
            select(ConversationModel).where(
                ConversationModel.conversation_id == uuid.UUID(formatted_id)
            )
        )
        conversation = result.scalar_one_or_none()

        if not conversation:
            logger.error(f"Conversation not found: {formatted_id}")
            return False

        # Update fields if provided
        if topic is not None:
            conversation.topic = topic

        if status is not None:
            conversation.status = status

        if metadata is not None:
            # Merge with existing metadata if present
            if conversation.extra_data:
                conversation.extra_data.update(metadata)
            else:
                conversation.extra_data = metadata

        conversation.updated_at = datetime.utcnow()
        await session.commit()

        logger.info(f"Updated conversation: {formatted_id}")
        return True


async def delete_conversation(cli: AgentCLI, conversation_id: str) -> bool:
    """
    Mark a conversation as inactive in the database.

    Args:
        cli: The AgentCLI instance
        conversation_id: ID of the conversation to delete

    Returns:
        True if the conversation was deleted, False otherwise
    """
    try:
        formatted_id = format_uuid(conversation_id)
    except ValueError:
        logger.error(f"Invalid conversation ID format: {conversation_id}")
        return False

    async with cli.db_client.session() as session:
        result = await session.execute(
            select(ConversationModel).where(
                ConversationModel.conversation_id == uuid.UUID(formatted_id)
            )
        )
        conversation = result.scalar_one_or_none()

        if not conversation:
            logger.error(f"Conversation not found: {formatted_id}")
            return False

        # Mark as inactive instead of deleting
        conversation.status = "inactive"
        conversation.updated_at = datetime.utcnow()
        await session.commit()

        # Clear current conversation if deleted
        if cli.current_conversation_id == formatted_id:
            cli.current_conversation_id = None

        logger.info(f"Deleted conversation: {formatted_id}")
        return True
