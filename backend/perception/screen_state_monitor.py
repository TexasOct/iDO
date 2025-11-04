"""
Screen state monitor
Monitor screen lock/unlock, sleep/wake events for automatic pause/resume of perception
"""

import platform
import threading
from typing import Callable, Optional
from core.logger import get_logger

logger = get_logger(__name__)


class ScreenStateMonitor:
    """Screen state monitor base class"""

    def __init__(
        self,
        on_screen_lock: Optional[Callable] = None,
        on_screen_unlock: Optional[Callable] = None,
    ):
        """
        Initialize screen state monitor

        Args:
            on_screen_lock: Screen lock/sleep callback
            on_screen_unlock: Screen unlock/wake callback
        """
        self.on_screen_lock = on_screen_lock
        self.on_screen_unlock = on_screen_unlock
        self.is_running = False
        self._thread = None

    def start(self) -> None:
        """Start listening"""
        raise NotImplementedError

    def stop(self) -> None:
        """Stop listening"""
        raise NotImplementedError


class MacOSScreenStateMonitor(ScreenStateMonitor):
    """macOS screen state monitor"""

    def start(self) -> None:
        """Start listening"""
        if self.is_running:
            return

        try:
            from AppKit import NSWorkspace
            from Foundation import NSNotificationCenter

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

        except ImportError:
            logger.error(
                "Cannot import AppKit/Foundation, screen state monitor unavailable"
            )
            self.is_running = False

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
            from AppKit import NSWorkspace

            self.is_running = False

            # Remove all observers
            nc = NSWorkspace.sharedWorkspace().notificationCenter()
            nc.removeObserver_(self)

            logger.info("macOS screen state monitor stopped")

        except Exception as e:
            logger.error(f"Failed to stop macOS screen state monitor: {e}")


class WindowsScreenStateMonitor(ScreenStateMonitor):
    """Windows screen state monitor"""

    def start(self) -> None:
        """Start listening"""
        if self.is_running:
            return

        try:
            import win32api
            import win32con
            import win32gui

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
            import win32api
            import win32con
            import win32gui

            # Create hidden window to receive messages
            wc = win32gui.WNDCLASS()
            wc.lpfnWndProc = self._wnd_proc
            wc.lpszClassName = "RewindScreenStateMonitor"
            wc.hInstance = win32api.GetModuleHandle(None)

            class_atom = win32gui.RegisterClass(wc)
            hwnd = win32gui.CreateWindow(
                class_atom,
                "Rewind Screen State Monitor",
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
        import win32con

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


class LinuxScreenStateMonitor(ScreenStateMonitor):
    """Linux screen state monitor"""

    def start(self) -> None:
        """Start listening"""
        if self.is_running:
            return

        try:
            # Try to use dbus to listen for logind signals
            import dbus
            from dbus.mainloop.glib import DBusGMainLoop

            DBusGMainLoop(set_as_default=True)

            self.is_running = True

            # Run DBus main loop in background thread
            self._thread = threading.Thread(target=self._dbus_loop, daemon=True)
            self._thread.start()

            logger.info("Linux screen state monitor started")

        except ImportError:
            logger.warning(
                "Cannot import dbus, screen state monitor unavailable (need to install python-dbus)"
            )
            self.is_running = False
        except Exception as e:
            logger.error(f"Failed to start Linux screen state monitor: {e}")
            self.is_running = False

    def _dbus_loop(self) -> None:
        """DBus main loop"""
        try:
            import dbus
            from gi.repository import GLib

            bus = dbus.SystemBus()

            # Listen for PrepareForSleep signal
            bus.add_signal_receiver(
                self._handle_prepare_for_sleep,
                "PrepareForSleep",
                "org.freedesktop.login1.Manager",
                "org.freedesktop.login1",
            )

            # Run main loop
            loop = GLib.MainLoop()
            while self.is_running:
                loop.get_context().iteration(False)
                threading.Event().wait(0.1)

        except Exception as e:
            logger.error(f"Linux DBus loop exception: {e}")

    def _handle_prepare_for_sleep(self, sleep: bool) -> None:
        """Handle system sleep/wake signal"""
        if sleep:
            logger.info("System about to sleep detected")
            if self.on_screen_lock:
                self.on_screen_lock()
        else:
            logger.info("System wake detected")
            if self.on_screen_unlock:
                self.on_screen_unlock()

    def stop(self) -> None:
        """Stop listening"""
        if not self.is_running:
            return

        self.is_running = False

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

        logger.info("Linux screen state monitor stopped")


def create_screen_state_monitor(
    on_screen_lock: Optional[Callable] = None,
    on_screen_unlock: Optional[Callable] = None,
) -> ScreenStateMonitor:
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
        return MacOSScreenStateMonitor(on_screen_lock, on_screen_unlock)
    elif system == "Windows":
        return WindowsScreenStateMonitor(on_screen_lock, on_screen_unlock)
    elif system == "Linux":
        return LinuxScreenStateMonitor(on_screen_lock, on_screen_unlock)
    else:
        logger.warning(
            f"Unsupported platform: {system}, screen state monitor unavailable"
        )
        return ScreenStateMonitor(on_screen_lock, on_screen_unlock)
