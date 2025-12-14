"""
Active window capture coordinator
Provides active window information for enriching screenshot records
"""

from typing import Any, Dict, List, Optional

import mss
from core.logger import get_logger

from .base import BaseActiveWindowCapture

logger = get_logger(__name__)


class ActiveWindowCapture(BaseActiveWindowCapture):
    """Active window capturer coordinator - provides context for screenshots"""

    def __init__(
        self,
        on_event=None,  # Not used, kept for API compatibility
        monitor_tracker: Optional[Any] = None,
    ):
        super().__init__()
        self.monitor_tracker = monitor_tracker
        self._platform_impl: Optional[BaseActiveWindowCapture] = None

    def set_platform_impl(self, impl: BaseActiveWindowCapture) -> None:
        """Set platform-specific implementation"""
        self._platform_impl = impl

    def get_active_window_info(self) -> Optional[Dict[str, Any]]:
        """
        Get current active window information from platform implementation

        This is called by screenshot capture to enrich screenshot records.
        """
        if self._platform_impl is None:
            logger.warning("Platform implementation not set")
            return None

        window_info = self._platform_impl.get_active_window_info()
        if window_info and window_info.get("window_bounds"):
            # Enrich with monitor-relative coordinates
            self._enrich_with_monitor_info(window_info)

        return window_info

    def capture(self):
        """Not used - window info is retrieved via get_active_window_info()"""
        return None

    def _enrich_with_monitor_info(self, window_info: Dict[str, Any]) -> None:
        """
        Enrich window info with monitor-relative coordinates

        Modifies window_info in place to add:
        - monitor_index: Which monitor the window is on
        - monitor_relative_bounds: Coordinates relative to monitor
        - monitor_info: Monitor dimensions and position
        """
        try:
            window_bounds = window_info.get("window_bounds")
            if window_bounds is None:
                return

            # Get monitor information
            with mss.mss() as sct:
                monitors = sct.monitors[1:]  # Skip the "all monitors" entry

                if not monitors:
                    return

                # Find which monitor contains the window
                monitor, monitor_index = self._find_window_monitor(
                    window_bounds, monitors
                )

                if monitor is None:
                    return

                # Calculate monitor-relative coordinates
                monitor_relative_bounds = {
                    "x": window_bounds["x"] - monitor["left"],
                    "y": window_bounds["y"] - monitor["top"],
                    "width": window_bounds["width"],
                    "height": window_bounds["height"],
                }

                # Add to window info
                window_info["monitor_index"] = monitor_index
                window_info["monitor_relative_bounds"] = monitor_relative_bounds
                window_info["monitor_info"] = {
                    "left": monitor["left"],
                    "top": monitor["top"],
                    "width": monitor["width"],
                    "height": monitor["height"],
                }

        except Exception as e:
            logger.error(f"Failed to enrich with monitor info: {e}")

    def _find_window_monitor(
        self, window_bounds: Dict[str, Any], monitors: List[Dict[str, Any]]
    ) -> tuple[Optional[Dict[str, Any]], int]:
        """
        Find which monitor contains the majority of the window

        Returns:
            Tuple of (monitor dict, 1-based monitor index) or (None, 0) if not found
        """
        max_overlap_area = 0
        best_monitor = None
        best_index = 0

        for i, monitor in enumerate(monitors):
            overlap_area = self._calculate_overlap_area(window_bounds, monitor)
            if overlap_area > max_overlap_area:
                max_overlap_area = overlap_area
                best_monitor = monitor
                best_index = i + 1  # 1-based index

        return best_monitor, best_index

    def _calculate_overlap_area(
        self, window_bounds: Dict[str, Any], monitor: Dict[str, Any]
    ) -> int:
        """Calculate overlap area between window and monitor"""
        # Window rectangle
        w_left = window_bounds["x"]
        w_top = window_bounds["y"]
        w_right = w_left + window_bounds["width"]
        w_bottom = w_top + window_bounds["height"]

        # Monitor rectangle
        m_left = monitor["left"]
        m_top = monitor["top"]
        m_right = m_left + monitor["width"]
        m_bottom = m_top + monitor["height"]

        # Calculate intersection
        overlap_left = max(w_left, m_left)
        overlap_top = max(w_top, m_top)
        overlap_right = min(w_right, m_right)
        overlap_bottom = min(w_bottom, m_bottom)

        # Check if there's overlap
        if overlap_left < overlap_right and overlap_top < overlap_bottom:
            return (overlap_right - overlap_left) * (overlap_bottom - overlap_top)

        return 0

    def start(self) -> None:
        """Start capturing"""
        if self.is_running:
            return
        self.is_running = True
        if self._platform_impl:
            self._platform_impl.start()
        logger.debug("Active window capture started")

    def stop(self) -> None:
        """Stop capturing"""
        if not self.is_running:
            return
        self.is_running = False
        if self._platform_impl:
            self._platform_impl.stop()
        logger.debug("Active window capture stopped")

    def output(self) -> None:
        """Output/flush processed data"""
        pass

    def get_stats(self) -> Dict[str, Any]:
        """Get capture statistics"""
        return {}
