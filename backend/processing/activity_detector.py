"""
User activity detector
Detects keyboard and mouse input activity to determine if user is actively using computer
"""

from typing import List
from datetime import datetime, timedelta
from core.models import RawRecord, RecordType
from core.logger import get_logger

logger = get_logger(__name__)


class ActivityDetector:
    """User activity detector"""

    def __init__(self, activity_threshold_seconds: int = 30):
        """
        Initialize activity detector

        Args:
            activity_threshold_seconds: Activity judgment threshold (seconds), consider active if there is keyboard/mouse input within this time
        """
        self.activity_threshold = activity_threshold_seconds

    def has_user_activity(self, records: List[RawRecord]) -> bool:
        """
        Detect if records contain user activity (keyboard or mouse input)

        Args:
            records: Raw record list

        Returns:
            True indicates active behavior, False indicates no active behavior
        """
        if not records:
            return False

        # Count keyboard and mouse input events
        keyboard_count = 0
        mouse_click_count = 0
        mouse_move_count = 0

        for record in records:
            record_type = self._get_record_type(record)

            if record_type == RecordType.KEYBOARD_RECORD:
                keyboard_count += 1
            elif record_type == RecordType.MOUSE_RECORD:
                action = record.data.get("action", "")
                if action in ["click", "double_click", "right_click", "middle_click"]:
                    mouse_click_count += 1
                elif action == "move":
                    mouse_move_count += 1

        # Judgment logic: consider active if there is any keyboard input or mouse click
        has_activity = keyboard_count > 0 or mouse_click_count > 0

        if has_activity:
            logger.debug(
                f"Detected user activity: "
                f"keyboard={keyboard_count}, "
                f"mouse_click={mouse_click_count}, "
                f"mouse_move={mouse_move_count}"
            )
        else:
            logger.debug(
                f"No user activity detected: "
                f"keyboard={keyboard_count}, "
                f"mouse_click={mouse_click_count}, "
                f"mouse_move={mouse_move_count} (screenshots only)"
            )

        return has_activity

    def filter_inactive_periods(self, records: List[RawRecord]) -> List[RawRecord]:
        """
        Filter out records during inactive periods

        Group records by time windows, only keep records within windows with keyboard/mouse activity

        Args:
            records: Raw record list

        Returns:
            Filtered record list
        """
        if not records:
            return []

        # Sort by time
        sorted_records = sorted(records, key=lambda x: x.timestamp)

        # Find all timestamps with keyboard/mouse input
        active_timestamps = []
        for record in sorted_records:
            record_type = self._get_record_type(record)

            if record_type in [RecordType.KEYBOARD_RECORD, RecordType.MOUSE_RECORD]:
                action = (
                    record.data.get("action", "")
                    if record_type == RecordType.MOUSE_RECORD
                    else "key"
                )
                # Only record actual input behaviors (keyboard keys, mouse clicks)
                if record_type == RecordType.KEYBOARD_RECORD or action in [
                    "click",
                    "double_click",
                    "right_click",
                    "middle_click",
                ]:
                    active_timestamps.append(record.timestamp)

        if not active_timestamps:
            logger.debug(
                "No keyboard/mouse input activity in records, filtering all records"
            )
            return []

        # Filter records: only keep records near active timestamps
        filtered = []
        for record in sorted_records:
            # Check if within threshold range of any active timestamp
            is_near_activity = any(
                abs((record.timestamp - active_time).total_seconds())
                <= self.activity_threshold
                for active_time in active_timestamps
            )

            if is_near_activity:
                filtered.append(record)

        if len(filtered) < len(sorted_records):
            logger.debug(
                f"Filtered inactive records: {len(sorted_records)} → {len(filtered)}"
            )

        return filtered

    def get_activity_periods(self, records: List[RawRecord]) -> List[tuple]:
        """
        Get active time periods list

        Args:
            records: Raw record list

        Returns:
            Active time periods list [(start_time, end_time), ...]
        """
        if not records:
            return []

        # Find all keyboard/mouse input timestamps
        active_timestamps = []
        for record in records:
            record_type = self._get_record_type(record)

            if record_type in [RecordType.KEYBOARD_RECORD, RecordType.MOUSE_RECORD]:
                action = (
                    record.data.get("action", "")
                    if record_type == RecordType.MOUSE_RECORD
                    else "key"
                )
                if record_type == RecordType.KEYBOARD_RECORD or action in [
                    "click",
                    "double_click",
                    "right_click",
                    "middle_click",
                ]:
                    active_timestamps.append(record.timestamp)

        if not active_timestamps:
            return []

        # Sort by time
        active_timestamps.sort()

        # Merge nearby timestamps into time periods
        periods = []
        current_start = active_timestamps[0]
        current_end = active_timestamps[0]

        for timestamp in active_timestamps[1:]:
            if (timestamp - current_end).total_seconds() <= self.activity_threshold:
                # Extend current time period
                current_end = timestamp
            else:
                # End current time period, start new time period
                periods.append(
                    (
                        current_start - timedelta(seconds=self.activity_threshold),
                        current_end + timedelta(seconds=self.activity_threshold),
                    )
                )
                current_start = timestamp
                current_end = timestamp

        # Add last time period
        periods.append(
            (
                current_start - timedelta(seconds=self.activity_threshold),
                current_end + timedelta(seconds=self.activity_threshold),
            )
        )

        return periods

    @staticmethod
    def _get_record_type(record: RawRecord) -> RecordType:
        """
        Compatible with old data format, ensure returns RecordType enum
        """
        record_type = record.type

        if isinstance(record_type, RecordType):
            return record_type

        # Compatible with old string/dictionary format
        normalized = str(record_type).lower()
        mapping = {
            "keyboard": RecordType.KEYBOARD_RECORD,
            "keyboard_record": RecordType.KEYBOARD_RECORD,
            "mouse": RecordType.MOUSE_RECORD,
            "mouse_record": RecordType.MOUSE_RECORD,
            "screenshot": RecordType.SCREENSHOT_RECORD,
            "screenshot_record": RecordType.SCREENSHOT_RECORD,
        }

        if normalized in mapping:
            return mapping[normalized]

        logger.warning(
            f"Unrecognized record type: {record_type}, defaulting to inactive event"
        )
        return RecordType.SCREENSHOT_RECORD
