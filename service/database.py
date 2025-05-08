from abc import ABC, abstractmethod
import uuid

from sqlalchemy import text
from sqlalchemy.engine import Engine

import schemas


class IDatabase(ABC):
    @abstractmethod
    def add_processed_webpage_urls(self, urls: list[str]):
        pass

    @abstractmethod
    def get_processed_webpage_urls(self) -> list[str]:
        pass

    @abstractmethod
    def track_is_transcribed(self, webpage_url: str) -> bool:
        pass


class PostgresDatabase(IDatabase):
    def __init__(self, engine: Engine):
        self.engine = engine

    def add_processed_webpage_urls(self, urls: list[str]):
        pass

    def get_processed_webpage_urls(self) -> list[str]:
        return []

    def track_is_transcribed(self, webpage_url: str) -> bool:
        track_uuid = uuid.uuid5(uuid.NAMESPACE_URL, webpage_url)
        with self.engine.connect() as connection:
            stmt = text(
                "SELECT COUNT(*) FROM tracks WHERE track_uuid = :track_uuid AND status = :status"
            )
            result = connection.execute(
                stmt,
                {
                    "track_uuid": track_uuid,
                    "status": schemas.TrackProcessingStatus.TRANSCRIBED.value,
                },
            )
            count = result.scalar_one_or_none()  # Use scalar_one_or_none for safety
            return count is not None and count > 0
