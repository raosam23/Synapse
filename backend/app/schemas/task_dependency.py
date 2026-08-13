"""Pydantic schemas for task dependencies."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TaskDependencyCreate(BaseModel):
    """Schema for creating a task dependency."""

    from_task_id: UUID = Field(description="The ID of the task that must finish first.")
    to_task_id: UUID = Field(
        description="The ID of the task that depends on from_task_id."
    )

    @model_validator(mode="after")
    def reject_self_link(self) -> "TaskDependencyCreate":
        """Reject self-linking dependencies."""
        if self.from_task_id == self.to_task_id:
            raise ValueError("from_task_id and to_task_id cannot be the same.")
        return self


class TaskDependencyRead(BaseModel):
    """Schema for reading a task dependency."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(description="The ID of the task dependency.")
    from_task_id: UUID = Field(description="The ID of the task that must finish first.")
    to_task_id: UUID = Field(
        description="The ID of the task that depends on from_task_id."
    )
