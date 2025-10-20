"""
Processing module command handlers
处理模块的命令处理器
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from . import tauri_command


@tauri_command()
async def get_processing_stats() -> Dict[str, Any]:
    """Get processing module statistics.

    Returns statistics about event and activity processing.

    @returns Statistics data with success flag and timestamp
    """
    from processing.pipeline import ProcessingPipeline

    pipeline = ProcessingPipeline()
    stats = pipeline.get_stats()

    return {
        "success": True,
        "data": stats,
        "timestamp": datetime.now().isoformat()
    }


@tauri_command()
async def get_events(
    limit: int = 50,
    event_type: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None
) -> Dict[str, Any]:
    """Get processed events with optional filters.

    @param limit - Maximum number of events to return (1-500)
    @param event_type - Optional event type filter
    @param start_time - Optional start time filter (ISO format)
    @param end_time - Optional end time filter (ISO format)
    @returns Events data with success flag and timestamp
    """
    from processing.pipeline import ProcessingPipeline

    pipeline = ProcessingPipeline()

    # Parse datetime if provided
    start_dt = datetime.fromisoformat(start_time) if start_time else None
    end_dt = datetime.fromisoformat(end_time) if end_time else None

    if event_type:
        events = await pipeline.persistence.get_events_by_type(event_type, limit)
    elif start_dt and end_dt:
        events = await pipeline.persistence.get_events_in_timeframe(start_dt, end_dt)
    else:
        events = await pipeline.get_recent_events(limit)

    events_data = []
    for event in events:
        events_data.append({
            "id": event.id,
            "startTime": event.start_time.isoformat(),
            "endTime": event.end_time.isoformat(),
            "type": event.type.value,
            "summary": event.summary,
            "sourceDataCount": len(event.source_data)
        })

    return {
        "success": True,
        "data": {
            "events": events_data,
            "count": len(events_data),
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
async def get_activities(limit: int = 20) -> Dict[str, Any]:
    """Get processed activities.

    @param limit - Maximum number of activities to return (1-100)
    @returns Activities data with success flag and timestamp
    """
    from processing.pipeline import ProcessingPipeline

    pipeline = ProcessingPipeline()
    activities = await pipeline.get_recent_activities(limit)

    activities_data = []
    for activity in activities:
        activities_data.append({
            "id": activity["id"],
            "description": activity["description"],
            "startTime": activity["start_time"].isoformat() if isinstance(activity["start_time"], datetime) else activity["start_time"],
            "endTime": activity["end_time"].isoformat() if isinstance(activity["end_time"], datetime) else activity["end_time"],
            "eventCount": activity.get("event_count", 0),
            "createdAt": activity.get("created_at", datetime.now()).isoformat()
        })

    return {
        "success": True,
        "data": {
            "activities": activities_data,
            "count": len(activities_data),
            "filters": {
                "limit": limit,
            }
        },
        "timestamp": datetime.now().isoformat()
    }


@tauri_command()
async def get_event_by_id(event_id: str) -> Dict[str, Any]:
    """Get event details by ID.

    @param event_id - The event ID
    @returns Event details with success flag and timestamp
    """
    from processing.pipeline import ProcessingPipeline
    import json

    pipeline = ProcessingPipeline()

    # Get event from database
    events_data = pipeline.persistence.db.execute_query(
        "SELECT * FROM events WHERE id = ?",
        (event_id,)
    )

    if not events_data:
        return {
            "success": False,
            "error": "Event not found",
            "timestamp": datetime.now().isoformat()
        }

    event_data = events_data[0]

    # Parse source data
    source_data = []
    if event_data.get("source_data"):
        source_data_json = json.loads(event_data["source_data"]) if isinstance(event_data["source_data"], str) else event_data["source_data"]
        source_data = source_data_json

    event_detail = {
        "id": event_data["id"],
        "startTime": event_data["start_time"],
        "endTime": event_data["end_time"],
        "type": event_data["type"],
        "summary": event_data["summary"],
        "sourceData": source_data,
        "createdAt": event_data.get("created_at")
    }

    return {
        "success": True,
        "data": event_detail,
        "timestamp": datetime.now().isoformat()
    }


@tauri_command()
async def get_activity_by_id(activity_id: str) -> Dict[str, Any]:
    """Get activity details by ID.

    @param activity_id - The activity ID
    @returns Activity details with success flag and timestamp
    """
    from processing.pipeline import ProcessingPipeline
    import json

    pipeline = ProcessingPipeline()

    # Get activity from database
    activities_data = pipeline.persistence.db.execute_query(
        "SELECT * FROM activities WHERE id = ?",
        (activity_id,)
    )

    if not activities_data:
        return {
            "success": False,
            "error": "Activity not found",
            "timestamp": datetime.now().isoformat()
        }

    activity_data = activities_data[0]

    # Parse source events
    source_events = []
    if activity_data.get("source_events"):
        source_events_json = json.loads(activity_data["source_events"]) if isinstance(activity_data["source_events"], str) else activity_data["source_events"]
        source_events = source_events_json

    activity_detail = {
        "id": activity_data["id"],
        "description": activity_data["description"],
        "startTime": activity_data["start_time"],
        "endTime": activity_data["end_time"],
        "sourceEvents": source_events,
        "createdAt": activity_data.get("created_at")
    }

    return {
        "success": True,
        "data": activity_detail,
        "timestamp": datetime.now().isoformat()
    }


@tauri_command()
async def start_processing() -> Dict[str, Any]:
    """Start the processing pipeline.

    Begins processing raw records into events and activities.

    @returns Success response with message and timestamp
    """
    from processing.pipeline import ProcessingPipeline

    pipeline = ProcessingPipeline()
    await pipeline.start()

    return {
        "success": True,
        "message": "处理管道已启动",
        "timestamp": datetime.now().isoformat()
    }


@tauri_command()
async def stop_processing() -> Dict[str, Any]:
    """Stop the processing pipeline.

    Stops processing raw records.

    @returns Success response with message and timestamp
    """
    from processing.pipeline import ProcessingPipeline

    pipeline = ProcessingPipeline()
    await pipeline.stop()

    return {
        "success": True,
        "message": "处理管道已停止",
        "timestamp": datetime.now().isoformat()
    }


@tauri_command()
async def finalize_current_activity() -> Dict[str, Any]:
    """Force finalize the current activity.

    Forces the completion of the current activity being processed.

    @returns Success response with message and timestamp
    """
    from processing.pipeline import ProcessingPipeline

    pipeline = ProcessingPipeline()
    await pipeline.force_finalize_activity()

    return {
        "success": True,
        "message": "当前活动已强制完成",
        "timestamp": datetime.now().isoformat()
    }


@tauri_command()
async def cleanup_old_data(days: int = 30) -> Dict[str, Any]:
    """Clean up old data.

    @param days - Number of days to keep (1-365)
    @returns Cleanup result with success flag and timestamp
    """
    from processing.pipeline import ProcessingPipeline

    pipeline = ProcessingPipeline()
    result = await pipeline.persistence.delete_old_data(days)

    return {
        "success": True,
        "data": result,
        "message": f"已清理 {days} 天前的数据",
        "timestamp": datetime.now().isoformat()
    }


@tauri_command()
async def get_persistence_stats() -> Dict[str, Any]:
    """Get persistence statistics.

    Returns statistics about data persistence including database size and record counts.

    @returns Statistics data with success flag and timestamp
    """
    from processing.pipeline import ProcessingPipeline

    pipeline = ProcessingPipeline()
    stats = pipeline.persistence.get_stats()

    return {
        "success": True,
        "data": stats,
        "timestamp": datetime.now().isoformat()
    }
