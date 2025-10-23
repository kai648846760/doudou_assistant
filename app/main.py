import pathlib

import webview


class API:
    def __init__(self) -> None:
        self.message = "PyWebView App"

    def get_message(self) -> str:
        return self.message


def main() -> None:
    data_dir = pathlib.Path("./data/webview_profile")
    data_dir.mkdir(parents=True, exist_ok=True)

    api = API()

    window = webview.create_window(
        "PyWebView App",
        url=(pathlib.Path(__file__).parent / "ui" / "index.html").resolve().as_uri(),
        js_api=api,
        storage_path=str(data_dir.resolve()),
    )

    webview.start()


if __name__ == "__main__":
    main()
