"""add_project_id_to_artifacts_and_fk

Revision ID: ce13371d1891
Revises: 475d3e0ba8c8
Create Date: 2025-05-18 04:42:50.455354

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision = "ce13371d1891"
down_revision = "475d3e0ba8c8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    print(
        f"Running upgrade for migration {revision} (Add project_id to artifacts and FK)"
    )
    try:
        op.add_column(
            "artifacts", sa.Column("project_id", UUID(as_uuid=True), nullable=True)
        )
        print("    Column 'project_id' added to 'artifacts' table.")

        op.create_foreign_key(
            "fk_artifacts_project_id",  # Constraint name
            "artifacts",  # Source table
            "projects",  # Referenced table
            ["project_id"],  # Local columns
            ["project_id"],  # Remote columns
            ondelete="CASCADE",  # Optional: Specify ondelete behavior
        )
        print(
            "    Foreign key 'fk_artifacts_project_id' created on 'artifacts.project_id' -> 'projects.project_id'."
        )

        # Optionally, if you want to make project_id NOT NULL after populating existing rows (requires a separate step/migration)
        # print("    IMPORTANT: If project_id should be NOT NULL, existing rows must be populated, then alter column.")

    except Exception as e:
        print(f"    Error during upgrade {revision}: {e}")
        raise
    print(f"Upgrade for migration {revision} completed.")


def downgrade() -> None:
    print(
        f"Running downgrade for migration {revision} (Remove project_id from artifacts and FK)"
    )
    try:
        op.drop_constraint("fk_artifacts_project_id", "artifacts", type_="foreignkey")
        print(
            "    Foreign key 'fk_artifacts_project_id' dropped from 'artifacts' table."
        )

        op.drop_column("artifacts", "project_id")
        print("    Column 'project_id' dropped from 'artifacts' table.")

    except Exception as e:
        print(f"    Error during downgrade {revision}: {e}")
        raise
    print(f"Downgrade for migration {revision} completed.")
