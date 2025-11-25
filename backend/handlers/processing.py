"""
Processing module command handlers
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from core.coordinator import get_coordinator
from core.db import DatabaseManager, get_db
from core.events import emit_activity_deleted, emit_event_deleted
from core.logger import get_logger
from models import (
    CleanupOldDataRequest,
    DeleteActivitiesByDateRequest,
    DeleteActivityRequest,
    DeleteDiariesByDateRequest,
    DeleteEventRequest,
    DeleteKnowledgeByDateRequest,
    DeleteTodosByDateRequest,
    GetActivitiesIncrementalRequest,
    GetActivitiesRequest,
    GetActivityByIdRequest,
    GetActivityCountByDateRequest,
    GetEventByIdRequest,
    GetEventsRequest,
)
from processing.image_manager import ImageManager, get_image_manager
from processing.pipeline import ProcessingPipeline

from . import api_handler

logger = get_logger(__name__)
_fallback_image_manager: Optional[ImageManager] = None


def _get_pipeline():
    coordinator = get_coordinator()
    return coordinator.processing_pipeline, coordinator


def _get_data_access() -> Tuple[DatabaseManager, ImageManager, Optional[ProcessingPipeline], Any]:
    pipeline, coordinator = _get_pipeline()

    db = getattr(pipeline, "db", None) if pipeline else None
    if db is None:
        db = get_db()

    global _fallback_image_manager
    image_manager = getattr(pipeline, "image_manager", None) if pipeline else None
    if image_manager is None:
        if _fallback_image_manager is None:
            _fallback_image_manager = get_image_manager()
        image_manager = _fallback_image_manager

    return db, image_manager, pipeline, coordinator


async def _load_event_screenshots_base64(
    db: DatabaseManager, image_manager: ImageManager, event_id: str
) -> Tuple[List[str], List[str]]:
    """Return screenshot hashes and base64 data for an event"""
    hashes = await _get_event_screenshot_hashes(db, event_id)

    screenshots: List[str] = []
    for img_hash in hashes:
        if not img_hash:
            continue
        data = image_manager.get_from_cache(img_hash)
        if not data:
            data = image_manager.load_thumbnail_base64(img_hash)
        if data:
            screenshots.append(data)

    return hashes, screenshots


async def _get_event_screenshot_hashes(
    db: DatabaseManager, event_id: str
) -> List[str]:
    try:
        return await db.events.get_screenshots(event_id)
    except Exception as exc:
        logger.error("Failed to load screenshot hashes for event %s: %s", event_id, exc)
        return []


def _calculate_persistence_stats(db: DatabaseManager) -> Dict[str, Any]:
    try:
        stats: Dict[str, Any] = dict(db.get_table_counts())

        try:
            size_bytes = db.db_path.stat().st_size
        except OSError:
            size_bytes = 0

        stats["databasePath"] = str(db.db_path)
        stats["databaseSize"] = size_bytes
        return stats

    except Exception as exc:
        logger.error("Failed to compute persistence stats: %s", exc)
        return {"error": str(exc)}


async def _delete_old_data(db: DatabaseManager, days: int) -> Dict[str, Any]:
    try:
        cutoff = datetime.now() - timedelta(days=days)
        cutoff_iso = cutoff.isoformat()

        return await db.delete_old_data(cutoff_iso, cutoff.strftime("%Y-%m-%d"))

    except Exception as exc:
        logger.error("Failed to clean up old data: %s", exc)
        return {"error": str(exc)}


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
    db, image_manager, _, _ = _get_data_access()

    start_dt = datetime.fromisoformat(body.start_time) if body.start_time else None
    end_dt = datetime.fromisoformat(body.end_time) if body.end_time else None

    if body.event_type:
        logger.warning(
            "Event type filter not supported in new architecture, returning recent events"
        )
        events = await db.events.get_recent(body.limit)
    elif start_dt and end_dt:
        events = await db.events.get_in_timeframe(
            start_dt.isoformat(), end_dt.isoformat()
        )
    else:
        events = await db.events.get_recent(body.limit)

    events_data = []
    for event in events:
        # New architecture events only contain core fields, provide backward-compatible structure here
        raw_event_id = (
            event.get("id") if isinstance(event, dict) else getattr(event, "id", "")
        )
        event_id = str(raw_event_id) if raw_event_id is not None else ""
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
        hashes, screenshots = await _load_event_screenshots_base64(
            db, image_manager, event_id
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
                "screenshots": screenshots,
                "screenshotHashes": hashes,
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
    db, _, _, _ = _get_data_access()
    activities = await db.activities.get_recent(body.limit, body.offset)

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
    db, image_manager, _, _ = _get_data_access()
    event = await db.events.get_by_id(body.event_id)

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
        "screenshots": (
            await _load_event_screenshots_base64(db, image_manager, body.event_id)
        )[1],
    }

    return {
        "success": True,
        "data": event_detail,
        "timestamp": datetime.now().isoformat(),
    }


@api_handler(body=GetActivityByIdRequest)
async def get_activity_by_id(body: GetActivityByIdRequest) -> Dict[str, Any]:
    """Get activity details by ID with full event summaries and records.

    @param body - Request parameters including activity ID.
    @returns Activity details with success flag and timestamp
    """
    db, _, _, _ = _get_data_access()
    activity = await db.activities.get_by_id(body.activity_id)

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
    db, _, _, _ = _get_data_access()

    existing = await db.activities.get_by_id(body.activity_id)
    if not existing:
        logger.warning(f"Attempted to delete non-existent activity: {body.activity_id}")
        return {
            "success": False,
            "error": "Activity not found",
            "timestamp": datetime.now().isoformat(),
        }

    await db.activities.delete(body.activity_id)
    success = True

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


@api_handler(
    body=DeleteEventRequest,
    method="DELETE",
    path="/events/delete",
    tags=["processing"],
)
async def delete_event(body: DeleteEventRequest) -> Dict[str, Any]:
    """Delete event by ID.

    Removes the event from persistence and emits deletion event to frontend.

    @param body - Request parameters including event ID.
    @returns Deletion result with success flag and timestamp
    """
    db, _, _, _ = _get_data_access()

    existing = await db.events.get_by_id(body.event_id)
    if not existing:
        logger.warning(f"Attempted to delete non-existent event: {body.event_id}")
        return {
            "success": False,
            "error": "Event not found",
            "timestamp": datetime.now().isoformat(),
        }

    await db.events.delete(body.event_id)
    success = True

    if not success:
        logger.warning(f"Attempted to delete non-existent event: {body.event_id}")
        return {
            "success": False,
            "error": "Event not found",
            "timestamp": datetime.now().isoformat(),
        }

    emit_event_deleted(body.event_id, datetime.now().isoformat())
    logger.info(f"Event deleted: {body.event_id}")

    return {
        "success": True,
        "message": "Event deleted",
        "data": {"deleted": True, "eventId": body.event_id},
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
        logger.debug(
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
    db, _, pipeline, _ = _get_data_access()

    # if pipeline and hasattr(pipeline, "delete_old_data"):
        # Use pipeline utility if available to keep behavior consistent
        # result = await pipeline.delete_old_data(body.days)
    # else:
        #
    result = await _delete_old_data(db, body.days)

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
    db, _, _, _ = _get_data_access()
    stats = _calculate_persistence_stats(db)

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
    try:
        db, _, _, _ = _get_data_access()

        # Query database for activity count by date
        counts = await db.activities.get_count_by_date()
        date_counts = [{"date": date, "count": count} for date, count in counts.items()]

        # Convert to map format: {"2025-01-15": 10, "2025-01-14": 5, ...}
        date_count_map = {item["date"]: item["count"] for item in date_counts}
        total_dates = len(date_count_map)
        total_activities = sum(date_count_map.values())

        logger.debug(
            f"Activity count by date: {total_dates} dates, {total_activities} total activities"
        )

        return {
            "success": True,
            "data": {
                "dateCountMap": date_count_map,
                "totalDates": total_dates,
                "totalActivities": total_activities,
            },
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to get activity count by date: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Failed to get activity count by date: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        }


@api_handler(
    body=DeleteActivitiesByDateRequest,
    method="DELETE",
    path="/activities/delete-by-date",
    tags=["processing"],
)
async def delete_activities_by_date(
    body: DeleteActivitiesByDateRequest,
) -> Dict[str, Any]:
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
            return {
                "success": False,
                "error": "Start date cannot be after end date",
                "timestamp": datetime.now().isoformat(),
            }

        deleted_count = await db.activities.delete_by_date_range(
            start_dt.isoformat(),
            datetime.combine(end_dt, datetime.max.time()).isoformat(),
        )

        logger.debug(
            f"Batch delete activities: {deleted_count} items deleted between {body.start_date} and {body.end_date}"
        )

        return {
            "success": True,
            "message": f"Successfully deleted {deleted_count} activities",
            "data": {
                "deleted_count": deleted_count,
                "start_date": body.start_date,
                "end_date": body.end_date,
            },
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to delete activities by date range: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Failed to delete activities: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        }


@api_handler(
    body=DeleteKnowledgeByDateRequest,
    method="DELETE",
    path="/knowledge/delete-by-date",
    tags=["insights"],
)
async def delete_knowledge_by_date(
    body: DeleteKnowledgeByDateRequest,
) -> Dict[str, Any]:
    """Delete knowledge in date range.

    Soft deletes all knowledge that fall within the specified date range.

    @param body - Request parameters including start_date and end_date (YYYY-MM-DD format).
    @returns Deletion result with count of deleted knowledge records
    """
    try:
        db, _, _, _ = _get_data_access()

        # Validate date range
        start_dt = datetime.strptime(body.start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(body.end_date, "%Y-%m-%d")

        if start_dt > end_dt:
            return {
                "success": False,
                "error": "Start date cannot be after end date",
                "timestamp": datetime.now().isoformat(),
            }

        deleted_count = await db.knowledge.delete_by_date_range(
            start_dt.isoformat(),
            datetime.combine(end_dt, datetime.max.time()).isoformat(),
        )

        logger.debug(
            f"Batch delete knowledge: {deleted_count} items deleted between {body.start_date} and {body.end_date}"
        )

        return {
            "success": True,
            "message": f"Successfully deleted {deleted_count} knowledge records",
            "data": {
                "deleted_count": deleted_count,
                "start_date": body.start_date,
                "end_date": body.end_date,
            },
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to delete knowledge by date range: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Failed to delete knowledge: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        }


@api_handler(
    body=DeleteTodosByDateRequest,
    method="DELETE",
    path="/todos/delete-by-date",
    tags=["insights"],
)
async def delete_todos_by_date(body: DeleteTodosByDateRequest) -> Dict[str, Any]:
    """Delete todos in date range.

    Soft deletes all todos that fall within the specified date range.

    @param body - Request parameters including start_date and end_date (YYYY-MM-DD format).
    @returns Deletion result with count of deleted todo records
    """
    try:
        db, _, _, _ = _get_data_access()

        # Validate date range
        start_dt = datetime.strptime(body.start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(body.end_date, "%Y-%m-%d")

        if start_dt > end_dt:
            return {
                "success": False,
                "error": "Start date cannot be after end date",
                "timestamp": datetime.now().isoformat(),
            }

        deleted_count = await db.todos.delete_by_date_range(
            start_dt.isoformat(),
            datetime.combine(end_dt, datetime.max.time()).isoformat(),
        )

        logger.debug(
            f"Batch delete todos: {deleted_count} items deleted between {body.start_date} and {body.end_date}"
        )

        return {
            "success": True,
            "message": f"Successfully deleted {deleted_count} todos",
            "data": {
                "deleted_count": deleted_count,
                "start_date": body.start_date,
                "end_date": body.end_date,
            },
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to delete todos by date range: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Failed to delete todos: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        }


@api_handler(
    body=DeleteDiariesByDateRequest,
    method="DELETE",
    path="/diaries/delete-by-date",
    tags=["insights"],
)
async def delete_diaries_by_date(body: DeleteDiariesByDateRequest) -> Dict[str, Any]:
    """Delete diaries in date range.

    Soft deletes all diaries that fall within the specified date range.

    @param body - Request parameters including start_date and end_date (YYYY-MM-DD format).
    @returns Deletion result with count of deleted diary records
    """
    try:
        db, _, _, _ = _get_data_access()

        # Validate date range
        start_dt = datetime.strptime(body.start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(body.end_date, "%Y-%m-%d")

        if start_dt > end_dt:
            return {
                "success": False,
                "error": "Start date cannot be after end date",
                "timestamp": datetime.now().isoformat(),
            }

        deleted_count = await db.diaries.delete_by_date_range(
            body.start_date, body.end_date
        )

        logger.debug(
            f"Batch delete diaries: {deleted_count} items deleted between {body.start_date} and {body.end_date}"
        )

        return {
            "success": True,
            "message": f"Successfully deleted {deleted_count} diaries",
            "data": {
                "deleted_count": deleted_count,
                "start_date": body.start_date,
                "end_date": body.end_date,
            },
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to delete diaries by date range: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Failed to delete diaries: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        }
