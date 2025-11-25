"""
Events Repository - Handles all event-related database operations
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.logger import get_logger
from core.sqls import queries

from .base import BaseRepository

logger = get_logger(__name__)


class EventsRepository(BaseRepository):
    """Repository for managing events in the database"""

    def __init__(self, db_path: Path):
        super().__init__(db_path)

    async def save(
        self,
        event_id: str,
        title: str,
        description: str,
        keywords: List[str],
        timestamp: str,
        screenshots: Optional[List[str]] = None,
    ) -> None:
        """
        Save or update an event

        Args:
            event_id: Unique event identifier
            title: Event title
            description: Event description
            keywords: List of keywords
            timestamp: Event timestamp
            screenshots: Optional list of screenshot hashes
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    INSERT OR REPLACE INTO events (
                        id, title, description, keywords, timestamp, deleted, created_at
                    ) VALUES (?, ?, ?, ?, ?, 0, CURRENT_TIMESTAMP)
                    """,
                    (
                        event_id,
                        title,
                        description,
                        json.dumps(keywords, ensure_ascii=False),
                        timestamp,
                    ),
                )

                unique_hashes: List[str] = []
                if screenshots:
                    seen = set()
                    for screenshot_hash in screenshots:
                        if screenshot_hash and screenshot_hash not in seen:
                            unique_hashes.append(screenshot_hash)
                            seen.add(screenshot_hash)
                        if len(unique_hashes) >= 6:
                            break

                    cursor.execute(
                        "DELETE FROM event_images WHERE event_id = ?", (event_id,)
                    )

                    for screenshot_hash in unique_hashes:
                        cursor.execute(
                            """
                            INSERT OR IGNORE INTO event_images (event_id, hash, created_at)
                            VALUES (?, ?, CURRENT_TIMESTAMP)
                            """,
                            (event_id, screenshot_hash),
                        )

                conn.commit()
                logger.debug(f"Saved event: {event_id}")

        except Exception as e:
            logger.error(f"Failed to save event {event_id}: {e}", exc_info=True)
            raise

    async def get_recent(
        self, limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get recent events with pagination

        Args:
            limit: Maximum number of events to return
            offset: Number of events to skip

        Returns:
            List of event dictionaries
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    SELECT id, title, description, keywords, timestamp, created_at
                    FROM events
                    WHERE deleted = 0
                    ORDER BY timestamp DESC
                    LIMIT ? OFFSET ?
                    """,
                    (limit, offset),
                )
                rows = cursor.fetchall()

            events = []
            for row in rows:
                event = {
                    "id": row["id"],
                    "title": row["title"],
                    "description": row["description"],
                    "keywords": json.loads(row["keywords"])
                    if row["keywords"]
                    else [],
                    "timestamp": row["timestamp"],
                    "created_at": row["created_at"],
                }

                # Get screenshots for this event
                event["screenshots"] = await self._load_screenshots(row["id"])
                events.append(event)

            return events

        except Exception as e:
            logger.error(f"Failed to get recent events: {e}", exc_info=True)
            return []

    async def get_by_id(self, event_id: str) -> Optional[Dict[str, Any]]:
        """
        Get event by ID

        Args:
            event_id: Event identifier

        Returns:
            Event dictionary or None if not found
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    SELECT id, title, description, keywords, timestamp, created_at
                    FROM events
                    WHERE id = ? AND deleted = 0
                    """,
                    (event_id,),
                )
                row = cursor.fetchone()

            if not row:
                return None

            event = {
                "id": row["id"],
                "title": row["title"],
                "description": row["description"],
                "keywords": json.loads(row["keywords"]) if row["keywords"] else [],
                "timestamp": row["timestamp"],
                "created_at": row["created_at"],
            }

            # Get screenshots for this event
            event["screenshots"] = await self._load_screenshots(row["id"])
            return event

        except Exception as e:
            logger.error(f"Failed to get event {event_id}: {e}", exc_info=True)
            return None

    async def get_by_ids(self, event_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Get multiple events by their IDs

        Args:
            event_ids: List of event identifiers

        Returns:
            List of event dictionaries
        """
        if not event_ids:
            return []

        try:
            placeholders = ",".join("?" * len(event_ids))
            with self._get_conn() as conn:
                cursor = conn.execute(
                    f"""
                    SELECT id, title, description, keywords, timestamp, created_at
                    FROM events
                    WHERE id IN ({placeholders}) AND deleted = 0
                    ORDER BY timestamp DESC
                    """,
                    event_ids,
                )
                rows = cursor.fetchall()

            events = []
            for row in rows:
                event = {
                    "id": row["id"],
                    "title": row["title"],
                    "description": row["description"],
                    "keywords": json.loads(row["keywords"])
                    if row["keywords"]
                    else [],
                    "timestamp": row["timestamp"],
                    "created_at": row["created_at"],
                }
                event["screenshots"] = await self._load_screenshots(row["id"])
                events.append(event)

            return events

        except Exception as e:
            logger.error(f"Failed to get events by IDs: {e}", exc_info=True)
            return []

    async def get_in_timeframe(
        self, start_time: str, end_time: str
    ) -> List[Dict[str, Any]]:
        """
        Get events within a time window

        Args:
            start_time: ISO timestamp lower bound (inclusive)
            end_time: ISO timestamp upper bound (inclusive)

        Returns:
            List of event dictionaries
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    SELECT id, title, description, keywords, timestamp, created_at
                    FROM events
                    WHERE timestamp >= ? AND timestamp <= ?
                      AND deleted = 0
                    ORDER BY timestamp ASC
                    """,
                    (start_time, end_time),
                )
                rows = cursor.fetchall()

            events: List[Dict[str, Any]] = []
            for row in rows:
                event = {
                    "id": row["id"],
                    "title": row["title"],
                    "description": row["description"],
                    "keywords": json.loads(row["keywords"])
                    if row["keywords"]
                    else [],
                    "timestamp": row["timestamp"],
                    "created_at": row["created_at"],
                }
                event["screenshots"] = await self._load_screenshots(row["id"])
                events.append(event)

            return events

        except Exception as e:
            logger.error(f"Failed to get events in timeframe: {e}", exc_info=True)
            return []

    async def delete(self, event_id: str) -> None:
        """
        Soft delete an event

        Args:
            event_id: Event identifier
        """
        try:
            with self._get_conn() as conn:
                conn.execute(
                    "UPDATE events SET deleted = 1 WHERE id = ?", (event_id,)
                )
                conn.commit()
                logger.debug(f"Deleted event: {event_id}")

        except Exception as e:
            logger.error(f"Failed to delete event {event_id}: {e}", exc_info=True)
            raise

    async def get_count_by_date(self) -> Dict[str, int]:
        """
        Get event count grouped by date

        Returns:
            Dictionary mapping date (YYYY-MM-DD) to event count
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    SELECT DATE(timestamp) as date, COUNT(*) as count
                    FROM events
                    WHERE deleted = 0
                    GROUP BY DATE(timestamp)
                    ORDER BY date DESC
                    """
                )
                rows = cursor.fetchall()

            return {row["date"]: row["count"] for row in rows}

        except Exception as e:
            logger.error(f"Failed to get event count by date: {e}", exc_info=True)
            return {}

    async def get_screenshots(self, event_id: str) -> List[str]:
        """Expose screenshot hashes for a specific event"""
        return await self._load_screenshots(event_id)

    async def _load_screenshots(self, event_id: str) -> List[str]:
        """
        Load screenshots for an event

        Args:
            event_id: Event identifier

        Returns:
            List of screenshot hashes
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    queries.SELECT_EVENT_IMAGE_HASHES, (event_id,)
                )
                rows = cursor.fetchall()

            return [row["hash"] for row in rows if row["hash"] and row["hash"].strip()]

        except Exception as e:
            logger.error(
                f"Failed to load screenshots for event {event_id}: {e}",
                exc_info=True,
            )
            return []
