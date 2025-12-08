"""
SessionAgent - Intelligent long-running agent for session aggregation
Aggregates Events (medium-grained work segments) into Activities (coarse-grained work sessions)
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set

from core.db import get_db
from core.logger import get_logger
from llm.manager import get_llm_manager
from llm.prompt_manager import get_prompt_manager
from core.json_parser import parse_json_from_response

logger = get_logger(__name__)


class SessionAgent:
    """
    Intelligent session aggregation agent

    Aggregates Events into Activities based on:
    - Thematic relevance (core): Same work topic/project/problem domain
    - Time continuity (strong signal): Events within 30min tend to merge
    - Goal association (strong signal): Different objects serving same high-level goal
    - Project consistency (auxiliary): Same project/repo/branch
    - Workflow continuity (auxiliary): Events forming a workflow
    """

    def __init__(
        self,
        aggregation_interval: int = 1800,  # 30 minutes
        time_window_min: int = 30,  # minutes
        time_window_max: int = 120,  # minutes
        language: str = "zh",
        min_event_duration_seconds: int = 120,  # 2 minutes
        min_event_actions: int = 2,  # Minimum 2 actions per event
    ):
        """
        Initialize SessionAgent

        Args:
            aggregation_interval: How often to run aggregation (seconds, default 30min)
            time_window_min: Minimum time window for session (minutes, default 30min)
            time_window_max: Maximum time window for session (minutes, default 120min)
            language: Language setting (zh|en)
            min_event_duration_seconds: Minimum event duration for quality filtering (default 120s)
            min_event_actions: Minimum number of actions per event (default 2)
        """
        self.aggregation_interval = aggregation_interval
        self.time_window_min = time_window_min
        self.time_window_max = time_window_max
        self.language = language
        self.min_event_duration_seconds = min_event_duration_seconds
        self.min_event_actions = min_event_actions

        # Initialize components
        self.db = get_db()
        self.llm_manager = get_llm_manager()
        self.prompt_manager = get_prompt_manager(language)

        # Running state
        self.is_running = False
        self.aggregation_task: Optional[asyncio.Task] = None

        # Statistics
        self.stats: Dict[str, Any] = {
            "activities_created": 0,
            "events_aggregated": 0,
            "events_filtered_quality": 0,  # Events filtered due to quality criteria
            "last_aggregation_time": None,
        }

        logger.debug(
            f"SessionAgent initialized (interval: {aggregation_interval}s, "
            f"time_window: {time_window_min}-{time_window_max}min, "
            f"quality_filter: min_duration={min_event_duration_seconds}s, min_actions={min_event_actions})"
        )

    async def start(self):
        """Start the session agent"""
        if self.is_running:
            logger.warning("SessionAgent is already running")
            return

        self.is_running = True

        # Start aggregation task
        self.aggregation_task = asyncio.create_task(
            self._periodic_session_aggregation()
        )

        logger.info(
            f"SessionAgent started (aggregation interval: {self.aggregation_interval}s)"
        )

    async def stop(self):
        """Stop the session agent"""
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

        logger.info("SessionAgent stopped")

    async def _periodic_session_aggregation(self):
        """Scheduled task: aggregate sessions every N minutes"""
        while self.is_running:
            try:
                await asyncio.sleep(self.aggregation_interval)
                await self._aggregate_sessions()
            except asyncio.CancelledError:
                logger.debug("Session aggregation task cancelled")
                break
            except Exception as e:
                logger.error(f"Session aggregation task exception: {e}", exc_info=True)

    async def _aggregate_sessions(self):
        """
        Main aggregation logic:
        1. Get unaggregated Events
        2. Call LLM to cluster into sessions
        3. Apply learned merge patterns
        4. Check split candidates
        5. Create Activity records
        """
        try:
            # Get unaggregated events
            unaggregated_events = await self._get_unaggregated_events()

            if not unaggregated_events or len(unaggregated_events) == 0:
                logger.debug("No events to aggregate into sessions")
                return

            logger.debug(
                f"Starting to aggregate {len(unaggregated_events)} events into activities (sessions)"
            )

            # Call LLM to cluster events into sessions
            activities = await self._cluster_events_to_sessions(unaggregated_events)

            if not activities:
                logger.debug("No activities generated from event clustering")
                return

            # Save activities and mark events as aggregated
            for activity_data in activities:
                activity_id = activity_data["id"]
                source_event_ids = activity_data.get("source_event_ids", [])

                if not source_event_ids:
                    logger.warning(f"Activity {activity_id} has no source events, skipping")
                    continue

                # Calculate session duration
                start_time = activity_data.get("start_time")
                end_time = activity_data.get("end_time")
                session_duration_minutes = None

                if start_time and end_time:
                    if isinstance(start_time, str):
                        start_time = datetime.fromisoformat(start_time)
                    if isinstance(end_time, str):
                        end_time = datetime.fromisoformat(end_time)

                    duration = end_time - start_time
                    session_duration_minutes = int(duration.total_seconds() / 60)

                # Save activity
                await self.db.activities_v2.save(
                    activity_id=activity_id,
                    title=activity_data.get("title", ""),
                    description=activity_data.get("description", ""),
                    start_time=activity_data["start_time"].isoformat() if isinstance(activity_data["start_time"], datetime) else activity_data["start_time"],
                    end_time=activity_data["end_time"].isoformat() if isinstance(activity_data["end_time"], datetime) else activity_data["end_time"],
                    source_event_ids=source_event_ids,
                    session_duration_minutes=session_duration_minutes,
                    topic_tags=activity_data.get("topic_tags", []),
                )

                # Mark events as aggregated
                await self.db.events_v2.mark_as_aggregated(
                    event_ids=source_event_ids,
                    activity_id=activity_id,
                )

                self.stats["activities_created"] += 1
                self.stats["events_aggregated"] += len(source_event_ids)

            self.stats["last_aggregation_time"] = datetime.now()

            logger.debug(
                f"Session aggregation completed: created {len(activities)} activities "
                f"from {self.stats['events_aggregated']} events"
            )

        except Exception as e:
            logger.error(f"Failed to aggregate sessions: {e}", exc_info=True)

    async def _get_unaggregated_events(
        self, since: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch events not yet aggregated into activities

        Args:
            since: Starting time to fetch events from

        Returns:
            List of event dictionaries
        """
        try:
            # Default: fetch events from last 2 hours
            start_time = since or datetime.now() - timedelta(hours=2)
            end_time = datetime.now()

            # Get events in timeframe
            events = await self.db.events_v2.get_in_timeframe(
                start_time.isoformat(), end_time.isoformat()
            )

            # Filter out already aggregated events and apply quality filters
            result: List[Dict[str, Any]] = []
            filtered_count = 0
            quality_filtered_count = 0

            for event in events:
                # Skip already aggregated events (using aggregated_into_activity_id field)
                if event.get("aggregated_into_activity_id"):
                    filtered_count += 1
                    continue

                # Quality filter 1: Check minimum number of actions
                source_action_ids = event.get("source_action_ids", [])
                if len(source_action_ids) < self.min_event_actions:
                    quality_filtered_count += 1
                    logger.debug(
                        f"Filtering out event {event.get('id')} - insufficient actions "
                        f"({len(source_action_ids)} < {self.min_event_actions})"
                    )
                    continue

                # Quality filter 2: Check minimum duration
                start_time_str = event.get("start_time")
                end_time_str = event.get("end_time")

                if start_time_str and end_time_str:
                    try:
                        event_start = datetime.fromisoformat(start_time_str) if isinstance(start_time_str, str) else start_time_str
                        event_end = datetime.fromisoformat(end_time_str) if isinstance(end_time_str, str) else end_time_str
                        duration_seconds = (event_end - event_start).total_seconds()

                        if duration_seconds < self.min_event_duration_seconds:
                            quality_filtered_count += 1
                            logger.debug(
                                f"Filtering out event {event.get('id')} - too short "
                                f"({duration_seconds:.1f}s < {self.min_event_duration_seconds}s)"
                            )
                            continue
                    except Exception as parse_error:
                        logger.warning(f"Failed to parse event timestamps: {parse_error}")
                        # If we can't parse timestamps, allow the event through
                        pass

                result.append(event)

            # Update statistics
            self.stats["events_filtered_quality"] += quality_filtered_count

            logger.debug(
                f"Event filtering: {len(events)} total, {filtered_count} already aggregated, "
                f"{quality_filtered_count} quality-filtered, {len(result)} remaining"
            )

            return result

        except Exception as exc:
            logger.error("Failed to get unaggregated events: %s", exc, exc_info=True)
            return []

    async def _cluster_events_to_sessions(
        self, events: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Use LLM to cluster events into session-level activities

        Args:
            events: List of event dictionaries

        Returns:
            List of activity dictionaries
        """
        if not events:
            return []

        try:
            logger.debug(f"Clustering {len(events)} events into sessions")

            # Build events JSON with index
            events_with_index = [
                {
                    "index": i + 1,
                    "title": event.get("title", ""),
                    "description": event.get("description", ""),
                    "start_time": event.get("start_time", ""),
                    "end_time": event.get("end_time", ""),
                }
                for i, event in enumerate(events)
            ]
            events_json = json.dumps(events_with_index, ensure_ascii=False, indent=2)

            # Build messages
            messages = self.prompt_manager.build_messages(
                "session_aggregation", "user_prompt_template", events_json=events_json
            )

            # Get configuration parameters
            config_params = self.prompt_manager.get_config_params("session_aggregation")

            # Call LLM
            response = await self.llm_manager.chat_completion(messages, **config_params)
            content = response.get("content", "").strip()

            # Parse JSON
            result = parse_json_from_response(content)

            if not isinstance(result, dict):
                logger.warning(f"Session clustering result format error: {content[:200]}")
                return []

            activities_data = result.get("activities", [])

            # Convert to complete activity objects
            activities = []
            for activity_data in activities_data:
                # Normalize source indexes
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
                    st = e.get("start_time")
                    et = e.get("end_time")

                    if st:
                        if isinstance(st, str):
                            st = datetime.fromisoformat(st)
                        if start_time is None or st < start_time:
                            start_time = st

                    if et:
                        if isinstance(et, str):
                            et = datetime.fromisoformat(et)
                        if end_time is None or et > end_time:
                            end_time = et

                if not start_time:
                    start_time = datetime.now()
                if not end_time:
                    end_time = start_time

                # Extract topic tags from LLM response if provided
                topic_tags = activity_data.get("topic_tags", [])
                if not topic_tags:
                    # Fallback: extract from title
                    topic_tags = []

                activity = {
                    "id": str(uuid.uuid4()),
                    "title": activity_data.get("title", "Unnamed session"),
                    "description": activity_data.get("description", ""),
                    "start_time": start_time,
                    "end_time": end_time,
                    "source_event_ids": source_event_ids,
                    "topic_tags": topic_tags,
                    "created_at": datetime.now(),
                }

                activities.append(activity)

            logger.debug(
                f"Clustering completed: generated {len(activities)} activities (before overlap detection)"
            )

            # Post-process: detect and merge overlapping activities
            activities = self._merge_overlapping_activities(activities)

            logger.debug(
                f"After overlap merging: {len(activities)} activities"
            )
            return activities

        except Exception as e:
            logger.error(f"Failed to cluster events to sessions: {e}", exc_info=True)
            return []

    def _merge_overlapping_activities(
        self, activities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Detect and merge overlapping activities to prevent duplicate time consumption

        Args:
            activities: List of activity dictionaries

        Returns:
            List of activities with overlaps merged
        """
        if len(activities) <= 1:
            return activities

        # Sort by start_time
        sorted_activities = sorted(
            activities,
            key=lambda a: a.get("start_time") or datetime.min
        )

        merged: List[Dict[str, Any]] = []
        current = sorted_activities[0].copy()

        for i in range(1, len(sorted_activities)):
            next_activity = sorted_activities[i]

            # Check for time overlap
            current_end = current.get("end_time")
            next_start = next_activity.get("start_time")

            if current_end and next_start:
                # Convert to datetime if needed
                if isinstance(current_end, str):
                    current_end = datetime.fromisoformat(current_end)
                if isinstance(next_start, str):
                    next_start = datetime.fromisoformat(next_start)

                # If overlapping, merge them
                if next_start < current_end:
                    logger.debug(
                        f"Detected overlapping activities: '{current.get('title')}' and '{next_activity.get('title')}'"
                    )

                    # Merge source_event_ids (remove duplicates)
                    current_events = set(current.get("source_event_ids", []))
                    next_events = set(next_activity.get("source_event_ids", []))
                    merged_events = list(current_events | next_events)

                    # Update end_time to the latest
                    next_end = next_activity.get("end_time")
                    if isinstance(next_end, str):
                        next_end = datetime.fromisoformat(next_end)
                    if next_end and next_end > current_end:
                        current["end_time"] = next_end

                    # Merge topic_tags
                    current_tags = set(current.get("topic_tags", []))
                    next_tags = set(next_activity.get("topic_tags", []))
                    merged_tags = list(current_tags | next_tags)

                    # Update current with merged data
                    current["source_event_ids"] = merged_events
                    current["topic_tags"] = merged_tags

                    # Merge titles and descriptions
                    current_title = current.get("title", "")
                    next_title = next_activity.get("title", "")
                    if next_title and next_title != current_title:
                        current["title"] = f"{current_title}; {next_title}"

                    current_desc = current.get("description", "")
                    next_desc = next_activity.get("description", "")
                    if next_desc and next_desc != current_desc:
                        if current_desc:
                            current["description"] = f"{current_desc}\n\n{next_desc}"
                        else:
                            current["description"] = next_desc

                    logger.debug(
                        f"Merged into: '{current.get('title')}' with {len(merged_events)} events"
                    )
                    continue

            # No overlap, save current and move to next
            merged.append(current)
            current = next_activity.copy()

        # Don't forget the last activity
        merged.append(current)

        return merged

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

    async def record_user_merge(
        self,
        merged_activity_id: str,
        original_activity_ids: List[str],
        original_activities: List[Dict[str, Any]],
    ) -> None:
        """
        Record user manual merge operation and learn from it

        Args:
            merged_activity_id: ID of the newly created merged activity
            original_activity_ids: IDs of the original activities that were merged
            original_activities: Full data of original activities
        """
        try:
            logger.debug(
                f"Recording user merge: {len(original_activity_ids)} activities -> {merged_activity_id}"
            )

            # Analyze merge pattern using LLM
            pattern = await self._analyze_merge_pattern(
                merged_activity_id, original_activities
            )

            if pattern:
                # Save learned pattern to database
                pattern_id = str(uuid.uuid4())
                await self.db.session_preferences.save_pattern(
                    pattern_id=pattern_id,
                    preference_type="merge_pattern",
                    pattern_description=pattern,
                    confidence_score=0.6,  # Initial confidence
                    times_observed=1,
                    last_observed=datetime.now().isoformat(),
                )

                logger.info(f"Learned new merge pattern: {pattern}")

        except Exception as e:
            logger.error(f"Failed to record user merge: {e}", exc_info=True)

    async def record_user_split(
        self,
        original_activity_id: str,
        new_activity_ids: List[str],
        original_activity: Dict[str, Any],
        source_events: List[Dict[str, Any]],
    ) -> None:
        """
        Record user manual split operation and learn from it

        Args:
            original_activity_id: ID of the original activity that was split
            new_activity_ids: IDs of the new activities created from split
            original_activity: Full data of original activity
            source_events: Source events of the original activity
        """
        try:
            logger.debug(
                f"Recording user split: {original_activity_id} -> {len(new_activity_ids)} activities"
            )

            # Analyze split pattern using LLM
            pattern = await self._analyze_split_pattern(
                original_activity, new_activity_ids, source_events
            )

            if pattern:
                # Save learned pattern to database
                pattern_id = str(uuid.uuid4())
                await self.db.session_preferences.save_pattern(
                    pattern_id=pattern_id,
                    preference_type="split_pattern",
                    pattern_description=pattern,
                    confidence_score=0.6,  # Initial confidence
                    times_observed=1,
                    last_observed=datetime.now().isoformat(),
                )

                logger.info(f"Learned new split pattern: {pattern}")

        except Exception as e:
            logger.error(f"Failed to record user split: {e}", exc_info=True)

    async def _analyze_merge_pattern(
        self, merged_activity_id: str, original_activities: List[Dict[str, Any]]
    ) -> Optional[str]:
        """
        Analyze why user merged these activities to extract pattern

        Args:
            merged_activity_id: ID of merged activity
            original_activities: Original activities that were merged

        Returns:
            Pattern description or None
        """
        try:
            # Build analysis prompt
            activities_summary = []
            for activity in original_activities:
                activities_summary.append(
                    {
                        "title": activity.get("title", ""),
                        "description": activity.get("description", ""),
                        "start_time": activity.get("start_time", ""),
                        "end_time": activity.get("end_time", ""),
                    }
                )

            import json

            activities_json = json.dumps(activities_summary, ensure_ascii=False, indent=2)

            # Simple prompt for pattern extraction
            messages = [
                {
                    "role": "system",
                    "content": "You are an expert at analyzing user behavior patterns. Analyze why the user merged these activities and extract a reusable pattern description (max 100 words).",
                },
                {
                    "role": "user",
                    "content": f"User merged these activities:\n{activities_json}\n\nWhat pattern or rule can we learn from this merge? Describe in one concise sentence.",
                },
            ]

            # Call LLM
            response = await self.llm_manager.chat_completion(
                messages, max_tokens=200, temperature=0.3
            )

            pattern = response.get("content", "").strip()
            return pattern if pattern else None

        except Exception as e:
            logger.error(f"Failed to analyze merge pattern: {e}", exc_info=True)
            return None

    async def _analyze_split_pattern(
        self,
        original_activity: Dict[str, Any],
        new_activity_ids: List[str],
        source_events: List[Dict[str, Any]],
    ) -> Optional[str]:
        """
        Analyze why user split this activity to extract pattern

        Args:
            original_activity: Original activity that was split
            new_activity_ids: IDs of new activities
            source_events: Source events of the activity

        Returns:
            Pattern description or None
        """
        try:
            # Build analysis prompt
            activity_summary = {
                "title": original_activity.get("title", ""),
                "description": original_activity.get("description", ""),
                "duration_minutes": original_activity.get("session_duration_minutes", 0),
                "num_events": len(source_events),
            }

            import json

            activity_json = json.dumps(activity_summary, ensure_ascii=False, indent=2)

            # Simple prompt for pattern extraction
            messages = [
                {
                    "role": "system",
                    "content": "You are an expert at analyzing user behavior patterns. Analyze why the user split this activity and extract a reusable pattern description (max 100 words).",
                },
                {
                    "role": "user",
                    "content": f"User split this activity into {len(new_activity_ids)} separate activities:\n{activity_json}\n\nWhat pattern or rule can we learn from this split? Describe in one concise sentence.",
                },
            ]

            # Call LLM
            response = await self.llm_manager.chat_completion(
                messages, max_tokens=200, temperature=0.3
            )

            pattern = response.get("content", "").strip()
            return pattern if pattern else None

        except Exception as e:
            logger.error(f"Failed to analyze split pattern: {e}", exc_info=True)
            return None

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics information"""
        return {
            "is_running": self.is_running,
            "aggregation_interval": self.aggregation_interval,
            "time_window_min": self.time_window_min,
            "time_window_max": self.time_window_max,
            "stats": self.stats.copy(),
        }
