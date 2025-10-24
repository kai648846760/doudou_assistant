import logging
import pathlib
import sys

import webview

from app.api import BridgeAPI

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def get_resource_path(*relative_parts: str) -> pathlib.Path:
    """Return the absolute path to a resource, supporting PyInstaller bundles."""
    if getattr(sys, "_MEIPASS", None):
        base_path = pathlib.Path(sys._MEIPASS) / "app"
    else:
        base_path = pathlib.Path(__file__).resolve().parent
    return base_path.joinpath(*relative_parts)


def main() -> None:
    data_dir = pathlib.Path("./data")
    data_dir.mkdir(parents=True, exist_ok=True)

    profile_dir = data_dir / "webview_profile"
    profile_dir.mkdir(parents=True, exist_ok=True)

    db_path = data_dir / "douyin.db"

    api = BridgeAPI(db_path)

    inject_js = get_resource_path("inject.js").read_text(encoding="utf-8")
    scroll_js = get_resource_path("scroll.js").read_text(encoding="utf-8")

    combined_js = inject_js + "\n\n" + scroll_js

    ui_window = webview.create_window(
        "DouDou Assistant",
        url=get_resource_path("ui", "index.html").resolve().as_uri(),
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
