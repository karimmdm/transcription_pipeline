import json
import logging
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import whisperx
from numpy.typing import NDArray
from pydantic import HttpUrl
from whisperx.types import (
    AlignedTranscriptionResult,
    TranscriptionResult,
)

from schemas import Track, TrackProcessingStatus, Transcript
from service.database_handler import IDatabase


class ITranscriberService(ABC):
    def __init__(self, database_service: IDatabase, save_directory: Path):
        """Initializes the TranscriberService."""
        self.logger = logging.getLogger(self.__class__.__name__)
        self.database_service = database_service
        self.save_directory = save_directory

    def unique_transcript_file_path(self, webpage_url: HttpUrl, extension: str) -> Path:
        """Saves the audio file as the UUID5 of the webpage_url and extension.

        Args:
            webpage_url: The URL of the track.

        Returns:
            The path to the saved audio file.

        """
        return Path(
            self.save_directory
            / f"{uuid.uuid5(uuid.NAMESPACE_URL, str(webpage_url))}.{extension}",
        )

    @abstractmethod
    def transcribe_audio(
        self, track: Track, save_to_disk: bool = False,
    ) -> tuple[Track, Transcript]:
        """Returns the path to the transcribed audio file.

        Args:
            track: the Track object with the audio_file_path set after downloading
            save_to_disk: save to the services save_directory
        Returns:
            The Track object

        """


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

    def _save_aligned_trasncript(
        self,
        aligned_result: AlignedTranscriptionResult,
        output_path: Path,
    ) -> None:
        with open(output_path, "w") as f:
            json.dump(aligned_result, f, indent=4)
        self.logger.info(f"Transcription saved to {output_path}")

    def _save_aligned_transcript_as_raw_text(
        self,
        aligned_result: AlignedTranscriptionResult,
        output_path: Path,
    ) -> None:
        segments = aligned_result["segments"]
        raw_text = ""
        for segment in segments:
            raw_text += segment["text"].strip() + "\n"
        with open(output_path, "w") as f:
            f.write(raw_text)
        self.logger.info(f"Raw transcript saved to {output_path}")

    def _perform_transcription_and_alignment(
        self, track: Track,
    ) -> AlignedTranscriptionResult:
        """Helper method to perform the actual transcription and alignment."""
        if not track.audio_file_path or not track.audio_file_path.exists():
            raise ValueError(
                f"Audio file path not set or file does not exist for track {track.uuid}: {track.audio_file_path}",
            )
        self.logger.debug(
            f"Transcribing audio file: {track.audio_file_path} for track {track.uuid}",
        )

        audio: NDArray = whisperx.load_audio(str(track.audio_file_path))
        result: TranscriptionResult = self.model.transcribe(
            audio,
            verbose=True if self.logger.isEnabledFor(logging.DEBUG) else False,
        )
        alignment_model: Any
        metadata: Any
        alignment_model, metadata = whisperx.load_align_model(
            language_code=result["language"], device=self.device,
        )

        aligned_result: AlignedTranscriptionResult = whisperx.align(
            result["segments"], alignment_model, metadata, audio, device=self.device,
        )
        return aligned_result

    def transcribe_audio(
        self, track: Track, save_to_disk: bool = False,
    ) -> tuple[Track, Transcript]:
        output_file_path = self.unique_transcript_file_path(
            track.webpage_url, extension="json",
        )

        aligned_result: AlignedTranscriptionResult  # This will be a dict conforming to the TypedDict

        if save_to_disk:
            if output_file_path.exists():
                self.logger.debug(
                    f"Loading transcript for {track.title} from {output_file_path}",
                )
                with open(output_file_path) as f:
                    aligned_result = json.load(f)  # json.load returns a dict

                raw_transcript_file_path = self.unique_transcript_file_path(
                    track.webpage_url, extension="txt",
                )
                if not raw_transcript_file_path.exists():
                    self._save_aligned_transcript_as_raw_text(
                        aligned_result, raw_transcript_file_path,
                    )
            else:
                aligned_result = self._perform_transcription_and_alignment(track)
                self._save_aligned_trasncript(aligned_result, output_file_path)
                self._save_aligned_transcript_as_raw_text(
                    aligned_result,
                    self.unique_transcript_file_path(track.webpage_url, "txt"),
                )
        else:
            aligned_result = self._perform_transcription_and_alignment(track)

        for segment in aligned_result.get("segments", []):
            segment.setdefault("chars", None)

        transcript = Transcript(
            uuid=uuid.uuid5(uuid.NAMESPACE_URL, str(track.webpage_url)),
            aligned_result=aligned_result,
        )

        track.transcript = transcript
        track.status = TrackProcessingStatus.TRANSCRIBED

        return track, transcript
