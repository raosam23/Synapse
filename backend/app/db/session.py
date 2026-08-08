"""Database session management"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

async_engine = create_async_engine(settings.DATABASE_URL, echo=True)
AsyncSessionLocal = async_sessionmaker[AsyncSession](
    async_engine, expire_on_commit=False
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get a database session

    Returns:
        AsyncGenerator[AsyncSession, None]: A generator that yields a new AsyncSession object.
    """
    async with AsyncSessionLocal() as session:
        yield session
