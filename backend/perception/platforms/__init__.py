"""
Platform-specific implementation package
Provides different keyboard, mouse, and screen state monitoring implementations based on operating system
"""

from .linux import (
    LinuxKeyboardMonitor,
    LinuxMouseMonitor,
    LinuxScreenStateMonitor,
    LinuxActiveWindowCapture,
)
from .macos import (
    MacOSKeyboardMonitor,
    MacOSMouseMonitor,
    MacOSScreenStateMonitor,
    MacOSActiveWindowCapture,
)
from .windows import (
    WindowsKeyboardMonitor,
    WindowsMouseMonitor,
    WindowsScreenStateMonitor,
    WindowsActiveWindowCapture,
)

__all__ = [
    "MacOSKeyboardMonitor",
    "MacOSMouseMonitor",
    "MacOSScreenStateMonitor",
    "MacOSActiveWindowCapture",
    "WindowsKeyboardMonitor",
    "WindowsMouseMonitor",
    "WindowsScreenStateMonitor",
    "WindowsActiveWindowCapture",
    "LinuxKeyboardMonitor",
    "LinuxMouseMonitor",
    "LinuxScreenStateMonitor",
    "LinuxActiveWindowCapture",
]
