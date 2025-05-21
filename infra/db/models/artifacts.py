"""
Artifact-specific models for the autonomous AI development team
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
    Float,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
import sqlalchemy as sa

# Add import for HalfVec if available
try:
    from pgvector.sqlalchemy import HalfVec
except ImportError:
    # If using an older version of pgvector-sqlalchemy that doesn't have HalfVec,
    # we can create a placeholder that will be handled at the database level
    from pgvector.sqlalchemy import Vector as HalfVec

from .base import Base
from .core import Agent, Project


class Artifact(Base):
    """An artifact is a document or file that is used by agents."""

    __tablename__ = "artifacts"

    artifact_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("uuid_generate_v4()"),
    )
    title = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    # Using HalfVec for content_vector to support 3072 dimensions
    content_vector = Column(HalfVec(3072), nullable=True)

    artifact_type = Column(String, nullable=False)
    project_id = Column(
        UUID(as_uuid=True), ForeignKey("projects.project_id"), nullable=False
    )
    url = Column(String, nullable=True)
    metadata_ = Column(
        "metadata", JSONB, nullable=True
    )  # Renamed to avoid Pydantic conflict

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP"),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP"),
        onupdate=sa.text("CURRENT_TIMESTAMP"),
    )

    created_by = Column(
        UUID(as_uuid=True), ForeignKey("agents.agent_id"), nullable=False
    )
    is_active = Column(Boolean, default=True, nullable=False)

    # Default status for the base artifact record, if the DB has a NOT NULL status column on artifacts table
    status = Column(
        String(50), nullable=False, default="created"
    )  # Default for base Artifact

    # Relationships
    creator = relationship(Agent, foreign_keys=[created_by])
    project = relationship(Project, back_populates="artifacts")

    __mapper_args__ = {
        "polymorphic_identity": "artifact",
        "polymorphic_on": artifact_type,
    }

    def __repr__(self):
        return f"<Artifact id={self.artifact_id} title={self.title} type={self.artifact_type}>"


class RequirementsArtifact(Artifact):
    """Model for user stories, features, requirements"""

    __tablename__ = "requirements_artifacts"
    __mapper_args__ = {"polymorphic_identity": "requirements"}

    artifact_id = Column(
        UUID(as_uuid=True),
        ForeignKey("artifacts.artifact_id"),
        primary_key=True,
    )
    content = Column(Text, nullable=False)
    acceptance_criteria = Column(JSONB, nullable=True)
    priority = Column(Integer, nullable=False, default=0, index=True)
    reasoning = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="pending", index=True)
    parent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("requirements_artifacts.artifact_id"),
        nullable=True,
    )
    stakeholder_value = Column(Text, nullable=True)
    extra_data = Column(JSONB, nullable=True)

    # Relationships
    parent = relationship(
        "RequirementsArtifact",
        foreign_keys=[parent_id],
        remote_side=[artifact_id],
        backref="children",
    )


class UserStoryArtifact(RequirementsArtifact):
    __mapper_args__ = {
        "polymorphic_identity": "user_story",
    }


class FeatureArtifact(RequirementsArtifact):
    __mapper_args__ = {
        "polymorphic_identity": "Feature",
    }


class DesignArtifact(Artifact):
    """Model for wireframes, architecture diagrams"""

    __tablename__ = "design_artifacts"
    __mapper_args__ = {"polymorphic_identity": "design"}

    artifact_id = Column(
        UUID(as_uuid=True),
        ForeignKey("artifacts.artifact_id"),
        primary_key=True,
    )
    content = Column(Text, nullable=True)
    content_format = Column(String(50), nullable=True)
    related_requirements = Column(ARRAY(UUID(as_uuid=True)), nullable=True)
    design_decisions = Column(JSONB, nullable=True)
    alternatives_considered = Column(JSONB, nullable=True)
    reasoning = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="draft")
    review_comments = Column(JSONB, nullable=True)
    version = Column(Integer, nullable=False, default=1)
    design_type = Column(String, nullable=False)


class ImplementationArtifact(Artifact):
    """Model for code implementations"""

    __tablename__ = "implementation_artifacts"
    __mapper_args__ = {"polymorphic_identity": "implementation"}

    artifact_id = Column(
        UUID(as_uuid=True),
        ForeignKey("artifacts.artifact_id"),
        primary_key=True,
    )
    related_files = Column(ARRAY(String), nullable=True)
    related_requirements = Column(ARRAY(UUID(as_uuid=True)), nullable=True)
    related_designs = Column(ARRAY(UUID(as_uuid=True)), nullable=True)
    implementation_decisions = Column(JSONB, nullable=True)
    approach_rationale = Column(Text, nullable=True)
    complexity_assessment = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="development")
    review_comments = Column(JSONB, nullable=True)
    metrics = Column(JSONB, nullable=True)
    code_repository_url = Column(String, nullable=True)
    commit_hash = Column(String, nullable=True)
    branch_name = Column(String, nullable=True)


class TestingArtifact(Artifact):
    """Model for test cases and results"""

    __tablename__ = "testing_artifacts"
    __mapper_args__ = {"polymorphic_identity": "testing"}

    artifact_id = Column(
        UUID(as_uuid=True),
        ForeignKey("artifacts.artifact_id"),
        primary_key=True,
    )
    test_files = Column(ARRAY(String), nullable=True)
    related_implementation = Column(ARRAY(UUID(as_uuid=True)), nullable=True)
    test_coverage = Column(JSONB, nullable=True)
    test_approach = Column(Text, nullable=True)
    results = Column(JSONB, nullable=True)
    status = Column(String(50), nullable=False, default="pending_execution")
    test_type = Column(String, nullable=False)


class ProjectVision(Artifact):
    """Model for project vision statements"""

    __tablename__ = "project_vision"
    __mapper_args__ = {"polymorphic_identity": "project_vision"}

    artifact_id = Column(
        UUID(as_uuid=True), ForeignKey("artifacts.artifact_id"), primary_key=True
    )
    vision_statement = Column(Text, nullable=False)
    target_audience = Column(Text, nullable=True)
    key_goals = Column(JSONB, nullable=True)
    success_metrics = Column(JSONB, nullable=True)
    constraints = Column(JSONB, nullable=True)
    status = Column(String(50), nullable=False, default="draft")


class ProjectRoadmap(Artifact):
    """Model for project timeline and milestones"""

    __tablename__ = "project_roadmap"
    __mapper_args__ = {"polymorphic_identity": "project_roadmap"}

    artifact_id = Column(
        UUID(as_uuid=True), ForeignKey("artifacts.artifact_id"), primary_key=True
    )
    time_horizons = Column(JSONB, nullable=True)
    milestones = Column(JSONB, nullable=True)
    feature_sequence = Column(JSONB, nullable=True)
    dependencies = Column(JSONB, nullable=True)
    status = Column(String(50), nullable=False, default="planning")
    timeline_start_date = Column(DateTime(timezone=True), nullable=True)
    timeline_end_date = Column(DateTime(timezone=True), nullable=True)
    phases = Column(JSONB, nullable=True)
    deliverables = Column(JSONB, nullable=True)
    risks = Column(JSONB, nullable=True)


class CodebaseAnalysis(Base):
    """Model for analyzing existing codebases"""

    __tablename__ = "codebase_analysis"

    analysis_id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    repository_id = Column(
        UUID(), nullable=False
    )  # Reference to repository being analyzed
    analysis_type = Column(
        String(50), nullable=False
    )  # TechStack, Architecture, Structure, Standards
    analysis_timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    analysis_result = Column(JSONB, nullable=False)  # Structured analysis findings
    confidence_score = Column(Float)  # Confidence in analysis accuracy
    related_files = Column(ARRAY(String))  # Files analyzed for this result


class DetectedPattern(Base):
    """Model for patterns detected in existing codebases"""

    __tablename__ = "detected_patterns"

    pattern_id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    repository_id = Column(UUID(), nullable=False)  # Reference to repository
    pattern_type = Column(
        String(50), nullable=False
    )  # Naming, Structure, Architecture, etc.
    pattern_name = Column(String(100), nullable=False)
    pattern_examples = Column(JSONB)  # Example instances of the pattern
    detection_confidence = Column(Float)
    description = Column(Text)
