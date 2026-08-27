"""Database session management"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import settings

async_engine: AsyncEngine | None = None
AsyncSessionLocal: async_sessionmaker[AsyncSession] | None = None


def _ensure_session_factory() -> async_sessionmaker[AsyncSession]:
    """Create the async engine/session factory on first DB use."""
    global async_engine, AsyncSessionLocal
    if AsyncSessionLocal is not None:
        return AsyncSessionLocal
    if not settings.DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not configured")
    # NullPool: TestClient uses a new event loop per test; pooled asyncpg
    # connections stay bound to the first loop and fail on the next test.
    async_engine = create_async_engine(
        settings.DATABASE_URL, echo=True, poolclass=NullPool
    )
    AsyncSessionLocal = async_sessionmaker[AsyncSession](
        async_engine, expire_on_commit=False
    )
    return AsyncSessionLocal


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get a database session

    Returns:
        AsyncGenerator[AsyncSession, None]: A generator that yields a new AsyncSession object.
    """
    session_factory = _ensure_session_factory()
    async with session_factory() as session:
        yield session
