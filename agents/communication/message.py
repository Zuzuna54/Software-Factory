"""
Message class with standardized structure for agent-to-agent communication.
"""

import enum
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union


class MessageType(enum.Enum):
    """
    Types of messages that can be exchanged between agents.

    - REQUEST: Ask another agent to do something
    - INFORM: Provide information or results
    - PROPOSE: Suggest a plan or design
    - CONFIRM: Express agreement on a plan or output
    - ALERT: Notify of a problem
    """

    REQUEST = "request"
    INFORM = "inform"
    PROPOSE = "propose"
    CONFIRM = "confirm"
    ALERT = "alert"


class Message:
    """
    Standardized message structure for agent-to-agent communication.

    Attributes:
        message_id: Unique identifier for the message
        conversation_id: Identifier for the conversation this message belongs to
        sender_id: Identifier of the agent sending the message
        recipient_id: Identifier of the agent receiving the message
        message_type: Type of message (REQUEST, INFORM, etc.)
        content: Main content of the message
        in_reply_to: ID of the message this is a reply to, if any
        metadata: Additional metadata about the message
        created_at: When the message was created
        task_id: Optional ID of a related task
        meeting_id: Optional ID of a related meeting
        context_vector: Optional vector embedding of the message content
    """

    def __init__(
        self,
        sender_id: str,
        recipient_id: str,
        message_type: MessageType,
        content: Union[str, Dict[str, Any]],
        conversation_id: Optional[str] = None,
        in_reply_to: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        message_id: Optional[str] = None,
        created_at: Optional[datetime] = None,
        task_id: Optional[str] = None,
        meeting_id: Optional[str] = None,
        context_vector: Optional[List[float]] = None,
    ):
        """
        Initialize a new message.

        Args:
            sender_id: ID of the agent sending the message
            recipient_id: ID of the agent receiving the message
            message_type: Type of message (REQUEST, INFORM, etc.)
            content: Main content of the message
            conversation_id: Optional ID for the conversation (generated if not provided)
            in_reply_to: Optional ID of the message this is replying to
            metadata: Optional additional metadata for the message
            message_id: Optional message ID (generated if not provided)
            created_at: Optional timestamp (current time if not provided)
            task_id: Optional ID of a related task
            meeting_id: Optional ID of a related meeting
            context_vector: Optional vector embedding of the message content
        """
        self.message_id = message_id or str(uuid.uuid4())
        self.conversation_id = conversation_id or str(uuid.uuid4())
        self.sender_id = sender_id
        self.recipient_id = recipient_id

        # Ensure message_type is a MessageType enum
        if isinstance(message_type, str):
            self.message_type = MessageType(message_type.lower())
        else:
            self.message_type = message_type

        self.content = content
        self.in_reply_to = in_reply_to
        self.metadata = metadata or {}
        self.created_at = created_at or datetime.utcnow()

        # Store new direct parameters
        self.task_id = task_id
        self.meeting_id = meeting_id
        self.context_vector = context_vector

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the message to a dictionary.

        Returns:
            Dictionary representation of the message
        """
        data = {
            "message_id": self.message_id,
            "conversation_id": self.conversation_id,
            "sender_id": self.sender_id,
            "recipient_id": self.recipient_id,
            "message_type": self.message_type.value,
            "content": self.content,
            "in_reply_to": self.in_reply_to,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "task_id": self.task_id,
            "meeting_id": self.meeting_id,
            "context_vector": self.context_vector,
        }
        # Filter out None values for cleaner output, especially for optional fields
        return {k: v for k, v in data.items() if v is not None}

    def to_json(self) -> str:
        """
        Convert the message to a JSON string.

        Returns:
            JSON string representation of the message
        """
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """
        Create a message from a dictionary.

        Args:
            data: Dictionary containing message data

        Returns:
            New Message instance
        """
        # Convert created_at from string to datetime if it exists
        if "created_at" in data and isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])

        return cls(
            message_id=data.get("message_id"),
            conversation_id=data.get("conversation_id"),
            sender_id=data["sender_id"],
            recipient_id=data["recipient_id"],
            message_type=data["message_type"],
            content=data["content"],
            in_reply_to=data.get("in_reply_to"),
            metadata=data.get("metadata"),
            created_at=data.get("created_at"),
            task_id=data.get("task_id"),
            meeting_id=data.get("meeting_id"),
            context_vector=data.get("context_vector"),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "Message":
        """
        Create a message from a JSON string.

        Args:
            json_str: JSON string containing message data

        Returns:
            New Message instance
        """
        return cls.from_dict(json.loads(json_str))

    def __str__(self) -> str:
        """String representation of the message."""
        return (
            f"Message(id={self.message_id}, "
            f"type={self.message_type.value}, "
            f"sender={self.sender_id}, "
            f"recipient={self.recipient_id})"
        )

    def __repr__(self) -> str:
        """Representation of the message."""
        return self.__str__()


class RequestMessage(Message):
    """
    Request message for asking another agent to do something.

    Additional attributes:
        action: The action being requested
        parameters: Parameters for the requested action
        priority: Priority of the request (1-5, with 5 being highest)
        deadline: Optional deadline for completing the request
    """

    def __init__(
        self,
        sender_id: str,
        recipient_id: str,
        action: str,
        parameters: Optional[Dict[str, Any]] = None,
        priority: int = 3,
        deadline: Optional[datetime] = None,
        **kwargs,
    ):
        """
        Initialize a request message.

        Args:
            sender_id: ID of the agent sending the message
            recipient_id: ID of the agent receiving the message
            action: The action being requested
            parameters: Parameters for the requested action
            priority: Priority of the request (1-5, with 5 being highest)
            deadline: Optional deadline for completing the request
            **kwargs: Additional arguments to pass to the Message constructor
        """
        # Construct content with request-specific fields
        content = {
            "action": action,
            "parameters": parameters or {},
            "priority": priority,
        }

        if deadline:
            content["deadline"] = deadline.isoformat()

        # Initialize base class
        super().__init__(
            sender_id=sender_id,
            recipient_id=recipient_id,
            message_type=MessageType.REQUEST,
            content=content,
            **kwargs,
        )


class InformMessage(Message):
    """
    Inform message for providing information or results.

    Additional attributes:
        information_type: Type of information being provided
        data: The actual information or results
        source: Source of the information
    """

    def __init__(
        self,
        sender_id: str,
        recipient_id: str,
        information_type: str,
        data: Any,
        source: Optional[str] = None,
        **kwargs,
    ):
        """
        Initialize an inform message.

        Args:
            sender_id: ID of the agent sending the message
            recipient_id: ID of the agent receiving the message
            information_type: Type of information being provided
            data: The actual information or results
            source: Source of the information
            **kwargs: Additional arguments to pass to the Message constructor
        """
        # Construct content with inform-specific fields
        content = {"information_type": information_type, "data": data}

        if source:
            content["source"] = source

        # Initialize base class
        super().__init__(
            sender_id=sender_id,
            recipient_id=recipient_id,
            message_type=MessageType.INFORM,
            content=content,
            **kwargs,
        )


class ProposeMessage(Message):
    """
    Propose message for suggesting a plan or design.

    Additional attributes:
        proposal_type: Type of proposal
        proposal: The actual proposal content
        alternatives: Alternative proposals if any
        reasoning: Reasoning behind the proposal
    """

    def __init__(
        self,
        sender_id: str,
        recipient_id: str,
        proposal_type: str,
        proposal: Dict[str, Any],
        alternatives: Optional[List[Dict[str, Any]]] = None,
        reasoning: Optional[str] = None,
        **kwargs,
    ):
        """
        Initialize a propose message.

        Args:
            sender_id: ID of the agent sending the message
            recipient_id: ID of the agent receiving the message
            proposal_type: Type of proposal
            proposal: The actual proposal content
            alternatives: Alternative proposals if any
            reasoning: Reasoning behind the proposal
            **kwargs: Additional arguments to pass to the Message constructor
        """
        # Construct content with propose-specific fields
        content = {"proposal_type": proposal_type, "proposal": proposal}

        if alternatives:
            content["alternatives"] = alternatives

        if reasoning:
            content["reasoning"] = reasoning

        # Initialize base class
        super().__init__(
            sender_id=sender_id,
            recipient_id=recipient_id,
            message_type=MessageType.PROPOSE,
            content=content,
            **kwargs,
        )


class ConfirmMessage(Message):
    """
    Confirm message for expressing agreement on a plan or output.

    Additional attributes:
        confirmation_type: Type of confirmation
        confirmed_item_id: ID of the item being confirmed
        comments: Optional comments on the confirmation
    """

    def __init__(
        self,
        sender_id: str,
        recipient_id: str,
        confirmation_type: str,
        confirmed_item_id: str,
        comments: Optional[str] = None,
        **kwargs,
    ):
        """
        Initialize a confirm message.

        Args:
            sender_id: ID of the agent sending the message
            recipient_id: ID of the agent receiving the message
            confirmation_type: Type of confirmation
            confirmed_item_id: ID of the item being confirmed
            comments: Optional comments on the confirmation
            **kwargs: Additional arguments to pass to the Message constructor
        """
        # Construct content with confirm-specific fields
        content = {
            "confirmation_type": confirmation_type,
            "confirmed_item_id": confirmed_item_id,
        }

        if comments:
            content["comments"] = comments

        # Initialize base class
        super().__init__(
            sender_id=sender_id,
            recipient_id=recipient_id,
            message_type=MessageType.CONFIRM,
            content=content,
            **kwargs,
        )


class AlertMessage(Message):
    """
    Alert message for notifying of a problem.

    Additional attributes:
        alert_type: Type of alert
        severity: Severity of the alert (1-5, with 5 being highest)
        details: Details of the alert
        suggested_actions: Suggested actions to address the problem
    """

    def __init__(
        self,
        sender_id: str,
        recipient_id: str,
        alert_type: str,
        severity: int,
        details: str,
        suggested_actions: Optional[List[str]] = None,
        **kwargs,
    ):
        """
        Initialize an alert message.

        Args:
            sender_id: ID of the agent sending the message
            recipient_id: ID of the agent receiving the message
            alert_type: Type of alert
            severity: Severity of the alert (1-5, with 5 being highest)
            details: Details of the alert
            suggested_actions: Suggested actions to address the problem
            **kwargs: Additional arguments to pass to the Message constructor
        """
        # Construct content with alert-specific fields
        content = {"alert_type": alert_type, "severity": severity, "details": details}

        if suggested_actions:
            content["suggested_actions"] = suggested_actions

        # Initialize base class
        super().__init__(
            sender_id=sender_id,
            recipient_id=recipient_id,
            message_type=MessageType.ALERT,
            content=content,
            **kwargs,
        )


# Factory methods for creating specific message types
def create_request(
    sender_id: str,
    recipient_id: str,
    action: str,
    parameters: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> RequestMessage:
    """Create a request message."""
    return RequestMessage(sender_id, recipient_id, action, parameters, **kwargs)


def create_inform(
    sender_id: str, recipient_id: str, information_type: str, data: Any, **kwargs
) -> InformMessage:
    """Create an inform message."""
    return InformMessage(sender_id, recipient_id, information_type, data, **kwargs)


def create_propose(
    sender_id: str,
    recipient_id: str,
    proposal_type: str,
    proposal: Dict[str, Any],
    **kwargs,
) -> ProposeMessage:
    """Create a propose message."""
    return ProposeMessage(sender_id, recipient_id, proposal_type, proposal, **kwargs)


def create_confirm(
    sender_id: str,
    recipient_id: str,
    confirmation_type: str,
    confirmed_item_id: str,
    **kwargs,
) -> ConfirmMessage:
    """Create a confirm message."""
    return ConfirmMessage(
        sender_id, recipient_id, confirmation_type, confirmed_item_id, **kwargs
    )


def create_alert(
    sender_id: str,
    recipient_id: str,
    alert_type: str,
    severity: int,
    details: str,
    **kwargs,
) -> AlertMessage:
    """Create an alert message."""
    return AlertMessage(
        sender_id, recipient_id, alert_type, severity, details, **kwargs
    )
