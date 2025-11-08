"""
Perception module command handlers
Perception module command handlers
"""

from datetime import datetime
from typing import Any, Dict, Protocol, Sequence, cast

from models import GetRecordsRequest

from . import api_handler


class PerceptionManagerProtocol(Protocol):
    is_running: bool
    storage: Any

    def get_stats(self) -> Dict[str, Any]: ...

    def get_records_by_type(self, event_type: str) -> Sequence[Any]: ...

    def get_records_in_timeframe(
        self, start: datetime, end: datetime
    ) -> Sequence[Any]: ...

    def get_recent_records(self, limit: int) -> Sequence[Any]: ...

    async def start(self) -> None: ...

    async def stop(self) -> None: ...

    def clear_buffer(self) -> None: ...

    def get_buffered_events(self) -> Sequence[Any]: ...


def _get_perception_manager() -> PerceptionManagerProtocol:
    from core.coordinator import get_coordinator

    coordinator = get_coordinator()
    manager = getattr(coordinator, "perception_manager", None)
    if manager is None:
        raise RuntimeError("Perception manager is not initialized")
    return cast(PerceptionManagerProtocol, manager)


@api_handler()
async def get_perception_stats() -> Dict[str, Any]:
    """Get perception module statistics.

    Returns statistics about the perception module including record counts and status.

    @returns Statistics data with success flag and timestamp
    """
    manager = _get_perception_manager()
    stats = manager.get_stats()

    return {"success": True, "data": stats, "timestamp": datetime.now().isoformat()}


@api_handler(body=GetRecordsRequest)
async def get_records(body: GetRecordsRequest) -> Dict[str, Any]:
    """Get perception records with optional filters.

    @param body - Request parameters including limit and filters.
    @returns Records data with success flag and timestamp
    """
    manager = _get_perception_manager()

    # Parse datetime if provided
    start_dt = datetime.fromisoformat(body.start_time) if body.start_time else None
    end_dt = datetime.fromisoformat(body.end_time) if body.end_time else None

    if body.event_type:
        records = manager.get_records_by_type(body.event_type)
    elif start_dt and end_dt:
        records = manager.get_records_in_timeframe(start_dt, end_dt)
    else:
        records = manager.get_recent_records(body.limit)

    # Convert to dict format
    records_data = []
    for record in records:
        record_dict = {
            "timestamp": record.timestamp.isoformat(),
            "type": record.type.value,
            "data": record.data,
        }
        records_data.append(record_dict)

    return {
        "success": True,
        "data": {
            "records": records_data,
            "count": len(records_data),
            "filters": {
                "limit": body.limit,
                "eventType": body.event_type,
                "startTime": body.start_time,
                "endTime": body.end_time,
            },
        },
        "timestamp": datetime.now().isoformat(),
    }


@api_handler()
async def start_perception() -> Dict[str, Any]:
    """Start the perception module.

    Starts monitoring keyboard, mouse, and screenshots.

    @returns Success response with message and timestamp
    """
    manager = _get_perception_manager()

    if manager.is_running:
        return {
            "success": True,
            "message": "Perception module is already running",
            "timestamp": datetime.now().isoformat(),
        }

    await manager.start()
    return {
        "success": True,
        "message": "Perception module started",
        "timestamp": datetime.now().isoformat(),
    }


@api_handler()
async def stop_perception() -> Dict[str, Any]:
    """Stop the perception module.

    Stops monitoring keyboard, mouse, and screenshots.

    @returns Success response with message and timestamp
    """
    manager = _get_perception_manager()

    if not manager.is_running:
        return {
            "success": True,
            "message": "Perception module not running",
            "timestamp": datetime.now().isoformat(),
        }

    await manager.stop()
    return {
        "success": True,
        "message": "Perception module stopped",
        "timestamp": datetime.now().isoformat(),
    }


@api_handler()
async def clear_records() -> Dict[str, Any]:
    """Clear all perception records.

    Removes all stored records and clears the buffer.

    @returns Success response with message and timestamp
    """
    manager = _get_perception_manager()

    manager.storage.clear()
    manager.clear_buffer()

    return {
        "success": True,
        "message": "All records cleared",
        "timestamp": datetime.now().isoformat(),
    }


@api_handler()
async def get_buffered_events() -> Dict[str, Any]:
    """Get buffered events.

    Returns events currently in the buffer waiting to be processed.

    @returns Buffered events data with success flag and timestamp
    """
    manager = _get_perception_manager()

    events = manager.get_buffered_events()

    events_data = []
    for event in events:
        event_dict = {
            "timestamp": event.timestamp.isoformat(),
            "type": event.type.value,
            "data": event.data,
        }
        events_data.append(event_dict)

    return {
        "success": True,
        "data": {"events": events_data, "count": len(events_data)},
        "timestamp": datetime.now().isoformat(),
    }
