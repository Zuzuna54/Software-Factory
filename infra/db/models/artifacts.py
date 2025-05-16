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

from .base import Base, UUID


class RequirementsArtifact(Base):
    """Model for user stories, features, requirements"""

    __tablename__ = "requirements_artifacts"

    artifact_id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(), nullable=False)
    artifact_type = Column(
        String(50), nullable=False
    )  # Vision, UserStory, Feature, Epic, etc.
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    acceptance_criteria = Column(JSONB)
    priority = Column(Integer)
    created_by = Column(UUID(), ForeignKey("agents.agent_id"))
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    reasoning = Column(Text)  # PM's rationale for this requirement
    status = Column(
        String(50), nullable=False
    )  # Draft, Reviewed, Approved, Implemented, etc.
    parent_id = Column(
        UUID(), ForeignKey("requirements_artifacts.artifact_id"), nullable=True
    )
    stakeholder_value = Column(Text)  # Description of business/user value
    extra_data = Column(JSONB)

    # Relationships
    creator = relationship("Agent", foreign_keys=[created_by])
    parent = relationship(
        "RequirementsArtifact", remote_side=[artifact_id], backref="children"
    )


class DesignArtifact(Base):
    """Model for wireframes, architecture diagrams"""

    __tablename__ = "design_artifacts"

    artifact_id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(), nullable=False)
    artifact_type = Column(
        String(50), nullable=False
    )  # Wireframe, StyleGuide, Architecture, ERD, etc.
    title = Column(String(255), nullable=False)
    description = Column(Text)
    content = Column(
        Text
    )  # Could be JSON, markdown, or base64 encoded for binary content
    content_format = Column(String(50))  # Markdown, JSON, PNG, etc.
    created_by = Column(UUID(), ForeignKey("agents.agent_id"))
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_modified_at = Column(DateTime)
    related_requirements = Column(ARRAY(UUID()))
    design_decisions = Column(JSONB)  # Structured record of key design decisions
    alternatives_considered = Column(JSONB)  # Other approaches that were evaluated
    reasoning = Column(Text)  # Why this design was chosen
    status = Column(String(50), nullable=False)
    review_comments = Column(JSONB)
    version = Column(Integer, nullable=False, default=1)

    # Relationships
    creator = relationship("Agent", foreign_keys=[created_by])


class ImplementationArtifact(Base):
    """Model for code implementations"""

    __tablename__ = "implementation_artifacts"

    artifact_id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(), nullable=False)
    artifact_type = Column(
        String(50), nullable=False
    )  # Component, Module, Function, API, etc.
    title = Column(String(255), nullable=False)
    description = Column(Text)
    related_files = Column(ARRAY(String))  # Paths to files implementing this artifact
    created_by = Column(UUID(), ForeignKey("agents.agent_id"))
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_modified_at = Column(DateTime)
    related_requirements = Column(ARRAY(UUID()))
    related_designs = Column(ARRAY(UUID()))
    implementation_decisions = Column(JSONB)
    approach_rationale = Column(Text)  # Why this implementation approach was chosen
    complexity_assessment = Column(Text)
    status = Column(String(50), nullable=False)
    review_comments = Column(JSONB)
    metrics = Column(JSONB)  # Code quality metrics, performance, etc.

    # Relationships
    creator = relationship("Agent", foreign_keys=[created_by])


class TestingArtifact(Base):
    """Model for test cases and results"""

    __tablename__ = "testing_artifacts"

    artifact_id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(), nullable=False)
    artifact_type = Column(
        String(50), nullable=False
    )  # UnitTest, IntegrationTest, E2E, etc.
    title = Column(String(255), nullable=False)
    description = Column(Text)
    test_files = Column(ARRAY(String))  # Paths to test files
    created_by = Column(UUID(), ForeignKey("agents.agent_id"))
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    related_implementation = Column(ARRAY(UUID()))
    test_coverage = Column(JSONB)  # What's being tested and coverage metrics
    test_approach = Column(Text)  # Testing strategy used
    results = Column(JSONB)  # Latest test results
    status = Column(String(50), nullable=False)

    # Relationships
    creator = relationship("Agent", foreign_keys=[created_by])


class ProjectVision(Base):
    """Model for project vision statements"""

    __tablename__ = "project_vision"

    vision_id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(), nullable=False)
    title = Column(String(255), nullable=False)
    vision_statement = Column(Text, nullable=False)
    target_audience = Column(Text)
    key_goals = Column(JSONB)
    success_metrics = Column(JSONB)
    constraints = Column(JSONB)
    created_by = Column(UUID(), ForeignKey("agents.agent_id"))
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_modified_at = Column(DateTime)
    status = Column(String(50), nullable=False)

    # Relationships
    creator = relationship("Agent", foreign_keys=[created_by])


class ProjectRoadmap(Base):
    """Model for project timeline and milestones"""

    __tablename__ = "project_roadmap"

    roadmap_id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    time_horizons = Column(JSONB)  # Structured timeframes for delivery
    milestones = Column(JSONB)
    feature_sequence = Column(JSONB)  # Order of feature development
    dependencies = Column(JSONB)
    created_by = Column(UUID(), ForeignKey("agents.agent_id"))
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_modified_at = Column(DateTime)
    status = Column(String(50), nullable=False)

    # Relationships
    creator = relationship("Agent", foreign_keys=[created_by])


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


class Artifact(Base):
    """An artifact is a document or file that is used by agents."""

    __tablename__ = "artifacts"

    id = Column(UUID, primary_key=True, server_default=sa.text("uuid_generate_v4()"))
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    content = Column(Text, nullable=True)
    # Using HalfVec for content_vector to support 3072 dimensions
    content_vector = Column(HalfVec(3072), nullable=True)

    artifact_type = Column(String, nullable=False)
    url = Column(String, nullable=True)
    extra_data = Column(
        JSONB, nullable=True
    )  # renamed from metadata to avoid conflicts

    created_by = Column(UUID, ForeignKey("agents.agent_id"), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<Artifact id={self.id} name={self.name}>"
