"""Pydantic schemas for projects."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.project import ProjectStatus


class ProjectCreate(BaseModel):
    """Pydantic schema for creating a project."""

    name: str = Field(
        description="The name of the project.",
        min_length=1,
    )
    requirements: str = Field(
        description="The requirements of the project.", min_length=1
    )
    duration_weeks: int = Field(
        description="The duration of the project in weeks.", ge=1
    )
    status: ProjectStatus = Field(
        description="The status of the project.", default=ProjectStatus.PLANNING
    )


class ProjectRead(BaseModel):
    """Pydantic schema for reading a project."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(description="The id of the project.")
    name: str = Field(description="The name of the project.")
    requirements: str = Field(description="The requirements of the project.")
    duration_weeks: int = Field(description="The duration of the project in weeks.")
    created_by_id: UUID = Field(
        description="The id of the user who created this project."
    )
    sprint_length_weeks: int = Field(
        description="The duration of the sprints in weeks."
    )
    status: ProjectStatus = Field(description="The status of the project.")
    ai_opinion: str | None = Field(description="The AI opinion of the project")
    created_at: datetime = Field(
        description="The date and time the project was created."
    )
    updated_at: datetime = Field(
        description="The date and time the project was last updated"
    )


class ProjectUpdate(BaseModel):
    """Pydantic schema for updating a project."""

    name: str | None = Field(
        description="The name of the project to update.",
        default=None,
        min_length=1,
    )
    requirements: str | None = Field(
        description="the requirements of the project to update.",
        default=None,
        min_length=1,
    )
    duration_weeks: int | None = Field(
        description="the duration of the project to update in weeks.",
        default=None,
        ge=1,
    )
    status: ProjectStatus | None = Field(
        description="the status of the project to update.", default=None
    )
    ai_opinion: str | None = Field(
        description="the ai opinion of the project to update.", default=None
    )

    @field_validator("requirements", "status", "name", mode="before")
    @classmethod
    def reject_null(cls, value: Any) -> Any:
        """Reject null values for the requirements, status and name fields."""
        if value is None:
            raise ValueError(
                "Null is not allowed, omit the field to leave it unchanged"
            )
        return value
