"""SQLModel schema for comments."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class Comment(SQLModel, table=True):
    """SQLModel schema for comments."""

    __tablename__ = "comments"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    task_id: UUID = Field(foreign_key="tasks.id", nullable=False, ondelete="CASCADE")
    body: str = Field(nullable=False)
    user_id: UUID | None = Field(default=None, foreign_key="users.id")
    is_ai: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.now, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.now, nullable=False)
