"""
Windows active window capture implementation
Uses Win32 API for window information
"""

from typing import TYPE_CHECKING, Any, Dict, Optional

from core.logger import get_logger
from perception.base import BaseActiveWindowCapture

logger = get_logger(__name__)

# Runtime imports
try:
    import win32gui  # type: ignore
    import win32process  # type: ignore
    import psutil  # type: ignore

    WINDOWS_AVAILABLE = True
except ImportError:
    WINDOWS_AVAILABLE = False
    logger.warning("Windows libraries (pywin32, psutil) not available")
    # Create placeholders for type checking
    if TYPE_CHECKING:
        win32gui = None  # type: ignore
        win32process = None  # type: ignore
        psutil = None  # type: ignore


class WindowsActiveWindowCapture(BaseActiveWindowCapture):
    """Windows active window capturer using Win32 API"""

    def __init__(
        self,
        on_event=None,
        monitor_tracker=None,
    ):
        super().__init__()
        self.on_event = on_event
        self.monitor_tracker = monitor_tracker

        if not WINDOWS_AVAILABLE:
            logger.error("Windows libraries not available")
            raise RuntimeError("Windows libraries (pywin32, psutil) not available")

    def get_active_window_info(self) -> Optional[Dict[str, Any]]:
        """
        Get current active window information

        Returns:
            Dictionary containing window info, or None if unavailable
        """
        try:
            # Get foreground window handle
            hwnd = win32gui.GetForegroundWindow()  # type: ignore
            if hwnd == 0:
                return None

            # Get window title
            window_title = win32gui.GetWindowText(hwnd)  # type: ignore

            # Get window rectangle (left, top, right, bottom)
            try:
                rect = win32gui.GetWindowRect(hwnd)  # type: ignore
                window_bounds = {
                    "x": rect[0],
                    "y": rect[1],
                    "width": rect[2] - rect[0],
                    "height": rect[3] - rect[1],
                }
            except Exception as e:
                logger.warning(f"Failed to get window rect: {e}")
                window_bounds = {"x": 0, "y": 0, "width": 0, "height": 0}

            # Get process information
            try:
                _, process_id = win32process.GetWindowThreadProcessId(hwnd)  # type: ignore
                process = psutil.Process(process_id)  # type: ignore
                app_name = process.name()
                # Remove .exe extension if present
                if app_name.lower().endswith(".exe"):
                    app_name = app_name[:-4]
            except Exception as e:
                logger.warning(f"Failed to get process info: {e}")
                app_name = "Unknown"
                process_id = 0

            return {
                "action": "capture",
                "timestamp": None,  # Will be set by coordinator
                "app_name": app_name,
                "app_bundle_id": None,  # Windows doesn't have bundle IDs
                "app_process_id": int(process_id),
                "window_title": window_title,
                "window_id": int(hwnd),
                "window_bounds": window_bounds,
            }

        except Exception as e:
            logger.error(f"Failed to get active window info on Windows: {e}")
            return None

    def start(self) -> None:
        """Start capturing"""
        if self.is_running:
            return
        self.is_running = True
        logger.debug("Windows active window capture started")

    def stop(self) -> None:
        """Stop capturing"""
        if not self.is_running:
            return
        self.is_running = False
        logger.debug("Windows active window capture stopped")

    def capture(self):
        """Not used - handled by coordinator"""
        return None

    def output(self) -> None:
        """Output/flush processed data"""
        pass

    def get_stats(self) -> Dict[str, Any]:
        """Get capture statistics"""
        return {}
