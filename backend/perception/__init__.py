"""
Perception module - 感知层模块

使用工厂模式根据平台自动选择合适的键盘和鼠标监控器实现

主要组件:
- PerceptionManager: 感知管理器，协调所有捕获器
- MonitorFactory: 监控器工厂，创建平台特定的实现
- 平台特定实现: macOS, Windows, Linux
"""

from .manager import PerceptionManager
from .factory import MonitorFactory, create_keyboard_monitor, create_mouse_monitor
from .base import BaseCapture, BaseKeyboardMonitor, BaseMouseMonitor

__all__ = [
    'PerceptionManager',
    'MonitorFactory',
    'create_keyboard_monitor',
    'create_mouse_monitor',
    'BaseCapture',
    'BaseKeyboardMonitor',
    'BaseMouseMonitor',
]
