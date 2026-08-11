"""Pydantic schemas for tasks."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.task import TaskStatus


class TaskCreate(BaseModel):
    """Pydantic schema for creating a task."""

    title: str = Field(description="The title of the task.", min_length=1)
    description: str | None = Field(
        description="The description of the task.", default=None
    )
    assignee_id: UUID | None = Field(
        description="The assignee id of the task.", default=None
    )
    sprint_id: UUID | None = Field(
        description="The sprint id of the task.", default=None
    )
    status: TaskStatus = Field(
        description="The status of the task.", default=TaskStatus.BACKLOG
    )
    story_points: int | None = Field(
        description="The story points of the task", default=None
    )
    risk_flag: bool | None = Field(
        description="The risk flag of the task", default=None
    )


class TaskRead(BaseModel):
    """Pydantic schema for reading a task."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(description="The id of the task.")
    title: str = Field(description="The title of the task.")
    description: str | None = Field(
        description="The description of the task.", default=None
    )
    assignee_id: UUID | None = Field(
        description="The assignee id of the task.", default=None
    )
    sprint_id: UUID | None = Field(
        description="The sprint id of the task.", default=None
    )
    status: TaskStatus = Field(description="The status of the task.")
    story_points: int | None = Field(
        description="The story points of the task.", default=None
    )
    risk_flag: bool | None = Field(
        description="The risk flag of the task.", default=None
    )


class TaskUpdate(BaseModel):
    """Pydantic schema for updating a task."""

    title: str | None = Field(
        description="The title of the task to update.", default=None, min_length=1
    )
    description: str | None = Field(
        description="The description of the task to update.", default=None
    )
    assignee_id: UUID | None = Field(
        description="The assignee id of the task to update.", default=None
    )
    sprint_id: UUID | None = Field(
        description="The sprint id of the task to update.", default=None
    )
    status: TaskStatus | None = Field(
        description="The status of the task to update.", default=None
    )
    story_points: int | None = Field(
        description="The story points of the task to update.", default=None
    )
    risk_flag: bool | None = Field(
        description="The risk flag of the task to update.", default=None
    )

    @field_validator("title", "status", mode="before")
    @classmethod
    def reject_null(cls, value: Any) -> Any:
        """Reject null values for the title and status fields."""
        if value is None:
            raise ValueError(
                "Null is not allowed, omit the field to leave it unchanged",
            )
        return value
