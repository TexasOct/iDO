"""
Event management handlers.

Handles all event-related operations including:
- CRUD operations for events
- Three-layer drill-down (events -> actions)
- Event details with screenshots
"""

from datetime import datetime
from typing import List, Tuple

from core.db import DatabaseManager, get_db
from core.events import emit_event_deleted
from core.logger import get_logger
from models import (
    DataResponse,
    DeleteEventRequest,
    GetEventByIdRequest,
    GetEventsRequest,
    TimedOperationResponse,
)
from models.requests import GetActionsByEventRequest
from models.responses import ActionResponse, GetActionsByEventResponse
from processing.image_manager import ImageManager, get_image_manager

from . import api_handler

logger = get_logger(__name__)
_fallback_image_manager: ImageManager | None = None


# ==================== Helper Functions ====================


def _get_data_access() -> Tuple[DatabaseManager, ImageManager]:
    """
    Get database and image manager instances.

    Returns:
        Tuple of (DatabaseManager, ImageManager)
    """
    from core.coordinator import get_coordinator

    coordinator = get_coordinator()
    pipeline = coordinator.processing_pipeline

    # Get database
    db = getattr(pipeline, "db", None) if pipeline else None
    if db is None:
        db = get_db()

    # Get image manager
    global _fallback_image_manager
    image_manager = getattr(pipeline, "image_manager", None) if pipeline else None
    if image_manager is None:
        if _fallback_image_manager is None:
            _fallback_image_manager = get_image_manager()
        image_manager = _fallback_image_manager

    return db, image_manager


async def _get_event_screenshot_hashes(
    db: DatabaseManager, event_id: str
) -> List[str]:
    """
    Get screenshot hashes for an event.

    Args:
        db: Database manager instance
        event_id: Event ID

    Returns:
        List of screenshot hashes
    """
    try:
        return await db.events.get_screenshots(event_id)
    except Exception as exc:
        logger.error("Failed to load screenshot hashes for event %s: %s", event_id, exc)
        return []


async def _load_event_screenshots_base64(
    db: DatabaseManager, image_manager: ImageManager, event_id: str
) -> Tuple[List[str], List[str]]:
    """
    Load screenshot hashes and base64 data for an event.

    Args:
        db: Database manager instance
        image_manager: Image manager instance
        event_id: Event ID

    Returns:
        Tuple of (screenshot_hashes, screenshot_base64_data)
    """
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


# ==================== API Handlers ====================


@api_handler(body=GetEventsRequest)
async def get_events(body: GetEventsRequest) -> DataResponse:
    """
    Get processed events with optional filters.

    Args:
        body: Request parameters including limit and filters.

    Returns:
        Events data with success flag and timestamp
    """
    db, image_manager = _get_data_access()

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

    return DataResponse(
        success=True,
        data={
            "events": events_data,
            "count": len(events_data),
            "filters": {
                "limit": body.limit,
                "eventType": body.event_type,
                "startTime": body.start_time,
                "endTime": body.end_time,
            },
        },
        timestamp=datetime.now().isoformat(),
    )


@api_handler(body=GetEventByIdRequest)
async def get_event_by_id(body: GetEventByIdRequest) -> DataResponse:
    """
    Get event details by ID.

    Args:
        body: Request parameters including event ID.

    Returns:
        Event details with success flag and timestamp
    """
    db, image_manager = _get_data_access()
    event = await db.events.get_by_id(body.event_id)

    if not event:
        return DataResponse(
            success=False,
            error="Event not found",
            timestamp=datetime.now().isoformat()
        )

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

    return DataResponse(
        success=True,
        data=event_detail,
        timestamp=datetime.now().isoformat()
    )


@api_handler(
    body=GetActionsByEventRequest,
    method="POST",
    path="/three-layer/get-actions-by-event",
    tags=["three-layer"],
)
async def get_actions_by_event(
    body: GetActionsByEventRequest,
) -> GetActionsByEventResponse:
    """
    Get all actions for a specific event (three-layer drill-down).

    Args:
        body: Request containing event_id

    Returns:
        Response with list of actions including screenshots
    """
    try:
        db = get_db()

        # Get the event to find source action IDs
        event = await db.events_v2.get_by_id(body.event_id)
        if not event:
            return GetActionsByEventResponse(
                success=False, actions=[], error="Event not found"
            )

        # Get source action IDs
        source_action_ids = event.get("source_action_ids", [])
        if not source_action_ids:
            return GetActionsByEventResponse(success=True, actions=[])

        # Get actions by IDs (this will automatically load screenshots)
        action_dicts = await db.actions.get_by_ids(source_action_ids)

        # Convert to ActionResponse objects
        actions = [
            ActionResponse(
                id=a["id"],
                title=a["title"],
                description=a["description"],
                keywords=a.get("keywords", []),
                timestamp=a["timestamp"],
                screenshots=a.get("screenshots", []),
                created_at=a["created_at"],
            )
            for a in action_dicts
        ]

        return GetActionsByEventResponse(success=True, actions=actions)

    except Exception as e:
        logger.error(f"Failed to get actions by event: {e}", exc_info=True)
        return GetActionsByEventResponse(
            success=False, actions=[], error=str(e)
        )


@api_handler(
    body=DeleteEventRequest,
    method="DELETE",
    path="/events/delete",
    tags=["processing"],
)
async def delete_event(body: DeleteEventRequest) -> TimedOperationResponse:
    """
    Delete event by ID.

    Removes the event from persistence and emits deletion event to frontend.

    Args:
        body: Request parameters including event ID.

    Returns:
        Deletion result with success flag and timestamp
    """
    db, _ = _get_data_access()

    existing = await db.events.get_by_id(body.event_id)
    if not existing:
        logger.warning(f"Attempted to delete non-existent event: {body.event_id}")
        return DataResponse(
            success=False,
            error="Event not found",
            timestamp=datetime.now().isoformat()
        )

    await db.events.delete(body.event_id)
    success = True

    if not success:
        logger.warning(f"Attempted to delete non-existent event: {body.event_id}")
        return DataResponse(
            success=False,
            error="Event not found",
            timestamp=datetime.now().isoformat()
        )

    emit_event_deleted(body.event_id, datetime.now().isoformat())
    logger.info(f"Event deleted: {body.event_id}")

    return TimedOperationResponse(
        success=True,
        message="Event deleted",
        data={"deleted": True, "eventId": body.event_id},
        timestamp=datetime.now().isoformat(),
    )
