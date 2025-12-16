"""
TodoAgent - Intelligent agent for TODO extraction and periodic merging
Extracts TODOs from screenshots and merges related TODOs periodically
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


class TodoAgent:
    """
    Intelligent TODO management agent

    Responsibilities:
    - Extract TODOs from screenshots
    - Periodically merge related TODOs
    - Quality filtering (minimum actionability criteria)
    """

    def __init__(
        self,
    ):
        """
        Initialize TodoAgent
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
            "todos_extracted": 0,
        }

        logger.debug("TodoAgent initialized")

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
        self, todos: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Validate TODOs with supervisor

        Args:
            todos: Original TODO list

        Returns:
            Validated/revised TODO list
        """
        try:
            from agents.supervisor import TodoSupervisor

            language = self._get_language()
            supervisor = TodoSupervisor(language=language)

            result = await supervisor.validate(todos)

            # Log validation results
            if not result.is_valid:
                logger.warning(
                    f"TodoSupervisor found {len(result.issues)} issues: {result.issues}"
                )
                if result.suggestions:
                    logger.info(f"TodoSupervisor suggestions: {result.suggestions}")

            # Use revised content if available, otherwise use original
            validated_todos = result.revised_content if result.revised_content else todos

            logger.debug(
                f"TodoAgent: Supervisor validated {len(todos)} → {len(validated_todos)} TODOs"
            )

            return validated_todos

        except Exception as e:
            logger.error(f"TodoAgent: Supervisor validation failed: {e}", exc_info=True)
            # On supervisor failure, return original todos
            return todos

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics information"""
        return {
            "language": self._get_language(),
            "stats": self.stats.copy(),
        }

    # ============ Scene-Based Extraction (Memory-Only) ============

    async def extract_todos_from_scenes(
        self,
        scenes: List[Dict[str, Any]],
        keyboard_records: Optional[List[RawRecord]] = None,
        mouse_records: Optional[List[RawRecord]] = None,
        enable_supervisor: bool = True,
    ) -> int:
        """
        Extract TODOs from pre-processed scene descriptions (memory-only, text-based)

        Args:
            scenes: List of scene description dictionaries
            keyboard_records: Keyboard event records for context
            mouse_records: Mouse event records for context
            enable_supervisor: Whether to enable supervisor validation (default True)

        Returns:
            Number of TODO items extracted and saved
        """
        if not scenes:
            return 0

        try:
            logger.debug(f"TodoAgent: Extracting TODOs from {len(scenes)} scenes")

            # Refresh prompt manager if language changed
            self._refresh_prompt_manager()

            # Step 1: Extract TODOs from scenes using LLM (text-only, no images)
            result = await self._extract_todos_from_scenes_llm(
                scenes, keyboard_records, mouse_records
            )

            todos = result.get("todos", [])

            if not todos:
                logger.debug("No TODOs extracted from scenes")
                return 0

            # Step 2: Apply supervisor validation
            if enable_supervisor:
                todos = await self._validate_with_supervisor(todos)

            # Step 3: Save TODO items to database
            saved_count = 0
            for todo_data in todos:
                todo_id = str(uuid.uuid4())

                # Calculate timestamp from scenes
                todo_timestamp = self._calculate_todo_timestamp_from_scenes(scenes)

                await self.db.todos.save(
                    todo_id=todo_id,
                    title=todo_data.get("title", ""),
                    description=todo_data.get("description", ""),
                    keywords=todo_data.get("keywords", []),
                    created_at=todo_timestamp.isoformat(),
                    completed=todo_data.get("completed", False),
                )
                saved_count += 1

            self.stats["todos_extracted"] += saved_count

            logger.debug(
                f"TodoAgent: Extracted and saved {saved_count} TODO items from scenes"
            )

            # Step 4: Scenes auto garbage-collected (memory-only, no cleanup needed)
            return saved_count

        except Exception as e:
            logger.error(
                f"TodoAgent: Failed to extract TODOs from scenes: {e}",
                exc_info=True,
            )
            return 0

    async def _extract_todos_from_scenes_llm(
        self,
        scenes: List[Dict[str, Any]],
        keyboard_records: Optional[List[RawRecord]] = None,
        mouse_records: Optional[List[RawRecord]] = None,
    ) -> Dict[str, Any]:
        """
        Call LLM to extract TODOs from scene descriptions

        Args:
            scenes: List of scene description dictionaries
            keyboard_records: Keyboard event records for context
            mouse_records: Mouse event records for context

        Returns:
            {"todos": [...]}
        """
        try:
            # Build input usage hint
            input_usage_hint = self._build_input_usage_hint(keyboard_records, mouse_records)

            # Build messages
            messages = self._build_todos_from_scenes_messages(scenes, input_usage_hint)

            # Get configuration parameters
            config_params = self.prompt_manager.get_config_params("todo_from_scenes")

            # Call LLM
            response = await self.llm_manager.chat_completion(messages, **config_params)
            content = response.get("content", "").strip()

            # Parse JSON
            result = parse_json_from_response(content)

            if not isinstance(result, dict):
                logger.warning(f"LLM returned incorrect format: {content[:200]}")
                return {"todos": []}

            todos = result.get("todos", [])
            logger.debug(f"TODO extraction from scenes completed: {len(todos)} TODO items")

            return {"todos": todos}

        except Exception as e:
            logger.error(f"TODO extraction from scenes failed: {e}", exc_info=True)
            return {"todos": []}

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

    def _build_todos_from_scenes_messages(
        self,
        scenes: List[Dict[str, Any]],
        input_usage_hint: str,
    ) -> List[Dict[str, Any]]:
        """
        Build TODO extraction messages from scenes (text-only, no images)

        Args:
            scenes: List of scene description dictionaries
            input_usage_hint: Keyboard/mouse activity hint

        Returns:
            Message list
        """
        # Get system prompt
        system_prompt = self.prompt_manager.get_system_prompt("todo_from_scenes")

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
            "todo_from_scenes",
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

    def _calculate_todo_timestamp_from_scenes(
        self, scenes: List[Dict[str, Any]]
    ) -> datetime:
        """
        Calculate TODO timestamp as earliest time among scenes

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

