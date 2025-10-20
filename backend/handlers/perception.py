"""
Perception module command handlers
感知模块的命令处理器
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from . import tauri_command


@tauri_command()
async def get_perception_stats() -> Dict[str, Any]:
    """Get perception module statistics.

    Returns statistics about the perception module including record counts and status.

    @returns Statistics data with success flag and timestamp
    """
    from perception.manager import PerceptionManager

    manager = PerceptionManager()
    stats = manager.get_stats()

    return {
        "success": True,
        "data": stats,
        "timestamp": datetime.now().isoformat()
    }


@tauri_command()
async def get_records(
    limit: int = 100,
    event_type: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None
) -> Dict[str, Any]:
    """Get perception records with optional filters.

    @param limit - Maximum number of records to return (1-1000)
    @param event_type - Optional event type filter
    @param start_time - Optional start time filter (ISO format)
    @param end_time - Optional end time filter (ISO format)
    @returns Records data with success flag and timestamp
    """
    from perception.manager import PerceptionManager

    manager = PerceptionManager()

    # Parse datetime if provided
    start_dt = datetime.fromisoformat(start_time) if start_time else None
    end_dt = datetime.fromisoformat(end_time) if end_time else None

    if event_type:
        records = manager.get_records_by_type(event_type)
    elif start_dt and end_dt:
        records = manager.get_records_in_timeframe(start_dt, end_dt)
    else:
        records = manager.get_recent_records(limit)

    # Convert to dict format
    records_data = []
    for record in records:
        record_dict = {
            "timestamp": record.timestamp.isoformat(),
            "type": record.type.value,
            "data": record.data
        }
        records_data.append(record_dict)

    return {
        "success": True,
        "data": {
            "records": records_data,
            "count": len(records_data),
            "filters": {
                "limit": limit,
                "eventType": event_type,
                "startTime": start_time,
                "endTime": end_time
            }
        },
        "timestamp": datetime.now().isoformat()
    }


@tauri_command()
async def start_perception() -> Dict[str, Any]:
    """Start the perception module.

    Starts monitoring keyboard, mouse, and screenshots.

    @returns Success response with message and timestamp
    """
    from perception.manager import PerceptionManager

    manager = PerceptionManager()
    if manager.is_running:
        return {
            "success": True,
            "message": "感知模块已在运行中",
            "timestamp": datetime.now().isoformat()
        }

    await manager.start()
    return {
        "success": True,
        "message": "感知模块已启动",
        "timestamp": datetime.now().isoformat()
    }


@tauri_command()
async def stop_perception() -> Dict[str, Any]:
    """Stop the perception module.

    Stops monitoring keyboard, mouse, and screenshots.

    @returns Success response with message and timestamp
    """
    from perception.manager import PerceptionManager

    manager = PerceptionManager()
    if not manager.is_running:
        return {
            "success": True,
            "message": "感知模块未在运行",
            "timestamp": datetime.now().isoformat()
        }

    await manager.stop()
    return {
        "success": True,
        "message": "感知模块已停止",
        "timestamp": datetime.now().isoformat()
    }


@tauri_command()
async def clear_records() -> Dict[str, Any]:
    """Clear all perception records.

    Removes all stored records and clears the buffer.

    @returns Success response with message and timestamp
    """
    from perception.manager import PerceptionManager

    manager = PerceptionManager()
    manager.storage.clear()
    manager.clear_buffer()

    return {
        "success": True,
        "message": "所有记录已清空",
        "timestamp": datetime.now().isoformat()
    }


@tauri_command()
async def get_buffered_events() -> Dict[str, Any]:
    """Get buffered events.

    Returns events currently in the buffer waiting to be processed.

    @returns Buffered events data with success flag and timestamp
    """
    from perception.manager import PerceptionManager

    manager = PerceptionManager()
    events = manager.get_buffered_events()

    events_data = []
    for event in events:
        event_dict = {
            "timestamp": event.timestamp.isoformat(),
            "type": event.type.value,
            "data": event.data
        }
        events_data.append(event_dict)

    return {
        "success": True,
        "data": {
            "events": events_data,
            "count": len(events_data)
        },
        "timestamp": datetime.now().isoformat()
    }
