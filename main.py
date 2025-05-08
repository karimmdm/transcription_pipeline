import logging
import sys
import paths
from service.database import IDatabase, PostgresDatabase
from service.downloader import SoundcloudDownloaderService, IDownloaderService
from service.transcriber import ITranscriberService
from sqlalchemy import create_engine, Engine
from config import settings


def run(
    logger: logging.Logger,
    database_service: IDatabase,
    downloader_service: IDownloaderService,
    transcriber_service: ITranscriberService,
):
    paths.init_tmp_paths()

    logger.debug(f"Attempting to download playlist: {settings.PLAYLIST_URL}")
    track_metadatas = downloader_service.get_playlist_tracks(settings.PLAYLIST_URL)

    for track in track_metadatas[0:1]:
        logger.debug(f"Processing track: {track.title} @ {track.webpage_url}")
        track_downloaded = downloader_service.download_track(track, paths.AUDIO_DIR)
        logger.debug(f"downloaded to {track_downloaded.audio_file_path}")


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
        save_directory=paths.AUDIO_DIR
    )
    transcriber_service: ITranscriberService = ITranscriberService()
    run(
        logger=logger,
        database_service=database_service,
        downloader_service=downloader_service,
        transcriber_service=transcriber_service,
    )
