"""SQLModel schema for projects."""

from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import Column
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, SQLModel


class ProjectStatus(str, Enum):
    """Project status enum."""

    PLANNING = "planning"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Project(SQLModel, table=True):
    """SQLModel schema for projects."""

    __tablename__ = "projects"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(nullable=False)
    requirements: str = Field(nullable=False)
    duration_weeks: int = Field(nullable=False)
    sprint_length_weeks: int = Field(default=2)
    status: ProjectStatus = Field(
        default=ProjectStatus.PLANNING,
        sa_column=Column(
            SAEnum(
                ProjectStatus,
                name="projectstatus",
                values_callable=lambda enum: [item.value for item in enum],
            ),
            nullable=False,
        ),
    )
    ai_opinion: str | None = Field(default=None)
    created_by_id: UUID = Field(foreign_key="users.id", default=None)
    created_at: datetime = Field(default_factory=datetime.now, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.now, nullable=False)
