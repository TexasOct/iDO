"""
macOS 鼠标事件捕获
使用 pynput 库监控鼠标操作（pynput的鼠标监听在macOS上是安全的）
"""

import time
from datetime import datetime
from typing import Optional, Callable, Tuple, Dict, Any
from pynput import mouse
from core.models import RawRecord, RecordType
from core.logger import get_logger
from perception.base import BaseMouseMonitor

logger = get_logger(__name__)


class MacOSMouseMonitor(BaseMouseMonitor):
    """macOS 鼠标事件捕获器（使用 pynput）"""

    def __init__(self, on_event: Optional[Callable[[RawRecord], None]] = None):
        super().__init__(on_event)
        self.listener: Optional[mouse.Listener] = None
        self._last_click_time = 0
        self._last_scroll_time = 0
        self._scroll_buffer = []
        self._click_timeout = 0.5  # 500ms 内的点击会被合并
        self._scroll_timeout = 0.1  # 100ms 内的滚动会被合并
        self._last_position = (0, 0)
        self._is_dragging = False
        self._drag_start_pos = None
        self._drag_start_time = None

    def capture(self) -> RawRecord:
        """捕获鼠标事件（同步方法，用于测试）"""
        return RawRecord(
            timestamp=datetime.now(),
            type=RecordType.MOUSE_RECORD,
            data={
                "action": "click",
                "button": "left",
                "position": (100, 100),
                "modifiers": []
            }
        )

    def output(self) -> None:
        """输出处理后的数据"""
        if self.on_event:
            for record in self._scroll_buffer:
                self.on_event(record)
        self._scroll_buffer.clear()

    def start(self):
        """开始鼠标监听"""
        if self.is_running:
            logger.warning("macOS 鼠标监听已在运行中")
            return

        self.is_running = True
        self.listener = mouse.Listener(
            on_move=self._on_move,
            on_click=self._on_click,
            on_scroll=self._on_scroll
        )
        self.listener.start()
        logger.info("✅ macOS 鼠标监听已启动（使用 pynput）")

    def stop(self):
        """停止鼠标监听"""
        if not self.is_running:
            return

        self.is_running = False
        if self.listener:
            try:
                self.listener.stop()
                # 等待 listener 线程真正结束，带更长的超时时间
                if hasattr(self.listener, '_thread') and self.listener._thread:
                    logger.debug("等待鼠标监听线程结束...")
                    self.listener._thread.join(timeout=3.0)
                    if self.listener._thread.is_alive():
                        logger.warning("鼠标监听线程未能在超时内结束，但继续进行")
                self.listener = None
                logger.info("macOS 鼠标监听已停止")
            except Exception as e:
                logger.error(f"停止鼠标监听失败: {e}")
                self.listener = None

    def _on_move(self, x: int, y: int):
        """处理鼠标移动事件"""
        if not self.is_running:
            return

        try:
            self._last_position = (x, y)

            # 如果正在拖拽，记录拖拽事件
            if self._is_dragging and self._drag_start_pos:
                current_time = time.time()
                if current_time - self._drag_start_time > 0.1:  # 拖拽超过100ms才记录
                    drag_data = {
                        "action": "drag",
                        "start_position": self._drag_start_pos,
                        "current_position": (x, y),
                        "duration": current_time - self._drag_start_time,
                        "timestamp": datetime.now().isoformat()
                    }

                    record = RawRecord(
                        timestamp=datetime.now(),
                        type=RecordType.MOUSE_RECORD,
                        data=drag_data
                    )

                    if self.on_event:
                        self.on_event(record)

                    # 更新拖拽开始位置，避免重复记录
                    self._drag_start_pos = (x, y)
                    self._drag_start_time = current_time

        except Exception as e:
            logger.error(f"处理鼠标移动事件失败: {e}")

    def _on_click(self, x: int, y: int, button: mouse.Button, pressed: bool):
        """处理鼠标点击事件"""
        if not self.is_running:
            return

        try:
            current_time = time.time()
            button_name = button.name if hasattr(button, 'name') else str(button)

            if pressed:
                # 鼠标按下
                self._last_click_time = current_time
                self._is_dragging = True
                self._drag_start_pos = (x, y)
                self._drag_start_time = current_time

                click_data = {
                    "action": "press",
                    "button": button_name,
                    "position": (x, y),
                    "timestamp": datetime.now().isoformat()
                }

            else:
                # 鼠标释放
                self._is_dragging = False

                # 判断是点击还是拖拽
                if (self._drag_start_pos and
                    current_time - self._drag_start_time > 0.1 and
                    self._distance(self._drag_start_pos, (x, y)) > 5):
                    # 拖拽结束
                    click_data = {
                        "action": "drag_end",
                        "button": button_name,
                        "start_position": self._drag_start_pos,
                        "end_position": (x, y),
                        "duration": current_time - self._drag_start_time,
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    # 普通点击
                    click_data = {
                        "action": "release",
                        "button": button_name,
                        "position": (x, y),
                        "timestamp": datetime.now().isoformat()
                    }

                self._drag_start_pos = None
                self._drag_start_time = None

            record = RawRecord(
                timestamp=datetime.now(),
                type=RecordType.MOUSE_RECORD,
                data=click_data
            )

            if self.on_event:
                self.on_event(record)

        except Exception as e:
            logger.error(f"处理鼠标点击事件失败: {e}")

    def _on_scroll(self, x: int, y: int, dx: int, dy: int):
        """处理鼠标滚动事件"""
        if not self.is_running:
            return

        try:
            current_time = time.time()

            # 合并连续的滚动事件
            if (current_time - self._last_scroll_time < self._scroll_timeout and
                self._scroll_buffer):
                # 合并到最后一个滚动事件
                last_record = self._scroll_buffer[-1]
                last_data = last_record.data
                last_data["dy"] += dy
                last_data["dx"] += dx
                last_data["end_position"] = (x, y)
            else:
                # 创建新的滚动事件
                scroll_data = {
                    "action": "scroll",
                    "position": (x, y),
                    "dx": dx,
                    "dy": dy,
                    "timestamp": datetime.now().isoformat()
                }

                record = RawRecord(
                    timestamp=datetime.now(),
                    type=RecordType.MOUSE_RECORD,
                    data=scroll_data
                )

                self._scroll_buffer.append(record)

            self._last_scroll_time = current_time

            # 定期输出滚动事件
            if len(self._scroll_buffer) >= 5 or current_time - self._last_scroll_time > 1.0:
                self.output()

        except Exception as e:
            logger.error(f"处理鼠标滚动事件失败: {e}")

    def _distance(self, pos1: Tuple[int, int], pos2: Tuple[int, int]) -> float:
        """计算两点之间的距离"""
        return ((pos1[0] - pos2[0]) ** 2 + (pos1[1] - pos2[1]) ** 2) ** 0.5

    def is_important_event(self, event_data: dict) -> bool:
        """判断是否为重要事件（需要记录）"""
        action = event_data.get("action", "")
        return action in ["press", "release", "drag", "drag_end", "scroll"]

    def get_stats(self) -> Dict[str, Any]:
        """获取捕获统计信息"""
        return {
            "is_running": self.is_running,
            "platform": "macOS",
            "implementation": "pynput",
            "last_position": self._last_position,
            "is_dragging": self._is_dragging,
            "scroll_buffer_size": len(self._scroll_buffer),
            "last_click_time": self._last_click_time,
            "last_scroll_time": self._last_scroll_time
        }
