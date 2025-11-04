"""
Asynchronous task manager
Responsible for coordinating asynchronous collection of keyboard, mouse, and screenshot data

Uses factory pattern to create platform-specific monitors
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from core.logger import get_logger
from .factory import create_keyboard_monitor, create_mouse_monitor
from .screenshot_capture import ScreenshotCapture
from .storage import SlidingWindowStorage, EventBuffer
from .screen_state_monitor import create_screen_state_monitor
from core.models import RawRecord

logger = get_logger(__name__)


class PerceptionManager:
    """Perception layer manager"""

    def __init__(
        self,
        capture_interval: float = 1.0,
        window_size: int = 20,
        on_data_captured: Optional[Callable[[RawRecord], None]] = None,
    ):
        """
        Initialize perception manager

        Args:
            capture_interval: Screenshot capture interval (seconds)
            window_size: Sliding window size (seconds)
            on_data_captured: Data capture callback function
        """
        self.capture_interval = capture_interval
        self.window_size = window_size
        self.on_data_captured = on_data_captured

        # Use factory pattern to create platform-specific monitors
        self.keyboard_capture = create_keyboard_monitor(self._on_keyboard_event)
        self.mouse_capture = create_mouse_monitor(self._on_mouse_event)
        self.screenshot_capture = ScreenshotCapture(self._on_screenshot_event)

        # Initialize storage
        self.storage = SlidingWindowStorage(window_size)
        self.event_buffer = EventBuffer()

        # Running state
        self.is_running = False
        self.is_paused = False  # Pause state (when screen is off)
        self.tasks: Dict[str, asyncio.Task] = {}

        # Screen state monitor
        self.screen_state_monitor = create_screen_state_monitor(
            on_screen_lock=self._on_screen_lock, on_screen_unlock=self._on_screen_unlock
        )

    def _on_screen_lock(self) -> None:
        """Screen lock/system sleep callback"""
        if not self.is_running:
            return

        logger.info("Screen locked/system sleeping, pausing perception")
        self.is_paused = True

        # Pause each capturer
        try:
            self.keyboard_capture.stop()
            self.mouse_capture.stop()
            self.screenshot_capture.stop()
            logger.debug("All capturers paused")
        except Exception as e:
            logger.error(f"Failed to pause capturers: {e}")

    def _on_screen_unlock(self) -> None:
        """Screen unlock/system wake callback"""
        if not self.is_running or not self.is_paused:
            return

        logger.info("Screen unlocked/system woke up, resuming perception")
        self.is_paused = False

        # Resume each capturer
        try:
            self.keyboard_capture.start()
            self.mouse_capture.start()
            self.screenshot_capture.start()
            logger.debug("All capturers resumed")
        except Exception as e:
            logger.error(f"Failed to resume capturers: {e}")

    def _on_keyboard_event(self, record: RawRecord) -> None:
        """Keyboard event callback"""
        # Don't process events when paused
        if self.is_paused:
            return

        try:
            # Record all keyboard events for subsequent processing to preserve usage context
            self.storage.add_record(record)
            self.event_buffer.add(record)

            if self.on_data_captured:
                self.on_data_captured(record)

            logger.debug(
                f"Keyboard event recorded: {record.data.get('key', 'unknown')}"
            )
        except Exception as e:
            logger.error(f"Failed to process keyboard event: {e}")

    def _on_mouse_event(self, record: RawRecord) -> None:
        """Mouse event callback"""
        # Don't process events when paused
        if self.is_paused:
            return

        try:
            # Only record important mouse events
            if self.mouse_capture.is_important_event(record.data):
                self.storage.add_record(record)
                self.event_buffer.add(record)

                if self.on_data_captured:
                    self.on_data_captured(record)

                logger.debug(
                    f"Mouse event recorded: {record.data.get('action', 'unknown')}"
                )
        except Exception as e:
            logger.error(f"Failed to process mouse event: {e}")

    def _on_screenshot_event(self, record: RawRecord) -> None:
        """Screenshot event callback"""
        # Don't process events when paused
        if self.is_paused:
            return

        try:
            if record:  # Screenshot may be None (duplicate screenshots)
                self.storage.add_record(record)
                self.event_buffer.add(record)

                if self.on_data_captured:
                    self.on_data_captured(record)

                logger.debug(
                    f"Screenshot recorded: {record.data.get('width', 0)}x{record.data.get('height', 0)}"
                )
        except Exception as e:
            logger.error(f"Failed to process screenshot event: {e}")

    async def start(self) -> None:
        """Start perception manager"""
        from datetime import datetime

        if self.is_running:
            logger.warning("Perception manager is already running")
            return

        try:
            start_total = datetime.now()
            self.is_running = True
            self.is_paused = False

            # Start screen state monitor
            start_time = datetime.now()
            self.screen_state_monitor.start()
            logger.debug(
                f"Screen state monitor startup time: {(datetime.now() - start_time).total_seconds():.3f}s"
            )

            # Start each capturer
            start_time = datetime.now()
            self.keyboard_capture.start()
            logger.debug(
                f"Keyboard capture startup time: {(datetime.now() - start_time).total_seconds():.3f}s"
            )

            start_time = datetime.now()
            self.mouse_capture.start()
            logger.debug(
                f"Mouse capture startup time: {(datetime.now() - start_time).total_seconds():.3f}s"
            )

            start_time = datetime.now()
            self.screenshot_capture.start()
            logger.debug(
                f"Screenshot capture startup time: {(datetime.now() - start_time).total_seconds():.3f}s"
            )

            # Start async tasks
            start_time = datetime.now()
            self.tasks["screenshot_task"] = asyncio.create_task(self._screenshot_loop())
            self.tasks["cleanup_task"] = asyncio.create_task(self._cleanup_loop())
            logger.debug(
                f"Async task creation time: {(datetime.now() - start_time).total_seconds():.3f}s"
            )

            total_elapsed = (datetime.now() - start_total).total_seconds()
            logger.info(
                f"Perception manager started (total time: {total_elapsed:.3f}s, screen state monitoring enabled)"
            )

        except Exception as e:
            logger.error(f"Failed to start perception manager: {e}")
            await self.stop()
            raise

    async def stop(self) -> None:
        """Stop perception manager"""
        if not self.is_running:
            return

        try:
            self.is_running = False
            self.is_paused = False

            # Stop screen state monitor
            self.screen_state_monitor.stop()

            # Stop all capturers
            self.keyboard_capture.stop()
            self.mouse_capture.stop()
            self.screenshot_capture.stop()

            # Cancel async tasks
            for task_name, task in self.tasks.items():
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

            self.tasks.clear()

            logger.info("Perception manager stopped")

        except Exception as e:
            logger.error(f"Failed to stop perception manager: {e}")

    async def _screenshot_loop(self) -> None:
        """Screenshot loop task"""
        try:
            loop = asyncio.get_event_loop()
            while self.is_running:
                # Execute synchronous screenshot operation in thread pool to avoid blocking event loop
                await loop.run_in_executor(
                    None,
                    self.screenshot_capture.capture_with_interval,
                    self.capture_interval,
                )
                await asyncio.sleep(0.1)  # Brief sleep to avoid excessive CPU usage
        except asyncio.CancelledError:
            logger.debug("Screenshot loop task cancelled")
        except Exception as e:
            logger.error(f"Screenshot loop task failed: {e}")

    async def _cleanup_loop(self) -> None:
        """Cleanup loop task"""
        try:
            # First cleanup delay 30 seconds (leave time for initialization)
            cleanup_interval = 30
            first_cleanup = True

            while self.is_running:
                await asyncio.sleep(cleanup_interval)

                if not self.is_running:
                    break

                # After first cleanup, change to cleanup every 60 seconds
                if first_cleanup:
                    first_cleanup = False
                    cleanup_interval = 60

                try:
                    self.storage._cleanup_expired_records()
                    logger.debug("Performing periodic cleanup")
                except Exception as e:
                    logger.error(f"Failed to cleanup expired records: {e}")
        except asyncio.CancelledError:
            logger.debug("Cleanup loop task cancelled")
        except Exception as e:
            logger.error(f"Cleanup loop task failed: {e}")

    def get_recent_records(self, count: int = 100) -> list:
        """Get recent records"""
        return self.storage.get_latest_records(count)

    def get_records_by_type(self, event_type: str) -> list:
        """Get records by type"""
        from core.models import RecordType

        try:
            event_type_enum = RecordType(event_type)
            return self.storage.get_records_by_type(event_type_enum)
        except ValueError:
            logger.error(f"Invalid event type: {event_type}")
            return []

    def get_records_in_timeframe(
        self, start_time: datetime, end_time: datetime
    ) -> list:
        """Get records within specified time range"""
        return self.storage.get_records_in_timeframe(start_time, end_time)

    def get_records_in_last_n_seconds(self, seconds: int) -> list:
        """Get records from last N seconds"""
        from datetime import datetime, timedelta

        end_time = datetime.now()
        start_time = end_time - timedelta(seconds=seconds)
        return self.storage.get_records_in_timeframe(start_time, end_time)

    def get_buffered_events(self) -> list:
        """Get events from buffer"""
        return self.event_buffer.get_all()

    def clear_buffer(self) -> None:
        """Clear event buffer"""
        self.event_buffer.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get manager statistics"""
        try:
            storage_stats = self.storage.get_stats()
            keyboard_stats = self.keyboard_capture.get_stats()
            mouse_stats = self.mouse_capture.get_stats()
            screenshot_stats = self.screenshot_capture.get_stats()

            return {
                "is_running": self.is_running,
                "capture_interval": self.capture_interval,
                "window_size": self.window_size,
                "storage": storage_stats,
                "keyboard": keyboard_stats,
                "mouse": mouse_stats,
                "screenshot": screenshot_stats,
                "buffer_size": self.event_buffer.size(),
                "active_tasks": len([t for t in self.tasks.values() if not t.done()]),
            }
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {"error": str(e)}

    def set_capture_interval(self, interval: float) -> None:
        """Set capture interval"""
        self.capture_interval = max(1, interval)  # Minimum interval 0.1 seconds
        logger.info(f"Capture interval set to: {self.capture_interval} seconds")

    def set_compression_settings(
        self, quality: int = 85, max_width: int = 1920, max_height: int = 1080
    ) -> None:
        """Set screenshot compression parameters"""
        self.screenshot_capture.set_compression_settings(quality, max_width, max_height)
