"""
Platform-specific implementation package
Provides different keyboard, mouse, and screen state monitoring implementations based on operating system
"""

from .linux import LinuxKeyboardMonitor, LinuxMouseMonitor, LinuxScreenStateMonitor
from .macos import MacOSKeyboardMonitor, MacOSMouseMonitor, MacOSScreenStateMonitor
from .windows import (
    WindowsKeyboardMonitor,
    WindowsMouseMonitor,
    WindowsScreenStateMonitor,
)

__all__ = [
    "MacOSKeyboardMonitor",
    "MacOSMouseMonitor",
    "MacOSScreenStateMonitor",
    "WindowsKeyboardMonitor",
    "WindowsMouseMonitor",
    "WindowsScreenStateMonitor",
    "LinuxKeyboardMonitor",
    "LinuxMouseMonitor",
    "LinuxScreenStateMonitor",
]
