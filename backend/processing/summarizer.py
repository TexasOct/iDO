"""
EventSummarizer (new architecture)
Handles action extraction, event aggregation, and provides merge capabilities for agents
"""

import base64
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from core.json_parser import parse_json_from_response
from core.logger import get_logger
from core.models import RawRecord, RecordType
from llm.manager import get_llm_manager
from llm.prompt_manager import get_prompt_manager
from processing.image_compression import get_image_optimizer
from processing.image_manager import get_image_manager

logger = get_logger(__name__)


class EventSummarizer:
    """Event processing and aggregation handler

    Provides action extraction, event aggregation, and merge utilities.
    Note: Knowledge and todo extraction/merge are delegated to dedicated agents.
    """

    def __init__(self, language: str = "zh"):
        """
        Args:
            language: Language setting (zh | en)
        """
        self.llm_manager = get_llm_manager()
        self.prompt_manager = get_prompt_manager(language)
        self.language = language
        self.image_manager = get_image_manager()
        self.image_optimizer = None

        try:
            self.image_optimizer = get_image_optimizer()
            logger.debug("EventSummarizer: Image optimization enabled")
        except Exception as exc:
            logger.warning(
                f"EventSummarizer: Failed to initialize image optimization, will skip compression: {exc}"
            )
            self.image_optimizer = None

    # ============ Action Extraction ============
    # Note: Knowledge and todo extraction are now handled by dedicated agents

    async def extract_actions_only(
        self,
        records: List[RawRecord],
        input_usage_hint: str = "",
        keyboard_records: Optional[List[RawRecord]] = None,
        mouse_records: Optional[List[RawRecord]] = None,
    ) -> Dict[str, Any]:
        """
        Extract actions from raw_records (knowledge and todos handled by dedicated agents)

        Args:
            records: List of raw records (mainly screenshots)
            input_usage_hint: Keyboard/mouse activity hint (legacy)
            keyboard_records: Keyboard event records for timestamp extraction
            mouse_records: Mouse event records for timestamp extraction

        Returns:
            {"actions": [...]}
        """
        if not records:
            return {"actions": []}

        try:
            logger.debug(f"Starting to extract actions, total {len(records)} records")

            # Build messages (including screenshots)
            messages = await self._build_action_extraction_messages(
                records, input_usage_hint, keyboard_records, mouse_records
            )

            # Get configuration parameters
            config_params = self.prompt_manager.get_config_params("action_extraction")

            # Call LLM (manager ensures latest activated model is used)
            response = await self.llm_manager.chat_completion(messages, **config_params)
            content = response.get("content", "").strip()

            # Parse JSON
            result = parse_json_from_response(content)

            if not isinstance(result, dict):
                logger.warning(f"LLM returned incorrect format: {content[:200]}")
                return {"actions": []}

            actions = result.get("actions", [])

            logger.debug(f"Action extraction completed: {len(actions)} actions")

            return {"actions": actions}

        except Exception as e:
            logger.error(f"Action extraction failed: {e}", exc_info=True)
            return {"actions": []}

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
        if not base64_data or not self.image_optimizer:
            return base64_data

        try:
            img_bytes = base64.b64decode(base64_data)
            optimized_bytes, meta = self.image_optimizer.optimize(
                img_bytes, is_first=is_first
            )

            if optimized_bytes and optimized_bytes != img_bytes:
                logger.debug(
                    "EventSummarizer: Image compression completed "
                    f"{meta.get('original_tokens', 0)} → {meta.get('optimized_tokens', 0)} tokens"
                )
            return base64.b64encode(optimized_bytes).decode("utf-8")
        except Exception as exc:
            logger.debug(
                f"EventSummarizer: Image compression failed, using original image: {exc}"
            )
            return base64_data

    def _format_timestamp(self, dt: datetime) -> str:
        """Format datetime to HH:MM:SS for prompts."""
        return dt.strftime("%H:%M:%S")

    def _format_time_range(self, start_dt: datetime, end_dt: datetime) -> str:
        """Format time range for prompts."""
        return f"{self._format_timestamp(start_dt)}-{self._format_timestamp(end_dt)}"

    async def extract_todos_only(
        self,
        records: List[RawRecord],
        keyboard_records: Optional[List[RawRecord]] = None,
        mouse_records: Optional[List[RawRecord]] = None,
    ) -> Dict[str, Any]:
        """
        Extract only todos from raw_records (used by TodoAgent)

        Args:
            records: List of raw records (mainly screenshots)
            keyboard_records: Keyboard event records for timestamp extraction
            mouse_records: Mouse event records for timestamp extraction

        Returns:
            {
                "todos": [...]
            }
        """
        if not records:
            return {"todos": []}

        try:
            logger.debug(
                f"Starting to extract todos only, total {len(records)} records"
            )

            # Build messages (including screenshots)
            messages = await self._build_todo_extraction_messages(
                records, keyboard_records, mouse_records
            )

            # Get configuration parameters
            config_params = self.prompt_manager.get_config_params("todo_extraction")

            # Call LLM (manager ensures latest activated model is used)
            response = await self.llm_manager.chat_completion(messages, **config_params)
            content = response.get("content", "").strip()

            # Parse JSON
            result = parse_json_from_response(content)

            if not isinstance(result, dict):
                logger.warning(f"LLM returned incorrect format: {content[:200]}")
                return {"todos": []}

            todos = result.get("todos", [])

            logger.debug(f"Todo extraction completed: {len(todos)} todos")

            return {"todos": todos}

        except Exception as e:
            logger.error(f"Todo extraction failed: {e}", exc_info=True)
            return {"todos": []}

    async def _build_todo_extraction_messages(
        self,
        records: List[RawRecord],
        keyboard_records: Optional[List[RawRecord]] = None,
        mouse_records: Optional[List[RawRecord]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Build TODO extraction messages (including system prompt, user prompt, screenshots)

        Args:
            records: Record list (mainly screenshots)
            keyboard_records: Keyboard event records for timestamp extraction
            mouse_records: Mouse event records for timestamp extraction

        Returns:
            Message list
        """
        # Get system prompt
        system_prompt = self.prompt_manager.get_system_prompt("todo_extraction")

        # Get user prompt template and format
        user_prompt_base = self.prompt_manager.get_user_prompt(
            "todo_extraction",
            "user_prompt_template",
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

        logger.debug(f"Built todo extraction messages: {screenshot_count} screenshots")

        # Build complete messages
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content_items},
        ]

        return messages

    async def extract_knowledge_only(
        self,
        records: List[RawRecord],
        keyboard_records: Optional[List[RawRecord]] = None,
        mouse_records: Optional[List[RawRecord]] = None,
    ) -> Dict[str, Any]:
        """
        Extract only knowledge from raw_records (used by KnowledgeAgent)

        Args:
            records: List of raw records (mainly screenshots)
            keyboard_records: Keyboard event records for timestamp extraction
            mouse_records: Mouse event records for timestamp extraction

        Returns:
            {
                "knowledge": [...]
            }
        """
        if not records:
            return {"knowledge": []}

        try:
            logger.debug(
                f"Starting to extract knowledge only, total {len(records)} records"
            )

            # Build messages (including screenshots)
            messages = await self._build_knowledge_extraction_messages(
                records, keyboard_records, mouse_records
            )

            # Get configuration parameters
            config_params = self.prompt_manager.get_config_params("knowledge_extraction")

            # Call LLM (manager ensures latest activated model is used)
            response = await self.llm_manager.chat_completion(messages, **config_params)
            content = response.get("content", "").strip()

            # Parse JSON
            result = parse_json_from_response(content)

            if not isinstance(result, dict):
                logger.warning(f"LLM returned incorrect format: {content[:200]}")
                return {"knowledge": []}

            knowledge = result.get("knowledge", [])

            logger.debug(f"Knowledge extraction completed: {len(knowledge)} knowledge items")

            return {"knowledge": knowledge}

        except Exception as e:
            logger.error(f"Knowledge extraction failed: {e}", exc_info=True)
            return {"knowledge": []}

    async def _build_knowledge_extraction_messages(
        self,
        records: List[RawRecord],
        keyboard_records: Optional[List[RawRecord]] = None,
        mouse_records: Optional[List[RawRecord]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Build knowledge extraction messages (including system prompt, user prompt, screenshots)

        Args:
            records: Record list (mainly screenshots)
            keyboard_records: Keyboard event records for timestamp extraction
            mouse_records: Mouse event records for timestamp extraction

        Returns:
            Message list
        """
        # Get system prompt
        system_prompt = self.prompt_manager.get_system_prompt("knowledge_extraction")

        # Get user prompt template and format
        user_prompt_base = self.prompt_manager.get_user_prompt(
            "knowledge_extraction",
            "user_prompt_template",
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

        logger.debug(f"Built knowledge extraction messages: {screenshot_count} screenshots")

        # Build complete messages
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content_items},
        ]

        return messages

    # ============ Event Aggregation ============

    async def aggregate_actions_to_events(
        self, actions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Aggregate actions into events

        Args:
            actions: Action list

        Returns:
            Event list
        """
        if not actions:
            return []

        try:
            logger.debug(f"Starting to aggregate {len(actions)} actions into events")

            # Build actions JSON with index
            actions_with_index = [
                {
                    "index": i + 1,
                    "title": action["title"],
                    "description": action["description"],
                }
                for i, action in enumerate(actions)
            ]
            actions_json = json.dumps(actions_with_index, ensure_ascii=False, indent=2)

            # Build messages
            messages = self.prompt_manager.build_messages(
                "event_aggregation", "user_prompt_template", actions_json=actions_json
            )

            # Get configuration parameters
            config_params = self.prompt_manager.get_config_params(
                "event_aggregation"
            )

            # Call LLM (manager ensures latest activated model is used)
            response = await self.llm_manager.chat_completion(messages, **config_params)
            content = response.get("content", "").strip()

            # Parse JSON
            result = parse_json_from_response(content)

            if not isinstance(result, dict):
                logger.warning(f"Aggregation result format error: {content[:200]}")
                return []

            events_data = result.get("events", [])

            # Convert to complete event objects
            events = []
            for event_data in events_data:
                # Normalize and deduplicate the LLM provided source indexes to
                # avoid associating the same action multiple times with one
                # event (LLM occasionally repeats indexes in its response).
                normalized_indexes = self._normalize_source_indexes(
                    event_data.get("source"), len(actions)
                )

                if not normalized_indexes:
                    continue

                source_action_ids: List[str] = []
                source_actions: List[Dict[str, Any]] = []
                for idx in normalized_indexes:
                    action = actions[idx - 1]
                    action_id = action.get("id")
                    if action_id:
                        source_action_ids.append(action_id)
                    source_actions.append(action)

                if not source_actions:
                    continue

                # Get timestamps
                start_time = None
                end_time = None
                for a in source_actions:
                    timestamp = a.get("timestamp")
                    if timestamp:
                        if isinstance(timestamp, str):
                            timestamp = datetime.fromisoformat(timestamp)
                        if start_time is None or timestamp < start_time:
                            start_time = timestamp
                        if end_time is None or timestamp > end_time:
                            end_time = timestamp

                if not start_time:
                    start_time = datetime.now()
                if not end_time:
                    end_time = start_time

                event = {
                    "id": str(uuid.uuid4()),
                    "title": event_data.get("title", "Unnamed event"),
                    "description": event_data.get("description", ""),
                    "start_time": start_time,
                    "end_time": end_time,
                    "source_action_ids": source_action_ids,
                    "created_at": datetime.now(),
                }

                events.append(event)

            logger.debug(
                f"Aggregation completed: generated {len(events)} events"
            )
            return events

        except Exception as e:
            logger.error(f"Failed to aggregate events: {e}", exc_info=True)
            return []

    def _normalize_source_indexes(
        self, raw_indexes: Any, total_actions: int
    ) -> List[int]:
        """Normalize LLM provided indexes to a unique, ordered int list."""
        if not isinstance(raw_indexes, list) or total_actions <= 0:
            return []

        normalized: List[int] = []
        seen: Set[int] = set()

        for idx in raw_indexes:
            try:
                idx_int = int(idx)
            except (TypeError, ValueError):
                continue

            if idx_int < 1 or idx_int > total_actions:
                continue

            if idx_int in seen:
                continue

            seen.add(idx_int)
            normalized.append(idx_int)

        return normalized

    # ============ Knowledge Merge ============

    async def merge_knowledge(
        self, knowledge_list: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Merge knowledge into combined_knowledge

        Args:
            knowledge_list: Knowledge list

        Returns:
            Combined_knowledge list
        """
        if not knowledge_list or len(knowledge_list) < 2:
            logger.debug("Insufficient knowledge count, skipping merge")
            return []

        try:
            logger.debug(f"Starting to merge {len(knowledge_list)} knowledge")

            # Build knowledge list JSON
            knowledge_json = json.dumps(knowledge_list, ensure_ascii=False, indent=2)

            # Build messages
            messages = self.prompt_manager.build_messages(
                "knowledge_merge", "user_prompt_template", knowledge_list=knowledge_json
            )

            # Get configuration parameters
            config_params = self.prompt_manager.get_config_params("knowledge_merge")

            # Call LLM (manager ensures latest activated model is used)
            response = await self.llm_manager.chat_completion(messages, **config_params)
            content = response.get("content", "").strip()

            # Parse JSON
            result = parse_json_from_response(content)

            if not isinstance(result, dict):
                logger.warning(f"Merge result format error: {content[:200]}")
                return []

            combined_list = result.get("combined_knowledge", [])

            # Add ID and timestamp
            for combined in combined_list:
                combined["id"] = str(uuid.uuid4())
                combined["created_at"] = datetime.now()
                # Ensure merged_from_ids exists
                if "merged_from_ids" not in combined:
                    combined["merged_from_ids"] = []

            logger.debug(
                f"Merge completed: generated {len(combined_list)} combined_knowledge"
            )
            return combined_list

        except Exception as e:
            logger.error(f"Failed to merge knowledge: {e}", exc_info=True)
            return []

    # ============ Todo Merge ============

    async def merge_todos(
        self, todo_list: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Merge todos into combined_todos

        Args:
            todo_list: Todo list

        Returns:
            Combined_todos list
        """
        if not todo_list or len(todo_list) < 2:
            logger.debug("Insufficient todo count, skipping merge")
            return []

        try:
            logger.debug(f"Starting to merge {len(todo_list)} todos")

            # Build todo list JSON
            todo_json = json.dumps(todo_list, ensure_ascii=False, indent=2)

            # Build messages
            messages = self.prompt_manager.build_messages(
                "todo_merge", "user_prompt_template", todo_list=todo_json
            )

            # Get configuration parameters
            config_params = self.prompt_manager.get_config_params("todo_merge")

            # Call LLM (manager ensures latest activated model is used)
            response = await self.llm_manager.chat_completion(messages, **config_params)
            content = response.get("content", "").strip()

            # Parse JSON
            result = parse_json_from_response(content)

            if not isinstance(result, dict):
                logger.warning(f"Merge result format error: {content[:200]}")
                return []

            combined_list = result.get("combined_todos", [])

            # Add ID, timestamp and completed status
            for combined in combined_list:
                combined["id"] = str(uuid.uuid4())
                combined["created_at"] = datetime.now()
                combined["completed"] = False
                # Ensure merged_from_ids exists
                if "merged_from_ids" not in combined:
                    combined["merged_from_ids"] = []

            logger.debug(
                f"Merge completed: generated {len(combined_list)} combined_todos"
            )
            return combined_list

        except Exception as e:
            logger.error(f"Failed to merge todos: {e}", exc_info=True)
            return []

    # ============ Extract from Events ============

    async def extract_todos_from_events(
        self, events: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Extract todos from events (text-based, no screenshots)

        Args:
            events: List of events with title and description

        Returns:
            List of TODO dictionaries
        """
        if not events:
            return []

        try:
            logger.debug(f"Starting to extract todos from {len(events)} events")

            # Build events JSON (only include title and description)
            events_simple = [
                {
                    "title": event.get("title", ""),
                    "description": event.get("description", ""),
                }
                for event in events
            ]
            events_json = json.dumps(events_simple, ensure_ascii=False, indent=2)

            # Build messages
            messages = self.prompt_manager.build_messages(
                "todo_from_events", "user_prompt_template", events_json=events_json
            )

            # Get configuration parameters
            config_params = self.prompt_manager.get_config_params("todo_from_events")

            # Call LLM
            response = await self.llm_manager.chat_completion(messages, **config_params)
            content = response.get("content", "").strip()

            # Parse JSON
            result = parse_json_from_response(content)

            if not isinstance(result, dict):
                logger.warning(f"LLM returned incorrect format: {content[:200]}")
                return []

            todos = result.get("todos", [])

            logger.debug(f"Todo extraction from events completed: {len(todos)} todos")
            return todos

        except Exception as e:
            logger.error(f"Failed to extract todos from events: {e}", exc_info=True)
            return []

    async def extract_knowledge_from_events(
        self, events: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Extract knowledge from events (text-based, no screenshots)

        Args:
            events: List of events with title and description

        Returns:
            List of knowledge dictionaries
        """
        if not events:
            return []

        try:
            logger.debug(f"Starting to extract knowledge from {len(events)} events")

            # Build events JSON (only include title and description)
            events_simple = [
                {
                    "title": event.get("title", ""),
                    "description": event.get("description", ""),
                }
                for event in events
            ]
            events_json = json.dumps(events_simple, ensure_ascii=False, indent=2)

            # Build messages
            messages = self.prompt_manager.build_messages(
                "knowledge_from_events", "user_prompt_template", events_json=events_json
            )

            # Get configuration parameters
            config_params = self.prompt_manager.get_config_params("knowledge_from_events")

            # Call LLM
            response = await self.llm_manager.chat_completion(messages, **config_params)
            content = response.get("content", "").strip()

            # Parse JSON
            result = parse_json_from_response(content)

            if not isinstance(result, dict):
                logger.warning(f"LLM returned incorrect format: {content[:200]}")
                return []

            knowledge = result.get("knowledge", [])

            logger.debug(f"Knowledge extraction from events completed: {len(knowledge)} knowledge items")
            return knowledge

        except Exception as e:
            logger.error(f"Failed to extract knowledge from events: {e}", exc_info=True)
            return []
