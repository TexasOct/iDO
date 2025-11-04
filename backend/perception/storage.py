"""
Sliding window storage
Implement 20-second temporary sliding window with automatic deletion on timeout
"""

import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from collections import deque
from threading import Lock
from core.models import RawRecord, RecordType
from core.logger import get_logger

logger = get_logger(__name__)


class SlidingWindowStorage:
    """Sliding window storage manager"""

    def __init__(self, window_size: int = 20):
        """
        Initialize sliding window storage

        Args:
            window_size: Window size (seconds)
        """
        self.window_size = window_size
        self.records: deque = deque()
        self.lock = Lock()
        self._last_cleanup = time.time()
        self._cleanup_interval = 5.0  # Clean up expired data every 5 seconds

    def add_record(self, record: RawRecord) -> None:
        """Add record to sliding window"""
        try:
            with self.lock:
                self.records.append(record)

                # Periodically clean up expired data
                current_time = time.time()
                if current_time - self._last_cleanup > self._cleanup_interval:
                    self._cleanup_expired_records()
                    self._last_cleanup = current_time

        except Exception as e:
            logger.error(f"Failed to add record to sliding window: {e}")

    def get_records(
        self,
        event_type: Optional[RecordType] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[RawRecord]:
        """
        Get records

        Args:
            event_type: Event type filter
            start_time: Start time filter
            end_time: End time filter

        Returns:
            Filtered record list
        """
        try:
            with self.lock:
                # First clean up expired data
                self._cleanup_expired_records()

                filtered_records = []
                for record in self.records:
                    # Type filter
                    if event_type and record.type != event_type:
                        continue

                    # Time filter
                    if start_time and record.timestamp < start_time:
                        continue
                    if end_time and record.timestamp > end_time:
                        continue

                    filtered_records.append(record)

                return filtered_records

        except Exception as e:
            logger.error(f"Failed to get records: {e}")
            return []

    def get_latest_records(self, count: int = 10) -> List[RawRecord]:
        """Get latest N records"""
        try:
            with self.lock:
                self._cleanup_expired_records()
                return list(self.records)[-count:]
        except Exception as e:
            logger.error(f"Failed to get latest records: {e}")
            return []

    def get_records_by_type(self, event_type: RecordType) -> List[RawRecord]:
        """Get records by event type"""
        return self.get_records(event_type=event_type)

    def get_records_in_timeframe(
        self, start_time: datetime, end_time: datetime
    ) -> List[RawRecord]:
        """Get records within specified time range"""
        return self.get_records(start_time=start_time, end_time=end_time)

    def _cleanup_expired_records(self) -> None:
        """Clean up expired records"""
        try:
            current_time = datetime.now()
            cutoff_time = current_time - timedelta(seconds=self.window_size)

            # Remove expired records from left side
            while self.records and self.records[0].timestamp < cutoff_time:
                self.records.popleft()

        except Exception as e:
            logger.error(f"Failed to clean up expired records: {e}")

    def clear(self) -> None:
        """Clear all records"""
        try:
            with self.lock:
                self.records.clear()
                logger.info("Sliding window storage cleared")
        except Exception as e:
            logger.error(f"Failed to clear storage: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        try:
            with self.lock:
                self._cleanup_expired_records()

                # Count records by type
                type_counts = {}
                for record in self.records:
                    type_name = record.type.value
                    type_counts[type_name] = type_counts.get(type_name, 0) + 1

                return {
                    "total_records": len(self.records),
                    "window_size_seconds": self.window_size,
                    "type_counts": type_counts,
                    "oldest_record": self.records[0].timestamp
                    if self.records
                    else None,
                    "newest_record": self.records[-1].timestamp
                    if self.records
                    else None,
                    "last_cleanup": self._last_cleanup,
                }
        except Exception as e:
            logger.error(f"Failed to get storage statistics: {e}")
            return {"error": str(e)}


class EventBuffer:
    """Event buffer for temporary storage and batch processing"""

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.buffer: List[RawRecord] = []
        self.lock = Lock()

    def add(self, record: RawRecord) -> None:
        """Add event to buffer"""
        try:
            with self.lock:
                self.buffer.append(record)

                # If buffer is full, remove oldest record
                if len(self.buffer) > self.max_size:
                    self.buffer.pop(0)

        except Exception as e:
            logger.error(f"Failed to add event to buffer: {e}")

    def get_all(self) -> List[RawRecord]:
        """Get all events and clear buffer"""
        try:
            with self.lock:
                events = self.buffer.copy()
                self.buffer.clear()
                return events
        except Exception as e:
            logger.error(f"Failed to get buffer events: {e}")
            return []

    def peek(self) -> List[RawRecord]:
        """Peek at buffer contents without clearing"""
        try:
            with self.lock:
                return self.buffer.copy()
        except Exception as e:
            logger.error(f"Failed to peek buffer: {e}")
            return []

    def clear(self) -> None:
        """Clear buffer"""
        try:
            with self.lock:
                self.buffer.clear()
        except Exception as e:
            logger.error(f"Failed to clear buffer: {e}")

    def size(self) -> int:
        """Get buffer size"""
        try:
            with self.lock:
                return len(self.buffer)
        except Exception as e:
            logger.error(f"Failed to get buffer size: {e}")
            return 0
