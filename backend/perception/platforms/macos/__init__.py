"""
macOS platform-specific implementation
Uses PyObjC NSEvent to monitor keyboard, pynput to monitor mouse
"""

from .keyboard import MacOSKeyboardMonitor
from .mouse import MacOSMouseMonitor
from .screen_state import MacOSScreenStateMonitor
from .active_window import MacOSActiveWindowCapture

__all__ = [
    "MacOSKeyboardMonitor",
    "MacOSMouseMonitor",
    "MacOSScreenStateMonitor",
    "MacOSActiveWindowCapture",
]
