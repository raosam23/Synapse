"""add sprints table and task sprint_id fk

Revision ID: 2ceb8997778b
Revises: 4c8dee595b3f
Create Date: 2026-09-05 10:45:46.493022

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2ceb8997778b"
down_revision: str | Sequence[str] | None = "4c8dee595b3f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "sprints",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("index", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "index", name="uix_project_index_unique"),
    )
    # Existing sprint_id values are untyped UUIDs; none can point at sprints yet.
    op.execute("UPDATE tasks SET sprint_id = NULL WHERE sprint_id IS NOT NULL")
    op.create_foreign_key(
        "fk_tasks_sprint_id_sprints",
        "tasks",
        "sprints",
        ["sprint_id"],
        ["id"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("fk_tasks_sprint_id_sprints", "tasks", type_="foreignkey")
    op.drop_table("sprints")
