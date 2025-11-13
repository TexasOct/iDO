"""
Diaries Repository - Handles all diary-related database operations
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.logger import get_logger

from .base import BaseRepository

logger = get_logger(__name__)


class DiariesRepository(BaseRepository):
    """Repository for managing diaries in the database"""

    def __init__(self, db_path: Path):
        super().__init__(db_path)

    async def save(
        self,
        diary_id: str,
        date: str,
        content: str,
        source_activity_ids: List[str],
    ) -> None:
        """Save or update a diary"""
        try:
            with self._get_conn() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO diaries (
                        id, date, content, source_activity_ids, created_at
                    ) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    (
                        diary_id,
                        date,
                        content,
                        json.dumps(source_activity_ids),
                    ),
                )
                conn.commit()
                logger.debug(f"Saved diary for date: {date}")
        except Exception as e:
            logger.error(f"Failed to save diary for {date}: {e}", exc_info=True)
            raise

    async def get_by_date(self, date: str) -> Optional[Dict[str, Any]]:
        """Get diary by date"""
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    SELECT id, date, content, source_activity_ids, created_at
                    FROM diaries
                    WHERE date = ?
                    """,
                    (date,),
                )
                row = cursor.fetchone()

            if not row:
                return None

            return {
                "id": row["id"],
                "date": row["date"],
                "content": row["content"],
                "source_activity_ids": json.loads(row["source_activity_ids"])
                if row["source_activity_ids"]
                else [],
                "created_at": row["created_at"],
            }

        except Exception as e:
            logger.error(f"Failed to get diary for date {date}: {e}", exc_info=True)
            return None

    async def get_list(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get diary list"""
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    SELECT id, date, content, source_activity_ids, created_at
                    FROM diaries
                    ORDER BY date DESC
                    LIMIT ?
                    """,
                    (limit,),
                )
                rows = cursor.fetchall()

            return [
                {
                    "id": row["id"],
                    "date": row["date"],
                    "content": row["content"],
                    "source_activity_ids": json.loads(row["source_activity_ids"])
                    if row["source_activity_ids"]
                    else [],
                    "created_at": row["created_at"],
                }
                for row in rows
            ]

        except Exception as e:
            logger.error(f"Failed to get diary list: {e}", exc_info=True)
            return []

    async def delete(self, diary_id: str) -> None:
        """Delete a diary"""
        try:
            with self._get_conn() as conn:
                conn.execute("DELETE FROM diaries WHERE id = ?", (diary_id,))
                conn.commit()
                logger.debug(f"Deleted diary: {diary_id}")
        except Exception as e:
            logger.error(f"Failed to delete diary {diary_id}: {e}", exc_info=True)
            raise
