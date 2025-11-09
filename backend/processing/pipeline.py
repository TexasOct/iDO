"""
Processing pipeline (new architecture)
Implements complete processing flow: raw_records → events/knowledge/todos → activities
"""

import asyncio
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from core.logger import get_logger
from core.models import RawRecord, RecordType

from .filter_rules import EventFilter
from .persistence import ProcessingPersistence
from .summarizer import EventSummarizer

logger = get_logger(__name__)


class ProcessingPipeline:
    """Processing pipeline (new architecture)"""

    def __init__(
        self,
        screenshot_threshold: int = 20,
        activity_summary_interval: int = 600,
        knowledge_merge_interval: int = 1200,
        todo_merge_interval: int = 1200,
        language: str = "zh",
        enable_screenshot_deduplication: bool = True,
    ):
        """
        Initialize processing pipeline

        Args:
            screenshot_threshold: Number of screenshots that trigger event extraction
            activity_summary_interval: Activity summary interval (seconds, default 10 minutes)
            knowledge_merge_interval: Knowledge merge interval (seconds, default 20 minutes)
            todo_merge_interval: Todo merge interval (seconds, default 20 minutes)
            language: Language setting (zh|en)
            enable_screenshot_deduplication: Whether to enable screenshot deduplication
        """
        self.screenshot_threshold = screenshot_threshold
        self.activity_summary_interval = activity_summary_interval
        self.knowledge_merge_interval = knowledge_merge_interval
        self.todo_merge_interval = todo_merge_interval
        self.language = language

        # Initialize components
        self.event_filter = EventFilter(
            enable_screenshot_deduplication=enable_screenshot_deduplication
        )
        self.summarizer = EventSummarizer(language=language)
        self.persistence = ProcessingPersistence()

        # Running state
        self.is_running = False

        # Screenshot accumulator (in memory)
        self.screenshot_accumulator: List[RawRecord] = []

        # Scheduled tasks
        self.activity_summary_task: Optional[asyncio.Task] = None
        self.knowledge_merge_task: Optional[asyncio.Task] = None
        self.todo_merge_task: Optional[asyncio.Task] = None

        # Statistics
        self.stats: Dict[str, Any] = {
            "total_screenshots": 0,
            "events_created": 0,
            "knowledge_created": 0,
            "todos_created": 0,
            "activities_created": 0,
            "combined_knowledge_created": 0,
            "combined_todos_created": 0,
            "last_processing_time": None,
        }

    async def start(self):
        """Start processing pipeline"""
        if self.is_running:
            logger.warning("Processing pipeline is already running")
            return

        self.is_running = True

        # Start scheduled tasks
        self.activity_summary_task = asyncio.create_task(
            self._periodic_activity_summary()
        )
        self.knowledge_merge_task = asyncio.create_task(
            self._periodic_knowledge_merge()
        )
        self.todo_merge_task = asyncio.create_task(self._periodic_todo_merge())

        logger.info(f"Processing pipeline started (language: {self.language})")
        logger.info(f"- Screenshot threshold: {self.screenshot_threshold}")
        logger.info(f"- Activity summary interval: {self.activity_summary_interval}s")
        logger.info(f"- Knowledge merge interval: {self.knowledge_merge_interval}s")
        logger.info(f"- Todo merge interval: {self.todo_merge_interval}s")

    async def stop(self):
        """Stop processing pipeline"""
        if not self.is_running:
            return

        self.is_running = False

        # Cancel scheduled tasks
        if self.activity_summary_task:
            self.activity_summary_task.cancel()
        if self.knowledge_merge_task:
            self.knowledge_merge_task.cancel()
        if self.todo_merge_task:
            self.todo_merge_task.cancel()

        # Process remaining accumulated screenshots
        if self.screenshot_accumulator:
            logger.info(
                f"Processing remaining {len(self.screenshot_accumulator)} screenshots"
            )
            await self._extract_events(self.screenshot_accumulator)
            self.screenshot_accumulator = []

        logger.info("Processing pipeline stopped")

    async def process_raw_records(self, raw_records: List[RawRecord]) -> Dict[str, Any]:
        """
        Process raw records (new logic)

        Args:
            raw_records: Raw record list

        Returns:
            Processing result
        """
        if not raw_records:
            return {"processed": 0}

        try:
            logger.debug(f"Received {len(raw_records)} raw records")

            # 1. Event filtering (including deduplication)
            filtered_records = self.event_filter.filter_all_events(raw_records)
            logger.debug(f"Remaining {len(filtered_records)} records after filtering")

            if not filtered_records:
                return {"processed": 0}

            # 2. Extract screenshot records
            screenshots = [
                r for r in filtered_records if r.type == RecordType.SCREENSHOT_RECORD
            ]

            # 3. Extract keyboard/mouse records (for activity detection)
            keyboard_records = [
                r for r in filtered_records if r.type == RecordType.KEYBOARD_RECORD
            ]
            mouse_records = [
                r for r in filtered_records if r.type == RecordType.MOUSE_RECORD
            ]

            # 4. Accumulate screenshots
            self.screenshot_accumulator.extend(screenshots)
            self.stats["total_screenshots"] += len(screenshots)

            logger.debug(
                f"Accumulated screenshots: {len(self.screenshot_accumulator)}/{self.screenshot_threshold}"
            )

            # 5. Check if threshold reached
            if len(self.screenshot_accumulator) >= self.screenshot_threshold:
                # Pass keyboard/mouse activity information
                await self._extract_events(
                    self.screenshot_accumulator,
                    has_keyboard_activity=len(keyboard_records) > 0,
                    has_mouse_activity=len(mouse_records) > 0,
                )

                # Clear accumulator
                processed_count = len(self.screenshot_accumulator)
                self.screenshot_accumulator = []

                return {
                    "processed": processed_count,
                    "accumulated": 0,
                    "extracted": True,
                }

            return {
                "processed": len(screenshots),
                "accumulated": len(self.screenshot_accumulator),
                "extracted": False,
            }

        except Exception as e:
            logger.error(f"Failed to process raw records: {e}", exc_info=True)
            return {"processed": 0, "error": str(e)}

    async def _extract_events(
        self,
        records: List[RawRecord],
        has_keyboard_activity: bool = False,
        has_mouse_activity: bool = False,
    ):
        """
        Call LLM to extract events, knowledge, todos

        Args:
            records: Record list (mainly screenshots)
            has_keyboard_activity: Whether there is keyboard activity
            has_mouse_activity: Whether there is mouse activity
        """
        if not records:
            return

        try:
            logger.info(
                f"Starting to extract events/knowledge/todos, total {len(records)} screenshots"
            )

            # Build keyboard/mouse activity hint
            input_usage_hint = self._build_input_usage_hint(
                has_keyboard_activity, has_mouse_activity
            )

            # Calculate event timestamps (using latest screenshot time)
            event_timestamps = [record.timestamp for record in records]
            event_timestamp = (
                max(event_timestamps) if event_timestamps else datetime.now()
            )

            # Call summarizer to extract
            result = await self.summarizer.extract_event_knowledge_todo(
                records, input_usage_hint=input_usage_hint
            )

            # Save events
            events = result.get("events", [])
            for event_data in events:
                event_id = str(uuid.uuid4())
                # Resolve screenshot hashes based on image_index from LLM
                event_hashes = self._resolve_event_screenshot_hashes(
                    event_data, records
                )
                await self.persistence.save_event(
                    {
                        "id": event_id,
                        "title": event_data["title"],
                        "description": event_data["description"],
                        "keywords": event_data.get("keywords", []),
                        "timestamp": event_timestamp,
                        "screenshot_hashes": event_hashes,
                    }
                )

            # Save knowledge
            knowledge_list = result.get("knowledge", [])
            for knowledge_data in knowledge_list:
                knowledge_id = str(uuid.uuid4())
                await self.persistence.save_knowledge(
                    {
                        "id": knowledge_id,
                        "title": knowledge_data["title"],
                        "description": knowledge_data["description"],
                        "keywords": knowledge_data.get("keywords", []),
                        "created_at": event_timestamp,
                    }
                )

            # Save todos
            todos = result.get("todos", [])
            for todo_data in todos:
                todo_id = str(uuid.uuid4())
                await self.persistence.save_todo(
                    {
                        "id": todo_id,
                        "title": todo_data["title"],
                        "description": todo_data["description"],
                        "keywords": todo_data.get("keywords", []),
                        "created_at": event_timestamp,
                        "completed": False,
                    }
                )

            # Update statistics
            self.stats["events_created"] += len(events)
            self.stats["knowledge_created"] += len(knowledge_list)
            self.stats["todos_created"] += len(todos)
            self.stats["last_processing_time"] = datetime.now()

            logger.info(
                f"Extraction completed: {len(events)} events, "
                f"{len(knowledge_list)} knowledge, "
                f"{len(todos)} todos"
            )

        except Exception as e:
            logger.error(
                f"Failed to extract events/knowledge/todos: {e}", exc_info=True
            )

    def _build_input_usage_hint(self, has_keyboard: bool, has_mouse: bool) -> str:
        """Build keyboard/mouse activity hint text"""
        hints = []

        if has_keyboard:
            hints.append(
                "用户有在使用键盘"
                if self.language == "zh"
                else "User has keyboard activity"
            )
        else:
            hints.append(
                "用户没有在使用键盘"
                if self.language == "zh"
                else "User has no keyboard activity"
            )

        if has_mouse:
            hints.append(
                "用户有在使用鼠标"
                if self.language == "zh"
                else "User has mouse activity"
            )
        else:
            hints.append(
                "用户没有在使用鼠标"
                if self.language == "zh"
                else "User has no mouse activity"
            )

        return "; ".join(hints)
        return "；".join(hints) if self.language == "zh" else "; ".join(hints)

    def _resolve_event_screenshot_hashes(
        self, event_data: Dict[str, Any], records: List[RawRecord]
    ) -> List[str]:
        """
        Resolve screenshot hashes based on image_index from LLM response

        Args:
            event_data: Event data containing image_index (or imageIndex)
            records: All raw records (screenshots)

        Returns:
            List of screenshot hashes filtered by image_index
        """
        # Get image_index from event data (support both snake_case and camelCase)
        image_indices = event_data.get("image_index") or event_data.get("imageIndex")

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
                    # Convert to integer and validate range
                    idx_int = int(idx)
                    if 0 <= idx_int < len(screenshot_records):
                        record = screenshot_records[idx_int]
                        data = record.data or {}
                        img_hash = data.get("hash")

                        # Add hash if valid and not duplicate
                        if img_hash and str(img_hash) not in seen:
                            seen.add(str(img_hash))
                            normalized_hashes.append(str(img_hash))

                            # Limit to 6 screenshots per event
                            if len(normalized_hashes) >= 6:
                                break
                except (ValueError, TypeError, IndexError):
                    logger.warning(f"Invalid image_index value: {idx}")
                    continue

            if normalized_hashes:
                logger.debug(
                    f"Resolved {len(normalized_hashes)} screenshot hashes from image_index {image_indices}"
                )
                return normalized_hashes

        # Fallback: use first 6 unique screenshot hashes
        logger.debug("No valid image_index found, using default screenshot hashes")
        fallback_hashes: List[str] = []
        seen = set()
        for record in screenshot_records:
            data = record.data or {}
            img_hash = data.get("hash")
            if img_hash and str(img_hash) not in seen:
                seen.add(str(img_hash))
                fallback_hashes.append(str(img_hash))
                if len(fallback_hashes) >= 6:
                    break
        return fallback_hashes

    # ============ Scheduled Tasks ============

    async def _periodic_activity_summary(self):
        """Scheduled task: summarize activities every N minutes"""
        while self.is_running:
            try:
                await asyncio.sleep(self.activity_summary_interval)
                await self._summarize_activities()
            except asyncio.CancelledError:
                logger.info("Activity summary task cancelled")
                break
            except Exception as e:
                logger.error(f"Activity summary task exception: {e}", exc_info=True)

    async def _summarize_activities(self):
        """Get recent unsummarized events, call LLM to aggregate into activities"""
        try:
            # Get unaggregated events
            recent_events = await self.persistence.get_unsummarized_events()

            if not recent_events or len(recent_events) == 0:
                logger.debug("No events to summarize")
                return

            logger.info(
                f"Starting to aggregate {len(recent_events)} events into activities"
            )

            # Call summarizer to aggregate
            activities = await self.summarizer.aggregate_events_to_activities(
                recent_events
            )

            # Save activities
            for activity_data in activities:
                await self.persistence.save_activity(activity_data)
                self.stats["activities_created"] += 1

            logger.info(f"Successfully created {len(activities)} activities")

        except Exception as e:
            logger.error(f"Failed to summarize activities: {e}", exc_info=True)

    async def _periodic_knowledge_merge(self):
        """Scheduled task: merge knowledge every N minutes"""
        while self.is_running:
            try:
                await asyncio.sleep(self.knowledge_merge_interval)
                await self._merge_knowledge()
            except asyncio.CancelledError:
                logger.info("Knowledge merge task cancelled")
                break
            except Exception as e:
                logger.error(f"Knowledge merge task exception: {e}", exc_info=True)

    async def _merge_knowledge(self):
        """Merge related knowledge into combined_knowledge"""
        try:
            # Get unmerged knowledge
            unmerged_knowledge = await self.persistence.get_unmerged_knowledge()

            if not unmerged_knowledge or len(unmerged_knowledge) < 2:
                logger.debug("Insufficient knowledge count, skipping merge")
                return

            # Limit batch size to prevent overwhelming LLM
            MAX_ITEMS_PER_MERGE = 50
            if len(unmerged_knowledge) > MAX_ITEMS_PER_MERGE:
                logger.warning(
                    f"Too many knowledge items ({len(unmerged_knowledge)}), "
                    f"limiting to {MAX_ITEMS_PER_MERGE} per batch"
                )
                unmerged_knowledge = unmerged_knowledge[:MAX_ITEMS_PER_MERGE]

            logger.info(f"Starting to merge {len(unmerged_knowledge)} knowledge")

            # Call summarizer to merge
            combined = await self.summarizer.merge_knowledge(unmerged_knowledge)

            # Save combined_knowledge
            merged_source_ids: Set[str] = set()
            for combined_data in combined:
                await self.persistence.save_combined_knowledge(combined_data)
                self.stats["combined_knowledge_created"] += 1
                merged_source_ids.update(
                    item_id
                    for item_id in combined_data.get("merged_from_ids", [])
                    if item_id
                )

            # Soft delete original knowledge records now represented by combined entries
            if merged_source_ids:
                deleted_count = await self.persistence.delete_knowledge_batch(
                    list(merged_source_ids)
                )
                if deleted_count:
                    logger.info(
                        f"Deleted {deleted_count} original knowledge records after merge"
                    )

            logger.info(f"Successfully merged into {len(combined)} combined_knowledge")

        except Exception as e:
            logger.error(f"Failed to merge knowledge: {e}", exc_info=True)

    async def _periodic_todo_merge(self):
        """Scheduled task: merge todos every N minutes"""
        while self.is_running:
            try:
                await asyncio.sleep(self.todo_merge_interval)
                await self._merge_todos()
            except asyncio.CancelledError:
                logger.info("Todo merge task cancelled")
                break
            except Exception as e:
                logger.error(f"Todo merge task exception: {e}", exc_info=True)

    async def _merge_todos(self):
        """Merge related todos into combined_todos"""
        try:
            # Get unmerged todos
            unmerged_todos = await self.persistence.get_unmerged_todos()

            if not unmerged_todos or len(unmerged_todos) < 2:
                logger.debug("Insufficient todos count, skipping merge")
                return

            # Limit batch size to prevent overwhelming LLM
            MAX_ITEMS_PER_MERGE = 50
            if len(unmerged_todos) > MAX_ITEMS_PER_MERGE:
                logger.warning(
                    f"Too many todo items ({len(unmerged_todos)}), "
                    f"limiting to {MAX_ITEMS_PER_MERGE} per batch"
                )
                unmerged_todos = unmerged_todos[:MAX_ITEMS_PER_MERGE]

            logger.info(f"Starting to merge {len(unmerged_todos)} todos")

            # Call summarizer to merge
            combined = await self.summarizer.merge_todos(unmerged_todos)

            # Save combined_todos
            merged_todo_ids: Set[str] = set()
            for combined_data in combined:
                await self.persistence.save_combined_todo(combined_data)
                self.stats["combined_todos_created"] += 1
                merged_todo_ids.update(
                    item_id
                    for item_id in combined_data.get("merged_from_ids", [])
                    if item_id
                )

            # Soft delete original todos to reduce storage usage
            if merged_todo_ids:
                deleted_count = await self.persistence.delete_todo_batch(
                    list(merged_todo_ids)
                )
                if deleted_count:
                    logger.info(f"Deleted {deleted_count} original todos after merge")

            logger.info(f"Successfully merged into {len(combined)} combined_todos")

        except Exception as e:
            logger.error(f"Failed to merge todos: {e}", exc_info=True)

    # ============ External Interfaces ============

    async def get_recent_events(
        self, limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get recent events"""
        return await self.persistence.get_recent_events(limit, offset)

    async def get_knowledge_list(self) -> List[Dict[str, Any]]:
        """Get knowledge list (prioritize returning combined)"""
        return await self.persistence.get_knowledge_list()

    async def get_todo_list(
        self, include_completed: bool = False
    ) -> List[Dict[str, Any]]:
        """Get todo list (prioritize returning combined)"""
        return await self.persistence.get_todo_list(include_completed)

    async def delete_knowledge(self, knowledge_id: str):
        """Delete knowledge (soft delete)"""
        await self.persistence.delete_knowledge(knowledge_id)

    async def delete_todo(self, todo_id: str):
        """Delete todo (soft delete)"""
        await self.persistence.delete_todo(todo_id)

    async def schedule_todo(
        self, todo_id: str, scheduled_date: str
    ) -> Optional[Dict[str, Any]]:
        """Schedule todo to a specific date"""
        return await self.persistence.schedule_todo(todo_id, scheduled_date)

    async def unschedule_todo(self, todo_id: str) -> Optional[Dict[str, Any]]:
        """Unschedule todo (remove scheduled date)"""
        return await self.persistence.unschedule_todo(todo_id)

    async def generate_diary_for_date(self, date: str) -> Dict[str, Any]:
        """Generate diary for specified date"""
        try:
            # Check if already exists
            existing = await self.persistence.get_diary_by_date(date)
            if existing:
                return existing

            # Get all activities for this date
            activities = await self.persistence.get_activities_by_date(date)

            if not activities:
                return {
                    "error": "该日期无活动记录"
                    if self.language == "zh"
                    else "No activities for this date"
                }

            # Call summarizer to generate diary
            diary_content = await self.summarizer.generate_diary(activities, date)

            # Save diary
            diary_id = str(uuid.uuid4())
            diary_data = {
                "id": diary_id,
                "date": date,
                "content": diary_content,
                "source_activity_ids": [a["id"] for a in activities],
                "created_at": datetime.now(),
            }

            await self.persistence.save_diary(diary_data)
            return diary_data

        except Exception as e:
            logger.error(f"Failed to generate diary: {e}", exc_info=True)
            return {"error": str(e)}

    async def delete_diary(self, diary_id: str):
        """Delete diary"""
        await self.persistence.delete_diary(diary_id)

    async def get_diary_list(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent diary list"""
        return await self.persistence.get_diary_list(limit)

    async def force_finalize_activity(self):
        """Manually trigger activity summary and knowledge/todo merge"""
        try:
            await self._summarize_activities()
            await self._merge_knowledge()
            await self._merge_todos()
        except Exception as exc:
            logger.error(f"Failed to force finalize activity: {exc}", exc_info=True)

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics information"""
        return {
            "is_running": self.is_running,
            "screenshot_threshold": self.screenshot_threshold,
            "accumulated_screenshots": len(self.screenshot_accumulator),
            "stats": self.stats.copy(),
        }
