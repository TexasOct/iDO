"""
Tauri event sending manager
Used to send event notifications from backend to frontend
"""

from typing import Any, Dict, Optional

from pydantic import RootModel

try:
    from pytauri import AppHandle, Emitter
except ImportError:  # pragma: no cover - May not be available in non-Tauri environments (like offline scripts, tests)
    AppHandle = Any  # type: ignore[assignment]
    Emitter = None  # type: ignore[assignment]
from core._event_state import event_state
from core.logger import get_logger

logger = get_logger(__name__)


class _RawEventPayload(RootModel[Dict[str, Any]]):
    """Wraps event payload for JSON serialization through PyTauri."""


def register_emit_handler(app_handle: AppHandle):
    """Register Tauri AppHandle for sending events through PyTauri Emitter."""
    if Emitter is None:
        logger.warning(
            "PyTauri not installed, event notification functionality unavailable"
        )
        return

    event_state.app_handle = app_handle
    logger.info("Registered Tauri AppHandle for event sending")


def _emit(event_name: str, payload: Dict[str, Any]) -> bool:
    """Send events to frontend through PyTauri."""
    if Emitter is None:
        logger.debug(
            f"[events] PyTauri Emitter unavailable, skipping event sending: {event_name}"
        )
        return False

    if event_state.app_handle is None:
        logger.warning(
            f"[events] AppHandle not registered, cannot send event: {event_name}"
        )
        return False

    try:
        Emitter.emit(event_state.app_handle, event_name, _RawEventPayload(payload))
        return True
    except Exception as exc:  # pragma: no cover - runtime exception logging
        logger.error(f"❌ [events] Event sending failed: {event_name}", exc_info=True)
        return False


def emit_activity_created(activity_data: Dict[str, Any]) -> bool:
    """
    Send "activity created" event to frontend

    Args:
        activity_data: Activity data dictionary, containing:
            - id: Activity ID
            - description: Activity description
            - startTime: Start time
            - endTime: End time
            - version: Version number
            - createdAt: Creation time

    Returns:
        True if sent successfully, False otherwise
    """
    logger.debug(
        "[emit_activity_created] Attempting to send activity creation event, AppHandle registered: %s",
        event_state.app_handle is not None,
    )

    payload = {
        "type": "activity_created",
        "data": activity_data,
        "timestamp": activity_data.get("createdAt"),
    }

    success = _emit("activity-created", payload)
    if success:
        logger.info(
            f"✅ [emit_activity_created] Successfully sent activity creation event: {activity_data.get('id')}"
        )
    return success


def emit_activity_updated(activity_data: Dict[str, Any]) -> bool:
    """
    Send "activity updated" event to frontend

    Args:
        activity_data: Updated activity data, should contain:
            - id: Activity ID
            - description: Activity description
            - startTime: Start time
            - endTime: End time
            - version: Version number
            - createdAt: Creation time

    Returns:
        True if sent successfully, False otherwise
    """
    payload = {
        "type": "activity_updated",
        "data": activity_data,
        "timestamp": activity_data.get("createdAt"),
    }

    success = _emit("activity-updated", payload)
    if success:
        logger.debug(f"✅ Activity update event sent: {activity_data.get('id')}")
    return success


def emit_activity_deleted(activity_id: str, timestamp: Optional[str] = None) -> bool:
    """
    Send "activity deleted" event to frontend

    Args:
        activity_id: ID of the deleted activity
        timestamp: Deletion timestamp

    Returns:
        True if sent successfully, False otherwise
    """
    from datetime import datetime

    resolved_timestamp = timestamp or datetime.now().isoformat()
    payload = {
        "type": "activity_deleted",
        "data": {"id": activity_id, "deletedAt": resolved_timestamp},
        "timestamp": resolved_timestamp,
    }

    success = _emit("activity-deleted", payload)
    if success:
        logger.debug(f"✅ Activity deletion event sent: {activity_id}")
    return success


def emit_event_deleted(event_id: str, timestamp: Optional[str] = None) -> bool:
    """
    Send "event deleted" event to frontend

    Args:
        event_id: ID of the deleted event
        timestamp: Deletion timestamp

    Returns:
        True if sent successfully, False otherwise
    """
    from datetime import datetime

    resolved_timestamp = timestamp or datetime.now().isoformat()
    payload = {
        "type": "event_deleted",
        "data": {"id": event_id, "deletedAt": resolved_timestamp},
        "timestamp": resolved_timestamp,
    }

    success = _emit("event-deleted", payload)
    if success:
        logger.debug(f"✅ Event deletion event sent: {event_id}")
    return success


def emit_bulk_update_completed(
    updated_count: int, timestamp: Optional[str] = None
) -> bool:
    """
    Send "bulk update completed" event to frontend
    Used to notify frontend that multiple activities have been batch updated

    Args:
        updated_count: Number of updated activities
        timestamp: Operation timestamp

    Returns:
        True if sent successfully, False otherwise
    """
    from datetime import datetime

    resolved_timestamp = timestamp or datetime.now().isoformat()
    payload = {
        "type": "bulk_update_completed",
        "data": {"updatedCount": updated_count, "timestamp": resolved_timestamp},
        "timestamp": resolved_timestamp,
    }

    success = _emit("bulk-update-completed", payload)
    if success:
        logger.debug(
            f"✅ Bulk update completion event sent: {updated_count} activities"
        )
    return success


def emit_agent_task_update(
    task_id: str,
    status: str,
    progress: Optional[Dict[str, Any]] = None,
    result: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
    timestamp: Optional[str] = None,
) -> bool:
    """
    Send "Agent task update" event to frontend

    Args:
        task_id: Task ID
        status: Task status (todo/processing/done/failed)
        progress: Task progress (optional)
        result: Task result (optional)
        error: Error information (optional)

    Returns:
        True if sent successfully, False otherwise
    """
    payload = {
        "taskId": task_id,
        "status": status,
    }

    if progress is not None:
        payload["progress"] = progress
    if result is not None:
        payload["result"] = result
    if error is not None:
        payload["error"] = error

    success = _emit("agent-task-update", payload)
    if success:
        logger.info(f"✅ Agent task update event sent: {task_id} -> {status}")
    return success


def emit_chat_message_chunk(
    conversation_id: str,
    chunk: str,
    done: bool = False,
    message_id: Optional[str] = None,
    timestamp: Optional[str] = None,
) -> bool:
    """
    Send "chat message chunk" event to frontend (for streaming output)

    Args:
        conversation_id: Conversation ID
        chunk: Text chunk content
        done: Whether completed (True indicates streaming output ended)
        message_id: Message ID (optional, provided when completed)

    Returns:
        True if sent successfully, False otherwise
    """
    payload = {
        "conversationId": conversation_id,
        "chunk": chunk,
        "done": done,
    }

    if message_id is not None:
        payload["messageId"] = message_id

    success = _emit("chat-message-chunk", payload)
    if success and done:
        logger.debug(f"✅ Chat message completion event sent: {conversation_id}")
    return success
