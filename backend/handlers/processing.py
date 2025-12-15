"""
Processing pipeline control and data cleanup handlers.

Handles processing pipeline control operations and batch data cleanup including:
- Start/stop processing pipeline
- Finalize current activity
- Get processing and persistence statistics
- Cleanup old data (activities, events, etc.)
- Delete knowledge, todos, and diaries by date range
"""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

from core.coordinator import get_coordinator
from core.db import DatabaseManager, get_db
from core.logger import get_logger
from models import (
    CleanupOldDataRequest,
    DataResponse,
    DeleteDiariesByDateRequest,
    DeleteKnowledgeByDateRequest,
    DeleteTodosByDateRequest,
    TimedOperationResponse,
)
from perception.image_manager import ImageManager, get_image_manager
from processing.pipeline import ProcessingPipeline

from . import api_handler

logger = get_logger(__name__)
_fallback_image_manager: Optional[ImageManager] = None


def _get_pipeline():
    """Get processing pipeline from coordinator.

    @returns Tuple of (ProcessingPipeline, Coordinator)
    """
    coordinator = get_coordinator()
    return coordinator.processing_pipeline, coordinator


def _get_data_access() -> Tuple[DatabaseManager, ImageManager, Optional[ProcessingPipeline], Any]:
    """Get database and related objects.

    Returns database manager, image manager, processing pipeline (if available),
    and coordinator instance. Falls back to standalone instances if pipeline
    is not initialized.

    @returns Tuple of (DatabaseManager, ImageManager, ProcessingPipeline|None, Coordinator)
    """
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


def _calculate_persistence_stats(db: DatabaseManager) -> Dict[str, Any]:
    """Calculate persistence statistics.

    Retrieves table counts and database size information.

    @param db - Database manager instance
    @returns Dictionary containing statistics or error information
    """
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
    """Helper for deleting old data.

    Args:
        db: Database manager instance
        days: Number of days to keep (delete older data)

    Returns:
        Dictionary with deletion results or error
    """
    try:
        cutoff = datetime.now() - timedelta(days=days)
        cutoff_iso = cutoff.isoformat()

        return await db.delete_old_data(cutoff_iso, cutoff.strftime("%Y-%m-%d"))

    except Exception as exc:
        logger.error("Failed to clean up old data: %s", exc)
        return {"error": str(exc)}


# Processing Control


@api_handler()
async def get_processing_stats() -> TimedOperationResponse:
    """Get processing module statistics.

    Returns statistics about event and activity processing.

    @returns Statistics data with success flag and timestamp
    """
    coordinator = get_coordinator()
    stats = coordinator.get_stats()

    return DataResponse(
        success=True, data=stats, timestamp=datetime.now().isoformat()
    )


@api_handler()
async def get_persistence_stats() -> DataResponse:
    """Get persistence statistics.

    Returns statistics about data persistence including database size and record counts.

    @returns Statistics data with success flag and timestamp
    """
    db, _, _, _ = _get_data_access()
    stats = _calculate_persistence_stats(db)

    return DataResponse(
        success=True, data=stats, timestamp=datetime.now().isoformat()
    )


@api_handler()
async def start_processing() -> TimedOperationResponse:
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
        return TimedOperationResponse(
            success=False,
            message=message,
            timestamp=datetime.now().isoformat(),
        )

    await pipeline.start()

    return TimedOperationResponse(success=True, message="Processing pipeline started", timestamp=datetime.now().isoformat())


@api_handler()
async def stop_processing() -> TimedOperationResponse:
    """Stop the processing pipeline.

    Stops processing raw records.

    @returns Success response with message and timestamp
    """
    pipeline, coordinator = _get_pipeline()
    if not pipeline:
        logger.debug(
            "stop_processing called with uninitialized processing pipeline, considered as stopped"
        )
        return TimedOperationResponse(success=True, message="Processing pipeline not running", timestamp=datetime.now().isoformat())

    await pipeline.stop()

    return TimedOperationResponse(success=True, message="Processing pipeline stopped", timestamp=datetime.now().isoformat())


@api_handler()
async def finalize_current_activity() -> TimedOperationResponse:
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
        return TimedOperationResponse(
            success=False,
            message=message,
            timestamp=datetime.now().isoformat(),
        )

    await pipeline.force_finalize_activity()

    return TimedOperationResponse(success=True, message="Current activity forcefully completed", timestamp=datetime.now().isoformat())


