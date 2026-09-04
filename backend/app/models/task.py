"""SQLModel schema for tasks."""

from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import Column
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, SQLModel


class TaskStatus(str, Enum):
    """Task status enum."""

    BACKLOG = "backlog"
    TODO = "todo"
    DOING = "doing"
    DONE = "done"


class Task(SQLModel, table=True):
    """SQLModel schema for tasks."""

    __tablename__ = "tasks"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    title: str = Field(nullable=False)
    sprint_id: UUID | None = None
    description: str | None = None
    status: TaskStatus = Field(
        default=TaskStatus.BACKLOG,
        sa_column=Column(
            SAEnum(
                TaskStatus,
                name="taskstatus",
                values_callable=lambda enum: [item.value for item in enum],
            ),
            nullable=False,
        ),
    )
    assignee_id: UUID | None = Field(foreign_key="team_members.id", default=None)
    story_points: int | None = None
    risk_flag: bool | None = None
    created_by_id: UUID | None = Field(foreign_key="users.id", default=None)
    created_at: datetime = Field(default_factory=datetime.now, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.now, nullable=False)
    project_id: UUID = Field(foreign_key="projects.id")
