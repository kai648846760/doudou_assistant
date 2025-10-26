from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from pathlib import Path
from threading import Event, Timer
from typing import Any
from urllib.parse import urlparse

from app.crawler import CrawlState
from app.db import Database

logger = logging.getLogger(__name__)


def retry_with_backoff(
    func: Callable[[], Any],
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,),
) -> Any:
    """遇到临时错误时使用指数退避重试函数。"""
    delay = initial_delay
    last_exception = None

    for attempt in range(max_retries):
        try:
            return func()
        except exceptions as exc:
            last_exception = exc
            if attempt < max_retries - 1:
                logger.warning(
                    f"第 {attempt + 1}/{max_retries} 次尝试失败: {exc}。"
                    f"将在 {delay:.1f} 秒后重试..."
                )
                time.sleep(delay)
                delay *= backoff_factor
            else:
                logger.error(f"{max_retries} 次尝试均失败: {exc}")

    raise last_exception


class BridgeAPI:
    """通过 pywebview 桥接暴露给 JavaScript 的 Python API。"""

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
        logger.info("桥接 API 已初始化")

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
                    logger.exception("向爬虫窗口注入脚本失败")
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
            logger.debug("UI 窗口尚未就绪，无法更新进度")

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
            logger.exception("执行预期的爬虫动作失败")

    def _load_crawler_url(self, url: str) -> None:
        if not self.crawler_window:
            raise RuntimeError("Crawler window is not available")

        try:
            self.crawler_window.show()
        except Exception:  # pragma: no cover - pywebview runtime
            logger.debug("无法显示爬虫窗口")

        self.state.set_status("navigating", f"正在打开 {url}")
        logger.info(f"加载页面: {url}")

        def load_with_retry():
            self.crawler_window.load_url(url)

        try:
            retry_with_backoff(
                load_with_retry, max_retries=3, initial_delay=0.5, backoff_factor=2.0
            )
            logger.info(f"页面加载成功: {url}")
        except Exception:  # pragma: no cover - pywebview runtime
            logger.exception("多次重试后仍无法加载爬虫窗口 URL")
            self.state.set_error(f"加载页面失败：{url}")

    def _stop_js_runtime(self) -> None:
        if not self.crawler_window:
            return
        logger.info("停止注入脚本运行")
        try:
            self.crawler_window.evaluate_js(
                "window.__douyinScroller && window.__douyinScroller.stop && window.__douyinScroller.stop();"
            )
            logger.debug("滚动脚本已停止")
        except Exception:  # pragma: no cover - pywebview runtime
            logger.warning("停止滚动脚本失败", exc_info=True)

    def _complete_crawl(self, message: str = "采集完成") -> None:
        self._stop_js_runtime()
        self._cancel_video_timer()
        self.state.complete(message)
        try:
            if self.crawler_window:
                self.crawler_window.hide()
        except Exception:  # pragma: no cover - pywebview runtime
            logger.debug("无法隐藏爬虫窗口")
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
                logger.info("捕获到视频数据，自动完成采集")
                self._complete_crawl("视频数据采集完成")

        self._video_complete_timer = Timer(delay, complete_video_crawl)
        self._video_complete_timer.start()

    # ---------------------------------------------------------------------
    # Login helpers
    # ---------------------------------------------------------------------
    def login_state(self) -> dict[str, Any]:
        if not self.crawler_window:
            return {"logged_in": False, "message": "登录窗口尚未就绪"}

        try:
            current_url = self.crawler_window.get_current_url() or ""
        except Exception:  # pragma: no cover - pywebview runtime
            current_url = ""

        if "douyin.com" not in current_url:
            try:
                self.crawler_window.load_url("https://www.douyin.com/")
                time.sleep(0.5)
            except Exception:  # pragma: no cover - pywebview runtime
                logger.debug("无法跳转至抖音首页以检查登录状态")

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
            logger.exception("执行登录状态脚本失败")
            return {"logged_in": False, "message": f"检查登录状态失败：{exc}"}

        if isinstance(result, str):
            try:
                data = json.loads(result)
            except json.JSONDecodeError:
                data = {"logged_in": False, "raw": result}
        else:
            data = result or {}

        logged_in = bool(data.get("logged_in"))
        message = (
            "已登录抖音"
            if logged_in
            else "未检测到登录，请点击“登录抖音”按钮完成登录。"
        )
        return {"logged_in": logged_in, "message": message, "details": data}

    # ---------------------------------------------------------------------
    # Crawl entry points
    # ---------------------------------------------------------------------
    def start_crawl_author(self, author_input: str) -> dict[str, Any]:
        if self.state.active:
            return {"success": False, "error": "当前已有采集任务在运行，请稍候再试"}

        resolved = self._resolve_author_input(author_input)
        url = resolved.get("url")
        identifier = resolved.get("identifier")
        if not url:
            return {"success": False, "error": "无法识别作者链接或 ID，请检查后重试"}

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
            "message": "正在打开作者主页...",
            "target": url,
            "context": context,
        }

    def start_crawl_video(self, url: str) -> dict[str, Any]:
        if self.state.active:
            return {"success": False, "error": "当前已有采集任务在运行，请稍候再试"}

        cleaned_url = url.strip()
        if not cleaned_url:
            return {"success": False, "error": "请输入视频链接"}

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
            "message": "正在打开视频页面...",
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
            logger.debug("收到的批次为空或格式不正确")
            return {"success": False, "error": "数据格式错误：需要包含内容的列表"}

        logger.info(f"收到 {len(items)} 条数据")

        def process_chunk():
            self.state.increment_received(len(items))
            result = self.db.upsert_videos(items)
            return result

        try:
            result = retry_with_backoff(
                process_chunk, max_retries=3, initial_delay=0.5, backoff_factor=2.0
            )
            inserted = result.get("inserted", 0)
            updated = result.get("updated", 0)
            self.state.update_counts(inserted, updated)
            logger.info(
                f"批量处理完成：新增 {inserted} 条，更新 {updated} 条；"
                f"累计新增 {self.state.items_inserted} 条，累计更新 {self.state.items_updated} 条"
            )

            if self.state.mode == "author":
                if inserted == 0:
                    self._duplicate_batches += 1
                else:
                    self._duplicate_batches = 0

                if self._duplicate_batches >= 3:
                    logger.info("连续收到重复数据，结束采集")
                    self._complete_crawl("检测到重复数据，采集已结束")
                else:
                    self.state.set_status(
                        "running",
                        f"新增 {inserted} 条视频，更新 {updated} 条",
                    )
            elif self.state.mode == "video":
                self.state.set_status(
                    "running", f"已接收 {inserted} 个新视频，更新 {updated} 个"
                )
                # Auto-complete video crawl after capturing data
                if inserted > 0 or updated > 0:
                    logger.info("已获取视频数据，即将自动结束采集")
                    self._schedule_video_completion(delay=2.0)
            else:
                self.state.set_status(
                    "running", f"已接收 {inserted} 个新视频，更新 {updated} 个"
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
            logger.exception("多次重试处理数据仍失败")
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
            logger.exception("查询视频列表时发生错误")
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
            logger.exception("导出 CSV 文件时发生错误")
            return {"success": False, "error": str(exc)}

    # ---------------------------------------------------------------------
    # Flow control
    # ---------------------------------------------------------------------
    def stop_crawl(self) -> dict[str, Any]:
        if not self.state.active:
            logger.warning("收到停止请求，但当前没有正在运行的采集任务")
            return {"success": False, "error": "当前没有正在运行的采集任务"}

        logger.info("用户请求停止采集")
        self._stop_event.set()
        self._stop_js_runtime()
        self._cancel_video_timer()
        self.state.stop(message="用户手动停止")
        try:
            if self.crawler_window:
                self.crawler_window.hide()
                logger.debug("已隐藏爬虫窗口")
        except Exception:  # pragma: no cover - pywebview runtime
            logger.warning("无法隐藏爬虫窗口", exc_info=True)
        self._emit_progress()
        logger.info("采集已停止")
        return {"success": True, "message": "采集已停止"}

    def on_scroll_complete(self) -> dict[str, Any]:
        logger.info("前端通知：滚动已完成")
        if self.state.active:
            self._complete_crawl("已到达列表尾部")
        return {"success": True}

    def open_login(self) -> dict[str, Any]:
        self._pending_action = None
        try:
            self._load_crawler_url("https://www.douyin.com/")
            return {"success": True, "message": "抖音页面已打开，请在弹窗中登录"}
        except Exception as exc:  # pragma: no cover - pywebview runtime
            logger.exception("打开抖音登录窗口失败")
            return {"success": False, "error": f"打开抖音失败：{exc}"}

    def open_login_window(self) -> dict[str, Any]:
        """创建独立登录窗口，检测登录状态，成功后自动关闭"""
        try:
            import webview
            import threading
            
            logger.info("创建登录窗口")
            
            # 创建登录窗口
            login_window = webview.create_window(
                "抖音登录",
                "https://www.douyin.com/",
                width=800,
                height=600,
            )
            
            def check_login_status():
                """在后台线程中检测登录状态"""
                import time
                max_attempts = 300  # 最多检测5分钟
                attempt = 0
                
                # 等待窗口加载
                time.sleep(2)
                
                while attempt < max_attempts:
                    try:
                        if not hasattr(login_window, 'evaluate_js'):
                            logger.debug("登录窗口未就绪")
                            time.sleep(1)
                            attempt += 1
                            continue
                        
                        # 检测登录状态
                        script = """
                            (function() {
                                try {
                                    const cookies = document.cookie || "";
                                    const hasSession = /sessionid(_ss)?=/.test(cookies);
                                    const loginButton = document.querySelector('[data-e2e="top-login-button"]')
                                        || document.querySelector('button[data-e2e="login-button"]')
                                        || document.querySelector('.login-button');
                                    const avatar = document.querySelector('[class*="avatar"]') 
                                        || document.querySelector('[class*="Avatar"]');
                                    const userInfo = document.querySelector('[class*="user-info"]')
                                        || document.querySelector('[class*="UserInfo"]');
                                    
                                    const isLoggedIn = hasSession || (!loginButton && (avatar || userInfo));
                                    
                                    return {
                                        logged_in: isLoggedIn,
                                        has_session: hasSession,
                                        has_login_button: !!loginButton,
                                        has_avatar: !!avatar,
                                        has_user_info: !!userInfo,
                                        url: window.location.href
                                    };
                                } catch (error) {
                                    return { logged_in: false, error: error.message };
                                }
                            })();
                        """
                        
                        result = login_window.evaluate_js(script)
                        
                        if isinstance(result, str):
                            try:
                                import json
                                result = json.loads(result)
                            except json.JSONDecodeError:
                                result = {}
                        
                        if result and result.get("logged_in"):
                            logger.info("检测到登录成功")
                            # 给用户一点时间看到登录成功的页面
                            time.sleep(1)
                            try:
                                login_window.destroy()
                                logger.info("登录窗口已关闭")
                            except Exception as e:
                                logger.warning(f"关闭登录窗口失败: {e}")
                            
                            # 通知主窗口更新登录状态
                            if self.ui_window:
                                try:
                                    self.ui_window.evaluate_js(
                                        "window.dispatchEvent(new CustomEvent('login-success'));"
                                    )
                                except Exception:
                                    pass
                            
                            return
                        
                    except Exception as e:
                        logger.debug(f"检测登录状态出错: {e}")
                    
                    time.sleep(1)
                    attempt += 1
                
                logger.info("登录检测超时或用户关闭了窗口")
                if self.ui_window:
                    try:
                        self.ui_window.evaluate_js(
                            "window.dispatchEvent(new CustomEvent('login-timeout'));"
                        )
                    except Exception:
                        pass
            
            # 在后台线程中检测登录状态
            thread = threading.Thread(target=check_login_status, daemon=True)
            thread.start()
            
            return {"success": True, "message": "登录窗口已打开，请在弹出窗口中登录"}
            
        except Exception as exc:  # pragma: no cover - pywebview runtime
            logger.exception("创建登录窗口失败")
            return {"success": False, "error": f"创建登录窗口失败：{exc}"}

    # ---------------------------------------------------------------------
    # Utilities
    # ---------------------------------------------------------------------
    def trigger_mock_push(self) -> dict[str, Any]:
        if self.crawler_window:
            try:
                self.crawler_window.evaluate_js("window.__awemeBridge?.mockPush();")
            except Exception:  # pragma: no cover - pywebview runtime
                logger.debug("触发模拟数据推送失败")
        return {"success": True}
