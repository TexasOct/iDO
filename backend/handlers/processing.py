"""
Processing module command handlers
"""

from typing import Dict, Any, Optional
from datetime import datetime
from core.coordinator import get_coordinator
from core.logger import get_logger
from core.events import emit_activity_deleted
from . import api_handler
from processing.persistence import ProcessingPersistence
from models import (
    GetEventsRequest,
    GetActivitiesRequest,
    GetEventByIdRequest,
    GetActivityByIdRequest,
    DeleteActivityRequest,
    CleanupOldDataRequest,
    GetActivitiesIncrementalRequest,
    GetActivityCountByDateRequest,
)

logger = get_logger(__name__)

_fallback_persistence: Optional[ProcessingPersistence] = None


def _get_pipeline():
    coordinator = get_coordinator()
    return coordinator.processing_pipeline, coordinator


def _get_persistence():
    global _fallback_persistence

    pipeline, coordinator = _get_pipeline()
    if pipeline and getattr(pipeline, "persistence", None):
        return pipeline.persistence, coordinator

    if _fallback_persistence is None:
        logger.debug(
            "Initializing ProcessingPersistence (new architecture) in read-only mode to access data"
        )
        _fallback_persistence = ProcessingPersistence()

    return _fallback_persistence, coordinator


@api_handler()
async def get_processing_stats() -> Dict[str, Any]:
    """Get processing module statistics.

    Returns statistics about event and activity processing.

    @returns Statistics data with success flag and timestamp
    """
    coordinator = get_coordinator()
    stats = coordinator.get_stats()

    return {"success": True, "data": stats, "timestamp": datetime.now().isoformat()}


@api_handler(body=GetEventsRequest)
async def get_events(body: GetEventsRequest) -> Dict[str, Any]:
    """Get processed events with optional filters.

    @param body - Request parameters including limit and filters.
    @returns Events data with success flag and timestamp
    """
    persistence, coordinator = _get_persistence()

    # Parse datetime if provided
    start_dt = datetime.fromisoformat(body.start_time) if body.start_time else None
    end_dt = datetime.fromisoformat(body.end_time) if body.end_time else None

    if body.event_type:
        events = await persistence.get_events_by_type(body.event_type, body.limit)
    elif start_dt and end_dt:
        events = await persistence.get_events_in_timeframe(start_dt, end_dt)
    else:
        events = await persistence.get_recent_events(body.limit)

    events_data = []
    for event in events:
        # New architecture events only contain core fields, provide backward-compatible structure here
        event_id = (
            event.get("id") if isinstance(event, dict) else getattr(event, "id", "")
        )
        timestamp = (
            event.get("timestamp")
            if isinstance(event, dict)
            else getattr(event, "timestamp", None)
        )
        if isinstance(timestamp, datetime):
            start_time = timestamp
        elif isinstance(timestamp, str):
            try:
                start_time = datetime.fromisoformat(timestamp)
            except ValueError:
                start_time = datetime.now()
        else:
            start_time = datetime.now()

        summary = (
            event.get("description")
            if isinstance(event, dict)
            else getattr(event, "summary", "")
        )
        events_data.append(
            {
                "id": event_id,
                "startTime": start_time.isoformat(),
                "endTime": start_time.isoformat(),
                "summary": summary,
                "sourceDataCount": len(event.get("keywords", []))
                if isinstance(event, dict)
                else len(getattr(event, "source_data", [])),
                "screenshots": event.get("screenshots", [])
                if isinstance(event, dict)
                else [],
            }
        )

    return {
        "success": True,
        "data": {
            "events": events_data,
            "count": len(events_data),
            "filters": {
                "limit": body.limit,
                "eventType": body.event_type,
                "startTime": body.start_time,
                "endTime": body.end_time,
            },
        },
        "timestamp": datetime.now().isoformat(),
    }


