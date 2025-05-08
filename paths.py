import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Root of the project (adjust if needed)
PROJECT_ROOT = Path(__file__).resolve().parent

TMP_DIR = PROJECT_ROOT / "tmp"
TRANSCRIPT_DIR = TMP_DIR / "transcripts"
AUDIO_DIR = TMP_DIR / "audio"


def init_tmp_paths():
    """Initializes the required directories by creating them if they don't exist."""
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    logger.debug(f"Temporary directory initialized at: {TMP_DIR}")

    TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)
    logger.debug(f"Transcript directory initialized at: {TRANSCRIPT_DIR}")

    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    logger.debug(f"Audio directory initialized at: {AUDIO_DIR}")
