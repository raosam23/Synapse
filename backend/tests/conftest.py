"""Shared pytest fixtures for backend unit tests."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.core.config import settings
from app.main import app
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


def _truncate_api_tables() -> None:
    if not settings.DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not configured")
    sync_url = settings.DATABASE_URL.replace(
        "postgresql+asyncpg://", "postgresql+psycopg://"
    )
    engine = create_engine(sync_url)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                TRUNCATE TABLE task_dependencies, tasks, team_members, revoked_tokens, users
                RESTART IDENTITY CASCADE;
                """
            )
        )


@pytest.fixture
def api_client():
    with TestClient(app) as test_client:
        yield test_client
    _truncate_api_tables()
