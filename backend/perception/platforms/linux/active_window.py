"""
Linux active window capture implementation
Uses X11 (python-xlib) with Wayland fallback
"""

import os
import subprocess
from typing import TYPE_CHECKING, Any, Dict, Optional

from core.logger import get_logger
from perception.base import BaseActiveWindowCapture

logger = get_logger(__name__)

# Runtime imports
try:
    from Xlib import X, display  # type: ignore

    X11_AVAILABLE = True
except ImportError:
    X11_AVAILABLE = False
    logger.warning("python-xlib not available")
    # Create placeholder for type checking
    if TYPE_CHECKING:
        display = None  # type: ignore
        X = None  # type: ignore


class LinuxActiveWindowCapture(BaseActiveWindowCapture):
    """Linux active window capturer using X11 or Wayland"""

    def __init__(
        self,
        on_event=None,
        monitor_tracker=None,
    ):
        super().__init__()
        self.on_event = on_event
        self.monitor_tracker = monitor_tracker

        # Detect display server
        self.is_wayland = self._detect_wayland()
        self.display = None

        if not self.is_wayland and X11_AVAILABLE:
            try:
                self.display = display.Display()  # type: ignore
                logger.info("Using X11 for active window capture")
            except Exception as e:
                logger.warning(f"Failed to connect to X11 display: {e}")
                self.display = None
        else:
            if self.is_wayland:
                logger.info("Wayland detected, using fallback method")
            else:
                logger.warning("Neither X11 nor Wayland properly configured")

    def _detect_wayland(self) -> bool:
        """Detect if running under Wayland"""
        wayland_display = os.environ.get("WAYLAND_DISPLAY")
        xdg_session_type = os.environ.get("XDG_SESSION_TYPE", "").lower()
        return wayland_display is not None or xdg_session_type == "wayland"

    def get_active_window_info(self) -> Optional[Dict[str, Any]]:
        """
        Get current active window information

        Returns:
            Dictionary containing window info, or None if unavailable
        """
        if not self.is_wayland and self.display is not None:
            return self._get_x11_window_info()
        else:
            return self._get_wayland_window_info()

    def _get_x11_window_info(self) -> Optional[Dict[str, Any]]:
        """Get window info using X11"""
        if self.display is None:
            return None

        try:
            # Get focused window
            root = self.display.screen().root  # type: ignore
            focus_window = self.display.get_input_focus().focus  # type: ignore

            if focus_window is None or focus_window == X.NONE:  # type: ignore
                return None

            # Get window properties
            try:
                window_name = (
                    focus_window.get_wm_name() or focus_window.get_full_property(
                        self.display.intern_atom("_NET_WM_NAME"), X.AnyPropertyType  # type: ignore
                    )
                )
                if hasattr(window_name, "value"):
                    window_title = window_name.value.decode("utf-8", errors="ignore")
                else:
                    window_title = str(window_name) if window_name else ""
            except Exception:
                window_title = ""

            # Get window class (application name)
            try:
                wm_class = focus_window.get_wm_class()
                app_name = wm_class[1] if wm_class and len(wm_class) > 1 else "Unknown"
            except Exception:
                app_name = "Unknown"

            # Get window geometry
            try:
                geometry = focus_window.get_geometry()
                # Translate to root coordinates
                translate = focus_window.translate_coords(root, 0, 0)
                window_bounds = {
                    "x": translate.x,
                    "y": translate.y,
                    "width": geometry.width,
                    "height": geometry.height,
                }
            except Exception as e:
                logger.warning(f"Failed to get window geometry: {e}")
                window_bounds = {"x": 0, "y": 0, "width": 0, "height": 0}

            # Get window ID and PID
            try:
                window_id = focus_window.id
                pid_property = focus_window.get_full_property(
                    self.display.intern_atom("_NET_WM_PID"), X.AnyPropertyType  # type: ignore
                )
                process_id = pid_property.value[0] if pid_property else 0
            except Exception:
                window_id = 0
                process_id = 0

            return {
                "action": "capture",
                "timestamp": None,  # Will be set by coordinator
                "app_name": app_name,
                "app_bundle_id": None,  # Linux doesn't have bundle IDs
                "app_process_id": int(process_id),
                "window_title": window_title,
                "window_id": int(window_id),
                "window_bounds": window_bounds,
            }

        except Exception as e:
            logger.error(f"Failed to get active window info via X11: {e}")
            return None

    def _get_wayland_window_info(self) -> Optional[Dict[str, Any]]:
        """Get window info using Wayland fallback (limited support)"""
        try:
            # Try using wmctrl as a fallback
            result = subprocess.run(
                ["wmctrl", "-lx"], capture_output=True, text=True, timeout=1
            )

            if result.returncode != 0:
                return None

            # Parse wmctrl output
            lines = result.stdout.strip().split("\n")
            if not lines:
                return None

            # Get the active window (first line is usually active)
            # Format: window_id desktop class hostname window_title
            parts = lines[0].split(None, 4)
            if len(parts) < 5:
                return None

            window_id = int(parts[0], 16)  # Hex window ID
            wm_class = parts[2].split(".")[1] if "." in parts[2] else parts[2]
            window_title = parts[4]

            # Note: Wayland doesn't provide geometry easily without compositor support
            return {
                "action": "capture",
                "timestamp": None,  # Will be set by coordinator
                "app_name": wm_class,
                "app_bundle_id": None,
                "app_process_id": 0,  # Not available via wmctrl
                "window_title": window_title,
                "window_id": window_id,
                "window_bounds": None,  # Not available in Wayland fallback
            }

        except FileNotFoundError:
            logger.warning("wmctrl not found - install for Wayland support")
            return None
        except Exception as e:
            logger.error(f"Failed to get active window info via Wayland: {e}")
            return None

    def start(self) -> None:
        """Start capturing"""
        if self.is_running:
            return
        self.is_running = True
        logger.debug("Linux active window capture started")

    def stop(self) -> None:
        """Stop capturing"""
        if not self.is_running:
            return
        self.is_running = False
        if self.display:
            try:
                self.display.close()
            except Exception as e:
                logger.warning(f"Failed to close X11 display: {e}")
            self.display = None
        logger.debug("Linux active window capture stopped")

    def capture(self):
        """Not used - handled by coordinator"""
        return None

    def output(self) -> None:
        """Output/flush processed data"""
        pass

    def get_stats(self) -> Dict[str, Any]:
        """Get capture statistics"""
        return {"is_wayland": self.is_wayland, "x11_available": X11_AVAILABLE}