# Data Cleanup


@api_handler(body=CleanupOldDataRequest)
async def cleanup_old_data(body: CleanupOldDataRequest) -> TimedOperationResponse:
    """Clean up old data.

    Deletes activities, events, and other data older than specified days.

    @param body - Request parameters including number of days to keep.
    @returns Cleanup result with success flag and timestamp
    """
    db, _, pipeline, _ = _get_data_access()

    # Use database delete_old_data method directly
    _result = await _delete_old_data(db, body.days)

    return DataResponse(
        success=True,
        message=f"Cleaned data from {body.days} days ago",
        timestamp=datetime.now().isoformat(),
    )


@api_handler(
    body=DeleteKnowledgeByDateRequest,
    method="DELETE",
    path="/knowledge/delete-by-date",
    tags=["insights"],
)
async def delete_knowledge_by_date(
    body: DeleteKnowledgeByDateRequest,
) -> TimedOperationResponse:
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
            return DataResponse(
                success=False,
                error="Start date cannot be after end date",
                timestamp=datetime.now().isoformat(),
            )

        deleted_count = await db.knowledge.delete_by_date_range(
            start_dt.isoformat(),
            datetime.combine(end_dt, datetime.max.time()).isoformat(),
        )

        logger.debug(
            f"Batch delete knowledge: {deleted_count} items deleted between {body.start_date} and {body.end_date}"
        )

        return TimedOperationResponse(
            success=True,
            message=f"Successfully deleted {deleted_count} knowledge records",
            data={
                "deleted_count": deleted_count,
                "start_date": body.start_date,
                "end_date": body.end_date,
            },
            timestamp=datetime.now().isoformat(),
        )
    except Exception as e:
        logger.error(f"Failed to delete knowledge by date range: {e}", exc_info=True)
        return DataResponse(
            success=False,
            message=f"Failed to delete knowledge: {str(e)}",
            timestamp=datetime.now().isoformat(),
        )


@api_handler(
    body=DeleteTodosByDateRequest,
    method="DELETE",
    path="/todos/delete-by-date",
    tags=["insights"],
)
async def delete_todos_by_date(body: DeleteTodosByDateRequest) -> TimedOperationResponse:
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
            return DataResponse(
                success=False,
                error="Start date cannot be after end date",
                timestamp=datetime.now().isoformat(),
            )

        deleted_count = await db.todos.delete_by_date_range(
            start_dt.isoformat(),
            datetime.combine(end_dt, datetime.max.time()).isoformat(),
        )

        logger.debug(
            f"Batch delete todos: {deleted_count} items deleted between {body.start_date} and {body.end_date}"
        )

        return TimedOperationResponse(
            success=True,
            message=f"Successfully deleted {deleted_count} todos",
            data={
                "deleted_count": deleted_count,
                "start_date": body.start_date,
                "end_date": body.end_date,
            },
            timestamp=datetime.now().isoformat(),
        )
    except Exception as e:
        logger.error(f"Failed to delete todos by date range: {e}", exc_info=True)
        return DataResponse(
            success=False,
            message=f"Failed to delete todos: {str(e)}",
            timestamp=datetime.now().isoformat(),
        )


@api_handler(
    body=DeleteDiariesByDateRequest,
    method="DELETE",
    path="/diaries/delete-by-date",
    tags=["insights"],
)
async def delete_diaries_by_date(body: DeleteDiariesByDateRequest) -> TimedOperationResponse:
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
            return DataResponse(
                success=False,
                error="Start date cannot be after end date",
                timestamp=datetime.now().isoformat(),
            )

        deleted_count = await db.diaries.delete_by_date_range(
            body.start_date, body.end_date
        )

        logger.debug(
            f"Batch delete diaries: {deleted_count} items deleted between {body.start_date} and {body.end_date}"
        )

        return DataResponse(
            success=True,
            message=f"Successfully deleted {deleted_count} diaries",
            data={
                "deleted_count": deleted_count,
                "start_date": body.start_date,
                "end_date": body.end_date,
            },
            timestamp=datetime.now().isoformat(),
        )
    except Exception as e:
        logger.error(f"Failed to delete diaries by date range: {e}", exc_info=True)
        return DataResponse(
            success=False,
            message=f"Failed to delete diaries: {str(e)}",
            timestamp=datetime.now().isoformat(),
        )
