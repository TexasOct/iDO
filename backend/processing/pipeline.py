"""
Processing pipeline (optimized architecture)
Implements complete processing flow:
- raw_records → actions (from screenshots)
- actions → events → knowledge/todos (from text, no screenshots)

This reduces token consumption by extracting knowledge/todos from event text
rather than repeatedly processing the same screenshots.
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

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
        self.event_aggregation_task: Optional[asyncio.Task] = None
        self.knowledge_merge_task: Optional[asyncio.Task] = None
        self.todo_merge_task: Optional[asyncio.Task] = None

        # Statistics
        self.stats: Dict[str, Any] = {
            "total_screenshots": 0,
            "actions_created": 0,
            "knowledge_created": 0,
            "todos_created": 0,
            "events_created": 0,
            "combined_knowledge_created": 0,
            "combined_todos_created": 0,
            "last_processing_time": None,
        }

    async def _get_action_screenshot_hashes(self, action_id: str) -> List[str]:
        try:
            return await self.db.actions.get_screenshots(action_id)
        except Exception as exc:
            logger.error("Failed to load screenshot hashes for action %s: %s", action_id, exc)
            return []

    async def _load_action_screenshots_base64(self, action_id: str) -> List[str]:
        hashes = await self._get_action_screenshot_hashes(action_id)

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

    async def _get_unaggregated_actions(
        self, since: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Fetch actions not yet aggregated into events"""
        try:
            start_time = since or datetime.now() - timedelta(hours=1)
            end_time = datetime.now()

            actions = await self.db.actions.get_in_timeframe(
                start_time.isoformat(), end_time.isoformat()
            )

            aggregated_ids = set(await self.db.events.get_all_source_action_ids())

            result: List[Dict[str, Any]] = []
            for action in actions:
                if action.get("id") in aggregated_ids:
                    continue

                timestamp_value = action.get("timestamp")
                if isinstance(timestamp_value, str):
                    try:
                        timestamp_value = datetime.fromisoformat(timestamp_value)
                    except ValueError:
                        timestamp_value = datetime.now()

                result.append(
                    {
                        "id": action.get("id"),
                        "title": action.get("title"),
                        "description": action.get("description"),
                        "keywords": action.get("keywords", []),
                        "timestamp": timestamp_value,
                        "created_at": action.get("created_at"),
                    }
                )

            return result

        except Exception as exc:
            logger.error("Failed to get unaggregated actions: %s", exc, exc_info=True)
            return []

    async def start(self):
        """Start processing pipeline"""
        if self.is_running:
            logger.warning("Processing pipeline is already running")
            return

        self.is_running = True

        # Start scheduled tasks
        # Note: todo merge and knowledge merge are now handled by TodoAgent and KnowledgeAgent
        self.event_aggregation_task = asyncio.create_task(
            self._periodic_event_aggregation()
        )

        logger.info(f"Processing pipeline started (language: {self.language})")
        logger.debug(f"- Screenshot threshold: {self.screenshot_threshold}")
        logger.debug(f"- Event aggregation interval: {self.activity_summary_interval}s")
        logger.debug("- Todo extraction and merge: handled by TodoAgent")
        logger.debug("- Knowledge extraction and merge: handled by KnowledgeAgent")

    async def stop(self):
        """Stop processing pipeline"""
        if not self.is_running:
            return

        self.is_running = False

        # Cancel scheduled tasks
        if self.event_aggregation_task:
            self.event_aggregation_task.cancel()
        # Note: todo_merge_task and knowledge_merge_task removed as merging is handled by dedicated agents

        # Process remaining accumulated screenshots with a hard timeout to avoid shutdown hangs
        if self.screenshot_accumulator:
            remaining = len(self.screenshot_accumulator)
            try:
                await asyncio.wait_for(
                    self._extract_actions(self.screenshot_accumulator, [], []),
                    timeout=2.5,
                )
                logger.debug(f"Processed remaining {remaining} screenshots on shutdown")
            except asyncio.TimeoutError:
                logger.warning(
                    f"Shutdown flush timed out, dropping {remaining} pending screenshots"
                )
            except Exception as exc:
                logger.error(
                    f"Failed to process remaining screenshots during shutdown: {exc}",
                    exc_info=True,
                )
            finally:
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
                # Pass keyboard/mouse records for timestamp extraction
                await self._extract_actions(
                    self.screenshot_accumulator,
                    keyboard_records,
                    mouse_records,
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

    async def _extract_actions(
        self,
        records: List[RawRecord],
        keyboard_records: List[RawRecord],
        mouse_records: List[RawRecord],
    ):
        """
        Call LLM to extract actions from screenshots

        Note: Knowledge and TODO extraction now happens in event aggregation phase,
        reducing token consumption by avoiding repeated screenshot processing.

        Args:
            records: Record list (mainly screenshots)
            keyboard_records: Keyboard event records
            mouse_records: Mouse event records
        """
        if not records:
            return

        try:
            logger.debug(
                f"Starting to extract actions from {len(records)} screenshots"
            )

            # Build keyboard/mouse activity hint (legacy)
            has_keyboard_activity = len(keyboard_records) > 0
            has_mouse_activity = len(mouse_records) > 0
            input_usage_hint = self._build_input_usage_hint(
                has_keyboard_activity, has_mouse_activity
            )

            # Extract screenshot records for timestamp calculation
            screenshot_records = [
                r for r in records if r.type == RecordType.SCREENSHOT_RECORD
            ]

            # Call summarizer to extract actions only
            result = await self.summarizer.extract_actions_only(
                records,
                input_usage_hint=input_usage_hint,
                keyboard_records=keyboard_records,
                mouse_records=mouse_records,
            )

            actions = result.get("actions", [])

            # Validate screenshot indices for every action first. If any action lacks
            # valid indices, drop the entire batch to avoid mismatched screenshots.
            resolved_actions: List[Dict[str, Any]] = []
            for action_data in actions:
                action_hashes = self._resolve_action_screenshot_hashes(
                    action_data, records
                )
                if not action_hashes:
                    logger.warning(
                        "Dropping extraction batch: invalid image_index in action '%s'",
                        action_data.get("title", "<no title>"),
                    )
                    return

                resolved_actions.append({"data": action_data, "hashes": action_hashes})

            # Save actions only after validation passes
            for resolved in resolved_actions:
                action_data = resolved["data"]
                action_hashes = resolved["hashes"]
                action_id = str(uuid.uuid4())

                # Calculate timestamp specific to this action
                image_indices = action_data.get("image_index") or action_data.get(
                    "imageIndex", []
                )
                action_timestamp = self._calculate_action_timestamp(
                    image_indices, screenshot_records
                )

                await self.db.actions.save(
                    action_id=action_id,
                    title=action_data["title"],
                    description=action_data["description"],
                    keywords=action_data.get("keywords", []),
                    timestamp=action_timestamp.isoformat(),
                    screenshots=action_hashes,
                )

            # Note: Knowledge and TODO extraction now happens in event aggregation phase
            # This reduces token consumption by avoiding repeated screenshot processing

            # Update statistics
            self.stats["actions_created"] += len(actions)
            self.stats["last_processing_time"] = datetime.now()

            logger.debug(
                f"Extraction completed: {len(actions)} actions"
            )

        except Exception as e:
            logger.error(
                f"Failed to extract actions: {e}", exc_info=True
            )

    def _calculate_action_timestamp(
        self, image_indices: List[int], screenshot_records: List[RawRecord]
    ) -> datetime:
        """
        Calculate action timestamp as earliest time among referenced screenshots.

        Args:
            image_indices: Screenshot indices from LLM (e.g., [0, 1, 2])
            screenshot_records: List of screenshot RawRecords

        Returns:
            Earliest timestamp among referenced screenshots
        """
        if not image_indices:
            # Fallback: use earliest screenshot overall
            logger.warning("Action has empty image_index, using earliest screenshot")
            return min(r.timestamp for r in screenshot_records)

        # Validate indices
        max_idx = len(screenshot_records) - 1
        valid_indices = [i for i in image_indices if 0 <= i <= max_idx]

        if not valid_indices:
            logger.warning(
                f"Action has invalid image_indices {image_indices}, "
                f"max valid index is {max_idx}. Using earliest screenshot."
            )
            return min(r.timestamp for r in screenshot_records)

        if len(valid_indices) < len(image_indices):
            invalid = set(image_indices) - set(valid_indices)
            logger.warning(f"Ignoring invalid image indices: {invalid}")

        # Return earliest timestamp among referenced screenshots
        referenced_times = [screenshot_records[i].timestamp for i in valid_indices]
        return min(referenced_times)

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

    def _resolve_action_screenshot_hashes(
        self, action_data: Dict[str, Any], records: List[RawRecord]
    ) -> Optional[List[str]]:
        """
        Resolve screenshot hashes based on image_index from LLM response

        Args:
            action_data: Action data containing image_index (or imageIndex)
            records: All raw records (screenshots)

        Returns:
            List of screenshot hashes filtered by image_index
        """
        # Get image_index from action data (support both snake_case and camelCase)
        image_indices = action_data.get("image_index") or action_data.get("imageIndex")

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

                            # Limit to 6 screenshots per action
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

        logger.warning("Action missing valid image_index: %s", image_indices)
        return None

    # ============ Scheduled Tasks ============

    async def _periodic_event_aggregation(self):
        """Scheduled task: aggregate events every N minutes"""
        while self.is_running:
            try:
                await asyncio.sleep(self.activity_summary_interval)
                await self._aggregate_events()
            except asyncio.CancelledError:
                logger.debug("Event aggregation task cancelled")
                break
            except Exception as e:
                logger.error(f"Event aggregation task exception: {e}", exc_info=True)

    async def _aggregate_events(self):
        """Get recent unaggregated actions, call LLM to aggregate into events, then extract todos and knowledge"""
        try:
            # Get unaggregated actions
            recent_actions = await self._get_unaggregated_actions()

            if not recent_actions or len(recent_actions) == 0:
                logger.debug("No actions to aggregate")
                return

            logger.debug(
                f"Starting to aggregate {len(recent_actions)} actions into events"
            )

            # Call summarizer to aggregate
            events = await self.summarizer.aggregate_actions_to_events(
                recent_actions
            )

            if not events:
                logger.debug("No events were created from aggregation")
                return

            # Save events
            for event_data in events:
                start_time = event_data.get("start_time", datetime.now())
                end_time = event_data.get("end_time", start_time)

                start_time = start_time.isoformat() if isinstance(start_time, datetime) else str(start_time)
                end_time = end_time.isoformat() if isinstance(end_time, datetime) else str(end_time)

                source_action_ids = [
                    str(action_id)
                    for action_id in event_data.get("source_action_ids", [])
                    if action_id
                ]

                await self.db.events.save(
                    event_id=event_data["id"],
                    title=event_data.get("title", ""),
                    description=event_data.get("description", ""),
                    start_time=start_time,
                    end_time=end_time,
                    source_action_ids=source_action_ids,
                )
                self.stats["events_created"] += 1

            logger.debug(f"Successfully created {len(events)} events")

            # Extract TODOs from events (text-based, no screenshots)
            try:
                todos = await self.summarizer.extract_todos_from_events(events)

                # Calculate fallback timestamp for todos
                fallback_timestamp = datetime.now()
                if events:
                    first_event_time = events[0].get("start_time")
                    if isinstance(first_event_time, datetime):
                        fallback_timestamp = first_event_time
                    elif isinstance(first_event_time, str):
                        try:
                            fallback_timestamp = datetime.fromisoformat(first_event_time)
                        except ValueError:
                            pass

                for todo_data in todos:
                    todo_id = str(uuid.uuid4())
                    await self.db.todos.save(
                        todo_id=todo_id,
                        title=todo_data["title"],
                        description=todo_data["description"],
                        keywords=todo_data.get("keywords", []),
                        created_at=fallback_timestamp.isoformat(),
                    )

                self.stats["todos_created"] += len(todos)
                logger.debug(f"Extracted {len(todos)} todos from events")
            except Exception as e:
                logger.error(f"Failed to extract todos from events: {e}", exc_info=True)

            # Extract knowledge from events (text-based, no screenshots)
            try:
                knowledge_list = await self.summarizer.extract_knowledge_from_events(events)

                # Calculate fallback timestamp for knowledge
                fallback_timestamp = datetime.now()
                if events:
                    first_event_time = events[0].get("start_time")
                    if isinstance(first_event_time, datetime):
                        fallback_timestamp = first_event_time
                    elif isinstance(first_event_time, str):
                        try:
                            fallback_timestamp = datetime.fromisoformat(first_event_time)
                        except ValueError:
                            pass

                for knowledge_data in knowledge_list:
                    knowledge_id = str(uuid.uuid4())
                    await self.db.knowledge.save(
                        knowledge_id=knowledge_id,
                        title=knowledge_data["title"],
                        description=knowledge_data["description"],
                        keywords=knowledge_data.get("keywords", []),
                        created_at=fallback_timestamp.isoformat(),
                    )

                self.stats["knowledge_created"] += len(knowledge_list)
                logger.debug(f"Extracted {len(knowledge_list)} knowledge items from events")
            except Exception as e:
                logger.error(f"Failed to extract knowledge from events: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"Failed to aggregate events: {e}", exc_info=True)

    # Note: _periodic_knowledge_merge() and _merge_knowledge() methods removed
    # Knowledge merging is now handled by KnowledgeAgent

    # Note: _periodic_todo_merge() and _merge_todos() methods removed
    # TODO merging is now handled by TodoAgent

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics information"""
        return {
            "is_running": self.is_running,
            "screenshot_threshold": self.screenshot_threshold,
            "accumulated_screenshots": len(self.screenshot_accumulator),
            "stats": self.stats.copy(),
        }
