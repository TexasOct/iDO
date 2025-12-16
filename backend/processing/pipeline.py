"""
Processing pipeline (agent-based architecture)
Simplified pipeline that delegates to specialized agents:
- raw_records → ActionAgent → actions (complete flow: extract + save)
- actions → EventAgent → events (complete flow: aggregate + save)
- events → SessionAgent → activities (complete flow: aggregate + save)

Pipeline now only handles:
- Filtering raw records
- Accumulating screenshots to threshold
- Triggering ActionAgent when ready
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.db import get_db
from core.logger import get_logger
from core.models import RawRecord, RecordType

from perception.image_manager import get_image_manager

from .event_filter import EventFilter

logger = get_logger(__name__)


class ProcessingPipeline:
    """Processing pipeline (new architecture)"""

    def __init__(
        self,
        screenshot_threshold: int = 20,
        max_screenshots_per_extraction: int = 20,
        activity_summary_interval: int = 600,
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
            screenshot_threshold: Number of screenshots that trigger action extraction
            max_screenshots_per_extraction: Maximum number of screenshots to send to LLM per extraction
            activity_summary_interval: Activity summary interval (seconds, default 10 minutes)
            language: Language setting (zh|en)
            enable_screenshot_deduplication: Whether to enable screenshot deduplication
            screenshot_similarity_threshold: Similarity threshold for deduplication (0-1)
            screenshot_hash_cache_size: Number of hashes to cache for comparison
            screenshot_hash_algorithms: List of hash algorithms to use
            enable_adaptive_threshold: Whether to enable scene-adaptive thresholds
        """
        self.screenshot_threshold = screenshot_threshold
        self.max_screenshots_per_extraction = max_screenshots_per_extraction
        self.activity_summary_interval = activity_summary_interval
        self.language = language

        # Initialize components
        self.event_filter = EventFilter(
            enable_screenshot_deduplication=enable_screenshot_deduplication,
            similarity_threshold=screenshot_similarity_threshold,
            hash_cache_size=screenshot_hash_cache_size,
            hash_algorithms=screenshot_hash_algorithms,
            enable_adaptive_threshold=enable_adaptive_threshold,
        )
        self.db = get_db()
        self.image_manager = get_image_manager()

        # Running state
        self.is_running = False

        # Agent references (set by coordinator)
        self.action_agent = None
        self.raw_agent = None
        self.knowledge_agent = None
        self.todo_agent = None

        # Screenshot accumulator (in memory)
        self.screenshot_accumulator: List[RawRecord] = []

        # Note: No scheduled tasks in pipeline anymore
        # - Event aggregation: handled by EventAgent
        # - Session aggregation: handled by SessionAgent
        # - Knowledge merge: handled by KnowledgeAgent
        # - Todo merge: handled by TodoAgent

        # Statistics
        self.stats: Dict[str, Any] = {
            "total_screenshots": 0,
            "actions_created": 0,
            "knowledge_created": 0,
            "todos_created": 0,
            "events_created": 0,
            "last_processing_time": None,
        }

    # Note: Action processing methods removed - now handled by ActionAgent
    # The following methods have been moved to their respective agents:
    # - _get_action_screenshot_hashes: moved to ActionAgent
    # - _load_action_screenshots_base64: moved to ActionAgent
    # - _calculate_action_timestamp: moved to ActionAgent
    # - _trigger_knowledge_extraction: moved to ActionAgent
    # - _resolve_action_screenshot_hashes: moved to ActionAgent
    # - _get_unaggregated_actions: moved to EventAgent
    # - _aggregate_actions_to_events: moved to EventAgent
    # - _cluster_events_to_sessions: moved to SessionAgent

    async def start(self):
        """Start processing pipeline"""
        if self.is_running:
            logger.warning("Processing pipeline is already running")
            return

        self.is_running = True

        # Note: Event aggregation is now handled by EventAgent (started by coordinator)
        # Note: Todo merge and knowledge merge are handled by TodoAgent and KnowledgeAgent (started by coordinator)
        # Pipeline now only handles action extraction (triggered by raw record processing)

        logger.info(f"Processing pipeline started (language: {self.language})")
        logger.debug(f"- Screenshot threshold: {self.screenshot_threshold}")
        logger.debug("- Action extraction: handled inline via ActionAgent")
        logger.debug("- Event aggregation: handled by EventAgent")
        logger.debug("- Todo extraction and merge: handled by TodoAgent")
        logger.debug("- Knowledge extraction and merge: handled by KnowledgeAgent")

    async def stop(self):
        """Stop processing pipeline"""
        if not self.is_running:
            return

        self.is_running = False

        # Note: Event aggregation task removed as aggregation is handled by EventAgent
        # Note: Todo and knowledge merge tasks removed as merging is handled by dedicated agents

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
            should_process = len(self.screenshot_accumulator) >= self.screenshot_threshold

            # Force processing if accumulator grows too large (prevent unbounded growth)
            # This handles edge cases where deduplication keeps us below threshold
            if len(self.screenshot_accumulator) > self.screenshot_threshold * 1.5:
                logger.warning(
                    f"Screenshot accumulator exceeded 1.5x threshold "
                    f"({len(self.screenshot_accumulator)} > {self.screenshot_threshold * 1.5}), "
                    f"forcing processing"
                )
                should_process = True

            if should_process:
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
        Extract actions using new RawAgent → ActionAgent flow (memory-only)

        New architecture:
        1. RawAgent extracts scene descriptions from screenshots (images → text)
        2. ActionAgent extracts actions from scene descriptions (text → actions)
        3. Scenes are memory-only, auto garbage-collected after processing

        Args:
            records: Record list (mainly screenshots)
            keyboard_records: Keyboard event records
            mouse_records: Mouse event records
        """
        if not records:
            return

        try:
            logger.debug(
                f"Starting to extract actions from {len(records)} screenshots via RawAgent flow"
            )

            # Check agent availability
            if not self.raw_agent:
                logger.error("RawAgent not available, cannot process scenes")
                raise Exception("RawAgent not available")

            if not self.action_agent:
                logger.error("ActionAgent not available, cannot process actions")
                raise Exception("ActionAgent not available")

            # Step 1: Extract scene descriptions from screenshots (RawAgent)
            logger.debug("Step 1: Extracting scene descriptions via RawAgent")
            scenes = await self.raw_agent.extract_scenes(
                records,
                keyboard_records=keyboard_records,
                mouse_records=mouse_records,
            )

            if not scenes:
                logger.warning(
                    "RawAgent returned no scenes, skipping action extraction"
                )
                return

            logger.debug(
                f"RawAgent extracted {len(scenes)} scene descriptions "
                f"({sum(len(s.get('visual_summary', '')) for s in scenes)} chars total)"
            )

            # Step 2: Extract actions from scene descriptions (ActionAgent)
            logger.debug(
                "Step 2: Extracting actions from scenes via ActionAgent (text-only)"
            )
            saved_count = await self.action_agent.extract_and_save_actions_from_scenes(
                scenes,
                keyboard_records=keyboard_records,
                mouse_records=mouse_records,
            )

            # Update statistics
            self.stats["actions_created"] += saved_count
            self.stats["last_processing_time"] = datetime.now()

            logger.debug(
                f"ActionAgent completed: saved {saved_count} actions from {len(scenes)} scenes"
            )

            # Step 3: Extract knowledge and TODOs in parallel from same scenes
            logger.debug(
                "Step 3: Extracting knowledge and TODOs in parallel from scenes"
            )

            extraction_tasks = []

            # Add KnowledgeAgent extraction if available
            if self.knowledge_agent:
                knowledge_task = self.knowledge_agent.extract_knowledge_from_scenes(
                    scenes,
                    keyboard_records=keyboard_records,
                    mouse_records=mouse_records,
                )
                extraction_tasks.append(("knowledge", knowledge_task))

            # Add TodoAgent extraction if available
            if self.todo_agent:
                todo_task = self.todo_agent.extract_todos_from_scenes(
                    scenes,
                    keyboard_records=keyboard_records,
                    mouse_records=mouse_records,
                )
                extraction_tasks.append(("todo", todo_task))

            # Execute extractions in parallel
            if extraction_tasks:
                results = await asyncio.gather(
                    *[task for _, task in extraction_tasks],
                    return_exceptions=True,
                )

                # Process results and update statistics
                for (agent_type, _), result in zip(extraction_tasks, results):
                    if isinstance(result, Exception):
                        logger.error(f"{agent_type} extraction failed: {result}", exc_info=result)
                    elif isinstance(result, int):
                        if agent_type == "knowledge":
                            self.stats["knowledge_created"] += result
                            logger.debug(f"KnowledgeAgent extracted {result} knowledge items")
                        elif agent_type == "todo":
                            self.stats["todos_created"] += result
                            logger.debug(f"TodoAgent extracted {result} TODO items")

            # Step 4: Scenes auto garbage-collected (memory-only, no cleanup needed)
            logger.debug("Scene descriptions will be auto garbage-collected")

        except Exception as e:
            logger.error(f"Failed to extract actions: {e}", exc_info=True)


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


    # ============ Scheduled Tasks ============
    # Note: Event aggregation is now handled by EventAgent (started by coordinator)
    # Note: Knowledge merge is now handled by KnowledgeAgent (started by coordinator)
    # Note: Todo merge is now handled by TodoAgent (started by coordinator)

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics information"""
        return {
            "is_running": self.is_running,
            "screenshot_threshold": self.screenshot_threshold,
            "accumulated_screenshots": len(self.screenshot_accumulator),
            "stats": self.stats.copy(),
        }
