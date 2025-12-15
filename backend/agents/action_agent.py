"""
ActionAgent - Intelligent agent for complete action extraction and saving
Handles the complete flow: raw_records -> actions (extract + save)
"""

import base64
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.db import get_db
from core.json_parser import parse_json_from_response
from core.logger import get_logger
from core.models import RawRecord, RecordType
from core.settings import get_settings
from llm.manager import get_llm_manager
from llm.prompt_manager import PromptManager
from perception.image_manager import get_image_manager
from processing.image import get_image_compressor

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

        # Initialize prompt manager
        language = self.settings.get_language()
        self.prompt_manager = PromptManager(language=language)

        # Initialize image manager and compressor
        self.image_manager = get_image_manager()
        self.image_compressor = None

        try:
            self.image_compressor = get_image_compressor()
            logger.debug("ActionAgent: Image compression enabled")
        except Exception as exc:
            logger.warning(
                f"ActionAgent: Failed to initialize image compression, will skip compression: {exc}"
            )
            self.image_compressor = None

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

    def _refresh_prompt_manager(self):
        """Refresh prompt manager if language changed"""
        current_language = self._get_language()
        if self.prompt_manager.language != current_language:
            self.prompt_manager = PromptManager(language=current_language)
            logger.debug(f"Prompt manager refreshed for language: {current_language}")

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

            # Refresh prompt manager if language changed
            self._refresh_prompt_manager()

            # Build messages (including screenshots)
            messages = await self._build_action_extraction_messages(
                records, input_usage_hint, keyboard_records, mouse_records
            )

            # Get configuration parameters
            config_params = self.prompt_manager.get_config_params("action_extraction")

            # Call LLM directly
            response = await self.llm_manager.chat_completion(messages, **config_params)
            content = response.get("content", "").strip()

            # Parse JSON
            result = parse_json_from_response(content)

            if not isinstance(result, dict):
                logger.warning(f"LLM returned incorrect format: {content[:200]}")
                return []

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

            # Refresh prompt manager if language changed
            self._refresh_prompt_manager()

            # Build input usage hint from keyboard/mouse records
            input_usage_hint = self._build_input_usage_hint(keyboard_records, mouse_records)

            # Build messages (text-only, no images)
            messages = self._build_action_from_scenes_messages(
                scenes, input_usage_hint
            )

            # Get configuration parameters
            config_params = self.prompt_manager.get_config_params("action_from_scenes")

            # Call LLM directly
            response = await self.llm_manager.chat_completion(messages, **config_params)
            content = response.get("content", "").strip()

            # Parse JSON
            result = parse_json_from_response(content)

            if not isinstance(result, dict):
                logger.warning(f"LLM returned incorrect format: {content[:200]}")
                return []

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

    async def _build_action_extraction_messages(
        self,
        records: List[RawRecord],
        input_usage_hint: str,
        keyboard_records: Optional[List[RawRecord]] = None,
        mouse_records: Optional[List[RawRecord]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Build action extraction messages (including system prompt, user prompt, screenshots)

        Args:
            records: Record list (mainly screenshots)
            input_usage_hint: Keyboard/mouse activity hint (legacy)
            keyboard_records: Keyboard event records for timestamp extraction
            mouse_records: Mouse event records for timestamp extraction

        Returns:
            Message list
        """
        # Get system prompt
        system_prompt = self.prompt_manager.get_system_prompt("action_extraction")

        # Get user prompt template and format
        user_prompt_base = self.prompt_manager.get_user_prompt(
            "action_extraction",
            "user_prompt_template",
            input_usage_hint=input_usage_hint,
        )

        # Build activity context with timestamp information
        context_parts = []

        if keyboard_records:
            keyboard_times = [r.timestamp for r in keyboard_records]
            if keyboard_times:
                time_range = self._format_time_range(
                    min(keyboard_times), max(keyboard_times)
                )
                context_parts.append(f"Keyboard activity: {time_range}")

        if mouse_records:
            mouse_times = [r.timestamp for r in mouse_records]
            if mouse_times:
                time_range = self._format_time_range(
                    min(mouse_times), max(mouse_times)
                )
                context_parts.append(f"Mouse activity: {time_range}")

        # Build screenshot list with timestamps
        screenshot_records = [
            r for r in records if r.type == RecordType.SCREENSHOT_RECORD
        ]
        screenshot_list_lines = [
            f"Image {i} captured at {self._format_timestamp(r.timestamp)}"
            for i, r in enumerate(screenshot_records[:20])
        ]

        # Construct enhanced user prompt with timestamp information
        enhanced_prompt_parts = []

        if context_parts:
            enhanced_prompt_parts.append("Activity Context:")
            enhanced_prompt_parts.extend(context_parts)
            enhanced_prompt_parts.append("")

        if screenshot_list_lines:
            enhanced_prompt_parts.append("Screenshots:")
            enhanced_prompt_parts.extend(screenshot_list_lines)
            enhanced_prompt_parts.append("")

        enhanced_prompt_parts.append(user_prompt_base)

        user_prompt = "\n".join(enhanced_prompt_parts)

        # Build content (text + screenshots)
        content_items = []

        # Add enhanced user prompt text
        content_items.append({"type": "text", "text": user_prompt})

        # Add screenshots
        screenshot_count = 0
        max_screenshots = 20
        for record in records:
            if (
                record.type == RecordType.SCREENSHOT_RECORD
                and screenshot_count < max_screenshots
            ):
                is_first_image = screenshot_count == 0
                img_data = self._get_record_image_data(record, is_first=is_first_image)
                if img_data:
                    content_items.append(
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{img_data}"},
                        }
                    )
                    screenshot_count += 1

        logger.debug(f"Built extraction messages: {screenshot_count} screenshots")

        # Build complete messages
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content_items},
        ]

        return messages

    def _build_action_from_scenes_messages(
        self,
        scenes: List[Dict[str, Any]],
        input_usage_hint: str,
    ) -> List[Dict[str, Any]]:
        """
        Build action extraction messages from scenes (text-only, no images)

        Args:
            scenes: List of scene description dictionaries
            input_usage_hint: Keyboard/mouse activity hint

        Returns:
            Message list
        """
        # Get system prompt
        system_prompt = self.prompt_manager.get_system_prompt("action_from_scenes")

        # Format scenes as text
        scenes_text_parts = []
        for scene in scenes:
            idx = scene.get("screenshot_index", 0)
            timestamp = scene.get("timestamp", "")
            visual_summary = scene.get("visual_summary", "")
            detected_text = scene.get("detected_text", "")
            ui_elements = scene.get("ui_elements", "")
            application_context = scene.get("application_context", "")
            inferred_activity = scene.get("inferred_activity", "")
            focus_areas = scene.get("focus_areas", "")

            scene_text = f"""Scene {idx} (timestamp: {timestamp}):
- Visual summary: {visual_summary}
- Application context: {application_context}
- Detected text: {detected_text}
- UI elements: {ui_elements}
- Inferred activity: {inferred_activity}
- Focus areas: {focus_areas}"""

            scenes_text_parts.append(scene_text)

        scenes_text = "\n\n".join(scenes_text_parts)

        # Get user prompt template and format
        user_prompt = self.prompt_manager.get_user_prompt(
            "action_from_scenes",
            "user_prompt_template",
            scenes_text=scenes_text,
            input_usage_hint=input_usage_hint,
        )

        # Build complete messages (text-only, no images)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        return messages

    def _build_input_usage_hint(
        self,
        keyboard_records: Optional[List[RawRecord]] = None,
        mouse_records: Optional[List[RawRecord]] = None,
    ) -> str:
        """
        Build input usage hint from keyboard/mouse records

        Args:
            keyboard_records: Keyboard event records
            mouse_records: Mouse event records

        Returns:
            Input usage hint string
        """
        context_parts = []

        if keyboard_records:
            keyboard_times = [r.timestamp for r in keyboard_records]
            if keyboard_times:
                time_range = self._format_time_range(
                    min(keyboard_times), max(keyboard_times)
                )
                context_parts.append(f"Keyboard activity: {time_range}")

        if mouse_records:
            mouse_times = [r.timestamp for r in mouse_records]
            if mouse_times:
                time_range = self._format_time_range(
                    min(mouse_times), max(mouse_times)
                )
                context_parts.append(f"Mouse activity: {time_range}")

        return "\n".join(context_parts) if context_parts else "No keyboard/mouse activity data available."

    def _get_record_image_data(
        self, record: RawRecord, *, is_first: bool = False
    ) -> Optional[str]:
        """Get screenshot record's base64 data and perform necessary compression"""
        try:
            data = record.data or {}
            # Directly read base64 carried in the record
            img_data = data.get("img_data")
            if img_data:
                return self._optimize_image_base64(img_data, is_first=is_first)
            img_hash = data.get("hash")
            if not img_hash:
                return None

            # Priority read from memory cache
            cached = self.image_manager.get_from_cache(img_hash)
            if cached:
                return self._optimize_image_base64(cached, is_first=is_first)

            # Fallback to read thumbnail
            thumbnail = self.image_manager.load_thumbnail_base64(img_hash)
            if thumbnail:
                return self._optimize_image_base64(thumbnail, is_first=is_first)
            return None
        except Exception as e:
            logger.debug(f"Failed to get screenshot data: {e}")
            return None

    def _optimize_image_base64(self, base64_data: str, *, is_first: bool) -> str:
        """Perform compression optimization on base64 image data"""
        if not base64_data or not self.image_compressor:
            return base64_data

        try:
            img_bytes = base64.b64decode(base64_data)
            optimized_bytes, meta = self.image_compressor.compress(img_bytes)

            if optimized_bytes and optimized_bytes != img_bytes:
                # Calculate token estimates
                original_tokens = int(len(img_bytes) / 1024 * 85)
                optimized_tokens = int(len(optimized_bytes) / 1024 * 85)
                logger.debug(
                    f"ActionAgent: Image compression completed "
                    f"{original_tokens} → {optimized_tokens} tokens"
                )
            return base64.b64encode(optimized_bytes).decode("utf-8")
        except Exception as exc:
            logger.debug(
                f"ActionAgent: Image compression failed, using original image: {exc}"
            )
            return base64_data

    def _format_timestamp(self, dt: datetime) -> str:
        """Format datetime to HH:MM:SS for prompts"""
        return dt.strftime("%H:%M:%S")

    def _format_time_range(self, start_dt: datetime, end_dt: datetime) -> str:
        """Format time range for prompts"""
        return f"{self._format_timestamp(start_dt)}-{self._format_timestamp(end_dt)}"

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics information"""
        return {
            "language": self._get_language(),
            "stats": self.stats.copy(),
        }
