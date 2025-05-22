"""Align models with database schema

Revision ID: 002_align_models_with_db
Create Date: 2023-12-10 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision = "002_align_models_with_db"
down_revision = "865de94d37c6"  # Use the most recent migration as the parent
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Update agents table to match the model
    op.add_column("agents", sa.Column("agent_role", sa.String(100), nullable=True))
    op.add_column("agents", sa.Column("system_prompt", sa.Text(), nullable=True))
    op.add_column("agents", sa.Column("extra_data", JSONB(), nullable=True))

    # Set a default value for agent_role to avoid nullable constraint issues
    op.execute("UPDATE agents SET agent_role = agent_type WHERE agent_role IS NULL")

    # Now make agent_role not nullable after setting defaults
    op.alter_column("agents", "agent_role", nullable=False)

    # Rename 'active' to 'status' for consistency with model
    op.alter_column(
        "agents",
        "active",
        new_column_name="status",
        type_=sa.String(50),
        existing_type=sa.Boolean(),
        nullable=False,
    )

    # Set initial values after type change
    op.execute("UPDATE agents SET status = 'active' WHERE status = 'true'")
    op.execute("UPDATE agents SET status = 'inactive' WHERE status = 'false'")

    # Rename metadata to extra_data in other tables for consistency
    op.alter_column("tasks", "metadata", new_column_name="extra_data")
    op.alter_column("artifacts", "metadata", new_column_name="extra_data")

    # Add missing columns in agent_messages table
    op.add_column(
        "agent_messages", sa.Column("updated_at", sa.DateTime(), nullable=True)
    )
    op.add_column("agent_messages", sa.Column("extra_data", JSONB(), nullable=True))

    # Add meeting.extra_data column
    op.add_column("meetings", sa.Column("extra_data", JSONB(), nullable=True))

    # Rename columns for consistency with models
    op.alter_column("agent_messages", "timestamp", new_column_name="created_at")


def downgrade() -> None:
    # Revert changes in reverse order

    # Rename columns back to original names
    op.alter_column("agent_messages", "created_at", new_column_name="timestamp")

    # Remove extra_data from meetings
    op.drop_column("meetings", "extra_data")

    # Remove columns from agent_messages
    op.drop_column("agent_messages", "extra_data")
    op.drop_column("agent_messages", "updated_at")

    # Rename extra_data back to metadata in tables
    op.alter_column("artifacts", "extra_data", new_column_name="metadata")
    op.alter_column("tasks", "extra_data", new_column_name="metadata")

    # Revert status to boolean active column
    op.execute(
        "ALTER TABLE agents ALTER COLUMN status TYPE boolean USING CASE WHEN status = 'active' THEN true ELSE false END"
    )
    op.alter_column("agents", "status", new_column_name="active")

    # Remove added columns from agents
    op.drop_column("agents", "extra_data")
    op.drop_column("agents", "system_prompt")
    op.drop_column("agents", "agent_role")
