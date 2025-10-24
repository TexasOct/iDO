"""
macOS 键盘事件捕获（使用 PyObjC）
使用 NSEvent 全局监听器监控键盘输入

解决方案:
使用 PyObjC 的 NSEvent.addGlobalMonitorForEventsMatchingMask_handler_
而不是 pynput，避免 TSMGetInputSourceProperty 在后台线程崩溃的问题。

注意事项:
1. 需要在系统偏好设置 -> 安全性与隐私 -> 辅助功能 中授予应用权限
2. NSEvent 监听器在 macOS 主事件循环中运行，避免线程冲突
3. 使用线程安全的队列在 Cocoa 和 Python 异步代码之间传递事件
"""

import sys
import threading
from datetime import datetime
from typing import Optional, Callable
from queue import Queue
from core.models import RawRecord, RecordType
from core.logger import get_logger
from .base import BaseCapture

logger = get_logger(__name__)

# 仅在 macOS 上导入 PyObjC
if sys.platform == "darwin":
    try:
        from AppKit import NSEvent, NSKeyDownMask, NSKeyUpMask, NSFlagsChangedMask
        from PyObjCTools import AppHelper
        PYOBJC_AVAILABLE = True
    except ImportError:
        PYOBJC_AVAILABLE = False
        logger.warning("PyObjC 未安装，macOS 键盘监听不可用")
        logger.warning("请运行: pip install pyobjc-framework-Cocoa")
else:
    PYOBJC_AVAILABLE = False


