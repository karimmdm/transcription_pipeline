import os
import logging
from abc import ABC, abstractmethod
from dtos import TrackBase
from yt_dlp import YoutubeDL
from pathlib import Path
from service.database import IDatabase


class IDownloaderService(ABC):
    def __init__(self, database_service: IDatabase, ydl_opts_override: dict = None):
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
        }
        if ydl_opts_override:
            self.base_ydl_opts.update(ydl_opts_override)
        self.database_service = database_service

    @abstractmethod
    def download_playlist(self, playlist_url: str, output_dir: Path) -> list[Path]:
        """
        Downloads multiple tracks from a playlist URL using yt-dlp.

        Args:
            playlist_url: The URL of the playlist.
            output_dir: The directory to save downloaded files.

        Returns:
            A list of Path objects to successfully downloaded audio files.
        """
        pass

    @abstractmethod
    def get_playlist_tracks(self, playlist_url: str) -> list[TrackBase]:
        """
        Retrieves the list of audio URLs, titles, and indices from a playlist.

        Args:
            playlist_url: The URL of the playlist.

        Returns:
            A list of TrackBase objects.
        """
        pass

    @abstractmethod
    def download_track(self, track_url: str, output_dir: Path) -> Path:
        """
        Downloads a single track from a given URL using yt-dlp.

        Args:
            track_url: The URL of the track to download.
            output_dir: The directory to save the downloaded file.

        Returns:
            A Path object to the downloaded audio file.
        """
        pass


class SoundcloudDownloaderService(IDownloaderService):
    def __init__(self, database_service: IDatabase, ydl_opts_override: dict = None):
        super().__init__(database_service, ydl_opts_override)

    def get_playlist_tracks(self, playlist_url: str) -> list[TrackBase]:
        self.logger.debug(f"Retrieving tracks from playlist: {playlist_url}")

        fetch_opts = self.base_ydl_opts.copy()
        fetch_opts["extract_flat"] = False

        with YoutubeDL(fetch_opts) as ydl:
            info = ydl.extract_info(playlist_url, download=False)
            entries = info.get("entries", [])
            if not entries:
                self.logger.warning(f"No entries found in playlist: {playlist_url}")
                return []

            self.logger.debug(f"Retrieved {len(entries)} entries from playlist.")
            parsed_tracks: list[TrackBase] = []
            for index, entry in enumerate(entries):
                title = entry.get("title", f"Unknown Title Track {index + 1}")
                track_webpage_url = entry.get("webpage_url")
                track_download_url = entry.get("url")
                uploader_name = entry.get("uploader")
                duration = entry.get("duration")

                if not track_webpage_url or not track_download_url:
                    self.logger.warning(
                        f"Skipping track {index + 1}: Missing webpage_url or download_url."
                    )
                    continue

                # TODO: self.database_service must not be None here
                if self.database_service and self.database_service.track_is_transcribed(
                    track_webpage_url
                ):
                    self.logger.info(
                        f"Skipping track {index + 1} @ {track_webpage_url}: Already transcribed."
                    )
                    continue

                track = TrackBase(
                    title=title,
                    webpage_url=track_webpage_url,
                    download_url=track_download_url,
                    uploader=uploader_name,
                    duration_seconds=duration,
                    track_number_in_playlist=index + 1,
                    playlist_url=playlist_url,
                )
                parsed_tracks.append(track)
                self.logger.debug(
                    f"Parsed track {track.title} @ (URL: {track.webpage_url}, "
                )
            return parsed_tracks

    def _download_single_track(
        self,
        track_url: str,
        title: str,
        track_number: int,
        output_dir: Path,
        audio_format: str = "wav",
    ) -> str:
        """Helper method to download a single track."""
        self.logger.info(f"Downloading track {track_number}: {title} ({track_url})")

        # Sanitize title for filename
        safe_title = "".join(
            c if c.isalnum() or c in (" ", "-", "_") else "_" for c in title
        ).rstrip()
        filename_template = f"{track_number:03d} - {safe_title}.%(ext)s"

        download_opts = self.base_ydl_opts.copy()
        download_opts.update(
            {
                "format": "bestaudio/best",
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": audio_format,
                        "preferredquality": "192",  # Or other desired quality
                    }
                ],
                "outtmpl": str(output_dir / filename_template),
            }
        )

        # Exceptions from YoutubeDL will propagate up
        with YoutubeDL(download_opts) as ydl:
            result = ydl.extract_info(track_url, download=True)
            # yt-dlp's prepare_filename usually gives the path based on outtmpl
            # after postprocessing.
            final_path = ydl.prepare_filename(result)
            if not final_path or not os.path.exists(final_path):
                # This case indicates an issue with yt-dlp's output or file creation
                # that didn't raise an exception but didn't produce the file.
                self.logger.error(
                    f"File not found after download and postprocessing for {title}. Expected at: {final_path}"
                )
                raise FileNotFoundError(
                    f"Downloaded file for '{title}' not found at expected path: {final_path}"
                )
            self.logger.info(f"Successfully downloaded and converted: {final_path}")
            return final_path

    def download_playlist(
        self, playlist_url: str, output_dir: Path, audio_format: str = "wav"
    ) -> list[str]:
        self.logger.info(
            f"Starting download for playlist: {playlist_url} to {output_dir}"
        )
        os.makedirs(output_dir, exist_ok=True)

        downloaded_file_paths: list[str] = []
        # If get_playlist_tracks fails, the exception will propagate up,
        # and this function will terminate, which is the desired behavior.
        tracks_to_download = self.get_playlist_tracks(playlist_url)

        if not tracks_to_download:
            self.logger.warning(
                f"No tracks found in playlist {playlist_url}. Nothing to download."
            )
            return downloaded_file_paths

        total_tracks = len(tracks_to_download)
        for i, track_info in enumerate(tracks_to_download):
            self.logger.info(
                f"Processing track {i + 1}/{total_tracks}: {track_info.title}"
            )
            # The URL from get_playlist_tracks might be the webpage URL.
            # _download_single_track will let yt-dlp resolve it to the actual media.
            # If _download_single_track fails, the exception will propagate up,
            # and this loop (and function) will terminate.

            # Use track_info.download_url for downloading, as it's intended to be the direct media link.
            # track_info.webpage_url is the canonical page for the track.
            # yt-dlp can usually handle either, but download_url is more direct if available.
            file_path = self._download_single_track(
                track_info.download_url,  # Use the download_url from TrackBase
                track_info.title,
                track_info.track_number_in_playlist
                or (i + 1),  # Use provided number or fall back to index
                output_dir,
                audio_format,
            )
            # If we reach here, _download_single_track was successful
            downloaded_file_paths.append(file_path)

        self.logger.info(
            f"Playlist download complete. {len(downloaded_file_paths)}/{total_tracks} tracks downloaded successfully to {output_dir}."
        )
        return downloaded_file_paths

    def download_track(self, track_url, output_dir):
        pass
