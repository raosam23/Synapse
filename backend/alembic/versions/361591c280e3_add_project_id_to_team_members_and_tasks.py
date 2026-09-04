"""add project_id to team_members and tasks

Revision ID: 361591c280e3
Revises: 2314653ed57a
Create Date: 2026-09-04 16:11:28.583507

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "361591c280e3"
down_revision: str | Sequence[str] | None = "2314653ed57a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("tasks", sa.Column("project_id", sa.Uuid(), nullable=False))
    op.create_foreign_key(
        "fk_tasks_project_id_projects",
        "tasks",
        "projects",
        ["project_id"],
        ["id"],
    )
    op.add_column("team_members", sa.Column("project_id", sa.Uuid(), nullable=False))
    op.drop_constraint("uq_team_members_user_id", "team_members", type_="unique")
    op.create_unique_constraint(
        "uq_team_member_project_user",
        "team_members",
        ["user_id", "project_id"],
    )
    op.create_foreign_key(
        "fk_team_members_project_id_projects",
        "team_members",
        "projects",
        ["project_id"],
        ["id"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "fk_team_members_project_id_projects",
        "team_members",
        type_="foreignkey",
    )
    op.drop_constraint("uq_team_member_project_user", "team_members", type_="unique")
    op.create_unique_constraint("uq_team_members_user_id", "team_members", ["user_id"])
    op.drop_column("team_members", "project_id")
    op.drop_constraint("fk_tasks_project_id_projects", "tasks", type_="foreignkey")
    op.drop_column("tasks", "project_id")
