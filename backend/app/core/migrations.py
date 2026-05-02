from pathlib import Path

from alembic import command
from alembic.config import Config

from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


def _normalize_async_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql://") and "+asyncpg" not in url:
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


def get_alembic_config() -> Config:
    project_root = Path(__file__).resolve().parents[2]
    alembic_dir = project_root / "alembic"
    config = Config()
    config.set_main_option("script_location", str(alembic_dir))
    config.set_main_option("sqlalchemy.url", _normalize_async_database_url(settings.database_url))
    return config


def run_migrations() -> None:
    logger.info("db_migrations_starting")
    command.upgrade(get_alembic_config(), "head")
    logger.info("db_migrations_complete")
