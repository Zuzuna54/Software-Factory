"""Fix model relationships

Revision ID: 003_fix_model_relationships
Create Date: 2023-12-11 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = "003_fix_model_relationships"
down_revision = "002_align_models_with_db"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add a column meeting_id to agent_messages if it doesn't exist.
    # Check if column exists first
    op.execute(
        """
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_name='agent_messages' AND column_name='meeting_id'
        ) THEN
            ALTER TABLE agent_messages ADD COLUMN meeting_id UUID REFERENCES meetings(meeting_id);
        END IF;
    END $$;
    """
    )

    # Create an index on meeting_id if it doesn't exist
    op.execute(
        """
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1
            FROM pg_indexes
            WHERE tablename = 'agent_messages' AND indexname = 'ix_agent_messages_meeting_id'
        ) THEN
            CREATE INDEX ix_agent_messages_meeting_id ON agent_messages (meeting_id);
        END IF;
    END $$;
    """
    )


def downgrade() -> None:
    # We don't actually remove the column in downgrade since it might cause data loss
    # and it's better to have the column than not have it
    pass
