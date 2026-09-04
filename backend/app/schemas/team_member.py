"""Pydantic schemas for team members."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TeamMemberCreate(BaseModel):
    """Pydantic schema for creating a team member."""

    skills: list[str] = Field(
        description="The skills of the team member.", default_factory=list
    )
    user_id: UUID = Field(description="The id of the person who is a team member.")
    project_id: UUID = Field(
        description="The id of the project the team member is part of."
    )


class TeamMemberUpdate(BaseModel):
    """Pydantic schema for updating a team member (omit fields; do not send null)."""

    skills: list[str] | None = Field(
        description="The skills of the team member to update.", default=None
    )

    @field_validator("skills", mode="before")
    @classmethod
    def reject_null(cls, value: Any) -> Any:
        if value is None:
            raise ValueError(
                "null is not allowed; omit the field to leave it unchanged"
            )
        return value


class TeamMemberRead(BaseModel):
    """Pydantic schema for reading a team member."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(description="The id of the team member.")
    name: str = Field(
        description="The display name from the linked user (name or email)."
    )
    skills: list[str] = Field(description="The list of skills of the team member.")
    user_id: UUID | None = Field(
        description="The id of the person who is a team member.", default=None
    )
    project_id: UUID = Field(
        description="The id of the project the team member is a part of."
    )
