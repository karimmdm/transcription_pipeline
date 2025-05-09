import json
import logging
import uuid
import whisperx
from pydantic import HttpUrl
from abc import ABC, abstractmethod
from pathlib import Path
from whisperx.types import (
    TranscriptionResult,
    AlignedTranscriptionResult,
    SingleAlignedSegment,
    SingleSegment,
)
from typing import Any, Dict, List
from schemas import Track, Transcript, TrackProcessingStatus
from service.database_handler import IDatabase
from numpy.typing import NDArray


class ITranscriberService(ABC):
    def __init__(self, database_service: IDatabase, save_directory: Path):
        """Initializes the TranscriberService."""
        self.logger = logging.getLogger(self.__class__.__name__)
        self.database_service = database_service
        self.save_directory = save_directory

    def unique_transcript_file_path(self, webpage_url: HttpUrl, extension: str) -> Path:
        return Path(
            self.save_directory
            / f"{uuid.uuid5(uuid.NAMESPACE_URL, str(webpage_url))}.{extension}"
        )

    @abstractmethod
    def transcribe_audio(
        self, track: Track, save_to_disk: bool = False
    ) -> tuple[Track, Transcript]:
        """
        Returns the path to the transcribed audio file.

        Args:
            track: the Track object with the audio_file_path set after downloading
            save_to_disk: save to the services save_directory
        Returns:
            The Track object
        """
        pass


class WhiserXTranscriberService(ITranscriberService):
    def __init__(
        self,
        database_service: IDatabase,
        save_directory: Path,
        model_name: str,
        device: str,
        compute_type: str,
    ):
        super().__init__(database_service, save_directory)
        self.model_name = model_name
        self.device = device
        self.model = whisperx.load_model(model_name, device, compute_type=compute_type)

    def _save_transcription(
        self,
        aligned_result: AlignedTranscriptionResult,
        output_path: Path,
    ) -> None:
        with open(output_path, "w") as f:
            json.dump(aligned_result, f, indent=4)
        self.logger.info(f"Transcription saved to {output_path}")

    def transcribe_audio(
        self, track: Track, save_to_disk: bool = False
    ) -> tuple[Track, Transcript]:
        if not track.audio_file_path:
            raise ValueError(
                f"Downloaded audio path was not set for track: {track.title}"
            )
        self.logger.debug(f"Transcribing audio file: {track.audio_file_path}")

        audio: NDArray = whisperx.load_audio(track.audio_file_path)

        result: TranscriptionResult = self.model.transcribe(
            audio, verbose=True if self.logger.isEnabledFor(logging.DEBUG) else False
        )

        alignment_model: Any
        metadata: Any
        alignment_model, metadata = whisperx.load_align_model(
            language_code=result["language"], device=self.device
        )

        aligned_result: AlignedTranscriptionResult = whisperx.align(
            result["segments"],
            alignment_model,
            metadata,
            audio,
            device=self.device,
        )

        for segment in aligned_result["segments"]:
            segment.setdefault("chars", None)

        transcript = Transcript(
            uuid=uuid.uuid5(uuid.NAMESPACE_URL, str(track.webpage_url)),
            title=track.title,
            webpage_url=track.webpage_url,
            aligned_result=aligned_result,
        )

        track.transcripts.append(transcript)
        track.status = TrackProcessingStatus.TRANSCRIBED

        if save_to_disk:
            self._save_transcription(
                aligned_result,
                self.unique_transcript_file_path(track.webpage_url, "json"),
            )

        return track, transcript
