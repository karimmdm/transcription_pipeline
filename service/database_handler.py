from abc import ABC, abstractmethod
from typing import Optional
import uuid

from sqlalchemy import select, func
from sqlalchemy.engine import Engine
from sqlalchemy.dialects.postgresql import insert as pg_insert

import schemas
from database import models  # Assuming your project structure allows this import


class IDatabase(ABC):
    @abstractmethod
    def track_is_transcribed(self, webpage_url: str) -> bool:
        pass


class PostgresDatabase(IDatabase):
    def __init__(self, engine: Engine):
        self.engine = engine

    def track_is_transcribed(self, webpage_url: str) -> bool:
        track_uuid = uuid.uuid5(uuid.NAMESPACE_URL, webpage_url)
        with self.engine.connect() as connection:
            stmt = (
                select(func.count(models.Track.id))
                .where(models.Track.track_uuid == track_uuid)
                .where(models.Track.status == schemas.TrackProcessingStatus.TRANSCRIBED)
            )
            count = connection.execute(stmt).scalar_one_or_none()
            return count is not None and count > 0
