import uuid
from enum import Enum
from typing import Optional, List
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
    id: Optional[int] = None

    # Core metadata
    title: str
    webpage_url: HttpUrl

    # Core Transcript Data
    aligned_result: AlignedTranscriptionResult
    embedding: List[float] = []

    model_config = {"from_attributes": True}


class Track(BaseModel):
    # Core identifiers
    uuid: uuid.UUID
    id: Optional[int] = None

    # Core metadata
    title: str
    webpage_url: HttpUrl
    download_url: HttpUrl
    uploader: Optional[str] = None
    duration_seconds: Optional[float] = None

    # Playlist context
    playlist_title: Optional[str] = None
    playlist_url: Optional[HttpUrl] = None
    track_number_in_playlist: Optional[int] = None

    # Piplene specific data
    status: TrackProcessingStatus = TrackProcessingStatus.PENDING
    audio_file_path: Optional[Path] = None
    transcripts: List[Transcript] = []

    model_config = {"from_attributes": True}
