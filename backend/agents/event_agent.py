"""
EventAgent - Intelligent agent for event aggregation from actions
Aggregates actions into events using LLM
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from core.db import get_db
from core.json_parser import parse_json_from_response
from core.logger import get_logger
from core.settings import get_settings
from llm.manager import get_llm_manager
from llm.prompt_manager import PromptManager

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

        # Initialize prompt manager
        language = self.settings.get_language()
        self.prompt_manager = PromptManager(language=language)

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

    def _refresh_prompt_manager(self):
        """Refresh prompt manager if language changed"""
        current_language = self._get_language()
        if self.prompt_manager.language != current_language:
            self.prompt_manager = PromptManager(language=current_language)
            logger.debug(f"Prompt manager refreshed for language: {current_language}")

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

            # Refresh prompt manager if language changed
            self._refresh_prompt_manager()

            # Call LLM to aggregate
            events = await self._aggregate_actions_llm(actions)

            logger.debug(
                f"Aggregation completed: generated {len(events)} events (after validation)"
            )

            return events

        except Exception as e:
            logger.error(f"Failed to aggregate actions to events: {e}", exc_info=True)
            return []

    async def _aggregate_actions_llm(
        self, actions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Call LLM to aggregate actions into events

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
            config_params = self.prompt_manager.get_config_params("event_aggregation")

            # Call LLM
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
                # Normalize and deduplicate the LLM provided source indexes
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

            # Validate with supervisor
            events = await self._validate_events_with_supervisor(events, actions)

            return events

        except Exception as e:
            logger.error(f"Failed to aggregate events: {e}", exc_info=True)
            return []

    def _normalize_source_indexes(
        self, source_value: Any, max_index: int
    ) -> List[int]:
        """
        Normalize source indexes from LLM response

        Args:
            source_value: Source value from LLM (can be list, int, or string)
            max_index: Maximum valid index

        Returns:
            List of normalized indexes (deduplicated, sorted)
        """
        indexes = []

        # Handle different formats
        if isinstance(source_value, list):
            for item in source_value:
                try:
                    idx = int(item)
                    if 1 <= idx <= max_index:
                        indexes.append(idx)
                except (ValueError, TypeError):
                    pass
        elif isinstance(source_value, (int, str)):
            try:
                idx = int(source_value)
                if 1 <= idx <= max_index:
                    indexes.append(idx)
            except (ValueError, TypeError):
                pass

        # Deduplicate and sort
        return sorted(list(set(indexes)))

    async def _validate_events_with_supervisor(
        self,
        events: List[Dict[str, Any]],
        source_actions: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Validate events with EventSupervisor

        Args:
            events: List of events to validate
            source_actions: Optional list of all source actions for semantic validation

        Returns:
            Validated (and possibly revised) list of events
        """
        if not events:
            return events

        try:
            from agents.supervisor import EventSupervisor

            supervisor = EventSupervisor(language=self._get_language())

            # Prepare events for validation (only title and description)
            events_for_validation = [
                {
                    "title": event.get("title", ""),
                    "description": event.get("description", ""),
                }
                for event in events
            ]

            # Build action mapping for semantic validation
            actions_for_validation = None
            if source_actions:
                # Create a mapping of action IDs to actions for lookup
                action_map = {
                    action.get("id"): action
                    for action in source_actions
                    if action.get("id")
                }

                # For each event, collect its source actions
                actions_for_validation = []
                for event in events:
                    source_action_ids = event.get("source_action_ids", [])
                    event_actions = []
                    for action_id in source_action_ids:
                        if action_id in action_map:
                            event_actions.append(action_map[action_id])

                    actions_for_validation.extend(event_actions)

                # Remove duplicates while preserving order
                seen_ids = set()
                unique_actions = []
                for action in actions_for_validation:
                    action_id = action.get("id")
                    if action_id and action_id not in seen_ids:
                        seen_ids.add(action_id)
                        unique_actions.append(action)
                actions_for_validation = unique_actions

            # Validate with source actions
            result = await supervisor.validate(
                events_for_validation, source_actions=actions_for_validation
            )

            if not result.is_valid and result.revised_content:
                logger.info(
                    f"EventSupervisor found issues: {result.issues}. "
                    f"Applying revised events."
                )

                # Apply revised content back to original events
                revised_events = result.revised_content
                if len(revised_events) == len(events):
                    # Simple case: same number of events, just update title/description
                    for i, event in enumerate(events):
                        event["title"] = revised_events[i].get("title", event["title"])
                        event["description"] = revised_events[i].get(
                            "description", event["description"]
                        )
                else:
                    logger.warning(
                        f"Supervisor returned different number of events "
                        f"({len(revised_events)} vs {len(events)}), using original"
                    )

            return events

        except Exception as e:
            logger.error(f"Event supervisor validation failed: {e}", exc_info=True)
            # On supervisor failure, return original events
            return events

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics information"""
        return {
            "is_running": self.is_running,
            "aggregation_interval": self.aggregation_interval,
            "time_window_hours": self.time_window_hours,
            "language": self._get_language(),
            "stats": self.stats.copy(),
        }
