"""Authentication schemas for the application."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    """Request schema for registering a new user."""

    email: EmailStr = Field(
        description="The email of the user. Must be a valid email address"
    )
    password: str = Field(
        min_length=8,
        max_length=72,
        description="The password of the user. Must be at least 8 characters long and less than 72 characters.",
    )
    name: str | None = Field(description="The name of the user", default=None)


class LoginRequest(BaseModel):
    """Request schema for logging in a user."""

    email: EmailStr = Field(
        description="The email of the user. Must be a valid email address"
    )
    password: str = Field(
        description="The password of the user", min_length=8, max_length=72
    )


class TokenResponse(BaseModel):
    """Response schema for the token."""

    access_token: str = Field(description="The access token for the user")
    token_type: str = Field(description="The type of the token", default="bearer")


class UserRead(BaseModel):
    """Response schema for the user."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(description="The unique identifier of the user")
    email: EmailStr = Field(description="The email of the user")
    name: str | None = Field(description="The name of the user", default=None)
    created_at: datetime = Field(description="The date and time the user was created")
