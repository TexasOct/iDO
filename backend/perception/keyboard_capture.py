"""
键盘事件捕获
根据平台自动选择合适的实现:
- macOS: 使用 PyObjC NSEvent (避免 pynput 的 TSMGetInputSourceProperty 崩溃)
- 其他平台: 使用 pynput

解决方案说明:
pynput 在 macOS 上与 Tauri 主线程冲突，调用 TSMGetInputSourceProperty 导致崩溃。
通过使用 PyObjC 的 NSEvent API，可以在 Cocoa 主事件循环中正确处理键盘事件。

参考:
- https://github.com/moses-palmer/pynput/issues/55
- https://stackoverflow.com/questions/77288206
"""

import sys
from typing import Optional, Callable
from core.models import RawRecord
from core.logger import get_logger
from .base import BaseCapture

logger = get_logger(__name__)

# 根据平台选择实现
if sys.platform == "darwin":
    # macOS: 使用 PyObjC NSEvent
    try:
        from .keyboard_capture_macos import KeyboardCaptureMacOS as _KeyboardCaptureImpl
        logger.info("✅ 使用 PyObjC NSEvent 实现 macOS 键盘捕获")
    except ImportError as e:
        logger.warning(f"⚠️  无法导入 macOS 键盘捕获实现: {e}")
        logger.warning("   将使用禁用的占位实现")
        _KeyboardCaptureImpl = None
else:
    # 其他平台: 使用 pynput
    try:
        from .keyboard_capture_pynput import KeyboardCapturePynput as _KeyboardCaptureImpl
        logger.info("✅ 使用 pynput 实现键盘捕获")
    except ImportError as e:
        logger.warning(f"⚠️  无法导入 pynput 键盘捕获实现: {e}")
        _KeyboardCaptureImpl = None


class KeyboardCaptureDisabled(BaseCapture):
    """禁用的键盘捕获（占位实现）"""

    def __init__(self, on_event: Optional[Callable[[RawRecord], None]] = None):
        super().__init__()
        self.on_event = on_event
        self._disabled_reason = "No keyboard capture implementation available"

    def capture(self) -> RawRecord:
        from datetime import datetime
        from core.models import RecordType
        return RawRecord(
            timestamp=datetime.now(),
            type=RecordType.KEYBOARD_RECORD,
            data={"key": "test_key", "action": "press", "modifiers": []}
        )

    def output(self) -> None:
        pass

    def start(self):
        logger.warning(f"⚠️  键盘捕获已禁用: {self._disabled_reason}")
        self.is_running = False

    def stop(self):
        pass

    def is_special_key(self, key_data: dict) -> bool:
        return False

    def get_stats(self) -> dict:
        return {
            "is_running": False,
            "status": "disabled",
            "reason": self._disabled_reason
        }


# 导出统一接口
if _KeyboardCaptureImpl is not None:
    KeyboardCapture = _KeyboardCaptureImpl
else:
    KeyboardCapture = KeyboardCaptureDisabled
    logger.warning("⚠️  键盘捕获功能不可用")


__all__ = ['KeyboardCapture']
