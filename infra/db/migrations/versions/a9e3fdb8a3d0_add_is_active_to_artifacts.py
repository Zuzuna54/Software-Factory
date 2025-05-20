"""add_is_active_to_artifacts

Revision ID: a9e3fdb8a3d0
Revises: 3f3256263e41
Create Date: 2025-05-18 04:46:50.441768

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "a9e3fdb8a3d0"
down_revision = "3f3256263e41"
branch_labels = None
depends_on = None


def upgrade() -> None:
    print(f"Running upgrade for migration {revision} (Add is_active to artifacts)")
    try:
        op.add_column(
            "artifacts",
            sa.Column(
                "is_active", sa.Boolean(), nullable=False, server_default=sa.true()
            ),
        )
        print(
            "    Column 'is_active' added to 'artifacts' table with server_default=True."
        )
    except Exception as e:
        print(f"    Error during upgrade {revision}: {e}")
        raise
    print(f"Upgrade for migration {revision} completed.")


def downgrade() -> None:
    print(
        f"Running downgrade for migration {revision} (Remove is_active from artifacts)"
    )
    try:
        op.drop_column("artifacts", "is_active")
        print("    Column 'is_active' dropped from 'artifacts' table.")
    except Exception as e:
        print(f"    Error during downgrade {revision}: {e}")
        raise
    print(f"Downgrade for migration {revision} completed.")
