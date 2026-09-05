"""Shared pytest fixtures for backend unit tests."""

from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

import pytest
from alembic.command import upgrade as alembic_upgrade
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.db import session as db_session
from app.main import app
from app.models.user import User

# Default local uvicorn / Swagger database from .env.example. Pytest must never
# truncate this; use TEST_DATABASE_URL → synapse_test instead.
_LOCAL_DEV_DATABASE_NAME = "synapse_db"


def _database_name(url: str) -> str:
    return urlparse(url).path.lstrip("/").split("?")[0]


def pytest_configure(config: pytest.Config) -> None:
    """Point the process at the test database before any TestClient or truncate."""
    test_url = settings.TEST_DATABASE_URL or settings.DATABASE_URL
    if not test_url:
        raise pytest.UsageError(
            "Set TEST_DATABASE_URL (local pytest) or DATABASE_URL (CI)."
        )
    if _database_name(test_url) == _LOCAL_DEV_DATABASE_NAME:
        raise pytest.UsageError(
            "Pytest refused to use database 'synapse_db' (local uvicorn/Swagger data). "
            "Set TEST_DATABASE_URL to a dedicated database such as synapse_test. "
            "See .env.example."
        )
    settings.DATABASE_URL = test_url


def pytest_sessionstart(session: pytest.Session) -> None:
    """Apply migrations to the test database so `uv run pytest` is enough locally."""
    if not settings.DATABASE_URL:
        raise pytest.UsageError("DATABASE_URL is not configured")
    sync_url = settings.DATABASE_URL.replace(
        "postgresql+asyncpg://", "postgresql+psycopg://"
    )
    try:
        engine = create_engine(sync_url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        raise pytest.UsageError(
            "Cannot connect to the pytest database. Create it with:\n"
            '  docker compose exec database psql -U "$POSTGRES_USER" '
            "-c 'CREATE DATABASE synapse_test;'\n"
            f"({exc})"
        ) from exc

    backend_root = Path(__file__).resolve().parents[1]
    alembic_cfg = Config(str(backend_root / "alembic.ini"))
    alembic_upgrade(alembic_cfg, "head")


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
                TRUNCATE TABLE comments, task_dependencies, tasks, sprints, team_members, projects, revoked_tokens, users
                RESTART IDENTITY CASCADE;
                """
            )
        )


def _use_nullpool_engine() -> None:
    """TestClient uses a new event loop per test; NullPool avoids reusing
    asyncpg connections bound to the previous loop. Production keeps a pool.
    """
    if not settings.DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not configured")
    db_session.async_engine = create_async_engine(
        settings.DATABASE_URL, echo=True, poolclass=NullPool
    )
    db_session.AsyncSessionLocal = async_sessionmaker(
        db_session.async_engine, expire_on_commit=False
    )


@pytest.fixture
def api_client():
    _use_nullpool_engine()
    with TestClient(app) as test_client:
        yield test_client
    _truncate_api_tables()
