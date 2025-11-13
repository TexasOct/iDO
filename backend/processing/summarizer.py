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
from llm.client import get_llm_client
from llm.prompt_manager import get_prompt_manager
from processing.image_compression import get_image_optimizer
from processing.image_manager import get_image_manager

logger = get_logger(__name__)


class EventSummarizer:
    """Event processing/summary entry point (new architecture)"""

    def __init__(self, llm_client=None, language: str = "zh"):
        """
        Args:
            llm_client: LLM client instance
            language: Language setting (zh | en)
        """
        self.llm_client = llm_client or get_llm_client()
        self.prompt_manager = get_prompt_manager(language)
        self.language = language
        self.image_manager = get_image_manager()
        self.image_optimizer = None

        try:
            self.image_optimizer = get_image_optimizer()
            logger.info("EventSummarizer: Image optimization enabled")
        except Exception as exc:
            logger.warning(
                f"EventSummarizer: Failed to initialize image optimization, will skip compression: {exc}"
            )
            self.image_optimizer = None
        # Simple result cache, can be reused as needed
        self._summary_cache: Dict[str, str] = {}

    # ============ Event/Knowledge/Todo Extraction ============

    async def extract_event_knowledge_todo(
        self, records: List[RawRecord], input_usage_hint: str = ""
    ) -> Dict[str, Any]:
        """
        Extract events, knowledge, todos from raw_records

        Args:
            records: List of raw records (mainly screenshots)
            input_usage_hint: Keyboard/mouse activity hint

        Returns:
            {
                "events": [...],
                "knowledge": [...],
                "todos": [...]
            }
        """
        if not records:
            return {"events": [], "knowledge": [], "todos": []}

        try:
            logger.info(
                f"Starting to extract events/knowledge/todos, total {len(records)} records"
            )

            # Build messages (including screenshots)
            messages = await self._build_extraction_messages(records, input_usage_hint)

            # Get configuration parameters
            config_params = self.prompt_manager.get_config_params("event_extraction")

            # Call LLM
            response = await self.llm_client.chat_completion(messages, **config_params)
            content = response.get("content", "").strip()

            # Parse JSON
            result = parse_json_from_response(content)

            if not isinstance(result, dict):
                logger.warning(f"LLM returned incorrect format: {content[:200]}")
                return {"events": [], "knowledge": [], "todos": []}

            events = result.get("events", [])
            knowledge = result.get("knowledge", [])
            todos = result.get("todos", [])

            logger.info(
                f"Extraction completed: {len(events)} events, "
                f"{len(knowledge)} knowledge, {len(todos)} todos"
            )

            return {"events": events, "knowledge": knowledge, "todos": todos}

        except Exception as e:
            logger.error(f"Extraction failed: {e}", exc_info=True)
            return {"events": [], "knowledge": [], "todos": []}

    async def _build_extraction_messages(
        self, records: List[RawRecord], input_usage_hint: str
    ) -> List[Dict[str, Any]]:
        """
        Build extraction messages (including system prompt, user prompt, screenshots)

        Args:
            records: Record list
            input_usage_hint: Keyboard/mouse activity hint

        Returns:
            Message list
        """
        # Get system prompt
        system_prompt = self.prompt_manager.get_system_prompt("event_extraction")

        # Get user prompt template and format
        user_prompt = self.prompt_manager.get_user_prompt(
            "event_extraction",
            "user_prompt_template",
            input_usage_hint=input_usage_hint,
        )

        # Build content (text + screenshots)
        content_items = []

        # Add user prompt text
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

    # ============ Legacy Interface Compatibility ============

    async def summarize_events(self, records: List[RawRecord]) -> str:
        """
        Legacy EventSummarizer event summary interface compatibility
        Use event extraction results to construct brief summary
        """
        if not records:
            return "No events"

        try:
            cache_key = f"{records[0].timestamp.isoformat()}-{len(records)}"
            if cache_key in self._summary_cache:
                return self._summary_cache[cache_key]

            extraction = await self.extract_event_knowledge_todo(records)
            events = extraction.get("events", [])

            if not events:
                summary = "No summarizable events available"
            else:
                lines = []
                for idx, event in enumerate(events, start=1):
                    title = (event.get("title") or f"Event{idx}").strip()
                    description = (event.get("description") or "").strip()
                    if description:
                        lines.append(f"{idx}. {title} - {description}")
                    else:
                        lines.append(f"{idx}. {title}")
                summary = "\n".join(lines)

            self._summary_cache[cache_key] = summary
            return summary

        except Exception as exc:
            logger.error(f"Event summary failed: {exc}")
            return "Event summary failed"

    async def summarize_activity(self, records: List[RawRecord]) -> str:
        """
        Provide a higher-level activity summary including events/knowledge/todos.
        """
        if not records:
            return "No activity records available"

        try:
            extraction = await self.extract_event_knowledge_todo(records)
            events = extraction.get("events", [])
            knowledge = extraction.get("knowledge", [])
            todos = extraction.get("todos", [])

            sections: List[str] = []

            if events:
                event_lines = []
                for idx, event in enumerate(events, start=1):
                    title = (event.get("title") or f"Activity {idx}").strip()
                    summary = (event.get("description") or "").strip()
                    if summary:
                        event_lines.append(f"{idx}. {title} — {summary}")
                    else:
                        event_lines.append(f"{idx}. {title}")
                sections.append("Recent events:\n" + "\n".join(event_lines))

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

    # ============ Activity Aggregation ============

    async def aggregate_events_to_activities(
        self, events: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Aggregate events into activities

        Args:
            events: Event list

        Returns:
            Activity list
        """
        if not events:
            return []

        try:
            logger.info(f"Starting to aggregate {len(events)} events into activities")

            # Build events JSON with index
            events_with_index = [
                {
                    "index": i + 1,
                    "title": event["title"],
                    "description": event["description"],
                }
                for i, event in enumerate(events)
            ]
            events_json = json.dumps(events_with_index, ensure_ascii=False, indent=2)

            # Build messages
            messages = self.prompt_manager.build_messages(
                "activity_aggregation", "user_prompt_template", events_json=events_json
            )

            # Get configuration parameters
            config_params = self.prompt_manager.get_config_params(
                "activity_aggregation"
            )

            # Call LLM
            response = await self.llm_client.chat_completion(messages, **config_params)
            content = response.get("content", "").strip()

            # Parse JSON
            result = parse_json_from_response(content)

            if not isinstance(result, dict):
                logger.warning(f"Aggregation result format error: {content[:200]}")
                return []

            activities_data = result.get("activities", [])

            # Convert to complete activity objects
            activities = []
            for activity_data in activities_data:
                # Normalize and deduplicate the LLM provided source indexes to
                # avoid associating the same event multiple times with one
                # activity (LLM occasionally repeats indexes in its response).
                normalized_indexes = self._normalize_source_indexes(
                    activity_data.get("source"), len(events)
                )

                if not normalized_indexes:
                    continue

                source_event_ids: List[str] = []
                source_events: List[Dict[str, Any]] = []
                for idx in normalized_indexes:
                    event = events[idx - 1]
                    event_id = event.get("id")
                    if event_id:
                        source_event_ids.append(event_id)
                    source_events.append(event)

                if not source_events:
                    continue

                # Get timestamps
                start_time = None
                end_time = None
                for e in source_events:
                    timestamp = e.get("timestamp")
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

                activity = {
                    "id": str(uuid.uuid4()),
                    "title": activity_data.get("title", "Unnamed activity"),
                    "description": activity_data.get("description", ""),
                    "start_time": start_time,
                    "end_time": end_time,
                    "source_event_ids": source_event_ids,
                    "created_at": datetime.now(),
                }

                activities.append(activity)

            logger.info(
                f"Aggregation completed: generated {len(activities)} activities"
            )
            return activities

        except Exception as e:
            logger.error(f"Failed to aggregate activities: {e}", exc_info=True)
            return []

    def _normalize_source_indexes(
        self, raw_indexes: Any, total_events: int
    ) -> List[int]:
        """Normalize LLM provided indexes to a unique, ordered int list."""
        if not isinstance(raw_indexes, list) or total_events <= 0:
            return []

        normalized: List[int] = []
        seen: Set[int] = set()

        for idx in raw_indexes:
            try:
                idx_int = int(idx)
            except (TypeError, ValueError):
                continue

            if idx_int < 1 or idx_int > total_events:
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
            logger.info(f"Starting to merge {len(knowledge_list)} knowledge")

            # Build knowledge list JSON
            knowledge_json = json.dumps(knowledge_list, ensure_ascii=False, indent=2)

            # Build messages
            messages = self.prompt_manager.build_messages(
                "knowledge_merge", "user_prompt_template", knowledge_list=knowledge_json
            )

            # Get configuration parameters
            config_params = self.prompt_manager.get_config_params("knowledge_merge")

            # Call LLM
            response = await self.llm_client.chat_completion(messages, **config_params)
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

            logger.info(
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
            logger.info(f"Starting to merge {len(todo_list)} todos")

            # Build todo list JSON
            todo_json = json.dumps(todo_list, ensure_ascii=False, indent=2)

            # Build messages
            messages = self.prompt_manager.build_messages(
                "todo_merge", "user_prompt_template", todo_list=todo_json
            )

            # Get configuration parameters
            config_params = self.prompt_manager.get_config_params("todo_merge")

            # Call LLM
            response = await self.llm_client.chat_completion(messages, **config_params)
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

            logger.info(
                f"Merge completed: generated {len(combined_list)} combined_todos"
            )
            return combined_list

        except Exception as e:
            logger.error(f"Failed to merge todos: {e}", exc_info=True)
            return []

    # ============ Diary Generation ============

    async def generate_diary(self, activities: List[Dict[str, Any]], date: str) -> str:
        """
        Generate diary

        Args:
            activities: Activity list
            date: Date (YYYY-MM-DD)

        Returns:
            Diary content (including activity references)
        """
        if not activities:
            return (
                "今天没有记录到活动。"
                if self.language == "zh"
                else "No activities recorded today."
            )

        try:
            logger.info(
                f"Starting to generate diary, total {len(activities)} activities"
            )

            # Build activities JSON
            activities_json = json.dumps(activities, ensure_ascii=False, indent=2)

            # Build messages
            messages = self.prompt_manager.build_messages(
                "diary_generation",
                "user_prompt_template",
                date=date,
                activities_json=activities_json,
            )

            # Get configuration parameters
            config_params = self.prompt_manager.get_config_params("diary_generation")

            # Call LLM
            response = await self.llm_client.chat_completion(messages, **config_params)
            content = response.get("content", "").strip()

            # Parse JSON
            result = parse_json_from_response(content)

            if isinstance(result, dict):
                diary_content = result.get("content", content)
            else:
                diary_content = content

            logger.info("Diary generation completed")
            return diary_content

        except Exception as e:
            logger.error(f"Failed to generate diary: {e}", exc_info=True)
            error_msg = (
                f"日记生成失败: {str(e)}"
                if self.language == "zh"
                else f"Diary generation failed: {str(e)}"
            )
            return error_msg
