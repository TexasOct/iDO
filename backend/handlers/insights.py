"""
Insights module command handlers (new architecture)
Insights module command handlers - handles events, knowledge, todos, diaries
"""

from datetime import datetime
from typing import Any, Dict, List

from core.coordinator import get_coordinator
from core.logger import get_logger
from models.requests import (
    DeleteItemRequest,
    GenerateDiaryRequest,
    GetDiaryListRequest,
    GetRecentEventsRequest,
    GetTodoListRequest,
    ScheduleTodoRequest,
    UnscheduleTodoRequest,
)

from . import api_handler

logger = get_logger(__name__)


def get_pipeline():
    """Get new architecture processing pipeline instance"""
    coordinator = get_coordinator()
    coordinator.ensure_managers_initialized()
    pipeline = getattr(coordinator, "processing_pipeline", None)

    if pipeline is None:
        logger.error("Failed to get processing pipeline instance")
        raise RuntimeError("processing pipeline not available")

    return pipeline


# ============ Event Related Interfaces ============


@api_handler(
    body=GetRecentEventsRequest,
    method="POST",
    path="/insights/recent-events",
    tags=["insights"],
    summary="Get recent events",
    description="Get recent N event records (supports pagination)",
)
async def get_recent_events(body: GetRecentEventsRequest) -> Dict[str, Any]:
    """Get recent events

    @param body - Request parameters including limit and offset
    @returns Event list and metadata
    """
    try:
        pipeline = get_pipeline()
        limit = body.limit if hasattr(body, "limit") else 50
        offset = body.offset if hasattr(body, "offset") else 0

        events = await pipeline.get_recent_events(limit, offset)

        return {
            "success": True,
            "data": {
                "events": events,
                "count": len(events),
            },
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to get recent events: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Failed to get recent events: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        }


# ============ Knowledge Related Interfaces ============


@api_handler(
    method="GET",
    path="/insights/knowledge",
    tags=["insights"],
    summary="Get knowledge list",
    description="Get all knowledge, prioritize returning combined_knowledge",
)
async def get_knowledge_list() -> Dict[str, Any]:
    """Get knowledge list

    @returns Knowledge list (prioritize returning combined)"""
    try:
        pipeline = get_pipeline()
        knowledge_list = await pipeline.get_knowledge_list()

        return {
            "success": True,
            "data": {
                "knowledge": knowledge_list,
                "count": len(knowledge_list),
            },
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to get knowledge list: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Failed to get knowledge list: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        }


@api_handler(
    body=DeleteItemRequest,
    method="POST",
    path="/insights/delete-knowledge",
    tags=["insights"],
    summary="Delete knowledge",
    description="Soft delete specified knowledge (including combined_knowledge)",
)
async def delete_knowledge(body: DeleteItemRequest) -> Dict[str, Any]:
    """Delete knowledge (soft delete)

    @param body - Contains knowledge ID to delete
    @returns Deletion result
    """
    try:
        pipeline = get_pipeline()
        await pipeline.delete_knowledge(body.id)

        return {
            "success": True,
            "message": "Knowledge deleted",
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to delete knowledge: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Failed to delete knowledge: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        }


# ============ Todo Related Interfaces ============


@api_handler(
    body=GetTodoListRequest,
    method="POST",
    path="/insights/todos",
    tags=["insights"],
    summary="Get todo list",
    description="Get all todos, prioritize returning combined_todos, optionally include completed",
)
async def get_todo_list(body: GetTodoListRequest) -> Dict[str, Any]:
    """Get todo list

    @param body - Request parameters, include include_completed
    @returns Todo list (prioritize returning combined)
    """
    try:
        pipeline = get_pipeline()
        include_completed = (
            body.include_completed if hasattr(body, "include_completed") else False
        )

        todo_list = await pipeline.get_todo_list(include_completed)

        return {
            "success": True,
            "data": {"todos": todo_list},
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to get todo list: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Failed to get todo list: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        }


@api_handler(
    body=DeleteItemRequest,
    method="POST",
    path="/insights/delete-todo",
    tags=["insights"],
    summary="Delete todo",
    description="Soft delete specified todo (including combined_todo)",
)
async def delete_todo(body: DeleteItemRequest) -> Dict[str, Any]:
    """Delete todo (soft delete)

    @param body - Contains todo ID to delete
    @returns Deletion result
    """
    try:
        pipeline = get_pipeline()
        await pipeline.delete_todo(body.id)

        return {
            "success": True,
            "message": "Todo deleted",
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to delete todo: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Failed to delete todo: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        }


@api_handler(
    body=ScheduleTodoRequest,
    method="POST",
    path="/insights/schedule-todo",
    tags=["insights"],
    summary="Schedule todo to a specific date",
    description="Set the scheduled_date for a todo",
)
async def schedule_todo(body: ScheduleTodoRequest) -> Dict[str, Any]:
    """Schedule todo to a specific date

    @param body - Contains todo ID and scheduled date
    @returns Updated todo
    """
    try:
        pipeline = get_pipeline()
        updated_todo = await pipeline.schedule_todo(body.todo_id, body.scheduled_date)

        if not updated_todo:
            return {
                "success": False,
                "message": "Todo not found",
                "timestamp": datetime.now().isoformat(),
            }

        return {
            "success": True,
            "data": updated_todo,
            "message": "Todo scheduled successfully",
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to schedule todo: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Failed to schedule todo: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        }


