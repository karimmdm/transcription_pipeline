
from pathlib import Path

from pydantic import HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent


class Settings(BaseSettings):
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "pipeline.log"
    URL: HttpUrl = HttpUrl("https://default.example.com/fallback")
    IS_PLAYLIST: bool = False
    DATABASE_URL: str = "postgresql://test_user:test_password@localhost:5432/test_db"
    TMP_DIR: Path = PROJECT_ROOT / "tmp"
    AUDIO_DIR: Path = TMP_DIR / "audio"
    TRANSCRIPT_DIR: Path = TMP_DIR / "transcripts"

    model_config = SettingsConfigDict(extra="ignore")


def get_settings() -> Settings:
    return Settings()


settings = get_settings()
