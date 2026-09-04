"""SQLModel schema for team members."""

from uuid import UUID, uuid4

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel, UniqueConstraint


class TeamMember(SQLModel, table=True):
    """SQLModel schema for team members."""

    __tablename__ = "team_members"
    __table_args__ = (
        UniqueConstraint("user_id", "project_id", name="uq_team_member_project_user"),
    )
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    skills: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False, server_default="[]"),
    )
    user_id: UUID | None = Field(default=None, foreign_key="users.id")
    project_id: UUID = Field(foreign_key="projects.id")
