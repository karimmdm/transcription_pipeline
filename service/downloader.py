import logging
from typing import Any, Optional

from pydantic import HttpUrl
import dtos
from abc import ABC, abstractmethod
from yt_dlp import YoutubeDL
from pathlib import Path
from service.database import IDatabase


class IDownloaderService(ABC):
    def __init__(
        self, database_service: IDatabase, save_directory: Path, ydl_opts_override: Optional[dict[str, Any]] = None
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
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "wav",
                    # You can optionally specify preferredquality if needed, e.g.,
                    # "preferredquality": "192",
                }
            ],
            "outtmpl": "%(title)s.%(ext)s",  # Default output template
        }
        if ydl_opts_override:
            self.base_ydl_opts.update(ydl_opts_override)
        self.database_service = database_service
        self.save_directory = save_directory

    @abstractmethod
    def get_playlist_tracks(self, playlist_url: str) -> list[dtos.TrackBase]:
        """
        Retrieves the list of audio URLs, titles, and indices from a playlist.

        Args:
            playlist_url: The URL of the playlist.

        Returns:
            A list of TrackBase objects.
        """
        pass

    @abstractmethod
    def download_track(
        self, track: dtos.TrackBase, output_dir: Path
    ) -> dtos.TrackDownloaded:
        """
        Downloads a single track from a given URL using yt-dlp.

        Args:
            track: A TrackBase object containing information about the track to be downloaded.
            output_dir: The directory to save the downloaded file.

        Returns:
            A TrackDownloaded object containing information about the downloaded track.
        """
        pass


class SoundcloudDownloaderService(IDownloaderService):
    def __init__(
        self, database_service: IDatabase, save_directory: Path, ydl_opts_override: Optional[dict] = None
    ):
        super().__init__(database_service=database_service, save_directory=save_directory, ydl_opts_override=ydl_opts_override)

    def get_playlist_tracks(self, playlist_url: HttpUrl) -> list[dtos.TrackBase]:
        self.logger.debug(f"Retrieving tracks from playlist: {playlist_url}")

        fetch_opts = self.base_ydl_opts.copy()
        fetch_opts["extract_flat"] = False

        with YoutubeDL(fetch_opts) as ydl:
            info: dict = ydl.extract_info(playlist_url, download=False)
            entries: dict = info.get("entries", [])
            if not entries:
                self.logger.warning(f"No entries found in playlist: {playlist_url}")
                return []

            self.logger.debug(f"Retrieved {len(entries)} entries from playlist.")
            parsed_tracks: list[dtos.TrackBase] = []
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

                # TODO: self.database_service must not be None here
                if self.database_service and self.database_service.track_is_transcribed(
                    track_webpage_url
                ):
                    self.logger.debug(
                        f"Skipping track {index + 1} @ {track_webpage_url}: Already transcribed."
                    )
                    continue

                track = dtos.TrackBase(
                    title=title,
                    webpage_url=HttpUrl(track_webpage_url),
                    download_url=HttpUrl(track_download_url),
                    uploader=uploader_name,
                    duration_seconds=duration,
                    track_number_in_playlist=index + 1,
                    playlist_url=HttpUrl(playlist_url),
                )
                parsed_tracks.append(track)
                self.logger.debug(
                    f"Parsed track {track.title} @ (URL: {track.webpage_url}, "
                )
            return parsed_tracks

    def download_track(self, track: dtos.TrackBase) -> dtos.TrackDownloaded:
        self.logger.debug(f"Downloading track: {track.title} @ {track.webpage_url}")
        download_opts: dict[str, Any] = self.base_ydl_opts.copy()
        download_opts["outtmpl"] = str(self.save_directory / track.title)
