"""
KnowledgeAgent - Intelligent agent for knowledge extraction and periodic merging
Extracts knowledge from screenshots and merges related knowledge periodically
"""

import asyncio
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.db import get_db
from core.logger import get_logger
from core.models import RawRecord
from core.settings import get_settings
from llm.manager import get_llm_manager

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
        merge_interval: int = 1200,  # 20 minutes
    ):
        """
        Initialize KnowledgeAgent

        Args:
            merge_interval: How often to run knowledge merging (seconds, default 20min)
        """
        self.merge_interval = merge_interval

        # Initialize components
        self.db = get_db()
        self.llm_manager = get_llm_manager()
        self.settings = get_settings()

        # Running state
        self.is_running = False
        self.merge_task: Optional[asyncio.Task] = None
        self.catchup_task: Optional[asyncio.Task] = None

        # Statistics
        self.stats: Dict[str, Any] = {
            "knowledge_extracted": 0,
            "knowledge_merged": 0,
            "last_merge_time": None,
        }

        logger.debug(f"KnowledgeAgent initialized (merge_interval: {merge_interval}s)")

    def _get_language(self) -> str:
        """Get current language setting from config with caching"""
        return self.settings.get_language()

    async def start(self):
        """Start the knowledge agent"""
        if self.is_running:
            logger.warning("KnowledgeAgent is already running")
            return

        self.is_running = True

        # Start merge task
        self.merge_task = asyncio.create_task(self._periodic_knowledge_merge())

        # Start catchup task
        self.catchup_task = asyncio.create_task(self._periodic_catchup())

        logger.info(
            f"KnowledgeAgent started (merge: {self.merge_interval}s, catchup: 300s)"
        )

    async def stop(self):
        """Stop the knowledge agent"""
        if not self.is_running:
            return

        self.is_running = False

        # Cancel merge task
        if self.merge_task:
            self.merge_task.cancel()
            try:
                await self.merge_task
            except asyncio.CancelledError:
                pass

        # Cancel catchup task
        if self.catchup_task:
            self.catchup_task.cancel()
            try:
                await self.catchup_task
            except asyncio.CancelledError:
                pass

        logger.info("KnowledgeAgent stopped")

    async def _periodic_knowledge_merge(self):
        """Scheduled task: merge knowledge every N minutes"""
        while self.is_running:
            try:
                await asyncio.sleep(self.merge_interval)
                await self._merge_knowledge()
            except asyncio.CancelledError:
                logger.debug("Knowledge merge task cancelled")
                break
            except Exception as e:
                logger.error(f"Knowledge merge task exception: {e}", exc_info=True)

    async def extract_knowledge(
        self,
        records: List[RawRecord],
        keyboard_records: Optional[List[RawRecord]] = None,
        mouse_records: Optional[List[RawRecord]] = None,
        enable_supervisor: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Extract knowledge from raw records (screenshots)

        Args:
            records: List of raw records (mainly screenshots)
            keyboard_records: Keyboard event records for timestamp extraction
            mouse_records: Mouse event records for timestamp extraction
            enable_supervisor: Whether to enable supervisor validation (default True)

        Returns:
            List of knowledge dictionaries
        """
        if not records:
            return []

        try:
            logger.debug(f"KnowledgeAgent: Extracting knowledge from {len(records)} records")

            # Import here to avoid circular dependency
            from processing.summarizer import EventSummarizer

            # Get current language from settings
            language = self._get_language()
            summarizer = EventSummarizer(language=language)
            result = await summarizer.extract_knowledge_only(
                records, keyboard_records, mouse_records
            )

            knowledge_list = result.get("knowledge", [])

            # Apply supervisor validation if enabled
            if enable_supervisor and knowledge_list:
                knowledge_list = await self._validate_with_supervisor(knowledge_list)

            self.stats["knowledge_extracted"] += len(knowledge_list)

            logger.debug(f"KnowledgeAgent: Extracted {len(knowledge_list)} knowledge items")
            return knowledge_list

        except Exception as e:
            logger.error(f"KnowledgeAgent: Failed to extract knowledge: {e}", exc_info=True)
            return []

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

    async def _merge_knowledge(self):
        """
        Main merge logic:
        1. Get unmerged knowledge from database
        2. Call LLM to merge related knowledge
        3. Save merged results to combined_knowledge table
        4. Soft delete original knowledge
        """
        try:
            # Get unmerged knowledge
            unmerged_knowledge = await self.db.knowledge.get_unmerged()

            if not unmerged_knowledge or len(unmerged_knowledge) < 2:
                logger.debug("KnowledgeAgent: Insufficient knowledge count, skipping merge")
                return

            logger.debug(f"KnowledgeAgent: Starting to merge {len(unmerged_knowledge)} knowledge items")

            # Call LLM to merge
            from processing.summarizer import EventSummarizer

            # Get current language from settings
            language = self._get_language()
            summarizer = EventSummarizer(language=language)
            merged_knowledge = await summarizer.merge_knowledge(unmerged_knowledge)

            if not merged_knowledge:
                logger.debug("KnowledgeAgent: No merged knowledge generated")
                return

            # Save merged knowledge and mark originals as deleted
            for merged_item in merged_knowledge:
                merged_knowledge_id = str(uuid.uuid4())
                source_knowledge_ids = merged_item.get("merged_from_ids", [])

                if not source_knowledge_ids:
                    logger.warning("KnowledgeAgent: Merged knowledge has no source IDs, skipping")
                    continue

                # Save to combined_knowledge
                await self.db.knowledge.save_combined(
                    knowledge_id=merged_knowledge_id,
                    title=merged_item.get("title", ""),
                    description=merged_item.get("description", ""),
                    keywords=merged_item.get("keywords", []),
                    merged_from_ids=source_knowledge_ids,
                )

                # Soft delete source knowledge
                await self.db.knowledge.delete_batch(source_knowledge_ids)

                self.stats["knowledge_merged"] += 1

            self.stats["last_merge_time"] = datetime.now()

            logger.debug(
                f"KnowledgeAgent: Merge completed, created {len(merged_knowledge)} merged knowledge items"
            )

        except Exception as e:
            logger.error(f"KnowledgeAgent: Failed to merge knowledge: {e}", exc_info=True)

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics information"""
        return {
            "is_running": self.is_running,
            "merge_interval": self.merge_interval,
            "language": self._get_language(),
            "stats": self.stats.copy(),
        }

    async def extract_knowledge_from_action(
        self,
        action_id: str,
        enable_supervisor: bool = True,
    ) -> int:
        """
        Extract knowledge from a single action (called after action is saved)

        Args:
            action_id: ID of the action to extract knowledge from
            enable_supervisor: Whether to enable supervisor validation

        Returns:
            Number of knowledge items extracted and saved
        """
        try:
            logger.debug(f"KnowledgeAgent: Extracting knowledge from action {action_id}")

            # Load action with screenshots
            action = await self.db.actions.get_by_id(action_id)
            if not action:
                logger.warning(f"KnowledgeAgent: Action {action_id} not found")
                return 0

            # Load screenshots as base64
            screenshots = await self._load_action_screenshots_base64(action_id)
            action["screenshots"] = screenshots

            # Call EventSummarizer
            from processing.summarizer import EventSummarizer

            language = self._get_language()
            summarizer = EventSummarizer(language=language)
            knowledge_list = await summarizer.extract_knowledge_from_action(action)

            if not knowledge_list:
                logger.debug(f"No knowledge extracted from action {action_id}")
                await self.db.actions.mark_knowledge_extracted(action_id)
                return 0

            # Apply supervisor validation
            if enable_supervisor:
                knowledge_list = await self._validate_with_supervisor(knowledge_list)

            # Save knowledge items
            import uuid
            from datetime import datetime

            saved_count = 0
            for knowledge_data in knowledge_list:
                knowledge_id = str(uuid.uuid4())
                await self.db.knowledge.save(
                    knowledge_id=knowledge_id,
                    title=knowledge_data.get("title", ""),
                    description=knowledge_data.get("description", ""),
                    keywords=knowledge_data.get("keywords", []),
                    created_at=action.get("timestamp") or datetime.now().isoformat(),
                    source_action_id=action_id,
                )
                saved_count += 1

            # Mark action as extracted
            await self.db.actions.mark_knowledge_extracted(action_id)

            self.stats["knowledge_extracted"] += saved_count

            logger.debug(f"Extracted {saved_count} knowledge items from action {action_id}")
            return saved_count

        except Exception as e:
            logger.error(f"Failed to extract knowledge from action {action_id}: {e}", exc_info=True)
            return 0

    async def _load_action_screenshots_base64(self, action_id: str) -> list[str]:
        """Load action screenshots as base64 strings"""
        try:
            from processing.image_manager import get_image_manager

            image_manager = get_image_manager()
            hashes = await self.db.actions.get_screenshots(action_id)

            screenshots = []
            for img_hash in hashes:
                if not img_hash:
                    continue

                data = image_manager.get_from_cache(img_hash)
                if not data:
                    data = image_manager.load_thumbnail_base64(img_hash)

                if data:
                    screenshots.append(data)

            return screenshots

        except Exception as e:
            logger.error(f"Failed to load screenshots for action {action_id}: {e}", exc_info=True)
            return []

    async def process_pending_extractions(self, limit: int = 10) -> int:
        """
        Process actions with extract_knowledge=true but knowledge_extracted=false
        Catch-up mechanism for missed extractions.
        """
        try:
            pending_actions = await self.db.actions.get_pending_knowledge_extraction(limit)

            if not pending_actions:
                return 0

            logger.debug(f"Processing {len(pending_actions)} pending knowledge extractions")

            total_extracted = 0
            for action in pending_actions:
                action_id = action.get("id")
                if action_id:
                    count = await self.extract_knowledge_from_action(action_id)
                    total_extracted += count

            logger.debug(f"Batch processing completed: extracted {total_extracted} knowledge items")
            return total_extracted

        except Exception as e:
            logger.error(f"Failed to process pending extractions: {e}", exc_info=True)
            return 0

    async def _periodic_catchup(self):
        """Scheduled task: catch up on missed extractions every 5 minutes"""
        catchup_interval = 300  # 5 minutes

        while self.is_running:
            try:
                await asyncio.sleep(catchup_interval)
                await self.process_pending_extractions(limit=20)
            except asyncio.CancelledError:
                logger.debug("Knowledge catchup task cancelled")
                break
            except Exception as e:
                logger.error(f"Knowledge catchup task exception: {e}", exc_info=True)

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

            # Step 1: Extract knowledge from scenes using LLM (text-only, no images)
            from processing.summarizer import EventSummarizer

            language = self._get_language()
            summarizer = EventSummarizer(language=language)
            result = await summarizer.extract_knowledge_from_scenes(
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

