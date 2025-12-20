"""
Record filtering rules
Implement intelligent filtering logic for keyboard, mouse, and screenshot records
Note: Image-level deduplication is handled by ImageFilter
"""

from typing import Any, Dict, List, Optional

from core.logger import get_logger
from core.models import RawRecord, RecordType

logger = get_logger(__name__)


class RecordFilter:
    """
    Record filter - handles RawRecord-level filtering and organization

    Responsibilities:
    1. Keyboard event filtering (special keys, modifiers)
    2. Mouse event filtering (important actions)
    3. Screenshot record selection (time window control)
    4. Event merging (consecutive event compression)

    Note: Image deduplication is handled by ImageFilter, not here
    """

    def __init__(
        self,
        min_screenshots_per_window: int = 2,
        scroll_merge_threshold: float = 0.1,
        click_merge_threshold: float = 0.5,
    ):
        """
        Initialize record filter

        Args:
            min_screenshots_per_window: Minimum screenshots to keep per time window
            scroll_merge_threshold: Time threshold for merging scroll events (seconds)
            click_merge_threshold: Time threshold for merging click events (seconds)
        """
        self.keyboard_special_keys = {
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

        self.mouse_important_actions = {
            "press",
            "release",
            "drag",
            "drag_end",
            "scroll",
        }

        self.scroll_merge_threshold = scroll_merge_threshold
        self.click_merge_threshold = click_merge_threshold
        self.min_screenshots_per_window = min_screenshots_per_window

        logger.debug("RecordFilter initialized")

    def filter_keyboard_events(self, records: List[RawRecord]) -> List[RawRecord]:
        """Filter keyboard events, currently keeps all keyboard records"""
        filtered_records = [
            record for record in records if record.type == RecordType.KEYBOARD_RECORD
        ]

        for record in filtered_records:
            logger.debug(f"Keeping keyboard event: {record.data.get('key', 'unknown')}")

        return filtered_records

    def filter_mouse_events(self, records: List[RawRecord]) -> List[RawRecord]:
        """Filter mouse events"""
        filtered_records = []

        for record in records:
            if record.type != RecordType.MOUSE_RECORD:
                continue

            # Check if this is an important mouse event
            if self._is_important_mouse_event(record):
                filtered_records.append(record)
                logger.debug(
                    f"Keeping mouse event: {record.data.get('action', 'unknown')}"
                )
            else:
                logger.debug(
                    f"Filtering mouse event: {record.data.get('action', 'unknown')}"
                )

        return filtered_records

    def filter_screenshot_records(self, records: List[RawRecord]) -> List[RawRecord]:
        """
        Filter screenshot records based on time window

        Note: This only does record-level time window control.
        Image deduplication is handled by ImageFilter.
        """
        filtered_records = []
        last_window_start = None
        screenshots_in_window = 0
        screenshot_interval = 1.0  # Sliding window length (seconds)

        for record in records:
            if record.type != RecordType.SCREENSHOT_RECORD:
                continue

            if last_window_start is None:
                last_window_start = record.timestamp
                screenshots_in_window = 0

            elapsed = (record.timestamp - last_window_start).total_seconds()

            # Reset count when window is exceeded
            if elapsed >= screenshot_interval:
                last_window_start = record.timestamp
                screenshots_in_window = 0

            if (
                elapsed < screenshot_interval
                and screenshots_in_window >= self.min_screenshots_per_window
            ):
                logger.debug(f"Filtering screenshot record: {record.timestamp}")
                continue

            filtered_records.append(record)
            screenshots_in_window += 1
            logger.debug(f"Keeping screenshot record: {record.timestamp}")

        return filtered_records

    def merge_consecutive_events(self, records: List[RawRecord]) -> List[RawRecord]:
        """Merge consecutive events"""
        if not records:
            return []

        merged_records = []
        current_group = [records[0]]

        for i in range(1, len(records)):
            current_record = records[i]
            previous_record = records[i - 1]

            # Check if events can be merged
            if self._can_merge_events(previous_record, current_record):
                current_group.append(current_record)
            else:
                # Merge current group
                merged_record = self._merge_event_group(current_group)
                if merged_record:
                    merged_records.append(merged_record)

                # Start new group
                current_group = [current_record]

        # Process last group
        if current_group:
            merged_record = self._merge_event_group(current_group)
            if merged_record:
                merged_records.append(merged_record)

        return merged_records

    def _is_special_keyboard_event(self, record: RawRecord) -> bool:
        """Determine if this is a special keyboard event"""
        data = record.data
        key = data.get("key", "").lower()
        action = data.get("action", "")
        modifiers = data.get("modifiers", [])

        # Special keys
        if key in self.keyboard_special_keys:
            return True

        # Regular keys with modifiers
        if modifiers and len(modifiers) > 0:
            return True

        # Special actions
        if action in ["press", "release"] and key in ["ctrl", "alt", "shift", "cmd"]:
            return True

        return False

    def _is_important_mouse_event(self, record: RawRecord) -> bool:
        """Determine if this is an important mouse event"""
        data = record.data
        action = data.get("action", "")

        return action in self.mouse_important_actions

    def _can_merge_events(self, prev_record: RawRecord, curr_record: RawRecord) -> bool:
        """Determine if two events can be merged"""
        # Different event types cannot be merged
        if prev_record.type != curr_record.type:
            return False

        # Time interval check
        time_diff = (curr_record.timestamp - prev_record.timestamp).total_seconds()

        if prev_record.type == RecordType.KEYBOARD_RECORD:
            # Keyboard events: same keys within 100ms can be merged
            return time_diff <= 0.1 and prev_record.data.get(
                "key"
            ) == curr_record.data.get("key")

        elif prev_record.type == RecordType.MOUSE_RECORD:
            # Mouse events: determine by action type
            prev_action = prev_record.data.get("action", "")
            curr_action = curr_record.data.get("action", "")

            if prev_action == "scroll" and curr_action == "scroll":
                return time_diff <= self.scroll_merge_threshold

            if prev_action == "press" and curr_action == "release":
                return time_diff <= self.click_merge_threshold

            return False

        elif prev_record.type == RecordType.SCREENSHOT_RECORD:
            # Screenshots: can be merged within 1 second
            return time_diff <= 1.0

        return False

    def _merge_event_group(self, group: List[RawRecord]) -> Optional[RawRecord]:
        """Merge event group"""
        if not group:
            return None

        if len(group) == 1:
            return group[0]

        # Create merged event
        merged_record = RawRecord(
            timestamp=group[0].timestamp,
            type=group[0].type,
            data=self._merge_event_data(group),
            screenshot_path=getattr(group[0], "screenshot_path", None),
        )

        # Add source event information
        merged_record.data["source_events"] = [record.to_dict() for record in group]

        return merged_record

    def _merge_event_data(self, group: List[RawRecord]) -> Dict[str, Any]:
        """Merge event data"""
        if not group:
            return {}

        first_record = group[0]
        event_type = first_record.type

        if event_type == RecordType.KEYBOARD_RECORD:
            return self._merge_keyboard_data(group)
        elif event_type == RecordType.MOUSE_RECORD:
            return self._merge_mouse_data(group)
        elif event_type == RecordType.SCREENSHOT_RECORD:
            return self._merge_screenshot_data(group)
        else:
            return first_record.data

    def _merge_keyboard_data(self, group: List[RawRecord]) -> Dict[str, Any]:
        """Merge keyboard event data"""
        first_data = group[0].data
        _last_data = group[-1].data

        return {
            "action": "sequence",
            "key": first_data.get("key", "unknown"),
            "key_type": first_data.get("key_type", "unknown"),
            "modifiers": first_data.get("modifiers", []),
            "count": len(group),
            "duration": (group[-1].timestamp - group[0].timestamp).total_seconds(),
            "start_time": group[0].timestamp.isoformat(),
            "end_time": group[-1].timestamp.isoformat(),
            "merged": True,
        }

    def _merge_mouse_data(self, group: List[RawRecord]) -> Dict[str, Any]:
        """Merge mouse event data"""
        first_data = group[0].data
        last_data = group[-1].data

        if first_data.get("action") == "scroll":
            # Merge scroll events
            total_dx = sum(record.data.get("dx", 0) for record in group)
            total_dy = sum(record.data.get("dy", 0) for record in group)

            return {
                "action": "scroll",
                "position": last_data.get("position", (0, 0)),
                "dx": total_dx,
                "dy": total_dy,
                "count": len(group),
                "duration": (group[-1].timestamp - group[0].timestamp).total_seconds(),
                "start_time": group[0].timestamp.isoformat(),
                "end_time": group[-1].timestamp.isoformat(),
                "merged": True,
            }

        elif (
            first_data.get("action") == "press" and last_data.get("action") == "release"
        ):
            # Merge click events
            return {
                "action": "click",
                "button": first_data.get("button", "unknown"),
                "start_position": first_data.get("position", (0, 0)),
                "end_position": last_data.get("position", (0, 0)),
                "duration": (group[-1].timestamp - group[0].timestamp).total_seconds(),
                "start_time": group[0].timestamp.isoformat(),
                "end_time": group[-1].timestamp.isoformat(),
                "merged": True,
            }

        else:
            # Other cases, return first event's data
            return first_data

    def _merge_screenshot_data(self, group: List[RawRecord]) -> Dict[str, Any]:
        """Merge screenshot data"""
        first_data = (group[0].data or {}).copy()
        last_data = group[-1].data or {}

        sequence_meta = {
            "sequenceCount": len(group),
            "sequenceDuration": (
                group[-1].timestamp - group[0].timestamp
            ).total_seconds(),
            "sequenceStart": group[0].timestamp.isoformat(),
            "sequenceEnd": group[-1].timestamp.isoformat(),
        }

        # Preserve original screenshot info while adding sequence metadata
        merged_data = {**first_data, "merged": True, "sequenceMeta": sequence_meta}

        # If later screenshot hash or path exists, keep latest value for cache matching
        for field in ("hash", "screenshotPath", "img_data"):
            if field not in merged_data and field in last_data:
                merged_data[field] = last_data[field]

        if "screenshotPath" not in merged_data and getattr(
            group[0], "screenshot_path", None
        ):
            merged_data["screenshotPath"] = group[0].screenshot_path

        return merged_data

    def filter_all_records(self, records: List[RawRecord]) -> List[RawRecord]:
        """
        Filter all records (keyboard, mouse, screenshot)

        Note: Screenshot image deduplication is NOT done here.
        Use ImageFilter.filter_screenshots() before calling this method.
        """
        logger.debug(f"Starting record filtering, original record count: {len(records)}")

        # Filter by type
        keyboard_events = self.filter_keyboard_events(records)
        mouse_events = self.filter_mouse_events(records)
        screenshot_records = self.filter_screenshot_records(records)

        # Merge all filtered records
        all_filtered = keyboard_events + mouse_events + screenshot_records

        # Sort by time
        all_filtered.sort(key=lambda x: x.timestamp)

        # Merge consecutive events
        merged_events = self.merge_consecutive_events(all_filtered)

        logger.debug(f"Filtering completed, final record count: {len(merged_events)}")
        logger.debug(
            f"Keyboard: {len(keyboard_events)}, Mouse: {len(mouse_events)}, Screenshots: {len(screenshot_records)}"
        )

        return merged_events
