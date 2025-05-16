"""
SQLAlchemy models for the autonomous AI development team
"""

from .base import Base, UUID, get_db
from .core import (
    Agent,
    AgentMessage,
    AgentActivity,
    Artifact,
    Task,
    Meeting,
    MeetingConversation,
)
from .artifacts import (
    RequirementsArtifact,
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
    "Artifact",
    "Task",
    "Meeting",
    "MeetingConversation",
    # Artifact models
    "RequirementsArtifact",
    "DesignArtifact",
    "ImplementationArtifact",
    "TestingArtifact",
    "ProjectVision",
    "ProjectRoadmap",
    "CodebaseAnalysis",
    "DetectedPattern",
]
