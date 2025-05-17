"""
Conversation management operations for the CLI tool.

This module contains functions for creating, selecting, and managing
conversations between agents.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
import json
import asyncio

from sqlalchemy import select
from sqlalchemy.sql import func

from agents.communication import Conversation
from infra.db.models.core import Conversation as ConversationModel, AgentMessage
from agents.cli.cli_core import AgentCLI
from agents.cli.cli_utils import logger, validate_uuid, format_uuid, is_valid_uuid


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


async def visualize_conversation(
    cli: AgentCLI,
    conversation_id: Optional[str] = None,
    format: str = "text",
    include_timestamps: bool = True,
) -> Dict[str, Any]:
    """
    Generate a conversation visualization.

    Args:
        cli: The AgentCLI instance
        conversation_id: Optional conversation ID (current conversation if not provided)
        format: Output format (text, json, mermaid)
        include_timestamps: Whether to include timestamps in the visualization

    Returns:
        Dictionary with visualization results
    """
    try:
        conversation_id = conversation_id or cli.current_conversation_id
        if not conversation_id:
            logger.error("No conversation selected")
            return {"status": "error", "error": "No conversation selected"}

        try:
            formatted_id = format_uuid(conversation_id)
        except ValueError:
            logger.error(f"Invalid conversation ID format: {conversation_id}")
            return {
                "status": "error",
                "error": f"Invalid conversation ID format: {conversation_id}",
            }

        # Get conversation details
        summary = await get_conversation_summary(cli, formatted_id)
        if not summary:
            return {
                "status": "error",
                "error": f"Conversation not found: {formatted_id}",
            }

        # Get all messages
        messages = await get_conversation_messages(cli, formatted_id, limit=100)
        if not messages:
            return {
                "status": "success",
                "message": "No messages in conversation",
                "visualization": "Empty conversation",
                "format": format,
            }

        # Create visualization based on format
        if format == "text":
            visualization = f"Conversation: {summary['conversation_id']}\n"
            visualization += f"Topic: {summary['topic']}\n"
            visualization += f"Status: {summary['status']}\n"
            visualization += f"Message count: {summary['message_count']}\n\n"

            for msg in messages:
                timestamp = f"[{msg['timestamp']}] " if include_timestamps else ""
                visualization += (
                    f"{timestamp}{msg['sender']} -> {msg['recipient']}: {msg['type']}\n"
                )

                content = msg.get("content")
                if isinstance(content, dict):
                    for key, value in content.items():
                        visualization += f"  {key}: {value}\n"
                elif content:
                    visualization += f"  {content}\n"

                visualization += "\n"

        elif format == "json":
            visualization = {
                "conversation_id": summary["conversation_id"],
                "topic": summary["topic"],
                "status": summary["status"],
                "message_count": summary["message_count"],
                "messages": [
                    {
                        "id": msg["id"],
                        "timestamp": msg["timestamp"] if include_timestamps else None,
                        "sender": msg["sender"],
                        "recipient": msg["recipient"],
                        "type": msg["type"],
                        "content": msg.get("content"),
                    }
                    for msg in messages
                ],
            }

        elif format == "mermaid":
            # Create a Mermaid sequence diagram
            visualization = "sequenceDiagram\n"

            # Identify all participants
            participants = set()
            for msg in messages:
                participants.add(msg["sender"])
                if msg["recipient"]:
                    participants.add(msg["recipient"])

            # Add participants
            for participant in participants:
                visualization += f"    participant {participant}\n"

            # Add messages
            for msg in messages:
                timestamp = f"[{msg['timestamp']}]" if include_timestamps else ""
                message_text = f"{msg['type']}: "

                content = msg.get("content")
                if isinstance(content, dict):
                    message_text += ", ".join(f"{k}={v}" for k, v in content.items())
                elif content:
                    # Escape any special characters that might break the diagram
                    message_text += str(content).replace('"', '\\"')

                # Truncate if too long
                if len(message_text) > 50:
                    message_text = message_text[:47] + "..."

                # Add the message arrow
                if msg["recipient"]:
                    visualization += f"    {msg['sender']}->>+{msg['recipient']}: {message_text} {timestamp}\n"
                else:
                    visualization += f"    {msg['sender']}-->>+{msg['sender']}: {message_text} {timestamp}\n"

        else:
            return {
                "status": "error",
                "error": f"Invalid format: {format}. Must be one of: text, json, mermaid",
            }

        return {
            "status": "success",
            "conversation_id": formatted_id,
            "topic": summary["topic"],
            "message_count": len(messages),
            "format": format,
            "visualization": visualization,
        }
    except Exception as e:
        logger.error(f"Error visualizing conversation: {str(e)}")
        return {"status": "error", "error": str(e)}


async def inject_message(
    cli: AgentCLI,
    conversation_id: str,
    sender_id: str,
    recipient_id: str,
    message_type: str,
    content: Any,
    timestamp: Optional[str] = None,
    parent_message_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Inject a message into a conversation.

    Args:
        cli: The AgentCLI instance
        conversation_id: Conversation ID
        sender_id: Sender agent ID
        recipient_id: Recipient agent ID
        message_type: Message type
        content: Message content
        timestamp: Optional timestamp (defaults to current time)
        parent_message_id: Optional parent message ID

    Returns:
        Dictionary with injected message details
    """
    try:
        # Format IDs
        try:
            formatted_conv_id = format_uuid(conversation_id)
            formatted_sender_id = format_uuid(sender_id)
            formatted_recipient_id = format_uuid(recipient_id)
            formatted_parent_id = (
                format_uuid(parent_message_id) if parent_message_id else None
            )
        except ValueError as e:
            return {"status": "error", "error": f"Invalid UUID format: {str(e)}"}

        # Check if conversation exists
        async with cli.db_client.session() as session:
            result = await session.execute(
                select(ConversationModel).where(
                    ConversationModel.conversation_id == uuid.UUID(formatted_conv_id)
                )
            )
            conversation = result.scalar_one_or_none()

            if not conversation:
                return {
                    "status": "error",
                    "error": f"Conversation not found: {formatted_conv_id}",
                }

            # Create timestamp if not provided
            message_timestamp = (
                datetime.fromisoformat(timestamp) if timestamp else datetime.utcnow()
            )

            # Create the message
            message = AgentMessage(
                message_id=uuid.uuid4(),
                sender_id=uuid.UUID(formatted_sender_id),
                receiver_id=uuid.UUID(formatted_recipient_id),
                conversation_id=uuid.UUID(formatted_conv_id),
                content=json.dumps(content) if isinstance(content, dict) else content,
                message_type=message_type,
                created_at=message_timestamp,
                parent_message_id=(
                    uuid.UUID(formatted_parent_id) if formatted_parent_id else None
                ),
                extra_data={"injected": True, "conversation_id": formatted_conv_id},
            )

            session.add(message)
            await session.commit()

            # Update conversation with participants if needed
            if conversation.participant_ids is None:
                conversation.participant_ids = []

            if uuid.UUID(formatted_sender_id) not in conversation.participant_ids:
                conversation.participant_ids.append(uuid.UUID(formatted_sender_id))

            if uuid.UUID(formatted_recipient_id) not in conversation.participant_ids:
                conversation.participant_ids.append(uuid.UUID(formatted_recipient_id))

            conversation.updated_at = datetime.utcnow()
            await session.commit()

        logger.info(f"Injected message into conversation: {formatted_conv_id}")

        return {
            "status": "success",
            "message_id": str(message.message_id),
            "conversation_id": formatted_conv_id,
            "sender_id": formatted_sender_id,
            "recipient_id": formatted_recipient_id,
            "message_type": message_type,
            "timestamp": message_timestamp.isoformat(),
            "parent_message_id": formatted_parent_id,
        }
    except Exception as e:
        logger.error(f"Error injecting message: {str(e)}")
        return {"status": "error", "error": str(e)}


