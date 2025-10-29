"""
Linux 键盘事件捕获
使用 pynput 库监控键盘输入

TODO: 未来可以考虑使用 X11 或 evdev 实现更原生的监控
"""

from datetime import datetime
from typing import Optional, Callable, Dict, Any
from pynput import keyboard
from core.models import RawRecord, RecordType
from core.logger import get_logger
from perception.base import BaseKeyboardMonitor

logger = get_logger(__name__)


class LinuxKeyboardMonitor(BaseKeyboardMonitor):
    """Linux 键盘事件捕获器（使用 pynput）"""

    def __init__(self, on_event: Optional[Callable[[RawRecord], None]] = None):
        super().__init__(on_event)
        self.listener: Optional[keyboard.Listener] = None
        self._key_buffer = []
        self._last_key_time = 0
        self._buffer_timeout = 0.1

    def capture(self) -> RawRecord:
        """捕获键盘事件（同步方法，用于测试）"""
        return RawRecord(
            timestamp=datetime.now(),
            type=RecordType.KEYBOARD_RECORD,
            data={
                "key": "test_key",
                "action": "press",
                "modifiers": []
            }
        )

    def output(self) -> None:
        """输出处理后的数据"""
        if self.on_event:
            for record in self._key_buffer:
                self.on_event(record)
        self._key_buffer.clear()

    def start(self):
        """启动键盘监听"""
        if self.is_running:
            logger.warning("Linux 键盘监听已在运行中")
            return

        try:
            self.is_running = True
            self.listener = keyboard.Listener(
                on_press=self._on_press,
                on_release=self._on_release
            )
            self.listener.start()
            logger.info("✅ Linux 键盘监听已启动（使用 pynput）")
            logger.info("   确保你的用户有访问输入设备的权限")

        except Exception as e:
            self.is_running = False
            logger.error(f"启动 Linux 键盘监听失败: {e}")
            raise

    def stop(self):
        """停止键盘监听"""
        if not self.is_running:
            return

        self.is_running = False
        if self.listener:
            try:
                self.listener.stop()
                if hasattr(self.listener, '_thread') and self.listener._thread:
                    self.listener._thread.join(timeout=3.0)
                self.listener = None
                logger.info("Linux 键盘监听已停止")
            except Exception as e:
                logger.error(f"停止 Linux 键盘监听失败: {e}")

    def _on_press(self, key):
        """处理按键按下事件"""
        if not self.is_running:
            return

        try:
            key_data = self._extract_key_data(key, "press")
            record = RawRecord(
                timestamp=datetime.now(),
                type=RecordType.KEYBOARD_RECORD,
                data=key_data
            )

            if self.on_event:
                self.on_event(record)

        except Exception as e:
            logger.error(f"处理按键事件失败: {e}")

    def _on_release(self, key):
        """处理按键释放事件"""
        if not self.is_running:
            return

        try:
            key_data = self._extract_key_data(key, "release")
            record = RawRecord(
                timestamp=datetime.now(),
                type=RecordType.KEYBOARD_RECORD,
                data=key_data
            )

            if self.on_event:
                self.on_event(record)

        except Exception as e:
            logger.error(f"处理按键释放事件失败: {e}")

    def _extract_key_data(self, key, action: str) -> dict:
        """提取按键数据"""
        try:
            # 尝试获取字符
            if hasattr(key, 'char') and key.char is not None:
                key_name = key.char
                key_type = "char"
            else:
                # 特殊键
                key_name = str(key).replace('Key.', '')
                key_type = "special"

            return {
                "key": key_name,
                "key_type": key_type,
                "action": action,
                "modifiers": [],  # pynput 不直接提供当前修饰键状态
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"提取按键数据失败: {e}")
            return {
                "key": "unknown",
                "action": action,
                "modifiers": [],
                "timestamp": datetime.now().isoformat()
            }

    def is_special_key(self, key_data: dict) -> bool:
        """判断是否为特殊键（需要记录）"""
        special_keys = {
            'enter', 'space', 'tab', 'backspace', 'delete',
            'up', 'down', 'left', 'right',
            'home', 'end', 'page_up', 'page_down',
            'f1', 'f2', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8', 'f9', 'f10', 'f11', 'f12',
            'esc', 'caps_lock', 'num_lock', 'scroll_lock',
            'insert', 'print_screen', 'pause',
            'cmd', 'alt', 'ctrl', 'shift', 'super'  # Linux 使用 'super' 代替 Windows 键
        }

        key = key_data.get("key", "").lower()
        return (
            key in special_keys or
            key_data.get("key_type") == "special"
        )

    def get_stats(self) -> Dict[str, Any]:
        """获取捕获统计信息"""
        return {
            "is_running": self.is_running,
            "platform": "Linux",
            "implementation": "pynput",
            "buffer_size": len(self._key_buffer),
            "last_key_time": self._last_key_time
        }
