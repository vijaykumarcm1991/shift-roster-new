"""Application logging configuration."""

import logging
import sys
from logging.config import dictConfig

from app.core.config import settings


def configure_logging() -> None:
    """Configure structured logging for the application."""
    log_level = "DEBUG" if settings.app_debug else "INFO"

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "stream": sys.stdout,
                    "formatter": "default",
                    "level": log_level,
                },
            },
            "loggers": {
                "uvicorn": {"handlers": ["console"], "level": log_level, "propagate": False},
                "uvicorn.error": {"handlers": ["console"], "level": log_level, "propagate": False},
                "uvicorn.access": {"handlers": ["console"], "level": log_level, "propagate": False},
                "sqlalchemy.engine": {"handlers": ["console"], "level": "WARNING", "propagate": False},
                "alembic": {"handlers": ["console"], "level": "INFO", "propagate": False},
            },
            "root": {"handlers": ["console"], "level": log_level},
        }
    )


def get_logger(name: str) -> logging.Logger:
    """Return a logger with the given name."""
    return logging.getLogger(name)
