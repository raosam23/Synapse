"""Guard: API tests must not run against the local uvicorn/Swagger database."""

from urllib.parse import urlparse

from sqlalchemy import create_engine, text

from app.core.config import settings


def test_pytest_does_not_use_local_dev_database() -> None:
    assert settings.DATABASE_URL is not None
    db_name = urlparse(settings.DATABASE_URL).path.lstrip("/").split("?")[0]
    assert db_name != "synapse_db"

    sync_url = settings.DATABASE_URL.replace(
        "postgresql+asyncpg://", "postgresql+psycopg://"
    )
    engine = create_engine(sync_url)
    with engine.connect() as conn:
        connected = conn.execute(text("SELECT current_database()")).scalar_one()
    assert connected != "synapse_db"
