"""
SQLite database wrapper
Provides basic operations like connection, query, insert, update
"""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.logger import get_logger

logger = get_logger(__name__)


class DatabaseManager:
    """Database manager"""

    def __init__(self, db_path: Optional[str] = None):
        # If no path is provided, use the unified data directory
        if db_path is None:
            from core.paths import get_db_path

            db_path = str(get_db_path())

        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Initialize database"""
        # Ensure database directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        # Create tables
        self._create_tables()
        logger.info(f"Database initialization completed: {self.db_path}")

    def _create_tables(self):
        """Create database tables"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Create raw_records table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS raw_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    type TEXT NOT NULL,
                    data TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create events table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    start_time TEXT,
                    end_time TEXT,
                    type TEXT,
                    summary TEXT,
                    source_data TEXT,
                    title TEXT DEFAULT '',
                    description TEXT DEFAULT '',
                    keywords TEXT,
                    timestamp TEXT,
                    deleted BOOLEAN DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create activities table (includes version field for incremental updates)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS activities (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    source_events TEXT,
                    source_event_ids TEXT,
                    version INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    deleted BOOLEAN DEFAULT 0
                )
            """)

            # Create tasks table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    status TEXT NOT NULL,
                    agent_type TEXT,
                    parameters TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create settings table (stores persistent configuration)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    type TEXT NOT NULL,
                    description TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create conversations table (conversations)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    related_activity_ids TEXT,
                    metadata TEXT
                )
            """)

            # Create messages table (messages)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
                    content TEXT NOT NULL,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
                )
            """)

            # Create llm_token_usage table (LLM Token usage statistics)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS llm_token_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    model TEXT NOT NULL,
                    prompt_tokens INTEGER NOT NULL DEFAULT 0,
                    completion_tokens INTEGER NOT NULL DEFAULT 0,
                    total_tokens INTEGER NOT NULL DEFAULT 0,
                    cost REAL DEFAULT 0.0,
                    request_type TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create event_images table (screenshot hashes corresponding to events)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS event_images (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL,
                    hash TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
                    UNIQUE(event_id, hash)
                )
            """)

            # Create llm_models table (model configuration)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS llm_models (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    provider TEXT NOT NULL,
                    api_url TEXT NOT NULL,
                    model TEXT NOT NULL,
                    api_key TEXT NOT NULL,
                    input_token_price REAL NOT NULL DEFAULT 0.0,
                    output_token_price REAL NOT NULL DEFAULT 0.0,
                    currency TEXT DEFAULT 'USD',
                    is_active INTEGER DEFAULT 0,
                    last_test_status INTEGER DEFAULT 0,
                    last_tested_at TEXT,
                    last_test_error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    CHECK(input_token_price >= 0),
                    CHECK(output_token_price >= 0)
                )
            """)

            # Create indexes to optimize query performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_conversation
                ON messages(conversation_id, timestamp DESC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversations_updated
                ON conversations(updated_at DESC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_event_images_event_id
                ON event_images(event_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_event_images_hash
                ON event_images(hash)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_llm_usage_timestamp
                ON llm_token_usage(timestamp DESC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_llm_usage_model
                ON llm_token_usage(model)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_llm_models_provider
                ON llm_models(provider)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_llm_models_is_active
                ON llm_models(is_active)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_llm_models_created_at
                ON llm_models(created_at DESC)
            """)

            conn.commit()
            # Check if tables need migration (add new fields)
            self._migrate_events_table(cursor, conn)
            self._migrate_activities_table(cursor, conn)
            self._migrate_llm_models_table(cursor, conn)
            logger.info("Database table creation completed")

    def _migrate_events_table(self, cursor, conn):
        """Migrate events table: add title, description, keywords, timestamp columns for new architecture compatibility, and modify NOT NULL constraints"""
        try:
            cursor.execute("PRAGMA table_info(events)")
            columns = {row[1]: row for row in cursor.fetchall()}

            # Check if NOT NULL constraints need to be modified
            needs_constraint_fix = False
            for col_name in [
                "start_time",
                "end_time",
                "type",
                "summary",
                "source_data",
            ]:
                if col_name in columns:
                    # columns[col_name][3] is the notnull flag (1 = NOT NULL, 0 = NULL)
                    if columns[col_name][3] == 1:  # If NOT NULL
                        needs_constraint_fix = True
                        break

            # If constraints need to be modified, rebuild table
            if needs_constraint_fix:
                logger.info(
                    "Detected events table needs NOT NULL constraint modification, rebuilding table..."
                )
                # Create temporary table
                cursor.execute("""
                    CREATE TABLE events_new (
                        id TEXT PRIMARY KEY,
                        start_time TEXT,
                        end_time TEXT,
                        type TEXT,
                        summary TEXT,
                        source_data TEXT,
                        title TEXT DEFAULT '',
                        description TEXT DEFAULT '',
                        keywords TEXT,
                        timestamp TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Migrate data
                cursor.execute("""
                    INSERT INTO events_new (
                        id, start_time, end_time, type, summary, source_data,
                        title, description, keywords, timestamp, created_at
                    )
                    SELECT
                        id, start_time, end_time, type, summary, source_data,
                        COALESCE(title, SUBSTR(COALESCE(summary, ''), 1, 100)),
                        COALESCE(description, COALESCE(summary, '')),
                        keywords, timestamp, created_at
                    FROM events
                """)

                # Delete old table
                cursor.execute("DROP TABLE events")

                # Rename new table
                cursor.execute("ALTER TABLE events_new RENAME TO events")

                # Rebuild indexes
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_events_timestamp
                    ON events(timestamp DESC)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_events_created
                    ON events(created_at DESC)
                """)

                conn.commit()
                logger.info("Events table NOT NULL constraints have been modified")

                # Refresh column information after rebuild
                cursor.execute("PRAGMA table_info(events)")
                columns = {row[1]: row for row in cursor.fetchall()}

            # Add missing columns if they don't exist
            if "title" not in columns:
                cursor.execute("""
                    ALTER TABLE events
                    ADD COLUMN title TEXT DEFAULT ''
                """)
                cursor.execute("""
                    UPDATE events
                    SET title = SUBSTR(COALESCE(summary, ''), 1, 100)
                    WHERE title = '' OR title IS NULL
                """)
                conn.commit()
                logger.info("Added title column to events table")

            if "description" not in columns:
                cursor.execute("""
                    ALTER TABLE events
                    ADD COLUMN description TEXT DEFAULT ''
                """)
                cursor.execute("""
                    UPDATE events
                    SET description = COALESCE(summary, '')
                    WHERE description = '' OR description IS NULL
                """)
                conn.commit()
                logger.info("Added description column to events table")

            if "keywords" not in columns:
                cursor.execute("""
                    ALTER TABLE events
                    ADD COLUMN keywords TEXT DEFAULT NULL
                """)
                conn.commit()
                logger.info("Added keywords column to events table")

            if "timestamp" not in columns:
                cursor.execute("""
                    ALTER TABLE events
                    ADD COLUMN timestamp TEXT DEFAULT NULL
                """)
                cursor.execute("""
                    UPDATE events
                    SET timestamp = start_time
                    WHERE timestamp IS NULL AND start_time IS NOT NULL
                """)
                conn.commit()
                logger.info("Added timestamp column to events table")

            if "deleted" not in columns:
                cursor.execute("""
                    ALTER TABLE events
                    ADD COLUMN deleted BOOLEAN DEFAULT 0
                """)
                conn.commit()
                logger.info("Added deleted column to events table")
        except Exception as e:
            logger.warning(
                f"Error migrating events table (column may already exist): {e}"
            )

    def _migrate_activities_table(self, cursor, conn):
        """Migrate activities table: fix NOT NULL constraints and add missing columns"""
        try:
            # Check if columns exist and their constraints
            cursor.execute("PRAGMA table_info(activities)")
            columns = {row[1]: row for row in cursor.fetchall()}

            # Check if NOT NULL constraints need to be modified
            needs_constraint_fix = False
            for col_name in ["source_events"]:
                if col_name in columns:
                    # columns[col_name][3] is the notnull flag (1 = NOT NULL, 0 = NULL)
                    if columns[col_name][3] == 1:  # If NOT NULL
                        needs_constraint_fix = True
                        break

            # If constraints need to be modified, rebuild table
            if needs_constraint_fix:
                logger.info(
                    "Detected activities table needs NOT NULL constraint modification, rebuilding table..."
                )
                # Create temporary table (with new columns)
                cursor.execute("""
                    CREATE TABLE activities_new (
                        id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        description TEXT NOT NULL,
                        start_time TEXT NOT NULL,
                        end_time TEXT NOT NULL,
                        source_events TEXT,
                        version INTEGER DEFAULT 1,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        deleted BOOLEAN DEFAULT 0,
                        source_event_ids TEXT
                    )
                """)

                # Migrate data
                cursor.execute("""
                    INSERT INTO activities_new (
                        id, title, description, start_time, end_time, source_events,
                        version, created_at, deleted, source_event_ids
                    )
                    SELECT
                        id, COALESCE(title, SUBSTR(description, 1, 50)), description,
                        start_time, end_time, source_events,
                        COALESCE(version, 1), created_at,
                        COALESCE(deleted, 0), source_event_ids
                    FROM activities
                """)

                # Delete old table
                cursor.execute("DROP TABLE activities")

                # Rename new table
                cursor.execute("ALTER TABLE activities_new RENAME TO activities")

                conn.commit()
                logger.info("Activities table NOT NULL constraints have been modified")
            else:
                # Only add missing columns
                column_names = [row[1] for row in columns.values()]

            # Check if columns exist
            cursor.execute("PRAGMA table_info(activities)")
            columns = [row[1] for row in cursor.fetchall()]

            if "version" not in columns:
                # Add version column, new records default to version 1
                cursor.execute("""
                    ALTER TABLE activities
                    ADD COLUMN version INTEGER DEFAULT 1
                """)
                conn.commit()
                logger.info("Added version column to activities table")

            if "title" not in columns:
                # Add title column, use first 50 characters of description as default value for existing records
                cursor.execute("""
                    ALTER TABLE activities
                    ADD COLUMN title TEXT DEFAULT ''
                """)
                # Set title for existing records (using first 50 characters of description)
                cursor.execute("""
                    UPDATE activities
                    SET title = SUBSTR(description, 1, 50)
                    WHERE title = '' OR title IS NULL
                """)
                conn.commit()
                logger.info("Added title column to activities table")

            if "deleted" not in columns:
                cursor.execute("""
                    ALTER TABLE activities
                    ADD COLUMN deleted BOOLEAN DEFAULT 0
                """)
                conn.commit()
                logger.info("Added deleted column to activities table")

            if "source_event_ids" not in columns:
                # Add source_event_ids column (new architecture uses this column name)
                # Note: This may be redundant with source_events column, but keep both for compatibility
                cursor.execute("""
                    ALTER TABLE activities
                    ADD COLUMN source_event_ids TEXT DEFAULT NULL
                """)
                # Extract event IDs from source_events for existing records
                cursor.execute("""
                    UPDATE activities
                    SET source_event_ids = source_events
                    WHERE source_event_ids IS NULL AND source_events IS NOT NULL
                """)
                conn.commit()
                logger.info("Added source_event_ids column to activities table")
        except Exception as e:
            logger.warning(
                f"Error migrating activities table (column may already exist): {e}"
            )

    def _migrate_llm_models_table(self, cursor, conn):
        """Migrate llm_models table: add test status related fields"""
        try:
            cursor.execute("PRAGMA table_info(llm_models)")
            columns = [row[1] for row in cursor.fetchall()]

            if "last_test_status" not in columns:
                cursor.execute(
                    "ALTER TABLE llm_models ADD COLUMN last_test_status INTEGER DEFAULT 0"
                )
            if "last_tested_at" not in columns:
                cursor.execute("ALTER TABLE llm_models ADD COLUMN last_tested_at TEXT")
            if "last_test_error" not in columns:
                cursor.execute("ALTER TABLE llm_models ADD COLUMN last_test_error TEXT")

            conn.commit()
        except Exception as e:
            logger.warning(
                f"Error migrating llm_models table (field may already exist): {e}"
            )

    @contextmanager
    def get_connection(self):
        """Get database connection context manager"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column name access for results
        try:
            yield conn
        finally:
            conn.close()

    def execute_query(self, query: str, params: Tuple = ()) -> List[Dict[str, Any]]:
        """Execute query and return results"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def execute_insert(self, query: str, params: Tuple = ()) -> int:
        """Execute insert operation and return inserted ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.lastrowid or 0

    def execute_update(self, query: str, params: Tuple = ()) -> int:
        """Execute update operation and return affected row count"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount

    def execute_delete(self, query: str, params: Tuple = ()) -> int:
        """Execute delete operation and return affected row count"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount

    # Raw record related methods
    def insert_raw_record(
        self, timestamp: str, event_type: str, data: Dict[str, Any]
    ) -> int:
        """Insert raw record"""
        query = """
            INSERT INTO raw_records (timestamp, type, data)
            VALUES (?, ?, ?)
        """
        params = (timestamp, event_type, json.dumps(data))
        return self.execute_insert(query, params)

    def get_raw_records(
        self, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get raw records"""
        query = """
            SELECT * FROM raw_records
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
        """
        return self.execute_query(query, (limit, offset))

    # Event related methods
    def insert_event(
        self,
        event_id: str,
        start_time: str,
        end_time: str,
        event_type: str,
        summary: str,
        source_data: List[Dict[str, Any]],
    ) -> int:
        """Insert event"""
        query = """
            INSERT INTO events (id, start_time, end_time, type, summary, source_data)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        params = (
            event_id,
            start_time,
            end_time,
            event_type,
            summary,
            json.dumps(source_data),
        )
        return self.execute_insert(query, params)

    def get_events(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Get events"""
        query = """
            SELECT * FROM events
            ORDER BY start_time DESC
            LIMIT ? OFFSET ?
        """
        return self.execute_query(query, (limit, offset))

    # Activity related methods
    def insert_activity(
        self,
        activity_id: str,
        title: str,
        description: str,
        start_time: str,
        end_time: str,
        source_events: List[Dict[str, Any]],
    ) -> int:
        """Insert activity"""
        query = """
            INSERT INTO activities (id, title, description, start_time, end_time, source_events)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        params = (
            activity_id,
            title,
            description,
            start_time,
            end_time,
            json.dumps(source_events),
        )
        return self.execute_insert(query, params)

    def delete_activity(self, activity_id: str) -> int:
        """Delete specified activity"""
        query = """
            DELETE FROM activities
            WHERE id = ?
        """
        return self.execute_delete(query, (activity_id,))

    def get_activities(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Get activities"""
        query = """
            SELECT * FROM activities
            ORDER BY start_time DESC
            LIMIT ? OFFSET ?
        """
        return self.execute_query(query, (limit, offset))

    def get_max_activity_version(self) -> int:
        """Get maximum version number from activities table"""
        query = "SELECT MAX(version) as max_version FROM activities"
        results = self.execute_query(query)
        if results and results[0].get("max_version"):
            return int(results[0]["max_version"])
        return 0

    def get_activities_after_version(
        self, version: int, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get activities after specified version number (incremental update)"""
        query = """
            SELECT * FROM activities
            WHERE version > ?
            ORDER BY version DESC, start_time DESC
            LIMIT ?
        """
        return self.execute_query(query, (version, limit))

    def get_activity_count_by_date(self) -> List[Dict[str, Any]]:
        """Get daily activity count statistics"""
        query = """
            SELECT
                DATE(start_time) as date,
                COUNT(*) as count
            FROM activities
            GROUP BY DATE(start_time)
            ORDER BY date DESC
        """
        return self.execute_query(query)

    # Task related methods
    def insert_task(
        self,
        task_id: str,
        title: str,
        description: str,
        status: str,
        agent_type: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Insert task"""
        query = """
            INSERT INTO tasks (id, title, description, status, agent_type, parameters)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        params = (
            task_id,
            title,
            description,
            status,
            agent_type,
            json.dumps(parameters or {}),
        )
        return self.execute_insert(query, params)

    def update_task_status(self, task_id: str, status: str) -> int:
        """Update task status"""
        query = """
            UPDATE tasks
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """
        return self.execute_update(query, (status, task_id))

    def get_tasks(
        self, status: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get tasks"""
        if status:
            query = """
                SELECT * FROM tasks
                WHERE status = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """
            return self.execute_query(query, (status, limit, offset))
        else:
            query = """
                SELECT * FROM tasks
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """
            return self.execute_query(query, (limit, offset))

    # Configuration related methods
    def set_setting(
        self,
        key: str,
        value: str,
        setting_type: str = "string",
        description: Optional[str] = None,
    ) -> int:
        """Set configuration item"""
        query = """
            INSERT OR REPLACE INTO settings (key, value, type, description, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """
        params = (key, value, setting_type, description)
        return self.execute_insert(query, params)

    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get configuration item"""
        query = "SELECT value FROM settings WHERE key = ?"
        results = self.execute_query(query, (key,))
        if results:
            return results[0]["value"]
        return default

    def get_all_settings(self) -> Dict[str, Any]:
        """Get all configuration items"""
        query = "SELECT key, value, type FROM settings ORDER BY key"
        results = self.execute_query(query)
        settings = {}
        for row in results:
            key = row["key"]
            value = row["value"]
            setting_type = row["type"]

            # Type conversion
            if setting_type == "bool":
                settings[key] = value.lower() in ("true", "1", "yes")
            elif setting_type == "int":
                try:
                    settings[key] = int(value)
                except ValueError:
                    settings[key] = value
            else:
                settings[key] = value
        return settings

    def delete_setting(self, key: str) -> int:
        """Delete configuration item"""
        query = "DELETE FROM settings WHERE key = ?"
        return self.execute_delete(query, (key,))

    # Conversation related methods
    def insert_conversation(
        self,
        conversation_id: str,
        title: str,
        related_activity_ids: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Insert conversation"""
        query = """
            INSERT INTO conversations (id, title, related_activity_ids, metadata)
            VALUES (?, ?, ?, ?)
        """
        params = (
            conversation_id,
            title,
            json.dumps(related_activity_ids or []),
            json.dumps(metadata or {}),
        )
        return self.execute_insert(query, params)

    def get_conversations(
        self, limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get conversation list (ordered by update time DESC)"""
        query = """
            SELECT * FROM conversations
            ORDER BY updated_at DESC
            LIMIT ? OFFSET ?
        """
        return self.execute_query(query, (limit, offset))

    def get_conversation_by_id(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation by ID"""
        query = "SELECT * FROM conversations WHERE id = ?"
        results = self.execute_query(query, (conversation_id,))
        return results[0] if results else None

    def update_conversation(
        self,
        conversation_id: str,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Update conversation"""
        updates = []
        params = []

        if title is not None:
            updates.append("title = ?")
            params.append(title)

        if metadata is not None:
            updates.append("metadata = ?")
            params.append(json.dumps(metadata))

        if not updates:
            return 0

        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(conversation_id)

        query = f"""
            UPDATE conversations
            SET {", ".join(updates)}
            WHERE id = ?
        """
        return self.execute_update(query, tuple(params))

    def delete_conversation(self, conversation_id: str) -> int:
        """Delete conversation (cascades to delete messages)"""
        query = "DELETE FROM conversations WHERE id = ?"
        return self.execute_delete(query, (conversation_id,))

    # Message related methods
    def insert_message(
        self,
        message_id: str,
        conversation_id: str,
        role: str,
        content: str,
        timestamp: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Insert message"""
        query = """
            INSERT INTO messages (id, conversation_id, role, content, timestamp, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        params = (
            message_id,
            conversation_id,
            role,
            content,
            timestamp or datetime.now().isoformat(),
            json.dumps(metadata or {}),
        )
        return self.execute_insert(query, params)

    def get_messages(
        self, conversation_id: str, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get conversation message list (ordered by time ASC)"""
        query = """
            SELECT * FROM messages
            WHERE conversation_id = ?
            ORDER BY timestamp ASC
            LIMIT ? OFFSET ?
        """
        return self.execute_query(query, (conversation_id, limit, offset))

    def get_message_by_id(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Get message by ID"""
        query = "SELECT * FROM messages WHERE id = ?"
        results = self.execute_query(query, (message_id,))
        return results[0] if results else None

    def delete_message(self, message_id: str) -> int:
        """Delete message"""
        query = "DELETE FROM messages WHERE id = ?"
        return self.execute_delete(query, (message_id,))

    def get_message_count(self, conversation_id: str) -> int:
        """Get message count for conversation"""
        query = "SELECT COUNT(*) as count FROM messages WHERE conversation_id = ?"
        results = self.execute_query(query, (conversation_id,))
        return results[0]["count"] if results else 0

    # LLM model management related methods
    def get_active_llm_model(self) -> Optional[Dict[str, Any]]:
        """Get currently active LLM model configuration"""
        query = """
            SELECT
                id,
                name,
                provider,
                api_url,
                model,
                api_key,
                input_token_price,
                output_token_price,
                currency,
                last_test_status,
                last_tested_at,
                last_test_error,
                created_at,
                updated_at
            FROM llm_models
            WHERE is_active = 1
            LIMIT 1
        """
        results = self.execute_query(query)
        return results[0] if results else None

    def get_llm_model_by_id(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Get model configuration by ID (includes API key and test status)"""
        query = """
            SELECT
                id,
                name,
                provider,
                api_url,
                model,
                api_key,
                input_token_price,
                output_token_price,
                currency,
                is_active,
                last_test_status,
                last_tested_at,
                last_test_error,
                created_at,
                updated_at
            FROM llm_models
            WHERE id = ?
            LIMIT 1
        """
        results = self.execute_query(query, (model_id,))
        return results[0] if results else None

    def update_model_test_result(
        self, model_id: str, success: bool, error: Optional[str] = None
    ) -> None:
        """Update model test result"""
        now = datetime.now().isoformat()
        query = """
            UPDATE llm_models
            SET
                last_test_status = ?,
                last_tested_at = ?,
                last_test_error = ?,
                updated_at = ?
            WHERE id = ?
        """
        self.execute_update(query, (1 if success else 0, now, error, now, model_id))


# Global database manager instance
db_manager: Optional[DatabaseManager] = None


def get_db() -> DatabaseManager:
    """Get database manager instance

    Read database path from database.path in config.toml,
    use default path ~/.config/ido/ido.db if not configured
    """
    global db_manager
    if db_manager is None:
        from config.loader import get_config
        from core.paths import get_db_path

        config = get_config()

        # Read database path from config.toml
        configured_path = config.get("database.path", "")

        # If path is configured and not empty, use configured path; otherwise use default path
        if configured_path and configured_path.strip():
            db_path = configured_path
        else:
            db_path = str(get_db_path())

        db_manager = DatabaseManager(db_path)
        logger.info(f"✓ Database manager initialized, path: {db_path}")

    return db_manager


def switch_database(new_db_path: str) -> bool:
    """Switch database to new path (for runtime database location modification)

    Args:
        new_db_path: New database path

    Returns:
        True if switch successful, False otherwise
    """
    global db_manager

    if db_manager is None:
        logger.error("Database manager not initialized")
        return False

    try:
        # Check if new path is the same
        if Path(db_manager.db_path).resolve() == Path(new_db_path).resolve():
            logger.info(
                f"New path is same as current path, no switch needed: {new_db_path}"
            )
            return True

        # Close current connection (DatabaseManager uses context manager, no manual closing needed)
        logger.info(f"Closing current database connection: {db_manager.db_path}")
        # Note: DatabaseManager uses context manager pattern, connections auto-close after use

        # Create directory for new path
        Path(new_db_path).parent.mkdir(parents=True, exist_ok=True)

        # Create new database manager
        db_manager = DatabaseManager(new_db_path)
        logger.info(f"✓ Database switched to: {new_db_path}")
        return True

    except Exception as e:
        logger.error(f"Database switch failed: {e}", exc_info=True)
        return False
