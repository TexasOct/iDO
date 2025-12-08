"""
Activity management handlers.

Handles all activity-related operations including:
- CRUD operations for activities
- Three-layer drill-down (activities -> events -> actions)
- Activity merging and splitting
- Batch operations
"""

import json
import uuid
from datetime import datetime
from typing import Any, List, Tuple

from core.coordinator import get_coordinator
from core.db import DatabaseManager, get_db
from core.events import emit_activity_deleted, emit_activity_merged, emit_activity_split
from core.logger import get_logger
from models import (
    ActivityCountResponse,
    DataResponse,
    DeleteActivitiesByDateRequest,
    DeleteActivityRequest,
    GetActivitiesIncrementalRequest,
    GetActivitiesRequest,
    GetActivityByIdRequest,
    GetActivityCountByDateRequest,
    IncrementalActivitiesResponse,
    TimedOperationResponse,
)
from models.requests import (
    GetEventsByActivityRequest,
    MergeActivitiesRequest,
    SplitActivityRequest,
)
from models.responses import (
    ActivityCountData,
    EventResponse,
    GetEventsByActivityResponse,
    IncrementalActivitiesData,
    MergeActivitiesResponse,
    SplitActivityResponse,
)

from . import api_handler

logger = get_logger(__name__)


# Helper functions

def _get_pipeline():
    """Get processing pipeline from coordinator"""
    coordinator = get_coordinator()
    return coordinator.processing_pipeline, coordinator


def _get_data_access() -> Tuple[DatabaseManager, Any, Any, Any]:
    """Get database and related data access objects"""
    pipeline, coordinator = _get_pipeline()

    db = getattr(pipeline, "db", None) if pipeline else None
    if db is None:
        db = get_db()

    image_manager = getattr(pipeline, "image_manager", None) if pipeline else None

    return db, image_manager, pipeline, coordinator


async def _get_event_screenshot_hashes(
    db: DatabaseManager, event_id: str
) -> List[str]:
    """Get screenshot hashes for an event"""
    try:
        return await db.events.get_screenshots(event_id)
    except Exception as exc:
        logger.error("Failed to load screenshot hashes for event %s: %s", event_id, exc)
        return []


# API handlers

@api_handler(body=GetActivitiesRequest)
async def get_activities(body: GetActivitiesRequest) -> DataResponse:
    """Get processed activities with optional date filtering.

    @param body - Request parameters including limit, offset, start, end.
    @returns Activities data with success flag and timestamp
    """
    db, _, _, _ = _get_data_access()
    activities = await db.activities_v2.get_recent(
        body.limit, body.offset, body.start, body.end
    )

    activities_data = []
    for activity in activities:
        start_time = activity.get("start_time")
        end_time = activity.get("end_time")

        if isinstance(start_time, str):
            try:
                start_time_dt = datetime.fromisoformat(start_time)
            except ValueError:
                start_time_dt = datetime.now()
        elif isinstance(start_time, datetime):
            start_time_dt = start_time
        else:
            start_time_dt = datetime.now()

        if isinstance(end_time, str):
            try:
                end_time_dt = datetime.fromisoformat(end_time)
            except ValueError:
                end_time_dt = start_time_dt
        elif isinstance(end_time, datetime):
            end_time_dt = end_time
        else:
            end_time_dt = start_time_dt

        created_at = activity.get("created_at")
        if isinstance(created_at, str):
            created_at_str = created_at
        else:
            created_at_str = datetime.now().isoformat()

        activities_data.append(
            {
                "id": activity.get("id"),
                "title": activity.get("title", ""),
                "description": activity.get("description", ""),
                "startTime": start_time_dt.isoformat(),
                "endTime": end_time_dt.isoformat(),
                "eventCount": len(activity.get("source_event_ids", [])),
                "createdAt": created_at_str,
                "sourceEventIds": activity.get("source_event_ids", []),
            }
        )

    return DataResponse(
        success=True,
        data={
            "activities": activities_data,
            "count": len(activities_data),
            "filters": {
                "limit": body.limit,
                "offset": body.offset,
            },
        },
        timestamp=datetime.now().isoformat(),
    )


