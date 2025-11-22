"""
Event filtering rules
Implement intelligent filtering logic for keyboard and mouse events
Add screenshot deduplication functionality with multi-hash similarity detection
"""

import base64
import io
from collections import deque
from typing import Any, Dict, List, Optional, Tuple

from core.logger import get_logger
from core.models import RawRecord, RecordType
from processing.image_manager import get_image_manager

logger = get_logger(__name__)

# Try to import imagehash and PIL
try:
    import imagehash
    from PIL import Image

    IMAGEHASH_AVAILABLE = True
except ImportError:
    IMAGEHASH_AVAILABLE = False
    logger.warning(
        "imagehash or PIL library not installed, screenshot deduplication functionality will be disabled"
    )


class EventFilter:
    """Event filter - supports screenshot deduplication with multi-hash similarity"""

    def __init__(
        self,
        enable_screenshot_deduplication: bool = True,
        hash_threshold: int = 5,
        similarity_threshold: float = 0.90,
        hash_cache_size: int = 10,
        hash_algorithms: Optional[List[str]] = None,
        enable_adaptive_threshold: bool = True,
    ):
        """
        Initialize event filter

        Args:
            enable_screenshot_deduplication: Whether to enable screenshot deduplication
            hash_threshold: Legacy perceptual hash difference threshold (kept for backward compatibility)
            similarity_threshold: Similarity threshold for multi-hash comparison (0-1, default 0.90)
            hash_cache_size: Number of recent screenshot hashes to cache (default 10)
            hash_algorithms: List of hash algorithms to use (default: ['phash', 'dhash', 'average_hash'])
            enable_adaptive_threshold: Whether to enable scene-adaptive thresholds (default True)
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

        self.scroll_merge_threshold = 0.1  # Scroll events within 100ms will be merged
        self.click_merge_threshold = 0.5  # Click events within 500ms will be merged
        self.min_screenshots_per_window = 2

        # Screenshot deduplication configuration
        self.enable_screenshot_deduplication = (
            enable_screenshot_deduplication and IMAGEHASH_AVAILABLE
        )
        self.hash_threshold = hash_threshold  # Legacy threshold (kept for compatibility)
        self.similarity_threshold = similarity_threshold
        self.hash_cache_size = hash_cache_size
        self.enable_adaptive_threshold = enable_adaptive_threshold

        # Hash algorithm configuration with weights
        if hash_algorithms is None:
            hash_algorithms = ['phash', 'dhash', 'average_hash']

        self.hash_algorithms = self._init_hash_algorithms(hash_algorithms)

        # Hash cache: deque of (timestamp, multi_hash_dict) tuples
        self.hash_cache: deque = deque(maxlen=hash_cache_size)

        # Legacy single hash (kept for backward compatibility)
        self.last_screenshot_hash = None

        self.image_manager = get_image_manager()

        if enable_screenshot_deduplication and not IMAGEHASH_AVAILABLE:
            logger.warning(
                "Screenshot deduplication feature disabled (missing dependency library)"
            )
        else:
            logger.info(
                f"Screenshot deduplication enabled: algorithms={list(self.hash_algorithms.keys())}, "
                f"similarity_threshold={similarity_threshold}, cache_size={hash_cache_size}"
            )

    def _init_hash_algorithms(self, algorithm_names: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Initialize hash algorithms with their functions and weights

        Args:
            algorithm_names: List of algorithm names to enable

        Returns:
            Dictionary mapping algorithm names to their config (function, weight)
        """
        if not IMAGEHASH_AVAILABLE:
            return {}

        # Available algorithms with default weights
        available_algorithms = {
            'phash': {
                'func': imagehash.phash,
                'weight': 0.5,  # 50% weight - best for structural similarity
                'description': 'Perceptual hash'
            },
            'dhash': {
                'func': imagehash.dhash,
                'weight': 0.3,  # 30% weight - good for detecting gradients
                'description': 'Difference hash'
            },
            'average_hash': {
                'func': imagehash.average_hash,
                'weight': 0.2,  # 20% weight - fast but less precise
                'description': 'Average hash'
            }
        }

        # Filter and normalize weights
        selected = {}
        total_weight = 0.0

        for name in algorithm_names:
            if name in available_algorithms:
                selected[name] = available_algorithms[name].copy()
                total_weight += selected[name]['weight']

        # Normalize weights to sum to 1.0
        if total_weight > 0:
            for name in selected:
                selected[name]['weight'] /= total_weight

        return selected

    def _compute_multi_hash(self, img: Image.Image) -> Optional[Dict[str, Any]]:
        """
        Compute multiple hash values for an image

        Args:
            img: PIL Image object

        Returns:
            Dictionary mapping algorithm names to hash values, or None on failure
        """
        if not IMAGEHASH_AVAILABLE or not self.hash_algorithms:
            return None

        try:
            multi_hash = {}
            for algo_name, algo_config in self.hash_algorithms.items():
                hash_func = algo_config['func']
                hash_value = hash_func(img)
                multi_hash[algo_name] = {
                    'hash': hash_value,
                    'weight': algo_config['weight']
                }
            return multi_hash
        except Exception as e:
            logger.debug(f"Failed to compute multi-hash: {e}")
            return None

    def _calculate_similarity(
        self,
        hash1: Dict[str, Any],
        hash2: Dict[str, Any]
    ) -> float:
        """
        Calculate weighted similarity score between two multi-hash dictionaries

        Args:
            hash1: First multi-hash dictionary
            hash2: Second multi-hash dictionary

        Returns:
            Similarity score (0-1), where 1.0 means identical
        """
        total_score = 0.0

        for algo_name, hash_info in hash1.items():
            if algo_name not in hash2:
                continue

            # Calculate hash distance (lower = more similar)
            hash_diff = hash_info['hash'] - hash2[algo_name]['hash']

            # Convert to similarity (0-1), assuming 64-bit hash max distance = 64
            max_distance = 64
            similarity = max(0.0, 1.0 - (hash_diff / max_distance))

            # Add weighted contribution
            weight = hash_info['weight']
            total_score += similarity * weight

        return total_score

    def _detect_scene_type(self, similarity: float) -> str:
        """
        Detect scene type based on similarity score

        Args:
            similarity: Similarity score (0-1)

        Returns:
            Scene type: 'static', 'video', or 'normal'
        """
        if similarity >= 0.99:
            return 'static'  # Static content (documents, reading)
        elif similarity >= 0.95:
            return 'video'   # Video playback or animations
        else:
            return 'normal'  # Normal interactive content

    def _get_adaptive_threshold(self, scene_type: str) -> float:
        """
        Get adaptive similarity threshold based on scene type

        Args:
            scene_type: Detected scene type

        Returns:
            Adjusted similarity threshold
        """
        if not self.enable_adaptive_threshold:
            return self.similarity_threshold

        # Adjust thresholds based on scene
        if scene_type == 'static':
            # Static scenes: lower threshold to reduce redundancy
            return 0.85
        elif scene_type == 'video':
            # Video scenes: higher threshold to preserve key frames
            return 0.98
        else:
            # Normal scenes: use configured threshold
            return self.similarity_threshold

    def filter_duplicate_screenshots(self, records: List[RawRecord]) -> List[RawRecord]:
        """
        Remove duplicate screenshots using multi-hash similarity detection

        Uses multiple hashing algorithms (phash, dhash, average_hash) with weighted scoring
        to detect similar images. Supports scene-adaptive thresholds for different content types.

        Args:
            records: Original record list

        Returns:
            Filtered record list with duplicates removed
        """
        if not self.enable_screenshot_deduplication:
            return records

        filtered = []
        skipped_count = 0

        for record in records:
            # Non-screenshot records are kept directly
            if record.type != RecordType.SCREENSHOT_RECORD:
                filtered.append(record)
                continue

            # Calculate multi-hash for screenshot
            try:
                img = self._load_image_from_record(record)

                if img is None:
                    # Unable to load image, keep record
                    filtered.append(record)
                    continue

                # Compute multi-hash
                multi_hash = self._compute_multi_hash(img)

                if multi_hash is None:
                    # Unable to calculate hash, keep record
                    filtered.append(record)
                    continue

                # Check similarity with cached hashes
                is_duplicate = False
                max_similarity = 0.0
                scene_type = 'normal'

                if self.hash_cache:
                    # Compare with all cached hashes
                    for cached_timestamp, cached_hash in self.hash_cache:
                        similarity = self._calculate_similarity(multi_hash, cached_hash)
                        max_similarity = max(max_similarity, similarity)

                    # Detect scene type and get adaptive threshold
                    scene_type = self._detect_scene_type(max_similarity)
                    adaptive_threshold = self._get_adaptive_threshold(scene_type)

                    # Check if duplicate
                    if max_similarity >= adaptive_threshold:
                        is_duplicate = True
                        skipped_count += 1
                        logger.debug(
                            f"Skipping duplicate screenshot: similarity={max_similarity:.3f}, "
                            f"scene={scene_type}, threshold={adaptive_threshold:.3f}"
                        )

                if not is_duplicate:
                    # Not duplicate, keep record and add to cache
                    filtered.append(record)
                    self.hash_cache.append((record.timestamp, multi_hash))

                    # Also update legacy single hash for backward compatibility
                    if 'phash' in multi_hash:
                        self.last_screenshot_hash = multi_hash['phash']['hash']

            except Exception as e:
                logger.warning(
                    f"Failed to process screenshot similarity: {e}, keeping screenshot"
                )
                filtered.append(record)

        if skipped_count > 0:
            logger.debug(
                f"Screenshot deduplication: {len(records)} → {len(filtered)} records "
                f"(removed {skipped_count} duplicates)"
            )

        return filtered

    def _load_image_from_record(self, record: RawRecord) -> Optional[Image.Image]:
        """
        Load PIL Image from a RawRecord

        Tries multiple sources in order:
        1. Embedded base64 data in record.data
        2. Memory cache using image hash
        3. Disk thumbnail using image hash

        Args:
            record: Screenshot record

        Returns:
            PIL Image object, or None if unable to load
        """
        if not IMAGEHASH_AVAILABLE:
            return None

        try:
            data = record.data or {}

            # Try to get base64 image data from data
            img_data_b64 = data.get("img_data")
            if img_data_b64:
                img_bytes = base64.b64decode(img_data_b64)
                return Image.open(io.BytesIO(img_bytes))

        except Exception as e:
            logger.debug(f"Failed to load image from embedded data: {e}")

        # Try to load from cache using hash
        try:
            img_hash = (record.data or {}).get("hash")
            if not img_hash:
                return None

            # First try memory cache
            cached_data = self.image_manager.get_from_cache(img_hash)
            if cached_data:
                img_bytes = base64.b64decode(cached_data)
                return Image.open(io.BytesIO(img_bytes))

            # Fallback to disk thumbnail
            thumbnail_data = self.image_manager.load_thumbnail_base64(img_hash)
            if thumbnail_data:
                img_bytes = base64.b64decode(thumbnail_data)
                return Image.open(io.BytesIO(img_bytes))

        except Exception as exc:
            logger.debug(f"Failed to load image from cache: {exc}")

        return None

    def _compute_image_hash(self, record: RawRecord) -> Optional[Any]:
        """
        Calculate perceptual hash of screenshot (legacy method for backward compatibility)

        Args:
            record: Screenshot record

        Returns:
            imagehash phash object, or None
        """
        if not IMAGEHASH_AVAILABLE:
            return None

        img = self._load_image_from_record(record)
        if img is None:
            return None

        try:
            return imagehash.phash(img)
        except Exception as e:
            logger.debug(f"Failed to calculate perceptual hash: {e}")
            return None

    def reset_deduplication_state(self):
        """Reset deduplication state (clears hash cache)"""
        self.last_screenshot_hash = None
        self.hash_cache.clear()
        logger.debug("Screenshot deduplication state reset")

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

    def filter_screenshot_events(self, records: List[RawRecord]) -> List[RawRecord]:
        """Filter screenshot events"""
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
                logger.debug(f"Filtering duplicate screenshot: {record.timestamp}")
                continue

            filtered_records.append(record)
            screenshots_in_window += 1
            logger.debug(f"Keeping screenshot: {record.timestamp}")

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
        last_data = group[-1].data

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

    def filter_all_events(self, records: List[RawRecord]) -> List[RawRecord]:
        """Filter all events (including screenshot deduplication)"""
        logger.info(f"Starting event filtering, original record count: {len(records)}")

        # Step 1: Screenshot deduplication
        dedup_records = self.filter_duplicate_screenshots(records)

        # Filter by type
        keyboard_events = self.filter_keyboard_events(dedup_records)
        mouse_events = self.filter_mouse_events(dedup_records)
        screenshot_events = self.filter_screenshot_events(dedup_records)

        # Merge all filtered events
        all_filtered = keyboard_events + mouse_events + screenshot_events

        # Sort by time
        all_filtered.sort(key=lambda x: x.timestamp)

        # Merge consecutive events
        merged_events = self.merge_consecutive_events(all_filtered)

        logger.info(f"Filtering completed, final record count: {len(merged_events)}")
        logger.info(
            f"Keyboard events: {len(keyboard_events)}, Mouse events: {len(mouse_events)}, Screenshots: {len(screenshot_events)}"
        )

        return merged_events
