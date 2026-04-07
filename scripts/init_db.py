from pathlib import Path

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.services.store import SQLiteStore


def init_db() -> Path:
    settings = get_settings()
    configure_logging(settings.log_level)
    logger = get_logger(__name__)

    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    SQLiteStore(settings.database_path).initialize_database()

    logger.info("database_initialized", extra={"database_path": str(settings.database_path)})
    return settings.database_path


if __name__ == "__main__":
    db_path = init_db()
    print(f"SQLite database initialized: {db_path}")
