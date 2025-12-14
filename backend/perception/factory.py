"""
Perception layer platform factory
Automatically creates corresponding keyboard and mouse monitors based on running platform

Design Pattern: Factory Pattern
- Callers only need to know the interface, without caring about specific implementation
- Automatically selects appropriate implementation based on platform
- Convenient for future expansion and maintenance
"""

import sys
from typing import Optional, Callable, Any
from core.logger import get_logger
from core.models import RawRecord

from .base import BaseKeyboardMonitor, BaseMouseMonitor, BaseActiveWindowCapture
from .platforms import (
    MacOSKeyboardMonitor,
    MacOSMouseMonitor,
    WindowsKeyboardMonitor,
    WindowsMouseMonitor,
    LinuxKeyboardMonitor,
    LinuxMouseMonitor,
    MacOSActiveWindowCapture,
    WindowsActiveWindowCapture,
    LinuxActiveWindowCapture,
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
            logger.debug("Creating macOS keyboard monitor (PyObjC NSEvent)")
            return MacOSKeyboardMonitor(on_event)

        elif platform == "win32":
            logger.debug("Creating Windows keyboard monitor (pynput)")
            return WindowsKeyboardMonitor(on_event)

        elif platform.startswith("linux"):
            logger.debug("Creating Linux keyboard monitor (pynput)")
            return LinuxKeyboardMonitor(on_event)

        else:
            logger.warning(
                f"Unknown platform: {platform}, using Linux implementation as default"
            )
            return LinuxKeyboardMonitor(on_event)

    @staticmethod
    def create_mouse_monitor(
        on_event: Optional[Callable[[RawRecord], None]] = None,
        on_position_update: Optional[Callable[[int, int], None]] = None,
    ) -> BaseMouseMonitor:
        """Create mouse monitor

        Automatically select appropriate implementation based on current platform:
        - macOS: pynput (mouse listening is safe on macOS)
        - Windows: pynput (extendable to Windows API)
        - Linux: pynput (extendable to X11/evdev)

        Args:
            on_event: Event callback function
            on_position_update: Position update callback for active monitor tracking

        Returns:
            BaseMouseMonitor: Mouse monitor instance
        """
        platform = MonitorFactory.get_platform()

        if platform == "darwin":
            logger.debug("Creating macOS mouse monitor (pynput)")
            return MacOSMouseMonitor(on_event, on_position_update)

        elif platform == "win32":
            logger.debug("Creating Windows mouse monitor (pynput)")
            return WindowsMouseMonitor(on_event)

        elif platform.startswith("linux"):
            logger.debug("Creating Linux mouse monitor (pynput)")
            return LinuxMouseMonitor(on_event)

        else:
            logger.warning(
                f"Unknown platform: {platform}, using Linux implementation as default"
            )
            return LinuxMouseMonitor(on_event)

    @staticmethod
    def create_active_window_capture(
        on_event: Optional[Callable[[RawRecord], None]] = None,
        monitor_tracker: Optional[Any] = None,
    ) -> BaseActiveWindowCapture:
        """Create active window capture

        Automatically select appropriate implementation based on current platform:
        - macOS: NSWorkspace + Quartz CGWindowListCopyWindowInfo
        - Windows: Win32 API (pywin32 + psutil)
        - Linux: X11 (python-xlib) with Wayland fallback

        Args:
            on_event: Event callback function
            monitor_tracker: Active monitor tracker for coordinate calculations

        Returns:
            BaseActiveWindowCapture: Active window capture instance
        """
        from .active_window_capture import ActiveWindowCapture

        platform = MonitorFactory.get_platform()

        # Create coordinator
        coordinator = ActiveWindowCapture(on_event, monitor_tracker)

        # Create and set platform-specific implementation
        if platform == "darwin":
            logger.debug("Creating macOS active window capture (NSWorkspace + Quartz)")
            impl = MacOSActiveWindowCapture(on_event, monitor_tracker)
        elif platform == "win32":
            logger.debug("Creating Windows active window capture (Win32 API)")
            impl = WindowsActiveWindowCapture(on_event, monitor_tracker)
        elif platform.startswith("linux"):
            logger.debug("Creating Linux active window capture (X11/Wayland)")
            impl = LinuxActiveWindowCapture(on_event, monitor_tracker)
        else:
            logger.warning(
                f"Unknown platform: {platform}, using Linux implementation as default"
            )
            impl = LinuxActiveWindowCapture(on_event, monitor_tracker)

        coordinator.set_platform_impl(impl)
        return coordinator


# Convenience functions
def create_keyboard_monitor(
    on_event: Optional[Callable[[RawRecord], None]] = None,
) -> BaseKeyboardMonitor:
    """Create keyboard monitor (convenience function)"""
    return MonitorFactory.create_keyboard_monitor(on_event)


def create_mouse_monitor(
    on_event: Optional[Callable[[RawRecord], None]] = None,
    on_position_update: Optional[Callable[[int, int], None]] = None,
) -> BaseMouseMonitor:
    """Create mouse monitor (convenience function)"""
    return MonitorFactory.create_mouse_monitor(on_event, on_position_update)


def create_active_window_capture(
    on_event: Optional[Callable[[RawRecord], None]] = None,
    monitor_tracker: Optional[Any] = None,
) -> BaseActiveWindowCapture:
    """Create active window capture (convenience function)"""
    return MonitorFactory.create_active_window_capture(on_event, monitor_tracker)
