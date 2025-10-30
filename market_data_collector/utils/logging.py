from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from ..config import settings

_MAX_BYTES = 10 * 1024 * 1024
_BACKUP_COUNT = 5
_LOGGING_INITIALIZED = False


def _resolve_level(level: int | str) -> int:
    if isinstance(level, int):
        return level
    if isinstance(level, str):
        normalized = level.upper()
        return getattr(logging, normalized, logging.INFO)
    return logging.INFO


def _resolve_log_file(path_value: str) -> Path:
    candidate = Path(path_value)
    if not candidate.is_absolute():
        candidate = Path.cwd() / candidate
    return candidate


def configure_logging(force: bool = False) -> None:
    """Configure application-wide logging using a rotating file handler."""

    global _LOGGING_INITIALIZED

    if _LOGGING_INITIALIZED and not force:
        return

    log_settings = settings.logging
    level = _resolve_level(log_settings.level)
    log_path = _resolve_log_file(log_settings.file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    existing_handlers = [
        handler
        for handler in root_logger.handlers
        if isinstance(handler, RotatingFileHandler)
        and getattr(handler, "baseFilename", None) == str(log_path)
    ]

    if existing_handlers and not force:
        _LOGGING_INITIALIZED = True
        return

    for handler in existing_handlers:
        root_logger.removeHandler(handler)
        handler.close()

    handler = RotatingFileHandler(
        log_path,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
    )
    handler.setLevel(level)
    formatter = logging.Formatter(log_settings.format, log_settings.datefmt)
    handler.setFormatter(formatter)

    root_logger.addHandler(handler)
    _LOGGING_INITIALIZED = True


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a logger with the collector configuration applied."""

    configure_logging()
    return logging.getLogger(name)


configure_logging()


__all__ = ["configure_logging", "get_logger"]
