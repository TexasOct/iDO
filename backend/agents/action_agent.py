"""
ActionAgent - Intelligent agent for complete action extraction and saving
Handles the complete flow: raw_records -> actions (extract + save)
"""

import asyncio
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.db import get_db
from core.logger import get_logger
from core.models import RawRecord, RecordType
from core.settings import get_settings
from llm.manager import get_llm_manager

logger = get_logger(__name__)


class ActionAgent:
    """
    Intelligent action extraction and saving agent

    Responsibilities:
    - Extract actions from raw records (screenshots) using LLM
    - Resolve screenshot hashes and timestamps
    - Save actions to database
    - Complete flow: raw_records -> actions (in database)
    """

    def __init__(self):
        """Initialize ActionAgent"""
        # Initialize components
        self.db = get_db()
        self.llm_manager = get_llm_manager()
        self.settings = get_settings()

        # Statistics
        self.stats: Dict[str, Any] = {
            "actions_extracted": 0,
            "actions_saved": 0,
            "actions_filtered": 0,
        }

        logger.debug("ActionAgent initialized")

    def _get_language(self) -> str:
        """Get current language setting from config with caching"""
        return self.settings.get_language()

    async def extract_and_save_actions(
        self,
        records: List[RawRecord],
        input_usage_hint: str = "",
        keyboard_records: Optional[List[RawRecord]] = None,
        mouse_records: Optional[List[RawRecord]] = None,
        enable_supervisor: bool = False,
    ) -> int:
        """
        Complete action extraction and saving flow

        Args:
            records: List of raw records (mainly screenshots)
            input_usage_hint: Keyboard/mouse activity hint (legacy)
            keyboard_records: Keyboard event records for timestamp extraction
            mouse_records: Mouse event records for timestamp extraction
            enable_supervisor: Whether to enable supervisor validation (default False)

        Returns:
            Number of actions saved
        """
        if not records:
            return 0

        try:
            logger.debug(f"ActionAgent: Processing {len(records)} records")

            # Step 1: Extract actions using LLM
            actions = await self._extract_actions(
                records, input_usage_hint, keyboard_records, mouse_records, enable_supervisor
            )

            if not actions:
                logger.debug("ActionAgent: No actions extracted")
                return 0

            # Step 2: Validate and resolve screenshot hashes
            screenshot_records = [
                r for r in records if r.type == RecordType.SCREENSHOT_RECORD
            ]

            resolved_actions: List[Dict[str, Any]] = []
            for action_data in actions:
                action_hashes = self._resolve_action_screenshot_hashes(
                    action_data, records
                )
                if not action_hashes:
                    logger.warning(
                        "Dropping action: invalid image_index in action '%s'",
                        action_data.get("title", "<no title>"),
                    )
                    self.stats["actions_filtered"] += 1
                    continue

                resolved_actions.append({"data": action_data, "hashes": action_hashes})

            # Step 3: Save actions to database
            saved_count = 0
            for resolved in resolved_actions:
                action_data = resolved["data"]
                action_hashes = resolved["hashes"]
                action_id = str(uuid.uuid4())

                # Calculate timestamp specific to this action
                image_indices = action_data.get("image_index") or action_data.get(
                    "imageIndex", []
                )
                action_timestamp = self._calculate_action_timestamp(
                    image_indices, screenshot_records
                )

                # Save action to database
                await self.db.actions.save(
                    action_id=action_id,
                    title=action_data["title"],
                    description=action_data["description"],
                    keywords=action_data.get("keywords", []),
                    timestamp=action_timestamp.isoformat(),
                    screenshots=action_hashes,
                )

                saved_count += 1
                self.stats["actions_saved"] += 1

            logger.debug(f"ActionAgent: Saved {saved_count} actions to database")
            return saved_count

        except Exception as e:
            logger.error(f"ActionAgent: Failed to process actions: {e}", exc_info=True)
            return 0

    async def _extract_actions(
        self,
        records: List[RawRecord],
        input_usage_hint: str = "",
        keyboard_records: Optional[List[RawRecord]] = None,
        mouse_records: Optional[List[RawRecord]] = None,
        enable_supervisor: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Extract actions from raw records using LLM

        Args:
            records: List of raw records (mainly screenshots)
            input_usage_hint: Keyboard/mouse activity hint (legacy)
            keyboard_records: Keyboard event records for timestamp extraction
            mouse_records: Mouse event records for timestamp extraction
            enable_supervisor: Whether to enable supervisor validation

        Returns:
            List of action dictionaries
        """
        if not records:
            return []

        try:
            logger.debug(f"ActionAgent: Extracting actions from {len(records)} records")

            # Import here to avoid circular dependency
            from processing.summarizer import EventSummarizer

            # Get current language from settings
            language = self._get_language()
            summarizer = EventSummarizer(language=language)
            result = await summarizer.extract_actions_only(
                records, input_usage_hint, keyboard_records, mouse_records
            )

            actions = result.get("actions", [])

            # Apply supervisor validation if enabled
            # Note: ActionSupervisor not yet implemented, placeholder for future
            if enable_supervisor and actions:
                actions = await self._validate_with_supervisor(actions)

            self.stats["actions_extracted"] += len(actions)

            logger.debug(f"ActionAgent: Extracted {len(actions)} actions")
            return actions

        except Exception as e:
            logger.error(f"ActionAgent: Failed to extract actions: {e}", exc_info=True)
            return []

    def _resolve_action_screenshot_hashes(
        self, action_data: Dict[str, Any], records: List[RawRecord]
    ) -> Optional[List[str]]:
        """
        Resolve screenshot hashes based on image_index from LLM response

        Args:
            action_data: Action data containing image_index (or imageIndex)
            records: All raw records (screenshots)

        Returns:
            List of screenshot hashes filtered by image_index
        """
        # Get image_index from action data (support both snake_case and camelCase)
        image_indices = action_data.get("image_index") or action_data.get("imageIndex")

        # Extract screenshot records
        screenshot_records = [
            r for r in records if r.type == RecordType.SCREENSHOT_RECORD
        ]

        # If image_index is provided and valid
        if isinstance(image_indices, list) and image_indices:
            normalized_hashes: List[str] = []
            seen = set()

            for idx in image_indices:
                try:
                    # Indices are zero-based per prompt
                    idx_int = int(idx)
                    if 0 <= idx_int < len(screenshot_records):
                        record = screenshot_records[idx_int]
                        data = record.data or {}
                        img_hash = data.get("hash")

                        # Add hash if valid and not duplicate
                        if img_hash and str(img_hash) not in seen:
                            seen.add(str(img_hash))
                            normalized_hashes.append(str(img_hash))

                            # Limit to 6 screenshots per action
                            if len(normalized_hashes) >= 6:
                                break
                except (ValueError, TypeError):
                    logger.warning(f"Invalid image_index value: {idx}")
                    return None

            if normalized_hashes:
                logger.debug(
                    f"Resolved {len(normalized_hashes)} screenshot hashes from image_index {image_indices}"
                )
                return normalized_hashes

        logger.warning("Action missing valid image_index: %s", image_indices)
        return None

    def _calculate_action_timestamp(
        self, image_indices: List[int], screenshot_records: List[RawRecord]
    ) -> datetime:
        """
        Calculate action timestamp as earliest time among referenced screenshots

        Args:
            image_indices: Screenshot indices from LLM (e.g., [0, 1, 2])
            screenshot_records: List of screenshot RawRecords

        Returns:
            Earliest timestamp among referenced screenshots
        """
        if not image_indices:
            # Fallback: use earliest screenshot overall
            logger.warning("Action has empty image_index, using earliest screenshot")
            return min(r.timestamp for r in screenshot_records)

        # Validate indices
        max_idx = len(screenshot_records) - 1
        valid_indices = [i for i in image_indices if 0 <= i <= max_idx]

        if not valid_indices:
            logger.warning(
                f"Action has invalid image_indices {image_indices}, "
                f"max valid index is {max_idx}. Using earliest screenshot."
            )
            return min(r.timestamp for r in screenshot_records)

        if len(valid_indices) < len(image_indices):
            invalid = set(image_indices) - set(valid_indices)
            logger.warning(f"Ignoring invalid image indices: {invalid}")

        # Return earliest timestamp among referenced screenshots
        referenced_times = [screenshot_records[i].timestamp for i in valid_indices]
        return min(referenced_times)

    async def _validate_with_supervisor(
        self, actions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Validate actions with supervisor (placeholder for future implementation)

        Args:
            actions: Original action list

        Returns:
            Validated/revised action list
        """
        # TODO: Implement ActionSupervisor when needed
        # For now, just return original actions
        logger.debug("ActionAgent: Supervisor validation not yet implemented")
        return actions

    # ============ Scene-Based Extraction (Memory-Only) ============

    async def extract_and_save_actions_from_scenes(
        self,
        scenes: List[Dict[str, Any]],
        keyboard_records: Optional[List[RawRecord]] = None,
        mouse_records: Optional[List[RawRecord]] = None,
        enable_supervisor: bool = False,
    ) -> int:
        """
        Extract and save actions from pre-processed scene descriptions (memory-only, text-based)

        Args:
            scenes: List of scene description dictionaries (from RawAgent)
            keyboard_records: Keyboard event records for context
            mouse_records: Mouse event records for context
            enable_supervisor: Whether to enable supervisor validation (default False)

        Returns:
            Number of actions saved
        """
        if not scenes:
            return 0

        try:
            logger.debug(f"ActionAgent: Processing {len(scenes)} scenes")

            # Step 1: Extract actions from scenes using LLM (text-only, no images)
            actions = await self._extract_actions_from_scenes(
                scenes, keyboard_records, mouse_records, enable_supervisor
            )

            if not actions:
                logger.debug("ActionAgent: No actions extracted from scenes")
                return 0

            # Step 2: Resolve screenshot hashes from scene_index
            resolved_actions: List[Dict[str, Any]] = []
            for action_data in actions:
                action_hashes = self._resolve_action_screenshot_hashes_from_scenes(
                    action_data, scenes
                )
                if not action_hashes:
                    logger.warning(
                        "Dropping action: invalid scene_index in action '%s'",
                        action_data.get("title", "<no title>"),
                    )
                    self.stats["actions_filtered"] += 1
                    continue

                resolved_actions.append({"data": action_data, "hashes": action_hashes})

            # Step 3: Save actions to database
            saved_count = 0

            for resolved in resolved_actions:
                action_data = resolved["data"]
                action_hashes = resolved["hashes"]
                action_id = str(uuid.uuid4())

                # Calculate timestamp from scene_index
                scene_indices = action_data.get("scene_index", [])
                action_timestamp = self._calculate_action_timestamp_from_scenes(
                    scene_indices, scenes
                )

                # Save action to database
                await self.db.actions.save(
                    action_id=action_id,
                    title=action_data["title"],
                    description=action_data["description"],
                    keywords=action_data.get("keywords", []),
                    timestamp=action_timestamp.isoformat(),
                    screenshots=action_hashes,
                )

                saved_count += 1
                self.stats["actions_saved"] += 1

            logger.debug(f"ActionAgent: Saved {saved_count} actions to database")
            return saved_count

        except Exception as e:
            logger.error(f"ActionAgent: Failed to process actions from scenes: {e}", exc_info=True)
            return 0

    async def _extract_actions_from_scenes(
        self,
        scenes: List[Dict[str, Any]],
        keyboard_records: Optional[List[RawRecord]] = None,
        mouse_records: Optional[List[RawRecord]] = None,
        enable_supervisor: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Extract actions from scene descriptions using LLM (text-only, no images)

        Args:
            scenes: List of scene description dictionaries
            keyboard_records: Keyboard event records for context
            mouse_records: Mouse event records for context
            enable_supervisor: Whether to enable supervisor validation

        Returns:
            List of action dictionaries
        """
        if not scenes:
            return []

        try:
            logger.debug(f"ActionAgent: Extracting actions from {len(scenes)} scenes")

            # Import here to avoid circular dependency
            from processing.summarizer import EventSummarizer

            # Get current language from settings
            language = self._get_language()
            summarizer = EventSummarizer(language=language)
            result = await summarizer.extract_actions_from_scenes(
                scenes, keyboard_records, mouse_records
            )

            actions = result.get("actions", [])

            # Apply supervisor validation if enabled
            if enable_supervisor and actions:
                actions = await self._validate_with_supervisor(actions)

            self.stats["actions_extracted"] += len(actions)

            logger.debug(f"ActionAgent: Extracted {len(actions)} actions from scenes")
            return actions

        except Exception as e:
            logger.error(f"ActionAgent: Failed to extract actions from scenes: {e}", exc_info=True)
            return []

    def _resolve_action_screenshot_hashes_from_scenes(
        self, action_data: Dict[str, Any], scenes: List[Dict[str, Any]]
    ) -> Optional[List[str]]:
        """
        Resolve screenshot hashes based on scene_index from LLM response

        Args:
            action_data: Action data containing scene_index
            scenes: List of scene description dictionaries

        Returns:
            List of screenshot hashes filtered by scene_index
        """
        # Get scene_index from action data
        scene_indices = action_data.get("scene_index", [])

        # If scene_index is provided and valid
        if isinstance(scene_indices, list) and scene_indices:
            normalized_hashes: List[str] = []
            seen = set()

            for idx in scene_indices:
                try:
                    # Indices are zero-based
                    idx_int = int(idx)
                    if 0 <= idx_int < len(scenes):
                        scene = scenes[idx_int]
                        screenshot_hash = scene.get("screenshot_hash", "")

                        # Add hash if valid and not duplicate
                        if screenshot_hash and str(screenshot_hash) not in seen:
                            seen.add(str(screenshot_hash))
                            normalized_hashes.append(str(screenshot_hash))

                            # Limit to 6 screenshots per action
                            if len(normalized_hashes) >= 6:
                                break
                except (ValueError, TypeError, KeyError):
                    logger.warning(f"Invalid scene_index value: {idx}")
                    return None

            if normalized_hashes:
                logger.debug(
                    f"Resolved {len(normalized_hashes)} screenshot hashes from scene_index {scene_indices}"
                )
                return normalized_hashes

        logger.warning("Action missing valid scene_index: %s", scene_indices)
        return None

    def _calculate_action_timestamp_from_scenes(
        self, scene_indices: List[int], scenes: List[Dict[str, Any]]
    ) -> datetime:
        """
        Calculate action timestamp as earliest time among referenced scenes

        Args:
            scene_indices: Scene indices from LLM (e.g., [0, 1, 2])
            scenes: List of scene description dictionaries

        Returns:
            Earliest timestamp among referenced scenes
        """
        if not scene_indices:
            # Fallback: use earliest scene overall
            logger.warning("Action has empty scene_index, using earliest scene")
            timestamps = [
                datetime.fromisoformat(scene.get("timestamp", datetime.now().isoformat()))
                for scene in scenes
                if scene.get("timestamp")
            ]
            return min(timestamps) if timestamps else datetime.now()

        # Validate indices
        max_idx = len(scenes) - 1
        valid_indices = [i for i in scene_indices if 0 <= i <= max_idx]

        if not valid_indices:
            logger.warning(
                f"Action has invalid scene_indices {scene_indices}, "
                f"max valid index is {max_idx}. Using earliest scene."
            )
            timestamps = [
                datetime.fromisoformat(scene.get("timestamp", datetime.now().isoformat()))
                for scene in scenes
                if scene.get("timestamp")
            ]
            return min(timestamps) if timestamps else datetime.now()

        if len(valid_indices) < len(scene_indices):
            invalid = set(scene_indices) - set(valid_indices)
            logger.warning(f"Ignoring invalid scene indices: {invalid}")

        # Return earliest timestamp among referenced scenes
        referenced_times = []
        for i in valid_indices:
            timestamp_str = scenes[i].get("timestamp")
            if timestamp_str:
                try:
                    referenced_times.append(datetime.fromisoformat(timestamp_str))
                except (ValueError, TypeError):
                    logger.warning(f"Invalid timestamp format in scene {i}: {timestamp_str}")

        return min(referenced_times) if referenced_times else datetime.now()

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics information"""
        return {
            "language": self._get_language(),
            "stats": self.stats.copy(),
        }
