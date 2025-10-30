"""Market data collector package initialization."""

from .config import (
    ExchangeSettings,
    LoggingSettings,
    MarketDataSettings,
    OrderbookSettings,
    RuntimeFlags,
    StorageSettings,
    get_settings,
    settings,
)
from .exchange import ExchangeAdapter, create_exchange_adapter
from .runtime import (
    Runtime,
    acquire_reader,
    get_runtime,
    reader_session,
    release_reader,
    runtime,
    start as start_runtime,
    stop as stop_runtime,
)
from .storage import SQLiteStorage
from .utils.logging import configure_logging, get_logger

__all__ = [
    "ExchangeSettings",
    "LoggingSettings",
    "MarketDataSettings",
    "OrderbookSettings",
    "RuntimeFlags",
    "StorageSettings",
    "get_settings",
    "settings",
    "ExchangeAdapter",
    "create_exchange_adapter",
    "Runtime",
    "runtime",
    "get_runtime",
    "start_runtime",
    "stop_runtime",
    "acquire_reader",
    "release_reader",
    "reader_session",
    "SQLiteStorage",
    "configure_logging",
    "get_logger",
]

configure_logging()
