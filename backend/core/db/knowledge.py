"""
Knowledge Repository - Handles all knowledge-related database operations
"""

import json
from pathlib import Path
from typing import Any, Dict, List

from core.logger import get_logger

from .base import BaseRepository

logger = get_logger(__name__)


class KnowledgeRepository(BaseRepository):
    """Repository for managing knowledge in the database"""

    def __init__(self, db_path: Path):
        super().__init__(db_path)

    async def save(
        self,
        knowledge_id: str,
        title: str,
        description: str,
        keywords: List[str],
    ) -> None:
        """Save or update knowledge"""
        try:
            with self._get_conn() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO knowledge (
                        id, title, description, keywords,
                        created_at, deleted
                    ) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, 0)
                    """,
                    (
                        knowledge_id,
                        title,
                        description,
                        json.dumps(keywords, ensure_ascii=False),
                    ),
                )
                conn.commit()
                logger.debug(f"Saved knowledge: {knowledge_id}")
        except Exception as e:
            logger.error(f"Failed to save knowledge {knowledge_id}: {e}", exc_info=True)
            raise

    async def save_combined(
        self,
        knowledge_id: str,
        title: str,
        description: str,
        keywords: List[str],
        merged_from_ids: List[str],
    ) -> None:
        """Save or update combined knowledge"""
        try:
            with self._get_conn() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO combined_knowledge (
                        id, title, description, keywords, merged_from_ids,
                        created_at, deleted
                    ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, 0)
                    """,
                    (
                        knowledge_id,
                        title,
                        description,
                        json.dumps(keywords, ensure_ascii=False),
                        json.dumps(merged_from_ids),
                    ),
                )
                conn.commit()
                logger.debug(f"Saved combined knowledge: {knowledge_id}")
        except Exception as e:
            logger.error(
                f"Failed to save combined knowledge {knowledge_id}: {e}", exc_info=True
            )
            raise

    async def get_list(self) -> List[Dict[str, Any]]:
        """
        Get knowledge list (prioritize returning combined)

        Returns:
            List of knowledge dictionaries
        """
        try:
            # First get combined_knowledge
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    SELECT id, title, description, keywords, merged_from_ids, created_at, deleted
                    FROM combined_knowledge
                    WHERE deleted = 0
                    ORDER BY created_at DESC
                    """
                )
                rows = cursor.fetchall()

            knowledge_list = []
            for row in rows:
                knowledge_list.append(
                    {
                        "id": row["id"],
                        "title": row["title"],
                        "description": row["description"],
                        "keywords": json.loads(row["keywords"])
                        if row["keywords"]
                        else [],
                        "merged_from_ids": json.loads(row["merged_from_ids"])
                        if row["merged_from_ids"]
                        else [],
                        "created_at": row["created_at"],
                        "deleted": bool(row["deleted"]),
                        "type": "combined",
                    }
                )

            # If no combined_knowledge, return original knowledge
            if not knowledge_list:
                with self._get_conn() as conn:
                    cursor = conn.execute(
                        """
                        SELECT id, title, description, keywords, created_at, deleted
                        FROM knowledge
                        WHERE deleted = 0
                        ORDER BY created_at DESC
                        """
                    )
                    rows = cursor.fetchall()

                for row in rows:
                    knowledge_list.append(
                        {
                            "id": row["id"],
                            "title": row["title"],
                            "description": row["description"],
                            "keywords": json.loads(row["keywords"])
                            if row["keywords"]
                            else [],
                            "created_at": row["created_at"],
                            "deleted": bool(row["deleted"]),
                            "type": "original",
                        }
                    )

            return knowledge_list

        except Exception as e:
            logger.error(f"Failed to get knowledge list: {e}", exc_info=True)
            return []

    async def delete(self, knowledge_id: str) -> None:
        """Soft delete knowledge"""
        try:
            with self._get_conn() as conn:
                # Try combined_knowledge first
                conn.execute(
                    "UPDATE combined_knowledge SET deleted = 1 WHERE id = ?",
                    (knowledge_id,),
                )
                # Also try original knowledge
                conn.execute(
                    "UPDATE knowledge SET deleted = 1 WHERE id = ?", (knowledge_id,)
                )
                conn.commit()
                logger.debug(f"Deleted knowledge: {knowledge_id}")
        except Exception as e:
            logger.error(
                f"Failed to delete knowledge {knowledge_id}: {e}", exc_info=True
            )
            raise

    async def get_count_by_date(self) -> Dict[str, int]:
        """
        Get knowledge count grouped by date

        Returns:
            Dictionary mapping date (YYYY-MM-DD) to knowledge count
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    SELECT DATE(created_at) as date, COUNT(*) as count
                    FROM combined_knowledge
                    WHERE deleted = 0
                    GROUP BY DATE(created_at)

                    UNION ALL

                    SELECT DATE(created_at) as date, COUNT(*) as count
                    FROM knowledge
                    WHERE deleted = 0
                      AND id NOT IN (SELECT merged_from_ids FROM combined_knowledge WHERE deleted = 0)
                    GROUP BY DATE(created_at)

                    ORDER BY date DESC
                    """
                )
                rows = cursor.fetchall()

            return {row["date"]: row["count"] for row in rows}

        except Exception as e:
            logger.error(
                f"Failed to get knowledge count by date: {e}", exc_info=True
            )
            return {}
