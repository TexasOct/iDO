"""
Linux screen state monitor implementation
"""

import threading
from importlib import import_module
from typing import Callable, Optional

from core.logger import get_logger
from perception.base import BaseEventListener

logger = get_logger(__name__)


class LinuxScreenStateMonitor(BaseEventListener):
    """Linux screen state monitor"""

    def __init__(
        self,
        on_screen_lock: Optional[Callable[[], None]] = None,
        on_screen_unlock: Optional[Callable[[], None]] = None,
    ):
        """
        Initialize Linux screen state monitor

        Args:
            on_screen_lock: Screen lock/sleep callback
            on_screen_unlock: Screen unlock/wake callback
        """
        super().__init__()
        self.on_screen_lock = on_screen_lock
        self.on_screen_unlock = on_screen_unlock
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start listening"""
        if self.is_running:
            return

        try:
            # Try to use dbus to listen for logind signals
            import_module("dbus")
            dbus_glib = import_module("dbus.mainloop.glib")
            DBusGMainLoop = getattr(dbus_glib, "DBusGMainLoop")

            DBusGMainLoop(set_as_default=True)

            self.is_running = True

            # Run DBus main loop in background thread
            self._thread = threading.Thread(target=self._dbus_loop, daemon=True)
            self._thread.start()

            logger.info("Linux screen state monitor started")

        except ModuleNotFoundError as exc:
            logger.warning(
                "Cannot import dbus dependencies (%s), screen state monitor unavailable",
                exc,
            )
            self.is_running = False
        except Exception as e:
            logger.error(f"Failed to start Linux screen state monitor: {e}")
            self.is_running = False

    def _dbus_loop(self) -> None:
        """DBus main loop"""
        try:
            dbus = import_module("dbus")
            gi_repository = import_module("gi.repository")
            GLib = getattr(gi_repository, "GLib")

            system_bus = getattr(dbus, "SystemBus")
            bus = system_bus()

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

        except ModuleNotFoundError as exc:
            logger.warning(
                "Missing dbus/gi dependencies for screen state monitor: %s", exc
            )
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
