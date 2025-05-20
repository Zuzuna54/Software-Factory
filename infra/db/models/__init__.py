"""
SQLAlchemy models for the autonomous AI development team
"""

from .base import Base, UUID, get_db
from .core import (
    Agent,
    AgentMessage,
    AgentActivity,
    Task,
    Meeting,
    MeetingConversation,
    Conversation,
    Project,
)
from .artifacts import (
    Artifact,
    RequirementsArtifact,
    UserStoryArtifact,
    DesignArtifact,
    ImplementationArtifact,
    TestingArtifact,
    ProjectVision,
    ProjectRoadmap,
    CodebaseAnalysis,
    DetectedPattern,
)

# Export all models
__all__ = [
    "Base",
    "UUID",
    "get_db",
    # Core models
    "Agent",
    "AgentMessage",
    "AgentActivity",
    "Task",
    "Meeting",
    "MeetingConversation",
    "Project",
    # Artifact models
    "Artifact",
    "RequirementsArtifact",
    "UserStoryArtifact",
    "DesignArtifact",
    "ImplementationArtifact",
    "TestingArtifact",
    "ProjectVision",
    "ProjectRoadmap",
    "CodebaseAnalysis",
    "DetectedPattern",
    "Conversation",
]
