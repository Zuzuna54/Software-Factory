"""
Core system models for the autonomous AI development team
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Identity,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    func,
    Float,
    JSON,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.declarative import declared_attr
from pgvector.sqlalchemy import Vector
import sqlalchemy as sa

# Add import for HalfVec if available
try:
    from pgvector.sqlalchemy import HalfVec
except ImportError:
    # If using an older version of pgvector-sqlalchemy that doesn't have HalfVec,
    # we can create a placeholder that will be handled at the database level
    from pgvector.sqlalchemy import Vector as HalfVec

metadata_obj = MetaData(schema="public")


class Base(DeclarativeBase):
    """Base class for all models."""

    metadata = metadata_obj
    type_annotation_map = {
        List[str]: ARRAY(String),
        Dict[str, Any]: JSONB,
    }

    @declared_attr.directive
    def __tablename__(cls) -> str:
        return cls.__name__.lower()

    # Define a vector column type for embeddings (3072 dimensions for Gemini)
    @staticmethod
    def get_vector_column(dimension=3072):
        return Column(Vector(dimension))


class Agent(Base):
    """Agent model for representing AI team members"""

    __tablename__ = "agents"
    __mapper_args__ = {"exclude_properties": ["id"]}

    agent_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    agent_type = Column(String(50), nullable=False)
    agent_name = Column(String(100), nullable=False)
    agent_role = Column(String(100), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    capabilities = Column(JSONB, nullable=True)
    system_prompt = Column(Text, nullable=True)
    status = Column(String(50), default="active", nullable=False)
    extra_data = Column(JSONB, nullable=True)  # Renamed from metadata to avoid conflict

    # Relationships
    sent_messages = relationship(
        "AgentMessage", foreign_keys="AgentMessage.sender_id", back_populates="sender"
    )
    received_messages = relationship(
        "AgentMessage",
        foreign_keys="AgentMessage.receiver_id",
        back_populates="recipient",
    )
    activities = relationship("AgentActivity", back_populates="agent")


class AgentMessage(Base):
    """Model for inter-agent communication"""

    __tablename__ = "agent_messages"
    __mapper_args__ = {"exclude_properties": ["id"]}

    message_id = Column(
        UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    sender_id = Column(UUID, ForeignKey("agents.agent_id"), nullable=False)
    receiver_id = Column(
        UUID, ForeignKey("agents.agent_id"), nullable=True
    )  # Use receiver_id to match DB
    related_task_id = Column(
        UUID, ForeignKey("tasks.task_id"), nullable=True
    )  # Match the actual column name
    meeting_id = Column(UUID, ForeignKey("meetings.meeting_id"), nullable=True)
    conversation_id = Column(
        UUID, ForeignKey("conversations.conversation_id"), nullable=True
    )

    content = Column(Text, nullable=False)
    # Using HalfVec for context_vector to support 3072 dimensions
    context_vector = Column(
        HalfVec(3072), nullable=True
    )  # Changed from Vector to HalfVec
    message_type = Column(String, nullable=False)
    extra_data = Column(
        JSONB, nullable=True
    )  # renamed from metadata to avoid conflicts

    parent_message_id = Column(
        UUID, ForeignKey("agent_messages.message_id"), nullable=True
    )

    # Relationships
    sender = relationship(
        "Agent", foreign_keys=[sender_id], back_populates="sent_messages"
    )
    recipient = relationship(
        "Agent", foreign_keys=[receiver_id], back_populates="received_messages"
    )
    related_task = relationship(
        "Task", back_populates="messages"
    )  # Match the column name
    meeting = relationship("Meeting", back_populates="messages")
    conversation = relationship("Conversation", back_populates="messages")
    parent_message = relationship("AgentMessage", remote_side=[message_id])

    def __repr__(self):
        return f"<AgentMessage id={self.message_id} agent_id={self.sender_id}>"


class AgentActivity(Base):
    """Model for tracking agent actions and decisions"""

    __tablename__ = "agent_activities"
    __mapper_args__ = {"exclude_properties": ["id"]}

    activity_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID, ForeignKey("agents.agent_id"), nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    activity_type = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    thought_process = Column(Text, nullable=True)
    input_data = Column(JSONB, nullable=True)
    output_data = Column(JSONB, nullable=True)
    related_files = Column(ARRAY(String), nullable=True)
    decisions_made = Column(JSONB, nullable=True)
    execution_time_ms = Column(Integer, nullable=True)

    # Relationships
    agent = relationship("Agent", back_populates="activities")


class Artifact(Base):
    """Model for general artifact storage"""

    __tablename__ = "artifacts"
    __mapper_args__ = {"exclude_properties": ["id"]}

    artifact_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    artifact_type = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_by = Column(UUID, ForeignKey("agents.agent_id"))
    last_modified_at = Column(DateTime)
    last_modified_by = Column(UUID, ForeignKey("agents.agent_id"))
    parent_id = Column(UUID, ForeignKey("artifacts.artifact_id"), nullable=True)
    status = Column(String(50), nullable=False)
    extra_data = Column(JSONB)  # Renamed from metadata to avoid conflict
    version = Column(Integer, nullable=False, default=1)
    content_vector = Column(Vector(3072))  # Vector for semantic search

    # Relationships
    parent = relationship("Artifact", remote_side=[artifact_id])
    creator = relationship("Agent", foreign_keys=[created_by])
    last_modifier = relationship("Agent", foreign_keys=[last_modified_by])


class Task(Base):
    """Model for task definitions and assignments"""

    __tablename__ = "tasks"
    __mapper_args__ = {"exclude_properties": ["id"]}

    task_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_by = Column(UUID, ForeignKey("agents.agent_id"))
    assigned_to = Column(UUID, ForeignKey("agents.agent_id"), nullable=True)
    sprint_id = Column(UUID, nullable=True)  # Reference to sprint
    priority = Column(Integer, nullable=False)
    status = Column(String(50), nullable=False)
    estimated_effort = Column(Float, nullable=True)
    actual_effort = Column(Float, nullable=True)
    dependencies = Column(ARRAY(UUID))  # Array of tasks this depends on
    extra_data = Column(JSONB)  # Renamed from metadata to avoid conflict
    related_artifacts = Column(ARRAY(UUID))  # References to requirements, designs, etc.

    # Relationships
    creator = relationship("Agent", foreign_keys=[created_by])
    assignee = relationship("Agent", foreign_keys=[assigned_to])
    messages = relationship("AgentMessage", back_populates="related_task")


class Meeting(Base):
    """Model for agile ceremony records"""

    __tablename__ = "meetings"
    __mapper_args__ = {"exclude_properties": ["id"]}

    meeting_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    meeting_type = Column(String(50), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    participants = Column(ARRAY(UUID))  # Array of agent IDs
    summary = Column(Text, nullable=True)
    decisions = Column(JSONB, nullable=True)
    action_items = Column(JSONB, nullable=True)
    extra_data = Column(JSONB, nullable=True)  # Renamed from metadata to avoid conflict

    # Relationships
    conversations = relationship("MeetingConversation", back_populates="meeting")
    messages = relationship("AgentMessage", back_populates="meeting")


class MeetingConversation(Base):
    """Model for meeting conversations"""

    __tablename__ = "meeting_conversations"
    __mapper_args__ = {"exclude_properties": ["id"]}

    conversation_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    meeting_id = Column(UUID, ForeignKey("meetings.meeting_id"), nullable=False)
    sequence_number = Column(Integer, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    speaker_id = Column(UUID, ForeignKey("agents.agent_id"), nullable=False)
    message = Column(Text, nullable=False)
    message_type = Column(String(50), nullable=True)

    # Relationships
    speaker = relationship("Agent")
    meeting = relationship("Meeting", back_populates="conversations")


class Conversation(Base):
    """Model for general conversations between agents"""

    __tablename__ = "conversations"
    __mapper_args__ = {"exclude_properties": ["id"]}

    conversation_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    topic = Column(String(255), nullable=True)
    status = Column(String(50), nullable=False, default="active")
    participant_ids = Column(ARRAY(UUID), nullable=True)
    extra_data = Column(
        JSONB, nullable=True
    )  # Changed from metadata to avoid conflict with SQLAlchemy

    # Relationship to associated messages
    messages = relationship(
        "AgentMessage",
        primaryjoin="Conversation.conversation_id == foreign(AgentMessage.extra_data['conversation_id'].astext.cast(UUID))",
        viewonly=True,
    )
