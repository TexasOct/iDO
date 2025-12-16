"""
KnowledgeAgent - Intelligent agent for knowledge extraction and periodic merging
Extracts knowledge from screenshots and merges related knowledge periodically
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.db import get_db
from core.json_parser import parse_json_from_response
from core.logger import get_logger
from core.models import RawRecord
from core.settings import get_settings
from llm.manager import get_llm_manager
from llm.prompt_manager import PromptManager

logger = get_logger(__name__)


class KnowledgeAgent:
    """
    Intelligent knowledge management agent

    Responsibilities:
    - Extract knowledge from screenshots
    - Periodically merge related knowledge
    - Quality filtering (minimum value criteria)
    """

    def __init__(
        self,
    ):
        """
        Initialize KnowledgeAgent
        """

        # Initialize components
        self.db = get_db()
        self.llm_manager = get_llm_manager()
        self.settings = get_settings()

        # Initialize prompt manager
        language = self.settings.get_language()
        self.prompt_manager = PromptManager(language=language)

        # Statistics
        self.stats: Dict[str, Any] = {
            "knowledge_extracted": 0,
        }

        logger.debug("KnowledgeAgent initialized")

    def _get_language(self) -> str:
        """Get current language setting from config with caching"""
        return self.settings.get_language()

    def _refresh_prompt_manager(self):
        """Refresh prompt manager if language changed"""
        current_language = self._get_language()
        if self.prompt_manager.language != current_language:
            self.prompt_manager = PromptManager(language=current_language)
            logger.debug(f"Prompt manager refreshed for language: {current_language}")

    async def _validate_with_supervisor(
        self, knowledge_list: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Validate knowledge with supervisor

        Args:
            knowledge_list: Original knowledge list

        Returns:
            Validated/revised knowledge list
        """
        try:
            from agents.supervisor import KnowledgeSupervisor

            language = self._get_language()
            supervisor = KnowledgeSupervisor(language=language)

            result = await supervisor.validate(knowledge_list)

            # Log validation results
            if not result.is_valid:
                logger.warning(
                    f"KnowledgeSupervisor found {len(result.issues)} issues: {result.issues}"
                )
                if result.suggestions:
                    logger.info(f"KnowledgeSupervisor suggestions: {result.suggestions}")

            # Use revised content if available, otherwise use original
            validated_knowledge = (
                result.revised_content if result.revised_content else knowledge_list
            )

            logger.debug(
                f"KnowledgeAgent: Supervisor validated {len(knowledge_list)} → {len(validated_knowledge)} knowledge items"
            )

            return validated_knowledge

        except Exception as e:
            logger.error(
                f"KnowledgeAgent: Supervisor validation failed: {e}", exc_info=True
            )
            # On supervisor failure, return original knowledge
            return knowledge_list

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics information"""
        return {
            "language": self._get_language(),
            "stats": self.stats.copy(),
        }

    # ============ Scene-Based Extraction (Memory-Only) ============

    async def extract_knowledge_from_scenes(
        self,
        scenes: List[Dict[str, Any]],
        keyboard_records: Optional[List[RawRecord]] = None,
        mouse_records: Optional[List[RawRecord]] = None,
        enable_supervisor: bool = True,
        source_action_id: Optional[str] = None,
    ) -> int:
        """
        Extract knowledge from pre-processed scene descriptions (memory-only, text-based)

        Args:
            scenes: List of scene description dictionaries
            keyboard_records: Keyboard event records for context
            mouse_records: Mouse event records for context
            enable_supervisor: Whether to enable supervisor validation (default True)
            source_action_id: Optional action ID that triggered this extraction

        Returns:
            Number of knowledge items extracted and saved
        """
        if not scenes:
            return 0

        try:
            logger.debug(f"KnowledgeAgent: Extracting knowledge from {len(scenes)} scenes")

            # Refresh prompt manager if language changed
            self._refresh_prompt_manager()

            # Step 1: Extract knowledge from scenes using LLM (text-only, no images)
            result = await self._extract_knowledge_from_scenes_llm(
                scenes, keyboard_records, mouse_records
            )

            knowledge_list = result.get("knowledge", [])

            if not knowledge_list:
                logger.debug("No knowledge extracted from scenes")
                return 0

            # Step 2: Apply supervisor validation
            if enable_supervisor:
                knowledge_list = await self._validate_with_supervisor(knowledge_list)

            # Step 3: Save knowledge items to database
            saved_count = 0
            for knowledge_data in knowledge_list:
                knowledge_id = str(uuid.uuid4())

                # Calculate timestamp from scenes
                scene_timestamp = self._calculate_knowledge_timestamp_from_scenes(scenes)

                await self.db.knowledge.save(
                    knowledge_id=knowledge_id,
                    title=knowledge_data.get("title", ""),
                    description=knowledge_data.get("description", ""),
                    keywords=knowledge_data.get("keywords", []),
                    created_at=scene_timestamp.isoformat(),
                    source_action_id=source_action_id,  # Link to action if provided
                )
                saved_count += 1

            self.stats["knowledge_extracted"] += saved_count

            logger.debug(
                f"KnowledgeAgent: Extracted and saved {saved_count} knowledge items from scenes"
            )

            # Step 4: Scenes auto garbage-collected (memory-only, no cleanup needed)
            return saved_count

        except Exception as e:
            logger.error(
                f"KnowledgeAgent: Failed to extract knowledge from scenes: {e}",
                exc_info=True,
            )
            return 0

    async def _extract_knowledge_from_scenes_llm(
        self,
        scenes: List[Dict[str, Any]],
        keyboard_records: Optional[List[RawRecord]] = None,
        mouse_records: Optional[List[RawRecord]] = None,
    ) -> Dict[str, Any]:
        """
        Call LLM to extract knowledge from scene descriptions

        Args:
            scenes: List of scene description dictionaries
            keyboard_records: Keyboard event records for context
            mouse_records: Mouse event records for context

        Returns:
            {"knowledge": [...]}
        """
        try:
            # Build input usage hint
            input_usage_hint = self._build_input_usage_hint(keyboard_records, mouse_records)

            # Build messages
            messages = self._build_knowledge_from_scenes_messages(scenes, input_usage_hint)

            # Get configuration parameters
            config_params = self.prompt_manager.get_config_params("knowledge_from_scenes")

            # Call LLM
            response = await self.llm_manager.chat_completion(messages, **config_params)
            content = response.get("content", "").strip()

            # Parse JSON
            result = parse_json_from_response(content)

            if not isinstance(result, dict):
                logger.warning(f"LLM returned incorrect format: {content[:200]}")
                return {"knowledge": []}

            knowledge = result.get("knowledge", [])
            logger.debug(f"Knowledge extraction from scenes completed: {len(knowledge)} knowledge items")

            return {"knowledge": knowledge}

        except Exception as e:
            logger.error(f"Knowledge extraction from scenes failed: {e}", exc_info=True)
            return {"knowledge": []}

    def _build_input_usage_hint(
        self,
        keyboard_records: Optional[List[RawRecord]] = None,
        mouse_records: Optional[List[RawRecord]] = None,
    ) -> str:
        """
        Build keyboard/mouse activity hint text

        Args:
            keyboard_records: Keyboard event records
            mouse_records: Mouse event records

        Returns:
            Activity hint string
        """
        has_keyboard = keyboard_records and len(keyboard_records) > 0
        has_mouse = mouse_records and len(mouse_records) > 0

        # Get perception settings
        keyboard_enabled = self.settings.get("perception.keyboard_enabled", True)
        mouse_enabled = self.settings.get("perception.mouse_enabled", True)

        hints = []
        language = self._get_language()

        # Keyboard perception status
        if keyboard_enabled:
            if has_keyboard:
                hints.append(
                    "用户有在使用键盘" if language == "zh" else "User has keyboard activity"
                )
            else:
                hints.append(
                    "用户没有在使用键盘" if language == "zh" else "User has no keyboard activity"
                )
        else:
            hints.append(
                "键盘感知已禁用，无法获取键盘输入信息"
                if language == "zh"
                else "Keyboard perception is disabled, no keyboard input available"
            )

        # Mouse perception status
        if mouse_enabled:
            if has_mouse:
                hints.append(
                    "用户有在使用鼠标" if language == "zh" else "User has mouse activity"
                )
            else:
                hints.append(
                    "用户没有在使用鼠标" if language == "zh" else "User has no mouse activity"
                )
        else:
            hints.append(
                "鼠标感知已禁用，无法获取鼠标移动信息"
                if language == "zh"
                else "Mouse perception is disabled, no mouse movement available"
            )

        return "; ".join(hints)

    def _build_knowledge_from_scenes_messages(
        self,
        scenes: List[Dict[str, Any]],
        input_usage_hint: str,
    ) -> List[Dict[str, Any]]:
        """
        Build knowledge extraction messages from scenes (text-only, no images)

        Args:
            scenes: List of scene description dictionaries
            input_usage_hint: Keyboard/mouse activity hint

        Returns:
            Message list
        """
        # Get system prompt
        system_prompt = self.prompt_manager.get_system_prompt("knowledge_from_scenes")

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
            "knowledge_from_scenes",
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

    def _calculate_knowledge_timestamp_from_scenes(
        self, scenes: List[Dict[str, Any]]
    ) -> datetime:
        """
        Calculate knowledge timestamp as earliest time among scenes

        Args:
            scenes: List of scene description dictionaries

        Returns:
            Earliest timestamp among scenes
        """
        if not scenes:
            return datetime.now()

        timestamps = []
        for scene in scenes:
            timestamp_str = scene.get("timestamp")
            if timestamp_str:
                try:
                    timestamps.append(datetime.fromisoformat(timestamp_str))
                except (ValueError, TypeError):
                    logger.warning(
                        f"Invalid timestamp format in scene: {timestamp_str}"
                    )

        return min(timestamps) if timestamps else datetime.now()

