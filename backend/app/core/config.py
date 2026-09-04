"""Configuration for the application"""

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Settings for the application"""

    APP_NAME: str = "Synapse AI"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "SynapseAI is a platform for AI-powered solutions"

    # Optional at import time so app.main (and test_health) can load without CI/.env.
    # Required before any DB access — see app.db.session.
    DATABASE_URL: str | None = None
    # Pytest only. Local uvicorn keeps DATABASE_URL (synapse_db); CI omits this
    # and uses DATABASE_URL (synapse_ci). See backend/tests/conftest.py.
    TEST_DATABASE_URL: str | None = None

    # JWT settings
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    SALT_ROUNDS: int = 12

    class Config:
        """Configuration for the application"""

        env_file = Path(__file__).resolve().parents[3] / ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
