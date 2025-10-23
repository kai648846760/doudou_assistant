import json
import pathlib
import threading
from typing import Optional

import webview

from app.crawler import AuthorCrawler
from app.db import Database


class API:
    def __init__(
        self,
        window: Optional[webview.Window] = None,
        db_path: Optional[str] = None,
    ) -> None:
        self.message = "Douyin Author Crawler"
        self.window = window
        self.database = Database(db_path or "./data/crawler.db")
        self.crawler = AuthorCrawler(self.database)
        self.is_logged_in = False
        self.crawl_active = False

    def bind_window(self, window: webview.Window) -> None:
        self.window = window

    def get_message(self) -> str:
        return self.message

    def check_login_status(self) -> dict:
        """Check if user is logged in to Douyin."""
        return {"logged_in": self.is_logged_in}

    def set_login_status(self, status: bool) -> dict:
        """Set login status (for testing purposes)."""
        self.is_logged_in = status
        return {"logged_in": self.is_logged_in}

    def navigate_to_login(self) -> None:
        """Navigate to Douyin login page."""
        if self.window:
            self.window.evaluate_js("window.showTab('login')")

    def start_crawl(self, author_input: str) -> dict:
        """Start crawling an author's videos."""
        if self.crawl_active:
            return {"success": False, "error": "Crawl already in progress"}

        if not self.is_logged_in:
            self.navigate_to_login()
            return {
                "success": False,
                "error": "Not logged in. Please log in to Douyin first.",
                "requires_login": True,
            }

        def crawl_thread() -> None:
            self.crawl_active = True
            try:

                def progress_callback(event_type: str, data: dict) -> None:
                    if self.window:
                        payload = json.dumps(data)
                        self.window.evaluate_js(
                            f"window.handleCrawlProgress({json.dumps(event_type)}, {payload})"
                        )

                result = self.crawler.crawl(author_input, progress_callback)

                if self.window:
                    payload = json.dumps(result)
                    self.window.evaluate_js(
                        f"window.handleCrawlComplete({payload})"
                    )

            except Exception as exc:  # noqa: BLE001
                if self.window:
                    error_data = json.dumps(
                        {"success": False, "error": str(exc)}
                    )
                    self.window.evaluate_js(
                        f"window.handleCrawlError({error_data})"
                    )
            finally:
                self.crawl_active = False

        thread = threading.Thread(target=crawl_thread, daemon=True)
        thread.start()

        return {"success": True, "message": "Crawl started"}

    def get_awemes(self, author_id: Optional[int] = None, limit: int = 100) -> dict:
        """Get collected awemes from database."""
        awemes = self.database.get_all_awemes(author_id, limit)
        return {"success": True, "awemes": awemes}

    def get_stats(self) -> dict:
        """Get overall statistics."""
        return {"success": True}


def main() -> None:
    data_dir = pathlib.Path("./data/webview_profile")
    data_dir.mkdir(parents=True, exist_ok=True)

    api = API(db_path=str((data_dir / "crawler.db").resolve()))

    window = webview.create_window(
        "Douyin Author Crawler",
        url=(pathlib.Path(__file__).parent / "ui" / "index.html").resolve().as_uri(),
        js_api=api,
        storage_path=str(data_dir.resolve()),
        width=1200,
        height=800,
    )

    api.bind_window(window)

    webview.start()


if __name__ == "__main__":
    main()
