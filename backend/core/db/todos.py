"""
Todos Repository - Handles all todo-related database operations
"""

import json
from datetime import datetime
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
        *,
        completed: bool = False,
        scheduled_date: Optional[str] = None,
        scheduled_time: Optional[str] = None,
        scheduled_end_time: Optional[str] = None,
        recurrence_rule: Optional[Dict[str, Any]] = None,
        created_at: Optional[str] = None,
    ) -> None:
        """Save or update a todo"""
        try:
            created = created_at or datetime.now().isoformat()
            with self._get_conn() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO todos (
                        id, title, description, keywords,
                        created_at, completed, deleted,
                        scheduled_date, scheduled_time, scheduled_end_time, recurrence_rule
                    ) VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?)
                    """,
                    (
                        todo_id,
                        title,
                        description,
                        json.dumps(keywords, ensure_ascii=False),
                        created,
                        int(completed),
                        scheduled_date,
                        scheduled_time,
                        scheduled_end_time,
                        json.dumps(recurrence_rule) if recurrence_rule else None,
                    ),
                )
                conn.commit()
                logger.debug(f"Saved todo: {todo_id}")

                # Send event to frontend
                from core.events import emit_todo_created

                emit_todo_created(
                    {
                        "id": todo_id,
                        "title": title,
                        "description": description,
                        "keywords": keywords,
                        "completed": completed,
                        "scheduled_date": scheduled_date,
                        "scheduled_time": scheduled_time,
                        "scheduled_end_time": scheduled_end_time,
                        "recurrence_rule": recurrence_rule,
                        "created_at": created,
                        "type": "original",
                    }
                )
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
        *,
        completed: bool = False,
        scheduled_date: Optional[str] = None,
        scheduled_time: Optional[str] = None,
        scheduled_end_time: Optional[str] = None,
        recurrence_rule: Optional[Dict[str, Any]] = None,
        created_at: Optional[str] = None,
    ) -> None:
        """Save or update a combined todo"""
        try:
            created = created_at or datetime.now().isoformat()
            with self._get_conn() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO combined_todos (
                        id, title, description, keywords, merged_from_ids,
                        created_at, completed, deleted,
                        scheduled_date, scheduled_time, scheduled_end_time, recurrence_rule
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?)
                    """,
                    (
                        todo_id,
                        title,
                        description,
                        json.dumps(keywords, ensure_ascii=False),
                        json.dumps(merged_from_ids),
                        created,
                        int(completed),
                        scheduled_date,
                        scheduled_time,
                        scheduled_end_time,
                        json.dumps(recurrence_rule) if recurrence_rule else None,
                    ),
                )
                conn.commit()
                logger.debug(f"Saved combined todo: {todo_id}")

                # Send event to frontend
                from core.events import emit_todo_updated

                emit_todo_updated(
                    {
                        "id": todo_id,
                        "title": title,
                        "description": description,
                        "keywords": keywords,
                        "completed": completed,
                        "scheduled_date": scheduled_date,
                        "scheduled_time": scheduled_time,
                        "scheduled_end_time": scheduled_end_time,
                        "recurrence_rule": recurrence_rule,
                        "created_at": created,
                        "merged_from_ids": merged_from_ids,
                        "type": "combined",
                    }
                )
        except Exception as e:
            logger.error(f"Failed to save combined todo {todo_id}: {e}", exc_info=True)
            raise

    async def get_unmerged(self) -> List[Dict[str, Any]]:
        """Return todos that have not been merged"""
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    SELECT t.id, t.title, t.description, t.keywords, t.created_at, t.completed
                    FROM todos t
                    WHERE t.deleted = 0
                    ORDER BY t.created_at ASC
                    """
                )
                rows = cursor.fetchall()

                merged_cursor = conn.execute(
                    """
                    SELECT merged_from_ids
                    FROM combined_todos
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
                        "completed": bool(row["completed"]),
                    }
                )

            return result

        except Exception as e:
            logger.error(f"Failed to get unmerged todos: {e}", exc_info=True)
            return []

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
            if include_completed:
                combined_query = """
                    SELECT id, title, description, keywords, merged_from_ids,
                           created_at, completed, deleted, scheduled_date, scheduled_time,
                           scheduled_end_time, recurrence_rule
                    FROM combined_todos
                    WHERE deleted = 0
                    ORDER BY completed ASC, created_at DESC
                """
                base_query = """
                    SELECT id, title, description, keywords, created_at,
                           completed, deleted, scheduled_date, scheduled_time,
                           scheduled_end_time, recurrence_rule
                    FROM todos
                    WHERE deleted = 0
                    ORDER BY completed ASC, created_at DESC
                """
            else:
                combined_query = """
                    SELECT id, title, description, keywords, merged_from_ids,
                           created_at, completed, deleted, scheduled_date, scheduled_time,
                           scheduled_end_time, recurrence_rule
                    FROM combined_todos
                    WHERE deleted = 0 AND completed = 0
                    ORDER BY created_at DESC
                """
                base_query = """
                    SELECT id, title, description, keywords, created_at,
                           completed, deleted, scheduled_date, scheduled_time,
                           scheduled_end_time, recurrence_rule
                    FROM todos
                    WHERE deleted = 0 AND completed = 0
                    ORDER BY created_at DESC
                """

            with self._get_conn() as conn:
                cursor = conn.execute(combined_query)
                rows = cursor.fetchall()

            todo_list: List[Dict[str, Any]] = []
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
                        "scheduled_end_time": row["scheduled_end_time"],
                        "recurrence_rule": json.loads(row["recurrence_rule"])
                        if row["recurrence_rule"]
                        else None,
                        "type": "combined",
                    }
                )

            if not todo_list:
                with self._get_conn() as conn:
                    cursor = conn.execute(base_query)
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
                            "scheduled_end_time": row["scheduled_end_time"],
                            "recurrence_rule": json.loads(row["recurrence_rule"])
                            if row["recurrence_rule"]
                            else None,
                            "type": "original",
                        }
                    )

            return todo_list

        except Exception as e:
            logger.error(f"Failed to get todo list: {e}", exc_info=True)
            return []

    async def schedule(
        self,
        todo_id: str,
        scheduled_date: str,
        scheduled_time: Optional[str] = None,
        scheduled_end_time: Optional[str] = None,
        recurrence_rule: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Schedule todo to a specific date and optional time window

        Args:
            todo_id: Todo ID
            scheduled_date: Scheduled date in YYYY-MM-DD format
            scheduled_time: Optional scheduled time in HH:MM format
            scheduled_end_time: Optional scheduled end time in HH:MM format
            recurrence_rule: Optional recurrence configuration dict

        Returns:
            Updated todo dict or None if not found
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()

                recurrence_json = json.dumps(recurrence_rule) if recurrence_rule else None

                cursor.execute(
                    """
                    UPDATE combined_todos
                    SET scheduled_date = ?, scheduled_time = ?,
                        scheduled_end_time = ?, recurrence_rule = ?
                    WHERE id = ? AND deleted = 0
                    """,
                    (
                        scheduled_date,
                        scheduled_time,
                        scheduled_end_time,
                        recurrence_json,
                        todo_id,
                    ),
                )
                conn.commit()

                cursor.execute(
                    """
                    SELECT id, title, description, keywords, merged_from_ids,
                           created_at, completed, deleted, scheduled_date, scheduled_time,
                           scheduled_end_time, recurrence_rule
                    FROM combined_todos
                    WHERE id = ? AND deleted = 0
                    """,
                    (todo_id,),
                )
                row = cursor.fetchone()

                if row:
                    updated_todo = {
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
                        "scheduled_end_time": row["scheduled_end_time"],
                        "recurrence_rule": json.loads(row["recurrence_rule"])
                        if row["recurrence_rule"]
                        else None,
                        "type": "combined",
                    }

                    # Send event to frontend
                    from core.events import emit_todo_updated

                    emit_todo_updated(updated_todo)

                    return updated_todo

                cursor.execute(
                    """
                    UPDATE todos
                    SET scheduled_date = ?, scheduled_time = ?,
                        scheduled_end_time = ?, recurrence_rule = ?
                    WHERE id = ? AND deleted = 0
                    """,
                    (
                        scheduled_date,
                        scheduled_time,
                        scheduled_end_time,
                        recurrence_json,
                        todo_id,
                    ),
                )
                conn.commit()

                cursor.execute(
                    """
                    SELECT id, title, description, keywords, created_at,
                           completed, deleted, scheduled_date, scheduled_time,
                           scheduled_end_time, recurrence_rule
                    FROM todos
                    WHERE id = ? AND deleted = 0
                    """,
                    (todo_id,),
                )
                row = cursor.fetchone()

                if row:
                    updated_todo = {
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
                        "scheduled_end_time": row["scheduled_end_time"],
                        "recurrence_rule": json.loads(row["recurrence_rule"])
                        if row["recurrence_rule"]
                        else None,
                        "type": "original",
                    }

                    # Send event to frontend
                    from core.events import emit_todo_updated

                    emit_todo_updated(updated_todo)

                    return updated_todo

                return None

        except Exception as e:
            logger.error(f"Failed to schedule todo: {e}", exc_info=True)
            return None

    async def unschedule(self, todo_id: str) -> Optional[Dict[str, Any]]:
        """Clear scheduling info for a todo"""
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    UPDATE combined_todos
                    SET scheduled_date = NULL,
                        scheduled_time = NULL,
                        scheduled_end_time = NULL,
                        recurrence_rule = NULL
                    WHERE id = ? AND deleted = 0
                    """,
                    (todo_id,),
                )
                conn.commit()

                cursor.execute(
                    """
                    SELECT id, title, description, keywords, merged_from_ids,
                           created_at, completed, deleted, scheduled_date
                    FROM combined_todos
                    WHERE id = ? AND deleted = 0
                    """,
                    (todo_id,),
                )
                row = cursor.fetchone()

                if row:
                    updated_todo = {
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
                        "type": "combined",
                    }

                    # Send event to frontend
                    from core.events import emit_todo_updated

                    emit_todo_updated(updated_todo)

                    return updated_todo

                cursor.execute(
                    """
                    UPDATE todos
                    SET scheduled_date = NULL,
                        scheduled_time = NULL,
                        scheduled_end_time = NULL,
                        recurrence_rule = NULL
                    WHERE id = ? AND deleted = 0
                    """,
                    (todo_id,),
                )
                conn.commit()

                cursor.execute(
                    """
                    SELECT id, title, description, keywords, created_at,
                           completed, deleted, scheduled_date
                    FROM todos
                    WHERE id = ? AND deleted = 0
                    """,
                    (todo_id,),
                )
                row = cursor.fetchone()

                if row:
                    updated_todo = {
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
                        "type": "original",
                    }

                    # Send event to frontend
                    from core.events import emit_todo_updated

                    emit_todo_updated(updated_todo)

                    return updated_todo

                return None

        except Exception as e:
            logger.error(f"Failed to unschedule todo: {e}", exc_info=True)
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

                # Send event to frontend
                from core.events import emit_todo_deleted

                emit_todo_deleted(todo_id)
        except Exception as e:
            logger.error(f"Failed to delete todo {todo_id}: {e}", exc_info=True)
            raise

    async def delete_batch(self, todo_ids: List[str]) -> int:
        """Soft delete multiple todos"""
        if not todo_ids:
            return 0

        try:
            placeholders = ",".join("?" for _ in todo_ids)
            with self._get_conn() as conn:
                cursor = conn.execute(
                    f"""
                    UPDATE todos
                    SET deleted = 1
                    WHERE deleted = 0 AND id IN ({placeholders})
                    """,
                    todo_ids,
                )
                conn.commit()
                return cursor.rowcount

        except Exception as e:
            logger.error(f"Failed to batch delete todos: {e}", exc_info=True)
            return 0

    async def delete_by_date_range(self, start_iso: str, end_iso: str) -> int:
        """Soft delete todos in a time window"""
        try:
            deleted_count = 0
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    UPDATE combined_todos
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
                    UPDATE todos
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
                f"Failed to delete todos between {start_iso} and {end_iso}: {e}",
                exc_info=True,
            )
            return 0
