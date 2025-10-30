from __future__ import annotations

import atexit
import logging
import os
import signal
import threading
import uuid
from collections.abc import Callable, Iterable
from contextlib import contextmanager
from pathlib import Path
from types import FrameType
from typing import IO, Any, Optional

logger = logging.getLogger(__name__)

_DEFAULT_LOCK_FILENAME = ".mdc.lock"
_ENV_LOCK_PATH = "MARKET_DATA_RUNTIME_LOCK_PATH"
_ENV_AUTO_START = "MARKET_DATA_RUNTIME_AUTO_START"


def _resolve_bool(value: Optional[str], default: bool) -> bool:
    if value is None:
        return default
    lowered = value.strip().lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    return default


def _resolve_lock_path(candidate: str | Path | None) -> Path:
    env_override = os.getenv(_ENV_LOCK_PATH)
    path_value: Path | None = None

    if candidate is not None:
        path_value = Path(candidate)
    elif env_override:
        path_value = Path(env_override)

    if path_value is None:
        path_value = Path.cwd() / _DEFAULT_LOCK_FILENAME

    if not path_value.is_absolute():
        path_value = Path.cwd() / path_value

    return path_value.resolve()


_HANDLED_SIGNALS: tuple[int, ...] = tuple(
    getattr(signal, name)
    for name in ("SIGINT", "SIGTERM", "SIGQUIT", "SIGBREAK")
    if hasattr(signal, name)
)


