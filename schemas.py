from enum import Enum
from typing import Optional, List
import uuid  # For uuid.UUID type

from pydantic import BaseModel, HttpUrl


class TranscriptBase(BaseModel):
    pass


class Transcript(TranscriptBase):
    pass


class TrackProcessingStatus(str, Enum):
    PENDING = "PENDING"
    DOWNLOADED = "DOWNLOADED"
    TRANSCRIBED = "TRANSCRIBED"
    EMBEDDED = "EMBEDDED"


class Track(BaseModel):
    # Core identifiers
    uuid: uuid.UUID
    id: Optional[int] = None  # Database ID, optional until saved

    # Core metadata
    title: str
    webpage_url: HttpUrl
    download_url: HttpUrl
    uploader: Optional[str] = None
    duration_seconds: Optional[float] = None

    # Playlist context (optional)
    playlist_title: Optional[str] = None
    playlist_url: Optional[HttpUrl] = None
    track_number_in_playlist: Optional[int] = None

    # Pipeline status and stage-specific data
    status: TrackProcessingStatus = TrackProcessingStatus.PENDING
    audio_file_path: Optional[str] = None
    transcriptions: Optional[List[Transcript]] = (
        None  # Or list[Transcript] for Python 3.9+
    )
    embedding: Optional[List[float]] = None  # Or list[float] for Python 3.9+

    # Pydantic V2 style for ORM mode (reading from SQLAlchemy model attributes)
    model_config = {"from_attributes": True}
