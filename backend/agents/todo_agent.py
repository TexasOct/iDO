"""
TodoAgent - Intelligent agent for TODO extraction and periodic merging
Extracts TODOs from screenshots and merges related TODOs periodically
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
        merge_interval: int = 1200,  # 20 minutes
    ):
        """
        Initialize TodoAgent

        Args:
            merge_interval: How often to run TODO merging (seconds, default 20min)
        """
        self.merge_interval = merge_interval

        # Initialize components
        self.db = get_db()
        self.llm_manager = get_llm_manager()
        self.settings = get_settings()

        # Running state
        self.is_running = False
        self.merge_task: Optional[asyncio.Task] = None

        # Statistics
        self.stats: Dict[str, Any] = {
            "todos_extracted": 0,
            "todos_merged": 0,
            "last_merge_time": None,
        }

        logger.debug(f"TodoAgent initialized (merge_interval: {merge_interval}s)")

    def _get_language(self) -> str:
        """Get current language setting from config with caching"""
        return self.settings.get_language()

    async def start(self):
        """Start the TODO agent"""
        if self.is_running:
            logger.warning("TodoAgent is already running")
            return

        self.is_running = True

        # Start merge task
        self.merge_task = asyncio.create_task(self._periodic_todo_merge())

        logger.info(f"TodoAgent started (merge interval: {self.merge_interval}s)")

    async def stop(self):
        """Stop the TODO agent"""
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

        logger.info("TodoAgent stopped")

    async def _periodic_todo_merge(self):
        """Scheduled task: merge TODOs every N minutes"""
        while self.is_running:
            try:
                await asyncio.sleep(self.merge_interval)
                await self._merge_todos()
            except asyncio.CancelledError:
                logger.debug("TODO merge task cancelled")
                break
            except Exception as e:
                logger.error(f"TODO merge task exception: {e}", exc_info=True)

    async def extract_todos(
        self,
        records: List[RawRecord],
        keyboard_records: Optional[List[RawRecord]] = None,
        mouse_records: Optional[List[RawRecord]] = None,
        enable_supervisor: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Extract TODOs from raw records (screenshots)

        Args:
            records: List of raw records (mainly screenshots)
            keyboard_records: Keyboard event records for timestamp extraction
            mouse_records: Mouse event records for timestamp extraction
            enable_supervisor: Whether to enable supervisor validation (default True)

        Returns:
            List of TODO dictionaries
        """
        if not records:
            return []

        try:
            logger.debug(f"TodoAgent: Extracting TODOs from {len(records)} records")

            # Import here to avoid circular dependency
            from processing.summarizer import EventSummarizer

            # Get current language from settings
            language = self._get_language()
            summarizer = EventSummarizer(language=language)
            result = await summarizer.extract_todos_only(
                records, keyboard_records, mouse_records
            )

            todos = result.get("todos", [])

            # Apply supervisor validation if enabled
            if enable_supervisor and todos:
                todos = await self._validate_with_supervisor(todos)

            self.stats["todos_extracted"] += len(todos)

            logger.debug(f"TodoAgent: Extracted {len(todos)} TODOs")
            return todos

        except Exception as e:
            logger.error(f"TodoAgent: Failed to extract TODOs: {e}", exc_info=True)
            return []

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

    async def _merge_todos(self):
        """
        Main merge logic:
        1. Get unmerged TODOs from database
        2. Call LLM to merge related TODOs
        3. Save merged results to combined_todos table
        4. Soft delete original TODOs
        """
        try:
            # Get unmerged todos
            unmerged_todos = await self.db.todos.get_unmerged()

            if not unmerged_todos or len(unmerged_todos) == 0:
                logger.debug("TodoAgent: No TODOs to merge")
                return

            logger.debug(f"TodoAgent: Starting to merge {len(unmerged_todos)} TODOs")

            # Call LLM to merge
            from processing.summarizer import EventSummarizer

            # Get current language from settings
            language = self._get_language()
            summarizer = EventSummarizer(language=language)
            merged_todos = await summarizer.merge_todos(unmerged_todos)

            if not merged_todos:
                logger.debug("TodoAgent: No merged TODOs generated")
                return

            # Save merged TODOs and mark originals as deleted
            for merged_todo in merged_todos:
                merged_todo_id = str(uuid.uuid4())
                source_todo_ids = merged_todo.get("merged_from_ids", [])

                if not source_todo_ids:
                    logger.warning("TodoAgent: Merged TODO has no source IDs, skipping")
                    continue

                # Save to combined_todos
                await self.db.todos.save_combined(
                    todo_id=merged_todo_id,
                    title=merged_todo.get("title", ""),
                    description=merged_todo.get("description", ""),
                    keywords=merged_todo.get("keywords", []),
                    merged_from_ids=source_todo_ids,
                )

                # Soft delete source todos
                await self.db.todos.delete_batch(source_todo_ids)

                self.stats["todos_merged"] += 1

            self.stats["last_merge_time"] = datetime.now()

            logger.debug(
                f"TodoAgent: Merge completed, created {len(merged_todos)} merged TODOs"
            )

        except Exception as e:
            logger.error(f"TodoAgent: Failed to merge TODOs: {e}", exc_info=True)

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics information"""
        return {
            "is_running": self.is_running,
            "merge_interval": self.merge_interval,
            "language": self._get_language(),
            "stats": self.stats.copy(),
        }
