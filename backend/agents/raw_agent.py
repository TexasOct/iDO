"""
RawAgent - Extract structured scene descriptions from screenshots (memory-only)
Processes raw screenshots once, outputs structured text data for reuse by other agents
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from core.logger import get_logger
from core.models import RawRecord, RecordType
from core.settings import get_settings
from llm.manager import get_llm_manager

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

    def __init__(self):
        """Initialize RawAgent"""
        self.llm_manager = get_llm_manager()
        self.settings = get_settings()

        # Statistics
        self.stats: Dict[str, Any] = {
            "scenes_extracted": 0,
            "extraction_rounds": 0,
        }

        logger.debug("RawAgent initialized")

    def _get_language(self) -> str:
        """Get current language setting from config"""
        return self.settings.get_language()

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

            # Import here to avoid circular dependency
            from processing.summarizer import EventSummarizer

            # Get current language from settings
            language = self._get_language()
            summarizer = EventSummarizer(language=language)

            # Call EventSummarizer to extract scenes
            result = await summarizer.extract_scenes_only(
                records, keyboard_records, mouse_records
            )

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

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics information"""
        return {
            "language": self._get_language(),
            "stats": self.stats.copy(),
        }
