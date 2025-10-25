import logging
import pathlib
import platform
import sys

import webview

from app.api import BridgeAPI

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def get_resource_path(relative_path: str) -> pathlib.Path:
    """获取资源文件的绝对路径，兼容 PyInstaller 打包后的运行时环境。
    
    在开发环境中返回相对于当前文件的路径，
    在 PyInstaller 打包后返回临时解压目录（_MEIPASS）中的路径。
    """
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller 打包后的临时目录
        base_path = pathlib.Path(sys._MEIPASS)
    else:
        # 开发环境
        base_path = pathlib.Path(__file__).parent
    return base_path / relative_path


def check_webview_runtime() -> bool:
    """检查当前平台是否有所需的 WebView 运行时。"""
    system = platform.system()
    logger.info(f"Running on {system} {platform.release()}")

    if system == "Windows":
        try:
            import winreg
        except ImportError:
            logger.warning("Cannot check WebView2 status: winreg not available")
            return True

        try:
            key_path = r"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path):
                logger.info("WebView2 runtime detected")
                return True
        except FileNotFoundError:
            try:
                key_path = r"SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path):
                    logger.info("WebView2 runtime detected")
                    return True
            except FileNotFoundError:
                logger.error("WebView2 runtime not found")
                return False
    elif system == "Darwin":
        logger.info("Using macOS WKWebView (built-in, no additional runtime required)")
    elif system == "Linux":
        logger.info("Using Linux WebKit (requires webkit2gtk)")
    else:
        logger.warning(f"Unknown platform: {system}")

    return True


def show_webview2_error() -> None:
    """显示缺少 WebView2 运行时的错误消息。"""
    error_message = """
需要 Microsoft Edge WebView2 运行时，但未安装。

请从以下地址下载并安装：
https://developer.microsoft.com/microsoft-edge/webview2/

安装后重启应用程序。
"""
    print(error_message, file=sys.stderr)
    logger.error("WebView2 runtime not installed. Application cannot start.")

    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "需要 WebView2",
            "未安装 Microsoft Edge WebView2 运行时。\n\n"
            "下载地址：\n"
            "https://developer.microsoft.com/microsoft-edge/webview2/\n\n"
            "应用程序现在将退出。",
        )
        root.destroy()
    except Exception:
        pass


def setup_console_logging(window) -> None:
    """设置 webview 窗口的控制台消息日志记录。"""

    def on_console_message(message, level):
        log_level = logging.DEBUG
        if level == "error":
            log_level = logging.ERROR
        elif level == "warning":
            log_level = logging.WARNING
        elif level == "info":
            log_level = logging.INFO

        logger.log(log_level, f"[JS Console] {message}")

    if hasattr(window.events, "console_message"):
        window.events.console_message += on_console_message


def main() -> None:
    logger.info("Starting DouDou Assistant")

    if not check_webview_runtime():
        show_webview2_error()
        sys.exit(1)

    data_dir = pathlib.Path("./data")
    data_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Data directory: {data_dir.resolve()}")

    profile_dir = data_dir / "webview_profile"
    profile_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Profile directory: {profile_dir.resolve()}")

    db_path = data_dir / "douyin.db"
    logger.info(f"Database path: {db_path.resolve()}")

    api = BridgeAPI(db_path)

    inject_path = get_resource_path("app/inject.js")
    scroll_path = get_resource_path("app/scroll.js")

    with inject_path.open("r", encoding="utf-8") as fp:
        inject_js = fp.read()
    logger.debug(f"Loaded inject.js ({len(inject_js)} chars)")

    with scroll_path.open("r", encoding="utf-8") as fp:
        scroll_js = fp.read()
    logger.debug(f"Loaded scroll.js ({len(scroll_js)} chars)")

    combined_js = inject_js + "\n\n" + scroll_js

    logger.info("Creating UI window")
    ui_window = webview.create_window(
        "DouDou Assistant",
        url=get_resource_path("app/ui/index.html").resolve().as_uri(),
        js_api=api,
        storage_path=str(profile_dir.resolve()),
    )
    setup_console_logging(ui_window)

    logger.info("Creating crawler window")
    crawler_window = webview.create_window(
        "Douyin Session",
        url="about:blank",
        js_api=api,
        hidden=True,
        storage_path=str(profile_dir.resolve()),
    )
    setup_console_logging(crawler_window)

    api.bind_windows(ui_window, crawler_window, combined_js)

    logger.info("Starting webview application")
    webview.start()
    logger.info("Application stopped")


if __name__ == "__main__":
    main()
