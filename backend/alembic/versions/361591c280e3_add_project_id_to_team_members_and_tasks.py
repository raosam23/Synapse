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
    op.add_column("tasks", sa.Column("project_id", sa.Uuid(), nullable=True))
    op.add_column("team_members", sa.Column("project_id", sa.Uuid(), nullable=True))

    # Prefer the row owner's first project, then any project, then drop leftovers.
    op.execute(
        """
        UPDATE tasks AS t
        SET project_id = (
            SELECT p.id
            FROM projects AS p
            WHERE p.created_by_id = t.created_by_id
            ORDER BY p.created_at
            LIMIT 1
        )
        WHERE t.project_id IS NULL
        """
    )
    op.execute(
        """
        UPDATE tasks
        SET project_id = (SELECT id FROM projects ORDER BY created_at LIMIT 1)
        WHERE project_id IS NULL
        """
    )
    op.execute(
        """
        UPDATE team_members AS tm
        SET project_id = (
            SELECT p.id
            FROM projects AS p
            WHERE tm.user_id IS NOT NULL
              AND p.created_by_id = tm.user_id
            ORDER BY p.created_at
            LIMIT 1
        )
        WHERE tm.project_id IS NULL
        """
    )
    op.execute(
        """
        UPDATE team_members
        SET project_id = (SELECT id FROM projects ORDER BY created_at LIMIT 1)
        WHERE project_id IS NULL
        """
    )
    op.execute(
        """
        DELETE FROM task_dependencies
        WHERE from_task_id IN (SELECT id FROM tasks WHERE project_id IS NULL)
           OR to_task_id IN (SELECT id FROM tasks WHERE project_id IS NULL)
        """
    )
    op.execute(
        """
        UPDATE tasks
        SET assignee_id = NULL
        WHERE assignee_id IN (
            SELECT id FROM team_members WHERE project_id IS NULL
        )
        """
    )
    op.execute("DELETE FROM tasks WHERE project_id IS NULL")
    op.execute("DELETE FROM team_members WHERE project_id IS NULL")

    op.alter_column(
        "tasks",
        "project_id",
        existing_type=sa.Uuid(),
        nullable=False,
    )
    op.alter_column(
        "team_members",
        "project_id",
        existing_type=sa.Uuid(),
        nullable=False,
    )
    op.create_foreign_key(
        "fk_tasks_project_id_projects",
        "tasks",
        "projects",
        ["project_id"],
        ["id"],
    )
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
    op.drop_constraint("fk_tasks_project_id_projects", "tasks", type_="foreignkey")

    # This revision allows the same user on two projects. The previous unique
    # was global on user_id, so extra seats must be removed first.
    op.execute(
        """
        UPDATE tasks
        SET assignee_id = NULL
        WHERE assignee_id IN (
            SELECT id FROM (
                SELECT id,
                       ROW_NUMBER() OVER (
                           PARTITION BY user_id ORDER BY id
                       ) AS rn
                FROM team_members
                WHERE user_id IS NOT NULL
            ) ranked
            WHERE rn > 1
        )
        """
    )
    op.execute(
        """
        DELETE FROM team_members
        WHERE id IN (
            SELECT id FROM (
                SELECT id,
                       ROW_NUMBER() OVER (
                           PARTITION BY user_id ORDER BY id
                       ) AS rn
                FROM team_members
                WHERE user_id IS NOT NULL
            ) ranked
            WHERE rn > 1
        )
        """
    )

    op.create_unique_constraint("uq_team_members_user_id", "team_members", ["user_id"])
    op.drop_column("team_members", "project_id")
    op.drop_column("tasks", "project_id")