class Runtime:
    """Manage lifecycle for the market data collector runtime."""

    def __init__(
        self,
        lock_path: str | Path | None = None,
        auto_start: bool | None = None,
        handled_signals: Iterable[int] | None = None,
    ) -> None:
        self.lock_path = _resolve_lock_path(lock_path)
        auto_start_env = os.getenv(_ENV_AUTO_START)
        if auto_start is None:
            self.auto_start = _resolve_bool(auto_start_env, True)
        else:
            self.auto_start = auto_start

        self._handled_signals: tuple[int, ...] = (
            tuple(handled_signals) if handled_signals is not None else _HANDLED_SIGNALS
        )
        self._lock_file: IO[str] | None = None
        self._lock_length: int = 1
        self._lock_acquired = False
        self._running = False
        self._shutdown_reason: str | None = None

        self._mutex = threading.RLock()
        self._stop_event = threading.Event()
        self._active_readers: dict[str, str | None] = {}
        self._collectors: dict[
            str,
            tuple[Callable[[], Any] | None, Callable[[], Any] | None],
        ] = {}
        self._collectors_started = False

        self._tasks: set[Any] = set()
        self._cleanup_callbacks: set[Callable[[], Any]] = set()
        self._previous_signal_handlers: dict[int, Any] = {}
        self._atexit_registered = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def start(self) -> None:
        """Start the runtime if it is not already running."""

        with self._mutex:
            if self._running:
                logger.debug("Runtime already running; start() call ignored")
                return

            self._acquire_process_lock()
            self._stop_event.clear()
            self._install_signal_handlers()
            self._register_atexit()

            self._running = True
            self._shutdown_reason = None

            logger.info(
                "Market data runtime started (pid=%s, lock=%s)",
                os.getpid(),
                self.lock_path,
            )

            if self._active_readers:
                self._start_collectors()

    def ensure_started(self) -> None:
        """Alias for :meth:`start` to emphasise idempotency."""

        self.start()

    def stop(self, reason: str | None = None) -> None:
        """Stop the runtime and release all managed resources."""

        with self._mutex:
            if not self._running and not self._lock_acquired:
                logger.debug("Runtime not running; stop() call ignored")
                return

            if reason:
                self._shutdown_reason = reason

            self._stop_event.set()
            self._stop_collectors()
            self._cancel_registered_tasks()
            self._run_cleanup_callbacks()
            self._restore_signal_handlers()
            self._release_process_lock()

            self._running = False
            self._collectors_started = False
            self._active_readers.clear()

            logger.info(
                "Market data runtime stopped (reason=%s)",
                self._shutdown_reason,
            )

    def register_collector(
        self,
        name: str,
        start: Callable[[], Any] | None = None,
        stop: Callable[[], Any] | None = None,
    ) -> None:
        """Register a collector lifecycle callbacks.

        The ``start`` callback is executed when collectors are activated, and ``stop``
        is executed when collectors are stopped or unregistered.
        """

        with self._mutex:
            self._collectors[name] = (start, stop)
            logger.debug("Collector registered: %s", name)

            if self._collectors_started and start is not None:
                self._invoke_callback(start, f"start collector '{name}'")
            elif self._active_readers and not self._collectors_started:
                self._start_collectors()

    def unregister_collector(self, name: str) -> None:
        """Remove a collector and invoke its stop callback if required."""

        with self._mutex:
            callbacks = self._collectors.pop(name, None)
            if callbacks is None:
                return

            _, stop_cb = callbacks
            if self._collectors_started and stop_cb is not None:
                self._invoke_callback(stop_cb, f"stop collector '{name}'")

            logger.debug("Collector unregistered: %s", name)

    def register_task(self, task: Any) -> None:
        """Track an asynchronous task so it can be cancelled on shutdown."""

        with self._mutex:
            self._tasks.add(task)

    def unregister_task(self, task: Any) -> None:
        with self._mutex:
            self._tasks.discard(task)

    def register_cleanup(self, callback: Callable[[], Any]) -> None:
        """Register an additional callback to invoke during shutdown."""

        with self._mutex:
            self._cleanup_callbacks.add(callback)

    def unregister_cleanup(self, callback: Callable[[], Any]) -> None:
        with self._mutex:
            self._cleanup_callbacks.discard(callback)

    def acquire_reader(self, name: str | None = None) -> str:
        """Register an active reader and start collectors if necessary."""

        with self._mutex:
            if not self._running:
                self.start()

            token = uuid.uuid4().hex
            self._active_readers[token] = name

            logger.debug(
                "Reader acquired: token=%s name=%s active=%d",
                token,
                name,
                len(self._active_readers),
            )

            if not self._collectors_started:
                self._start_collectors()

            return token

    def release_reader(self, token: str) -> None:
        """Release a reader previously acquired with :meth:`acquire_reader`."""

        with self._mutex:
            if token not in self._active_readers:
                logger.debug("Attempted to release unknown reader token: %s", token)
                return

            name = self._active_readers.pop(token)
            logger.debug(
                "Reader released: token=%s name=%s remaining=%d",
                token,
                name,
                len(self._active_readers),
            )

            if not self._active_readers:
                self._stop_collectors()

    # ------------------------------------------------------------------
    # Introspection helpers
    # ------------------------------------------------------------------
    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def active_readers(self) -> int:
        return len(self._active_readers)

    @property
    def stop_event(self) -> threading.Event:
        return self._stop_event

    def snapshot(self) -> dict[str, Any]:
        """Return a snapshot of runtime state for debugging/tests."""

        with self._mutex:
            return {
                "is_running": self._running,
                "lock_path": str(self.lock_path),
                "active_readers": len(self._active_readers),
                "collectors_started": self._collectors_started,
                "pid": os.getpid(),
                "shutdown_reason": self._shutdown_reason,
            }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _register_atexit(self) -> None:
        if self._atexit_registered:
            return

        atexit.register(self._atexit_shutdown)
        self._atexit_registered = True

    def _atexit_shutdown(self) -> None:
        try:
            self.stop(reason="atexit")
        except Exception:  # pragma: no cover - defensive logging
            logger.exception("Exception during atexit runtime shutdown")

    def _start_collectors(self) -> None:
        if self._collectors_started:
            return

        if self._collectors:
            logger.debug("Starting collectors (%d registered)", len(self._collectors))

        for name, (start_cb, _) in self._collectors.items():
            if start_cb is None:
                continue
            self._invoke_callback(start_cb, f"start collector '{name}'")

        self._collectors_started = True

    def _stop_collectors(self) -> None:
        if not self._collectors_started:
            return

        if self._collectors:
            logger.debug("Stopping collectors (%d registered)", len(self._collectors))

        for name, (_, stop_cb) in list(self._collectors.items())[::-1]:
            if stop_cb is None:
                continue
            self._invoke_callback(stop_cb, f"stop collector '{name}'")

        self._collectors_started = False

    def _cancel_registered_tasks(self) -> None:
        if not self._tasks:
            return

        for task in list(self._tasks):
            try:
                if hasattr(task, "cancel") and callable(task.cancel):
                    task.cancel()
                elif hasattr(task, "stop") and callable(task.stop):
                    task.stop()
                elif callable(task):
                    task()
            except Exception:  # pragma: no cover - defensive logging
                logger.exception("Failed to cancel registered task: %r", task)
            finally:
                self._tasks.discard(task)

    def _run_cleanup_callbacks(self) -> None:
        if not self._cleanup_callbacks:
            return

        for callback in list(self._cleanup_callbacks):
            self._invoke_callback(callback, "runtime cleanup")
            self._cleanup_callbacks.discard(callback)

    def _invoke_callback(self, callback: Callable[[], Any], description: str) -> None:
        try:
            callback()
        except Exception:  # pragma: no cover - defensive logging
            logger.exception("Failed to %s", description)

    def _install_signal_handlers(self) -> None:
        self._previous_signal_handlers.clear()

        for signum in self._handled_signals:
            try:
                previous = signal.getsignal(signum)
                if previous == self._handle_signal:
                    continue
                signal.signal(signum, self._handle_signal)
                self._previous_signal_handlers[signum] = previous
            except ValueError:  # pragma: no cover - signal registration failure
                logger.debug(
                    "Unable to register signal handler for %s", signum, exc_info=True
                )

    def _restore_signal_handlers(self) -> None:
        if not self._previous_signal_handlers:
            return

        for signum, handler in self._previous_signal_handlers.items():
            try:
                signal.signal(signum, handler)
            except ValueError:  # pragma: no cover - non-main thread
                logger.debug(
                    "Unable to restore signal handler for %s", signum, exc_info=True
                )
        self._previous_signal_handlers.clear()

    def _handle_signal(self, signum: int, frame: FrameType | None) -> None:
        signame = self._signal_name(signum)
        logger.info("Received signal %s; initiating runtime shutdown", signame)

        previous = self._previous_signal_handlers.get(signum)
        try:
            self.stop(reason=f"signal:{signame}")
        finally:
            if callable(previous):
                previous(signum, frame)
            elif previous is signal.SIG_DFL:
                try:
                    signal.signal(signum, signal.SIG_DFL)
                    os.kill(os.getpid(), signum)
                except Exception:  # pragma: no cover - defensive logging
                    logger.debug("Failed to re-emit default signal", exc_info=True)

    def _signal_name(self, signum: int) -> str:
        try:
            return signal.Signals(signum).name
        except ValueError:  # pragma: no cover - unknown signal
            return str(signum)

    def _acquire_process_lock(self) -> None:
        if self._lock_acquired:
            return

        self.lock_path.parent.mkdir(parents=True, exist_ok=True)

        lock_file = self.lock_path.open("a+")
        lock_file.seek(0)
        lock_file.truncate()
        lock_file.write(str(os.getpid()))
        lock_file.flush()

        try:
            self._lock_length = max(lock_file.tell(), 1)
            self._lock_file_exclusive(lock_file)
        except Exception:
            lock_file.close()
            raise

        self._lock_file = lock_file
        self._lock_acquired = True

    def _release_process_lock(self) -> None:
        if not self._lock_acquired or self._lock_file is None:
            return

        try:
            self._unlock_file(self._lock_file)
        finally:
            try:
                self._lock_file.close()
            finally:
                self._lock_file = None
                self._lock_acquired = False

        try:
            self.lock_path.unlink()
        except FileNotFoundError:
            pass
        except OSError:  # pragma: no cover - best effort cleanup
            logger.debug("Unable to remove lock file %s", self.lock_path, exc_info=True)

    def _lock_file_exclusive(self, handle: IO[str]) -> None:
        try:
            if os.name == "posix":
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            else:
                import msvcrt  # type: ignore

                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, self._lock_length)
        except (BlockingIOError, OSError) as exc:
            raise RuntimeError(
                f"Market data runtime already active (lock file: {self.lock_path})"
            ) from exc

    def _unlock_file(self, handle: IO[str]) -> None:
        try:
            if os.name == "posix":
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            else:
                import msvcrt  # type: ignore

                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, self._lock_length)
        except OSError:  # pragma: no cover - best effort
            logger.debug("Failed to unlock file %s", self.lock_path, exc_info=True)