@api_handler(body=GetActivityByIdRequest)
async def get_activity_by_id(body: GetActivityByIdRequest) -> DataResponse:
    """Get activity details by ID with full event summaries and records.

    @param body - Request parameters including activity ID.
    @returns Activity details with success flag and timestamp
    """
    db, _, _, _ = _get_data_access()
    activity = await db.activities_v2.get_by_id(body.activity_id)

    if not activity:
        return DataResponse(success=False, error="Activity not found", timestamp=datetime.now().isoformat())

    start_time = activity.get("start_time")
    end_time = activity.get("end_time")

    def _parse_dt(value):
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value).isoformat()
            except ValueError:
                return datetime.now().isoformat()
        return datetime.now().isoformat()

    # Get event details with screenshot hashes
    source_event_ids = activity.get("source_event_ids", [])
    event_summaries = []

    if source_event_ids:
        events = await db.events.get_by_ids(source_event_ids)

        for event in events:
            # Get screenshot hashes for this event
            screenshot_hashes = await _get_event_screenshot_hashes(
                db, event["id"]
            )

            # Build records from screenshot hashes (simulate raw records)
            records = []
            for img_hash in screenshot_hashes:
                records.append(
                    {
                        "id": img_hash,  # Use hash as record ID
                        "timestamp": event.get("timestamp", datetime.now().isoformat()),
                        "content": "Screenshot captured",
                        "metadata": {
                            "action": "capture",
                            "hash": img_hash,
                            "screenshotPath": "",  # Empty path, will use hash fallback
                        },
                    }
                )

            event_summary = {
                "id": event["id"],
                "title": event.get("title", ""),
                "timestamp": event.get("timestamp", datetime.now().isoformat()),
                "events": [
                    {
                        "id": f"{event['id']}-detail",
                        "startTime": event.get("timestamp", datetime.now().isoformat()),
                        "endTime": event.get("timestamp", datetime.now().isoformat()),
                        "records": records,
                    }
                ],
            }
            event_summaries.append(event_summary)

    activity_detail = {
        "id": activity.get("id"),
        "title": activity.get("title", ""),
        "description": activity.get("description", ""),
        "startTime": _parse_dt(start_time),
        "endTime": _parse_dt(end_time),
        "sourceEventIds": source_event_ids,
        "eventSummaries": event_summaries,
        "createdAt": activity.get("created_at"),
    }

    return DataResponse(success=True, data=activity_detail, timestamp=datetime.now().isoformat())


@api_handler(body=GetActivitiesIncrementalRequest)
async def get_activities_incremental(
    body: GetActivitiesIncrementalRequest,
) -> IncrementalActivitiesResponse:
    """Get incremental activity updates based on version negotiation.

    This handler implements version-based incremental updates. The client provides
    its current version number, and the server returns only activities created or
    updated after that version.

    @param body - Request parameters including client version and limit.
    @returns New activities data with success flag, max version, and timestamp
    """
    # New architecture does not yet support versioned incremental updates, return empty result for compatibility
    return IncrementalActivitiesResponse(
        success=True,
        data=IncrementalActivitiesData(
            activities=[],
            count=0,
            max_version=body.version,
        ),
    )


@api_handler(body=GetActivityCountByDateRequest)
async def get_activity_count_by_date(
    body: GetActivityCountByDateRequest,
) -> ActivityCountResponse:
    """Get activity count for each date (total count, not paginated).

    Returns the total number of activities for each date in the database.

    @param body - Request parameters (empty).
    @returns Activity count statistics by date
    """
    try:
        db, _, _, _ = _get_data_access()

        # Query database for activity count by date
        counts = await db.activities_v2.get_count_by_date()

        # Convert to map format: {"2025-01-15": 10, "2025-01-14": 5, ...}
        date_count_map = {date: count for date, count in counts.items()}
        total_dates = len(date_count_map)
        total_activities = sum(date_count_map.values())

        logger.debug(
            f"Activity count by date: {total_dates} dates, {total_activities} total activities"
        )

        return ActivityCountResponse(
            success=True,
            data=ActivityCountData(
                date_count_map=date_count_map,
                total_dates=total_dates,
                total_activities=total_activities,
            ),
        )
    except Exception as e:
        logger.error(f"Failed to get activity count by date: {e}", exc_info=True)
        return ActivityCountResponse(
            success=False,
            data=ActivityCountData(
                date_count_map={},
                total_dates=0,
                total_activities=0,
            ),
        )


