"""add_url_to_artifacts

Revision ID: 3f3256263e41
Revises: 5f9c8474a002
Create Date: 2025-05-18 04:45:45.223733

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "3f3256263e41"
down_revision = "5f9c8474a002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    print(f"Running upgrade for migration {revision} (Add url to artifacts)")
    try:
        op.add_column("artifacts", sa.Column("url", sa.String(), nullable=True))
        print("    Column 'url' added to 'artifacts' table.")
    except Exception as e:
        print(f"    Error during upgrade {revision}: {e}")
        raise
    print(f"Upgrade for migration {revision} completed.")


def downgrade() -> None:
    print(f"Running downgrade for migration {revision} (Remove url from artifacts)")
    try:
        op.drop_column("artifacts", "url")
        print("    Column 'url' dropped from 'artifacts' table.")
    except Exception as e:
        print(f"    Error during downgrade {revision}: {e}")
        raise
    print(f"Downgrade for migration {revision} completed.")
