# agents/tests/test_communication.py

import pytest
import json
from datetime import datetime
from uuid import UUID

from agents.communication.protocol import (
    AgentMessage,
    MessageType,
    CommunicationProtocol,
)

# Fixture comm_protocol is provided by conftest.py
SENDER_ID = "agent_sender_123"
RECEIVER_ID = "agent_receiver_456"


def test_create_request_message(comm_protocol: CommunicationProtocol):
    content = {"action": "get_status", "resource": "service_X"}
    msg = comm_protocol.create_request(SENDER_ID, RECEIVER_ID, content)

    assert isinstance(msg, AgentMessage)
    assert msg.sender == SENDER_ID
    assert msg.receiver == RECEIVER_ID
    assert msg.message_type == MessageType.REQUEST
    assert msg.content == content
    assert isinstance(msg.message_id, str)
    assert isinstance(msg.created_at, datetime)
    assert msg.metadata == {}


def test_create_inform_message(comm_protocol: CommunicationProtocol):
    content = "Task completed successfully."
    task_id = "task_abc"
    msg = comm_protocol.create_inform(
        SENDER_ID, RECEIVER_ID, content, related_task=task_id
    )

    assert msg.message_type == MessageType.INFORM
    assert msg.content == content
    assert msg.related_task == task_id


def test_create_alert_message(comm_protocol: CommunicationProtocol):
    content = "High CPU usage detected on node Y."
    metadata = {"node": "node_Y", "cpu_usage": 95.5}
    msg = comm_protocol.create_alert(
        SENDER_ID, RECEIVER_ID, content, severity="HIGH", metadata=metadata
    )

    assert msg.message_type == MessageType.ALERT
    assert msg.content == content
    assert msg.metadata["severity"] == "HIGH"
    assert msg.metadata["node"] == "node_Y"
    assert msg.metadata["cpu_usage"] == 95.5


def test_message_serialization_deserialization(comm_protocol: CommunicationProtocol):
    """Test converting a message to dict/JSON and back."""
    content = {"data": [1, 2, 3], "status": "OK"}
    original_msg = comm_protocol.create_propose(
        sender=SENDER_ID,
        receiver=RECEIVER_ID,
        content=content,
        conversation_id="conv_789",
        metadata={"priority": 1},
    )

    # To Dict
    msg_dict = original_msg.to_dict()
    assert isinstance(msg_dict, dict)
    assert msg_dict["sender"] == SENDER_ID
    assert msg_dict["receiver"] == RECEIVER_ID
    assert msg_dict["message_type"] == "PROPOSE"  # Enum value
    assert msg_dict["content"] == content
    assert msg_dict["message_id"] == original_msg.message_id
    assert msg_dict["conversation_id"] == "conv_789"
    assert isinstance(msg_dict["created_at"], str)  # ISO format string
    assert msg_dict["metadata"] == {"priority": 1}

    # From Dict
    parsed_msg_from_dict = AgentMessage.from_dict(msg_dict)
    assert isinstance(parsed_msg_from_dict, AgentMessage)
    assert (
        parsed_msg_from_dict.message_type == MessageType.PROPOSE
    )  # Converted back to Enum
    assert (
        parsed_msg_from_dict.created_at == original_msg.created_at
    )  # Converted back to datetime
    assert parsed_msg_from_dict == original_msg

    # To JSON
    msg_json = original_msg.to_json()
    assert isinstance(msg_json, str)
    # Check if it looks like JSON
    assert msg_json.startswith("{")
    assert msg_json.endswith("}")
    assert '"message_type": "PROPOSE"' in msg_json

    # From JSON
    parsed_msg_from_json = AgentMessage.from_json(msg_json)
    assert isinstance(parsed_msg_from_json, AgentMessage)
    assert parsed_msg_from_json == original_msg


def test_parse_message_utility(comm_protocol: CommunicationProtocol):
    """Test the protocol's parse_message helper."""
    content = "Parsing test"
    original_msg = comm_protocol.create_inform(SENDER_ID, RECEIVER_ID, content)

    msg_dict = original_msg.to_dict()
    msg_json = original_msg.to_json()

    parsed_from_dict = comm_protocol.parse_message(msg_dict)
    assert parsed_from_dict == original_msg

    parsed_from_json = comm_protocol.parse_message(msg_json)
    assert parsed_from_json == original_msg

    # Test invalid types
    assert comm_protocol.parse_message(123) is None
    assert comm_protocol.parse_message(None) is None


def test_from_dict_invalid_type(comm_protocol: CommunicationProtocol):
    """Test parsing a dict with an invalid message type."""
    invalid_dict = {
        "sender": SENDER_ID,
        "receiver": RECEIVER_ID,
        "message_type": "INVALID_TYPE",  # Not in Enum
        "content": "test",
    }
    with pytest.raises(ValueError, match="Invalid message type"):
        AgentMessage.from_dict(invalid_dict)


def test_from_dict_missing_fields(comm_protocol: CommunicationProtocol):
    """Test parsing a dict missing required fields."""
    invalid_dict = {
        "sender": SENDER_ID,
        # missing receiver, message_type, content
    }
    with pytest.raises(ValueError, match="Missing required fields"):
        AgentMessage.from_dict(invalid_dict)
