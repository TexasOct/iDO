"""
Screen state monitor factory
Creates platform-appropriate screen state monitor instances
"""

import platform
from typing import Callable, Optional

from core.logger import get_logger
from perception.base import BaseEventListener

logger = get_logger(__name__)


def create_screen_state_monitor(
    on_screen_lock: Optional[Callable[[], None]] = None,
    on_screen_unlock: Optional[Callable[[], None]] = None,
) -> BaseEventListener:
    """
    Create screen state monitor suitable for current platform

    Args:
        on_screen_lock: Screen lock/sleep callback
        on_screen_unlock: Screen unlock/wake callback

    Returns:
        Screen state monitor instance
    """
    system = platform.system()

    if system == "Darwin":
        from perception.platforms.macos import MacOSScreenStateMonitor

        return MacOSScreenStateMonitor(on_screen_lock, on_screen_unlock)
    elif system == "Windows":
        from perception.platforms.windows import WindowsScreenStateMonitor

        return WindowsScreenStateMonitor(on_screen_lock, on_screen_unlock)
    elif system == "Linux":
        from perception.platforms.linux import LinuxScreenStateMonitor

        return LinuxScreenStateMonitor(on_screen_lock, on_screen_unlock)
    else:
        logger.warning(
            f"Unsupported platform: {system}, screen state monitor unavailable"
        )
        # Return a no-op event listener
        class NoOpScreenStateMonitor(BaseEventListener):
            """No-op screen state monitor for unsupported platforms"""
            def start(self):
                """No-op start"""
                self.is_running = True

            def stop(self):
                """No-op stop"""
                self.is_running = False

        return NoOpScreenStateMonitor()
