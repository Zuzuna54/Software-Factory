"""add_description_to_artifacts

Revision ID: 5f9c8474a002
Revises: ce13371d1891
Create Date: 2025-05-18 04:44:33.344510

"""

from alembic import op
import sqlalchemy as sa
import uuid

# Remove JSONB, ARRAY, VECTOR if present, keep UUID if needed (not for this migration)


# revision identifiers, used by Alembic.
revision = "5f9c8474a002"
down_revision = "ce13371d1891"
branch_labels = None
depends_on = None


def upgrade() -> None:
    print(f"Running upgrade for migration {revision} (Add description to artifacts)")
    try:
        op.add_column("artifacts", sa.Column("description", sa.Text(), nullable=True))
        print("    Column 'description' added to 'artifacts' table.")
    except Exception as e:
        print(f"    Error during upgrade {revision}: {e}")
        raise
    print(f"Upgrade for migration {revision} completed.")


def downgrade() -> None:
    print(
        f"Running downgrade for migration {revision} (Remove description from artifacts)"
    )
    try:
        op.drop_column("artifacts", "description")
        print("    Column 'description' dropped from 'artifacts' table.")
    except Exception as e:
        print(f"    Error during downgrade {revision}: {e}")
        raise
    print(f"Downgrade for migration {revision} completed.")
