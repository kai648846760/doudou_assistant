import logging
import pathlib

import webview

from app.api import BridgeAPI

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def main() -> None:
    data_dir = pathlib.Path("./data")
    data_dir.mkdir(parents=True, exist_ok=True)

    profile_dir = data_dir / "webview_profile"
    profile_dir.mkdir(parents=True, exist_ok=True)

    db_path = data_dir / "aweme.db"

    api = BridgeAPI(db_path)

    inject_path = pathlib.Path(__file__).parent / "inject.js"
    with inject_path.open("r", encoding="utf-8") as fp:
        inject_js = fp.read()

    ui_window = webview.create_window(
        "PyWebView App - Aweme Crawler",
        url=(pathlib.Path(__file__).parent / "ui" / "index.html").resolve().as_uri(),
        js_api=api,
        storage_path=str(profile_dir.resolve()),
    )

    crawler_profile = data_dir / "crawler_profile"
    crawler_profile.mkdir(parents=True, exist_ok=True)

    crawler_window = webview.create_window(
        "Crawler Session",
        url="about:blank",
        js_api=api,
        hidden=True,
        storage_path=str(crawler_profile.resolve()),
    )

    api.bind_windows(ui_window, crawler_window, inject_js)

    webview.start()


if __name__ == "__main__":
    main()