async def simulate_conversation_failure(
    cli: AgentCLI, conversation_id: str, failure_type: str, recover: bool = True
) -> Dict[str, Any]:
    """
    Simulate a conversation failure for testing error handling.

    Args:
        cli: The AgentCLI instance
        conversation_id: Conversation ID
        failure_type: Type of failure to simulate
        recover: Whether to automatically recover the conversation

    Returns:
        Dictionary with simulation results
    """
    try:
        # Format ID
        try:
            formatted_id = format_uuid(conversation_id)
        except ValueError:
            return {
                "status": "error",
                "error": f"Invalid conversation ID format: {conversation_id}",
            }

        # Check if conversation exists
        async with cli.db_client.session() as session:
            result = await session.execute(
                select(ConversationModel).where(
                    ConversationModel.conversation_id == uuid.UUID(formatted_id)
                )
            )
            conversation = result.scalar_one_or_none()

            if not conversation:
                return {
                    "status": "error",
                    "error": f"Conversation not found: {formatted_id}",
                }

            # Validate failure type
            valid_failure_types = [
                "timeout",
                "message_loss",
                "protocol_error",
                "agent_disconnect",
                "database_error",
            ]
            if failure_type not in valid_failure_types:
                return {
                    "status": "error",
                    "error": f"Invalid failure type: {failure_type}. Valid types: {', '.join(valid_failure_types)}",
                }

            # Get previous status
            previous_status = conversation.status

            # Set error message based on type
            error_messages = {
                "timeout": "Simulated timeout: Conversation response timed out after waiting 30 seconds",
                "message_loss": "Simulated message loss: Message delivery confirmation not received",
                "protocol_error": "Simulated protocol error: Invalid message format received",
                "agent_disconnect": "Simulated agent disconnect: Agent unexpectedly terminated connection",
                "database_error": "Simulated database error: Transaction failed due to constraint violation",
            }

            error_message = error_messages.get(failure_type)

            # Update conversation status to reflect error
            conversation.status = "error"
            conversation.extra_data = {
                **(conversation.extra_data or {}),
                "last_error": {
                    "type": failure_type,
                    "message": error_message,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            }

            # Create an error message in the conversation
            error_msg = AgentMessage(
                message_id=uuid.uuid4(),
                sender_id=uuid.UUID(
                    formatted_id
                ),  # Use conversation ID as sender for system messages
                receiver_id=None,
                conversation_id=uuid.UUID(formatted_id),
                content=error_message,
                message_type="system_error",
                created_at=datetime.utcnow(),
                extra_data={
                    "error_type": failure_type,
                    "simulated": True,
                    "conversation_id": formatted_id,
                },
            )

            session.add(error_msg)
            await session.commit()

            # Recover if requested
            if recover:
                await asyncio.sleep(2)  # Simulate recovery time

                conversation.status = previous_status
                conversation.extra_data = {
                    **(conversation.extra_data or {}),
                    "recovery": {
                        "timestamp": datetime.utcnow().isoformat(),
                        "recovered_from": failure_type,
                    },
                }

                # Create a recovery message
                recovery_msg = AgentMessage(
                    message_id=uuid.uuid4(),
                    sender_id=uuid.UUID(
                        formatted_id
                    ),  # Use conversation ID as sender for system messages
                    receiver_id=None,
                    conversation_id=uuid.UUID(formatted_id),
                    content=f"Conversation recovered from {failure_type} error",
                    message_type="system_info",
                    created_at=datetime.utcnow(),
                    extra_data={
                        "recovery_from": failure_type,
                        "simulated": True,
                        "conversation_id": formatted_id,
                    },
                )

                session.add(recovery_msg)
                await session.commit()

        return {
            "status": "success",
            "conversation_id": formatted_id,
            "failure_type": failure_type,
            "error_message": error_message,
            "recovered": recover,
            "recovery_time_ms": 2000 if recover else None,
            "current_status": previous_status if recover else "error",
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error simulating conversation failure: {str(e)}")
        return {"status": "error", "error": str(e)}


async def export_conversation(
    cli: AgentCLI,
    conversation_id: str,
    format: str = "json",
    output_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Export a conversation to a file.

    Args:
        cli: The AgentCLI instance
        conversation_id: Conversation ID
        format: Export format (json, markdown, html, csv)
        output_path: Optional output file path

    Returns:
        Dictionary with export results
    """
    try:
        # Format ID
        try:
            formatted_id = format_uuid(conversation_id)
        except ValueError:
            return {
                "status": "error",
                "error": f"Invalid conversation ID format: {conversation_id}",
            }

        # Get conversation details
        summary = await get_conversation_summary(cli, formatted_id)
        if not summary:
            return {
                "status": "error",
                "error": f"Conversation not found: {formatted_id}",
            }

        # Get all messages
        messages = await get_conversation_messages(cli, formatted_id, limit=1000)

        # Validate format
        valid_formats = ["json", "markdown", "html", "csv"]
        if format not in valid_formats:
            return {
                "status": "error",
                "error": f"Invalid format: {format}. Valid formats: {', '.join(valid_formats)}",
            }

        # Generate default output path if not provided
        if not output_path:
            topic_slug = (
                summary["topic"].lower().replace(" ", "_")[:30]
                if summary["topic"]
                else "conversation"
            )
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            output_path = f"./conversation_{topic_slug}_{timestamp}.{format}"

        # Generate content based on format
        if format == "json":
            content = {
                "conversation_id": summary["conversation_id"],
                "topic": summary["topic"],
                "created_at": summary["created_at"],
                "updated_at": summary["updated_at"],
                "status": summary["status"],
                "participants": summary["participants"],
                "message_count": len(messages),
                "messages": messages,
            }
            exported_content = json.dumps(content, indent=2)

        elif format == "markdown":
            content = f"# Conversation: {summary['topic']}\n\n"
            content += f"**ID:** {summary['conversation_id']}  \n"
            content += f"**Created:** {summary['created_at']}  \n"
            content += f"**Status:** {summary['status']}  \n"
            content += f"**Participants:** {', '.join(summary['participants'])}  \n\n"
            content += f"## Messages ({len(messages)})\n\n"

            for msg in messages:
                content += (
                    f"### {msg['timestamp']} - {msg['sender']} → {msg['recipient']}\n\n"
                )
                content += f"**Type:** {msg['type']}  \n"

                msg_content = msg.get("content")
                if isinstance(msg_content, dict):
                    content += "**Content:**\n\n```json\n"
                    content += json.dumps(msg_content, indent=2)
                    content += "\n```\n\n"
                else:
                    content += f"**Content:** {msg_content}\n\n"

                content += "---\n\n"

            exported_content = content

        elif format == "html":
            content = f"<!DOCTYPE html>\n<html>\n<head>\n<title>Conversation: {summary['topic']}</title>\n"
            content += "<style>\n"
            content += "body { font-family: Arial, sans-serif; margin: 20px; }\n"
            content += "h1 { color: #333; }\n"
            content += (
                ".meta { background: #f5f5f5; padding: 10px; border-radius: 5px; }\n"
            )
            content += ".message { margin-bottom: 20px; border-bottom: 1px solid #ddd; padding-bottom: 10px; }\n"
            content += ".sender { font-weight: bold; }\n"
            content += ".time { color: #666; font-size: 0.8em; }\n"
            content += ".content { white-space: pre-wrap; }\n"
            content += "</style>\n</head>\n<body>\n"

            content += f"<h1>Conversation: {summary['topic']}</h1>\n"
            content += "<div class='meta'>\n"
            content += f"<p><strong>ID:</strong> {summary['conversation_id']}</p>\n"
            content += f"<p><strong>Created:</strong> {summary['created_at']}</p>\n"
            content += f"<p><strong>Status:</strong> {summary['status']}</p>\n"
            content += f"<p><strong>Participants:</strong> {', '.join(summary['participants'])}</p>\n"
            content += "</div>\n"

            content += f"<h2>Messages ({len(messages)})</h2>\n"

            for msg in messages:
                content += "<div class='message'>\n"
                content += (
                    f"<p class='sender'>{msg['sender']} → {msg['recipient']}</p>\n"
                )
                content += (
                    f"<p class='time'>{msg['timestamp']} | Type: {msg['type']}</p>\n"
                )

                msg_content = msg.get("content")
                if isinstance(msg_content, dict):
                    content += "<pre class='content'>"
                    content += json.dumps(msg_content, indent=2)
                    content += "</pre>\n"
                else:
                    content += f"<p class='content'>{msg_content}</p>\n"

                content += "</div>\n"

            content += "</body>\n</html>"
            exported_content = content

        elif format == "csv":
            import csv
            from io import StringIO

            # Create CSV content
            output = StringIO()
            writer = csv.writer(output)

            # Write header
            writer.writerow(["timestamp", "sender", "recipient", "type", "content"])

            # Write messages
            for msg in messages:
                msg_content = msg.get("content")
                if isinstance(msg_content, dict):
                    msg_content = json.dumps(msg_content)

                writer.writerow(
                    [
                        msg["timestamp"],
                        msg["sender"],
                        msg["recipient"],
                        msg["type"],
                        msg_content,
                    ]
                )

            exported_content = output.getvalue()
            output.close()

        # Write to file
        with open(output_path, "w") as f:
            f.write(exported_content)

        return {
            "status": "success",
            "conversation_id": formatted_id,
            "format": format,
            "message_count": len(messages),
            "output_path": output_path,
            "file_size_bytes": len(exported_content),
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error exporting conversation: {str(e)}")
        return {"status": "error", "error": str(e)}
