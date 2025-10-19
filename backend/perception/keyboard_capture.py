"""
键盘事件捕获
使用 pynput 库监控键盘输入
"""

import time
from datetime import datetime
from typing import Optional, Callable
from pynput import keyboard
from core.models import RawRecord, RecordType
from core.logger import get_logger
from .base import BaseCapture

logger = get_logger(__name__)


class KeyboardCapture(BaseCapture):
    """键盘事件捕获器"""
    
    def __init__(self, on_event: Optional[Callable[[RawRecord], None]] = None):
        super().__init__()
        self.on_event = on_event
        self.listener: Optional[keyboard.Listener] = None
        self._last_key_time = 0
        self._key_buffer = []
        self._buffer_timeout = 0.1  # 100ms 内的按键会被合并
        
    def capture(self) -> RawRecord:
        """捕获键盘事件（同步方法，用于测试）"""
        # 这个方法主要用于测试，实际使用中通过监听器异步捕获
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
        """开始键盘监听"""
        if self.is_running:
            logger.warning("键盘监听已在运行中")
            return
        
        self.is_running = True
        self.listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release
        )
        self.listener.start()
        logger.info("键盘监听已启动")
    
    def stop(self):
        """停止键盘监听"""
        if not self.is_running:
            return
        
        self.is_running = False
        if self.listener:
            self.listener.stop()
            self.listener = None
        logger.info("键盘监听已停止")
    
    def _on_press(self, key):
        """处理按键按下事件"""
        if not self.is_running:
            return
        
        try:
            current_time = time.time()
            key_data = self._extract_key_data(key, "press")
            
            # 检查是否需要合并按键（快速连续按键）
            if current_time - self._last_key_time < self._buffer_timeout:
                self._key_buffer.append(RawRecord(
                    timestamp=datetime.now(),
                    type=RecordType.KEYBOARD_RECORD,
                    data=key_data
                ))
            else:
                # 输出之前的缓冲数据
                self.output()
                # 添加新事件
                self._key_buffer.append(RawRecord(
                    timestamp=datetime.now(),
                    type=RecordType.KEYBOARD_RECORD,
                    data=key_data
                ))
            
            self._last_key_time = current_time
            
        except Exception as e:
            logger.error(f"处理按键按下事件失败: {e}")
    
    def _on_release(self, key):
        """处理按键释放事件"""
        if not self.is_running:
            return
        
        try:
            # 只处理特殊键的释放事件（如 Ctrl, Alt, Shift）
            if hasattr(key, 'char') and key.char is not None:
                return  # 普通字符的释放事件忽略
            
            key_data = self._extract_key_data(key, "release")
            self._key_buffer.append(RawRecord(
                timestamp=datetime.now(),
                type=RecordType.KEYBOARD_RECORD,
                data=key_data
            ))
            
        except Exception as e:
            logger.error(f"处理按键释放事件失败: {e}")
    
    def _extract_key_data(self, key, action: str) -> dict:
        """提取按键数据"""
        key_data = {
            "action": action,
            "modifiers": [],
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            if hasattr(key, 'char') and key.char is not None:
                # 普通字符
                key_data["key"] = key.char
                key_data["key_type"] = "char"
            elif hasattr(key, 'name'):
                # 特殊键
                key_data["key"] = key.name
                key_data["key_type"] = "special"
            else:
                # 未知键
                key_data["key"] = str(key)
                key_data["key_type"] = "unknown"
            
            # 检查修饰键
            if hasattr(key, 'ctrl') and key.ctrl:
                key_data["modifiers"].append("ctrl")
            if hasattr(key, 'alt') and key.alt:
                key_data["modifiers"].append("alt")
            if hasattr(key, 'shift') and key.shift:
                key_data["modifiers"].append("shift")
            if hasattr(key, 'cmd') and key.cmd:
                key_data["modifiers"].append("cmd")
            
        except Exception as e:
            logger.error(f"提取按键数据失败: {e}")
            key_data["key"] = "unknown"
            key_data["key_type"] = "error"
        
        return key_data
    
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
        return {
            "is_running": self.is_running,
            "buffer_size": len(self._key_buffer),
            "last_key_time": self._last_key_time
        }
