"""
Todos Repository - Handles all todo-related database operations
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.logger import get_logger

from .base import BaseRepository

logger = get_logger(__name__)


class TodosRepository(BaseRepository):
    """Repository for managing todos in the database"""

    def __init__(self, db_path: Path):
        super().__init__(db_path)

    async def save(
        self,
        todo_id: str,
        title: str,
        description: str,
        keywords: List[str],
    ) -> None:
        """Save or update a todo"""
        try:
            with self._get_conn() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO todos (
                        id, title, description, keywords,
                        created_at, completed, deleted
                    ) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, 0, 0)
                    """,
                    (
                        todo_id,
                        title,
                        description,
                        json.dumps(keywords, ensure_ascii=False),
                    ),
                )
                conn.commit()
                logger.debug(f"Saved todo: {todo_id}")
        except Exception as e:
            logger.error(f"Failed to save todo {todo_id}: {e}", exc_info=True)
            raise

    async def save_combined(
        self,
        todo_id: str,
        title: str,
        description: str,
        keywords: List[str],
        merged_from_ids: List[str],
    ) -> None:
        """Save or update a combined todo"""
        try:
            with self._get_conn() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO combined_todos (
                        id, title, description, keywords, merged_from_ids,
                        created_at, completed, deleted
                    ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, 0, 0)
                    """,
                    (
                        todo_id,
                        title,
                        description,
                        json.dumps(keywords, ensure_ascii=False),
                        json.dumps(merged_from_ids),
                    ),
                )
                conn.commit()
                logger.debug(f"Saved combined todo: {todo_id}")
        except Exception as e:
            logger.error(f"Failed to save combined todo {todo_id}: {e}", exc_info=True)
            raise

    async def get_list(
        self, include_completed: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get todo list (prioritize returning combined)

        Args:
            include_completed: Whether to include completed todos

        Returns:
            List of todo dictionaries
        """
        try:
            # First get combined_todos
            if include_completed:
                query = """
                    SELECT id, title, description, keywords, merged_from_ids,
                           created_at, completed, deleted, scheduled_date, scheduled_time
                    FROM combined_todos
                    WHERE deleted = 0
                    ORDER BY completed ASC, created_at DESC
                """
            else:
                query = """
                    SELECT id, title, description, keywords, merged_from_ids,
                           created_at, completed, deleted, scheduled_date, scheduled_time
                    FROM combined_todos
                    WHERE deleted = 0 AND completed = 0
                    ORDER BY created_at DESC
                """

            with self._get_conn() as conn:
                cursor = conn.execute(query)
                rows = cursor.fetchall()

            todo_list = []
            for row in rows:
                todo_list.append(
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
                        "completed": bool(row["completed"]),
                        "deleted": bool(row["deleted"]),
                        "scheduled_date": row["scheduled_date"],
                        "scheduled_time": row["scheduled_time"],
                        "type": "combined",
                    }
                )

            # If no combined_todos, return original todos
            if not todo_list:
                if include_completed:
                    query = """
                        SELECT id, title, description, keywords, created_at,
                               completed, deleted, scheduled_date, scheduled_time
                        FROM todos
                        WHERE deleted = 0
                        ORDER BY completed ASC, created_at DESC
                    """
                else:
                    query = """
                        SELECT id, title, description, keywords, created_at,
                               completed, deleted, scheduled_date, scheduled_time
                        FROM todos
                        WHERE deleted = 0 AND completed = 0
                        ORDER BY created_at DESC
                    """

                with self._get_conn() as conn:
                    cursor = conn.execute(query)
                    rows = cursor.fetchall()

                for row in rows:
                    todo_list.append(
                        {
                            "id": row["id"],
                            "title": row["title"],
                            "description": row["description"],
                            "keywords": json.loads(row["keywords"])
                            if row["keywords"]
                            else [],
                            "created_at": row["created_at"],
                            "completed": bool(row["completed"]),
                            "deleted": bool(row["deleted"]),
                            "scheduled_date": row["scheduled_date"],
                            "scheduled_time": row["scheduled_time"],
                            "type": "original",
                        }
                    )

            return todo_list

        except Exception as e:
            logger.error(f"Failed to get todo list: {e}", exc_info=True)
            return []

    async def schedule(
        self, todo_id: str, scheduled_date: str, scheduled_time: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Schedule todo to a specific date and optional time

        Args:
            todo_id: Todo ID
            scheduled_date: Scheduled date in YYYY-MM-DD format
            scheduled_time: Optional scheduled time in HH:MM format

        Returns:
            Updated todo dict or None if not found
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()

                # Try to update combined_todos first
                cursor.execute(
                    """
                    UPDATE combined_todos
                    SET scheduled_date = ?, scheduled_time = ?
                    WHERE id = ? AND deleted = 0
                    """,
                    (scheduled_date, scheduled_time, todo_id),
                )
                conn.commit()

                # Check if update was successful
                cursor.execute(
                    """
                    SELECT id, title, description, keywords, merged_from_ids,
                           created_at, completed, deleted, scheduled_date, scheduled_time
                    FROM combined_todos
                    WHERE id = ? AND deleted = 0
                    """,
                    (todo_id,),
                )
                row = cursor.fetchone()

                if row:
                    return {
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
                        "completed": bool(row["completed"]),
                        "deleted": bool(row["deleted"]),
                        "scheduled_date": row["scheduled_date"],
                        "scheduled_time": row["scheduled_time"],
                        "type": "combined",
                    }

                # If not found in combined_todos, try original todos
                cursor.execute(
                    """
                    UPDATE todos
                    SET scheduled_date = ?, scheduled_time = ?
                    WHERE id = ? AND deleted = 0
                    """,
                    (scheduled_date, scheduled_time, todo_id),
                )
                conn.commit()

                cursor.execute(
                    """
                    SELECT id, title, description, keywords, created_at,
                           completed, deleted, scheduled_date, scheduled_time
                    FROM todos
                    WHERE id = ? AND deleted = 0
                    """,
                    (todo_id,),
                )
                row = cursor.fetchone()

                if row:
                    return {
                        "id": row["id"],
                        "title": row["title"],
                        "description": row["description"],
                        "keywords": json.loads(row["keywords"])
                        if row["keywords"]
                        else [],
                        "created_at": row["created_at"],
                        "completed": bool(row["completed"]),
                        "deleted": bool(row["deleted"]),
                        "scheduled_date": row["scheduled_date"],
                        "scheduled_time": row["scheduled_time"],
                        "type": "original",
                    }

                return None

        except Exception as e:
            logger.error(f"Failed to schedule todo: {e}", exc_info=True)
            return None

    async def delete(self, todo_id: str) -> None:
        """Soft delete a todo"""
        try:
            with self._get_conn() as conn:
                # Try combined_todos first
                conn.execute(
                    "UPDATE combined_todos SET deleted = 1 WHERE id = ?", (todo_id,)
                )
                # Also try original todos
                conn.execute("UPDATE todos SET deleted = 1 WHERE id = ?", (todo_id,))
                conn.commit()
                logger.debug(f"Deleted todo: {todo_id}")
        except Exception as e:
            logger.error(f"Failed to delete todo {todo_id}: {e}", exc_info=True)
            raise
