"""
macOS platform-specific implementation
Uses PyObjC NSEvent to monitor keyboard, pynput to monitor mouse
"""

from .keyboard import MacOSKeyboardMonitor
from .mouse import MacOSMouseMonitor

__all__ = ["MacOSKeyboardMonitor", "MacOSMouseMonitor"]
