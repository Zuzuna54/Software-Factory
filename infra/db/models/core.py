"""
Core system models for the autonomous AI development team
"""

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
    Float,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, VECTOR
from sqlalchemy.orm import relationship

from .base import Base, UUID


class Agent(Base):
    """Agent model for representing AI team members"""

    __tablename__ = "agents"

    agent_id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    agent_type = Column(String(50), nullable=False)
    agent_name = Column(String(100), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    capabilities = Column(JSONB)
    active = Column(Boolean, nullable=False, default=True)

    # Relationships
    messages_sent = relationship(
        "AgentMessage", foreign_keys="AgentMessage.sender_id", back_populates="sender"
    )
    messages_received = relationship(
        "AgentMessage",
        foreign_keys="AgentMessage.receiver_id",
        back_populates="receiver",
    )
    activities = relationship("AgentActivity", back_populates="agent")


class AgentMessage(Base):
    """Model for inter-agent communication"""

    __tablename__ = "agent_messages"

    message_id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    sender_id = Column(UUID(), ForeignKey("agents.agent_id"))
    receiver_id = Column(UUID(), ForeignKey("agents.agent_id"))
    message_type = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    related_task_id = Column(UUID(), ForeignKey("tasks.task_id"), nullable=True)
    metadata = Column(JSONB)
    parent_message_id = Column(
        UUID(), ForeignKey("agent_messages.message_id"), nullable=True
    )
    context_vector = Column(VECTOR(1536))  # Vector for semantic search

    # Relationships
    sender = relationship(
        "Agent", foreign_keys=[sender_id], back_populates="messages_sent"
    )
    receiver = relationship(
        "Agent", foreign_keys=[receiver_id], back_populates="messages_received"
    )
    related_task = relationship("Task", back_populates="related_messages")
    parent_message = relationship(
        "AgentMessage", remote_side=[message_id], backref="replies"
    )


class AgentActivity(Base):
    """Model for tracking agent actions and decisions"""

    __tablename__ = "agent_activities"

    activity_id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(), ForeignKey("agents.agent_id"), nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    activity_type = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    thought_process = Column(Text)
    input_data = Column(JSONB)
    output_data = Column(JSONB)
    related_files = Column(ARRAY(String))
    decisions_made = Column(JSONB)
    execution_time_ms = Column(Integer)

    # Relationships
    agent = relationship("Agent", back_populates="activities")


class Artifact(Base):
    """Model for general artifact storage"""

    __tablename__ = "artifacts"

    artifact_id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    artifact_type = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_by = Column(UUID(), ForeignKey("agents.agent_id"))
    last_modified_at = Column(DateTime)
    last_modified_by = Column(UUID(), ForeignKey("agents.agent_id"))
    parent_id = Column(UUID(), ForeignKey("artifacts.artifact_id"), nullable=True)
    status = Column(String(50), nullable=False)
    metadata = Column(JSONB)
    version = Column(Integer, nullable=False, default=1)
    content_vector = Column(VECTOR(1536))  # Vector for semantic search

    # Relationships
    creator = relationship("Agent", foreign_keys=[created_by])
    modifier = relationship("Agent", foreign_keys=[last_modified_by])
    parent = relationship("Artifact", remote_side=[artifact_id], backref="children")


class Task(Base):
    """Model for task definitions and assignments"""

    __tablename__ = "tasks"

    task_id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_by = Column(UUID(), ForeignKey("agents.agent_id"))
    assigned_to = Column(UUID(), ForeignKey("agents.agent_id"), nullable=True)
    sprint_id = Column(UUID(), nullable=True)  # Reference to sprint
    priority = Column(Integer, nullable=False)
    status = Column(String(50), nullable=False)
    estimated_effort = Column(Float, nullable=True)
    actual_effort = Column(Float, nullable=True)
    dependencies = Column(ARRAY(UUID()))  # Array of tasks this depends on
    metadata = Column(JSONB)
    related_artifacts = Column(
        ARRAY(UUID())
    )  # References to requirements, designs, etc.

    # Relationships
    creator = relationship("Agent", foreign_keys=[created_by])
    assignee = relationship("Agent", foreign_keys=[assigned_to])
    related_messages = relationship("AgentMessage", back_populates="related_task")


class Meeting(Base):
    """Model for agile ceremony records"""

    __tablename__ = "meetings"

    meeting_id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    meeting_type = Column(String(50), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    participants = Column(ARRAY(UUID()))  # Array of agent IDs
    summary = Column(Text, nullable=True)
    decisions = Column(JSONB, nullable=True)
    action_items = Column(JSONB, nullable=True)

    # Relationships
    conversations = relationship("MeetingConversation", back_populates="meeting")


class MeetingConversation(Base):
    """Model for meeting conversations"""

    __tablename__ = "meeting_conversations"

    conversation_id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    meeting_id = Column(UUID(), ForeignKey("meetings.meeting_id"), nullable=False)
    sequence_number = Column(Integer, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    speaker_id = Column(UUID(), ForeignKey("agents.agent_id"), nullable=False)
    message = Column(Text, nullable=False)
    message_type = Column(String(50), nullable=True)
    context = Column(JSONB, nullable=True)

    # Relationships
    meeting = relationship("Meeting", back_populates="conversations")
    speaker = relationship("Agent")
