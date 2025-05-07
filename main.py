import logging
import paths
from service.database import IDatabase, PostgresDatabase
from service.downloader import SoundcloudDownloaderService, IDownloaderService
from service.transcriber import ITranscriberService
from sqlalchemy import create_engine
from config import settings


def run(
    database_service: IDatabase,
    downloader_service: IDownloaderService,
    transcriber_service: ITranscriberService,
):
    paths.init_tmp_paths()

    logger.info(f"Attempting to download playlist: {settings.PLAYLIST_URL}")
    tracks = downloader_service.get_playlist_tracks(settings.PLAYLIST_URL)


if __name__ == "__main__":
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.DEBUG),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(settings.LOG_FILE),
            logging.StreamHandler(),
        ],
    )

    logger = logging.getLogger(__name__)
    db_engine = create_engine(settings.DATABASE_URL)
    database_service: IDatabase = PostgresDatabase(db_engine)
    downloader_service: IDownloaderService = SoundcloudDownloaderService(database_service)
    transcriber_service: ITranscriberService = None
    run(
        database_service=database_service,
        downloader_service=downloader_service,
        transcriber_service=transcriber_service,
    )
