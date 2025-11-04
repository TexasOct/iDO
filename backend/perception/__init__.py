"""
Perception module - Perception layer module

Uses factory pattern to automatically select appropriate keyboard and mouse monitor implementations based on platform

Main components:
- PerceptionManager: Perception manager, coordinates all capturers
- MonitorFactory: Monitor factory, creates platform-specific implementations
- Platform-specific implementations: macOS, Windows, Linux
"""

from .manager import PerceptionManager
from .factory import MonitorFactory, create_keyboard_monitor, create_mouse_monitor
from .base import BaseCapture, BaseKeyboardMonitor, BaseMouseMonitor

__all__ = [
    "PerceptionManager",
    "MonitorFactory",
    "create_keyboard_monitor",
    "create_mouse_monitor",
    "BaseCapture",
    "BaseKeyboardMonitor",
    "BaseMouseMonitor",
]
