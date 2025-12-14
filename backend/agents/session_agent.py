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
from core.json_parser import parse_json_from_response
from core.logger import get_logger
from core.settings import get_settings
from llm.manager import get_llm_manager
from llm.prompt_manager import get_prompt_manager

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
        min_event_duration_seconds: int = 120,  # 2 minutes
        min_event_actions: int = 2,  # Minimum 2 actions per event
        merge_time_gap_tolerance: int = 300,  # 5 minutes tolerance for adjacent activities
        merge_similarity_threshold: float = 0.6,  # Minimum similarity score for merging
    ):
        """
        Initialize SessionAgent

        Args:
            aggregation_interval: How often to run aggregation (seconds, default 30min)
            time_window_min: Minimum time window for session (minutes, default 30min)
            time_window_max: Maximum time window for session (minutes, default 120min)
            min_event_duration_seconds: Minimum event duration for quality filtering (default 120s)
            min_event_actions: Minimum number of actions per event (default 2)
            merge_time_gap_tolerance: Max time gap (seconds) to consider for merging adjacent activities (default 300s/5min)
            merge_similarity_threshold: Minimum semantic similarity score (0-1) required for merging (default 0.6)
        """
        self.aggregation_interval = aggregation_interval
        self.time_window_min = time_window_min
        self.time_window_max = time_window_max
        self.min_event_duration_seconds = min_event_duration_seconds
        self.min_event_actions = min_event_actions
        self.merge_time_gap_tolerance = merge_time_gap_tolerance
        self.merge_similarity_threshold = merge_similarity_threshold

        # Initialize components
        self.db = get_db()
        self.llm_manager = get_llm_manager()
        self.settings = get_settings()

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
            f"quality_filter: min_duration={min_event_duration_seconds}s, min_actions={min_event_actions}, "
            f"merge_config: gap_tolerance={merge_time_gap_tolerance}s, similarity_threshold={merge_similarity_threshold})"
        )

    def _get_language(self) -> str:
        """Get current language setting from config with caching"""
        return self.settings.get_language()

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
        5. Merge with existing activities if applicable
        6. Create Activity records
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

            # Merge with existing activities before saving
            activities_to_save, activities_to_update = await self._merge_with_existing_activities(activities)

            # Update existing activities
            for update_data in activities_to_update:
                await self.db.activities.save(
                    activity_id=update_data["id"],
                    title=update_data["title"],
                    description=update_data["description"],
                    start_time=update_data["start_time"].isoformat() if isinstance(update_data["start_time"], datetime) else update_data["start_time"],
                    end_time=update_data["end_time"].isoformat() if isinstance(update_data["end_time"], datetime) else update_data["end_time"],
                    source_event_ids=update_data["source_event_ids"],
                    session_duration_minutes=update_data.get("session_duration_minutes"),
                    topic_tags=update_data.get("topic_tags", []),
                )

                # Mark new events as aggregated to this existing activity
                new_event_ids = update_data.get("_new_event_ids", [])
                if new_event_ids:
                    await self.db.events.mark_as_aggregated(
                        event_ids=new_event_ids,
                        activity_id=update_data["id"],
                    )
                    self.stats["events_aggregated"] += len(new_event_ids)

                logger.debug(
                    f"Updated existing activity {update_data['id']} with {len(new_event_ids)} new events "
                    f"(merge reason: {update_data.get('_merge_reason', 'unknown')})"
                )

            # Save new activities
            for activity_data in activities_to_save:
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
                await self.db.activities.save(
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
                await self.db.events.mark_as_aggregated(
                    event_ids=source_event_ids,
                    activity_id=activity_id,
                )

                self.stats["activities_created"] += 1
                self.stats["events_aggregated"] += len(source_event_ids)

            self.stats["last_aggregation_time"] = datetime.now()

            logger.debug(
                f"Session aggregation completed: created {len(activities_to_save)} new activities, "
                f"updated {len(activities_to_update)} existing activities, "
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
            events = await self.db.events.get_in_timeframe(
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

            # Get current language and prompt manager
            language = self._get_language()
            prompt_manager = get_prompt_manager(language)

            # Build messages
            messages = prompt_manager.build_messages(
                "session_aggregation", "user_prompt_template", events_json=events_json
            )

            # Get configuration parameters
            config_params = prompt_manager.get_config_params("session_aggregation")

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

            # Validate with supervisor, passing original events for semantic validation
            activities = await self._validate_activities_with_supervisor(
                activities, events
            )

            return activities

        except Exception as e:
            logger.error(f"Failed to cluster events to sessions: {e}", exc_info=True)
            return []

    async def _validate_activities_with_supervisor(
        self,
        activities: List[Dict[str, Any]],
        source_events: Optional[List[Dict[str, Any]]] = None,
        max_iterations: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Validate activities with ActivitySupervisor using multi-round revision

        Args:
            activities: List of activities to validate
            source_events: Optional list of all source events for semantic validation
            max_iterations: Maximum number of validation iterations (default: 3)

        Returns:
            Validated (and possibly revised) list of activities
        """
        if not activities:
            return activities

        try:
            from agents.supervisor import ActivitySupervisor

            language = self._get_language()
            supervisor = ActivitySupervisor(language=language)

            current_activities = activities
            iteration = 0

            while iteration < max_iterations:
                iteration += 1
                logger.debug(f"ActivitySupervisor validation iteration {iteration}/{max_iterations}")

                # Prepare activities for validation (only title and description)
                activities_for_validation = [
                    {
                        "title": activity.get("title", ""),
                        "description": activity.get("description", ""),
                    }
                    for activity in current_activities
                ]

                # Build event mapping for semantic validation
                events_for_validation = None
                if source_events:
                    # Create a mapping of event IDs to events for lookup
                    event_map = {event.get("id"): event for event in source_events if event.get("id")}

                    # For each activity, collect its source events
                    events_for_validation = []
                    for activity in current_activities:
                        source_event_ids = activity.get("source_event_ids", [])
                        activity_events = []
                        for event_id in source_event_ids:
                            if event_id in event_map:
                                activity_events.append(event_map[event_id])

                        # Add all events (we'll pass them all and let supervisor map them)
                        events_for_validation.extend(activity_events)

                    # Remove duplicates while preserving order
                    seen_ids = set()
                    unique_events = []
                    for event in events_for_validation:
                        event_id = event.get("id")
                        if event_id and event_id not in seen_ids:
                            seen_ids.add(event_id)
                            unique_events.append(event)
                    events_for_validation = unique_events

                # Validate with source events
                result = await supervisor.validate(
                    activities_for_validation, source_events=events_for_validation
                )

                # Check if we have revised content
                if not result.revised_content or len(result.revised_content) == 0:
                    # No revisions provided, accept current activities
                    if result.issues or result.suggestions:
                        logger.info(
                            f"ActivitySupervisor iteration {iteration} - No revisions provided. "
                            f"Issues: {result.issues}, Suggestions: {result.suggestions}"
                        )
                    else:
                        logger.info(f"ActivitySupervisor iteration {iteration} - All activities validated successfully")
                    break

                # We have revisions - check if count matches
                revised_activities = result.revised_content
                assert revised_activities is not None  # Type assertion for type checker

                if len(revised_activities) != len(current_activities):
                    # Activity count changed (split/merge)
                    logger.warning(
                        f"ActivitySupervisor iteration {iteration} changed activity count from "
                        f"{len(current_activities)} to {len(revised_activities)}. "
                        f"Keeping original activities (split/merge not yet implemented)."
                    )
                    break

                # Apply revisions - update title and description
                changes_made = False
                for i, activity in enumerate(current_activities):
                    if i < len(revised_activities):
                        old_title = activity["title"]
                        old_desc = activity["description"]
                        new_title = revised_activities[i].get("title", old_title)
                        new_desc = revised_activities[i].get("description", old_desc)

                        if old_title != new_title or old_desc != new_desc:
                            activity["title"] = new_title
                            activity["description"] = new_desc
                            changes_made = True
                            logger.debug(
                                f"ActivitySupervisor iteration {iteration} - Activity {i} revised: "
                                f"title: '{old_title}' → '{new_title}'"
                            )

                if not changes_made:
                    # No actual changes made, stop iterations
                    logger.info(
                        f"ActivitySupervisor iteration {iteration} - No changes made, stopping iterations"
                    )
                    break

                logger.info(
                    f"ActivitySupervisor iteration {iteration} - Applied revisions. "
                    f"Issues: {result.issues}, Suggestions: {result.suggestions}"
                )

                # If supervisor says it's valid now, we can stop
                if result.is_valid:
                    logger.info(
                        f"ActivitySupervisor iteration {iteration} - Activities now valid, stopping iterations"
                    )
                    break

            if iteration >= max_iterations:
                logger.warning(
                    f"ActivitySupervisor reached max iterations ({max_iterations}), using current state"
                )

            return current_activities

        except Exception as e:
            logger.error(f"ActivitySupervisor validation failed: {e}", exc_info=True)
            # Return original activities if validation fails
            return activities

    def _calculate_activity_similarity(
        self, activity1: Dict[str, Any], activity2: Dict[str, Any]
    ) -> float:
        """
        Calculate semantic similarity between two activities

        Uses multiple signals:
        - Title similarity (Jaccard similarity on words)
        - Topic tag overlap (Jaccard similarity on tags)

        Args:
            activity1: First activity dictionary
            activity2: Second activity dictionary

        Returns:
            Similarity score between 0.0 and 1.0
        """
        # Extract titles
        title1 = (activity1.get("title") or "").lower().strip()
        title2 = (activity2.get("title") or "").lower().strip()

        # If either title is empty, low similarity
        if not title1 or not title2:
            return 0.0

        # Exact match on title = very high similarity
        if title1 == title2:
            return 1.0

        # Calculate word-level Jaccard similarity for titles
        words1 = set(title1.split())
        words2 = set(title2.split())

        if not words1 or not words2:
            title_similarity = 0.0
        else:
            intersection = len(words1 & words2)
            union = len(words1 | words2)
            title_similarity = intersection / union if union > 0 else 0.0

        # Calculate topic tag Jaccard similarity
        tags1 = set(activity1.get("topic_tags", []))
        tags2 = set(activity2.get("topic_tags", []))

        if not tags1 or not tags2:
            tag_similarity = 0.0
        else:
            intersection = len(tags1 & tags2)
            union = len(tags1 | tags2)
            tag_similarity = intersection / union if union > 0 else 0.0

        # Weighted combination: title is more important than tags
        # Title weight: 0.7, Tag weight: 0.3
        combined_similarity = (title_similarity * 0.7) + (tag_similarity * 0.3)

        return combined_similarity

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

            # Check for time overlap or proximity
            current_end = current.get("end_time")
            next_start = next_activity.get("start_time")

            should_merge = False
            merge_reason = ""

            if current_end and next_start:
                # Convert to datetime if needed
                if isinstance(current_end, str):
                    current_end = datetime.fromisoformat(current_end)
                if isinstance(next_start, str):
                    next_start = datetime.fromisoformat(next_start)

                # Calculate time gap between activities
                time_gap = (next_start - current_end).total_seconds()

                # Case 1: Direct time overlap (original logic)
                if next_start < current_end:
                    should_merge = True
                    merge_reason = "time_overlap"

                # Case 2: Adjacent or small gap with semantic similarity
                elif 0 <= time_gap <= self.merge_time_gap_tolerance:
                    # Calculate semantic similarity
                    similarity = self._calculate_activity_similarity(current, next_activity)

                    if similarity >= self.merge_similarity_threshold:
                        should_merge = True
                        merge_reason = f"proximity_similarity (gap: {time_gap:.0f}s, similarity: {similarity:.2f})"

                # Perform merge if criteria met
                if should_merge:
                    logger.debug(
                        f"Merging activities (reason: {merge_reason}): '{current.get('title')}' and '{next_activity.get('title')}'"
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

                    # Merge titles and descriptions based on duration
                    # Calculate durations to determine primary activity
                    current_start = current.get("start_time")
                    if isinstance(current_start, str):
                        current_start = datetime.fromisoformat(current_start)
                    next_start_dt = next_activity.get("start_time")
                    if isinstance(next_start_dt, str):
                        next_start_dt = datetime.fromisoformat(next_start_dt)

                    current_duration = (current_end - current_start).total_seconds() if current_start and current_end else 0
                    next_duration = (next_end - next_start_dt).total_seconds() if next_start_dt and next_end else 0

                    current_title = current.get("title", "")
                    next_title = next_activity.get("title", "")
                    current_desc = current.get("description", "")
                    next_desc = next_activity.get("description", "")

                    # Select title from the longer-duration activity (primary activity)
                    if next_title and next_title != current_title:
                        if next_duration > current_duration:
                            # Next activity is primary, use its title
                            logger.debug(
                                f"Selected '{next_title}' as primary (duration: {next_duration:.0f}s > {current_duration:.0f}s)"
                            )
                            current["title"] = next_title
                            # Add current as secondary context in description if needed
                            if current_desc and current_title:
                                current["description"] = f"{next_desc}\n\n[Related: {current_title}]\n{current_desc}" if next_desc else current_desc
                            elif next_desc:
                                current["description"] = next_desc
                        else:
                            # Current activity is primary, keep its title
                            logger.debug(
                                f"Kept '{current_title}' as primary (duration: {current_duration:.0f}s >= {next_duration:.0f}s)"
                            )
                            # Keep current title, add next as secondary context
                            if next_desc and next_title:
                                if current_desc:
                                    current["description"] = f"{current_desc}\n\n[Related: {next_title}]\n{next_desc}"
                                else:
                                    current["description"] = next_desc
                            # If only next has description, use it
                            elif next_desc and not current_desc:
                                current["description"] = next_desc
                    else:
                        # Same title or one is empty, just merge descriptions
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

    async def _get_recent_activities_for_merge(
        self, lookback_hours: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Get recent activities from database for merge checking

        Args:
            lookback_hours: How many hours to look back (default: 2 hours)

        Returns:
            List of recent activity dictionaries
        """
        try:
            # Query activities from the last N hours
            start_time = datetime.now() - timedelta(hours=lookback_hours)
            end_time = datetime.now()

            activities = await self.db.activities.get_by_date(
                start_time.strftime("%Y-%m-%d"),
                end_time.strftime("%Y-%m-%d"),
            )

            # Filter to only include activities within the time window
            # (get_by_date uses date, we need more precise filtering)
            filtered_activities = []
            for activity in activities:
                activity_start = activity.get("start_time")
                if isinstance(activity_start, str):
                    activity_start = datetime.fromisoformat(activity_start)

                if activity_start and activity_start >= start_time:
                    filtered_activities.append(activity)

            logger.debug(
                f"Found {len(filtered_activities)} recent activities in the last {lookback_hours} hours"
            )

            return filtered_activities

        except Exception as e:
            logger.error(f"Failed to get recent activities for merge: {e}", exc_info=True)
            return []

    async def _merge_with_existing_activities(
        self, new_activities: List[Dict[str, Any]]
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Check if new activities should be merged with existing activities

        Args:
            new_activities: List of newly created activity dictionaries

        Returns:
            Tuple of (activities_to_save, activities_to_update)
            - activities_to_save: New activities that don't merge with existing ones
            - activities_to_update: Existing activities that should be updated with new events
        """
        if not new_activities:
            return [], []

        try:
            # Get recent activities from database
            existing_activities = await self._get_recent_activities_for_merge(lookback_hours=2)

            if not existing_activities:
                # No existing activities to merge with
                return new_activities, []

            # Sort existing activities by end_time for efficient checking
            def get_sort_key(activity: Dict[str, Any]) -> datetime:
                end_time = activity.get("end_time")
                if isinstance(end_time, str):
                    try:
                        return datetime.fromisoformat(end_time)
                    except (ValueError, TypeError):
                        return datetime.min
                elif isinstance(end_time, datetime):
                    return end_time
                return datetime.min

            existing_activities_sorted = sorted(existing_activities, key=get_sort_key)

            activities_to_save = []
            activities_to_update = []
            merged_new_activity_ids = set()

            # For each new activity, check if it should merge with any existing activity
            for new_activity in new_activities:
                merged = False

                new_start = new_activity.get("start_time")
                if isinstance(new_start, str):
                    new_start = datetime.fromisoformat(new_start)

                # Check against each existing activity
                for existing_activity in existing_activities_sorted:
                    existing_end = existing_activity.get("end_time")
                    if isinstance(existing_end, str):
                        existing_end = datetime.fromisoformat(existing_end)

                    existing_start = existing_activity.get("start_time")
                    if isinstance(existing_start, str):
                        existing_start = datetime.fromisoformat(existing_start)

                    if not existing_end or not new_start or not existing_start:
                        continue

                    # Calculate time gap
                    time_gap = (new_start - existing_end).total_seconds()

                    # Check merge conditions
                    should_merge = False
                    merge_reason = ""

                    # Case 1: Time overlap
                    new_end = new_activity.get("end_time")
                    if isinstance(new_end, str):
                        new_end = datetime.fromisoformat(new_end)

                    if new_end and new_start < existing_end:
                        should_merge = True
                        merge_reason = "time_overlap"

                    # Case 2: Adjacent or small gap with semantic similarity
                    elif 0 <= time_gap <= self.merge_time_gap_tolerance:
                        similarity = self._calculate_activity_similarity(
                            existing_activity, new_activity
                        )

                        if similarity >= self.merge_similarity_threshold:
                            should_merge = True
                            merge_reason = f"proximity_similarity (gap: {time_gap:.0f}s, similarity: {similarity:.2f})"

                    if should_merge:
                        # Merge new activity into existing activity
                        logger.debug(
                            f"Merging new activity '{new_activity.get('title')}' into existing "
                            f"activity '{existing_activity.get('title')}' (reason: {merge_reason})"
                        )

                        # Merge source_event_ids
                        existing_events = set(existing_activity.get("source_event_ids", []))
                        new_events = set(new_activity.get("source_event_ids", []))
                        all_events = list(existing_events | new_events)
                        new_event_ids_only = list(new_events - existing_events)

                        # Update time range
                        merged_start = min(existing_start, new_start)
                        merged_end = max(existing_end, new_end) if new_end else existing_end

                        # Calculate new duration
                        duration_minutes = int((merged_end - merged_start).total_seconds() / 60)

                        # Merge topic tags
                        existing_tags = set(existing_activity.get("topic_tags", []))
                        new_tags = set(new_activity.get("topic_tags", []))
                        merged_tags = list(existing_tags | new_tags)

                        # Determine primary title/description based on duration
                        existing_duration = (existing_end - existing_start).total_seconds()
                        new_duration = (new_end - new_start).total_seconds() if new_end else 0

                        if new_duration > existing_duration:
                            # New activity is primary
                            title = new_activity.get("title", existing_activity.get("title", ""))
                            description = new_activity.get("description", "")
                            if description and existing_activity.get("description"):
                                description = f"{description}\n\n[Related: {existing_activity.get('title')}]\n{existing_activity.get('description')}"
                            elif existing_activity.get("description"):
                                description = existing_activity.get("description")
                        else:
                            # Existing activity is primary
                            title = existing_activity.get("title", "")
                            description = existing_activity.get("description", "")
                            if new_activity.get("description") and new_activity.get("title"):
                                if description:
                                    description = f"{description}\n\n[Related: {new_activity.get('title')}]\n{new_activity.get('description')}"
                                else:
                                    description = new_activity.get("description", "")

                        # Create update record
                        update_record = {
                            "id": existing_activity["id"],
                            "title": title,
                            "description": description,
                            "start_time": merged_start,
                            "end_time": merged_end,
                            "source_event_ids": all_events,
                            "session_duration_minutes": duration_minutes,
                            "topic_tags": merged_tags,
                            "_new_event_ids": new_event_ids_only,
                            "_merge_reason": merge_reason,
                        }

                        # Check if this existing activity was already updated in this batch
                        existing_update = None
                        for idx, update in enumerate(activities_to_update):
                            if update["id"] == existing_activity["id"]:
                                existing_update = idx
                                break

                        if existing_update is not None:
                            # Merge with previous update
                            prev_update = activities_to_update[existing_update]
                            prev_events = set(prev_update["source_event_ids"])
                            combined_events = list(prev_events | set(all_events))
                            prev_new_events = set(prev_update.get("_new_event_ids", []))
                            combined_new_events = list(prev_new_events | set(new_event_ids_only))

                            prev_update["source_event_ids"] = combined_events
                            prev_update["_new_event_ids"] = combined_new_events
                            prev_update["end_time"] = max(prev_update["end_time"], merged_end)
                            prev_update["session_duration_minutes"] = int(
                                (prev_update["end_time"] - prev_update["start_time"]).total_seconds() / 60
                            )
                        else:
                            activities_to_update.append(update_record)

                        merged_new_activity_ids.add(new_activity["id"])
                        merged = True
                        break

                if not merged:
                    # No merge happened, this is a new activity to save
                    activities_to_save.append(new_activity)

            logger.debug(
                f"Merge check completed: {len(activities_to_save)} new activities to save, "
                f"{len(activities_to_update)} existing activities to update, "
                f"{len(merged_new_activity_ids)} new activities merged"
            )

            return activities_to_save, activities_to_update

        except Exception as e:
            logger.error(f"Failed to merge with existing activities: {e}", exc_info=True)
            # On error, return all as new activities
            return new_activities, []

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
            "language": self._get_language(),
            "stats": self.stats.copy(),
        }
