"""SQLModel schema for team members."""

from uuid import UUID, uuid4

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class TeamMember(SQLModel, table=True):
    """SQLModel schema for team members."""

    __tablename__ = "team_members"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str
    skills: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False, server_default="[]"),
    )
