"""
Perception layer platform factory
Automatically creates corresponding keyboard and mouse monitors based on running platform

Design Pattern: Factory Pattern
- Callers only need to know the interface, without caring about specific implementation
- Automatically selects appropriate implementation based on platform
- Convenient for future expansion and maintenance
"""

import sys
from typing import Optional, Callable
from core.logger import get_logger
from core.models import RawRecord

from .base import BaseKeyboardMonitor, BaseMouseMonitor
from .platforms import (
    MacOSKeyboardMonitor,
    MacOSMouseMonitor,
    WindowsKeyboardMonitor,
    WindowsMouseMonitor,
    LinuxKeyboardMonitor,
    LinuxMouseMonitor,
)

logger = get_logger(__name__)


class MonitorFactory:
    """Monitor factory class"""

    @staticmethod
    def get_platform() -> str:
        """Get current platform identifier

        Returns:
            str: 'darwin' (macOS), 'win32' (Windows), 'linux' (Linux)
        """
        return sys.platform

    @staticmethod
    def create_keyboard_monitor(
        on_event: Optional[Callable[[RawRecord], None]] = None,
    ) -> BaseKeyboardMonitor:
        """Create keyboard monitor

        Automatically selects appropriate implementation based on current platform:
        - macOS: PyObjC NSEvent (avoids pynput TSM crashes)
        - Windows: pynput (extendable to Windows API)
        - Linux: pynput (extendable to X11/evdev)

        Args:
            on_event: Event callback function

        Returns:
            BaseKeyboardMonitor: Keyboard monitor instance
        """
        platform = MonitorFactory.get_platform()

        if platform == "darwin":
            logger.info("Creating macOS keyboard monitor (PyObjC NSEvent)")
            return MacOSKeyboardMonitor(on_event)

        elif platform == "win32":
            logger.info("Creating Windows keyboard monitor (pynput)")
            return WindowsKeyboardMonitor(on_event)

        elif platform.startswith("linux"):
            logger.info("Creating Linux keyboard monitor (pynput)")
            return LinuxKeyboardMonitor(on_event)

        else:
            logger.warning(
                f"Unknown platform: {platform}, using Linux implementation as default"
            )
            return LinuxKeyboardMonitor(on_event)

    @staticmethod
    def create_mouse_monitor(
        on_event: Optional[Callable[[RawRecord], None]] = None,
    ) -> BaseMouseMonitor:
        """Create mouse monitor

        Automatically select appropriate implementation based on current platform:
        - macOS: pynput (mouse listening is safe on macOS)
        - Windows: pynput (extendable to Windows API)
        - Linux: pynput (extendable to X11/evdev)

        Args:
            on_event: Event callback function

        Returns:
            BaseMouseMonitor: Mouse monitor instance
        """
        platform = MonitorFactory.get_platform()

        if platform == "darwin":
            logger.info("Creating macOS mouse monitor (pynput)")
            return MacOSMouseMonitor(on_event)

        elif platform == "win32":
            logger.info("Creating Windows mouse monitor (pynput)")
            return WindowsMouseMonitor(on_event)

        elif platform.startswith("linux"):
            logger.info("Creating Linux mouse monitor (pynput)")
            return LinuxMouseMonitor(on_event)

        else:
            logger.warning(
                f"Unknown platform: {platform}, using Linux implementation as default"
            )
            return LinuxMouseMonitor(on_event)


# Convenience functions
def create_keyboard_monitor(
    on_event: Optional[Callable[[RawRecord], None]] = None,
) -> BaseKeyboardMonitor:
    """Create keyboard monitor (convenience function)"""
    return MonitorFactory.create_keyboard_monitor(on_event)


def create_mouse_monitor(
    on_event: Optional[Callable[[RawRecord], None]] = None,
) -> BaseMouseMonitor:
    """Create mouse monitor (convenience function)"""
    return MonitorFactory.create_mouse_monitor(on_event)
