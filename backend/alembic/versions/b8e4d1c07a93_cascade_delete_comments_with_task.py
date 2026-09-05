"""cascade delete comments with task

Revision ID: b8e4d1c07a93
Revises: c967607de137
Create Date: 2026-09-06 01:01:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b8e4d1c07a93"
down_revision: str | Sequence[str] | None = "c967607de137"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint("comments_task_id_fkey", "comments", type_="foreignkey")
    op.create_foreign_key(
        "fk_comments_task_id_tasks",
        "comments",
        "tasks",
        ["task_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("fk_comments_task_id_tasks", "comments", type_="foreignkey")
    op.create_foreign_key(
        "comments_task_id_fkey",
        "comments",
        "tasks",
        ["task_id"],
        ["id"],
    )
