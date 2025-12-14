"""
macOS active window capture implementation
Uses NSWorkspace for application info and Quartz for window geometry
"""

from typing import TYPE_CHECKING, Any, Dict, Optional

from core.logger import get_logger
from perception.base import BaseActiveWindowCapture

logger = get_logger(__name__)

# Runtime imports
try:
    from AppKit import NSWorkspace  # type: ignore
    from Quartz import (  # type: ignore[import-untyped]
        CGWindowListCopyWindowInfo,  # type: ignore[attr-defined]
        kCGNullWindowID,  # type: ignore[attr-defined]
        kCGWindowListOptionOnScreenOnly,  # type: ignore[attr-defined]
    )

    MACOS_AVAILABLE = True
except ImportError:
    MACOS_AVAILABLE = False
    logger.warning("macOS frameworks not available")
    # Create placeholders for type checking
    if TYPE_CHECKING:
        NSWorkspace = None  # type: ignore
        CGWindowListCopyWindowInfo = None  # type: ignore
        kCGNullWindowID = None  # type: ignore
        kCGWindowListOptionOnScreenOnly = None  # type: ignore


class MacOSActiveWindowCapture(BaseActiveWindowCapture):
    """macOS active window capturer using NSWorkspace and Quartz"""

    def __init__(
        self,
        on_event=None,
        monitor_tracker=None,
    ):
        super().__init__()
        self.on_event = on_event
        self.monitor_tracker = monitor_tracker

        if not MACOS_AVAILABLE:
            logger.error("macOS frameworks not available")
            raise RuntimeError("macOS frameworks not available")

        self.workspace = NSWorkspace.sharedWorkspace()  # type: ignore

    def get_active_window_info(self) -> Optional[Dict[str, Any]]:
        """
        Get current active window information

        Returns:
            Dictionary containing window info, or None if unavailable
        """
        try:
            # Get frontmost application
            frontmost_app = self.workspace.frontmostApplication()
            if frontmost_app is None:
                return None

            app_name = frontmost_app.localizedName()
            bundle_id = frontmost_app.bundleIdentifier()
            process_id = frontmost_app.processIdentifier()

            # Get window information using Quartz
            window_list = CGWindowListCopyWindowInfo(  # type: ignore
                kCGWindowListOptionOnScreenOnly, kCGNullWindowID  # type: ignore
            )

            if window_list is None:
                return None

            # Find the frontmost window for this application
            window_info = None
            for window in window_list:
                # Check if this window belongs to the frontmost app
                if window.get("kCGWindowOwnerPID") == process_id:
                    # Check if it's a normal window (layer 0)
                    if window.get("kCGWindowLayer", -1) == 0:
                        window_info = window
                        break

            if window_info is None:
                # No window found, but we have app info
                # This can happen with menu bar apps or apps without windows
                return {
                    "action": "capture",
                    "timestamp": None,  # Will be set by coordinator
                    "app_name": str(app_name) if app_name else "Unknown",
                    "app_bundle_id": str(bundle_id) if bundle_id else None,
                    "app_process_id": int(process_id),
                    "window_title": "",
                    "window_id": None,
                    "window_bounds": None,
                }

            # Extract window information
            window_title = window_info.get("kCGWindowName", "")
            window_id = window_info.get("kCGWindowNumber", 0)

            # Extract window bounds
            bounds = window_info.get("kCGWindowBounds", {})
            window_bounds = {
                "x": int(bounds.get("X", 0)),
                "y": int(bounds.get("Y", 0)),
                "width": int(bounds.get("Width", 0)),
                "height": int(bounds.get("Height", 0)),
            }

            return {
                "action": "capture",
                "timestamp": None,  # Will be set by coordinator
                "app_name": str(app_name) if app_name else "Unknown",
                "app_bundle_id": str(bundle_id) if bundle_id else None,
                "app_process_id": int(process_id),
                "window_title": str(window_title) if window_title else "",
                "window_id": int(window_id),
                "window_bounds": window_bounds,
            }

        except Exception as e:
            logger.error(f"Failed to get active window info on macOS: {e}")
            return None

    def start(self) -> None:
        """Start capturing"""
        if self.is_running:
            return
        self.is_running = True
        logger.debug("macOS active window capture started")

    def stop(self) -> None:
        """Stop capturing"""
        if not self.is_running:
            return
        self.is_running = False
        logger.debug("macOS active window capture stopped")

    def capture(self):
        """Not used - handled by coordinator"""
        return None

    def output(self) -> None:
        """Output/flush processed data"""
        pass

    def get_stats(self) -> Dict[str, Any]:
        """Get capture statistics"""
        return {}
