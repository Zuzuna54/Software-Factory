"""Convert high dimensional vectors to halfvec

Revision ID: 865de94d37c6
Revises: 001_initial_schema
Create Date: 2025-05-16 20:44:05.166146

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision = "865de94d37c6"
down_revision = "001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # First, drop existing vector indexes if they exist
    op.execute("DROP INDEX IF EXISTS ix_agent_messages_context_vector")
    op.execute("DROP INDEX IF EXISTS ix_artifacts_content_vector")

    # Convert vector columns to halfvec
    op.execute(
        "ALTER TABLE agent_messages ALTER COLUMN context_vector TYPE halfvec(3072) USING context_vector::halfvec(3072)"
    )
    op.execute(
        "ALTER TABLE artifacts ALTER COLUMN content_vector TYPE halfvec(3072) USING content_vector::halfvec(3072)"
    )

    # Create new HNSW indexes using halfvec_cosine_ops
    op.execute(
        """
        CREATE INDEX ix_agent_messages_context_vector ON agent_messages 
        USING hnsw (context_vector halfvec_cosine_ops) 
        WITH (m=16, ef_construction=64)
    """
    )
    op.execute(
        """
        CREATE INDEX ix_artifacts_content_vector ON artifacts 
        USING hnsw (content_vector halfvec_cosine_ops) 
        WITH (m=16, ef_construction=64)
    """
    )


def downgrade() -> None:
    # Drop halfvec indexes
    op.execute("DROP INDEX IF EXISTS ix_agent_messages_context_vector")
    op.execute("DROP INDEX IF EXISTS ix_artifacts_content_vector")

    # Convert back to regular vector type
    op.execute(
        "ALTER TABLE agent_messages ALTER COLUMN context_vector TYPE vector(3072) USING context_vector::vector(3072)"
    )
    op.execute(
        "ALTER TABLE artifacts ALTER COLUMN content_vector TYPE vector(3072) USING content_vector::vector(3072)"
    )

    # Create vector indexes with vector_cosine_ops
    op.execute(
        """
        CREATE INDEX ix_agent_messages_context_vector ON agent_messages 
        USING hnsw (context_vector vector_cosine_ops) 
        WITH (m=16, ef_construction=64)
    """
    )
    op.execute(
        """
        CREATE INDEX ix_artifacts_content_vector ON artifacts 
        USING hnsw (content_vector vector_cosine_ops) 
        WITH (m=16, ef_construction=64)
    """
    )
