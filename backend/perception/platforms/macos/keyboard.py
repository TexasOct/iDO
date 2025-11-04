"""
macOS keyboard event capture (using PyObjC)
Uses NSEvent global monitor to capture keyboard input

Solution:
Use PyObjC's NSEvent.addGlobalMonitorForEventsMatchingMask_handler_
instead of pynput, to avoid TSMGetInputSourceProperty crashes in background threads.

Notes:
1. Need to grant accessibility permissions in System Preferences -> Security & Privacy -> Accessibility
2. NSEvent monitor runs in macOS main event loop, avoiding thread conflicts
3. Use thread-safe queue to pass events between Cocoa and Python async code
"""

import sys
import threading
from datetime import datetime
from typing import Optional, Callable, Dict, Any
from queue import Queue
from core.models import RawRecord, RecordType
from core.logger import get_logger
from perception.base import BaseKeyboardMonitor

logger = get_logger(__name__)

# Only import PyObjC on macOS
if sys.platform == "darwin":
    try:
        from AppKit import NSEvent, NSKeyDownMask, NSKeyUpMask, NSFlagsChangedMask
        from PyObjCTools import AppHelper

        PYOBJC_AVAILABLE = True
    except ImportError:
        PYOBJC_AVAILABLE = False
        logger.warning("PyObjC not installed, macOS keyboard listening unavailable")
        logger.warning("Please run: uv add pyobjc-framework-Cocoa")
else:
    PYOBJC_AVAILABLE = False