@api_handler(body=GetActivitiesRequest)
async def get_activities(body: GetActivitiesRequest) -> Dict[str, Any]:
    """Get processed activities.

    @param body - Request parameters including limit.
    @returns Activities data with success flag and timestamp
    """
    persistence, coordinator = _get_persistence()
    activities = await persistence.get_recent_activities(body.limit, body.offset)

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

    return {
        "success": True,
        "data": {
            "activities": activities_data,
            "count": len(activities_data),
            "filters": {
                "limit": body.limit,
                "offset": body.offset,
            },
        },
        "timestamp": datetime.now().isoformat(),
    }


@api_handler(body=GetEventByIdRequest)
async def get_event_by_id(body: GetEventByIdRequest) -> Dict[str, Any]:
    """Get event details by ID.

    @param body - Request parameters including event ID.
    @returns Event details with success flag and timestamp
    """
    persistence, _ = _get_persistence()
    event = await persistence.get_event_by_id(body.event_id)

    if not event:
        return {
            "success": False,
            "error": "Event not found",
            "timestamp": datetime.now().isoformat(),
        }

    timestamp = event.get("timestamp")
    if isinstance(timestamp, datetime):
        ts_str = timestamp.isoformat()
    else:
        ts_str = str(timestamp or datetime.now().isoformat())

    event_detail = {
        "id": event.get("id"),
        "startTime": ts_str,
        "endTime": ts_str,
        "type": "event",
        "summary": event.get("description", ""),
        "keywords": event.get("keywords", []),
        "createdAt": event.get("created_at"),
        "screenshots": event.get("screenshots", []),
    }

    return {
        "success": True,
        "data": event_detail,
        "timestamp": datetime.now().isoformat(),
    }


@api_handler(body=GetActivityByIdRequest)
async def get_activity_by_id(body: GetActivityByIdRequest) -> Dict[str, Any]:
    """Get activity details by ID.

    @param body - Request parameters including activity ID.
    @returns Activity details with success flag and timestamp
    """
    persistence, _ = _get_persistence()
    activity = await persistence.get_activity_by_id(body.activity_id)

    if not activity:
        return {
            "success": False,
            "error": "Activity not found",
            "timestamp": datetime.now().isoformat(),
        }

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

    activity_detail = {
        "id": activity.get("id"),
        "title": activity.get("title", ""),
        "description": activity.get("description", ""),
        "startTime": _parse_dt(start_time),
        "endTime": _parse_dt(end_time),
        "sourceEventIds": activity.get("source_event_ids", []),
        "createdAt": activity.get("created_at"),
    }

    return {
        "success": True,
        "data": activity_detail,
        "timestamp": datetime.now().isoformat(),
    }


@api_handler(
    body=DeleteActivityRequest,
    method="DELETE",
    path="/activities/delete",
    tags=["processing"],
)
async def delete_activity(body: DeleteActivityRequest) -> Dict[str, Any]:
    """Delete activity by ID.

    Removes the activity from persistence and emits deletion event to frontend.

    @param body - Request parameters including activity ID.
    @returns Deletion result with success flag and timestamp
    """
    persistence, _ = _get_persistence()

    success = await persistence.delete_activity(body.activity_id)

    if not success:
        logger.warning(f"Attempted to delete non-existent activity: {body.activity_id}")
        return {
            "success": False,
            "error": "Activity not found",
            "timestamp": datetime.now().isoformat(),
        }

    emit_activity_deleted(body.activity_id, datetime.now().isoformat())
    logger.info(f"Activity deleted: {body.activity_id}")

    return {
        "success": True,
        "message": "Activity deleted",
        "data": {"deleted": True, "activityId": body.activity_id},
        "timestamp": datetime.now().isoformat(),
    }


