from __future__ import annotations

import datetime as dt
import threading
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CrawlState:
    """跟踪和序列化爬取进度供 UI 使用。"""

    active: bool = False
    mode: str | None = None
    target: str | None = None
    status: str = "idle"
    status_message: str | None = None
    started_at: dt.datetime | None = None
    items_received: int = 0
    items_inserted: int = 0
    items_updated: int = 0
    last_error: str | None = None
    context: dict[str, Any] = field(default_factory=dict)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def reset(self) -> None:
        with self.lock:
            self.active = False
            self.mode = None
            self.target = None
            self.status = "idle"
            self.status_message = None
            self.started_at = None
            self.items_received = 0
            self.items_inserted = 0
            self.items_updated = 0
            self.last_error = None
            self.context = {}

    def start(
        self, mode: str, target: str, context: dict[str, Any] | None = None
    ) -> None:
        with self.lock:
            self.active = True
            self.mode = mode
            self.target = target
            self.context = context or {}
            self.status = "running"
            self.status_message = "采集已启动"
            self.started_at = dt.datetime.utcnow()
            self.items_received = 0
            self.items_inserted = 0
            self.items_updated = 0
            self.last_error = None

    def stop(self, status: str = "stopped", message: str | None = None) -> None:
        with self.lock:
            self.active = False
            self.status = status
            if message is not None:
                self.status_message = message

    def complete(self, message: str | None = None) -> None:
        with self.lock:
            self.active = False
            self.status = "complete"
            if message is not None:
                self.status_message = message

    def set_status(self, status: str, message: str | None = None) -> None:
        with self.lock:
            self.status = status
            if message is not None:
                self.status_message = message

    def increment_received(self, count: int) -> None:
        if count <= 0:
            return
        with self.lock:
            self.items_received += count

    def update_counts(self, inserted: int, updated: int) -> None:
        if inserted == 0 and updated == 0:
            return
        with self.lock:
            self.items_inserted += inserted
            self.items_updated += updated

    def set_error(self, error: str) -> None:
        with self.lock:
            self.last_error = error
            self.active = False
            self.status = "error"
            self.status_message = error

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            return {
                "active": self.active,
                "mode": self.mode,
                "target": self.target,
                "status": self.status,
                "status_message": self.status_message,
                "started_at": self.started_at.isoformat() if self.started_at else None,
                "items_received": self.items_received,
                "items_inserted": self.items_inserted,
                "items_updated": self.items_updated,
                "last_error": self.last_error,
                "context": self.context,
            }
