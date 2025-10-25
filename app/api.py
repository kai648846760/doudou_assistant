from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from threading import Event, Timer
from typing import Any
from urllib.parse import urlparse

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
        self.inject_js = ""
        self._stop_event = Event()
        self._pending_action: dict[str, Any] | None = None
        self._duplicate_batches = 0
        self._video_complete_timer: Timer | None = None
        logger.info("Bridge API initialised")

    # ---------------------------------------------------------------------
    # Window binding and helpers
    # ---------------------------------------------------------------------
    def bind_windows(self, ui_window, crawler_window, inject_js: str) -> None:
        self.ui_window = ui_window
        self.crawler_window = crawler_window
        self.inject_js = inject_js

        def on_ui_loaded() -> None:
            self._emit_progress()

        def on_crawler_loaded() -> None:
            if self.inject_js:
                try:
                    crawler_window.evaluate_js(self.inject_js)
                except Exception:  # pragma: no cover - pywebview runtime
                    logger.exception("Failed to inject JavaScript into crawler window")
            self._apply_pending_action()

        ui_window.events.loaded += on_ui_loaded
        crawler_window.events.loaded += on_crawler_loaded

    def _emit_progress(self) -> None:
        if not self.ui_window:
            return
        status = self.state.snapshot()
        try:
            js_code = (
                "window.dispatchEvent(new CustomEvent('crawl-progress', { detail: "
                + json.dumps(status)
                + " }));"
            )
            self.ui_window.evaluate_js(js_code)
        except Exception:  # pragma: no cover - pywebview runtime
            logger.debug("UI window not ready for progress update")

    def _apply_pending_action(self) -> None:
        if not self.crawler_window or not self._pending_action:
            return

        action = self._pending_action
        self._pending_action = None

        if action.get("mode") == "author":
            latest = action.get("latest") or {}
            payload = json.dumps(
                {
                    "latest_aweme_id": latest.get("aweme_id"),
                    "latest_create_time": latest.get("create_time"),
                    "author_id": latest.get("author_id"),
                }
            )
            script = (
                "(function(){"
                "window.__douyinCrawlerContext = " + payload + ";"
                "if (window.__douyinScroller) { window.__douyinScroller.start(); }"
                "})();"
            )
        else:
            script = "(function(){ window.scrollTo(0, 0); })();"

        try:
            self.crawler_window.evaluate_js(script)
        except Exception:  # pragma: no cover - pywebview runtime
            logger.exception("Failed to apply pending crawler action")

    def _load_crawler_url(self, url: str) -> None:
        if not self.crawler_window:
            raise RuntimeError("Crawler window is not available")

        try:
            self.crawler_window.show()
        except Exception:  # pragma: no cover - pywebview runtime
            logger.debug("Unable to show crawler window")

        self.state.set_status("navigating", f"Opening {url}")
        try:
            self.crawler_window.load_url(url)
        except Exception:  # pragma: no cover - pywebview runtime
            logger.exception("Failed to load URL in crawler window")

    def _stop_js_runtime(self) -> None:
        if not self.crawler_window:
            return
        try:
            self.crawler_window.evaluate_js(
                "window.__douyinScroller && window.__douyinScroller.stop && window.__douyinScroller.stop();"
            )
        except Exception:  # pragma: no cover - pywebview runtime
            logger.debug("Failed to stop scroller runtime")

    def _complete_crawl(self, message: str = "Crawl complete") -> None:
        self._stop_js_runtime()
        self._cancel_video_timer()
        self.state.complete(message)
        try:
            if self.crawler_window:
                self.crawler_window.hide()
        except Exception:  # pragma: no cover - pywebview runtime
            logger.debug("Unable to hide crawler window")
        self._emit_progress()

    def _cancel_video_timer(self) -> None:
        """Cancel any pending video completion timer."""
        if self._video_complete_timer:
            self._video_complete_timer.cancel()
            self._video_complete_timer = None

    def _schedule_video_completion(self, delay: float = 2.0) -> None:
        """Schedule automatic completion of video crawl after a delay."""
        self._cancel_video_timer()

        def complete_video_crawl():
            if self.state.active and self.state.mode == "video":
                logger.info("Auto-completing video crawl after successful capture")
                self._complete_crawl("Video captured successfully")

        self._video_complete_timer = Timer(delay, complete_video_crawl)
        self._video_complete_timer.start()

    # ---------------------------------------------------------------------
    # Login helpers
    # ---------------------------------------------------------------------
    def login_state(self) -> dict[str, Any]:
        if not self.crawler_window:
            return {"logged_in": False, "message": "Crawler window not ready"}

        try:
            current_url = self.crawler_window.get_current_url() or ""
        except Exception:  # pragma: no cover - pywebview runtime
            current_url = ""

        if "douyin.com" not in current_url:
            try:
                self.crawler_window.load_url("https://www.douyin.com/")
                time.sleep(0.5)
            except Exception:  # pragma: no cover - pywebview runtime
                logger.debug("Unable to navigate to Douyin for login check")

        script = """
            (function() {
                try {
                    const cookies = document.cookie || "";
                    const hasSession = /sessionid(_ss)?=/.test(cookies);
                    const loginButton = document.querySelector('[data-e2e="top-login-button"]')
                        || document.querySelector('button[data-e2e="login-button"]')
                        || document.querySelector('.login-button');
                    return {
                        logged_in: hasSession || !loginButton,
                        cookies,
                        url: window.location.href
                    };
                } catch (error) {
                    return { logged_in: false, error: error.message, url: window.location.href };
                }
            })();
        """
        try:
            result = self.crawler_window.evaluate_js(script)
        except Exception as exc:  # pragma: no cover - pywebview runtime
            logger.exception("Failed to evaluate login script")
            return {"logged_in": False, "message": f"Login check failed: {exc}"}

        if isinstance(result, str):
            try:
                data = json.loads(result)
            except json.JSONDecodeError:
                data = {"logged_in": False, "raw": result}
        else:
            data = result or {}

        logged_in = bool(data.get("logged_in"))
        message = (
            "Logged in to Douyin"
            if logged_in
            else "Not logged in – open the Douyin window and sign in."
        )
        return {"logged_in": logged_in, "message": message, "details": data}

    # ---------------------------------------------------------------------
    # Crawl entry points
    # ---------------------------------------------------------------------
    def start_crawl_author(self, author_input: str) -> dict[str, Any]:
        if self.state.active:
            return {"success": False, "error": "Another crawl is already running"}

        resolved = self._resolve_author_input(author_input)
        url = resolved.get("url")
        identifier = resolved.get("identifier")
        if not url:
            return {"success": False, "error": "Could not resolve author input"}

        author_record = None
        if identifier:
            author_record = self.db.find_author(identifier)

        latest = None
        if author_record:
            latest = self.db.get_latest_for_author(author_record.author_id)

        context = {
            "author_identifier": identifier,
            "author_id": author_record.author_id if author_record else None,
            "author_name": author_record.nickname if author_record else None,
        }

        self.state.start("author", url, context=context)
        self._stop_event.clear()
        self._duplicate_batches = 0
        self._cancel_video_timer()
        self._pending_action = {"mode": "author", "latest": latest}

        self._load_crawler_url(url)
        self._emit_progress()

        return {
            "success": True,
            "message": "Navigating to author profile",
            "target": url,
            "context": context,
        }

    def start_crawl_video(self, url: str) -> dict[str, Any]:
        if self.state.active:
            return {"success": False, "error": "Another crawl is already running"}

        cleaned_url = url.strip()
        if not cleaned_url:
            return {"success": False, "error": "Video URL is required"}

        if not cleaned_url.startswith("http"):
            cleaned_url = f"https://www.douyin.com/video/{cleaned_url}"

        self.state.start("video", cleaned_url)
        self._stop_event.clear()
        self._duplicate_batches = 0
        self._cancel_video_timer()
        self._pending_action = {"mode": "video"}

        self._load_crawler_url(cleaned_url)
        self._emit_progress()

        return {
            "success": True,
            "message": "Navigating to video",
            "target": cleaned_url,
        }

    def _resolve_author_input(self, author_input: str) -> dict[str, str | None]:
        value = (author_input or "").strip()
        if not value:
            return {"url": None, "identifier": None}

        url = value
        if not url.startswith("http"):
            slug = value.lstrip("@")
            url = f"https://www.douyin.com/user/{slug}"

        parsed = urlparse(url)
        if not parsed.scheme:
            url = "https://" + url.lstrip("/")
            parsed = urlparse(url)

        identifier = None
        path_parts = [part for part in parsed.path.split("/") if part]
        if path_parts:
            if path_parts[0] == "user" and len(path_parts) >= 2:
                identifier = path_parts[1]
            elif len(path_parts) == 1:
                identifier = path_parts[0]

        return {"url": url, "identifier": identifier}

    # ---------------------------------------------------------------------
    # Data ingestion
    # ---------------------------------------------------------------------
    def push_chunk(self, items: list[dict[str, Any]]) -> dict[str, Any]:
        if not isinstance(items, list) or not items:
            return {"success": False, "error": "Items must be a non-empty list"}

        try:
            self.state.increment_received(len(items))
            result = self.db.upsert_videos(items)
            inserted = result.get("inserted", 0)
            updated = result.get("updated", 0)
            self.state.update_counts(inserted, updated)

            if self.state.mode == "author":
                if inserted == 0:
                    self._duplicate_batches += 1
                else:
                    self._duplicate_batches = 0

                if self._duplicate_batches >= 3:
                    logger.info("Duplicate batches threshold reached; completing crawl")
                    self._complete_crawl("Reached existing items")
                else:
                    self.state.set_status(
                        "running",
                        f"Inserted {inserted} new videos, {updated} refreshed",
                    )
            elif self.state.mode == "video":
                self.state.set_status(
                    "running", f"Captured {inserted} new videos, {updated} refreshed"
                )
                # Auto-complete video crawl after capturing data
                if inserted > 0 or updated > 0:
                    logger.info("Video data captured, scheduling completion")
                    self._schedule_video_completion(delay=2.0)
            else:
                self.state.set_status(
                    "running", f"Captured {inserted} new videos, {updated} refreshed"
                )

            self._emit_progress()

            return {
                "success": True,
                "inserted": inserted,
                "updated": updated,
                "total_inserted": self.state.items_inserted,
                "total_updated": self.state.items_updated,
            }
        except Exception as exc:  # pragma: no cover - runtime side effects
            logger.exception("Error processing chunk")
            self.state.set_error(str(exc))
            self._emit_progress()
            return {"success": False, "error": str(exc)}

    # ---------------------------------------------------------------------
    # Data querying and export
    # ---------------------------------------------------------------------
    def list_videos(
        self,
        filters: dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict[str, Any]:
        try:
            return self.db.list_videos(filters or {}, page, page_size)
        except Exception as exc:  # pragma: no cover - DB failure handling
            logger.exception("Error listing videos")
            return {
                "error": str(exc),
                "items": [],
                "page": page,
                "page_size": page_size,
                "total": 0,
            }

    def export_csv(self, filters: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            export_path = self.db.export_csv(filters or {})
            return {"success": True, "path": str(export_path)}
        except Exception as exc:  # pragma: no cover - IO failure
            logger.exception("Error exporting CSV")
            return {"success": False, "error": str(exc)}

    # ---------------------------------------------------------------------
    # Flow control
    # ---------------------------------------------------------------------
    def stop_crawl(self) -> dict[str, Any]:
        if not self.state.active:
            return {"success": False, "error": "No active crawl"}

        self._stop_event.set()
        self._stop_js_runtime()
        self._cancel_video_timer()
        self.state.stop(message="Stopped by user")
        try:
            if self.crawler_window:
                self.crawler_window.hide()
        except Exception:  # pragma: no cover - pywebview runtime
            logger.debug("Unable to hide crawler window")
        self._emit_progress()
        return {"success": True, "message": "Crawl stopped"}

    def on_scroll_complete(self) -> dict[str, Any]:
        logger.info("Scroll reported as complete from JS bridge")
        if self.state.active:
            self._complete_crawl("Reached end of list")
        return {"success": True}

    def open_login(self) -> dict[str, Any]:
        self._pending_action = None
        try:
            self._load_crawler_url("https://www.douyin.com/")
            return {"success": True, "message": "Douyin login window opened"}
        except Exception as exc:  # pragma: no cover - pywebview runtime
            logger.exception("Failed to open Douyin login window")
            return {"success": False, "error": str(exc)}

    # ---------------------------------------------------------------------
    # Utilities
    # ---------------------------------------------------------------------
    def trigger_mock_push(self) -> dict[str, Any]:
        if self.crawler_window:
            try:
                self.crawler_window.evaluate_js("window.__awemeBridge?.mockPush();")
            except Exception:  # pragma: no cover - pywebview runtime
                logger.debug("Failed to trigger mock push")
        return {"success": True}
