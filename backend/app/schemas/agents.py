"""Schemas for the agents."""

from uuid import UUID

from pydantic import BaseModel, Field


class BacklogTaskDraft(BaseModel):
    """Pydantic schema for a backlog task draft."""

    title: str = Field(
        description=(
            "GitHub-style issue title, e.g. '[Feature]: Comment model + CRUD API'. "
            "Name the gap, not a generic setup step."
        ),
        min_length=1,
    )
    description: str = Field(
        description=(
            "Full GitHub issue body in markdown with headings: Description, "
            "Required behavior, Acceptance criteria (checkboxes - [ ]), Out of scope, "
            "Related requirement, optional Sequence. Several paragraphs, not one line."
        ),
        min_length=700,
    )
    story_points: int | None = Field(
        description=(
            "Fibonacci-ish effort (1,2,3,5,8,13) matching the description. "
            "Omit if unknown. Do not use 8 for trivial work."
        ),
        default=None,
        ge=1,
    )


class RequirementAnalysis(BaseModel):
    """Pydantic schema for a requirement analysis."""

    opinion: str = Field(
        description="The opinion of the requirement analysis.", min_length=1
    )
    tasks: list[BacklogTaskDraft] = Field(
        description="The tasks that are part of the requirement analysis."
    )


class SprintAssignment(BaseModel):
    """Pydantic schema for a sprint assignment."""

    task_id: UUID
    member_id: UUID


class SprintPlan(BaseModel):
    """Pydantic schema for a sprint plan."""

    assignments: list[SprintAssignment]
