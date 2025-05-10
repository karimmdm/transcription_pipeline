import uuid
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, HttpUrl
from whisperx.types import AlignedTranscriptionResult


class TrackProcessingStatus(str, Enum):
    PENDING = "PENDING"
    DOWNLOADED = "DOWNLOADED"
    TRANSCRIBED = "TRANSCRIBED"
    EMBEDDED = "EMBEDDED"


class Transcript(BaseModel):
    # Core identifiers
    uuid: uuid.UUID
    id: int | None = None

    # Core Transcript Data
    aligned_result: AlignedTranscriptionResult
    embedding: list[float] = []

    model_config = {"from_attributes": True}


class Track(BaseModel):
    # Core identifiers
    uuid: uuid.UUID
    id: int | None = None

    # Core metadata
    title: str
    webpage_url: HttpUrl
    download_url: HttpUrl
    uploader: str | None = None
    duration_seconds: float | None = None

    # Playlist context
    playlist_title: str | None = None
    playlist_url: HttpUrl | None = None
    track_number_in_playlist: int | None = None

    # Piplene specific data
    status: TrackProcessingStatus = TrackProcessingStatus.PENDING
    audio_file_path: Path | None = None
    transcript: Transcript | None = None

    model_config = {"from_attributes": True}
