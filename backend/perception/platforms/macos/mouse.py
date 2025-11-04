"""
macOS mouse event capture
Using pynput library to monitor mouse operations (pynput mouse listening is safe on macOS)
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
    """macOS mouse event capturer (using pynput)"""

    def __init__(self, on_event: Optional[Callable[[RawRecord], None]] = None):
        super().__init__(on_event)
        self.listener: Optional[mouse.Listener] = None
        self._last_click_time = 0
        self._last_scroll_time = 0
        self._scroll_buffer = []
        self._click_timeout = 0.5  # Clicks within 500ms will be merged
        self._scroll_timeout = 0.1  # Scrolls within 100ms will be merged
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
            logger.warning("macOS mouse listener is already running")
            return

        self.is_running = True
        self.listener = mouse.Listener(
            on_move=self._on_move, on_click=self._on_click, on_scroll=self._on_scroll
        )
        self.listener.start()
        logger.info("✅ macOS mouse listener started (using pynput)")

    def stop(self):
        """Stop mouse listening"""
        if not self.is_running:
            return

        self.is_running = False
        if self.listener:
            try:
                self.listener.stop()
                # Wait for listener thread to truly end, with longer timeout
                if hasattr(self.listener, "_thread") and self.listener._thread:
                    logger.debug("Waiting for mouse listener thread to end...")
                    self.listener._thread.join(timeout=3.0)
                    if self.listener._thread.is_alive():
                        logger.warning(
                            "Mouse listener thread did not end within timeout, but continuing"
                        )
                self.listener = None
                logger.info("macOS mouse listener stopped")
            except Exception as e:
                logger.error(f"Failed to stop mouse listener: {e}")
                self.listener = None

    def _on_move(self, x: int, y: int):
        """Handle mouse move event"""
        if not self.is_running:
            return

        try:
            self._last_position = (x, y)

            # Record drag event if dragging
            if self._is_dragging and self._drag_start_pos:
                current_time = time.time()
                if (
                    current_time - self._drag_start_time > 0.1
                ):  # Only record if drag exceeds 100ms
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

                    # Update drag start position to avoid duplicate records
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
                # Mouse press down
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
                # Mouse release
                self._is_dragging = False

                # Determine if it's click or drag
                if (
                    self._drag_start_pos
                    and current_time - self._drag_start_time > 0.1
                    and self._distance(self._drag_start_pos, (x, y)) > 5
                ):
                    # Drag end
                    click_data = {
                        "action": "drag_end",
                        "button": button_name,
                        "position": (x, y),
                        "start_position": self._drag_start_pos,
                        "end_position": (x, y),
                        "duration": current_time - self._drag_start_time,
                        "timestamp": datetime.now().isoformat(),
                    }
                else:
                    # Normal click
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
            self._last_scroll_time = current_time

            # Merge consecutive scroll events
            if (
                current_time - self._last_scroll_time < self._scroll_timeout
                and self._scroll_buffer
            ):
                # Merge to last scroll event
                last_record = self._scroll_buffer[-1]
                last_data = last_record.data
                dy += last_data.get("dy", 0)

                # Update last scroll event
                last_data["dy"] = dy
            else:
                # New scroll event
                scroll_data = {
                    "action": "scroll",
                    "button": "middle",
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

            # Periodically output scroll events
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
            "platform": "macOS",
            "implementation": "pynput",
            "last_position": self._last_position,
            "is_dragging": self._is_dragging,
            "scroll_buffer_size": len(self._scroll_buffer),
            "last_click_time": self._last_click_time,
            "last_scroll_time": self._last_scroll_time,
        }
