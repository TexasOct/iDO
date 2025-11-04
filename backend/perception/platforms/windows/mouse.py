"""
Windows mouse event capture
Using pynput library to monitor mouse operations

TODO: Consider using Windows API (pywin32) in the future for more native monitoring
"""

import time
from datetime import datetime
from typing import Optional, Callable, Tuple, Dict, Any
from pynput import mouse
from core.models import RawRecord, RecordType
from core.logger import get_logger
from perception.base import BaseMouseMonitor

logger = get_logger(__name__)


class WindowsMouseMonitor(BaseMouseMonitor):
    """Windows mouse event capturer (using pynput)"""

    def __init__(self, on_event: Optional[Callable[[RawRecord], None]] = None):
        super().__init__(on_event)
        self.listener: Optional[mouse.Listener] = None
        self._last_click_time = 0
        self._last_scroll_time = 0
        self._scroll_buffer = []
        self._click_timeout = 0.5
        self._scroll_timeout = 0.1
        self._last_position = (0, 0)
        self._is_dragging = False
        self._drag_start_pos = None
        self._drag_start_time = None

    def capture(self) -> RawRecord:
        """Capture mouse event (synchronous method, for testing)"""
        return RawRecord(
            timestamp=datetime.now(),
            type=RecordType.MOUSE_RECORD,
            data={
                "action": "click",
                "button": "left",
                "position": (100, 100),
                "modifiers": [],
            },
        )

    def output(self) -> None:
        """Output processed data"""
        if self.on_event:
            for record in self._scroll_buffer:
                self.on_event(record)
        self._scroll_buffer.clear()

    def start(self):
        """Start mouse listening"""
        if self.is_running:
            logger.warning("Windows mouse listener is already running")
            return

        self.is_running = True
        self.listener = mouse.Listener(
            on_move=self._on_move, on_click=self._on_click, on_scroll=self._on_scroll
        )
        self.listener.start()
        logger.info("✅ Windows mouse listener started (using pynput)")

    def stop(self):
        """Stop mouse listening"""
        if not self.is_running:
            return

        self.is_running = False
        if self.listener:
            try:
                self.listener.stop()
                if hasattr(self.listener, "_thread") and self.listener._thread:
                    self.listener._thread.join(timeout=3.0)
                self.listener = None
                logger.info("Windows mouse listener stopped")
            except Exception as e:
                logger.error(f"Failed to stop mouse listener: {e}")
                self.listener = None

    def _on_move(self, x: int, y: int):
        """Handle mouse move event"""
        if not self.is_running:
            return

        try:
            self._last_position = (x, y)

            if self._is_dragging and self._drag_start_pos:
                current_time = time.time()
                if current_time - self._drag_start_time > 0.1:
                    drag_data = {
                        "action": "drag",
                        "start_position": self._drag_start_pos,
                        "current_position": (x, y),
                        "duration": current_time - self._drag_start_time,
                        "timestamp": datetime.now().isoformat(),
                    }

                    record = RawRecord(
                        timestamp=datetime.now(),
                        type=RecordType.MOUSE_RECORD,
                        data=drag_data,
                    )

                    if self.on_event:
                        self.on_event(record)

                    self._drag_start_pos = (x, y)
                    self._drag_start_time = current_time

        except Exception as e:
            logger.error(f"Failed to handle mouse move event: {e}")

    def _on_click(self, x: int, y: int, button: mouse.Button, pressed: bool):
        """Handle mouse click event"""
        if not self.is_running:
            return

        try:
            current_time = time.time()
            button_name = button.name if hasattr(button, "name") else str(button)

            if pressed:
                self._last_click_time = current_time
                self._is_dragging = True
                self._drag_start_pos = (x, y)
                self._drag_start_time = current_time

                click_data = {
                    "action": "press",
                    "button": button_name,
                    "position": (x, y),
                    "timestamp": datetime.now().isoformat(),
                }
            else:
                self._is_dragging = False

                if (
                    self._drag_start_pos
                    and current_time - self._drag_start_time > 0.1
                    and self._distance(self._drag_start_pos, (x, y)) > 5
                ):
                    click_data = {
                        "action": "drag_end",
                        "button": button_name,
                        "start_position": self._drag_start_pos,
                        "end_position": (x, y),
                        "duration": current_time - self._drag_start_time,
                        "timestamp": datetime.now().isoformat(),
                    }
                else:
                    click_data = {
                        "action": "release",
                        "button": button_name,
                        "position": (x, y),
                        "timestamp": datetime.now().isoformat(),
                    }

                self._drag_start_pos = None
                self._drag_start_time = None

            record = RawRecord(
                timestamp=datetime.now(), type=RecordType.MOUSE_RECORD, data=click_data
            )

            if self.on_event:
                self.on_event(record)

        except Exception as e:
            logger.error(f"Failed to handle mouse click event: {e}")

    def _on_scroll(self, x: int, y: int, dx: int, dy: int):
        """Handle mouse scroll event"""
        if not self.is_running:
            return

        try:
            current_time = time.time()

            if (
                current_time - self._last_scroll_time < self._scroll_timeout
                and self._scroll_buffer
            ):
                last_record = self._scroll_buffer[-1]
                last_data = last_record.data
                last_data["dy"] += dy
                last_data["dx"] += dx
                last_data["end_position"] = (x, y)
            else:
                scroll_data = {
                    "action": "scroll",
                    "position": (x, y),
                    "dx": dx,
                    "dy": dy,
                    "timestamp": datetime.now().isoformat(),
                }

                record = RawRecord(
                    timestamp=datetime.now(),
                    type=RecordType.MOUSE_RECORD,
                    data=scroll_data,
                )

                self._scroll_buffer.append(record)

            self._last_scroll_time = current_time

            if (
                len(self._scroll_buffer) >= 5
                or current_time - self._last_scroll_time > 1.0
            ):
                self.output()

        except Exception as e:
            logger.error(f"Failed to handle mouse scroll event: {e}")

    def _distance(self, pos1: Tuple[int, int], pos2: Tuple[int, int]) -> float:
        """Calculate distance between two points"""
        return ((pos1[0] - pos2[0]) ** 2 + (pos1[1] - pos2[1]) ** 2) ** 0.5

    def is_important_event(self, event_data: dict) -> bool:
        """Determine if it's an important event (needs to be recorded)"""
        action = event_data.get("action", "")
        return action in ["press", "release", "drag", "drag_end", "scroll"]

    def get_stats(self) -> Dict[str, Any]:
        """Get capture statistics"""
        return {
            "is_running": self.is_running,
            "platform": "Windows",
            "implementation": "pynput",
            "last_position": self._last_position,
            "is_dragging": self._is_dragging,
            "scroll_buffer_size": len(self._scroll_buffer),
            "last_click_time": self._last_click_time,
            "last_scroll_time": self._last_scroll_time,
        }