class KeyboardCaptureMacOS(BaseCapture):
    """macOS 键盘事件捕获器（使用 PyObjC）"""

    def __init__(self, on_event: Optional[Callable[[RawRecord], None]] = None):
        super().__init__()
        self.on_event = on_event
        self.event_queue: Queue = Queue()
        self.monitor = None
        self.processing_thread: Optional[threading.Thread] = None
        self._last_key_time = 0
        self._key_buffer = []
        self._buffer_timeout = 0.1  # 100ms 内的按键会被合并

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
        if not PYOBJC_AVAILABLE:
            logger.error("PyObjC 不可用，无法启动 macOS 键盘监听")
            logger.info("请运行: uv add pyobjc-framework-Cocoa")
            return

        if self.is_running:
            logger.warning("macOS 键盘监听已在运行中")
            return

        try:
            self.is_running = True

            # 创建全局事件监听器
            mask = NSKeyDownMask | NSKeyUpMask | NSFlagsChangedMask
            self.monitor = NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(
                mask,
                self._event_handler
            )

            # 启动事件处理线程
            self.processing_thread = threading.Thread(
                target=self._process_events,
                daemon=True
            )
            self.processing_thread.start()

            logger.info("✅ macOS 键盘监听已启动（使用 PyObjC NSEvent）")
            logger.info("   如果无法捕获按键，请检查系统偏好设置 -> 安全性与隐私 -> 辅助功能")

        except Exception as e:
            self.is_running = False
            logger.error(f"启动 macOS 键盘监听失败: {e}")
            raise

    def stop(self):
        """停止键盘监听"""
        if not self.is_running:
            return

        self.is_running = False

        try:
            # 移除全局监听器
            if self.monitor and PYOBJC_AVAILABLE:
                NSEvent.removeMonitor_(self.monitor)
                self.monitor = None

            # 等待处理线程结束
            if self.processing_thread and self.processing_thread.is_alive():
                logger.debug("等待键盘处理线程结束...")
                self.processing_thread.join(timeout=3.0)
                if self.processing_thread.is_alive():
                    logger.warning("键盘处理线程未能在超时时间内结束，但继续进行")
                self.processing_thread = None

            # 清空事件队列
            while not self.event_queue.empty():
                try:
                    self.event_queue.get_nowait()
                except:
                    break

            logger.info("macOS 键盘监听已停止")

        except Exception as e:
            logger.error(f"停止 macOS 键盘监听失败: {e}")

    def _event_handler(self, event):
        """NSEvent 回调处理器（在 Cocoa 主线程中运行）"""
        try:
            # 提取事件数据
            event_type = event.type()
            modifiers = event.modifierFlags()

            # 确定动作类型
            if event_type == 10:  # NSKeyDown
                action = "press"
            elif event_type == 11:  # NSKeyUp
                action = "release"
            elif event_type == 12:  # NSFlagsChanged
                action = "modifier"
            else:
                action = "unknown"

            # 构建事件数据
            key_data = {
                "action": action,
                "modifiers": self._extract_modifiers(modifiers),
                "timestamp": datetime.now().isoformat()
            }

            # 添加键码和字符信息（NSFlagsChanged 事件没有 keyCode 和 characters）
            if event_type == 12:  # NSFlagsChanged
                # 修饰键事件，从 modifiers 中推断按键
                key_data["key_code"] = 0
                key_data["key"] = self._get_modifier_key_name(modifiers)
                key_data["key_type"] = "modifier"
            else:
                # 普通按键事件
                key_code = event.keyCode()
                key_data["key_code"] = key_code

                # 尝试获取字符（只有 KeyDown/KeyUp 有 characters）
                try:
                    characters = event.characters()
                    if characters and len(characters) > 0:
                        key_data["key"] = characters
                        key_data["key_type"] = "char"
                    else:
                        key_data["key"] = self._get_special_key_name(key_code)
                        key_data["key_type"] = "special"
                except (AttributeError, RuntimeError):
                    # 某些事件没有 characters 方法
                    key_data["key"] = self._get_special_key_name(key_code)
                    key_data["key_type"] = "special"

            # 将事件放入队列（线程安全）
            record = RawRecord(
                timestamp=datetime.now(),
                type=RecordType.KEYBOARD_RECORD,
                data=key_data
            )
            self.event_queue.put(record)

        except Exception as e:
            logger.error(f"处理 NSEvent 失败: {e}")

    def _process_events(self):
        """事件处理线程（在后台处理队列中的事件）"""
        import time

        while self.is_running:
            try:
                # 从队列中获取事件（非阻塞）
                if not self.event_queue.empty():
                    record = self.event_queue.get(timeout=0.1)
                    current_time = time.time()

                    # 检查是否需要合并按键（快速连续按键）
                    if current_time - self._last_key_time < self._buffer_timeout:
                        self._key_buffer.append(record)
                    else:
                        # 输出之前的缓冲数据
                        self.output()
                        # 添加新事件
                        self._key_buffer.append(record)

                    self._last_key_time = current_time
                else:
                    # 没有事件时短暂休眠
                    time.sleep(0.01)

            except Exception as e:
                if self.is_running:
                    logger.error(f"处理键盘事件失败: {e}")

        # 线程退出前输出剩余缓冲
        self.output()

    def _extract_modifiers(self, modifier_flags: int) -> list:
        """从修饰键标志中提取修饰键列表"""
        modifiers = []

        # NSEvent 修饰键标志位
        NSCommandKeyMask = 1 << 20
        NSAlternateKeyMask = 1 << 19
        NSShiftKeyMask = 1 << 17
        NSControlKeyMask = 1 << 18

        if modifier_flags & NSCommandKeyMask:
            modifiers.append("cmd")
        if modifier_flags & NSAlternateKeyMask:
            modifiers.append("alt")
        if modifier_flags & NSShiftKeyMask:
            modifiers.append("shift")
        if modifier_flags & NSControlKeyMask:
            modifiers.append("ctrl")

        return modifiers

    def _get_special_key_name(self, key_code: int) -> str:
        """根据键码获取特殊键名称"""
        # macOS 键码映射（常用特殊键）
        key_map = {
            36: 'enter',
            49: 'space',
            48: 'tab',
            51: 'backspace',
            53: 'esc',
            117: 'delete',
            122: 'f1',
            120: 'f2',
            99: 'f3',
            118: 'f4',
            96: 'f5',
            97: 'f6',
            98: 'f7',
            100: 'f8',
            101: 'f9',
            109: 'f10',
            103: 'f11',
            111: 'f12',
            123: 'left',
            124: 'right',
            125: 'down',
            126: 'up',
            115: 'home',
            119: 'end',
            116: 'page_up',
            121: 'page_down',
        }

        return key_map.get(key_code, f'key_{key_code}')

    def _get_modifier_key_name(self, modifier_flags: int) -> str:
        """从修饰键标志中获取按键名称（用于 NSFlagsChanged 事件）"""
        # NSEvent 修饰键标志位
        NSCommandKeyMask = 1 << 20
        NSAlternateKeyMask = 1 << 19
        NSShiftKeyMask = 1 << 17
        NSControlKeyMask = 1 << 18
        NSCapsLockKeyMask = 1 << 16

        # 检测哪个修饰键被按下
        if modifier_flags & NSCommandKeyMask:
            return "cmd"
        elif modifier_flags & NSAlternateKeyMask:
            return "alt"
        elif modifier_flags & NSShiftKeyMask:
            return "shift"
        elif modifier_flags & NSControlKeyMask:
            return "ctrl"
        elif modifier_flags & NSCapsLockKeyMask:
            return "caps_lock"
        else:
            return "modifier"

    def is_special_key(self, key_data: dict) -> bool:
        """判断是否为特殊键（需要记录）"""
        special_keys = {
            'enter', 'space', 'tab', 'backspace', 'delete',
            'up', 'down', 'left', 'right',
            'home', 'end', 'page_up', 'page_down',
            'f1', 'f2', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8', 'f9', 'f10', 'f11', 'f12',
            'esc', 'caps_lock', 'num_lock', 'scroll_lock',
            'insert', 'print_screen', 'pause'
        }

        key = key_data.get("key", "").lower()
        return (
            key in special_keys or
            len(key_data.get("modifiers", [])) > 0 or
            key_data.get("key_type") == "special"
        )

    def get_stats(self) -> dict:
        """获取捕获统计信息"""
        stats = {
            "is_running": self.is_running,
            "buffer_size": len(self._key_buffer),
            "queue_size": self.event_queue.qsize(),
            "last_key_time": self._last_key_time,
            "implementation": "PyObjC NSEvent"
        }

        if not PYOBJC_AVAILABLE:
            stats["status"] = "pyobjc_not_available"
            stats["message"] = "请运行: uv add pyobjc-framework-Cocoa"

        return stats
