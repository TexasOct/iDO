"""
ActivitiesV2 Repository - Handles all activity-related database operations
Activities are coarse-grained work sessions (NEW top layer)
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.logger import get_logger

from .base import BaseRepository

logger = get_logger(__name__)


class ActivitiesV2Repository(BaseRepository):
    """Repository for managing activities_v2 (work sessions) in the database"""

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
        session_duration_minutes: Optional[int] = None,
        topic_tags: Optional[List[str]] = None,
        user_merged_from_ids: Optional[List[str]] = None,
        user_split_into_ids: Optional[List[str]] = None,
    ) -> None:
        """Save or update an activity (work session)"""
        try:
            with self._get_conn() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO activities_v2 (
                        id, title, description, start_time, end_time,
                        source_event_ids, session_duration_minutes, topic_tags,
                        user_merged_from_ids, user_split_into_ids,
                        created_at, updated_at, deleted
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 0)
                    """,
                    (
                        activity_id,
                        title,
                        description,
                        start_time,
                        end_time,
                        json.dumps(source_event_ids),
                        session_duration_minutes,
                        json.dumps(topic_tags) if topic_tags else None,
                        json.dumps(user_merged_from_ids) if user_merged_from_ids else None,
                        json.dumps(user_split_into_ids) if user_split_into_ids else None,
                    ),
                )
                conn.commit()
                logger.debug(f"Saved activity_v2: {activity_id}")
        except Exception as e:
            logger.error(f"Failed to save activity_v2 {activity_id}: {e}", exc_info=True)
            raise

    async def update(
        self,
        activity_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        source_event_ids: Optional[List[str]] = None,
        topic_tags: Optional[List[str]] = None,
    ) -> None:
        """Update an existing activity"""
        try:
            updates = []
            params = []

            if title is not None:
                updates.append("title = ?")
                params.append(title)
            if description is not None:
                updates.append("description = ?")
                params.append(description)
            if source_event_ids is not None:
                updates.append("source_event_ids = ?")
                params.append(json.dumps(source_event_ids))
            if topic_tags is not None:
                updates.append("topic_tags = ?")
                params.append(json.dumps(topic_tags))

            if not updates:
                return

            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(activity_id)

            with self._get_conn() as conn:
                conn.execute(
                    f"UPDATE activities_v2 SET {', '.join(updates)} WHERE id = ?",
                    params,
                )
                conn.commit()
                logger.debug(f"Updated activity_v2: {activity_id}")

        except Exception as e:
            logger.error(f"Failed to update activity_v2 {activity_id}: {e}", exc_info=True)
            raise

    async def get_recent(
        self,
        limit: int = 50,
        offset: int = 0,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> List[Dict[str, Any]]:
        """Get recent activities with pagination and optional date filtering

        Args:
            limit: Maximum number of activities to return
            offset: Number of activities to skip
            start_date: Optional start date filter (YYYY-MM-DD format)
            end_date: Optional end date filter (YYYY-MM-DD format)
        """
        try:
            # Build WHERE clause
            where_clauses = ["deleted = 0"]
            params: list[str | int] = []

            if start_date:
                where_clauses.append("date(start_time) >= date(?)")
                params.append(start_date)

            if end_date:
                where_clauses.append("date(start_time) <= date(?)")
                params.append(end_date)

            where_clause = " AND ".join(where_clauses)

            # Add limit and offset
            params.extend([limit, offset])

            with self._get_conn() as conn:
                cursor = conn.execute(
                    f"""
                    SELECT id, title, description, start_time, end_time,
                           source_event_ids, session_duration_minutes, topic_tags,
                           user_merged_from_ids, user_split_into_ids,
                           created_at, updated_at
                    FROM activities_v2
                    WHERE {where_clause}
                    ORDER BY start_time DESC
                    LIMIT ? OFFSET ?
                    """,
                    tuple(params),
                )
                rows = cursor.fetchall()

            return [self._row_to_dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get recent activities_v2: {e}", exc_info=True)
            return []

    async def get_by_id(self, activity_id: str) -> Optional[Dict[str, Any]]:
        """Get activity by ID"""
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    SELECT id, title, description, start_time, end_time,
                           source_event_ids, session_duration_minutes, topic_tags,
                           user_merged_from_ids, user_split_into_ids,
                           created_at, updated_at
                    FROM activities_v2
                    WHERE id = ? AND deleted = 0
                    """,
                    (activity_id,),
                )
                row = cursor.fetchone()

            if not row:
                return None

            return self._row_to_dict(row)

        except Exception as e:
            logger.error(f"Failed to get activity_v2 {activity_id}: {e}", exc_info=True)
            return None

    async def get_by_date(
        self, start_date: str, end_date: str
    ) -> List[Dict[str, Any]]:
        """Get activities within a date range"""
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    SELECT id, title, description, start_time, end_time,
                           source_event_ids, session_duration_minutes, topic_tags,
                           user_merged_from_ids, user_split_into_ids,
                           created_at, updated_at
                    FROM activities_v2
                    WHERE deleted = 0
                      AND DATE(start_time) >= ?
                      AND DATE(start_time) <= ?
                    ORDER BY start_time DESC
                    """,
                    (start_date, end_date),
                )
                rows = cursor.fetchall()

            return [self._row_to_dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get activities_v2 by date: {e}", exc_info=True)
            return []

    async def get_all_source_event_ids(self) -> List[str]:
        """Return all event ids referenced by non-deleted activities"""
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    SELECT source_event_ids
                    FROM activities_v2
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

    async def record_user_merge(
        self, activity_id: str, merged_from_ids: List[str]
    ) -> None:
        """Record user manual merge operation for learning"""
        try:
            with self._get_conn() as conn:
                conn.execute(
                    """
                    UPDATE activities_v2
                    SET user_merged_from_ids = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (json.dumps(merged_from_ids), activity_id),
                )
                conn.commit()
                logger.debug(f"Recorded user merge for activity_v2: {activity_id}")

        except Exception as e:
            logger.error(f"Failed to record user merge: {e}", exc_info=True)
            raise

    async def record_user_split(
        self, activity_id: str, split_into_ids: List[str]
    ) -> None:
        """Record user manual split operation for learning"""
        try:
            with self._get_conn() as conn:
                conn.execute(
                    """
                    UPDATE activities_v2
                    SET user_split_into_ids = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (json.dumps(split_into_ids), activity_id),
                )
                conn.commit()
                logger.debug(f"Recorded user split for activity_v2: {activity_id}")

        except Exception as e:
            logger.error(f"Failed to record user split: {e}", exc_info=True)
            raise

    async def delete(self, activity_id: str) -> None:
        """Soft delete an activity"""
        try:
            with self._get_conn() as conn:
                conn.execute(
                    "UPDATE activities_v2 SET deleted = 1 WHERE id = ?", (activity_id,)
                )
                conn.commit()
                logger.debug(f"Deleted activity_v2: {activity_id}")
        except Exception as e:
            logger.error(
                f"Failed to delete activity_v2 {activity_id}: {e}", exc_info=True
            )
            raise

    async def mark_deleted(self, activity_id: str) -> None:
        """Alias for delete() - soft delete an activity"""
        await self.delete(activity_id)

    async def delete_by_date_range(self, start_iso: str, end_iso: str) -> int:
        """Soft delete activities inside the given timestamp window"""
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    UPDATE activities_v2
                    SET deleted = 1
                    WHERE deleted = 0
                      AND start_time >= ?
                      AND start_time <= ?
                    """,
                    (start_iso, end_iso),
                )
                conn.commit()
                logger.debug(
                    f"Deleted {cursor.rowcount} activities_v2 between {start_iso} and {end_iso}"
                )
                return cursor.rowcount

        except Exception as e:
            logger.error(
                f"Failed to delete activities_v2 between {start_iso} and {end_iso}: {e}",
                exc_info=True,
            )
            raise

    async def get_count_by_date(self) -> Dict[str, int]:
        """Get activity count grouped by date"""
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    SELECT DATE(start_time) as date, COUNT(*) as count
                    FROM activities_v2
                    WHERE deleted = 0
                    GROUP BY DATE(start_time)
                    ORDER BY date DESC
                    """
                )
                rows = cursor.fetchall()

            return {row["date"]: row["count"] for row in rows}

        except Exception as e:
            logger.error(
                f"Failed to get activity_v2 count by date: {e}", exc_info=True
            )
            return {}

    def _row_to_dict(self, row) -> Dict[str, Any]:
        """Convert database row to dictionary"""
        return {
            "id": row["id"],
            "title": row["title"],
            "description": row["description"],
            "start_time": row["start_time"],
            "end_time": row["end_time"],
            "source_event_ids": json.loads(row["source_event_ids"])
            if row["source_event_ids"]
            else [],
            "session_duration_minutes": row["session_duration_minutes"],
            "topic_tags": json.loads(row["topic_tags"]) if row["topic_tags"] else [],
            "user_merged_from_ids": json.loads(row["user_merged_from_ids"])
            if row["user_merged_from_ids"]
            else None,
            "user_split_into_ids": json.loads(row["user_split_into_ids"])
            if row["user_split_into_ids"]
            else None,
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
