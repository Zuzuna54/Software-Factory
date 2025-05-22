import uuid
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from agents.communication.message import Message, MessageType  # Direct import
from agents.logging.activity_logger import ActivityLevel  # Added import

logger = logging.getLogger(__name__)


async def send_message_logic(
    agent,
    receiver_id: uuid.UUID,
    content: str,
    message_type: str = "INFORM",
    task_id: Optional[uuid.UUID] = None,
    meeting_id: Optional[uuid.UUID] = None,
    parent_message_id: Optional[uuid.UUID] = None,
    context_vector=None,  # Type hint could be List[float] or similar depending on usage
    conversation_id: Optional[uuid.UUID] = None,
    extra_data: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """
    Send a message to another agent using the Communication Protocol.
    Args:
        agent: The agent instance.
        receiver_id: UUID of the receiving agent
        content: Message content
        message_type: Type of message (REQUEST, INFORM, PROPOSE, CONFIRM, ALERT)
        task_id: Optional ID of related task
        meeting_id: Optional ID of related meeting
        parent_message_id: Optional ID of parent message if this is a reply
        context_vector: Optional vector embedding of message content
        conversation_id: Optional ID of the conversation
        extra_data: Optional additional metadata for the message
    Returns:
        UUID of the created message if successful, None otherwise.
    """
    if not agent.protocol:
        logger.warning(
            f"Agent {agent.agent_id} has no Protocol initialized. Cannot send message."
        )
        return None

    try:
        # Dynamically import MessageType from agent's context if possible or ensure it's passed/available
        # This assumes agent.protocol or agent itself can provide MessageType or it's globally imported
        # For simplicity, assuming MessageType is accessible via agent.protocol.MessageType or similar
        # Or it's imported directly in this file: from agents.communication.message import MessageType, Message
        from agents.communication.message import Message, MessageType  # Direct import

        try:
            msg_type_enum = MessageType[message_type.upper()]
        except KeyError:
            logger.error(
                f"Invalid message type string: {message_type}. Defaulting to INFORM."
            )
            msg_type_enum = MessageType.INFORM

        message_to_send = Message(
            message_id=uuid.uuid4(),
            sender_id=str(agent.agent_id),
            recipient_id=str(receiver_id),
            message_type=msg_type_enum,
            content=content,
            conversation_id=conversation_id if conversation_id else None,
            in_reply_to=parent_message_id,
            metadata=extra_data or {},
            task_id=task_id,
            meeting_id=meeting_id,
            created_at=datetime.now(),  # Consider utcnow() if consistency is needed
            context_vector=context_vector if context_vector else None,
        )

        success = await agent.protocol.send_message(message_to_send)

        if success:
            await agent.activity_logger.log_communication(
                message_type=message_to_send.message_type.value,
                sender_id=agent.agent_id,
                recipient_id=receiver_id,
                content_summary=(
                    content[:100] + "..." if len(content) > 100 else content
                ),
                message_id=message_to_send.message_id,
                metadata=message_to_send.metadata,
            )
            logger.info(
                f"Message sent via Protocol: {message_to_send.message_id} from {agent.agent_id} to {receiver_id}"
            )
            return str(message_to_send.message_id)
        else:
            logger.error(
                f"Protocol failed to send message from {agent.agent_id} to {receiver_id}"
            )
            # Optionally, log this failure with activity_logger.log_error
            # await agent.activity_logger.log_error(...)
            return None

    except Exception as e:
        logger.error(
            f"Error during send_message via Protocol for agent {agent.agent_id}: {str(e)}"
        )
        await agent.activity_logger.log_error(
            error_type="SendMessageProtocolError",
            description=f"Failed to send message from {agent.agent_id} to {receiver_id}",
            exception=e,
            context={"receiver_id": str(receiver_id), "message_type": message_type},
            severity=ActivityLevel.ERROR,  # Now using Enum
        )
        return None
