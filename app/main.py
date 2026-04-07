from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.erp_mock import router as erp_mock_router
from app.api.health import router as health_router
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.services.store import SQLiteStore


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    logger = get_logger(__name__)
    SQLiteStore(settings.database_path).initialize_database()
    logger.info(
        "application_startup",
        extra={
            "app_name": settings.app_name,
            "environment": settings.environment,
            "database_path": str(settings.database_path),
        },
    )
    yield
    logger.info("application_shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
    )
    app.include_router(health_router)
    app.include_router(erp_mock_router)
    return app


app = create_app()
