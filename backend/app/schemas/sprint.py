"""Pydantic schemas for sprints."""

from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SprintCreate(BaseModel):
    """Pydantic schema for creating a sprint."""

    project_id: UUID = Field(description="The id of the project the sprint is part of.")
    start_date: date = Field(description="The start date of the first sprint.")


class SprintRead(BaseModel):
    """Pydantic schema for reading a sprint."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(description="The id of the sprint.")
    project_id: UUID = Field(
        description="The id of the project the sprint is a part of."
    )
    index: int = Field(description="The index of the sprint.")
    start_date: date = Field(description="The start date of the sprint.")
    end_date: date = Field(description="The end date of the sprint.")
