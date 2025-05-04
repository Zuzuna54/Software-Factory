# agents/communication/protocol.py

import json
import logging
from enum import Enum
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field, asdict
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Standardized message types (speech acts) for agent-to-agent communication."""

    REQUEST = "REQUEST"  # Ask another agent to perform an action
    INFORM = "INFORM"  # Provide factual information or results
    PROPOSE = "PROPOSE"  # Suggest a plan, design, or course of action
    CONFIRM = "CONFIRM"  # Indicate agreement with a proposal or statement
    REJECT = (
        "REJECT"  # Indicate disagreement or inability to fulfill a request/proposal
    )
    QUERY = "QUERY"  # Ask for information
    ALERT = "ALERT"  # Notify of a significant event or potential problem
    BUG_REPORT = "BUG_REPORT"  # Report a specific bug or defect
    TASK_ASSIGNMENT = "TASK_ASSIGNMENT"  # Formal assignment of a task
    TASK_UPDATE = "TASK_UPDATE"  # Update on the status or progress of a task
    REVIEW_REQUEST = (
        "REVIEW_REQUEST"  # Request a review of an artifact (code, design, etc.)
    )
    REVIEW_FEEDBACK = "REVIEW_FEEDBACK"  # Provide feedback from a review
    MEETING_INVITE = "MEETING_INVITE"  # Invite agent(s) to a meeting
    MEETING_MESSAGE = "MEETING_MESSAGE"  # Message sent within the context of a meeting


@dataclass
class AgentMessage:
    """Structured message format for agent-to-agent communication.

    Uses standard fields based on FIPA ACL principles but simplified.
    """

    sender: str  # Agent ID of the sender
    receiver: str  # Agent ID of the receiver
    message_type: MessageType  # The communicative act (intent) of the message
    content: Union[
        str, Dict[str, Any]
    ]  # Payload: can be simple text or structured data (dict)
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    conversation_id: Optional[str] = (
        None  # Optional: To group related messages in a conversation
    )
    related_task: Optional[str] = None  # Optional: Link to a specific task ID
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(
        default_factory=dict
    )  # For additional, non-standard info

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary format for serialization."""
        result = asdict(self)
        result["message_type"] = self.message_type.value  # Store enum value as string
        result["created_at"] = (
            self.created_at.isoformat()
        )  # Store datetime as ISO string
        return result

    def to_json(self) -> str:
        """Convert message to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentMessage":
        """Create AgentMessage from dictionary, handling type conversions."""
        # Convert string message type back to enum
        try:
            if isinstance(data.get("message_type"), str):
                data["message_type"] = MessageType(data["message_type"])
        except ValueError as e:
            logger.error(
                f"Invalid message_type value '{data.get("message_type")}' during parsing: {e}"
            )
            # Decide handling: raise error, use default, or skip?
            # For robustness, maybe default or raise
            raise ValueError(f"Invalid message type: {data.get('message_type')}") from e

        # Convert ISO string timestamp back to datetime
        try:
            if isinstance(data.get("created_at"), str):
                data["created_at"] = datetime.fromisoformat(data["created_at"])
        except (ValueError, TypeError) as e:
            logger.warning(
                f"Could not parse created_at timestamp '{data.get("created_at")}': {e}"
            )
            # Default to now if parsing fails?
            data["created_at"] = datetime.now()

        # Ensure required fields are present
        required_fields = ["sender", "receiver", "message_type", "content"]
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            raise ValueError(
                f"Missing required fields in message data: {missing_fields}"
            )

        # Create instance using validated/converted data
        # We need to handle potential extra keys in the dict if not using a library like Pydantic
        # Get the expected field names from the dataclass itself
        expected_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in expected_fields}

        return cls(**filtered_data)

    @classmethod
    def from_json(cls, json_str: str) -> "AgentMessage":
        """Create AgentMessage from JSON string."""
        try:
            data = json.loads(json_str)
            return cls.from_dict(data)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON message: {e}")
            raise ValueError(f"Invalid JSON format: {e}") from e


class CommunicationProtocol:
    """Provides helper methods to create standard AgentMessage types."""

    def __init__(self):
        # Can add configuration or state if needed later
        pass

    def _create_message(
        self,
        sender: str,
        receiver: str,
        message_type: MessageType,
        content: Union[str, Dict[str, Any]],
        conversation_id: Optional[str] = None,
        related_task: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentMessage:
        """Generic message creation helper."""
        return AgentMessage(
            sender=sender,
            receiver=receiver,
            message_type=message_type,
            content=content,
            conversation_id=conversation_id,
            related_task=related_task,
            metadata=metadata or {},
        )

    # --- Factory methods for common message types ---

    def create_request(
        self,
        sender: str,
        receiver: str,
        content: Union[str, Dict[str, Any]],
        conversation_id: Optional[str] = None,
        related_task: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentMessage:
        """Create a REQUEST message."""
        return self._create_message(
            sender,
            receiver,
            MessageType.REQUEST,
            content,
            conversation_id,
            related_task,
            metadata,
        )

    def create_inform(
        self,
        sender: str,
        receiver: str,
        content: Union[str, Dict[str, Any]],
        conversation_id: Optional[str] = None,
        related_task: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentMessage:
        """Create an INFORM message."""
        return self._create_message(
            sender,
            receiver,
            MessageType.INFORM,
            content,
            conversation_id,
            related_task,
            metadata,
        )

    def create_propose(
        self,
        sender: str,
        receiver: str,
        content: Union[str, Dict[str, Any]],
        conversation_id: Optional[str] = None,
        related_task: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentMessage:
        """Create a PROPOSE message."""
        return self._create_message(
            sender,
            receiver,
            MessageType.PROPOSE,
            content,
            conversation_id,
            related_task,
            metadata,
        )

    def create_confirm(
        self,
        sender: str,
        receiver: str,
        content: Union[str, Dict[str, Any]],
        conversation_id: Optional[str] = None,
        related_task: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentMessage:
        """Create a CONFIRM message."""
        return self._create_message(
            sender,
            receiver,
            MessageType.CONFIRM,
            content,
            conversation_id,
            related_task,
            metadata,
        )

    def create_reject(
        self,
        sender: str,
        receiver: str,
        content: Union[str, Dict[str, Any]],
        reason: Optional[str] = None,
        conversation_id: Optional[str] = None,
        related_task: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentMessage:
        """Create a REJECT message."""
        md = metadata or {}
        if reason:
            md["rejection_reason"] = reason
        return self._create_message(
            sender,
            receiver,
            MessageType.REJECT,
            content,
            conversation_id,
            related_task,
            md,
        )

    def create_query(
        self,
        sender: str,
        receiver: str,
        content: Union[str, Dict[str, Any]],
        conversation_id: Optional[str] = None,
        related_task: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentMessage:
        """Create a QUERY message."""
        return self._create_message(
            sender,
            receiver,
            MessageType.QUERY,
            content,
            conversation_id,
            related_task,
            metadata,
        )

    def create_alert(
        self,
        sender: str,
        receiver: str,
        content: Union[str, Dict[str, Any]],
        severity: str = "MEDIUM",
        conversation_id: Optional[str] = None,
        related_task: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentMessage:
        """Create an ALERT message."""
        md = metadata or {}
        md["severity"] = severity
        return self._create_message(
            sender,
            receiver,
            MessageType.ALERT,
            content,
            conversation_id,
            related_task,
            md,
        )

    def create_bug_report(
        self,
        sender: str,
        receiver: str,
        content: Union[str, Dict[str, Any]],
        test_failure: Optional[str] = None,
        severity: str = "MEDIUM",
        conversation_id: Optional[str] = None,
        related_task: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentMessage:
        """Create a BUG_REPORT message."""
        md = metadata or {}
        md["severity"] = severity
        if test_failure:
            md["test_failure"] = test_failure
        return self._create_message(
            sender,
            receiver,
            MessageType.BUG_REPORT,
            content,
            conversation_id,
            related_task,
            md,
        )

    def create_task_assignment(
        self,
        sender: str,
        receiver: str,
        task_id: str,
        content: Union[str, Dict[str, Any]],
        conversation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentMessage:
        """Create a TASK_ASSIGNMENT message."""
        return self._create_message(
            sender,
            receiver,
            MessageType.TASK_ASSIGNMENT,
            content,
            conversation_id,
            task_id,
            metadata,
        )

    def create_task_update(
        self,
        sender: str,
        receiver: str,
        task_id: str,
        status: str,
        content: Union[str, Dict[str, Any]],
        conversation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentMessage:
        """Create a TASK_UPDATE message."""
        md = metadata or {}
        md["task_status"] = status
        return self._create_message(
            sender,
            receiver,
            MessageType.TASK_UPDATE,
            content,
            conversation_id,
            task_id,
            md,
        )

    def create_review_request(
        self,
        sender: str,
        receiver: str,
        artifact_id: str,
        content: Union[str, Dict[str, Any]],
        conversation_id: Optional[str] = None,
        related_task: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentMessage:
        """Create a REVIEW_REQUEST message."""
        md = metadata or {}
        md["artifact_id"] = artifact_id
        return self._create_message(
            sender,
            receiver,
            MessageType.REVIEW_REQUEST,
            content,
            conversation_id,
            related_task,
            md,
        )

    def create_review_feedback(
        self,
        sender: str,
        receiver: str,
        artifact_id: str,
        feedback: Union[str, List[Dict[str, Any]]],
        approved: bool,
        conversation_id: Optional[str] = None,
        related_task: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentMessage:
        """Create a REVIEW_FEEDBACK message."""
        md = metadata or {}
        md["artifact_id"] = artifact_id
        md["approved"] = approved
        # Content can be the detailed feedback itself if it's structured
        content_payload = (
            feedback
            if isinstance(feedback, dict) or isinstance(feedback, list)
            else {"summary": feedback}
        )
        return self._create_message(
            sender,
            receiver,
            MessageType.REVIEW_FEEDBACK,
            content_payload,
            conversation_id,
            related_task,
            md,
        )

    # --- Parsing ---

    def parse_message(
        self, message_data: Union[str, Dict[str, Any]]
    ) -> Optional[AgentMessage]:
        """Parse message data (JSON string or dict) into an AgentMessage object."""
        try:
            if isinstance(message_data, str):
                return AgentMessage.from_json(message_data)
            elif isinstance(message_data, dict):
                return AgentMessage.from_dict(message_data)
            else:
                logger.error(
                    f"Invalid data type for message parsing: {type(message_data)}"
                )
                return None
        except (ValueError, TypeError) as e:
            logger.error(f"Failed to parse AgentMessage: {e}", exc_info=True)
            return None
