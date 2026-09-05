"""SQLModel schema for sprints."""

from datetime import date
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel, UniqueConstraint


class Sprint(SQLModel, table=True):
    """Sprint model for Sprint."""

    __tablename__ = "sprints"
    __table_args__ = (
        UniqueConstraint("project_id", "index", name="uix_project_index_unique"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    project_id: UUID = Field(foreign_key="projects.id", nullable=False)
    index: int = Field(nullable=False)
    start_date: date = Field(nullable=False)
    end_date: date = Field(nullable=False)