class MacOSKeyboardMonitor(BaseKeyboardMonitor):
    """macOS keyboard event capturer (using PyObjC)"""

    def __init__(self, on_event: Optional[Callable[[RawRecord], None]] = None):
        super().__init__(on_event)
        self.event_queue: Queue = Queue()
        self.monitor = None
        self.processing_thread: Optional[threading.Thread] = None
        self._last_key_time = 0
        self._key_buffer = []
        self._buffer_timeout = 0.1  # Keys within 100ms will be merged

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
        if not PYOBJC_AVAILABLE:
            logger.error("PyObjC unavailable, cannot start macOS keyboard listening")
            logger.info("Please run: uv add pyobjc-framework-Cocoa")
            return

        if self.is_running:
            logger.warning("macOS keyboard listener is already running")
            return

        try:
            self.is_running = True

            # Create global event listener
            mask = NSKeyDownMask | NSKeyUpMask | NSFlagsChangedMask
            self.monitor = NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(
                mask, self._event_handler
            )

            # Start event processing thread
            self.processing_thread = threading.Thread(
                target=self._process_events, daemon=True
            )
            self.processing_thread.start()

            logger.info("✅ macOS keyboard listener started (using PyObjC NSEvent)")
            logger.info(
                "   If unable to capture keys, check System Preferences -> Security & Privacy -> Accessibility"
            )

        except Exception as e:
            self.is_running = False
            logger.error(f"Failed to start macOS keyboard listener: {e}")
            raise

    def stop(self):
        """Stop keyboard listening"""
        if not self.is_running:
            return

        self.is_running = False

        try:
            # Remove global monitor
            if self.monitor and PYOBJC_AVAILABLE:
                NSEvent.removeMonitor_(self.monitor)
                self.monitor = None

            # Wait for processing thread to end
            if self.processing_thread and self.processing_thread.is_alive():
                logger.debug("Waiting for keyboard processing thread to end...")
                self.processing_thread.join(timeout=3.0)
                if self.processing_thread.is_alive():
                    logger.warning(
                        "Keyboard processing thread did not end within timeout, but continuing"
                    )
                self.processing_thread = None

            # Clear event queue
            while not self.event_queue.empty():
                try:
                    self.event_queue.get_nowait()
                except:
                    break

            logger.info("macOS keyboard listener stopped")

        except Exception as e:
            logger.error(f"Failed to stop macOS keyboard listener: {e}")

    def _event_handler(self, event):
        """NSEvent callback handler (runs in Cocoa main thread)"""
        try:
            # Extract event data
            event_type = event.type()
            modifiers = event.modifierFlags()

            # Determine action type
            if event_type == 10:  # NSKeyDown
                action = "press"
            elif event_type == 11:  # NSKeyUp
                action = "release"
            elif event_type == 12:  # NSFlagsChanged
                action = "modifier"
            else:
                action = "unknown"

            # Build event data
            key_data = {
                "action": action,
                "modifiers": self._extract_modifiers(modifiers),
                "timestamp": datetime.now().isoformat(),
            }

            # Add key code and character information (NSFlagsChanged events have no keyCode and characters)
            if event_type == 12:  # NSFlagsChanged
                # Modifier key event, infer key from modifiers
                key_data["key_code"] = 0
                key_data["key"] = self._get_modifier_key_name(modifiers)
                key_data["key_type"] = "modifier"
            else:
                # Normal key event
                key_code = event.keyCode()
                key_data["key_code"] = key_code

                # Try to get characters (only KeyDown/KeyUp have characters)
                try:
                    characters = event.characters()
                    if characters and len(characters) > 0:
                        key_data["key"] = characters
                        key_data["key_type"] = "char"
                    else:
                        key_data["key"] = self._get_special_key_name(key_code)
                        key_data["key_type"] = "special"
                except (AttributeError, RuntimeError):
                    # Some events don't have characters method
                    key_data["key"] = self._get_special_key_name(key_code)
                    key_data["key_type"] = "special"

            # Put event into queue (thread-safe)
            record = RawRecord(
                timestamp=datetime.now(), type=RecordType.KEYBOARD_RECORD, data=key_data
            )
            self.event_queue.put(record)

        except Exception as e:
            logger.error(f"Failed to process NSEvent: {e}")

    def _process_events(self):
        """Event processing thread (process events in queue in background)"""
        import time

        while self.is_running:
            try:
                # Get event from queue (non-blocking)
                if not self.event_queue.empty():
                    record = self.event_queue.get(timeout=0.1)
                    current_time = time.time()

                    # Check if keys need to be merged (rapid consecutive keys)
                    if current_time - self._last_key_time < self._buffer_timeout:
                        self._key_buffer.append(record)
                    else:
                        # Output previous buffered data
                        self.output()
                        # Add new event
                        self._key_buffer.append(record)

                    self._last_key_time = current_time
                else:
                    # Brief sleep when no events
                    time.sleep(0.01)
            except Exception as e:
                if self.is_running:
                    logger.error(f"Failed to handle keyboard event: {e}")

        # Output remaining buffer before thread exit
        self.output()

    def _extract_modifiers(self, modifier_flags: int) -> list:
        """Extract modifier list from modifier flags"""
        modifiers = []

        # NSEvent modifier flag bits
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
        """Get special key name from key code"""
        # macOS key code mapping (common special keys)
        key_map = {
            36: "enter",
            49: "space",
            48: "tab",
            51: "backspace",
            53: "esc",
            117: "delete",
            122: "f1",
            120: "f2",
            99: "f3",
            118: "f4",
            96: "f5",
            97: "f6",
            98: "f7",
            100: "f8",
            101: "f9",
            109: "f10",
            103: "f11",
            111: "f12",
            123: "left",
            124: "right",
            125: "down",
            126: "up",
            115: "home",
            119: "end",
            116: "page_up",
            121: "page_down",
        }

        return key_map.get(key_code, f"key_{key_code}")

    def _get_modifier_key_name(self, modifier_flags: int) -> str:
        """Get key name from modifier flags (for NSFlagsChanged events)"""
        # NSEvent modifier flag bits
        NSCommandKeyMask = 1 << 20
        NSAlternateKeyMask = 1 << 19
        NSShiftKeyMask = 1 << 17
        NSControlKeyMask = 1 << 18
        NSCapsLockKeyMask = 1 << 16

        # Detect which modifier key is pressed
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
        """Determine if it's a special key (needs to be recorded)"""
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
        }

        key = key_data.get("key", "").lower()
        return (
            key in special_keys
            or len(key_data.get("modifiers", [])) > 0
            or key_data.get("key_type") == "special"
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get capture statistics"""
        stats = {
            "is_running": self.is_running and PYOBJC_AVAILABLE,
            "platform": "macOS",
            "implementation": "PyObjC NSEvent",
            "buffer_size": len(self._key_buffer),
            "queue_size": self.event_queue.qsize(),
            "last_key_time": self._last_key_time,
        }

        if not PYOBJC_AVAILABLE:
            stats["status"] = "pyobjc_not_available"
            stats["message"] = "Please run: uv add pyobjc-framework-Cocoa"

        return stats
