import uuid
import logging
from typing import Optional

from agents.communication.message import Message

# Assuming Message, ActivityCategory, ActivityLevel are available
# from agents.communication.message import Message
# from agents.logging.activity_logger import ActivityCategory, ActivityLevel

logger = logging.getLogger(__name__)


async def receive_message_logic(agent, message_id: uuid.UUID) -> Optional["Message"]:
    """
    Process a received message by fetching it via the Communication Protocol.
    Args:
        agent: The agent instance.
        message_id: UUID of the message to process
    Returns:
        The Message object if found and processed, None otherwise.
    """
    if not agent.protocol:
        logger.warning(
            f"Agent {agent.agent_id} has no Protocol initialized. Cannot receive message."
        )
        return None

    try:
        # Import Message directly if not passed or available via agent context
        from agents.communication.message import Message  # Direct import

        # Import enums for logging
        from agents.logging.activity_logger import ActivityCategory, ActivityLevel

        message = await agent.protocol.get_message(message_id)

        if not message:
            logger.warning(f"Message {message_id} not found via Protocol.")
            await agent.activity_logger.log_activity(
                activity_type="message_fetch_failed",
                description=f"Message {message_id} not found via Protocol for agent {agent.agent_id}",
                category=ActivityCategory.COMMUNICATION,
                level=ActivityLevel.WARNING,
                details={"message_id": str(message_id)},
            )
            return None

        await agent.activity_logger.log_communication(
            message_type=f"RECEIVED_{message.message_type.value}",
            sender_id=message.sender_id,  # This is already a string UUID from the Message model
            recipient_id=agent.agent_id,  # This is a UUID object, consider str(agent.agent_id)
            content_summary=(
                message.content[:100] + "..."
                if len(message.content) > 100
                else message.content
            ),
            message_id=message.message_id,  # This is already a UUID object
            metadata=message.metadata,
        )

        logger.info(
            f"Message {message.message_id} received and logged by agent {agent.agent_id}."
        )
        return message

    except Exception as e:
        logger.error(
            f"Error receiving message via Protocol for agent {agent.agent_id}: {str(e)}"
        )
        # Make sure ActivityLevel is imported or handle missing import
        from agents.logging.activity_logger import (
            ActivityLevel,
        )  # Ensure import if not already done

        await agent.activity_logger.log_error(
            error_type="ReceiveMessageProtocolError",
            description=f"Error processing message {message_id} via Protocol for agent {agent.agent_id}",
            exception=e,
            severity=ActivityLevel.ERROR,
            context={"message_id": str(message_id)},
        )
        return None
