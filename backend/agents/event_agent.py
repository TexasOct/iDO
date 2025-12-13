"""
EventAgent - Intelligent agent for event aggregation from actions
Aggregates actions into events using LLM
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from core.db import get_db
from core.logger import get_logger
from core.settings import get_settings
from llm.manager import get_llm_manager

logger = get_logger(__name__)


class EventAgent:
    """
    Intelligent event aggregation agent

    Aggregates actions into events based on:
    - Semantic similarity (core): Actions describing the same work segment
    - Time continuity (strong signal): Actions within short time span
    - Task consistency (auxiliary): Actions forming a coherent task
    """

    def __init__(
        self,
        aggregation_interval: int = 600,  # 10 minutes
        time_window_hours: int = 1,  # Look back 1 hour for unaggregated actions
    ):
        """
        Initialize EventAgent

        Args:
            aggregation_interval: How often to run aggregation (seconds, default 10min)
            time_window_hours: Time window to look back for unaggregated actions (hours)
        """
        self.aggregation_interval = aggregation_interval
        self.time_window_hours = time_window_hours

        # Initialize components
        self.db = get_db()
        self.llm_manager = get_llm_manager()
        self.settings = get_settings()

        # Running state
        self.is_running = False
        self.aggregation_task: Optional[asyncio.Task] = None

        # Statistics
        self.stats: Dict[str, Any] = {
            "events_created": 0,
            "actions_aggregated": 0,
            "last_aggregation_time": None,
        }

        logger.debug(
            f"EventAgent initialized (interval: {aggregation_interval}s, "
            f"time_window: {time_window_hours}h)"
        )

    def _get_language(self) -> str:
        """Get current language setting from config with caching"""
        return self.settings.get_language()

    async def start(self):
        """Start the event agent"""
        if self.is_running:
            logger.warning("EventAgent is already running")
            return

        self.is_running = True

        # Start aggregation task
        self.aggregation_task = asyncio.create_task(self._periodic_event_aggregation())

        logger.info(
            f"EventAgent started (aggregation interval: {self.aggregation_interval}s)"
        )

    async def stop(self):
        """Stop the event agent"""
        if not self.is_running:
            return

        self.is_running = False

        # Cancel aggregation task
        if self.aggregation_task:
            self.aggregation_task.cancel()
            try:
                await self.aggregation_task
            except asyncio.CancelledError:
                pass

        logger.info("EventAgent stopped")

    async def _periodic_event_aggregation(self):
        """Scheduled task: aggregate events every N minutes"""
        while self.is_running:
            try:
                await asyncio.sleep(self.aggregation_interval)
                await self._aggregate_events()
            except asyncio.CancelledError:
                logger.debug("Event aggregation task cancelled")
                break
            except Exception as e:
                logger.error(f"Event aggregation task exception: {e}", exc_info=True)

    async def _aggregate_events(self):
        """
        Main aggregation logic:
        1. Get unaggregated actions
        2. Call LLM to aggregate into events
        3. Apply supervisor validation
        4. Save events to database
        """
        try:
            # Get unaggregated actions
            unaggregated_actions = await self._get_unaggregated_actions()

            if not unaggregated_actions or len(unaggregated_actions) == 0:
                logger.debug("No actions to aggregate into events")
                return

            logger.debug(
                f"Starting to aggregate {len(unaggregated_actions)} actions into events"
            )

            # Call LLM to aggregate actions into events
            events = await self._aggregate_actions_to_events(unaggregated_actions)

            if not events:
                logger.debug("No events generated from action aggregation")
                return

            # Save events and update statistics
            for event_data in events:
                event_id = event_data.get("id")
                if not event_id:
                    logger.warning("Event missing id, skipping")
                    continue

                source_action_ids = event_data.get("source_action_ids", [])
                if not source_action_ids:
                    logger.warning(f"Event {event_id} has no source actions, skipping")
                    continue

                # Convert timestamps
                start_time = event_data.get("start_time", datetime.now())
                end_time = event_data.get("end_time", start_time)

                start_time = (
                    start_time.isoformat()
                    if isinstance(start_time, datetime)
                    else str(start_time)
                )
                end_time = (
                    end_time.isoformat()
                    if isinstance(end_time, datetime)
                    else str(end_time)
                )

                # Save event
                await self.db.events.save(
                    event_id=event_id,
                    title=event_data.get("title", ""),
                    description=event_data.get("description", ""),
                    start_time=start_time,
                    end_time=end_time,
                    source_action_ids=[str(aid) for aid in source_action_ids if aid],
                )

                self.stats["events_created"] += 1
                self.stats["actions_aggregated"] += len(source_action_ids)

            self.stats["last_aggregation_time"] = datetime.now()

            logger.debug(
                f"Event aggregation completed: created {len(events)} events "
                f"from {self.stats['actions_aggregated']} actions"
            )

        except Exception as e:
            logger.error(f"Failed to aggregate events: {e}", exc_info=True)

    async def _get_unaggregated_actions(
        self, since: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch actions not yet aggregated into events

        Args:
            since: Starting time to fetch actions from

        Returns:
            List of action dictionaries
        """
        try:
            # Default: fetch actions from last N hours
            start_time = since or datetime.now() - timedelta(hours=self.time_window_hours)
            end_time = datetime.now()

            # Get actions in timeframe
            actions = await self.db.actions.get_in_timeframe(
                start_time.isoformat(), end_time.isoformat()
            )

            # Get all source action IDs that are already aggregated
            aggregated_ids = set(await self.db.events.get_all_source_action_ids())

            # Filter out already aggregated actions
            result: List[Dict[str, Any]] = []
            filtered_count = 0

            for action in actions:
                action_id = action.get("id")
                if action_id in aggregated_ids:
                    filtered_count += 1
                    continue

                # Normalize timestamp
                timestamp_value = action.get("timestamp")
                if isinstance(timestamp_value, str):
                    try:
                        timestamp_value = datetime.fromisoformat(timestamp_value)
                    except ValueError:
                        timestamp_value = datetime.now()

                result.append(
                    {
                        "id": action_id,
                        "title": action.get("title"),
                        "description": action.get("description"),
                        "keywords": action.get("keywords", []),
                        "timestamp": timestamp_value,
                        "created_at": action.get("created_at"),
                    }
                )

            logger.debug(
                f"Action filtering: {len(actions)} total, {filtered_count} already aggregated, "
                f"{len(result)} remaining"
            )

            return result

        except Exception as exc:
            logger.error("Failed to get unaggregated actions: %s", exc, exc_info=True)
            return []

    async def _aggregate_actions_to_events(
        self, actions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Use LLM to aggregate actions into events

        Args:
            actions: List of action dictionaries

        Returns:
            List of event dictionaries
        """
        if not actions:
            return []

        try:
            logger.debug(f"Aggregating {len(actions)} actions into events")

            # Import here to avoid circular dependency
            from processing.summarizer import EventSummarizer

            # Get current language from settings
            language = self._get_language()
            summarizer = EventSummarizer(language=language)

            # Call summarizer to aggregate
            events = await summarizer.aggregate_actions_to_events(actions)

            logger.debug(
                f"Aggregation completed: generated {len(events)} events (before validation)"
            )

            # Validate with supervisor (EventSupervisor already integrated in summarizer)
            # No additional validation needed here

            return events

        except Exception as e:
            logger.error(f"Failed to aggregate actions to events: {e}", exc_info=True)
            return []

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics information"""
        return {
            "is_running": self.is_running,
            "aggregation_interval": self.aggregation_interval,
            "time_window_hours": self.time_window_hours,
            "language": self._get_language(),
            "stats": self.stats.copy(),
        }
