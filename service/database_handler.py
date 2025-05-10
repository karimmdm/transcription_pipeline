import uuid
from abc import ABC, abstractmethod

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import Engine

import schemas
from database import models  # Assuming your project structure allows this import


class IDatabase(ABC):
    @abstractmethod
    def track_is_transcribed(self, webpage_url: str) -> bool:
        pass

    @abstractmethod
    def insert_track(self, track: schemas.Track) -> None:
        pass

    @abstractmethod
    def insert_transcript(self, transcript: schemas.Transcript) -> None:
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

    def insert_track(self, track: schemas.Track) -> None:
        values_to_insert = {
            "track_uuid": track.uuid,
            "title": track.title,
            "webpage_url": str(track.webpage_url),
            "download_url": str(track.download_url),
            "playlist_url": str(track.playlist_url) if track.playlist_url else None,
            "track_number_in_playlist": track.track_number_in_playlist,
            "uploader": track.uploader,
            "status": track.status,
            "duration_seconds": track.duration_seconds,
            "audio_file_path": str(track.audio_file_path)
            if track.audio_file_path
            else None,
        }

        with self.engine.connect() as connection:
            stmt = (
                pg_insert(models.Track)
                .values(**values_to_insert)
                .on_conflict_do_update(
                    index_elements=[models.Track.track_uuid],
                    set_={
                        "title": pg_insert(models.Track).excluded.title,
                        "webpage_url": pg_insert(models.Track).excluded.webpage_url,
                        "download_url": pg_insert(models.Track).excluded.download_url,
                        "playlist_url": pg_insert(models.Track).excluded.playlist_url,
                        "track_number_in_playlist": pg_insert(
                            models.Track,
                        ).excluded.track_number_in_playlist,
                        "uploader": pg_insert(models.Track).excluded.uploader,
                        "status": pg_insert(models.Track).excluded.status,
                        "duration_seconds": pg_insert(
                            models.Track,
                        ).excluded.duration_seconds,
                        "audio_file_path": pg_insert(
                            models.Track,
                        ).excluded.audio_file_path,
                    },
                )
            )
            connection.execute(stmt)
            connection.commit()

    def insert_transcript(self, transcript: schemas.Transcript) -> None:
        values_to_insert = {
            "track_uuid": transcript.uuid,
            "aligned_segments_data": transcript.aligned_result,
            "embeddings": transcript.embedding,
        }

        with self.engine.connect() as connection:
            stmt = (
                pg_insert(models.Transcript)
                .values(**values_to_insert)
                .on_conflict_do_update(
                    index_elements=[models.Transcript.track_uuid],
                    set_={
                        "aligned_segments_data": pg_insert(
                            models.Transcript,
                        ).excluded.aligned_segments_data,
                        "embeddings": pg_insert(models.Transcript).excluded.embeddings,
                    },
                )
            )
            connection.execute(stmt)
            connection.commit()