# Three-layer drill-down: get events by activity

@api_handler(
    body=GetEventsByActivityRequest,
    method="POST",
    path="/three-layer/get-events-by-activity",
    tags=["three-layer"],
)
async def get_events_by_activity(
    body: GetEventsByActivityRequest,
) -> GetEventsByActivityResponse:
    """
    Get all events for a specific activity

    Args:
        body: Request containing activity_id

    Returns:
        Response with list of events
    """
    try:
        db = get_db()

        # Get the activity to find source event IDs
        activity = await db.activities_v2.get_by_id(body.activity_id)
        if not activity:
            return GetEventsByActivityResponse(
                success=False, events=[], error="Activity not found"
            )

        # Get source event IDs
        source_event_ids = activity.get("source_event_ids", [])
        if not source_event_ids:
            return GetEventsByActivityResponse(success=True, events=[])

        # Get events by IDs
        event_dicts = await db.events_v2.get_by_ids(source_event_ids)

        # Convert to EventResponse objects
        events = [
            EventResponse(
                id=e["id"],
                title=e["title"],
                description=e["description"],
                start_time=e["start_time"],
                end_time=e["end_time"],
                source_action_ids=e.get("source_action_ids", []),
                created_at=e["created_at"],
            )
            for e in event_dicts
        ]

        return GetEventsByActivityResponse(success=True, events=events)

    except Exception as e:
        logger.error(f"Failed to get events by activity: {e}", exc_info=True)
        return GetEventsByActivityResponse(
            success=False, events=[], error=str(e)
        )


# Delete operations

@api_handler(
    body=DeleteActivityRequest,
    method="DELETE",
    path="/activities/delete",
    tags=["processing"],
)
async def delete_activity(body: DeleteActivityRequest) -> TimedOperationResponse:
    """Delete activity by ID.

    Removes the activity from persistence and emits deletion event to frontend.

    @param body - Request parameters including activity ID.
    @returns Deletion result with success flag and timestamp
    """
    db, _, _, _ = _get_data_access()

    existing = await db.activities_v2.get_by_id(body.activity_id)
    if not existing:
        logger.warning(f"Attempted to delete non-existent activity: {body.activity_id}")
        return DataResponse(success=False, error="Activity not found", timestamp=datetime.now().isoformat())

    await db.activities_v2.delete(body.activity_id)
    success = True

    if not success:
        logger.warning(f"Attempted to delete non-existent activity: {body.activity_id}")
        return DataResponse(success=False, error="Activity not found", timestamp=datetime.now().isoformat())

    emit_activity_deleted(body.activity_id, datetime.now().isoformat())
    logger.info(f"Activity deleted: {body.activity_id}")

    return TimedOperationResponse(
        success=True,
        message="Activity deleted",
        data={"deleted": True, "activityId": body.activity_id},
        timestamp=datetime.now().isoformat(),
    )


