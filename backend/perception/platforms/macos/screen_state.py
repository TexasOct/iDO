"""
macOS screen state monitor implementation
"""

from importlib import import_module
from typing import Callable, Optional

from core.logger import get_logger
from perception.base import BaseEventListener

logger = get_logger(__name__)


class MacOSScreenStateMonitor(BaseEventListener):
    """macOS screen state monitor"""

    def __init__(
        self,
        on_screen_lock: Optional[Callable[[], None]] = None,
        on_screen_unlock: Optional[Callable[[], None]] = None,
    ):
        """
        Initialize macOS screen state monitor

        Args:
            on_screen_lock: Screen lock/sleep callback
            on_screen_unlock: Screen unlock/wake callback
        """
        super().__init__()
        self.on_screen_lock = on_screen_lock
        self.on_screen_unlock = on_screen_unlock

    def start(self) -> None:
        """Start listening"""
        if self.is_running:
            return

        try:
            appkit = import_module("AppKit")
            NSWorkspace = getattr(appkit, "NSWorkspace")

            self.is_running = True

            # Get notification center
            nc = NSWorkspace.sharedWorkspace().notificationCenter()

            # Monitor screen lock
            nc.addObserver_selector_name_object_(
                self, "screenDidLock:", "NSWorkspaceScreensDidSleepNotification", None
            )

            # Monitor screen wake
            nc.addObserver_selector_name_object_(
                self, "screenDidUnlock:", "NSWorkspaceScreensDidWakeNotification", None
            )

            # Monitor system sleep
            nc.addObserver_selector_name_object_(
                self, "screenDidLock:", "NSWorkspaceWillSleepNotification", None
            )

            # Monitor system wake
            nc.addObserver_selector_name_object_(
                self, "screenDidUnlock:", "NSWorkspaceDidWakeNotification", None
            )

            logger.info("macOS screen state monitor started")

        except Exception as e:
            logger.error(f"Failed to start macOS screen state monitor: {e}")
            self.is_running = False

    def screenDidLock_(self, notification) -> None:
        """Screen lock/sleep callback"""
        logger.info("Screen lock/system sleep detected")
        if self.on_screen_lock:
            try:
                self.on_screen_lock()
            except Exception as e:
                logger.error(f"Failed to execute screen lock callback: {e}")

    def screenDidUnlock_(self, notification) -> None:
        """Screen unlock/wake callback"""
        logger.info("Screen unlock/system wake detected")
        if self.on_screen_unlock:
            try:
                self.on_screen_unlock()
            except Exception as e:
                logger.error(f"Failed to execute screen unlock callback: {e}")

    def stop(self) -> None:
        """Stop listening"""
        if not self.is_running:
            return

        try:
            appkit = import_module("AppKit")
            NSWorkspace = getattr(appkit, "NSWorkspace")
            self.is_running = False

            # Remove all observers
            nc = NSWorkspace.sharedWorkspace().notificationCenter()
            nc.removeObserver_(self)

            logger.info("macOS screen state monitor stopped")

        except Exception as e:
            logger.error(f"Failed to stop macOS screen state monitor: {e}")
