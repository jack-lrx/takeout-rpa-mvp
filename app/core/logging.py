import logging
from logging.config import dictConfig


LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
        }
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}


def configure_logging(level: str = "INFO") -> None:
    config = LOGGING_CONFIG.copy()
    config["root"] = dict(LOGGING_CONFIG["root"])
    config["root"]["level"] = level.upper()
    dictConfig(config)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
