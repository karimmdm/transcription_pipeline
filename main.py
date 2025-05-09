import logging
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from config import settings
from schemas import Track
from service.database_handler import IDatabase, PostgresDatabase
from service.downloader import IDownloaderService, SoundcloudDownloaderService
from service.transcriber import ITranscriberService, WhiserXTranscriberService


def run(
    logger: logging.Logger,
    database_service: IDatabase,
    downloader_service: IDownloaderService,
    transcriber_service: ITranscriberService,
) -> None:
    tracks: list[Track] = []
    if settings.IS_PLAYLIST:
        logger.debug(f"Attempting to download playlist: {settings.URL}")
        tracks.extend(downloader_service.download_playlist(settings.URL))
    else:
        logger.debug(f"Attempting to download track: {settings.URL}")
        tracks.append(downloader_service.download_track(settings.URL))

    for track in tracks:
        if track:
            logger.debug(f"Processing track: {track.title} @ {track.webpage_url}")
            track_transcribed, transcript = transcriber_service.transcribe_audio(
                track=track, save_to_disk=True
            )


if __name__ == "__main__":
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.DEBUG),
        # format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(settings.LOG_FILE), logging.StreamHandler()],
    )

    logger = logging.getLogger(__name__)
    db_engine: Engine = create_engine(settings.DATABASE_URL)
    database_service: IDatabase = PostgresDatabase(db_engine)
    downloader_service: IDownloaderService = SoundcloudDownloaderService(
        database_service,
        save_directory=settings.AUDIO_DIR,
    )
    transcriber_service: ITranscriberService = WhiserXTranscriberService(
        database_service=database_service,
        save_directory=settings.TRANSCRIPT_DIR,
        model_name="medium",
        device="cpu",
        compute_type="int8",
    )
    run(
        logger=logger,
        database_service=database_service,
        downloader_service=downloader_service,
        transcriber_service=transcriber_service,
    )
