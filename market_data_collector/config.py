from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

import yaml
from pydantic import BaseModel, Field, ValidationError

PACKAGE_ROOT = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = PACKAGE_ROOT / "configs" / "market.yaml"
ENV_PREFIX = "MARKET_DATA_"
ENV_CONFIG_PATH_KEY = f"{ENV_PREFIX}CONFIG_PATH"


class ExchangeSettings(BaseModel):
    """Configuration for the upstream exchange from which data is pulled."""

    name: str
    market_type: str
    base_rest_url: str
    base_websocket_url: str


class OrderbookSettings(BaseModel):
    """Order book collection configuration."""

    depth: int = Field(gt=0)


class StorageSettings(BaseModel):
    """Persistence configuration for collected market data."""

    backend: str
    path: str
    compression: str | None = None


class LoggingSettings(BaseModel):
    """Logging configuration for the collector."""

    level: str = "INFO"
    file: str = "logs/market_data_collector.log"
    format: str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    datefmt: str | None = None


class RuntimeFlags(BaseModel):
    """Feature flags toggling runtime behaviour."""

    dry_run: bool = False
    enable_metrics: bool = True
    use_proxy: bool = False


class MarketDataSettings(BaseModel):
    """Top-level configuration container for the market data collector."""

    exchange: ExchangeSettings
    symbols: List[str]
    intervals: Dict[str, str]
    orderbook: OrderbookSettings
    storage: StorageSettings
    logging: LoggingSettings
    runtime: RuntimeFlags


def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Configuration file {path} must contain a mapping at the root.")
    return data


def _deep_merge(base: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
    for key, value in overrides.items():
        if (
            key in base
            and isinstance(base[key], dict)
            and isinstance(value, dict)
        ):
            base[key] = _deep_merge(dict(base[key]), value)
        else:
            base[key] = value
    return base


def _parse_env_value(raw_value: str) -> Any:
    value = raw_value.strip()
    if value == "":
        return value

    try:
        return json.loads(value)
    except json.JSONDecodeError:
        lower = value.lower()
        if lower in {"true", "false"}:
            return lower == "true"
        if lower in {"null", "none"}:
            return None
        try:
            if lower.startswith("0") and lower != "0":
                raise ValueError
            return int(value)
        except ValueError:
            try:
                return float(value)
            except ValueError:
                return value


def _set_nested(mapping: Dict[str, Any], path: List[str], value: Any) -> None:
    cursor = mapping
    for key in path[:-1]:
        cursor = cursor.setdefault(key, {})
    cursor[path[-1]] = value


def _collect_env_overrides() -> Dict[str, Any]:
    overrides: Dict[str, Any] = {}
    for key, value in os.environ.items():
        if not key.startswith(ENV_PREFIX):
            continue
        if key == ENV_CONFIG_PATH_KEY:
            continue
        trimmed = key[len(ENV_PREFIX) :]
        if not trimmed:
            continue
        segments = [segment.lower() for segment in trimmed.split("__") if segment]
        if not segments:
            continue
        _set_nested(overrides, segments, _parse_env_value(value))
    return overrides


def _load_composed_config() -> Dict[str, Any]:
    config_data = _load_yaml(DEFAULT_CONFIG_PATH)

    custom_config_path = os.getenv(ENV_CONFIG_PATH_KEY)
    if custom_config_path:
        override_path = Path(custom_config_path).expanduser()
        override_data = _load_yaml(override_path)
        config_data = _deep_merge(config_data, override_data)

    env_overrides = _collect_env_overrides()
    if env_overrides:
        config_data = _deep_merge(config_data, env_overrides)

    return config_data


@lru_cache(maxsize=1)
def get_settings() -> MarketDataSettings:
    """Return cached application settings built from defaults and overrides."""

    raw_config = _load_composed_config()
    try:
        return MarketDataSettings.model_validate(raw_config)
    except ValidationError as exc:  # pragma: no cover - pydantic raises rich errors
        raise ValueError("Invalid market data configuration") from exc


settings: MarketDataSettings = get_settings()


__all__ = [
    "ExchangeSettings",
    "OrderbookSettings",
    "StorageSettings",
    "LoggingSettings",
    "RuntimeFlags",
    "MarketDataSettings",
    "get_settings",
    "settings",
]
