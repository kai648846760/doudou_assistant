from __future__ import annotations

import json
import logging
from pathlib import Path
from threading import Event
from typing import Any, Dict, List

from app.crawler import CrawlState
from app.db import Database

logger = logging.getLogger(__name__)


class BridgeAPI:
    """Python API exposed to JavaScript via pywebview bridge."""

    def __init__(self, db_path: Path) -> None:
        self.db = Database(db_path)
        self.state = CrawlState()
        self.ui_window = None
        self.crawler_window = None
        self.inject_js = None
        self._stop_event = Event()
        logger.info("Bridge API initialized")

    def bind_windows(self, ui_window, crawler_window, inject_js: str) -> None:
        """Bind UI and crawler windows to this API."""
        self.ui_window = ui_window
        self.crawler_window = crawler_window
        self.inject_js = inject_js

        def on_ui_loaded():
            self._emit_progress()

        def on_crawler_loaded():
            if self.inject_js:
                crawler_window.evaluate_js(self.inject_js)

        ui_window.events.loaded += on_ui_loaded
        crawler_window.events.loaded += on_crawler_loaded

    def login_state(self) -> Dict[str, Any]:
        """Check login state from webview cookies/session."""
        return {
            "logged_in": False,
            "message": "Not implemented - use webview session storage",
        }

    def _emit_progress(self) -> None:
        """Emit current progress to UI."""
        if self.ui_window:
            status = self.state.snapshot()
            js_code = f"window.dispatchEvent(new CustomEvent('crawl-progress', {{ detail: {json.dumps(status)} }}));"
            try:
                self.ui_window.evaluate_js(js_code)
            except Exception:
                pass

    def start_crawl_author(self, author_input: str) -> Dict[str, Any]:
        """Start crawling an author profile."""
        logger.info(f"Starting author crawl: {author_input}")
        if self.state.active:
            return {"success": False, "error": "Crawl already active"}

        self._stop_event.clear()
        self.state.start(mode="author", target=author_input)

        if self.crawler_window:
            self.crawler_window.show()
            self.crawler_window.load_url(author_input)

        self._emit_progress()
        return {
            "success": True,
            "message": f"Started crawl for author: {author_input}",
        }

    def start_crawl_video(self, url: str) -> Dict[str, Any]:
        """Start crawling a single video."""
        logger.info(f"Starting video crawl: {url}")
        if self.state.active:
            return {"success": False, "error": "Crawl already active"}

        self._stop_event.clear()
        self.state.start(mode="video", target=url)

        if self.crawler_window:
            self.crawler_window.show()
            self.crawler_window.load_url(url)

        self._emit_progress()
        return {
            "success": True,
            "message": f"Started crawl for video: {url}",
        }

    def push_chunk(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Receive a chunk of items from JS, validate, and write to DB."""
        if not items:
            return {"success": False, "error": "No items provided"}

        if not isinstance(items, list):
            logger.error(f"push_chunk called with non-list: {type(items)}")
            return {"success": False, "error": "Items must be a list"}

        try:
            logger.info(f"Received chunk with {len(items)} items")
            for idx, item in enumerate(items):
                if not isinstance(item, dict):
                    raise TypeError(f"Item at index {idx} is not a dict")
            self.state.increment_received(len(items))

            result = self.db.write_items(items)
            inserted = result["inserted"]
            updated = result["updated"]

            self.state.update_counts(inserted, updated)

            logger.info(f"Processed chunk: inserted={inserted}, updated={updated}")
            
            self._emit_progress()
            
            return {
                "success": True,
                "inserted": inserted,
                "updated": updated,
                "total": self.state.items_inserted + self.state.items_updated,
            }
        except Exception as exc:
            logger.exception("Error processing chunk")
            error_msg = str(exc)
            self.state.set_error(error_msg)
            self._emit_progress()
            return {"success": False, "error": error_msg}

    def get_crawl_status(self) -> Dict[str, Any]:
        """Get current crawl status and progress."""
        return self.state.snapshot()

    def list_videos(
        self,
        filters: Dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Dict[str, Any]:
        """List videos with filtering and pagination."""
        try:
            return self.db.list_videos(filters, page, page_size)
        except Exception as exc:
            logger.exception("Error listing videos")
            return {"error": str(exc), "items": [], "page": page, "page_size": page_size, "total": 0}

    def export_csv(self, filters: Dict[str, Any] | None = None) -> Dict[str, Any]:
        """Export filtered data to CSV."""
        try:
            export_path = self.db.export_csv(filters)
            logger.info(f"Exported to: {export_path}")
            return {"success": True, "path": str(export_path)}
        except Exception as exc:
            logger.exception("Error exporting CSV")
            return {"success": False, "error": str(exc)}

    def stop_crawl(self) -> Dict[str, Any]:
        """Stop the active crawl."""
        if not self.state.active:
            return {"success": False, "error": "No active crawl"}

        self._stop_event.set()
        self.state.stop()
        if self.crawler_window:
            try:
                self.crawler_window.hide()
            except Exception:
                pass
        logger.info("Crawl stopped")
        self._emit_progress()
        return {"success": True, "message": "Crawl stopped"}

    def trigger_mock_push(self) -> Dict[str, Any]:
        """Trigger mock data push from the crawler window for testing."""
        if self.crawler_window:
            self.crawler_window.evaluate_js("window.__awemeBridge?.mockPush();")
        return {"success": True}
