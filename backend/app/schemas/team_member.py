"""Pydantic schemas for team members."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TeamMemberCreate(BaseModel):
    """Pydantic schema for creating a team member."""

    name: str = Field(description="The name of the team member.", min_length=1)
    skills: list[str] = Field(
        description="The skills of the team member.", default_factory=list
    )


class TeamMemberUpdate(BaseModel):
    """Pydantic schema for updating a team member."""

    name: str | None = Field(
        description="The name of the team member to update.", min_length=1, default=None
    )
    skills: list[str] | None = Field(
        description="The skills of the team member to update.", default=None
    )


class TeamMemberRead(BaseModel):
    """Pydantic schema for reading a team member."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(description="The id of the team member.")
    name: str = Field(description="The name of the team member.")
    skills: list[str] = Field(description="The list of skills of the team member.")
