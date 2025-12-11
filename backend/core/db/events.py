"""
EventsV2 Repository - Handles all event-related database operations
Events are medium-grained activity segments (formerly Activities)
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.logger import get_logger

from .base import BaseRepository

logger = get_logger(__name__)


class EventsRepository(BaseRepository):
    """Repository for managing events_v2 in the database"""

    def __init__(self, db_path: Path):
        super().__init__(db_path)

    async def save(
        self,
        event_id: str,
        title: str,
        description: str,
        start_time: str,
        end_time: str,
        source_action_ids: List[str],
        version: int = 1,
    ) -> None:
        """Save or update an event"""
        try:
            with self._get_conn() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO events_v2 (
                        id, title, description, start_time, end_time,
                        source_action_ids, version, created_at, deleted
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, 0)
                    """,
                    (
                        event_id,
                        title,
                        description,
                        start_time,
                        end_time,
                        json.dumps(source_action_ids),
                        version,
                    ),
                )
                conn.commit()
                logger.debug(f"Saved event_v2: {event_id}")
        except Exception as e:
            logger.error(f"Failed to save event_v2 {event_id}: {e}", exc_info=True)
            raise

    async def get_recent(
        self, limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get recent events with pagination"""
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    SELECT id, title, description, start_time, end_time,
                           source_action_ids, aggregated_into_activity_id, version, created_at
                    FROM events_v2
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
                    "source_action_ids": json.loads(row["source_action_ids"])
                    if row["source_action_ids"]
                    else [],
                    "aggregated_into_activity_id": row["aggregated_into_activity_id"],
                    "version": row["version"],
                    "created_at": row["created_at"],
                }
                for row in rows
            ]

        except Exception as e:
            logger.error(f"Failed to get recent events_v2: {e}", exc_info=True)
            return []

    async def get_by_id(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Get event by ID"""
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    SELECT id, title, description, start_time, end_time,
                           source_action_ids, aggregated_into_activity_id, version, created_at
                    FROM events_v2
                    WHERE id = ? AND deleted = 0
                    """,
                    (event_id,),
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
                "source_action_ids": json.loads(row["source_action_ids"])
                if row["source_action_ids"]
                else [],
                "aggregated_into_activity_id": row["aggregated_into_activity_id"],
                "version": row["version"],
                "created_at": row["created_at"],
            }

        except Exception as e:
            logger.error(f"Failed to get event_v2 {event_id}: {e}", exc_info=True)
            return None

    async def get_by_ids(self, event_ids: List[str]) -> List[Dict[str, Any]]:
        """Get multiple events by their IDs"""
        if not event_ids:
            return []

        try:
            placeholders = ",".join("?" * len(event_ids))
            with self._get_conn() as conn:
                cursor = conn.execute(
                    f"""
                    SELECT id, title, description, start_time, end_time,
                           source_action_ids, aggregated_into_activity_id, version, created_at
                    FROM events_v2
                    WHERE id IN ({placeholders}) AND deleted = 0
                    ORDER BY start_time DESC
                    """,
                    event_ids,
                )
                rows = cursor.fetchall()

            return [
                {
                    "id": row["id"],
                    "title": row["title"],
                    "description": row["description"],
                    "start_time": row["start_time"],
                    "end_time": row["end_time"],
                    "source_action_ids": json.loads(row["source_action_ids"])
                    if row["source_action_ids"]
                    else [],
                    "aggregated_into_activity_id": row["aggregated_into_activity_id"],
                    "version": row["version"],
                    "created_at": row["created_at"],
                }
                for row in rows
            ]

        except Exception as e:
            logger.error(f"Failed to get events_v2 by IDs: {e}", exc_info=True)
            return []

    async def get_in_timeframe(
        self, start_time: str, end_time: str
    ) -> List[Dict[str, Any]]:
        """Get events within a time window"""
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    SELECT id, title, description, start_time, end_time,
                           source_action_ids, aggregated_into_activity_id, version, created_at
                    FROM events_v2
                    WHERE start_time >= ? AND start_time <= ?
                      AND deleted = 0
                    ORDER BY start_time ASC
                    """,
                    (start_time, end_time),
                )
                rows = cursor.fetchall()

            return [
                {
                    "id": row["id"],
                    "title": row["title"],
                    "description": row["description"],
                    "start_time": row["start_time"],
                    "end_time": row["end_time"],
                    "source_action_ids": json.loads(row["source_action_ids"])
                    if row["source_action_ids"]
                    else [],
                    "aggregated_into_activity_id": row["aggregated_into_activity_id"],
                    "version": row["version"],
                    "created_at": row["created_at"],
                }
                for row in rows
            ]

        except Exception as e:
            logger.error(f"Failed to get events_v2 in timeframe: {e}", exc_info=True)
            return []

    async def get_by_date(
        self, start_date: str, end_date: str
    ) -> List[Dict[str, Any]]:
        """
        Get events within a date range

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format

        Returns:
            List of event dictionaries
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    SELECT id, title, description, start_time, end_time,
                           source_action_ids, aggregated_into_activity_id, version, created_at
                    FROM events_v2
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
                    "source_action_ids": json.loads(row["source_action_ids"])
                    if row["source_action_ids"]
                    else [],
                    "aggregated_into_activity_id": row["aggregated_into_activity_id"],
                    "version": row["version"],
                    "created_at": row["created_at"],
                }
                for row in rows
            ]

        except Exception as e:
            logger.error(f"Failed to get events_v2 by date: {e}", exc_info=True)
            return []

    async def get_all_source_action_ids(self) -> List[str]:
        """Return all action ids referenced by non-deleted events"""
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    SELECT source_action_ids
                    FROM events_v2
                    WHERE deleted = 0
                    """
                )
                rows = cursor.fetchall()

            aggregated_ids: List[str] = []
            for row in rows:
                if not row["source_action_ids"]:
                    continue
                try:
                    aggregated_ids.extend(json.loads(row["source_action_ids"]))
                except (TypeError, json.JSONDecodeError):
                    continue

            return aggregated_ids

        except Exception as e:
            logger.error(
                f"Failed to load aggregated event action ids: {e}", exc_info=True
            )
            return []

    async def mark_as_aggregated(
        self, event_ids: List[str], activity_id: str
    ) -> None:
        """
        Mark events as aggregated into an activity

        Args:
            event_ids: List of event IDs to mark
            activity_id: The activity ID they were aggregated into
        """
        if not event_ids:
            return

        try:
            placeholders = ",".join("?" * len(event_ids))
            with self._get_conn() as conn:
                conn.execute(
                    f"""
                    UPDATE events_v2
                    SET aggregated_into_activity_id = ?
                    WHERE id IN ({placeholders})
                    """,
                    [activity_id] + event_ids,
                )
                conn.commit()
                logger.debug(
                    f"Marked {len(event_ids)} events as aggregated into activity {activity_id}"
                )

        except Exception as e:
            logger.error(f"Failed to mark events as aggregated: {e}", exc_info=True)
            raise

    async def delete(self, event_id: str) -> None:
        """Soft delete an event"""
        try:
            with self._get_conn() as conn:
                conn.execute(
                    "UPDATE events_v2 SET deleted = 1 WHERE id = ?", (event_id,)
                )
                conn.commit()
                logger.debug(f"Deleted event_v2: {event_id}")
        except Exception as e:
            logger.error(
                f"Failed to delete event_v2 {event_id}: {e}", exc_info=True
            )
            raise

    async def get_screenshots(self, event_id: str) -> List[str]:
        """Return screenshot hashes for all actions referenced by the event"""
        event = await self.get_by_id(event_id)
        if not event:
            return []

        action_ids = event.get("source_action_ids") or []
        if not action_ids:
            return []

        try:
            placeholders = ",".join("?" * len(action_ids))
            with self._get_conn() as conn:
                cursor = conn.execute(
                    f"""
                    SELECT hash
                    FROM action_images
                    WHERE action_id IN ({placeholders})
                    ORDER BY created_at ASC
                    """,
                    action_ids,
                )
                rows = cursor.fetchall()

            # Deduplicate while preserving order
            seen: set[str] = set()
            hashes: List[str] = []
            for row in rows:
                hash_value = row["hash"]
                if hash_value and hash_value.strip() and hash_value not in seen:
                    seen.add(hash_value)
                    hashes.append(hash_value)
            return hashes

        except Exception as e:
            logger.error(f"Failed to load screenshots for event {event_id}: {e}", exc_info=True)
            return []

    async def get_count_by_date(self) -> Dict[str, int]:
        """Get event count grouped by date"""
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    SELECT DATE(start_time) as date, COUNT(*) as count
                    FROM events_v2
                    WHERE deleted = 0
                    GROUP BY DATE(start_time)
                    ORDER BY date DESC
                    """
                )
                rows = cursor.fetchall()

            return {row["date"]: row["count"] for row in rows}

        except Exception as e:
            logger.error(
                f"Failed to get event_v2 count by date: {e}", exc_info=True
            )
            return {}
