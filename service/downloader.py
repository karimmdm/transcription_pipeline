import logging
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from pydantic import HttpUrl
from yt_dlp import YoutubeDL

from schemas import Track, TrackProcessingStatus
from service.database_handler import IDatabase


class IDownloaderService(ABC):
    def __init__(
        self,
        database_service: IDatabase,
        save_directory: Path,
        ydl_opts_override: dict[str, Any] | None = None,
    ):
        """Initializes the DownloaderService.

        Args:
            ydl_opts_override (dict, optional): Options to override default yt-dlp settings.
                                                Defaults to None.

        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.base_ydl_opts = {
            "quiet": True,
            "ignoreerrors": True,
            "format": "bestaudio/best",
            "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "wav"}],
        }
        if ydl_opts_override:
            self.base_ydl_opts.update(ydl_opts_override)
        self.database_service = database_service
        self.save_directory = save_directory

    def unique_audio_file_path(self, webpage_url: HttpUrl) -> Path:
        """Saves the wav audio file as the UUID5 of the webpage_url.

        Args:
            webpage_url: The URL of the track.

        Returns:
            The path to the saved .wav file.

        """
        return Path(
            self.save_directory
            / f"{uuid.uuid5(uuid.NAMESPACE_URL, str(webpage_url))}.wav",
        )

    @abstractmethod
    def download_playlist(self, playlist_url: HttpUrl) -> list[Track]:
        """Downloads all tracks from a given playlist using yt-dlp.

        Args:
            playlist_url: The URL of the playlist.

        Returns:
            A list of Track objects.

        """

    @abstractmethod
    def download_track(self, webpage_url: HttpUrl) -> Track:
        """Downloads a single track from a given URL using yt-dlp.

        Args:
            webpage_url: The URL of the track.
            output_dir: The directory to save the downloaded file.

        Returns:
            The updated Track object with download information.

        """


class SoundcloudDownloaderService(IDownloaderService):
    def __init__(
        self,
        database_service: IDatabase,
        save_directory: Path,
        ydl_opts_override: dict | None = None,
    ):
        super().__init__(
            database_service=database_service,
            save_directory=save_directory,
            ydl_opts_override=ydl_opts_override,
        )

    def _get_track_metadata(self, track_url: HttpUrl) -> Track | None:
        self.logger.debug(f"Retrieving metadata for track: {track_url}")
        fetch_opts = self.base_ydl_opts.copy()
        with YoutubeDL(fetch_opts) as ydl:
            info: dict | None = ydl.extract_info(str(track_url), download=False)

            if not info:
                self.logger.warning(f"No info found for track: {track_url}")
                raise ValueError(f"Could not extract metadata for track: {track_url}")

            track_webpage_url: str | None = info.get("webpage_url")
            track_download_url: str | None = info.get("url")

            if not track_webpage_url or not track_download_url:
                self.logger.error(
                    f"Essential metadata (webpage_url or download_url) missing for {track_url}",
                )
                raise ValueError(f"Essential metadata missing for track: {track_url}")

            # TODO: move this check into main.py
            if self.database_service.track_is_transcribed(
                webpage_url=track_webpage_url,
            ):
                self.logger.debug(f"Track @ {track_webpage_url} is already transcribed.")
                return None

            track_data = Track(
                uuid=uuid.uuid5(uuid.NAMESPACE_URL, track_webpage_url),
                title=info.get("title", "Unknown Title"),
                webpage_url=HttpUrl(track_webpage_url),
                download_url=HttpUrl(track_download_url),
                uploader=info.get("uploader"),
                duration_seconds=info.get("duration"),
                status=TrackProcessingStatus.PENDING,
            )
            self.logger.debug(
                f"Parsed track {track_data.title} - (URL: {track_data.webpage_url} - UUID: {track_data.uuid})",
            )
            return track_data

    def _download_track(self, track: Track) -> Track:
        output_file_path = self.unique_audio_file_path(track.webpage_url)

        if not output_file_path.exists():
            self.logger.debug(
                f"Audio file for {track.title} not found. Attempting download to {output_file_path}",
            )
            download_opts: dict[str, Any] = self.base_ydl_opts.copy()
            output_template_base = str(output_file_path.with_suffix(""))
            download_opts["outtmpl"] = output_template_base
            with YoutubeDL(download_opts) as ydl:
                self.logger.debug(
                    f"yt-dlp download: {track.title} @ {track.webpage_url}. "
                    f"Base template: {output_template_base}",
                )
                ydl.download([str(track.download_url)])

            if not output_file_path.exists():
                self.logger.error(
                    f"Expected audio file not found at {output_file_path} after download attempt for {track.title}",
                )
                raise FileNotFoundError(
                    f"Download failed: Expected audio file not found at {output_file_path} for {track.title}",
                )
            self.logger.info(
                f"Successfully downloaded track: {track.title} to {output_file_path}",
            )
        else:
            self.logger.debug(
                f"Audio file for {track.title} already exists at {output_file_path}",
            )

        track.audio_file_path = output_file_path
        track.status = TrackProcessingStatus.DOWNLOADED
        return track

    def _get_playlist_tracks_metadata(self, playlist_url: HttpUrl) -> list[Track]:
        self.logger.debug(f"Retrieving tracks from playlist: {playlist_url}")

        fetch_opts = self.base_ydl_opts.copy()
        fetch_opts["extract_flat"] = False

        with YoutubeDL(fetch_opts) as ydl:
            info: dict | None = ydl.extract_info(
                url=str(playlist_url), download=False,
            )
            if not info:
                self.logger.warning(f"No info found for playlist: {playlist_url}")
                return []

            entries: dict = info.get("entries", [])
            if not entries:
                self.logger.warning(f"No entries found in playlist: {playlist_url}")
                return []

            self.logger.debug(f"Retrieved {len(entries)} entries from playlist.")
            playlist_track_metadatas: list[Track] = []
            playlist_title: str | None = info.get("title")
            for index, entry in enumerate(entries):
                title: str = entry.get("title", f"Unknown Title Track {index + 1}")
                track_webpage_url: str = entry.get("webpage_url")
                track_download_url: str = entry.get("url")
                uploader_name: str = entry.get("uploader")
                duration: float = entry.get("duration")

                if not track_webpage_url or not track_download_url:
                    self.logger.warning(
                        f"Skipping track {index + 1}: Missing webpage_url or download_url.",
                    )
                    continue

                # TODO: Move this check into into main.py
                if self.database_service.track_is_transcribed(
                    webpage_url=track_webpage_url,
                ):
                    self.logger.debug(
                        f"Skipping track {index + 1} @ {track_webpage_url}: Already transcribed.",
                    )
                    continue

                track = Track(
                    uuid=uuid.uuid5(uuid.NAMESPACE_URL, track_webpage_url),
                    title=title,
                    webpage_url=HttpUrl(track_webpage_url),
                    download_url=HttpUrl(track_download_url),
                    uploader=uploader_name,
                    duration_seconds=duration,
                    track_number_in_playlist=index + 1,
                    playlist_url=playlist_url,
                    status=TrackProcessingStatus.PENDING,
                )
                if playlist_title:
                    track.playlist_title = playlist_title
                playlist_track_metadatas.append(track)
                self.logger.debug(
                    f"Parsed track {track.title} - (URL: {track.webpage_url} - UUID: {track.uuid})",
                )
            return playlist_track_metadatas

    def download_track(self, webpage_url: HttpUrl) -> Track:
        track = self._get_track_metadata(webpage_url)
        if not track:
            raise Exception(f"Could not download track: {webpage_url}")
        return self._download_track(track)

    def download_playlist(self, playlist_url: HttpUrl) -> list[Track]:
        tracks = self._get_playlist_tracks_metadata(playlist_url)
        for track in tracks:
            self._download_track(track)
        return tracks
