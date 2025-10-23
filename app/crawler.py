from __future__ import annotations

import datetime as dt
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class CrawlState:
    """Tracks the current state of a crawl session."""

    active: bool = False
    mode: Optional[str] = None
    target: Optional[str] = None
    started_at: Optional[dt.datetime] = None
    items_received: int = 0
    items_inserted: int = 0
    items_updated: int = 0
    last_error: Optional[str] = None
    lock: threading.Lock = field(default_factory=threading.Lock)

    def reset(self) -> None:
        with self.lock:
            self.active = False
            self.mode = None
            self.target = None
            self.started_at = None
            self.items_received = 0
            self.items_inserted = 0
            self.items_updated = 0
            self.last_error = None

    def start(self, mode: str, target: str) -> None:
        with self.lock:
            self.active = True
            self.mode = mode
            self.target = target
            self.started_at = dt.datetime.utcnow()
            self.items_received = 0
            self.items_inserted = 0
            self.items_updated = 0
            self.last_error = None

    def stop(self) -> None:
        with self.lock:
            self.active = False

    def update_counts(self, inserted: int, updated: int) -> None:
        with self.lock:
            self.items_inserted += inserted
            self.items_updated += updated

    def increment_received(self, count: int) -> None:
        with self.lock:
            self.items_received += count

    def set_error(self, error: str) -> None:
        with self.lock:
            self.last_error = error
            self.active = False

    def snapshot(self) -> Dict[str, Any]:
        with self.lock:
            return {
                "active": self.active,
                "mode": self.mode,
                "target": self.target,
                "started_at": self.started_at.isoformat() if self.started_at else None,
                "items_received": self.items_received,
                "items_inserted": self.items_inserted,
                "items_updated": self.items_updated,
                "last_error": self.last_error,
            }
