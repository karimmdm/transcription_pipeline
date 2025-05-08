from pydantic import BaseModel, HttpUrl
from typing import Optional, List, Dict, Any
from enum import Enum


class TranscriptBase(BaseModel):
    pass


class Transcript(TranscriptBase):
    pass


class TrackProcessingStatus(str, Enum):
    PENDING = "PENDING"
    DOWNLOADED = "DOWNLOADED"
    TRANSCRIBED = "TRANSCRIBED"
    EMBEDDED = "EMBEDDED"


class TrackBase(BaseModel):
    title: str
    webpage_url: HttpUrl
    download_url: HttpUrl
    playlist_url: Optional[HttpUrl] = None
    track_number_in_playlist: Optional[int] = None
    status: TrackProcessingStatus = TrackProcessingStatus.PENDING
    uploader: Optional[str] = None
    duration_seconds: Optional[float] = None


class TrackDownloaded(TrackBase):
    id: int
    audio_file_path: str

    class Config:
        orm_mode = True  # Allows Pydantic to work with ORM models (SQLAlchemy)


class TrackTranscribed(TrackDownloaded):
    transcriptions: List[Transcript] = []
    status: TrackProcessingStatus = TrackProcessingStatus.TRANSCRIBED

    class Config:
        orm_mode = True  # Allows Pydantic to work with ORM models (SQLAlchemy)


class TrackEmbedded(TrackTranscribed):
    embedding: Optional[List[float]] = None
    status: TrackProcessingStatus = TrackProcessingStatus.EMBEDDED

    class Config:
        orm_mode = True  # Allows Pydantic to work with ORM models (SQLAlchemy)
