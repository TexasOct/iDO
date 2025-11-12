"""
Windows screen state monitor implementation
"""

import threading
from typing import Callable, Optional

from core.logger import get_logger
from perception.base import BaseEventListener

logger = get_logger(__name__)


class WindowsScreenStateMonitor(BaseEventListener):
    """Windows screen state monitor"""

    def __init__(
        self,
        on_screen_lock: Optional[Callable[[], None]] = None,
        on_screen_unlock: Optional[Callable[[], None]] = None,
    ):
        """
        Initialize Windows screen state monitor

        Args:
            on_screen_lock: Screen lock/sleep callback
            on_screen_unlock: Screen unlock/wake callback
        """
        super().__init__()
        self.on_screen_lock = on_screen_lock
        self.on_screen_unlock = on_screen_unlock
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start listening"""
        if self.is_running:
            return

        try:
            # Check if required modules are available
            import win32api  # type: ignore  # noqa: F401
            import win32con  # type: ignore  # noqa: F401
            import win32gui  # type: ignore  # noqa: F401

            self.is_running = True

            # Monitor Windows messages in background thread
            self._thread = threading.Thread(target=self._message_loop, daemon=True)
            self._thread.start()

            logger.info("Windows screen state monitor started")

        except ImportError:
            logger.error("Cannot import pywin32, screen state monitor unavailable")
            self.is_running = False

        except Exception as e:
            logger.error(f"Failed to start Windows screen state monitor: {e}")
            self.is_running = False

    def _message_loop(self) -> None:
        """Windows message loop"""
        try:
            import win32api  # type: ignore
            import win32con  # type: ignore
            import win32gui  # type: ignore

            # Create hidden window to receive messages
            wc = win32gui.WNDCLASS()
            wc.lpfnWndProc = self._wnd_proc
            wc.lpszClassName = "iDOScreenStateMonitor"
            wc.hInstance = win32api.GetModuleHandle(None)

            class_atom = win32gui.RegisterClass(wc)
            hwnd = win32gui.CreateWindow(
                class_atom,
                "iDO Screen State Monitor",
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                wc.hInstance,
                None,
            )

            # Message loop
            while self.is_running:
                win32gui.PumpWaitingMessages()
                threading.Event().wait(0.1)

            win32gui.DestroyWindow(hwnd)
            win32gui.UnregisterClass(class_atom, wc.hInstance)

        except Exception as e:
            logger.error(f"Windows message loop exception: {e}")

    def _wnd_proc(self, hwnd, msg, wparam, lparam):
        """Windows window message handling"""
        import win32con  # type: ignore

        if msg == win32con.WM_POWERBROADCAST:
            if wparam == win32con.PBT_APMSUSPEND:
                # System suspend
                logger.info("System suspend detected")
                if self.on_screen_lock:
                    self.on_screen_lock()
            elif wparam == win32con.PBT_APMRESUMEAUTOMATIC:
                # System resume
                logger.info("System resume detected")
                if self.on_screen_unlock:
                    self.on_screen_unlock()

        return 0

    def stop(self) -> None:
        """Stop listening"""
        if not self.is_running:
            return

        self.is_running = False

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

        logger.info("Windows screen state monitor stopped")