# ----------------------------------------------------------------------
# Module-level singleton helpers
# ----------------------------------------------------------------------
try:
    _RUNTIME_SINGLETON
except NameError:  # pragma: no cover - first import
    _RUNTIME_SINGLETON: Runtime | None = None

try:
    _RUNTIME_LOCK
except NameError:  # pragma: no cover - first import
    _RUNTIME_LOCK = threading.Lock()


def get_runtime(auto_start: bool | None = None) -> Runtime:
    """Return the process-wide runtime singleton."""

    global _RUNTIME_SINGLETON

    with _RUNTIME_LOCK:
        if _RUNTIME_SINGLETON is None:
            _RUNTIME_SINGLETON = Runtime(auto_start=auto_start)
        elif auto_start is not None:
            _RUNTIME_SINGLETON.auto_start = auto_start

        return _RUNTIME_SINGLETON


runtime = get_runtime()

if runtime.auto_start:
    runtime.start()


def start() -> None:
    """Convenience alias for :func:`Runtime.start`."""

    runtime.start()


def stop(reason: str | None = None) -> None:
    runtime.stop(reason)


def acquire_reader(name: str | None = None) -> str:
    return runtime.acquire_reader(name)


def release_reader(token: str) -> None:
    runtime.release_reader(token)


@contextmanager
def reader_session(name: str | None = None):
    """Context manager wrapping :meth:`Runtime.acquire_reader`/``release``."""

    token = runtime.acquire_reader(name)
    try:
        yield runtime
    finally:
        runtime.release_reader(token)


__all__ = [
    "Runtime",
    "runtime",
    "get_runtime",
    "start",
    "stop",
    "acquire_reader",
    "release_reader",
    "reader_session",
]
