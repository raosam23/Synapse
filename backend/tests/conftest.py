"""Shared pytest fixtures."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

import app.db.session as db_session
from app.core.config import settings
from app.main import app

TEAM_MEMBERS_URL = "/api/v1/team-members"


@pytest.fixture(scope="session", autouse=True)
def _use_null_pool_for_tests():
    """Avoid asyncpg 'another operation is in progress' under TestClient."""
    engine = create_async_engine(
        settings.DATABASE_URL,
        poolclass=NullPool,
        echo=False,
    )
    db_session.async_engine = engine
    db_session.AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    yield


@pytest.fixture
def client():
    """HTTP client against the FastAPI app."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def team_member_ids(client):
    """Track created team member IDs and delete them after the test."""
    created: list[str] = []
    yield created
    for member_id in created:
        client.delete(f"{TEAM_MEMBERS_URL}/{member_id}")
