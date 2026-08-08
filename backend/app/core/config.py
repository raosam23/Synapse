"""Configuration for the application"""

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Settings for the application"""

    APP_NAME: str = "SynapseAI"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "SynapseAI is a platform for AI-powered solutions"

    # Database settings
    DATABASE_URL: str

    class Config:
        """Configuration for the application"""

        env_file = Path(__file__).resolve().parents[3] / ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
