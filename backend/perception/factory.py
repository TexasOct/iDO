"""
Perception layer platform factory
Automatically creates platform-specific perception components (monitors, captures, listeners)

Design Pattern: Factory Pattern
- Callers only need to know the interface, without caring about specific implementation
- Automatically selects appropriate implementation based on platform
- Convenient for future expansion and maintenance

Components created:
- Keyboard Monitor: Captures keyboard events
- Mouse Monitor: Captures mouse events
- Active Window Capture: Captures active window information
- Screen State Monitor: Monitors screen lock/unlock events
"""

import sys
from typing import Optional, Callable, Any
from core.logger import get_logger
from core.models import RawRecord

from .base import BaseKeyboardMonitor, BaseMouseMonitor, BaseActiveWindowCapture, BaseEventListener
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


class PerceptionFactory:
    """Perception layer component factory class"""

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
        platform = PerceptionFactory.get_platform()

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
        platform = PerceptionFactory.get_platform()

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

        platform = PerceptionFactory.get_platform()

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

    @staticmethod
    def create_screen_state_monitor(
        on_screen_lock: Optional[Callable[[], None]] = None,
        on_screen_unlock: Optional[Callable[[], None]] = None,
    ) -> BaseEventListener:
        """Create screen state monitor

        Automatically select appropriate implementation based on current platform:
        - macOS: macOS screen state monitor
        - Windows: Windows screen state monitor
        - Linux: Linux screen state monitor

        Args:
            on_screen_lock: Screen lock/sleep callback
            on_screen_unlock: Screen unlock/wake callback

        Returns:
            BaseEventListener: Screen state monitor instance
        """
        platform = PerceptionFactory.get_platform()

        if platform == "darwin":
            logger.debug("Creating macOS screen state monitor")
            from .platforms.macos import MacOSScreenStateMonitor
            return MacOSScreenStateMonitor(on_screen_lock, on_screen_unlock)

        elif platform == "win32":
            logger.debug("Creating Windows screen state monitor")
            from .platforms.windows import WindowsScreenStateMonitor
            return WindowsScreenStateMonitor(on_screen_lock, on_screen_unlock)

        elif platform.startswith("linux"):
            logger.debug("Creating Linux screen state monitor")
            from .platforms.linux import LinuxScreenStateMonitor
            return LinuxScreenStateMonitor(on_screen_lock, on_screen_unlock)

        else:
            logger.warning(
                f"Unsupported platform: {platform}, screen state monitor unavailable"
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


# Convenience functions
def create_keyboard_monitor(
    on_event: Optional[Callable[[RawRecord], None]] = None,
) -> BaseKeyboardMonitor:
    """Create keyboard monitor (convenience function)"""
    return PerceptionFactory.create_keyboard_monitor(on_event)


def create_mouse_monitor(
    on_event: Optional[Callable[[RawRecord], None]] = None,
    on_position_update: Optional[Callable[[int, int], None]] = None,
) -> BaseMouseMonitor:
    """Create mouse monitor (convenience function)"""
    return PerceptionFactory.create_mouse_monitor(on_event, on_position_update)


def create_active_window_capture(
    on_event: Optional[Callable[[RawRecord], None]] = None,
    monitor_tracker: Optional[Any] = None,
) -> BaseActiveWindowCapture:
    """Create active window capture (convenience function)"""
    return PerceptionFactory.create_active_window_capture(on_event, monitor_tracker)


def create_screen_state_monitor(
    on_screen_lock: Optional[Callable[[], None]] = None,
    on_screen_unlock: Optional[Callable[[], None]] = None,
) -> BaseEventListener:
    """Create screen state monitor (convenience function)"""
    return PerceptionFactory.create_screen_state_monitor(on_screen_lock, on_screen_unlock)