@api_handler(
    body=UnscheduleTodoRequest,
    method="POST",
    path="/insights/unschedule-todo",
    tags=["insights"],
    summary="Unschedule todo",
    description="Remove the scheduled_date from a todo",
)
async def unschedule_todo(body: UnscheduleTodoRequest) -> Dict[str, Any]:
    """Unschedule todo

    @param body - Contains todo ID
    @returns Updated todo
    """
    try:
        pipeline = get_pipeline()
        updated_todo = await pipeline.unschedule_todo(body.todo_id)

        if not updated_todo:
            return {
                "success": False,
                "message": "Todo not found",
                "timestamp": datetime.now().isoformat(),
            }

        return {
            "success": True,
            "data": updated_todo,
            "message": "Todo unscheduled successfully",
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to unschedule todo: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Failed to unschedule todo: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        }


# ============ Diary Related Interfaces ============


@api_handler(
    body=GenerateDiaryRequest,
    method="POST",
    path="/insights/generate-diary",
    tags=["insights"],
    summary="Generate diary",
    description="Generate diary for specified date based on all activities of that date",
)
async def generate_diary(body: GenerateDiaryRequest) -> Dict[str, Any]:
    """Generate diary

    @param body - Contains date (YYYY-MM-DD format)
    @returns Generated diary content
    """
    try:
        pipeline = get_pipeline()
        diary = await pipeline.generate_diary_for_date(body.date)

        if "error" in diary:
            return {
                "success": False,
                "message": diary["error"],
                "timestamp": datetime.now().isoformat(),
            }

        return {"success": True, "data": diary, "timestamp": datetime.now().isoformat()}

    except Exception as e:
        logger.error(f"Failed to generate diary: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Failed to generate diary: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        }


@api_handler(
    body=GetDiaryListRequest,
    method="POST",
    path="/insights/diaries",
    tags=["insights"],
    summary="Get diary list",
    description="Get recent diary records",
)
async def get_diary_list(body: GetDiaryListRequest) -> Dict[str, Any]:
    """Get diary list"""
    try:
        pipeline = get_pipeline()
        diaries = await pipeline.get_diary_list(body.limit)

        return {
            "success": True,
            "data": {"diaries": diaries, "count": len(diaries)},
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to get diary list: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Failed to get diary list: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        }


@api_handler(
    body=DeleteItemRequest,
    method="POST",
    path="/insights/delete-diary",
    tags=["insights"],
    summary="Delete diary",
    description="Delete specified diary",
)
async def delete_diary(body: DeleteItemRequest) -> Dict[str, Any]:
    """Delete diary

    @param body - Contains the diary ID to delete
    @returns Deletion result
    """
    try:
        pipeline = get_pipeline()
        await pipeline.delete_diary(body.id)

        return {
            "success": True,
            "message": "Diary deleted",
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to delete diary: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Failed to delete diary: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        }


# ============ Statistics Interface ============


@api_handler(
    method="GET",
    path="/insights/stats",
    tags=["insights"],
    summary="Get pipeline statistics",
    description="Get current pipeline runtime status and statistics data",
)
async def get_pipeline_stats() -> Dict[str, Any]:
    """Get pipeline statistics

    @returns pipeline runtime status and statistics data
    """
    try:
        pipeline = get_pipeline()
        stats = pipeline.get_stats()

        return {"success": True, "data": stats, "timestamp": datetime.now().isoformat()}

    except Exception as e:
        logger.error(f"Failed to get pipeline statistics: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Failed to get pipeline statistics: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        }


@api_handler(
    method="GET",
    path="/insights/event-count-by-date",
    tags=["insights"],
    summary="Get event count by date",
    description="Get total event count for each date in database",
)
async def get_event_count_by_date() -> Dict[str, Any]:
    """Get event count grouped by date

    @returns Event count statistics by date
    """
    try:
        pipeline = get_pipeline()
        date_counts = await pipeline.persistence.get_event_count_by_date()

        # Convert to map format: {"2025-01-15": 10, "2025-01-14": 5, ...}
        date_count_map = {item["date"]: item["count"] for item in date_counts}
        total_dates = len(date_count_map)
        total_events = sum(date_count_map.values())

        logger.debug(f"Event count by date: {total_dates} dates, {total_events} total events")

        return {
            "success": True,
            "data": {
                "dateCountMap": date_count_map,
                "totalDates": total_dates,
                "totalEvents": total_events
            },
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to get event count by date: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Failed to get event count by date: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        }


@api_handler(
    method="GET",
    path="/insights/knowledge-count-by-date",
    tags=["insights"],
    summary="Get knowledge count by date",
    description="Get total knowledge count for each date in database",
)
async def get_knowledge_count_by_date() -> Dict[str, Any]:
    """Get knowledge count grouped by date

    @returns Knowledge count statistics by date
    """
    try:
        pipeline = get_pipeline()
        date_counts = await pipeline.persistence.get_knowledge_count_by_date()

        # Convert to map format: {"2025-01-15": 10, "2025-01-14": 5, ...}
        date_count_map = {item["date"]: item["count"] for item in date_counts}
        total_dates = len(date_count_map)
        total_knowledge = sum(date_count_map.values())

        logger.debug(f"Knowledge count by date: {total_dates} dates, {total_knowledge} total knowledge")

        return {
            "success": True,
            "data": {
                "dateCountMap": date_count_map,
                "totalDates": total_dates,
                "totalKnowledge": total_knowledge
            },
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to get knowledge count by date: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Failed to get knowledge count by date: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        }
