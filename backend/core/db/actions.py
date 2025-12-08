"""
Actions Repository - Handles all action-related database operations
Actions are fine-grained operations extracted from screenshots (formerly Events)
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.logger import get_logger
from core.sqls import queries

from .base import BaseRepository

logger = get_logger(__name__)


class ActionsRepository(BaseRepository):
    """Repository for managing actions in the database"""

    def __init__(self, db_path: Path):
        super().__init__(db_path)

    async def save(
        self,
        action_id: str,
        title: str,
        description: str,
        keywords: List[str],
        timestamp: str,
        screenshots: Optional[List[str]] = None,
    ) -> None:
        """
        Save or update an action

        Args:
            action_id: Unique action identifier
            title: Action title
            description: Action description
            keywords: List of keywords
            timestamp: Action timestamp
            screenshots: Optional list of screenshot hashes
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    INSERT OR REPLACE INTO actions (
                        id, title, description, keywords, timestamp, deleted, created_at
                    ) VALUES (?, ?, ?, ?, ?, 0, CURRENT_TIMESTAMP)
                    """,
                    (
                        action_id,
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
                        "DELETE FROM action_images WHERE action_id = ?", (action_id,)
                    )

                    for screenshot_hash in unique_hashes:
                        cursor.execute(
                            """
                            INSERT OR IGNORE INTO action_images (action_id, hash, created_at)
                            VALUES (?, ?, CURRENT_TIMESTAMP)
                            """,
                            (action_id, screenshot_hash),
                        )

                conn.commit()
                logger.debug(f"Saved action: {action_id}")

        except Exception as e:
            logger.error(f"Failed to save action {action_id}: {e}", exc_info=True)
            raise

    async def get_recent(
        self, limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get recent actions with pagination

        Args:
            limit: Maximum number of actions to return
            offset: Number of actions to skip

        Returns:
            List of action dictionaries
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    SELECT id, title, description, keywords, timestamp, aggregated_into_event_id, created_at
                    FROM actions
                    WHERE deleted = 0
                    ORDER BY timestamp DESC
                    LIMIT ? OFFSET ?
                    """,
                    (limit, offset),
                )
                rows = cursor.fetchall()

            actions = []
            for row in rows:
                action = {
                    "id": row["id"],
                    "title": row["title"],
                    "description": row["description"],
                    "keywords": json.loads(row["keywords"])
                    if row["keywords"]
                    else [],
                    "timestamp": row["timestamp"],
                    "aggregated_into_event_id": row["aggregated_into_event_id"],
                    "created_at": row["created_at"],
                }

                # Get screenshots for this action
                action["screenshots"] = await self._load_screenshots(row["id"])
                actions.append(action)

            return actions

        except Exception as e:
            logger.error(f"Failed to get recent actions: {e}", exc_info=True)
            return []

    async def get_by_id(self, action_id: str) -> Optional[Dict[str, Any]]:
        """
        Get action by ID

        Args:
            action_id: Action identifier

        Returns:
            Action dictionary or None if not found
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    SELECT id, title, description, keywords, timestamp, aggregated_into_event_id, created_at
                    FROM actions
                    WHERE id = ? AND deleted = 0
                    """,
                    (action_id,),
                )
                row = cursor.fetchone()

            if not row:
                return None

            action = {
                "id": row["id"],
                "title": row["title"],
                "description": row["description"],
                "keywords": json.loads(row["keywords"]) if row["keywords"] else [],
                "timestamp": row["timestamp"],
                "aggregated_into_event_id": row["aggregated_into_event_id"],
                "created_at": row["created_at"],
            }

            # Get screenshots for this action
            action["screenshots"] = await self._load_screenshots(row["id"])
            return action

        except Exception as e:
            logger.error(f"Failed to get action {action_id}: {e}", exc_info=True)
            return None

    async def get_by_ids(self, action_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Get multiple actions by their IDs

        Args:
            action_ids: List of action identifiers

        Returns:
            List of action dictionaries
        """
        if not action_ids:
            return []

        try:
            placeholders = ",".join("?" * len(action_ids))
            with self._get_conn() as conn:
                cursor = conn.execute(
                    f"""
                    SELECT id, title, description, keywords, timestamp, aggregated_into_event_id, created_at
                    FROM actions
                    WHERE id IN ({placeholders}) AND deleted = 0
                    ORDER BY timestamp DESC
                    """,
                    action_ids,
                )
                rows = cursor.fetchall()

            actions = []
            for row in rows:
                action = {
                    "id": row["id"],
                    "title": row["title"],
                    "description": row["description"],
                    "keywords": json.loads(row["keywords"])
                    if row["keywords"]
                    else [],
                    "timestamp": row["timestamp"],
                    "aggregated_into_event_id": row["aggregated_into_event_id"],
                    "created_at": row["created_at"],
                }
                action["screenshots"] = await self._load_screenshots(row["id"])
                actions.append(action)

            return actions

        except Exception as e:
            logger.error(f"Failed to get actions by IDs: {e}", exc_info=True)
            return []

    async def get_in_timeframe(
        self, start_time: str, end_time: str
    ) -> List[Dict[str, Any]]:
        """
        Get actions within a time window

        Args:
            start_time: ISO timestamp lower bound (inclusive)
            end_time: ISO timestamp upper bound (inclusive)

        Returns:
            List of action dictionaries
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    SELECT id, title, description, keywords, timestamp, aggregated_into_event_id, created_at
                    FROM actions
                    WHERE timestamp >= ? AND timestamp <= ?
                      AND deleted = 0
                    ORDER BY timestamp ASC
                    """,
                    (start_time, end_time),
                )
                rows = cursor.fetchall()

            actions: List[Dict[str, Any]] = []
            for row in rows:
                action = {
                    "id": row["id"],
                    "title": row["title"],
                    "description": row["description"],
                    "keywords": json.loads(row["keywords"])
                    if row["keywords"]
                    else [],
                    "timestamp": row["timestamp"],
                    "aggregated_into_event_id": row["aggregated_into_event_id"],
                    "created_at": row["created_at"],
                }
                action["screenshots"] = await self._load_screenshots(row["id"])
                actions.append(action)

            return actions

        except Exception as e:
            logger.error(f"Failed to get actions in timeframe: {e}", exc_info=True)
            return []

    async def delete(self, action_id: str) -> None:
        """
        Soft delete an action

        Args:
            action_id: Action identifier
        """
        try:
            with self._get_conn() as conn:
                conn.execute(
                    "UPDATE actions SET deleted = 1 WHERE id = ?", (action_id,)
                )
                conn.commit()
                logger.debug(f"Deleted action: {action_id}")

        except Exception as e:
            logger.error(f"Failed to delete action {action_id}: {e}", exc_info=True)
            raise

    async def mark_as_aggregated(
        self, action_ids: List[str], event_id: str
    ) -> None:
        """
        Mark actions as aggregated into an event

        Args:
            action_ids: List of action IDs to mark
            event_id: The event ID they were aggregated into
        """
        if not action_ids:
            return

        try:
            placeholders = ",".join("?" * len(action_ids))
            with self._get_conn() as conn:
                conn.execute(
                    f"""
                    UPDATE actions
                    SET aggregated_into_event_id = ?
                    WHERE id IN ({placeholders})
                    """,
                    [event_id] + action_ids,
                )
                conn.commit()
                logger.debug(
                    f"Marked {len(action_ids)} actions as aggregated into event {event_id}"
                )

        except Exception as e:
            logger.error(f"Failed to mark actions as aggregated: {e}", exc_info=True)
            raise

    async def get_count_by_date(self) -> Dict[str, int]:
        """
        Get action count grouped by date

        Returns:
            Dictionary mapping date (YYYY-MM-DD) to action count
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    SELECT DATE(timestamp) as date, COUNT(*) as count
                    FROM actions
                    WHERE deleted = 0
                    GROUP BY DATE(timestamp)
                    ORDER BY date DESC
                    """
                )
                rows = cursor.fetchall()

            return {row["date"]: row["count"] for row in rows}

        except Exception as e:
            logger.error(f"Failed to get action count by date: {e}", exc_info=True)
            return {}

    async def get_screenshots(self, action_id: str) -> List[str]:
        """Expose screenshot hashes for a specific action"""
        return await self._load_screenshots(action_id)

    async def _load_screenshots(self, action_id: str) -> List[str]:
        """
        Load screenshots for an action

        Args:
            action_id: Action identifier

        Returns:
            List of screenshot hashes
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    SELECT hash FROM action_images
                    WHERE action_id = ?
                    ORDER BY created_at ASC
                    """,
                    (action_id,),
                )
                rows = cursor.fetchall()

            return [row["hash"] for row in rows if row["hash"] and row["hash"].strip()]

        except Exception as e:
            logger.error(
                f"Failed to load screenshots for action {action_id}: {e}",
                exc_info=True,
            )
            return []
