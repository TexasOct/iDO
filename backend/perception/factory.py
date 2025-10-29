"""
感知层平台工厂
根据运行平台自动创建相应的键盘和鼠标监控器

设计模式：工厂模式 (Factory Pattern)
- 调用者只需要知道接口，无需关心具体实现
- 根据平台自动选择合适的实现
- 方便未来扩展和维护
"""

import sys
from typing import Optional, Callable
from core.logger import get_logger
from core.models import RawRecord

from .base import BaseKeyboardMonitor, BaseMouseMonitor
from .platforms import (
    MacOSKeyboardMonitor, MacOSMouseMonitor,
    WindowsKeyboardMonitor, WindowsMouseMonitor,
    LinuxKeyboardMonitor, LinuxMouseMonitor
)

logger = get_logger(__name__)


class MonitorFactory:
    """监控器工厂类"""

    @staticmethod
    def get_platform() -> str:
        """获取当前平台标识

        Returns:
            str: 'darwin' (macOS), 'win32' (Windows), 'linux' (Linux)
        """
        return sys.platform

    @staticmethod
    def create_keyboard_monitor(
        on_event: Optional[Callable[[RawRecord], None]] = None
    ) -> BaseKeyboardMonitor:
        """创建键盘监控器

        根据当前平台自动选择合适的实现：
        - macOS: PyObjC NSEvent (避免 pynput 的 TSM 崩溃)
        - Windows: pynput (可扩展为 Windows API)
        - Linux: pynput (可扩展为 X11/evdev)

        Args:
            on_event: 事件回调函数

        Returns:
            BaseKeyboardMonitor: 键盘监控器实例
        """
        platform = MonitorFactory.get_platform()

        if platform == "darwin":
            logger.info("创建 macOS 键盘监控器（PyObjC NSEvent）")
            return MacOSKeyboardMonitor(on_event)

        elif platform == "win32":
            logger.info("创建 Windows 键盘监控器（pynput）")
            return WindowsKeyboardMonitor(on_event)

        elif platform.startswith("linux"):
            logger.info("创建 Linux 键盘监控器（pynput）")
            return LinuxKeyboardMonitor(on_event)

        else:
            logger.warning(f"未知平台: {platform}，使用 Linux 实现作为默认")
            return LinuxKeyboardMonitor(on_event)

    @staticmethod
    def create_mouse_monitor(
        on_event: Optional[Callable[[RawRecord], None]] = None
    ) -> BaseMouseMonitor:
        """创建鼠标监控器

        根据当前平台自动选择合适的实现：
        - macOS: pynput (鼠标监听在 macOS 上是安全的)
        - Windows: pynput (可扩展为 Windows API)
        - Linux: pynput (可扩展为 X11/evdev)

        Args:
            on_event: 事件回调函数

        Returns:
            BaseMouseMonitor: 鼠标监控器实例
        """
        platform = MonitorFactory.get_platform()

        if platform == "darwin":
            logger.info("创建 macOS 鼠标监控器（pynput）")
            return MacOSMouseMonitor(on_event)

        elif platform == "win32":
            logger.info("创建 Windows 鼠标监控器（pynput）")
            return WindowsMouseMonitor(on_event)

        elif platform.startswith("linux"):
            logger.info("创建 Linux 鼠标监控器（pynput）")
            return LinuxMouseMonitor(on_event)

        else:
            logger.warning(f"未知平台: {platform}，使用 Linux 实现作为默认")
            return LinuxMouseMonitor(on_event)


# 便捷函数
def create_keyboard_monitor(
    on_event: Optional[Callable[[RawRecord], None]] = None
) -> BaseKeyboardMonitor:
    """创建键盘监控器（便捷函数）"""
    return MonitorFactory.create_keyboard_monitor(on_event)


def create_mouse_monitor(
    on_event: Optional[Callable[[RawRecord], None]] = None
) -> BaseMouseMonitor:
    """创建鼠标监控器（便捷函数）"""
    return MonitorFactory.create_mouse_monitor(on_event)
