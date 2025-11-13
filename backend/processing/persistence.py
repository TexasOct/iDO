"""
Data persistence interface (new architecture)
Handles database storage for events, knowledge, todos, activities, diaries
"""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.db import get_db
from core.logger import get_logger
from processing.image_manager import get_image_manager

logger = get_logger(__name__)

# Import database module - use unified core.db


class ProcessingPersistence:
    """Processing data persistence (new architecture)"""

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize persistence

        Args:
            db_path: Database file path (optional, not recommended, should use unified database)
        """
        self.db_path = db_path
        self.image_manager = get_image_manager()
        self.db_manager = get_db()

        # Ensure new architecture required tables exist
        self._ensure_new_architecture_tables()

    def _ensure_new_architecture_tables(self):
        """Ensure tables required for new architecture exist"""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()

            # Knowledge table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS knowledge (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    keywords TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    deleted BOOLEAN DEFAULT 0
                )
            """)

            # Todos table (new architecture)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS todos (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    keywords TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    completed BOOLEAN DEFAULT 0,
                    deleted BOOLEAN DEFAULT 0,
                    scheduled_date TEXT
                )
            """)

            # Add scheduled_date column if it doesn't exist (migration)
            try:
                cursor.execute("ALTER TABLE todos ADD COLUMN scheduled_date TEXT")
                conn.commit()
            except sqlite3.OperationalError:
                # Column already exists
                pass

            # CombinedKnowledge table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS combined_knowledge (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    keywords TEXT,
                    merged_from_ids TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    deleted BOOLEAN DEFAULT 0
                )
            """)

            # CombinedTodos table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS combined_todos (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    keywords TEXT,
                    merged_from_ids TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    completed BOOLEAN DEFAULT 0,
                    deleted BOOLEAN DEFAULT 0,
                    scheduled_date TEXT
                )
            """)

            # Add scheduled_date column if it doesn't exist (migration)
            try:
                cursor.execute(
                    "ALTER TABLE combined_todos ADD COLUMN scheduled_date TEXT"
                )
                conn.commit()
            except sqlite3.OperationalError:
                # Column already exists
                pass

            # Diaries table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS diaries (
                    id TEXT PRIMARY KEY,
                    date TEXT NOT NULL UNIQUE,
                    content TEXT NOT NULL,
                    source_activity_ids TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    deleted BOOLEAN DEFAULT 0
                )
            """)

            # Create indexes
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_knowledge_created ON knowledge(created_at DESC)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_knowledge_deleted ON knowledge(deleted)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_todos_created ON todos(created_at DESC)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_todos_completed ON todos(completed)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_todos_deleted ON todos(deleted)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_combined_knowledge_created ON combined_knowledge(created_at DESC)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_combined_todos_created ON combined_todos(created_at DESC)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_diaries_date ON diaries(date DESC)"
            )

            conn.commit()
            logger.debug("New architecture tables check completed")

    def _get_conn(self) -> sqlite3.Connection:
        """Get database connection (compatible with old interface)"""
        # Directly return connection, don't use context manager
        conn = sqlite3.connect(self.db_manager.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # ============ Event Related Methods ============

    async def save_event(self, event: Dict[str, Any]) -> bool:
        """
        Save event to database

        Args:
            event: Event data dictionary, containing id, title, description, keywords, timestamp

        Returns:
            Whether saved successfully
        """
        try:
            query = """
                INSERT INTO events (id, title, description, keywords, timestamp, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """
            keywords_json = json.dumps(event.get("keywords", []), ensure_ascii=False)
            timestamp = event.get("timestamp")
            if isinstance(timestamp, datetime):
                timestamp = timestamp.isoformat()

            params = (
                event["id"],
                event["title"],
                event["description"],
                keywords_json,
                timestamp,
                datetime.now().isoformat(),
            )

            screenshot_hashes = event.get("screenshot_hashes", [])
            unique_hashes = []
            seen = set()
            for img_hash in screenshot_hashes[:6]:
                if img_hash and img_hash not in seen:
                    seen.add(img_hash)
                    unique_hashes.append(img_hash)

            with self._get_conn() as conn:
                conn.execute(query, params)
                if unique_hashes:
                    self._replace_event_screenshots(conn, event["id"], unique_hashes)
                conn.commit()

            logger.debug(f"Event saved: {event['id']}")
            return True

        except Exception as e:
            logger.error(f"Failed to save event: {e}")
            return False

    def _replace_event_screenshots(
        self, conn: sqlite3.Connection, event_id: str, hashes: List[str]
    ) -> None:
        try:
            conn.execute("DELETE FROM event_images WHERE event_id = ?", (event_id,))
            for img_hash in hashes:
                conn.execute(
                    "INSERT OR IGNORE INTO event_images (event_id, hash, created_at) VALUES (?, ?, ?)",
                    (event_id, img_hash, datetime.now().isoformat()),
                )
        except Exception as exc:
            logger.error(f"Failed to save event screenshot: {exc}")

    def _load_event_screenshots(self, event_id: str) -> List[str]:
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    "SELECT hash FROM event_images WHERE event_id = ? ORDER BY created_at ASC",
                    (event_id,),
                )
                hashes = [row["hash"] for row in cursor.fetchall()]
        except Exception as exc:
            logger.error(f"Failed to load event screenshot hash: {exc}")
            return []

        screenshots: List[str] = []
        for img_hash in hashes:
            if not img_hash:
                continue
            data = self.image_manager.get_from_cache(img_hash)
            if not data:
                data = self.image_manager.load_thumbnail_base64(img_hash)
            if data:
                screenshots.append(data)

        return screenshots

    async def get_event_screenshots(self, event_id: str) -> List[str]:
        """Get screenshot hashes for a specific event

        Args:
            event_id: Event ID

        Returns:
            List of screenshot hashes
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    "SELECT hash FROM event_images WHERE event_id = ? ORDER BY created_at ASC",
                    (event_id,),
                )
                return [row["hash"] for row in cursor.fetchall()]
        except Exception as exc:
            logger.error(f"Failed to get event screenshots: {exc}")
            return []

    async def get_recent_events(
        self, limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get recent events

        Args:
            limit: Number to return
            offset: Number to skip

        Returns:
            Event list
        """
        try:
            query = """
                SELECT id, title, description, keywords, timestamp, created_at
                FROM events
                WHERE deleted = 0
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
            """

            with self._get_conn() as conn:
                cursor = conn.execute(query, (limit, offset))
                rows = cursor.fetchall()

            events = []
            for row in rows:
                events.append(
                    {
                        "id": row["id"],
                        "title": row["title"],
                        "description": row["description"],
                        "keywords": json.loads(row["keywords"])
                        if row["keywords"]
                        else [],
                        "timestamp": row["timestamp"],
                        "created_at": row["created_at"],
                        "screenshots": self._load_event_screenshots(row["id"]),
                    }
                )

            return events

        except Exception as e:
            logger.error(f"Failed to get recent events: {e}")
            return []

    async def get_events_by_type(
        self, event_type: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get events by type (new architecture doesn't distinguish types yet, returns recent events)"""
        logger.warning(
            "New architecture events don't store type information, ignoring event_type=%s",
            event_type,
        )
        return await self.get_recent_events(limit)

    async def get_events_in_timeframe(
        self, start_time: datetime, end_time: datetime
    ) -> List[Dict[str, Any]]:
        """Get events within specified time range"""
        try:
            query = """
                SELECT id, title, description, keywords, timestamp, created_at
                FROM events
                WHERE timestamp >= ? AND timestamp <= ?
                  AND deleted = 0
                ORDER BY timestamp ASC
            """

            with self._get_conn() as conn:
                cursor = conn.execute(
                    query, (start_time.isoformat(), end_time.isoformat())
                )
                rows = cursor.fetchall()

            events = []
            for row in rows:
                events.append(
                    {
                        "id": row["id"],
                        "title": row["title"],
                        "description": row["description"],
                        "keywords": json.loads(row["keywords"])
                        if row["keywords"]
                        else [],
                        "timestamp": datetime.fromisoformat(row["timestamp"]),
                        "created_at": row["created_at"],
                        "screenshots": self._load_event_screenshots(row["id"]),
                    }
                )

            return events

        except Exception as e:
            logger.error(f"Failed to get events by time range: {e}")
            return []

    async def get_event_by_id(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Get event details by ID"""
        try:
            query = """
                SELECT id, title, description, keywords, timestamp, created_at
                FROM events
                WHERE id = ? AND deleted = 0
            """

            with self._get_conn() as conn:
                cursor = conn.execute(query, (event_id,))
                row = cursor.fetchone()

            if not row:
                return None

            return {
                "id": row["id"],
                "title": row["title"],
                "description": row["description"],
                "keywords": json.loads(row["keywords"]) if row["keywords"] else [],
                "timestamp": row["timestamp"],
                "created_at": row["created_at"],
                "screenshots": self._load_event_screenshots(row["id"]),
            }

        except Exception as e:
            logger.error(f"Failed to get event by ID: {e}")
            return None

    async def get_unsummarized_events(
        self, since: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get events that have not been aggregated into activities

        Args:
            since: Start time (optional)

        Returns:
            Event list
        """
        try:
            # Simplified version: Get recent events not referenced in activities
            # Should actually check if activities.source_event_ids contains this event
            if since:
                query = """
                    SELECT id, title, description, keywords, timestamp, created_at
                    FROM events
                    WHERE timestamp >= ? AND deleted = 0
                    ORDER BY timestamp ASC
                """
                params = (since.isoformat(),)
            else:
                # Get events from the last 1 hour
                query = """
                    SELECT id, title, description, keywords, timestamp, created_at
                    FROM events
                    WHERE timestamp >= datetime('now', '-1 hour') AND deleted = 0
                    ORDER BY timestamp ASC
                """
                params = ()

            with self._get_conn() as conn:
                cursor = conn.execute(query, params)
                rows = cursor.fetchall()

                # Get all aggregated event ids
                cursor = conn.execute("""
                    SELECT source_event_ids
                    FROM activities
                    WHERE deleted = 0
                """)
                aggregated_rows = cursor.fetchall()

            events = []
            aggregated_ids = set()

            for row in aggregated_rows:
                source_ids = row["source_event_ids"]
                if not source_ids:
                    continue
                try:
                    for event_id in json.loads(source_ids):
                        aggregated_ids.add(event_id)
                except (TypeError, json.JSONDecodeError):
                    continue

            for row in rows:
                if row["id"] in aggregated_ids:
                    continue

                events.append(
                    {
                        "id": row["id"],
                        "title": row["title"],
                        "description": row["description"],
                        "keywords": json.loads(row["keywords"])
                        if row["keywords"]
                        else [],
                        "timestamp": datetime.fromisoformat(row["timestamp"]),
                        "created_at": row["created_at"],
                    }
                )

            return events

        except Exception as e:
            logger.error(f"Failed to get unsummarized events: {e}")
            return []

    # ============ Knowledge Related Methods ============

    async def save_knowledge(self, knowledge: Dict[str, Any]) -> bool:
        """
        Save knowledge to database

        Args:
            knowledge: Knowledge data dictionary

        Returns:
            Whether save was successful
        """
        try:
            query = """
                INSERT INTO knowledge (id, title, description, keywords, created_at, deleted)
                VALUES (?, ?, ?, ?, ?, 0)
            """
            keywords_json = json.dumps(
                knowledge.get("keywords", []), ensure_ascii=False
            )
            created_at = knowledge.get("created_at")
            if isinstance(created_at, datetime):
                created_at = created_at.isoformat()

            params = (
                knowledge["id"],
                knowledge["title"],
                knowledge["description"],
                keywords_json,
                created_at or datetime.now().isoformat(),
            )

            with self._get_conn() as conn:
                conn.execute(query, params)
                conn.commit()

            logger.debug(f"Knowledge saved: {knowledge['id']}")
            return True

        except Exception as e:
            logger.error(f"Failed to save knowledge: {e}")
            return False

    async def get_unmerged_knowledge(self) -> List[Dict[str, Any]]:
        """
        Get unmerged knowledge

        Returns:
            Knowledge list
        """
        try:
            # Get knowledge not in combined_knowledge.merged_from_ids
            query = """
                SELECT k.id, k.title, k.description, k.keywords, k.created_at
                FROM knowledge k
                WHERE k.deleted = 0
                ORDER BY k.created_at ASC
            """

            with self._get_conn() as conn:
                cursor = conn.execute(query)
                rows = cursor.fetchall()

                # Get merged knowledge ids
                cursor = conn.execute("""
                    SELECT merged_from_ids
                    FROM combined_knowledge
                    WHERE deleted = 0
                """)
                merged_rows = cursor.fetchall()

            knowledge_list = []
            merged_ids = set()

            for row in merged_rows:
                merged = row["merged_from_ids"]
                if not merged:
                    continue
                try:
                    for item_id in json.loads(merged):
                        merged_ids.add(item_id)
                except (TypeError, json.JSONDecodeError):
                    continue

            for row in rows:
                if row["id"] in merged_ids:
                    continue

                knowledge_list.append(
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

            return knowledge_list

        except Exception as e:
            logger.error(f"Failed to get unmerged knowledge: {e}")
            return []

    async def save_combined_knowledge(self, combined: Dict[str, Any]) -> bool:
        """
        Save combined_knowledge to database

        Args:
            combined: combined_knowledge data dictionary

        Returns:
            Whether save was successful
        """
        try:
            query = """
                INSERT INTO combined_knowledge (id, title, description, keywords, merged_from_ids, created_at, deleted)
                VALUES (?, ?, ?, ?, ?, ?, 0)
            """
            keywords_json = json.dumps(combined.get("keywords", []), ensure_ascii=False)
            merged_from_ids_json = json.dumps(
                combined.get("merged_from_ids", []), ensure_ascii=False
            )
            created_at = combined.get("created_at")
            if isinstance(created_at, datetime):
                created_at = created_at.isoformat()

            params = (
                combined["id"],
                combined["title"],
                combined["description"],
                keywords_json,
                merged_from_ids_json,
                created_at or datetime.now().isoformat(),
            )

            with self._get_conn() as conn:
                conn.execute(query, params)
                conn.commit()

            logger.debug(f"CombinedKnowledge saved: {combined['id']}")
            return True

        except Exception as e:
            logger.error(f"Failed to save combined_knowledge: {e}")
            return False

    async def get_knowledge_list(
        self, include_deleted: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get knowledge list (prioritize returning combined)

        Args:
            include_deleted: Whether to include deleted ones

        Returns:
            Knowledge list
        """
        try:
            # First get combined_knowledge
            if include_deleted:
                query = """
                    SELECT id, title, description, keywords, merged_from_ids, created_at, deleted
                    FROM combined_knowledge
                    ORDER BY created_at DESC
                """
            else:
                query = """
                    SELECT id, title, description, keywords, merged_from_ids, created_at, deleted
                    FROM combined_knowledge
                    WHERE deleted = 0
                    ORDER BY created_at DESC
                """

            with self._get_conn() as conn:
                cursor = conn.execute(query)
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
                if include_deleted:
                    query = """
                        SELECT id, title, description, keywords, created_at, deleted
                        FROM knowledge
                        ORDER BY created_at DESC
                    """
                else:
                    query = """
                        SELECT id, title, description, keywords, created_at, deleted
                        FROM knowledge
                        WHERE deleted = 0
                        ORDER BY created_at DESC
                    """

                with self._get_conn() as conn:
                    cursor = conn.execute(query)
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
            logger.error(f"Failed to get knowledge list: {e}")
            return []

    async def delete_knowledge(self, knowledge_id: str) -> bool:
        """
        Delete knowledge (soft delete)

        Args:
            knowledge_id: knowledge ID

        Returns:
            Whether successful
        """
        try:
            # First try to delete from combined_knowledge
            query1 = "UPDATE combined_knowledge SET deleted = 1 WHERE id = ?"
            query2 = "UPDATE knowledge SET deleted = 1 WHERE id = ?"

            with self._get_conn() as conn:
                cursor = conn.execute(query1, (knowledge_id,))
                if cursor.rowcount == 0:
                    # If not in combined, delete from original knowledge
                    conn.execute(query2, (knowledge_id,))
                conn.commit()

            logger.debug(f"Knowledge deleted: {knowledge_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete knowledge: {e}")
            return False

    async def delete_knowledge_batch(self, knowledge_ids: List[str]) -> int:
        """
        Soft delete a batch of knowledge records.

        Args:
            knowledge_ids: List of knowledge IDs to mark deleted

        Returns:
            Count of rows affected
        """
        if not knowledge_ids:
            return 0

        try:
            placeholders = ",".join("?" for _ in knowledge_ids)
            query = f"""
                UPDATE knowledge
                SET deleted = 1
                WHERE deleted = 0 AND id IN ({placeholders})
            """

            with self._get_conn() as conn:
                cursor = conn.execute(query, knowledge_ids)
                conn.commit()
                affected = cursor.rowcount

            logger.debug(f"Batch deleted {affected} knowledge records")
            return affected

        except Exception as e:
            logger.error(f"Failed to batch delete knowledge: {e}")
            return 0

    # ============ Todo Related Methods ============

    async def save_todo(self, todo: Dict[str, Any]) -> bool:
        """
        Save todo to database

        Args:
            todo: todo data dictionary

        Returns:
            Whether save was successful
        """
        try:
            query = """
                INSERT INTO todos (id, title, description, keywords, created_at, completed, deleted)
                VALUES (?, ?, ?, ?, ?, ?, 0)
            """
            keywords_json = json.dumps(todo.get("keywords", []), ensure_ascii=False)
            created_at = todo.get("created_at")
            if isinstance(created_at, datetime):
                created_at = created_at.isoformat()

            params = (
                todo["id"],
                todo["title"],
                todo["description"],
                keywords_json,
                created_at or datetime.now().isoformat(),
                int(todo.get("completed", False)),
            )

            with self._get_conn() as conn:
                conn.execute(query, params)
                conn.commit()

            logger.debug(f"Todo saved: {todo['id']}")
            return True

        except Exception as e:
            logger.error(f"Failed to save todo: {e}")
            return False

    async def get_unmerged_todos(self) -> List[Dict[str, Any]]:
        """
        Get unmerged todos

        Returns:
            Todo list
        """
        try:
            query = """
                SELECT t.id, t.title, t.description, t.keywords, t.created_at, t.completed
                FROM todos t
                WHERE t.deleted = 0
                ORDER BY t.created_at ASC
            """

            with self._get_conn() as conn:
                cursor = conn.execute(query)
                rows = cursor.fetchall()

                # Get merged todos ids
                cursor = conn.execute("""
                    SELECT merged_from_ids
                    FROM combined_todos
                    WHERE deleted = 0
                """)
                merged_rows = cursor.fetchall()

            todo_list = []
            merged_ids = set()

            for row in merged_rows:
                merged = row["merged_from_ids"]
                if not merged:
                    continue
                try:
                    for item_id in json.loads(merged):
                        merged_ids.add(item_id)
                except (TypeError, json.JSONDecodeError):
                    continue

            for row in rows:
                if row["id"] in merged_ids:
                    continue

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
                    }
                )

            return todo_list

        except Exception as e:
            logger.error(f"Failed to get unmerged todos: {e}")
            return []

    async def save_combined_todo(self, combined: Dict[str, Any]) -> bool:
        """
        Save combined_todo to database

        Args:
            combined: combined_todo data dictionary

        Returns:
            Whether save was successful
        """
        try:
            query = """
                INSERT INTO combined_todos (id, title, description, keywords, merged_from_ids, created_at, completed, deleted)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0)
            """
            keywords_json = json.dumps(combined.get("keywords", []), ensure_ascii=False)
            merged_from_ids_json = json.dumps(
                combined.get("merged_from_ids", []), ensure_ascii=False
            )
            created_at = combined.get("created_at")
            if isinstance(created_at, datetime):
                created_at = created_at.isoformat()

            params = (
                combined["id"],
                combined["title"],
                combined["description"],
                keywords_json,
                merged_from_ids_json,
                created_at or datetime.now().isoformat(),
                int(combined.get("completed", False)),
            )

            with self._get_conn() as conn:
                conn.execute(query, params)
                conn.commit()

            logger.debug(f"CombinedTodo saved: {combined['id']}")
            return True

        except Exception as e:
            logger.error(f"Failed to save combined_todo: {e}")
            return False

    async def get_todo_list(
        self, include_completed: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get todo list (prioritize returning combined)

        Args:
            include_completed: Whether to include completed ones

        Returns:
            Todo list
        """
        try:
            # First get combined_todos
            if include_completed:
                query = """
                    SELECT id, title, description, keywords, merged_from_ids, created_at, completed, deleted, scheduled_date
                    FROM combined_todos
                    WHERE deleted = 0
                    ORDER BY completed ASC, created_at DESC
                """
            else:
                query = """
                    SELECT id, title, description, keywords, merged_from_ids, created_at, completed, deleted, scheduled_date
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
                        "type": "combined",
                    }
                )

            # If no combined_todos, return original todos
            if not todo_list:
                if include_completed:
                    query = """
                        SELECT id, title, description, keywords, created_at, completed, deleted, scheduled_date
                        FROM todos
                        WHERE deleted = 0
                        ORDER BY completed ASC, created_at DESC
                    """
                else:
                    query = """
                        SELECT id, title, description, keywords, created_at, completed, deleted, scheduled_date
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
                            "type": "original",
                        }
                    )

            return todo_list

        except Exception as e:
            logger.error(f"Failed to get todo list: {e}")
            return []

    async def schedule_todo(
        self, todo_id: str, scheduled_date: str
    ) -> Optional[Dict[str, Any]]:
        """
        Schedule todo to a specific date

        Args:
            todo_id: todo ID
            scheduled_date: scheduled date in YYYY-MM-DD format

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
                    SET scheduled_date = ?
                    WHERE id = ? AND deleted = 0
                    """,
                    (scheduled_date, todo_id),
                )
                conn.commit()

                # Check if update was successful
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
                        "type": "combined",
                    }

                # If not found in combined_todos, try original todos
                cursor.execute(
                    """
                    UPDATE todos
                    SET scheduled_date = ?
                    WHERE id = ? AND deleted = 0
                    """,
                    (scheduled_date, todo_id),
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
                        "type": "original",
                    }

                return None

        except Exception as e:
            logger.error(f"Failed to schedule todo: {e}", exc_info=True)
            return None

    async def unschedule_todo(self, todo_id: str) -> Optional[Dict[str, Any]]:
        """
        Unschedule todo (remove scheduled date)

        Args:
            todo_id: todo ID

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
                    SET scheduled_date = NULL
                    WHERE id = ? AND deleted = 0
                    """,
                    (todo_id,),
                )
                conn.commit()

                # Check if update was successful
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
                        "type": "combined",
                    }

                # If not found in combined_todos, try original todos
                cursor.execute(
                    """
                    UPDATE todos
                    SET scheduled_date = NULL
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
                        "type": "original",
                    }

                return None

        except Exception as e:
            logger.error(f"Failed to unschedule todo: {e}", exc_info=True)
            return None

    async def delete_todo(self, todo_id: str) -> bool:
        """
        Delete todo (soft delete)

        Args:
            todo_id: todo ID

        Returns:
            Whether successful
        """
        try:
            # First try to delete from combined_todos
            query1 = "UPDATE combined_todos SET deleted = 1 WHERE id = ?"
            query2 = "UPDATE todos SET deleted = 1 WHERE id = ?"

            with self._get_conn() as conn:
                cursor = conn.execute(query1, (todo_id,))
                if cursor.rowcount == 0:
                    # If not in combined, delete from original todos
                    conn.execute(query2, (todo_id,))
                conn.commit()

            logger.debug(f"Todo deleted: {todo_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete todo: {e}")
            return False

    async def delete_todo_batch(self, todo_ids: List[str]) -> int:
        """
        Soft delete a batch of todo records.

        Args:
            todo_ids: List of todo IDs to mark deleted

        Returns:
            Count of rows affected
        """
        if not todo_ids:
            return 0

        try:
            placeholders = ",".join("?" for _ in todo_ids)
            query = f"""
                UPDATE todos
                SET deleted = 1
                WHERE deleted = 0 AND id IN ({placeholders})
            """

            with self._get_conn() as conn:
                cursor = conn.execute(query, todo_ids)
                conn.commit()
                affected = cursor.rowcount

            logger.debug(f"Batch deleted {affected} todos")
            return affected

        except Exception as e:
            logger.error(f"Failed to batch delete todos: {e}")
            return 0

    # ============ Activity Related Methods ============

    async def save_activity(self, activity: Dict[str, Any]) -> bool:
        """
        Save activity to database

        Args:
            activity: activity data dictionary

        Returns:
            Whether save was successful
        """
        try:
            query = """
                INSERT INTO activities (id, title, description, start_time, end_time, source_event_ids, created_at, deleted)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0)
            """
            source_event_ids_json = json.dumps(
                activity.get("source_event_ids", []), ensure_ascii=False
            )

            start_time = activity.get("start_time")
            if isinstance(start_time, datetime):
                start_time = start_time.isoformat()

            end_time = activity.get("end_time")
            if isinstance(end_time, datetime):
                end_time = end_time.isoformat()

            created_at = activity.get("created_at")
            if isinstance(created_at, datetime):
                created_at = created_at.isoformat()

            params = (
                activity["id"],
                activity["title"],
                activity["description"],
                start_time,
                end_time,
                source_event_ids_json,
                created_at or datetime.now().isoformat(),
            )

            with self._get_conn() as conn:
                conn.execute(query, params)
                conn.commit()

            logger.debug(f"Activity saved: {activity['id']}")
            return True

        except Exception as e:
            logger.error(f"Failed to save activity: {e}")
            return False

    async def get_recent_activities(
        self, limit: int = 10, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get recent activities

        Args:
            limit: Return count
            offset: Offset (for pagination)

        Returns:
            Activity list
        """
        try:
            query = """
                SELECT id, title, description, start_time, end_time, source_event_ids, created_at
                FROM activities
                WHERE deleted = 0
                ORDER BY start_time DESC
                LIMIT ? OFFSET ?
            """

            with self._get_conn() as conn:
                cursor = conn.execute(query, (limit, offset))
                rows = cursor.fetchall()

            activities = []
            for row in rows:
                activities.append(
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
                )

            return activities

        except Exception as e:
            logger.error(f"Failed to get recent activities: {e}")
            return []

    async def get_activity_by_id(self, activity_id: str) -> Optional[Dict[str, Any]]:
        """Get activity details by ID"""
        try:
            query = """
                SELECT id, title, description, start_time, end_time, source_event_ids, created_at
                FROM activities
                WHERE id = ? AND deleted = 0
            """

            with self._get_conn() as conn:
                cursor = conn.execute(query, (activity_id,))
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
            logger.error(f"Failed to get activity by ID: {e}")
            return None

    async def get_events_by_ids(self, event_ids: List[str]) -> List[Dict[str, Any]]:
        """Batch get event details"""
        if not event_ids:
            return []

        try:
            placeholders = ",".join(["?"] * len(event_ids))
            query = f"""
                SELECT id, title, description, keywords, timestamp, created_at
                FROM events
                WHERE id IN ({placeholders}) AND deleted = 0
            """

            with self._get_conn() as conn:
                cursor = conn.execute(query, tuple(event_ids))
                rows = cursor.fetchall()

            events: List[Dict[str, Any]] = []
            for row in rows:
                events.append(
                    {
                        "id": row["id"],
                        "title": row["title"],
                        "description": row["description"],
                        "keywords": json.loads(row["keywords"])
                        if row["keywords"]
                        else [],
                        "timestamp": row["timestamp"],
                        "created_at": row["created_at"],
                    }
                )

            return events

        except Exception as e:
            logger.error(f"Failed to batch get events: {e}")
            return []

    async def delete_activity(self, activity_id: str) -> bool:
        """Soft delete specified activity"""
        try:
            query = "UPDATE activities SET deleted = 1 WHERE id = ?"
            with self._get_conn() as conn:
                cursor = conn.execute(query, (activity_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to delete activity: {e}")
            return False

    async def delete_event(self, event_id: str) -> bool:
        """Soft delete specified event"""
        try:
            query = "UPDATE events SET deleted = 1 WHERE id = ? AND deleted = 0"
            with self._get_conn() as conn:
                cursor = conn.execute(query, (event_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to delete event: {e}")
            return False

    async def get_activities_by_date(self, date_str: str) -> List[Dict[str, Any]]:
        """
        Get all activities for specified date

        Args:
            date_str: Date string (YYYY-MM-DD)

        Returns:
            Activity list
        """
        try:
            # Parse date
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            start_datetime = datetime.combine(target_date, datetime.min.time())
            end_datetime = datetime.combine(target_date, datetime.max.time())

            query = """
                SELECT id, title, description, start_time, end_time, source_event_ids, created_at
                FROM activities
                WHERE deleted = 0
                  AND start_time >= ?
                  AND start_time <= ?
                ORDER BY start_time ASC
            """

            with self._get_conn() as conn:
                cursor = conn.execute(
                    query, (start_datetime.isoformat(), end_datetime.isoformat())
                )
                rows = cursor.fetchall()

            activities = []
            for row in rows:
                activities.append(
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
                )

            return activities

        except Exception as e:
            logger.error(f"Failed to get activities for specified date: {e}")
            return []

    async def get_activity_count_by_date(self) -> List[Dict[str, Any]]:
        """
        Get activity count grouped by date

        Returns:
            List of dict with 'date' and 'count' keys
        """
        try:
            from core.sqls import queries

            with self._get_conn() as conn:
                cursor = conn.execute(queries.SELECT_ACTIVITY_COUNT_BY_DATE)
                rows = cursor.fetchall()

            result = []
            for row in rows:
                result.append({"date": row["date"], "count": row["count"]})

            return result

        except Exception as e:
            logger.error(f"Failed to get activity count by date: {e}")
            return []

    async def get_event_count_by_date(self) -> List[Dict[str, Any]]:
        """
        Get event count grouped by date

        Returns:
            List of dict with 'date' and 'count' keys
        """
        try:
            from core.sqls import queries

            with self._get_conn() as conn:
                cursor = conn.execute(queries.SELECT_EVENT_COUNT_BY_DATE)
                rows = cursor.fetchall()

            result = []
            for row in rows:
                result.append({"date": row["date"], "count": row["count"]})

            return result

        except Exception as e:
            logger.error(f"Failed to get event count by date: {e}")
            return []

    async def get_knowledge_count_by_date(self) -> List[Dict[str, Any]]:
        """
        Get combined knowledge count grouped by date

        Returns:
            List of dict with 'date' and 'count' keys
        """
        try:
            from core.sqls import queries

            with self._get_conn() as conn:
                cursor = conn.execute(queries.SELECT_COMBINED_KNOWLEDGE_COUNT_BY_DATE)
                rows = cursor.fetchall()

            result = []
            for row in rows:
                result.append({"date": row["date"], "count": row["count"]})

            # If no combined knowledge, fall back to regular knowledge
            if not result:
                with self._get_conn() as conn:
                    cursor = conn.execute(queries.SELECT_KNOWLEDGE_COUNT_BY_DATE)
                    rows = cursor.fetchall()

                for row in rows:
                    result.append({"date": row["date"], "count": row["count"]})

            return result

        except Exception as e:
            logger.error(f"Failed to get knowledge count by date: {e}")
            return []

    # ============ Diary Related Methods ============

    async def save_diary(self, diary: Dict[str, Any]) -> bool:
        """
        Save diary to database

        Args:
            diary: diary data dictionary

        Returns:
            Whether save was successful
        """
        try:
            query = """
                INSERT OR REPLACE INTO diaries (id, date, content, source_activity_ids, created_at, deleted)
                VALUES (?, ?, ?, ?, ?, 0)
            """
            source_activity_ids_json = json.dumps(
                diary.get("source_activity_ids", []), ensure_ascii=False
            )
            created_at = diary.get("created_at")
            if isinstance(created_at, datetime):
                created_at = created_at.isoformat()

            params = (
                diary["id"],
                diary["date"],
                diary["content"],
                source_activity_ids_json,
                created_at or datetime.now().isoformat(),
            )

            with self._get_conn() as conn:
                conn.execute(query, params)
                conn.commit()

            logger.debug(f"Diary saved: {diary['date']}")
            return True

        except Exception as e:
            logger.error(f"Failed to save diary: {e}")
            return False

    async def get_diary_by_date(self, date_str: str) -> Optional[Dict[str, Any]]:
        """
        Get diary for specified date

        Args:
            date_str: Date string (YYYY-MM-DD)

        Returns:
            Diary data or None
        """
        try:
            query = """
                SELECT id, date, content, source_activity_ids, created_at
                FROM diaries
                WHERE date = ? AND deleted = 0
            """

            with self._get_conn() as conn:
                cursor = conn.execute(query, (date_str,))
                row = cursor.fetchone()

            if row:
                return {
                    "id": row["id"],
                    "date": row["date"],
                    "content": row["content"],
                    "source_activity_ids": json.loads(row["source_activity_ids"])
                    if row["source_activity_ids"]
                    else [],
                    "created_at": row["created_at"],
                }
            return None

        except Exception as e:
            logger.error(f"Failed to get diary: {e}")
            return None

    async def delete_diary(self, diary_id: str) -> bool:
        """
        Delete diary (soft delete)

        Args:
            diary_id: diary ID

        Returns:
            Whether successful
        """
        try:
            query = "UPDATE diaries SET deleted = 1 WHERE id = ?"

            with self._get_conn() as conn:
                conn.execute(query, (diary_id,))
                conn.commit()

            logger.debug(f"Diary deleted: {diary_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete diary: {e}")
            return False

    # ============ Batch Delete Methods ============

    async def delete_activities_by_date(self, start_date: str, end_date: str) -> int:
        """
        Delete activities in date range (soft delete)

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            Number of activities deleted
        """
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            end_dt = datetime.combine(end_dt, datetime.max.time())

            query = """
                UPDATE activities
                SET deleted = 1
                WHERE deleted = 0
                  AND start_time >= ?
                  AND start_time <= ?
            """

            with self._get_conn() as conn:
                cursor = conn.execute(query, (start_dt.isoformat(), end_dt.isoformat()))
                conn.commit()
                affected = cursor.rowcount

            logger.info(
                f"Deleted {affected} activities between {start_date} and {end_date}"
            )
            return affected

        except Exception as e:
            logger.error(f"Failed to delete activities by date range: {e}")
            return 0

    async def delete_knowledge_by_date(self, start_date: str, end_date: str) -> int:
        """
        Delete knowledge in date range (soft delete)

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            Number of knowledge records deleted
        """
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").isoformat()
            end_dt = datetime.combine(
                datetime.strptime(end_date, "%Y-%m-%d"), datetime.max.time()
            ).isoformat()

            deleted_count = 0

            with self._get_conn() as conn:
                # Delete from combined_knowledge
                cursor = conn.execute(
                    """
                    UPDATE combined_knowledge
                    SET deleted = 1
                    WHERE deleted = 0
                      AND created_at >= ?
                      AND created_at <= ?
                    """,
                    (start_dt, end_dt),
                )
                deleted_count += cursor.rowcount

                # Delete from regular knowledge
                cursor = conn.execute(
                    """
                    UPDATE knowledge
                    SET deleted = 1
                    WHERE deleted = 0
                      AND created_at >= ?
                      AND created_at <= ?
                    """,
                    (start_dt, end_dt),
                )
                deleted_count += cursor.rowcount

                conn.commit()

            logger.info(
                f"Deleted {deleted_count} knowledge records between {start_date} and {end_date}"
            )
            return deleted_count

        except Exception as e:
            logger.error(f"Failed to delete knowledge by date range: {e}")
            return 0

    async def delete_todos_by_date(self, start_date: str, end_date: str) -> int:
        """
        Delete todos in date range (soft delete)

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            Number of todo records deleted
        """
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").isoformat()
            end_dt = datetime.combine(
                datetime.strptime(end_date, "%Y-%m-%d"), datetime.max.time()
            ).isoformat()

            deleted_count = 0

            with self._get_conn() as conn:
                # Delete from combined_todos
                cursor = conn.execute(
                    """
                    UPDATE combined_todos
                    SET deleted = 1
                    WHERE deleted = 0
                      AND created_at >= ?
                      AND created_at <= ?
                    """,
                    (start_dt, end_dt),
                )
                deleted_count += cursor.rowcount

                # Delete from regular todos
                cursor = conn.execute(
                    """
                    UPDATE todos
                    SET deleted = 1
                    WHERE deleted = 0
                      AND created_at >= ?
                      AND created_at <= ?
                    """,
                    (start_dt, end_dt),
                )
                deleted_count += cursor.rowcount

                conn.commit()

            logger.info(
                f"Deleted {deleted_count} todos between {start_date} and {end_date}"
            )
            return deleted_count

        except Exception as e:
            logger.error(f"Failed to delete todos by date range: {e}")
            return 0

    async def delete_diaries_by_date(self, start_date: str, end_date: str) -> int:
        """
        Delete diaries in date range (soft delete)

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            Number of diary records deleted
        """
        try:
            query = """
                UPDATE diaries
                SET deleted = 1
                WHERE deleted = 0
                  AND date >= ?
                  AND date <= ?
            """

            with self._get_conn() as conn:
                cursor = conn.execute(query, (start_date, end_date))
                conn.commit()
                affected = cursor.rowcount

            logger.info(
                f"Deleted {affected} diaries between {start_date} and {end_date}"
            )
            return affected

        except Exception as e:
            logger.error(f"Failed to delete diaries by date range: {e}")
            return 0

    async def delete_old_data(self, days: int = 30) -> Dict[str, Any]:
        """Clean up data older than specified days"""
        try:
            cutoff = datetime.now() - timedelta(days=days)
            cutoff_iso = cutoff.isoformat()

            deleted_counts = {
                "events": 0,
                "activities": 0,
                "knowledge": 0,
                "todos": 0,
                "combinedKnowledge": 0,
                "combinedTodos": 0,
                "diaries": 0,
            }

            with self._get_conn() as conn:
                conn.execute(
                    "DELETE FROM event_images WHERE event_id IN (SELECT id FROM events WHERE timestamp < ?)",
                    (cutoff_iso,),
                )
                cursor = conn.execute(
                    "DELETE FROM events WHERE timestamp < ?", (cutoff_iso,)
                )
                deleted_counts["events"] = cursor.rowcount

                cursor = conn.execute(
                    "UPDATE activities SET deleted = 1 WHERE deleted = 0 AND start_time < ?",
                    (cutoff_iso,),
                )
                deleted_counts["activities"] = cursor.rowcount

                cursor = conn.execute(
                    "UPDATE knowledge SET deleted = 1 WHERE deleted = 0 AND created_at < ?",
                    (cutoff_iso,),
                )
                deleted_counts["knowledge"] = cursor.rowcount

                cursor = conn.execute(
                    "UPDATE todos SET deleted = 1 WHERE deleted = 0 AND created_at < ?",
                    (cutoff_iso,),
                )
                deleted_counts["todos"] = cursor.rowcount

                cursor = conn.execute(
                    "UPDATE combined_knowledge SET deleted = 1 WHERE deleted = 0 AND created_at < ?",
                    (cutoff_iso,),
                )
                deleted_counts["combinedKnowledge"] = cursor.rowcount

                cursor = conn.execute(
                    "UPDATE combined_todos SET deleted = 1 WHERE deleted = 0 AND created_at < ?",
                    (cutoff_iso,),
                )
                deleted_counts["combinedTodos"] = cursor.rowcount

                cursor = conn.execute(
                    "UPDATE diaries SET deleted = 1 WHERE deleted = 0 AND date < ?",
                    (cutoff.strftime("%Y-%m-%d"),),
                )
                deleted_counts["diaries"] = cursor.rowcount

                conn.commit()

            return deleted_counts

        except Exception as e:
            logger.error(f"Failed to clean up old data: {e}")
            return {"error": str(e)}  # type: ignore[return-value]

    def get_stats(self) -> Dict[str, Any]:
        """Get persistence layer statistics information"""
        try:
            stats = {}
            with self._get_conn() as conn:
                for table in [
                    "events",
                    "activities",
                    "knowledge",
                    "todos",
                    "combined_knowledge",
                    "combined_todos",
                    "diaries",
                ]:
                    cursor = conn.execute(
                        f"SELECT COUNT(1) AS count FROM {table} WHERE deleted = 0"
                        if table
                        in [
                            "activities",
                            "knowledge",
                            "todos",
                            "combined_knowledge",
                            "combined_todos",
                            "diaries",
                        ]
                        else f"SELECT COUNT(1) AS count FROM {table}"
                    )
                    row = cursor.fetchone()
                    stats[table] = row["count"] if row else 0

                db_path = self.db_path or Path(__file__).parent.parent / "db" / "ido.db"
                try:
                    size_bytes = Path(db_path).stat().st_size
                except OSError:
                    size_bytes = 0

            stats["databasePath"] = str(db_path)
            stats["databaseSize"] = size_bytes
            return stats

        except Exception as e:
            logger.error(f"Failed to get persistence statistics: {e}")
            return {"error": str(e)}

    async def get_diary_list(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get latest diary list

                Args:
                    limit: Return count

                Returns:
                    Diary list
        """
        try:
            query = """
                SELECT id, date, content, source_activity_ids, created_at
                FROM diaries
                WHERE deleted = 0
                ORDER BY date DESC
                LIMIT ?
            """

            with self._get_conn() as conn:
                cursor = conn.execute(query, (limit,))
                rows = cursor.fetchall()

            diaries = []
            for row in rows:
                diaries.append(
                    {
                        "id": row["id"],
                        "date": row["date"],
                        "content": row["content"],
                        "source_activity_ids": json.loads(row["source_activity_ids"])
                        if row["source_activity_ids"]
                        else [],
                        "created_at": row["created_at"],
                    }
                )

            return diaries

        except Exception as e:
            logger.error(f"Failed to get diary list: {e}")
            return []
