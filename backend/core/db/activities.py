"""
Activities Repository - Handles all activity-related database operations
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.logger import get_logger

from .base import BaseRepository

logger = get_logger(__name__)


class ActivitiesRepository(BaseRepository):
    """Repository for managing activities in the database"""

    def __init__(self, db_path: Path):
        super().__init__(db_path)

    async def save(
        self,
        activity_id: str,
        title: str,
        description: str,
        start_time: str,
        end_time: str,
        source_event_ids: List[str],
    ) -> None:
        """Save or update an activity"""
        try:
            with self._get_conn() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO activities (
                        id, title, description, start_time, end_time,
                        source_event_ids, created_at, deleted
                    ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, 0)
                    """,
                    (
                        activity_id,
                        title,
                        description,
                        start_time,
                        end_time,
                        json.dumps(source_event_ids),
                    ),
                )
                conn.commit()
                logger.debug(f"Saved activity: {activity_id}")
        except Exception as e:
            logger.error(f"Failed to save activity {activity_id}: {e}", exc_info=True)
            raise

    async def get_recent(
        self, limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get recent activities with pagination"""
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    SELECT id, title, description, start_time, end_time,
                           source_event_ids, created_at
                    FROM activities
                    WHERE deleted = 0
                    ORDER BY start_time DESC
                    LIMIT ? OFFSET ?
                    """,
                    (limit, offset),
                )
                rows = cursor.fetchall()

            return [
                {
                    "id": row["id"],
                    "title": row["title"],
                    "description": row["description"],
                    "start_time": row["start_time"],
                    "end_time": row["end_time"],
                    "source_event_ids": json.loads(row["source_event_ids"])
                    if row["source_event_ids"]
                    else [],
                    "created_at": row["created_at"],
                }
                for row in rows
            ]

        except Exception as e:
            logger.error(f"Failed to get recent activities: {e}", exc_info=True)
            return []

    async def get_by_id(self, activity_id: str) -> Optional[Dict[str, Any]]:
        """Get activity by ID"""
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    SELECT id, title, description, start_time, end_time,
                           source_event_ids, created_at
                    FROM activities
                    WHERE id = ? AND deleted = 0
                    """,
                    (activity_id,),
                )
                row = cursor.fetchone()

            if not row:
                return None

            return {
                "id": row["id"],
                "title": row["title"],
                "description": row["description"],
                "start_time": row["start_time"],
                "end_time": row["end_time"],
                "source_event_ids": json.loads(row["source_event_ids"])
                if row["source_event_ids"]
                else [],
                "created_at": row["created_at"],
            }

        except Exception as e:
            logger.error(f"Failed to get activity {activity_id}: {e}", exc_info=True)
            return None

    async def get_by_date(
        self, start_date: str, end_date: str
    ) -> List[Dict[str, Any]]:
        """
        Get activities within a date range

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format

        Returns:
            List of activity dictionaries
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    SELECT id, title, description, start_time, end_time,
                           source_event_ids, created_at
                    FROM activities
                    WHERE deleted = 0
                      AND DATE(start_time) >= ?
                      AND DATE(start_time) <= ?
                    ORDER BY start_time DESC
                    """,
                    (start_date, end_date),
                )
                rows = cursor.fetchall()

            return [
                {
                    "id": row["id"],
                    "title": row["title"],
                    "description": row["description"],
                    "start_time": row["start_time"],
                    "end_time": row["end_time"],
                    "source_event_ids": json.loads(row["source_event_ids"])
                    if row["source_event_ids"]
                    else [],
                    "created_at": row["created_at"],
                }
                for row in rows
            ]

        except Exception as e:
            logger.error(f"Failed to get activities by date: {e}", exc_info=True)
            return []

    async def get_all_source_event_ids(self) -> List[str]:
        """Return all event ids referenced by non-deleted activities"""
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    SELECT source_event_ids
                    FROM activities
                    WHERE deleted = 0
                    """
                )
                rows = cursor.fetchall()

            aggregated_ids: List[str] = []
            for row in rows:
                if not row["source_event_ids"]:
                    continue
                try:
                    aggregated_ids.extend(json.loads(row["source_event_ids"]))
                except (TypeError, json.JSONDecodeError):
                    continue

            return aggregated_ids

        except Exception as e:
            logger.error(
                f"Failed to load aggregated activity event ids: {e}", exc_info=True
            )
            return []

    async def delete(self, activity_id: str) -> None:
        """Soft delete an activity"""
        try:
            with self._get_conn() as conn:
                conn.execute(
                    "UPDATE activities SET deleted = 1 WHERE id = ?", (activity_id,)
                )
                conn.commit()
                logger.debug(f"Deleted activity: {activity_id}")
        except Exception as e:
            logger.error(
                f"Failed to delete activity {activity_id}: {e}", exc_info=True
            )
            raise

    async def delete_by_date_range(self, start_iso: str, end_iso: str) -> int:
        """Soft delete activities inside the given timestamp window"""
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    UPDATE activities
                    SET deleted = 1
                    WHERE deleted = 0
                      AND start_time >= ?
                      AND start_time <= ?
                    """,
                    (start_iso, end_iso),
                )
                conn.commit()
                return cursor.rowcount

        except Exception as e:
            logger.error(
                f"Failed to delete activities between {start_iso} and {end_iso}: {e}",
                exc_info=True,
            )
            return 0

    async def get_count_by_date(self) -> Dict[str, int]:
        """Get activity count grouped by date"""
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    SELECT DATE(start_time) as date, COUNT(*) as count
                    FROM activities
                    WHERE deleted = 0
                    GROUP BY DATE(start_time)
                    ORDER BY date DESC
                    """
                )
                rows = cursor.fetchall()

            return {row["date"]: row["count"] for row in rows}

        except Exception as e:
            logger.error(
                f"Failed to get activity count by date: {e}", exc_info=True
            )
            return {}
