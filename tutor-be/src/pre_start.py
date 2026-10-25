"""Boot-time initialisation, called from the FastAPI lifespan hook."""

from pathlib import Path

from loguru import logger

from src.core.config import BASE_DIR, settings
from src.seed import seed_all


async def init_services() -> None:
    _ensure_data_dir()
    _log_tutor_config()
    await seed_all()


def _ensure_data_dir() -> None:
    """SQLite will not create a missing parent directory — it just fails to
    open the file."""
    if settings.DATABASE_URL.startswith("sqlite"):
        db_path = Path(settings.DATABASE_URL.split("///", 1)[-1])
        db_path.parent.mkdir(parents=True, exist_ok=True)
    (BASE_DIR / "data").mkdir(parents=True, exist_ok=True)


def _log_tutor_config() -> None:
    if settings.azure_configured:
        logger.info(
            "Azure LLM configured — chat={} analysis={}",
            settings.AZURE_LLM_MODEL,
            settings.AZURE_LLM_ANALYSIS_MODEL or settings.AZURE_LLM_MODEL,
        )
    else:
        logger.warning(
            "AZURE_LLM_* not configured — the tutor will refuse turns instead of "
            "faking replies. Set them in tutor-be/.env"
        )
