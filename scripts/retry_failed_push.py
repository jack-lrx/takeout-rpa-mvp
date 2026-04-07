from __future__ import annotations

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.services.erp_client import ERPDispatcher
from app.services.store import SQLiteStore

logger = get_logger(__name__)


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    store = SQLiteStore(settings.database_path)
    store.initialize_database()
    summary = ERPDispatcher(store).retry_failed(limit=settings.retry_batch_size)
    logger.info("retry_summary %s", summary)
    print(summary)


if __name__ == "__main__":
    main()
