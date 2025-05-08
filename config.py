import os

from pydantic import HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "pipeline.log"
    URL: HttpUrl
    IS_PLAYLIST: bool = False

    WHISPER_MODEL_NAME: str = "medium"
    WHISPER_DEVICE: str = "cpu"
    WHISPER_BATCH_SIZE: int = 16

    DATABASE_URL: str

    # Pydantic V2 style configuration using model_config
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def __init__(self, **values):
        super().__init__(**values)


def get_settings() -> Settings:
    """Returns the settings object, dynamically deciding whether to load from the .env file
    or rely solely on environment variables (e.g., in production).
    """
    if os.environ.get("PRODUCTION", "").lower() == "true":
        # Ignore the .env file in production
        return Settings(_env_file=None)
    # Load from the .env file in development
    return Settings()


# Create a global settings instance
settings = get_settings()