@api_handler(
    body=DeleteActivitiesByDateRequest,
    method="DELETE",
    path="/activities/delete-by-date",
    tags=["processing"],
)
async def delete_activities_by_date(
    body: DeleteActivitiesByDateRequest,
) -> TimedOperationResponse:
    """Delete activities in date range.

    Soft deletes all activities that fall within the specified date range.

    @param body - Request parameters including start_date and end_date (YYYY-MM-DD format).
    @returns Deletion result with count of deleted activities
    """
    try:
        db, _, _, _ = _get_data_access()

        # Validate date range
        start_dt = datetime.strptime(body.start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(body.end_date, "%Y-%m-%d")

        if start_dt > end_dt:
            return DataResponse(success=False, error="Start date cannot be after end date", timestamp=datetime.now().isoformat())

        deleted_count = await db.activities_v2.delete_by_date_range(
            start_dt.isoformat(),
            datetime.combine(end_dt, datetime.max.time()).isoformat(),
        )

        logger.debug(
            f"Batch delete activities: {deleted_count} items deleted between {body.start_date} and {body.end_date}"
        )

        return TimedOperationResponse(
            success=True,
            message=f"Successfully deleted {deleted_count} activities",
            data={
                "deleted_count": deleted_count,
                "start_date": body.start_date,
                "end_date": body.end_date,
            },
            timestamp=datetime.now().isoformat(),
        )
    except Exception as e:
        logger.error(f"Failed to delete activities by date range: {e}", exc_info=True)
        return DataResponse(
            success=False,
            message=f"Failed to delete activities: {str(e)}",
            timestamp=datetime.now().isoformat(),
        )


# Merge and split operations

@api_handler(
    body=MergeActivitiesRequest,
    method="POST",
    path="/activities/merge",
    tags=["activities"],
)
async def merge_activities_handler(
    body: MergeActivitiesRequest,
) -> MergeActivitiesResponse:
    """
    Merge multiple activities into a single activity

    Args:
        body: Merge request with activity IDs and merged content

    Returns:
        Response with merged activity ID or error
    """
    try:
        db = get_db()
        coordinator = get_coordinator()

        if len(body.activity_ids) < 2:
            return MergeActivitiesResponse(
                success=False, error="Need at least 2 activities to merge"
            )

        # Fetch all activities to merge
        activities = []
        for activity_id in body.activity_ids:
            activity = await db.activities_v2.get_by_id(activity_id)
            if not activity:
                return MergeActivitiesResponse(
                    success=False, error=f"Activity {activity_id} not found"
                )
            activities.append(activity)

        # Sort by start_time
        activities.sort(
            key=lambda a: datetime.fromisoformat(a["start_time"])
            if isinstance(a["start_time"], str)
            else a["start_time"]
        )

        # Calculate merged time range
        start_times = [
            datetime.fromisoformat(a["start_time"])
            if isinstance(a["start_time"], str)
            else a["start_time"]
            for a in activities
        ]
        end_times = [
            datetime.fromisoformat(a["end_time"])
            if isinstance(a["end_time"], str)
            else a["end_time"]
            for a in activities
        ]

        merged_start_time = min(start_times)
        merged_end_time = max(end_times)

        # Collect all source event IDs
        merged_source_event_ids = []
        for activity in activities:
            source_event_ids = activity.get("source_event_ids", [])
            if isinstance(source_event_ids, str):
                try:
                    source_event_ids = json.loads(source_event_ids)
                except Exception:
                    source_event_ids = []
            merged_source_event_ids.extend(source_event_ids)

        # Calculate session duration
        duration = merged_end_time - merged_start_time
        session_duration_minutes = int(duration.total_seconds() / 60)

        # Merge topic tags (deduplicate)
        merged_topic_tags = []
        for activity in activities:
            topic_tags = activity.get("topic_tags", [])
            if isinstance(topic_tags, str):
                try:
                    topic_tags = json.loads(topic_tags)
                except Exception:
                    topic_tags = []
            for tag in topic_tags:
                if tag not in merged_topic_tags:
                    merged_topic_tags.append(tag)

        # Create merged activity
        merged_activity_id = str(uuid.uuid4())

        await db.activities_v2.save(
            activity_id=merged_activity_id,
            title=body.merged_title or activities[0].get("title", "Merged session"),
            description=body.merged_description
            or " | ".join([a.get("description", "") for a in activities]),
            start_time=merged_start_time.isoformat(),
            end_time=merged_end_time.isoformat(),
            source_event_ids=merged_source_event_ids,
            session_duration_minutes=session_duration_minutes,
            topic_tags=merged_topic_tags,
            user_merged_from_ids=body.activity_ids,
        )

        # Mark original activities as deleted
        for activity_id in body.activity_ids:
            await db.activities_v2.mark_deleted(activity_id)

        # Record user merge action for learning (if session_agent is available)
        if coordinator.session_agent:
            await coordinator.session_agent.record_user_merge(
                merged_activity_id, body.activity_ids, activities
            )

        # Emit event to notify frontend
        emit_activity_merged(
            merged_activity_id=merged_activity_id,
            original_activity_ids=body.activity_ids,
        )

        logger.info(
            f"Merged {len(body.activity_ids)} activities into {merged_activity_id}"
        )

        return MergeActivitiesResponse(
            success=True, merged_activity_id=merged_activity_id
        )

    except Exception as e:
        logger.error(f"Failed to merge activities: {e}", exc_info=True)
        return MergeActivitiesResponse(success=False, error=str(e))


@api_handler(
    body=SplitActivityRequest,
    method="POST",
    path="/activities/split",
    tags=["activities"],
)
async def split_activity_handler(
    body: SplitActivityRequest,
) -> SplitActivityResponse:
    """
    Split an activity into multiple activities

    Args:
        body: Split request with activity ID and split points

    Returns:
        Response with new activity IDs or error
    """
    try:
        db = get_db()
        coordinator = get_coordinator()

        # Fetch original activity
        activity = await db.activities_v2.get_by_id(body.activity_id)
        if not activity:
            return SplitActivityResponse(
                success=False, error=f"Activity {body.activity_id} not found"
            )

        # Get source events
        source_event_ids = activity.get("source_event_ids", [])
        if isinstance(source_event_ids, str):
            try:
                source_event_ids = json.loads(source_event_ids)
            except Exception:
                source_event_ids = []

        # Fetch all source events
        source_events = []
        for event_id in source_event_ids:
            event = await db.events_v2.get_by_id(event_id)
            if event:
                source_events.append(event)

        if not source_events:
            return SplitActivityResponse(
                success=False, error="No source events found for this activity"
            )

        # Validate split points
        if len(body.split_points) < 2:
            return SplitActivityResponse(
                success=False, error="Need at least 2 split points to split activity"
            )

        # Create new activities from split points
        new_activity_ids = []

        for split_point in body.split_points:
            # Validate event indexes
            event_indexes = split_point.event_indexes
            if not event_indexes:
                return SplitActivityResponse(
                    success=False, error="Each split point must include at least 1 event"
                )

            # Get events for this split
            split_events = []
            split_event_ids = []

            for idx in event_indexes:
                # Convert 1-based to 0-based
                idx_zero_based = idx - 1
                if idx_zero_based < 0 or idx_zero_based >= len(source_events):
                    return SplitActivityResponse(
                        success=False,
                        error=f"Invalid event index {idx} (must be 1-{len(source_events)})",
                    )

                event = source_events[idx_zero_based]
                split_events.append(event)
                split_event_ids.append(event["id"])

            # Calculate time range for this split
            split_start_times = [
                datetime.fromisoformat(e["start_time"])
                if isinstance(e["start_time"], str)
                else e["start_time"]
                for e in split_events
            ]
            split_end_times = [
                datetime.fromisoformat(e["end_time"])
                if isinstance(e["end_time"], str)
                else e["end_time"]
                for e in split_events
            ]

            split_start_time = min(split_start_times)
            split_end_time = max(split_end_times)

            # Calculate session duration
            duration = split_end_time - split_start_time
            session_duration_minutes = int(duration.total_seconds() / 60)

            # Create new activity
            new_activity_id = str(uuid.uuid4())

            await db.activities_v2.save(
                activity_id=new_activity_id,
                title=split_point.title,
                description=split_point.description,
                start_time=split_start_time.isoformat(),
                end_time=split_end_time.isoformat(),
                source_event_ids=split_event_ids,
                session_duration_minutes=session_duration_minutes,
                topic_tags=[],  # User can add tags later
            )

            new_activity_ids.append(new_activity_id)

        # Mark original activity as deleted
        await db.activities_v2.mark_deleted(body.activity_id)

        # Update the original activity to record split info
        await db.activities_v2.record_user_split(body.activity_id, new_activity_ids)

        # Record user split action for learning (if session_agent is available)
        if coordinator.session_agent:
            await coordinator.session_agent.record_user_split(
                body.activity_id, new_activity_ids, activity, source_events
            )

        # Emit event to notify frontend
        emit_activity_split(
            original_activity_id=body.activity_id,
            new_activity_ids=new_activity_ids,
        )

        logger.info(
            f"Split activity {body.activity_id} into {len(new_activity_ids)} new activities"
        )

        return SplitActivityResponse(success=True, new_activity_ids=new_activity_ids)

    except Exception as e:
        logger.error(f"Failed to split activity: {e}", exc_info=True)
        return SplitActivityResponse(success=False, error=str(e))
