import logging
import schemas
import uuid
from typing import Any, Optional
from pydantic import HttpUrl
from abc import ABC, abstractmethod
from yt_dlp import YoutubeDL
from pathlib import Path
from service.database import IDatabase


class IDownloaderService(ABC):
    def __init__(
        self,
        database_service: IDatabase,
        save_directory: Path,
        ydl_opts_override: Optional[dict[str, Any]] = None,
    ):
        """
        Initializes the DownloaderService.

        Args:
            ydl_opts_override (dict, optional): Options to override default yt-dlp settings.
                                                Defaults to None.
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.base_ydl_opts = {
            "quiet": True,
            "ignoreerrors": True,
            "format": "bestaudio/best",  # Select the best audio stream
            "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "wav"}],
        }
        if ydl_opts_override:
            self.base_ydl_opts.update(ydl_opts_override)
        self.database_service = database_service
        self.save_directory = save_directory

    @abstractmethod
    def get_playlist_tracks_metadata(
        self, playlist_url: HttpUrl
    ) -> list[schemas.Track]:
        """
        Retrieves the list of audio URLs, titles, and indices from a playlist.

        Args:
            playlist_url: The URL of the playlist.

        Returns:
            A list of Track objects.
        """
        pass

    @abstractmethod
    def get_track_metadata(self, track_url: HttpUrl) -> Optional[schemas.Track]:
        """
        Retrieves the metadata for a single track.

        Args:
            track_url: The URL of the track.

        Returns:
            A Track object if found, None otherwise.
        """
        pass

    @abstractmethod
    def download_track(self, track: schemas.Track) -> schemas.Track:
        """
        Downloads a single track from a given URL using yt-dlp.

        Args:
            track: A TrackBase object containing information about the track to be downloaded.
            output_dir: The directory to save the downloaded file.

        Returns:
            The updated Track object with download information.
        """
        pass


class SoundcloudDownloaderService(IDownloaderService):
    def __init__(
        self,
        database_service: IDatabase,
        save_directory: Path,
        ydl_opts_override: Optional[dict] = None,
    ):
        super().__init__(
            database_service=database_service,
            save_directory=save_directory,
            ydl_opts_override=ydl_opts_override,
        )

    def get_playlist_tracks_metadata(
        self, playlist_url: HttpUrl
    ) -> list[schemas.Track]:
        self.logger.debug(f"Retrieving tracks from playlist: {playlist_url}")

        fetch_opts = self.base_ydl_opts.copy()
        fetch_opts["extract_flat"] = False

        with YoutubeDL(fetch_opts) as ydl:
            info: Optional[dict] = ydl.extract_info(
                url=str(playlist_url), download=False
            )
            if not info:
                self.logger.warning(f"No info found for playlist: {playlist_url}")
                return []

            entries: dict = info.get("entries", [])
            if not entries:
                self.logger.warning(f"No entries found in playlist: {playlist_url}")
                return []

            self.logger.debug(f"Retrieved {len(entries)} entries from playlist.")
            playlist_track_metadatas: list[schemas.Track] = []
            playlist_title: Optional[str] = info.get("title")
            for index, entry in enumerate(entries):
                title: str = entry.get("title", f"Unknown Title Track {index + 1}")
                track_webpage_url: str = entry.get("webpage_url")
                track_download_url: str = entry.get("url")
                uploader_name: str = entry.get("uploader")
                duration: float = entry.get("duration")

                if not track_webpage_url or not track_download_url:
                    self.logger.warning(
                        f"Skipping track {index + 1}: Missing webpage_url or download_url."
                    )
                    continue

                if self.database_service.track_is_transcribed(
                    webpage_url=track_webpage_url
                ):
                    self.logger.debug(
                        f"Skipping track {index + 1} @ {track_webpage_url}: Already transcribed."
                    )
                    continue

                # Instantiate the consolidated Track model
                track = schemas.Track(
                    uuid=uuid.uuid5(uuid.NAMESPACE_URL, track_webpage_url),
                    title=title,
                    webpage_url=HttpUrl(track_webpage_url),
                    download_url=HttpUrl(track_download_url),
                    uploader=uploader_name,
                    duration_seconds=duration,
                    track_number_in_playlist=index + 1,
                    playlist_url=playlist_url,
                    status=schemas.TrackProcessingStatus.PENDING,  # Explicitly set initial status
                )
                if playlist_title:
                    track.playlist_title = playlist_title
                playlist_track_metadatas.append(track)
                self.logger.debug(
                    f"Parsed track {track.title} - (URL: {track.webpage_url} - UUID: {track.uuid})"
                )
            return playlist_track_metadatas

    def get_track_metadata(self, track_url: HttpUrl) -> Optional[schemas.Track]:
        self.logger.debug(f"Retrieving metadata for track: {track_url}")
        fetch_opts = self.base_ydl_opts.copy()
        with YoutubeDL(fetch_opts) as ydl:
            info: Optional[dict] = ydl.extract_info(str(track_url), download=False)

            if not info:
                self.logger.warning(f"No info found for track: {track_url}")
                raise ValueError(f"Could not extract metadata for track: {track_url}")

            track_webpage_url: Optional[str] = info.get("webpage_url")
            track_download_url: Optional[str] = info.get("url")

            if not track_webpage_url or not track_download_url:
                self.logger.error(
                    f"Essential metadata (webpage_url or download_url) missing for {track_url}"
                )
                raise ValueError(f"Essential metadata missing for track: {track_url}")

            if self.database_service.track_is_transcribed(
                webpage_url=track_webpage_url
            ):
                self.logger.debug(f"Track @ {track_webpage_url} is lready transcribed.")
                return None

            track_data = schemas.Track(
                uuid=uuid.uuid5(uuid.NAMESPACE_URL, track_webpage_url),
                title=info.get("title", "Unknown Title"),
                webpage_url=HttpUrl(track_webpage_url),
                download_url=HttpUrl(track_download_url),
                uploader=info.get("uploader"),
                duration_seconds=info.get("duration"),
                status=schemas.TrackProcessingStatus.PENDING,
            )
            self.logger.debug(
                f"Parsed track {track_data.title} - (URL: {track_data.webpage_url} - UUID: {track_data.uuid})"
            )
            return track_data

    def download_track(self, track: schemas.Track) -> schemas.Track:
        self.logger.debug(f"Downloading track: {track.title} @ {track.webpage_url}")
        download_opts: dict[str, Any] = self.base_ydl_opts.copy()
        output_template = str(self.save_directory / f"{track.uuid}.%(ext)s")
        download_opts["outtmpl"] = output_template
        download_opts["quiet"] = True
        with YoutubeDL(download_opts) as ydl:
            ydl.download([str(track.download_url)])

        track.audio_file_path = str(
            self.save_directory / f"{track.uuid}.wav"
        )  # Assuming wav
        track.status = schemas.TrackProcessingStatus.DOWNLOADED
        return track
