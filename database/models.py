import uuid  # Import uuid for Mapped type hint
from enum import Enum
from typing import Any, Optional

from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


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
        Integer, primary_key=True, index=True, autoincrement=True,
    )
    track_uuid: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), unique=True, nullable=False, index=True,
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    webpage_url: Mapped[str] = mapped_column(
        String(1024), nullable=False, unique=True, index=True,
    )
    download_url: Mapped[str] = mapped_column(String(1024), nullable=False, index=True)
    playlist_url: Mapped[str | None] = mapped_column(
        String(1024), nullable=True, index=True,
    )
    track_number_in_playlist: Mapped[int | None] = mapped_column(
        Integer, nullable=True,
    )
    uploader: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[TrackProcessingStatus] = mapped_column(
        SQLAlchemyEnum(TrackProcessingStatus, name="track_processing_status_enum"),
        nullable=False,
        default=TrackProcessingStatus.PENDING,
        index=True,
    )
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    audio_file_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    transcript: Mapped[Optional["Transcript"]] = relationship(
        "Transcript",
        back_populates="track",
        cascade="all, delete-orphan"
    )


class Transcript(Base):
    __tablename__ = "transcripts"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True,
    )
    track_uuid: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tracks.track_uuid", ondelete="CASCADE"),
        nullable=False,
        index=True,
        unique=True,
    )
    aligned_segments_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True,
    )
    embeddings: Mapped[list[float] | None] = mapped_column(
        ARRAY(Float), nullable=True,
    )

    track: Mapped[Track] = relationship(
        "Track",
        back_populates="transcript"
    )

