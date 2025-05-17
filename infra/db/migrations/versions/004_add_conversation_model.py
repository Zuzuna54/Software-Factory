"""Add conversation model

Revision ID: 004_add_conversation_model
Create Date: 2024-05-17 14:30:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID

# revision identifiers, used by Alembic.
revision = "004_add_conversation_model"
down_revision = "003_fix_model_relationships"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create the conversations table
    op.create_table(
        "conversations",
        sa.Column("conversation_id", UUID, primary_key=True),
        sa.Column(
            "created_at", sa.DateTime, nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.Column("topic", sa.String(255), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("participant_ids", ARRAY(UUID), nullable=True),
        sa.Column(
            "extra_data", JSONB, nullable=True
        ),  # Changed from metadata to avoid conflict with SQLAlchemy
    )

    # Create an index on conversation_id
    op.create_index("ix_conversations_id", "conversations", ["conversation_id"])

    # Create an index on status
    op.create_index("ix_conversations_status", "conversations", ["status"])

    # First, populate conversations table with existing conversation data from agent_messages
    op.execute(
        """
    DO $$
    BEGIN
        -- Insert conversations from distinct conversation_ids in agent_messages
        INSERT INTO conversations (conversation_id, created_at, topic, status)
        SELECT DISTINCT 
            (extra_data->>'conversation_id')::uuid AS conversation_id,
            MIN(created_at) AS created_at,
            'Imported conversation' AS topic,
            'active' AS status
        FROM agent_messages
        WHERE extra_data->>'conversation_id' IS NOT NULL
        GROUP BY extra_data->>'conversation_id';
    END $$;
    """
    )

    # Now add a direct conversation_id column to agent_messages table
    op.execute(
        """
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_name='agent_messages' AND column_name='conversation_id'
        ) THEN
            ALTER TABLE agent_messages ADD COLUMN conversation_id UUID REFERENCES conversations(conversation_id);
        END IF;
    END $$;
    """
    )

    # Create an index on conversation_id in agent_messages
    op.execute(
        """
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1
            FROM pg_indexes
            WHERE tablename = 'agent_messages' AND indexname = 'ix_agent_messages_conversation_id'
        ) THEN
            CREATE INDEX ix_agent_messages_conversation_id ON agent_messages (conversation_id);
        END IF;
    END $$;
    """
    )

    # Now update agent_messages with conversation_id from extra_data
    op.execute(
        """
    DO $$
    BEGIN
        -- Update the conversation_id column from extra_data field where possible
        UPDATE agent_messages
        SET conversation_id = (extra_data->>'conversation_id')::uuid
        WHERE extra_data->>'conversation_id' IS NOT NULL
          AND conversation_id IS NULL
          AND EXISTS (
              SELECT 1 FROM conversations 
              WHERE conversations.conversation_id = (agent_messages.extra_data->>'conversation_id')::uuid
          );
    END $$;
    """
    )


def downgrade() -> None:
    # Remove the conversation_id column from agent_messages
    op.execute(
        """
    DO $$
    BEGIN
        IF EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_name='agent_messages' AND column_name='conversation_id'
        ) THEN
            ALTER TABLE agent_messages DROP COLUMN conversation_id;
        END IF;
    END $$;
    """
    )

    # Drop the conversations table
    op.drop_table("conversations")
