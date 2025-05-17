"""
Message operations for the CLI tool.

This module contains functions for creating and sending messages
between agents in different formats.
"""

from typing import Any, Dict, List, Optional, Union

from agents.communication import (
    Message,
    MessageType,
    create_request,
    create_inform,
    create_propose,
    create_confirm,
    create_alert,
)
from .cli_core import AgentCLI, logger


async def send_message(
    cli: AgentCLI,
    sender_id: str,
    recipient_id: str,
    message_type: MessageType,
    content: Dict[str, Any],
    conversation_id: Optional[str] = None,
    in_reply_to: Optional[str] = None,
) -> Optional[Message]:
    """
    Send a message.

    Args:
        cli: The AgentCLI instance
        sender_id: ID of the agent sending the message
        recipient_id: ID of the agent receiving the message
        message_type: Type of message (REQUEST, INFORM, etc.)
        content: Message content
        conversation_id: Optional conversation ID (current conversation if not provided)
        in_reply_to: Optional ID of the message this is replying to

    Returns:
        The message if sent successfully, None otherwise
    """
    # Check if sender exists
    if sender_id not in cli.agents:
        logger.error(f"Sender agent not found: {sender_id}")
        return None

    # Check if recipient exists
    if recipient_id not in cli.agents:
        logger.error(f"Recipient agent not found: {recipient_id}")
        return None

    # Determine conversation
    if conversation_id:
        # Use specified conversation
        if conversation_id not in cli.conversations:
            logger.error(f"Conversation not found: {conversation_id}")
            return None
        conversation = cli.conversations[conversation_id]
    elif cli.current_conversation_id:
        # Use current conversation
        conversation = cli.conversations[cli.current_conversation_id]
    else:
        # Create a new conversation
        from .cli_conversation_ops import create_conversation

        conversation_id = create_conversation(
            cli, topic=f"Conversation between {sender_id} and {recipient_id}"
        )
        conversation = cli.conversations[conversation_id]

    # Create message
    message = Message(
        sender_id=sender_id,
        recipient_id=recipient_id,
        message_type=message_type,
        content=content,
        conversation_id=conversation.conversation_id,
        in_reply_to=in_reply_to,
    )

    # Send through conversation
    success = await conversation.add_message(message)

    if success:
        logger.info(f"Message sent: {message.message_id}")
        return message

    logger.error("Failed to send message")
    return None


async def send_request(
    cli: AgentCLI,
    sender_id: str,
    recipient_id: str,
    action: str,
    parameters: Optional[Dict[str, Any]] = None,
    priority: int = 3,
    **kwargs,
) -> Optional[Message]:
    """
    Send a request message.

    Args:
        cli: The AgentCLI instance
        sender_id: ID of the agent sending the message
        recipient_id: ID of the agent receiving the message
        action: The action being requested
        parameters: Parameters for the requested action
        priority: Priority of the request (1-5, with 5 being highest)
        **kwargs: Additional message arguments

    Returns:
        The message if sent successfully, None otherwise
    """
    message = create_request(
        sender_id=sender_id,
        recipient_id=recipient_id,
        action=action,
        parameters=parameters,
        priority=priority,
        **kwargs,
    )

    if cli.current_conversation:
        success = await cli.current_conversation.add_message(message)
        return message if success else None

    success = await cli.protocol.send_message(message)
    return message if success else None


async def send_inform(
    cli: AgentCLI,
    sender_id: str,
    recipient_id: str,
    information_type: str,
    data: Any,
    **kwargs,
) -> Optional[Message]:
    """
    Send an inform message.

    Args:
        cli: The AgentCLI instance
        sender_id: ID of the agent sending the message
        recipient_id: ID of the agent receiving the message
        information_type: Type of information being provided
        data: The actual information or results
        **kwargs: Additional message arguments

    Returns:
        The message if sent successfully, None otherwise
    """
    message = create_inform(
        sender_id=sender_id,
        recipient_id=recipient_id,
        information_type=information_type,
        data=data,
        **kwargs,
    )

    if cli.current_conversation:
        success = await cli.current_conversation.add_message(message)
        return message if success else None

    success = await cli.protocol.send_message(message)
    return message if success else None


async def send_propose(
    cli: AgentCLI,
    sender_id: str,
    recipient_id: str,
    proposal_type: str,
    proposal: Dict[str, Any],
    alternatives: Optional[List[Dict[str, Any]]] = None,
    reasoning: Optional[str] = None,
    **kwargs,
) -> Optional[Message]:
    """
    Send a propose message.

    Args:
        cli: The AgentCLI instance
        sender_id: ID of the agent sending the message
        recipient_id: ID of the agent receiving the message
        proposal_type: Type of proposal
        proposal: The actual proposal content
        alternatives: Alternative proposals if any
        reasoning: Reasoning behind the proposal
        **kwargs: Additional message arguments

    Returns:
        The message if sent successfully, None otherwise
    """
    message = create_propose(
        sender_id=sender_id,
        recipient_id=recipient_id,
        proposal_type=proposal_type,
        proposal=proposal,
        alternatives=alternatives,
        reasoning=reasoning,
        **kwargs,
    )

    if cli.current_conversation:
        success = await cli.current_conversation.add_message(message)
        return message if success else None

    success = await cli.protocol.send_message(message)
    return message if success else None


async def send_confirm(
    cli: AgentCLI,
    sender_id: str,
    recipient_id: str,
    confirmation_type: str,
    confirmed_item_id: str,
    comments: Optional[str] = None,
    **kwargs,
) -> Optional[Message]:
    """
    Send a confirm message.

    Args:
        cli: The AgentCLI instance
        sender_id: ID of the agent sending the message
        recipient_id: ID of the agent receiving the message
        confirmation_type: Type of confirmation
        confirmed_item_id: ID of the item being confirmed
        comments: Optional comments on the confirmation
        **kwargs: Additional message arguments

    Returns:
        The message if sent successfully, None otherwise
    """
    message = create_confirm(
        sender_id=sender_id,
        recipient_id=recipient_id,
        confirmation_type=confirmation_type,
        confirmed_item_id=confirmed_item_id,
        comments=comments,
        **kwargs,
    )

    if cli.current_conversation:
        success = await cli.current_conversation.add_message(message)
        return message if success else None

    success = await cli.protocol.send_message(message)
    return message if success else None


async def send_alert(
    cli: AgentCLI,
    sender_id: str,
    recipient_id: str,
    alert_type: str,
    severity: int,
    details: str,
    suggested_actions: Optional[List[str]] = None,
    **kwargs,
) -> Optional[Message]:
    """
    Send an alert message.

    Args:
        cli: The AgentCLI instance
        sender_id: ID of the agent sending the message
        recipient_id: ID of the agent receiving the message
        alert_type: Type of alert
        severity: Severity of the alert (1-5, with 5 being highest)
        details: Details of the alert
        suggested_actions: Suggested actions to address the problem
        **kwargs: Additional message arguments

    Returns:
        The message if sent successfully, None otherwise
    """
    message = create_alert(
        sender_id=sender_id,
        recipient_id=recipient_id,
        alert_type=alert_type,
        severity=severity,
        details=details,
        suggested_actions=suggested_actions,
        **kwargs,
    )

    if cli.current_conversation:
        success = await cli.current_conversation.add_message(message)
        return message if success else None

    success = await cli.protocol.send_message(message)
    return message if success else None
