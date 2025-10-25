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

    db_path = data_dir / "douyin.db"

    api = BridgeAPI(db_path)

    inject_path = pathlib.Path(__file__).parent / "inject.js"
    scroll_path = pathlib.Path(__file__).parent / "scroll.js"

    with inject_path.open("r", encoding="utf-8") as fp:
        inject_js = fp.read()

    with scroll_path.open("r", encoding="utf-8") as fp:
        scroll_js = fp.read()

    combined_js = inject_js + "\n\n" + scroll_js

    ui_window = webview.create_window(
        "DouDou Assistant",
        url=(pathlib.Path(__file__).parent / "ui" / "index.html").resolve().as_uri(),
        js_api=api,
        storage_path=str(profile_dir.resolve()),
    )

    crawler_window = webview.create_window(
        "Douyin Session",
        url="about:blank",
        js_api=api,
        hidden=True,
        storage_path=str(profile_dir.resolve()),
    )

    api.bind_windows(ui_window, crawler_window, combined_js)

    webview.start()


if __name__ == "__main__":
    main()
