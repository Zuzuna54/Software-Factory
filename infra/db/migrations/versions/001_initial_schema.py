"""Initial schema creation

Revision ID: 001_initial_schema
Create Date: 2023-07-14 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY, VECTOR

# revision identifiers, used by Alembic.
revision = "001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable required PostgreSQL extensions
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgvector"')

    # Create agents table
    op.create_table(
        "agents",
        sa.Column(
            "agent_id",
            UUID(),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("agent_type", sa.String(50), nullable=False),
        sa.Column("agent_name", sa.String(100), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column("capabilities", JSONB(), nullable=True),
        sa.Column(
            "active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
    )

    # Create tasks table
    op.create_table(
        "tasks",
        sa.Column(
            "task_id",
            UUID(),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column(
            "created_by", UUID(), sa.ForeignKey("agents.agent_id"), nullable=True
        ),
        sa.Column(
            "assigned_to", UUID(), sa.ForeignKey("agents.agent_id"), nullable=True
        ),
        sa.Column("sprint_id", UUID(), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("estimated_effort", sa.Float(), nullable=True),
        sa.Column("actual_effort", sa.Float(), nullable=True),
        sa.Column("dependencies", ARRAY(UUID()), nullable=True),
        sa.Column("metadata", JSONB(), nullable=True),
        sa.Column("related_artifacts", ARRAY(UUID()), nullable=True),
    )

    # Create agent_messages table
    op.create_table(
        "agent_messages",
        sa.Column(
            "message_id",
            UUID(),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "timestamp", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column("sender_id", UUID(), sa.ForeignKey("agents.agent_id"), nullable=True),
        sa.Column(
            "receiver_id", UUID(), sa.ForeignKey("agents.agent_id"), nullable=True
        ),
        sa.Column("message_type", sa.String(50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "related_task_id", UUID(), sa.ForeignKey("tasks.task_id"), nullable=True
        ),
        sa.Column("metadata", JSONB(), nullable=True),
        sa.Column(
            "parent_message_id",
            UUID(),
            sa.ForeignKey("agent_messages.message_id"),
            nullable=True,
        ),
        sa.Column("context_vector", VECTOR(1536), nullable=True),
    )

    # Create agent_activities table
    op.create_table(
        "agent_activities",
        sa.Column(
            "activity_id",
            UUID(),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("agent_id", UUID(), sa.ForeignKey("agents.agent_id"), nullable=False),
        sa.Column(
            "timestamp", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column("activity_type", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("thought_process", sa.Text(), nullable=True),
        sa.Column("input_data", JSONB(), nullable=True),
        sa.Column("output_data", JSONB(), nullable=True),
        sa.Column("related_files", ARRAY(sa.String()), nullable=True),
        sa.Column("decisions_made", JSONB(), nullable=True),
        sa.Column("execution_time_ms", sa.Integer(), nullable=True),
    )

    # Create artifacts table
    op.create_table(
        "artifacts",
        sa.Column(
            "artifact_id",
            UUID(),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("artifact_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column(
            "created_by", UUID(), sa.ForeignKey("agents.agent_id"), nullable=True
        ),
        sa.Column("last_modified_at", sa.DateTime(), nullable=True),
        sa.Column(
            "last_modified_by", UUID(), sa.ForeignKey("agents.agent_id"), nullable=True
        ),
        sa.Column(
            "parent_id", UUID(), sa.ForeignKey("artifacts.artifact_id"), nullable=True
        ),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("metadata", JSONB(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("content_vector", VECTOR(1536), nullable=True),
    )

    # Create meetings table
    op.create_table(
        "meetings",
        sa.Column(
            "meeting_id",
            UUID(),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("meeting_type", sa.String(50), nullable=False),
        sa.Column("start_time", sa.DateTime(), nullable=False),
        sa.Column("end_time", sa.DateTime(), nullable=True),
        sa.Column("participants", ARRAY(UUID()), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("decisions", JSONB(), nullable=True),
        sa.Column("action_items", JSONB(), nullable=True),
    )

    # Create meeting_conversations table
    op.create_table(
        "meeting_conversations",
        sa.Column(
            "conversation_id",
            UUID(),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "meeting_id", UUID(), sa.ForeignKey("meetings.meeting_id"), nullable=False
        ),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column(
            "timestamp", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column(
            "speaker_id", UUID(), sa.ForeignKey("agents.agent_id"), nullable=False
        ),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("message_type", sa.String(50), nullable=True),
        sa.Column("context", JSONB(), nullable=True),
    )

    # Create requirements_artifacts table
    op.create_table(
        "requirements_artifacts",
        sa.Column(
            "artifact_id",
            UUID(),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("project_id", UUID(), nullable=False),
        sa.Column("artifact_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("acceptance_criteria", JSONB(), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=True),
        sa.Column(
            "created_by", UUID(), sa.ForeignKey("agents.agent_id"), nullable=True
        ),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column("reasoning", sa.Text(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column(
            "parent_id",
            UUID(),
            sa.ForeignKey("requirements_artifacts.artifact_id"),
            nullable=True,
        ),
        sa.Column("stakeholder_value", sa.Text(), nullable=True),
        sa.Column("metadata", JSONB(), nullable=True),
    )

    # Create design_artifacts table
    op.create_table(
        "design_artifacts",
        sa.Column(
            "artifact_id",
            UUID(),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("project_id", UUID(), nullable=False),
        sa.Column("artifact_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("content_format", sa.String(50), nullable=True),
        sa.Column(
            "created_by", UUID(), sa.ForeignKey("agents.agent_id"), nullable=True
        ),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column("last_modified_at", sa.DateTime(), nullable=True),
        sa.Column("related_requirements", ARRAY(UUID()), nullable=True),
        sa.Column("design_decisions", JSONB(), nullable=True),
        sa.Column("alternatives_considered", JSONB(), nullable=True),
        sa.Column("reasoning", sa.Text(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("review_comments", JSONB(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
    )

    # Create implementation_artifacts table
    op.create_table(
        "implementation_artifacts",
        sa.Column(
            "artifact_id",
            UUID(),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("project_id", UUID(), nullable=False),
        sa.Column("artifact_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("related_files", ARRAY(sa.String()), nullable=True),
        sa.Column(
            "created_by", UUID(), sa.ForeignKey("agents.agent_id"), nullable=True
        ),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column("last_modified_at", sa.DateTime(), nullable=True),
        sa.Column("related_requirements", ARRAY(UUID()), nullable=True),
        sa.Column("related_designs", ARRAY(UUID()), nullable=True),
        sa.Column("implementation_decisions", JSONB(), nullable=True),
        sa.Column("approach_rationale", sa.Text(), nullable=True),
        sa.Column("complexity_assessment", sa.Text(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("review_comments", JSONB(), nullable=True),
        sa.Column("metrics", JSONB(), nullable=True),
    )

    # Create testing_artifacts table
    op.create_table(
        "testing_artifacts",
        sa.Column(
            "artifact_id",
            UUID(),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("project_id", UUID(), nullable=False),
        sa.Column("artifact_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("test_files", ARRAY(sa.String()), nullable=True),
        sa.Column(
            "created_by", UUID(), sa.ForeignKey("agents.agent_id"), nullable=True
        ),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column("related_implementation", ARRAY(UUID()), nullable=True),
        sa.Column("test_coverage", JSONB(), nullable=True),
        sa.Column("test_approach", sa.Text(), nullable=True),
        sa.Column("results", JSONB(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False),
    )

    # Create project_vision table
    op.create_table(
        "project_vision",
        sa.Column(
            "vision_id",
            UUID(),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("project_id", UUID(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("vision_statement", sa.Text(), nullable=False),
        sa.Column("target_audience", sa.Text(), nullable=True),
        sa.Column("key_goals", JSONB(), nullable=True),
        sa.Column("success_metrics", JSONB(), nullable=True),
        sa.Column("constraints", JSONB(), nullable=True),
        sa.Column(
            "created_by", UUID(), sa.ForeignKey("agents.agent_id"), nullable=True
        ),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column("last_modified_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False),
    )

    # Create project_roadmap table
    op.create_table(
        "project_roadmap",
        sa.Column(
            "roadmap_id",
            UUID(),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("project_id", UUID(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("time_horizons", JSONB(), nullable=True),
        sa.Column("milestones", JSONB(), nullable=True),
        sa.Column("feature_sequence", JSONB(), nullable=True),
        sa.Column("dependencies", JSONB(), nullable=True),
        sa.Column(
            "created_by", UUID(), sa.ForeignKey("agents.agent_id"), nullable=True
        ),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column("last_modified_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False),
    )

    # Create codebase_analysis table
    op.create_table(
        "codebase_analysis",
        sa.Column(
            "analysis_id",
            UUID(),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("repository_id", UUID(), nullable=False),
        sa.Column("analysis_type", sa.String(50), nullable=False),
        sa.Column(
            "analysis_timestamp",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("analysis_result", JSONB(), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("related_files", ARRAY(sa.String()), nullable=True),
    )

    # Create detected_patterns table
    op.create_table(
        "detected_patterns",
        sa.Column(
            "pattern_id",
            UUID(),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("repository_id", UUID(), nullable=False),
        sa.Column("pattern_type", sa.String(50), nullable=False),
        sa.Column("pattern_name", sa.String(100), nullable=False),
        sa.Column("pattern_examples", JSONB(), nullable=True),
        sa.Column("detection_confidence", sa.Float(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
    )

    # Create indexes for common lookup patterns
    op.create_index("ix_agents_agent_type", "agents", ["agent_type"])
    op.create_index("ix_agent_messages_sender_id", "agent_messages", ["sender_id"])
    op.create_index("ix_agent_messages_receiver_id", "agent_messages", ["receiver_id"])
    op.create_index("ix_agent_activities_agent_id", "agent_activities", ["agent_id"])
    op.create_index("ix_tasks_status", "tasks", ["status"])
    op.create_index("ix_tasks_assigned_to", "tasks", ["assigned_to"])
    op.create_index("ix_artifacts_artifact_type", "artifacts", ["artifact_type"])
    op.create_index("ix_artifacts_created_by", "artifacts", ["created_by"])

    # Create indexes for vector search
    op.execute(
        "CREATE INDEX ix_agent_messages_context_vector ON agent_messages USING ivfflat (context_vector vector_cosine_ops)"
    )
    op.execute(
        "CREATE INDEX ix_artifacts_content_vector ON artifacts USING ivfflat (content_vector vector_cosine_ops)"
    )


def downgrade() -> None:
    # Drop tables in reverse order of creation (to respect foreign keys)
    op.drop_table("detected_patterns")
    op.drop_table("codebase_analysis")
    op.drop_table("project_roadmap")
    op.drop_table("project_vision")
    op.drop_table("testing_artifacts")
    op.drop_table("implementation_artifacts")
    op.drop_table("design_artifacts")
    op.drop_table("requirements_artifacts")
    op.drop_table("meeting_conversations")
    op.drop_table("meetings")
    op.drop_table("artifacts")
    op.drop_table("agent_activities")
    op.drop_table("agent_messages")
    op.drop_table("tasks")
    op.drop_table("agents")

    # Drop extensions
    op.execute('DROP EXTENSION IF EXISTS "pgvector"')
    op.execute('DROP EXTENSION IF EXISTS "uuid-ossp"')
