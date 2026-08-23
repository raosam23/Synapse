"""SQLModel schemas for the Users."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    """User model."""

    __tablename__ = "users"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    email: str = Field(unique=True, index=True)
    password_hash: str = Field(nullable=False)
    name: str | None = None
    created_at: datetime = Field(default_factory=datetime.now, nullable=False)
