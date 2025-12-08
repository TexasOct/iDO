"""
EventSummarizer (new architecture)
Unified handling of event extraction, merging, diary generation and other LLM interaction capabilities
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
    """Event processing/summary entry point (new architecture)"""

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
        # Simple result cache, can be reused as needed
        self._summary_cache: Dict[str, str] = {}

    # ============ Action/Knowledge/Todo Extraction ============

    async def extract_action_knowledge_todo(
        self,
        records: List[RawRecord],
        input_usage_hint: str = "",
        keyboard_records: Optional[List[RawRecord]] = None,
        mouse_records: Optional[List[RawRecord]] = None,
    ) -> Dict[str, Any]:
        """
        Extract actions, knowledge, todos from raw_records

        Args:
            records: List of raw records (mainly screenshots)
            input_usage_hint: Keyboard/mouse activity hint (legacy)
            keyboard_records: Keyboard event records for timestamp extraction
            mouse_records: Mouse event records for timestamp extraction

        Returns:
            {
                "actions": [...],
                "knowledge": [...],
                "todos": [...]
            }
        """
        if not records:
            return {"actions": [], "knowledge": [], "todos": []}

        try:
            logger.debug(
                f"Starting to extract actions/knowledge/todos, total {len(records)} records"
            )

            # Build messages (including screenshots)
            messages = await self._build_extraction_messages(
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
                return {"actions": [], "knowledge": [], "todos": []}

            actions = result.get("actions", [])
            knowledge = result.get("knowledge", [])
            todos = result.get("todos", [])

            logger.debug(
                f"Extraction completed: {len(actions)} actions, "
                f"{len(knowledge)} knowledge, {len(todos)} todos"
            )

            return {"actions": actions, "knowledge": knowledge, "todos": todos}

        except Exception as e:
            logger.error(f"Extraction failed: {e}", exc_info=True)
            return {"actions": [], "knowledge": [], "todos": []}

    async def _build_extraction_messages(
        self,
        records: List[RawRecord],
        input_usage_hint: str,
        keyboard_records: Optional[List[RawRecord]] = None,
        mouse_records: Optional[List[RawRecord]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Build extraction messages (including system prompt, user prompt, screenshots)

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

    # ============ Legacy Interface Compatibility ============

    async def summarize_events(self, records: List[RawRecord]) -> str:
        """
        Legacy EventSummarizer event summary interface compatibility
        Use action extraction results to construct brief summary
        """
        if not records:
            return "No actions"

        try:
            cache_key = f"{records[0].timestamp.isoformat()}-{len(records)}"
            if cache_key in self._summary_cache:
                return self._summary_cache[cache_key]

            extraction = await self.extract_action_knowledge_todo(records)
            actions = extraction.get("actions", [])

            if not actions:
                summary = "No summarizable actions available"
            else:
                lines = []
                for idx, action in enumerate(actions, start=1):
                    title = (action.get("title") or f"Action{idx}").strip()
                    description = (action.get("description") or "").strip()
                    if description:
                        lines.append(f"{idx}. {title} - {description}")
                    else:
                        lines.append(f"{idx}. {title}")
                summary = "\n".join(lines)

            self._summary_cache[cache_key] = summary
            return summary

        except Exception as exc:
            logger.error(f"Action summary failed: {exc}")
            return "Action summary failed"

    async def summarize_activity(self, records: List[RawRecord]) -> str:
        """
        Provide a higher-level activity summary including actions/knowledge/todos.
        """
        if not records:
            return "No activity records available"

        try:
            extraction = await self.extract_action_knowledge_todo(records)
            actions = extraction.get("actions", [])
            knowledge = extraction.get("knowledge", [])
            todos = extraction.get("todos", [])

            sections: List[str] = []

            if actions:
                action_lines = []
                for idx, action in enumerate(actions, start=1):
                    title = (action.get("title") or f"Action {idx}").strip()
                    summary = (action.get("description") or "").strip()
                    if summary:
                        action_lines.append(f"{idx}. {title} — {summary}")
                    else:
                        action_lines.append(f"{idx}. {title}")
                sections.append("Recent actions:\n" + "\n".join(action_lines))

            if knowledge:
                knowledge_lines = [
                    f"- {item.get('title', 'Insight')}: {item.get('description', '').strip()}"
                    for item in knowledge
                ]
                sections.append("Key takeaways:\n" + "\n".join(knowledge_lines))

            if todos:
                todo_lines = [
                    f"- {todo.get('title', 'Todo')}"
                    for todo in todos
                ]
                sections.append("Suggested follow-ups:\n" + "\n".join(todo_lines))

            if not sections:
                return "Activity detected but nothing noteworthy to summarize"

            return "\n\n".join(sections)

        except Exception as exc:
            logger.error(f"Activity summary failed: {exc}")
            return "Activity summary failed"

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
