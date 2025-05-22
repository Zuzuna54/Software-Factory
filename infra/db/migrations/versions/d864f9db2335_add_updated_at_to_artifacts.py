"""add_updated_at_to_artifacts

Revision ID: d864f9db2335
Revises: a9e3fdb8a3d0
Create Date: 2025-05-18 04:47:44.090748

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "d864f9db2335"
down_revision = "a9e3fdb8a3d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    print(f"Running upgrade for migration {revision} (Add updated_at to artifacts)")
    try:
        op.add_column(
            "artifacts",
            sa.Column(
                "updated_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("now()"),
            ),
        )
        print(
            "    Column 'updated_at' added to 'artifacts' table with server_default=now()."
        )
    except Exception as e:
        print(f"    Error during upgrade {revision}: {e}")
        raise
    print(f"Upgrade for migration {revision} completed.")


def downgrade() -> None:
    print(
        f"Running downgrade for migration {revision} (Remove updated_at from artifacts)"
    )
    try:
        op.drop_column("artifacts", "updated_at")
        print("    Column 'updated_at' dropped from 'artifacts' table.")
    except Exception as e:
        print(f"    Error during downgrade {revision}: {e}")
        raise
    print(f"Downgrade for migration {revision} completed.")
