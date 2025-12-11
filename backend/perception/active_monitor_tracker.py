"""
Active monitor tracker for smart screenshot filtering

Tracks which monitor is currently active based on mouse position,
enabling smart screenshot capture that only captures the active screen.
"""

import time
from datetime import datetime
from typing import Dict, List, Optional

from core.logger import get_logger

logger = get_logger(__name__)


class ActiveMonitorTracker:
    """Tracks the currently active monitor based on mouse activity"""

    def __init__(self, inactive_timeout: float = 30.0):
        """
        Initialize active monitor tracker

        Args:
            inactive_timeout: Seconds of inactivity before considering all monitors active
        """
        self._current_monitor_index: int = 1  # Default to primary monitor
        self._monitors_info: List[Dict] = []
        self._last_activity_time: float = time.time()
        self._inactive_timeout: float = inactive_timeout
        self._last_mouse_position: Optional[tuple[int, int]] = None

    def update_monitors_info(self, monitors: List[Dict]) -> None:
        """
        Update the list of available monitors

        Args:
            monitors: List of monitor info dicts with 'index', 'left', 'top', 'width', 'height'
        """
        self._monitors_info = monitors
        logger.debug(f"Updated monitors info: {len(monitors)} monitors")

    def update_from_mouse(self, x: int, y: int) -> None:
        """
        Update active monitor based on mouse position

        Args:
            x: Mouse X coordinate (absolute)
            y: Mouse Y coordinate (absolute)
        """
        if not self._monitors_info:
            logger.warning("No monitor info available, cannot update active monitor")
            return

        # Find which monitor contains this coordinate
        new_monitor_index = self._get_monitor_from_position(x, y)

        if new_monitor_index != self._current_monitor_index:
            logger.debug(
                f"Active monitor changed: {self._current_monitor_index} -> {new_monitor_index} "
                f"(mouse at {x}, {y})"
            )
            self._current_monitor_index = new_monitor_index

        self._last_activity_time = time.time()
        self._last_mouse_position = (x, y)

    def _get_monitor_from_position(self, x: int, y: int) -> int:
        """
        Determine which monitor contains the given coordinates

        Args:
            x: Absolute X coordinate
            y: Absolute Y coordinate

        Returns:
            Monitor index (1-based), defaults to primary (1) if not found
        """
        for monitor in self._monitors_info:
            left = monitor.get("left", 0)
            top = monitor.get("top", 0)
            width = monitor.get("width", 0)
            height = monitor.get("height", 0)

            # Check if point is within monitor bounds
            if (left <= x < left + width) and (top <= y < top + height):
                return monitor.get("index", 1)

        # Fallback: return primary monitor
        logger.debug(
            f"Position ({x}, {y}) not found in any monitor bounds, "
            f"using primary monitor"
        )
        return self._get_primary_monitor_index()

    def _get_primary_monitor_index(self) -> int:
        """Get the primary monitor index (marked as is_primary or first monitor)"""
        for monitor in self._monitors_info:
            if monitor.get("is_primary", False):
                return monitor.get("index", 1)
        return 1  # Default to first monitor

    def get_active_monitor_index(self) -> int:
        """
        Get the currently active monitor index

        Returns:
            Monitor index (1-based)
        """
        return self._current_monitor_index

    def should_capture_all_monitors(self) -> bool:
        """
        Check if we should capture all monitors (due to inactivity timeout)

        Returns:
            True if inactive for too long, False otherwise
        """
        inactive_duration = time.time() - self._last_activity_time
        return inactive_duration >= self._inactive_timeout

    def get_stats(self) -> Dict:
        """Get tracker statistics for debugging"""
        inactive_duration = time.time() - self._last_activity_time
        return {
            "current_monitor_index": self._current_monitor_index,
            "monitors_count": len(self._monitors_info),
            "last_mouse_position": self._last_mouse_position,
            "inactive_duration_seconds": round(inactive_duration, 2),
            "should_capture_all": self.should_capture_all_monitors(),
            "inactive_timeout": self._inactive_timeout,
        }
