"""
Knowledge Repository - Handles all knowledge-related database operations
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

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
        *,
        created_at: Optional[str] = None,
    ) -> None:
        """Save or update knowledge"""
        try:
            created = created_at or datetime.now().isoformat()
            with self._get_conn() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO knowledge (
                        id, title, description, keywords,
                        created_at, deleted
                    ) VALUES (?, ?, ?, ?, ?, 0)
                    """,
                    (
                        knowledge_id,
                        title,
                        description,
                        json.dumps(keywords, ensure_ascii=False),
                        created,
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
        *,
        created_at: Optional[str] = None,
    ) -> None:
        """Save or update combined knowledge"""
        try:
            created = created_at or datetime.now().isoformat()
            with self._get_conn() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO combined_knowledge (
                        id, title, description, keywords, merged_from_ids,
                        created_at, deleted
                    ) VALUES (?, ?, ?, ?, ?, ?, 0)
                    """,
                    (
                        knowledge_id,
                        title,
                        description,
                        json.dumps(keywords, ensure_ascii=False),
                        json.dumps(merged_from_ids),
                        created,
                    ),
                )
                conn.commit()
                logger.debug(f"Saved combined knowledge: {knowledge_id}")
        except Exception as e:
            logger.error(
                f"Failed to save combined knowledge {knowledge_id}: {e}", exc_info=True
            )
            raise

    async def get_list(self, include_deleted: bool = False) -> List[Dict[str, Any]]:
        """
        Get knowledge list (prioritize returning combined)

        Args:
            include_deleted: Whether to include deleted rows

        Returns:
            List of knowledge dictionaries
        """
        try:
            base_where = "" if include_deleted else "WHERE deleted = 0"

            with self._get_conn() as conn:
                cursor = conn.execute(
                    f"""
                    SELECT id, title, description, keywords, merged_from_ids, created_at, deleted
                    FROM combined_knowledge
                    {base_where}
                    ORDER BY created_at DESC
                    """
                )
                rows = cursor.fetchall()

            knowledge_list: List[Dict[str, Any]] = []
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

            if not knowledge_list:
                with self._get_conn() as conn:
                    cursor = conn.execute(
                        f"""
                        SELECT id, title, description, keywords, created_at, deleted
                        FROM knowledge
                        {base_where}
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

    async def get_unmerged(self) -> List[Dict[str, Any]]:
        """Return knowledge that has not been merged"""
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    SELECT k.id, k.title, k.description, k.keywords, k.created_at
                    FROM knowledge k
                    WHERE k.deleted = 0
                    ORDER BY k.created_at ASC
                    """
                )
                rows = cursor.fetchall()

                merged_cursor = conn.execute(
                    """
                    SELECT merged_from_ids
                    FROM combined_knowledge
                    WHERE deleted = 0
                    """
                )
                merged_rows = merged_cursor.fetchall()

            merged_ids = set()
            for row in merged_rows:
                if not row["merged_from_ids"]:
                    continue
                try:
                    for item_id in json.loads(row["merged_from_ids"]):
                        merged_ids.add(item_id)
                except (TypeError, json.JSONDecodeError):
                    continue

            result: List[Dict[str, Any]] = []
            for row in rows:
                if row["id"] in merged_ids:
                    continue
                result.append(
                    {
                        "id": row["id"],
                        "title": row["title"],
                        "description": row["description"],
                        "keywords": json.loads(row["keywords"])
                        if row["keywords"]
                        else [],
                        "created_at": row["created_at"],
                    }
                )

            return result

        except Exception as e:
            logger.error(f"Failed to get unmerged knowledge: {e}", exc_info=True)
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

    async def delete_batch(self, knowledge_ids: List[str]) -> int:
        """Soft delete multiple knowledge rows"""
        if not knowledge_ids:
            return 0

        try:
            placeholders = ",".join("?" for _ in knowledge_ids)
            with self._get_conn() as conn:
                cursor = conn.execute(
                    f"""
                    UPDATE knowledge
                    SET deleted = 1
                    WHERE deleted = 0 AND id IN ({placeholders})
                    """,
                    knowledge_ids,
                )
                conn.commit()
                return cursor.rowcount

        except Exception as e:
            logger.error(f"Failed to batch delete knowledge: {e}", exc_info=True)
            return 0

    async def delete_by_date_range(self, start_iso: str, end_iso: str) -> int:
        """Soft delete knowledge rows in a time window"""
        try:
            deleted_count = 0
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    UPDATE combined_knowledge
                    SET deleted = 1
                    WHERE deleted = 0
                      AND created_at >= ?
                      AND created_at <= ?
                    """,
                    (start_iso, end_iso),
                )
                deleted_count += cursor.rowcount

                cursor = conn.execute(
                    """
                    UPDATE knowledge
                    SET deleted = 1
                    WHERE deleted = 0
                      AND created_at >= ?
                      AND created_at <= ?
                    """,
                    (start_iso, end_iso),
                )
                deleted_count += cursor.rowcount

                conn.commit()

            return deleted_count

        except Exception as e:
            logger.error(
                f"Failed to delete knowledge between {start_iso} and {end_iso}: {e}",
                exc_info=True,
            )
            return 0

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