@api_handler()
async def start_processing() -> Dict[str, Any]:
    """Start the processing pipeline.

    Begins processing raw records into events and activities.

    @returns Success response with message and timestamp
    """
    pipeline, coordinator = _get_pipeline()
    if not pipeline:
        message = (
            coordinator.last_error
            or "Processing pipeline unavailable, please check model configuration."
        )
        logger.warning(
            f"start_processing called but processing pipeline not initialized: {message}"
        )
        return {
            "success": False,
            "message": message,
            "timestamp": datetime.now().isoformat(),
        }

    await pipeline.start()

    return {
        "success": True,
        "message": "Processing pipeline started",
        "timestamp": datetime.now().isoformat(),
    }


@api_handler()
async def stop_processing() -> Dict[str, Any]:
    """Stop the processing pipeline.

    Stops processing raw records.

    @returns Success response with message and timestamp
    """
    pipeline, coordinator = _get_pipeline()
    if not pipeline:
        logger.info(
            "stop_processing called with uninitialized processing pipeline, considered as stopped"
        )
        return {
            "success": True,
            "message": "Processing pipeline not running",
            "timestamp": datetime.now().isoformat(),
        }

    await pipeline.stop()

    return {
        "success": True,
        "message": "Processing pipeline stopped",
        "timestamp": datetime.now().isoformat(),
    }


@api_handler()
async def finalize_current_activity() -> Dict[str, Any]:
    """Force finalize the current activity.

    Forces the completion of the current activity being processed.

    @returns Success response with message and timestamp
    """
    pipeline, coordinator = _get_pipeline()
    if not pipeline:
        message = (
            coordinator.last_error
            or "Processing pipeline unavailable, cannot finalize activity."
        )
        logger.warning(f"finalize_current_activity call failed: {message}")
        return {
            "success": False,
            "message": message,
            "timestamp": datetime.now().isoformat(),
        }

    await pipeline.force_finalize_activity()

    return {
        "success": True,
        "message": "Current activity forcefully completed",
        "timestamp": datetime.now().isoformat(),
    }


@api_handler(body=CleanupOldDataRequest)
async def cleanup_old_data(body: CleanupOldDataRequest) -> Dict[str, Any]:
    """Clean up old data.

    @param body - Request parameters including number of days to keep.
    @returns Cleanup result with success flag and timestamp
    """
    persistence, coordinator = _get_persistence()
    result = await persistence.delete_old_data(body.days)

    return {
        "success": True,
        "data": result,
        "message": f"Cleaned data from {body.days} days ago",
        "timestamp": datetime.now().isoformat(),
    }


@api_handler()
async def get_persistence_stats() -> Dict[str, Any]:
    """Get persistence statistics.

    Returns statistics about data persistence including database size and record counts.

    @returns Statistics data with success flag and timestamp
    """
    persistence, coordinator = _get_persistence()
    stats = persistence.get_stats()

    return {"success": True, "data": stats, "timestamp": datetime.now().isoformat()}


@api_handler(body=GetActivitiesIncrementalRequest)
async def get_activities_incremental(
    body: GetActivitiesIncrementalRequest,
) -> Dict[str, Any]:
    """Get incremental activity updates based on version negotiation.

    This handler implements version-based incremental updates. The client provides
    its current version number, and the server returns only activities created or
    updated after that version.

    @param body - Request parameters including client version and limit.
    @returns New activities data with success flag, max version, and timestamp
    """
    # New architecture does not yet support versioned incremental updates, return empty result for compatibility
    return {
        "success": True,
        "data": {
            "activities": [],
            "count": 0,
            "maxVersion": body.version,
            "clientVersion": body.version,
        },
        "timestamp": datetime.now().isoformat(),
    }


@api_handler(body=GetActivityCountByDateRequest)
async def get_activity_count_by_date(
    body: GetActivityCountByDateRequest,
) -> Dict[str, Any]:
    """Get activity count for each date (total count, not paginated).

    Returns the total number of activities for each date in the database.

    @param body - Request parameters (empty).
    @returns Activity count statistics by date
    """
    # New architecture does not yet provide date statistics, return empty data structure
    return {
        "success": True,
        "data": {"dateCountMap": {}, "totalDates": 0, "totalActivities": 0},
        "timestamp": datetime.now().isoformat(),
    }
