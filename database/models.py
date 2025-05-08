from enum import Enum

from sqlalchemy import (
    Column,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy import Enum as SQLAlchemyEnum  # Renamed to avoid conflict
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class TrackProcessingStatus(str, Enum):
    PENDING = "PENDING"
    DOWNLOADED = "DOWNLOADED"
    TRANSCRIBED = "TRANSCRIBED"
    EMBEDDED = "EMBEDDED"


class Track(Base):
    __tablename__ = "tracks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    track_uuid = Column(PG_UUID(True), unique=True, nullable=False, index=True)
    title = Column(String(512), nullable=False)
    webpage_url = Column(String(1024), nullable=False, unique=True, index=True)
    download_url = Column(String(1024), nullable=False, index=True)
    playlist_url = Column(String(1024), nullable=True, index=True)
    track_number_in_playlist = Column(Integer, nullable=True)
    uploader = Column(String(255), nullable=True)  # Added uploader field
    status: Column[TrackProcessingStatus] = Column(
        SQLAlchemyEnum(TrackProcessingStatus, name="track_processing_status_enum"),
        nullable=False,
        default=TrackProcessingStatus.PENDING,
        index=True,
    )
    duration_seconds = Column(Float, nullable=True)
    audio_file_path = Column(String(1024), nullable=True)
    transcripts = relationship(
        "Transcript",
        back_populates="track",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<Track(id={self.id}, title='{self.title[:30]}...', webpage_url='{self.webpage_url}')>"


class Transcript(Base):
    __tablename__ = "transcripts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    track_id = Column(
        Integer,
        ForeignKey("tracks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    track = relationship("Track", back_populates="transcripts")

    def __repr__(self):
        return f"<Transcription(id={self.id}, track_id={self.track_id}')>"
