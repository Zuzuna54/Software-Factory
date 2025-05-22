"""align_artifact_project_models_and_add_project_table

Revision ID: 475d3e0ba8c8
Revises: 004_add_conversation_model
Create Date: 2025-05-18 04:34:14.911525

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import uuid
from sqlalchemy.dialects.postgresql import UUID as PG_UUID  # Renamed to avoid clash
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision = "475d3e0ba8c8"
down_revision = "004_add_conversation_model"
branch_labels = None
depends_on = None


def upgrade() -> None:
    print(
        f"Running upgrade for migration {revision} (Ensure 'projects' table exists ONLY - using has_table check)"
    )
    bind = op.get_bind()
    if not bind.dialect.has_table(bind, "projects"):
        print("    Table 'projects' does not exist. Creating...")
        try:
            op.create_table(
                "projects",
                sa.Column("project_id", PG_UUID(as_uuid=True), nullable=False),
                sa.Column("name", sa.String(length=255), nullable=False),
                sa.Column("description", sa.Text(), nullable=True),
                sa.Column(
                    "created_at",
                    sa.DateTime(),
                    nullable=False,
                    server_default=sa.text("now()"),
                ),
                sa.Column(
                    "updated_at",
                    sa.DateTime(),
                    nullable=False,
                    server_default=sa.text("now()"),
                    onupdate=sa.text("now()"),
                ),
                sa.PrimaryKeyConstraint("project_id"),
                sa.UniqueConstraint("name"),
            )
            print("    Table 'projects' created successfully.")
        except Exception as e:
            print(f"    Error during 'projects' table creation: {e}")
            raise
    else:
        print("    Table 'projects' already exists. Skipping creation.")
    print(
        f"Upgrade for migration {revision} (Ensure 'projects' table exists ONLY) completed."
    )


def downgrade() -> None:
    print(
        f"Running downgrade for migration {revision} (Drop 'projects' table ONLY - using has_table check)"
    )
    bind = op.get_bind()
    if bind.dialect.has_table(bind, "projects"):
        print("    Table 'projects' exists. Dropping...")
        try:
            op.drop_table("projects")
            print("    Table 'projects' dropped successfully.")
        except Exception as e:
            print(f"    Error during 'projects' table drop: {e}")
            raise
    else:
        print("    Table 'projects' does not exist. Skipping drop.")
    print(f"Downgrade for migration {revision} (Drop 'projects' table ONLY) completed.")
