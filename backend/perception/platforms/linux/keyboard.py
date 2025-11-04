"""
Linux keyboard event capture
Monitor keyboard input using pynput library

TODO: Consider using X11 or evdev for more native monitoring in the future
"""

from datetime import datetime
from typing import Optional, Callable, Dict, Any
from pynput import keyboard
from core.models import RawRecord, RecordType
from core.logger import get_logger
from perception.base import BaseKeyboardMonitor

logger = get_logger(__name__)


class LinuxKeyboardMonitor(BaseKeyboardMonitor):
    """Linux keyboard event capturer (using pynput)"""

    def __init__(self, on_event: Optional[Callable[[RawRecord], None]] = None):
        super().__init__(on_event)
        self.listener: Optional[keyboard.Listener] = None
        self._key_buffer = []
        self._last_key_time = 0
        self._buffer_timeout = 0.1

    def capture(self) -> RawRecord:
        """Capture keyboard event (sync method, for testing)"""
        return RawRecord(
            timestamp=datetime.now(),
            type=RecordType.KEYBOARD_RECORD,
            data={"key": "test_key", "action": "press", "modifiers": []},
        )

    def output(self) -> None:
        """Output processed data"""
        if self.on_event:
            for record in self._key_buffer:
                self.on_event(record)
        self._key_buffer.clear()

    def start(self):
        """Start keyboard listening"""
        if self.is_running:
            logger.warning("Linux keyboard listener is already running")
            return

        try:
            self.is_running = True
            self.listener = keyboard.Listener(
                on_press=self._on_press, on_release=self._on_release
            )
            self.listener.start()
            logger.info("✅ Linux keyboard listener started (using pynput)")
            logger.info("   Ensure your user has permission to access input devices")

        except Exception as e:
            self.is_running = False
            logger.error(f"Failed to start Linux keyboard listener: {e}")
            raise

    def stop(self):
        """Stop keyboard listening"""
        if not self.is_running:
            return

        self.is_running = False
        if self.listener:
            try:
                self.listener.stop()
                if hasattr(self.listener, "_thread") and self.listener._thread:
                    self.listener._thread.join(timeout=3.0)
                self.listener = None
                logger.info("Linux keyboard listener stopped")
            except Exception as e:
                logger.error(f"Failed to stop Linux keyboard listener: {e}")

    def _on_press(self, key):
        """Handle key press event"""
        if not self.is_running:
            return

        try:
            key_data = self._extract_key_data(key, "press")
            record = RawRecord(
                timestamp=datetime.now(), type=RecordType.KEYBOARD_RECORD, data=key_data
            )

            if self.on_event:
                self.on_event(record)

        except Exception as e:
            logger.error(f"Failed to handle key event: {e}")

    def _on_release(self, key):
        """Handle key release event"""
        if not self.is_running:
            return

        try:
            key_data = self._extract_key_data(key, "release")
            record = RawRecord(
                timestamp=datetime.now(), type=RecordType.KEYBOARD_RECORD, data=key_data
            )

            if self.on_event:
                self.on_event(record)

        except Exception as e:
            logger.error(f"Failed to handle key release event: {e}")

    def _extract_key_data(self, key, action: str) -> dict:
        """Extract key data"""
        try:
            # Try to get character
            if hasattr(key, "char") and key.char is not None:
                key_name = key.char
                key_type = "char"
            else:
                # Special key
                key_name = str(key).replace("Key.", "")
                key_type = "special"

            return {
                "key": key_name,
                "key_type": key_type,
                "action": action,
                "modifiers": [],  # pynput doesn't directly provide current modifier key state
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Failed to extract key data: {e}")
            return {
                "key": "unknown",
                "action": action,
                "modifiers": [],
                "timestamp": datetime.now().isoformat(),
            }

    def is_special_key(self, key_data: dict) -> bool:
        """Determine if this is a special key (needs to be recorded)"""
        special_keys = {
            "enter",
            "space",
            "tab",
            "backspace",
            "delete",
            "up",
            "down",
            "left",
            "right",
            "home",
            "end",
            "page_up",
            "page_down",
            "f1",
            "f2",
            "f3",
            "f4",
            "f5",
            "f6",
            "f7",
            "f8",
            "f9",
            "f10",
            "f11",
            "f12",
            "esc",
            "caps_lock",
            "num_lock",
            "scroll_lock",
            "insert",
            "print_screen",
            "pause",
            "cmd",
            "alt",
            "ctrl",
            "shift",
            "super",  # Linux uses 'super' instead of Windows key
        }

        key = key_data.get("key", "").lower()
        return key in special_keys or key_data.get("key_type") == "special"

    def get_stats(self) -> Dict[str, Any]:
        """Get capture statistics"""
        return {
            "is_running": self.is_running,
            "platform": "Linux",
            "implementation": "pynput",
            "buffer_size": len(self._key_buffer),
            "last_key_time": self._last_key_time,
        }
