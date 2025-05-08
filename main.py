import logging

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

import paths
from config import settings
from service.database import IDatabase, PostgresDatabase
from service.downloader import IDownloaderService, SoundcloudDownloaderService
from service.transcriber import ITranscriberService, WhiserXTranscriberService


def run(
    logger: logging.Logger,
    database_service: IDatabase,
    downloader_service: IDownloaderService,
    transcriber_service: ITranscriberService,
):
    paths.init_tmp_paths()

    logger.debug(f"Attempting to download playlist: {settings.URL}")
    if settings.IS_PLAYLIST:
        track_metadatas = downloader_service.get_playlist_tracks_metadata(settings.URL)
        for metadata in track_metadatas[0:1]:
            logger.debug(f"Processing track: {metadata.title} @ {metadata.webpage_url}")
            track_downloaded = downloader_service.download_track(metadata)
            logger.debug(f"downloaded to {track_downloaded.audio_file_path}")
    else:
        track_metadata = downloader_service.get_track_metadata(settings.URL)
        if track_metadata:
            logger.debug(
                f"Processing track: {track_metadata.title} @ {track_metadata.webpage_url}"
            )
            track_downloaded = downloader_service.download_track(track_metadata)


if __name__ == "__main__":
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.DEBUG),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(settings.LOG_FILE), logging.StreamHandler()],
    )

    logger = logging.getLogger(__name__)
    db_engine: Engine = create_engine(settings.DATABASE_URL)
    database_service: IDatabase = PostgresDatabase(db_engine)
    downloader_service: IDownloaderService = SoundcloudDownloaderService(
        database_service,
        save_directory=paths.AUDIO_DIR,
    )
    transcriber_service: ITranscriberService = WhiserXTranscriberService()
    run(
        logger=logger,
        database_service=database_service,
        downloader_service=downloader_service,
        transcriber_service=transcriber_service,
    )
