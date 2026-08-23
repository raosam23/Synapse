"""Shared pytest fixtures for backend unit tests."""

from uuid import uuid4

import pytest

from app.models.user import User


@pytest.fixture
def current_user() -> User:
    """A fake authenticated user, used to satisfy the `CurrentUser` dependency
    on route functions that are called directly (bypassing FastAPI's DI)."""
    return User(
        id=uuid4(),
        email="test.user@example.com",
        password_hash="not-a-real-hash",
        name="Test User",
    )
