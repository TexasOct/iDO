"""
RawAgent - Extract structured scene descriptions from screenshots (memory-only)
Processes raw screenshots once, outputs structured text data for reuse by other agents
"""

from typing import Any, Dict, List, Optional

from core.json_parser import parse_json_from_response
from core.logger import get_logger
from core.models import RawRecord, RecordType
from core.settings import get_settings
from llm.manager import get_llm_manager
from llm.prompt_manager import PromptManager
from perception.image_manager import get_image_manager

# Image processing now handled by ProcessingPipeline's ImageFilter

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

        # Image preprocessing is now handled by ProcessingPipeline's ImageFilter
        # RawAgent only needs to retrieve preprocessed image data from records
        self.image_manager = get_image_manager()

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
                # Validate scene is a dictionary
                if not isinstance(scene, dict):
                    logger.warning(f"Scene is not a dict (got {type(scene).__name__}): {scene}")
                    continue

                try:
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
                except Exception as e:
                    logger.warning(f"Failed to process scene: {e}", exc_info=True)
                    continue

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

        # Add preprocessed screenshots
        # At this point, all screenshots have been filtered, optimized, and sampled by ProcessingPipeline
        screenshot_records = [
            r for r in records if r.type == RecordType.SCREENSHOT_RECORD
        ]

        screenshot_count = 0
        for record in screenshot_records:
            # Get preprocessed image data (already optimized by ImageFilter)
            img_data = self._get_preprocessed_image_data(record)

            if img_data:
                content_items.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{img_data}"},
                    }
                )
                screenshot_count += 1

        logger.debug(
            f"Built scene extraction messages with {screenshot_count} preprocessed screenshots"
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

    def _get_preprocessed_image_data(self, record: RawRecord) -> Optional[str]:
        """
        Get preprocessed image data from record

        ProcessingPipeline's ImageFilter has already:
        - Deduplicated screenshots
        - Filtered out static/blank screens
        - Compressed images
        - Stored optimized base64 in record.data["optimized_img_data"]

        And ImageSampler has already:
        - Applied time interval sampling
        - Limited to max count

        Args:
            record: RawRecord with preprocessed image data

        Returns:
            Optimized base64 image data, or None if not available
        """
        try:
            data = record.data or {}

            # First priority: preprocessed data from ImageFilter
            optimized_data = data.get("optimized_img_data")
            if optimized_data:
                return optimized_data

            # Fallback: original embedded data (if ImageFilter was skipped somehow)
            img_data = data.get("img_data")
            if img_data:
                logger.debug("Using original img_data (optimized_img_data not found)")
                return img_data

            # Last resort: load from cache/thumbnail
            img_hash = data.get("hash")
            if img_hash:
                cached = self.image_manager.get_from_cache(img_hash)
                if cached:
                    logger.debug("Using cached data (optimized_img_data not found)")
                    return cached

                thumbnail = self.image_manager.load_thumbnail_base64(img_hash)
                if thumbnail:
                    logger.debug("Using thumbnail data (optimized_img_data not found)")
                    return thumbnail

            logger.warning("No image data found in record")
            return None

        except Exception as e:
            logger.debug(f"Failed to get preprocessed image data: {e}")
            return None

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
