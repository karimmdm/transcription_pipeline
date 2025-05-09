from enum import Enum
import uuid  # Import uuid for Mapped type hint

from sqlalchemy import Float, ForeignKey, Integer, String, Enum as SQLAlchemyEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB, ARRAY
from sqlalchemy.orm import DeclarativeBase, relationship, Mapped, mapped_column
from typing import List, Optional, Dict, Any  # For Mapped type hints


class Base(DeclarativeBase):
    pass


class TrackProcessingStatus(str, Enum):
    PENDING = "PENDING"
    DOWNLOADED = "DOWNLOADED"
    TRANSCRIBED = "TRANSCRIBED"
    EMBEDDED = "EMBEDDED"


class Track(Base):
    __tablename__ = "tracks"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    track_uuid: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), unique=True, nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    webpage_url: Mapped[str] = mapped_column(
        String(1024), nullable=False, unique=True, index=True
    )
    download_url: Mapped[str] = mapped_column(String(1024), nullable=False, index=True)
    playlist_url: Mapped[Optional[str]] = mapped_column(
        String(1024), nullable=True, index=True
    )
    track_number_in_playlist: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )
    uploader: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[TrackProcessingStatus] = mapped_column(
        SQLAlchemyEnum(TrackProcessingStatus, name="track_processing_status_enum"),
        nullable=False,
        default=TrackProcessingStatus.PENDING,
        index=True,
    )
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    audio_file_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)

    transcripts: Mapped[List["Transcript"]] = relationship(
        "Transcript",
        back_populates="track",
        cascade="all, delete-orphan",
    )


class Transcript(Base):
    __tablename__ = "transcripts"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    track_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("tracks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    track: Mapped["Track"] = relationship("Track", back_populates="transcripts")
    aligned_segments_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True
    )
    embeddings: Mapped[Optional[List[float]]] = mapped_column(
        ARRAY(Float), nullable=True
    )
