from abc import ABC, abstractmethod
from sqlalchemy import Engine
from typing import List
import dtos


class IDatabase(ABC):
    @abstractmethod
    def add_processed_webpage_urls(self, urls: List[str]):
        pass

    @abstractmethod
    def get_processed_webpage_urls(self) -> List[str]:
        pass

    @abstractmethod
    def track_is_transcribed(self, webpage_url: str) -> bool:
        pass


class PostgresDatabase(IDatabase):
    def __init__(self, engine: Engine):
        self.engine = engine

    def add_processed_webpage_urls(self, urls: List[str]):
        with self.engine.connect() as connection:
            for url in urls:
                connection.execute(
                    "INSERT INTO processed_urls (webpage_url) VALUES (%s) ON CONFLICT DO NOTHING",
                    (url,),
                )

    def get_processed_webpage_urls(self) -> List[str]:
        with self.engine.connect() as connection:
            result = connection.execute("SELECT webpage_url FROM processed_urls")
            return [row[0] for row in result.fetchall()]

    def track_is_transcribed(self, webpage_url: str) -> bool:
        with self.engine.connect() as connection:
            result = connection.execute(
                "SELECT COUNT(*) FROM tracks WHERE webpage_url = %s AND status = %s",
                (webpage_url, dtos.TrackProcessingStatus.TRANSCRIBED.value),
            )
            count = result.scalar()
            return count > 0
