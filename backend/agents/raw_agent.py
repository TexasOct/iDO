"""
RawAgent - Extract structured scene descriptions from screenshots (memory-only)
Processes raw screenshots once, outputs structured text data for reuse by other agents
"""

import base64
from typing import Any, Dict, List, Optional

from core.json_parser import parse_json_from_response
from core.logger import get_logger
from core.models import RawRecord, RecordType
from core.settings import get_settings
from llm.manager import get_llm_manager
from llm.prompt_manager import PromptManager
from processing.image_processing import get_image_compressor
from processing.image_manager import get_image_manager

logger = get_logger(__name__)


class RawAgent:
    """
    Raw scene extraction agent - Converts screenshots to structured text descriptions

    This agent processes raw screenshots and extracts high-level semantic information
    as structured text. The output is kept in memory and passed to ActionAgent and
    KnowledgeAgent, eliminating the need to send images to LLM multiple times.

    Flow:
        Raw Screenshots → RawAgent (LLM + images) → Scene Descriptions (text)
            → ActionAgent (text-only)
            → KnowledgeAgent (text-only)
    """

    def __init__(self, max_screenshots: int = 20):
        """
        Initialize RawAgent

        Args:
            max_screenshots: Maximum number of screenshots to send to LLM per extraction
        """
        self.llm_manager = get_llm_manager()
        self.settings = get_settings()
        self.max_screenshots = max_screenshots

        # Initialize prompt manager
        language = self.settings.get_language()
        self.prompt_manager = PromptManager(language=language)

        # Initialize image manager and compressor
        self.image_manager = get_image_manager()
        self.image_compressor = None

        try:
            self.image_compressor = get_image_compressor()
            logger.debug("RawAgent: Image compression enabled")
        except Exception as exc:
            logger.warning(
                f"RawAgent: Failed to initialize image compression, will skip compression: {exc}"
            )
            self.image_compressor = None

        # Statistics
        self.stats: Dict[str, Any] = {
            "scenes_extracted": 0,
            "extraction_rounds": 0,
        }

        logger.debug(f"RawAgent initialized (max_screenshots: {max_screenshots})")

    def _get_language(self) -> str:
        """Get current language setting from config"""
        return self.settings.get_language()

    def _refresh_prompt_manager(self):
        """Refresh prompt manager if language changed"""
        current_language = self._get_language()
        if self.prompt_manager.language != current_language:
            self.prompt_manager = PromptManager(language=current_language)
            logger.debug(f"Prompt manager refreshed for language: {current_language}")

    async def extract_scenes(
        self,
        records: List[RawRecord],
        keyboard_records: Optional[List[RawRecord]] = None,
        mouse_records: Optional[List[RawRecord]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Extract scene descriptions from raw records (screenshots)

        Args:
            records: List of raw records (mainly screenshots)
            keyboard_records: Keyboard event records for timestamp extraction
            mouse_records: Mouse event records for timestamp extraction

        Returns:
            List of scene description dictionaries:
            [
                {
                    "screenshot_index": 0,
                    "screenshot_hash": "abc123...",
                    "timestamp": "2025-01-01T12:00:00",
                    "visual_summary": "Code editor showing...",
                    "detected_text": "function login() {...}",
                    "ui_elements": "Editor, file explorer, terminal",
                    "application_context": "VS Code, working on auth",
                    "inferred_activity": "Writing authentication code",
                    "focus_areas": "Code editing area"
                },
                ...
            ]
        """
        if not records:
            return []

        try:
            logger.debug(f"RawAgent: Extracting scenes from {len(records)} records")

            # Refresh prompt manager if language changed
            self._refresh_prompt_manager()

            # Build input usage hint from keyboard/mouse records
            input_usage_hint = self._build_input_usage_hint(keyboard_records, mouse_records)

            # Build messages (including screenshots)
            messages = await self._build_scene_extraction_messages(
                records, input_usage_hint
            )

            # Get configuration parameters
            config_params = self.prompt_manager.get_config_params("raw_extraction")

            # Call LLM directly
            response = await self.llm_manager.chat_completion(messages, **config_params)
            content = response.get("content", "").strip()

            # Parse JSON
            result = parse_json_from_response(content)

            if not isinstance(result, dict):
                logger.warning(f"LLM returned incorrect format: {content[:200]}")
                return []

            scenes = result.get("scenes", [])

            # Enrich scene data with screenshot hashes and timestamps
            screenshot_records = [
                r for r in records if r.type == RecordType.SCREENSHOT_RECORD
            ]

            enriched_scenes = []
            for scene in scenes:
                screenshot_index = scene.get("screenshot_index", 0)

                # Validate index
                if 0 <= screenshot_index < len(screenshot_records):
                    screenshot_record = screenshot_records[screenshot_index]
                    screenshot_hash = screenshot_record.data.get("hash", "")
                    timestamp = screenshot_record.timestamp.isoformat()

                    enriched_scenes.append(
                        {
                            "screenshot_index": screenshot_index,
                            "screenshot_hash": screenshot_hash,
                            "timestamp": timestamp,
                            "visual_summary": scene.get("visual_summary", ""),
                            "detected_text": scene.get("detected_text", ""),
                            "ui_elements": scene.get("ui_elements", ""),
                            "application_context": scene.get("application_context", ""),
                            "inferred_activity": scene.get("inferred_activity", ""),
                            "focus_areas": scene.get("focus_areas", ""),
                        }
                    )
                else:
                    logger.warning(
                        f"Invalid screenshot_index {screenshot_index} in scene (max {len(screenshot_records)-1})"
                    )

            self.stats["scenes_extracted"] += len(enriched_scenes)
            self.stats["extraction_rounds"] += 1

            logger.debug(f"RawAgent: Extracted {len(enriched_scenes)} scene descriptions")
            return enriched_scenes

        except Exception as e:
            logger.error(f"RawAgent: Failed to extract scenes: {e}", exc_info=True)
            return []

    async def _build_scene_extraction_messages(
        self,
        records: List[RawRecord],
        input_usage_hint: str,
    ) -> List[Dict[str, Any]]:
        """
        Build scene extraction messages (including system prompt, user prompt, screenshots)

        Args:
            records: Record list (mainly screenshots)
            input_usage_hint: Keyboard/mouse activity hint

        Returns:
            Message list
        """
        # Get system prompt
        system_prompt = self.prompt_manager.get_system_prompt("raw_extraction")

        # Get user prompt template and format
        user_prompt_base = self.prompt_manager.get_user_prompt(
            "raw_extraction",
            "user_prompt_template",
            input_usage_hint=input_usage_hint,
        )

        # Build message content (text + screenshots)
        content_items = [{"type": "text", "text": user_prompt_base}]

        # Add screenshots (limit to avoid API constraints)
        screenshot_records = [
            r for r in records if r.type == RecordType.SCREENSHOT_RECORD
        ]

        # Use configured max_screenshots limit
        max_screenshots = self.max_screenshots
        screenshot_count = 0

        for idx, record in enumerate(screenshot_records):
            if screenshot_count >= max_screenshots:
                logger.warning(
                    f"Scene extraction: Reached max screenshot limit ({max_screenshots}), "
                    f"truncating from {len(screenshot_records)} to {max_screenshots}"
                )
                break

            img_data = self._get_record_image_data(record, is_first=(idx == 0))
            if img_data:
                content_items.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{img_data}"},
                    }
                )
                screenshot_count += 1

        logger.debug(
            f"Built scene extraction messages: {screenshot_count} screenshots "
            f"(total available: {len(screenshot_records)})"
        )

        # Build complete messages
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content_items},
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
                    f"RawAgent: Image compression completed "
                    f"{original_tokens} → {optimized_tokens} tokens"
                )
            return base64.b64encode(optimized_bytes).decode("utf-8")
        except Exception as exc:
            logger.debug(
                f"RawAgent: Image compression failed, using original image: {exc}"
            )
            return base64_data

    def _format_timestamp(self, dt) -> str:
        """Format datetime to HH:MM:SS for prompts"""
        from datetime import datetime
        if isinstance(dt, datetime):
            return dt.strftime("%H:%M:%S")
        return str(dt)

    def _format_time_range(self, start_dt, end_dt) -> str:
        """Format time range for prompts"""
        return f"{self._format_timestamp(start_dt)}-{self._format_timestamp(end_dt)}"

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics information"""
        return {
            "language": self._get_language(),
            "stats": self.stats.copy(),
        }
