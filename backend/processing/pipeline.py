"""
Processing pipeline (new architecture)
Implements complete processing flow: raw_records → events/knowledge/todos → activities
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set

from core.db import get_db
from core.logger import get_logger
from core.models import RawRecord, RecordType

from .filter_rules import EventFilter
from .image_manager import get_image_manager
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
        screenshot_similarity_threshold: float = 0.90,
        screenshot_hash_cache_size: int = 10,
        screenshot_hash_algorithms: Optional[List[str]] = None,
        enable_adaptive_threshold: bool = True,
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
            screenshot_similarity_threshold: Similarity threshold for deduplication (0-1)
            screenshot_hash_cache_size: Number of hashes to cache for comparison
            screenshot_hash_algorithms: List of hash algorithms to use
            enable_adaptive_threshold: Whether to enable scene-adaptive thresholds
        """
        self.screenshot_threshold = screenshot_threshold
        self.activity_summary_interval = activity_summary_interval
        self.knowledge_merge_interval = knowledge_merge_interval
        self.todo_merge_interval = todo_merge_interval
        self.language = language

        # Initialize components
        self.event_filter = EventFilter(
            enable_screenshot_deduplication=enable_screenshot_deduplication,
            similarity_threshold=screenshot_similarity_threshold,
            hash_cache_size=screenshot_hash_cache_size,
            hash_algorithms=screenshot_hash_algorithms,
            enable_adaptive_threshold=enable_adaptive_threshold,
        )
        self.summarizer = EventSummarizer(language=language)
        self.db = get_db()
        self.image_manager = get_image_manager()

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

    async def _get_event_screenshot_hashes(self, event_id: str) -> List[str]:
        try:
            return await self.db.events.get_screenshots(event_id)
        except Exception as exc:
            logger.error("Failed to load screenshot hashes for event %s: %s", event_id, exc)
            return []

    async def _load_event_screenshots_base64(self, event_id: str) -> List[str]:
        hashes = await self._get_event_screenshot_hashes(event_id)

        screenshots: List[str] = []
        for img_hash in hashes:
            if not img_hash:
                continue
            data = self.image_manager.get_from_cache(img_hash)
            if not data:
                data = self.image_manager.load_thumbnail_base64(img_hash)
            if data:
                screenshots.append(data)

        return screenshots

    async def _get_unsummarized_events(
        self, since: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Fetch events not yet aggregated into activities"""
        try:
            start_time = since or datetime.now() - timedelta(hours=1)
            end_time = datetime.now()

            events = await self.db.events.get_in_timeframe(
                start_time.isoformat(), end_time.isoformat()
            )

            aggregated_ids = set(await self.db.activities.get_all_source_event_ids())

            result: List[Dict[str, Any]] = []
            for event in events:
                if event.get("id") in aggregated_ids:
                    continue

                timestamp_value = event.get("timestamp")
                if isinstance(timestamp_value, str):
                    try:
                        timestamp_value = datetime.fromisoformat(timestamp_value)
                    except ValueError:
                        timestamp_value = datetime.now()

                result.append(
                    {
                        "id": event.get("id"),
                        "title": event.get("title"),
                        "description": event.get("description"),
                        "keywords": event.get("keywords", []),
                        "timestamp": timestamp_value,
                        "created_at": event.get("created_at"),
                    }
                )

            return result

        except Exception as exc:
            logger.error("Failed to get unsummarized events: %s", exc, exc_info=True)
            return []

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
        logger.debug(f"- Screenshot threshold: {self.screenshot_threshold}")
        logger.debug(f"- Activity summary interval: {self.activity_summary_interval}s")
        logger.debug(f"- Knowledge merge interval: {self.knowledge_merge_interval}s")
        logger.debug(f"- Todo merge interval: {self.todo_merge_interval}s")

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
            logger.debug(
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
            logger.debug(
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

            events = result.get("events", [])

            # Validate screenshot indices for every event first. If any event lacks
            # valid indices, drop the entire batch to avoid mismatched screenshots.
            resolved_events: List[Dict[str, Any]] = []
            for event_data in events:
                event_hashes = self._resolve_event_screenshot_hashes(
                    event_data, records
                )
                if not event_hashes:
                    logger.warning(
                        "Dropping extraction batch: invalid image_index in event '%s'",
                        event_data.get("title", "<no title>"),
                    )
                    return

                resolved_events.append({"data": event_data, "hashes": event_hashes})

            # Save events only after validation passes
            for resolved in resolved_events:
                event_data = resolved["data"]
                event_hashes = resolved["hashes"]
                event_id = str(uuid.uuid4())

                await self.db.events.save(
                    event_id=event_id,
                    title=event_data["title"],
                    description=event_data["description"],
                    keywords=event_data.get("keywords", []),
                    timestamp=event_timestamp.isoformat(),
                    screenshots=event_hashes,
                )

            # Save knowledge
            knowledge_list = result.get("knowledge", [])
            for knowledge_data in knowledge_list:
                knowledge_id = str(uuid.uuid4())
                await self.db.knowledge.save(
                    knowledge_id=knowledge_id,
                    title=knowledge_data["title"],
                    description=knowledge_data["description"],
                    keywords=knowledge_data.get("keywords", []),
                    created_at=event_timestamp.isoformat(),
                )

            # Save todos
            todos = result.get("todos", [])
            for todo_data in todos:
                todo_id = str(uuid.uuid4())
                await self.db.todos.save(
                    todo_id=todo_id,
                    title=todo_data["title"],
                    description=todo_data["description"],
                    keywords=todo_data.get("keywords", []),
                    created_at=event_timestamp.isoformat(),
                )

            # Update statistics
            self.stats["events_created"] += len(events)
            self.stats["knowledge_created"] += len(knowledge_list)
            self.stats["todos_created"] += len(todos)
            self.stats["last_processing_time"] = datetime.now()

            logger.debug(
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
        # Get perception settings
        from core.settings import get_settings

        settings = get_settings()
        keyboard_enabled = settings.get("perception.keyboard_enabled", True)
        mouse_enabled = settings.get("perception.mouse_enabled", True)

        hints = []

        # Keyboard perception status
        if keyboard_enabled:
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
        else:
            hints.append(
                "键盘感知已禁用，无法获取键盘输入信息"
                if self.language == "zh"
                else "Keyboard perception is disabled, no keyboard input available"
            )

        # Mouse perception status
        if mouse_enabled:
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
        else:
            hints.append(
                "鼠标感知已禁用，无法获取鼠标输入信息"
                if self.language == "zh"
                else "Mouse perception is disabled, no mouse input available"
            )

        return "；".join(hints) if self.language == "zh" else "; ".join(hints)

    def _resolve_event_screenshot_hashes(
        self, event_data: Dict[str, Any], records: List[RawRecord]
    ) -> Optional[List[str]]:
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
                    # Indices are zero-based per prompt; still accept strings that
                    # can be converted to integers.
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
                except (ValueError, TypeError):
                    logger.warning(f"Invalid image_index value: {idx}")
                    return None

            if normalized_hashes:
                logger.debug(
                    f"Resolved {len(normalized_hashes)} screenshot hashes from image_index {image_indices}"
                )
                return normalized_hashes

        logger.warning("Event missing valid image_index: %s", image_indices)
        return None

    # ============ Scheduled Tasks ============

    async def _periodic_activity_summary(self):
        """Scheduled task: summarize activities every N minutes"""
        while self.is_running:
            try:
                await asyncio.sleep(self.activity_summary_interval)
                await self._summarize_activities()
            except asyncio.CancelledError:
                logger.debug("Activity summary task cancelled")
                break
            except Exception as e:
                logger.error(f"Activity summary task exception: {e}", exc_info=True)

    async def _summarize_activities(self):
        """Get recent unsummarized events, call LLM to aggregate into activities"""
        try:
            # Get unaggregated events
            recent_events = await self._get_unsummarized_events()

            if not recent_events or len(recent_events) == 0:
                logger.debug("No events to summarize")
                return

            logger.debug(
                f"Starting to aggregate {len(recent_events)} events into activities"
            )

            # Call summarizer to aggregate
            activities = await self.summarizer.aggregate_events_to_activities(
                recent_events
            )

            # Save activities

            for activity_data in activities:
                start_time = activity_data.get("start_time", datetime.now())
                end_time = activity_data.get("end_time", start_time)

                start_time = start_time.isoformat() if isinstance(start_time, datetime) else str(start_time)
                end_time = end_time.isoformat() if isinstance(end_time, datetime) else str(end_time)

                source_event_ids = [
                    str(event_id)
                    for event_id in activity_data.get("source_event_ids", [])
                    if event_id
                ]

                await self.db.activities.save(
                    activity_id=activity_data["id"],
                    title=activity_data.get("title", ""),
                    description=activity_data.get("description", ""),
                    start_time=start_time,
                    end_time=end_time,
                    source_event_ids=source_event_ids,
                )
                self.stats["activities_created"] += 1

            logger.debug(f"Successfully created {len(activities)} activities")

        except Exception as e:
            logger.error(f"Failed to summarize activities: {e}", exc_info=True)

    async def _periodic_knowledge_merge(self):
        """Scheduled task: merge knowledge every N minutes"""
        while self.is_running:
            try:
                await asyncio.sleep(self.knowledge_merge_interval)
                await self._merge_knowledge()
            except asyncio.CancelledError:
                logger.debug("Knowledge merge task cancelled")
                break
            except Exception as e:
                logger.error(f"Knowledge merge task exception: {e}", exc_info=True)

    async def _merge_knowledge(self):
        """Merge related knowledge into combined_knowledge"""
        try:
            # Get unmerged knowledge
            unmerged_knowledge = await self.db.knowledge.get_unmerged()

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

            logger.debug(f"Starting to merge {len(unmerged_knowledge)} knowledge")

            # Call summarizer to merge
            combined = await self.summarizer.merge_knowledge(unmerged_knowledge)

            # Save combined_knowledge
            merged_source_ids: Set[str] = set()
            for combined_data in combined:
                await self.db.knowledge.save_combined(
                    knowledge_id=combined_data["id"],
                    title=combined_data.get("title", ""),
                    description=combined_data.get("description", ""),
                    keywords=combined_data.get("keywords", []),
                    merged_from_ids=combined_data.get("merged_from_ids", []),
                )
                self.stats["combined_knowledge_created"] += 1
                merged_source_ids.update(
                    item_id
                    for item_id in combined_data.get("merged_from_ids", [])
                    if item_id
                )

            # Soft delete original knowledge records now represented by combined entries
            if merged_source_ids:
                deleted_count = await self.db.knowledge.delete_batch(
                    list(merged_source_ids)
                )
                if deleted_count:
                    logger.debug(
                        f"Deleted {deleted_count} original knowledge records after merge"
                    )

            logger.debug(f"Successfully merged into {len(combined)} combined_knowledge")

        except Exception as e:
            logger.error(f"Failed to merge knowledge: {e}", exc_info=True)

    async def _periodic_todo_merge(self):
        """Scheduled task: merge todos every N minutes"""
        while self.is_running:
            try:
                await asyncio.sleep(self.todo_merge_interval)
                await self._merge_todos()
            except asyncio.CancelledError:
                logger.debug("Todo merge task cancelled")
                break
            except Exception as e:
                logger.error(f"Todo merge task exception: {e}", exc_info=True)

    async def _merge_todos(self):
        """Merge related todos into combined_todos"""
        try:
            # Get unmerged todos
            unmerged_todos = await self.db.todos.get_unmerged()

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

            logger.debug(f"Starting to merge {len(unmerged_todos)} todos")

            # Call summarizer to merge
            combined = await self.summarizer.merge_todos(unmerged_todos)

            # Save combined_todos
            merged_todo_ids: Set[str] = set()
            for combined_data in combined:
                await self.db.todos.save_combined(
                    todo_id=combined_data["id"],
                    title=combined_data.get("title", ""),
                    description=combined_data.get("description", ""),
                    keywords=combined_data.get("keywords", []),
                    merged_from_ids=combined_data.get("merged_from_ids", []),
                    completed=bool(combined_data.get("completed", False)),
                )
                self.stats["combined_todos_created"] += 1
                merged_todo_ids.update(
                    item_id
                    for item_id in combined_data.get("merged_from_ids", [])
                    if item_id
                )

            # Soft delete original todos to reduce storage usage
            if merged_todo_ids:
                deleted_count = await self.db.todos.delete_batch(list(merged_todo_ids))
                if deleted_count:
                    logger.debug(f"Deleted {deleted_count} original todos after merge")

            logger.debug(f"Successfully merged into {len(combined)} combined_todos")

        except Exception as e:
            logger.error(f"Failed to merge todos: {e}", exc_info=True)

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics information"""
        return {
            "is_running": self.is_running,
            "screenshot_threshold": self.screenshot_threshold,
            "accumulated_screenshots": len(self.screenshot_accumulator),
            "stats": self.stats.copy(),
        }
