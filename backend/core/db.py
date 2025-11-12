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
from core.sqls import migrations, queries, schema

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

            # Create all tables
            for table_sql in schema.ALL_TABLES:
                cursor.execute(table_sql)

            # Create all indexes
            for index_sql in schema.ALL_INDEXES:
                cursor.execute(index_sql)

            conn.commit()

            # Check if tables need migration (add new fields)
            self._migrate_events_table(cursor, conn)
            self._migrate_activities_table(cursor, conn)
            self._migrate_llm_models_table(cursor, conn)
            self._migrate_messages_table(cursor, conn)
            logger.info("Database table creation completed")

    def _migrate_events_table(self, cursor, conn):
        """Migrate events table: add title, description, keywords, timestamp columns for new architecture compatibility, and modify NOT NULL constraints"""
        try:
            cursor.execute(queries.PRAGMA_TABLE_INFO.format("events"))
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
                cursor.execute(migrations.CREATE_EVENTS_NEW_TABLE)

                # Migrate data
                cursor.execute(migrations.MIGRATE_EVENTS_DATA)

                # Delete old table
                cursor.execute(migrations.DROP_OLD_EVENTS_TABLE)

                # Rename new table
                cursor.execute(migrations.RENAME_EVENTS_TABLE)

                # Rebuild indexes
                cursor.execute(schema.CREATE_EVENTS_TIMESTAMP_INDEX)
                cursor.execute(schema.CREATE_EVENTS_CREATED_INDEX)

                conn.commit()
                logger.info("Events table NOT NULL constraints have been modified")

                # Refresh column information after rebuild
                cursor.execute(queries.PRAGMA_TABLE_INFO.format("events"))
                columns = {row[1]: row for row in cursor.fetchall()}

            # Add missing columns if they don't exist
            if "title" not in columns:
                cursor.execute(migrations.ADD_EVENTS_TITLE_COLUMN)
                cursor.execute(migrations.UPDATE_EVENTS_TITLE)
                conn.commit()
                logger.info("Added title column to events table")

            if "description" not in columns:
                cursor.execute(migrations.ADD_EVENTS_DESCRIPTION_COLUMN)
                cursor.execute(migrations.UPDATE_EVENTS_DESCRIPTION)
                conn.commit()
                logger.info("Added description column to events table")

            if "keywords" not in columns:
                cursor.execute(migrations.ADD_EVENTS_KEYWORDS_COLUMN)
                conn.commit()
                logger.info("Added keywords column to events table")

            if "timestamp" not in columns:
                cursor.execute(migrations.ADD_EVENTS_TIMESTAMP_COLUMN)
                cursor.execute(migrations.UPDATE_EVENTS_TIMESTAMP)
                conn.commit()
                logger.info("Added timestamp column to events table")

            if "deleted" not in columns:
                cursor.execute(migrations.ADD_EVENTS_DELETED_COLUMN)
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
            cursor.execute(queries.PRAGMA_TABLE_INFO.format("activities"))
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
                cursor.execute(migrations.CREATE_ACTIVITIES_NEW_TABLE)

                # Migrate data
                cursor.execute(migrations.MIGRATE_ACTIVITIES_DATA)

                # Delete old table
                cursor.execute(migrations.DROP_OLD_ACTIVITIES_TABLE)

                # Rename new table
                cursor.execute(migrations.RENAME_ACTIVITIES_TABLE)

                conn.commit()
                logger.info("Activities table NOT NULL constraints have been modified")

            # Check if columns exist
            cursor.execute(queries.PRAGMA_TABLE_INFO.format("activities"))
            columns = [row[1] for row in cursor.fetchall()]

            if "version" not in columns:
                # Add version column, new records default to version 1
                cursor.execute(migrations.ADD_ACTIVITIES_VERSION_COLUMN)
                conn.commit()
                logger.info("Added version column to activities table")

            if "title" not in columns:
                # Add title column, use first 50 characters of description as default value for existing records
                cursor.execute(migrations.ADD_ACTIVITIES_TITLE_COLUMN)
                # Set title for existing records (using first 50 characters of description)
                cursor.execute(migrations.UPDATE_ACTIVITIES_TITLE)
                conn.commit()
                logger.info("Added title column to activities table")

            if "deleted" not in columns:
                cursor.execute(migrations.ADD_ACTIVITIES_DELETED_COLUMN)
                conn.commit()
                logger.info("Added deleted column to activities table")

            if "source_event_ids" not in columns:
                # Add source_event_ids column (new architecture uses this column name)
                # Note: This may be redundant with source_events column, but keep both for compatibility
                cursor.execute(migrations.ADD_ACTIVITIES_SOURCE_EVENT_IDS_COLUMN)
                # Extract event IDs from source_events for existing records
                cursor.execute(migrations.UPDATE_ACTIVITIES_SOURCE_EVENT_IDS)
                conn.commit()
                logger.info("Added source_event_ids column to activities table")
        except Exception as e:
            logger.warning(
                f"Error migrating activities table (column may already exist): {e}"
            )

    def _migrate_llm_models_table(self, cursor, conn):
        """Migrate llm_models table: add test status related fields"""
        try:
            cursor.execute(queries.PRAGMA_TABLE_INFO.format("llm_models"))
            columns = [row[1] for row in cursor.fetchall()]

            if "last_test_status" not in columns:
                cursor.execute(migrations.ADD_LLM_MODELS_LAST_TEST_STATUS_COLUMN)
            if "last_tested_at" not in columns:
                cursor.execute(migrations.ADD_LLM_MODELS_LAST_TESTED_AT_COLUMN)
            if "last_test_error" not in columns:
                cursor.execute(migrations.ADD_LLM_MODELS_LAST_TEST_ERROR_COLUMN)

            conn.commit()
        except Exception as e:
            logger.warning(
                f"Error migrating llm_models table (field may already exist): {e}"
            )

    def _migrate_messages_table(self, cursor, conn):
        """Migrate messages table: add images field for multimodal support"""
        try:
            cursor.execute(queries.PRAGMA_TABLE_INFO.format("messages"))
            columns = [row[1] for row in cursor.fetchall()]

            if "images" not in columns:
                cursor.execute(migrations.ADD_MESSAGES_IMAGES_COLUMN)
                logger.info("Added 'images' column to messages table")

            conn.commit()
        except Exception as e:
            logger.warning(
                f"Error migrating messages table (field may already exist): {e}"
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
        params = (timestamp, event_type, json.dumps(data))
        return self.execute_insert(queries.INSERT_RAW_RECORD, params)

    def get_raw_records(
        self, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get raw records"""
        return self.execute_query(queries.SELECT_RAW_RECORDS, (limit, offset))

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
        params = (
            event_id,
            start_time,
            end_time,
            event_type,
            summary,
            json.dumps(source_data),
        )
        return self.execute_insert(queries.INSERT_EVENT, params)

    def get_events(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Get events"""
        return self.execute_query(queries.SELECT_EVENTS, (limit, offset))

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
        params = (
            activity_id,
            title,
            description,
            start_time,
            end_time,
            json.dumps(source_events),
        )
        return self.execute_insert(queries.INSERT_ACTIVITY, params)

    def delete_activity(self, activity_id: str) -> int:
        """Delete specified activity"""
        return self.execute_delete(queries.DELETE_ACTIVITY, (activity_id,))

    def get_activities(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Get activities"""
        return self.execute_query(queries.SELECT_ACTIVITIES, (limit, offset))

    def get_max_activity_version(self) -> int:
        """Get maximum version number from activities table"""
        results = self.execute_query(queries.SELECT_MAX_ACTIVITY_VERSION)
        if results and results[0].get("max_version"):
            return int(results[0]["max_version"])
        return 0

    def get_activities_after_version(
        self, version: int, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get activities after specified version number (incremental update)"""
        return self.execute_query(queries.SELECT_ACTIVITIES_AFTER_VERSION, (version, limit))

    def get_activity_count_by_date(self) -> List[Dict[str, Any]]:
        """Get daily activity count statistics"""
        return self.execute_query(queries.SELECT_ACTIVITY_COUNT_BY_DATE)

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
        params = (
            task_id,
            title,
            description,
            status,
            agent_type,
            json.dumps(parameters or {}),
        )
        return self.execute_insert(queries.INSERT_TASK, params)

    def update_task_status(self, task_id: str, status: str) -> int:
        """Update task status"""
        return self.execute_update(queries.UPDATE_TASK_STATUS, (status, task_id))

    def get_tasks(
        self, status: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get tasks"""
        if status:
            return self.execute_query(queries.SELECT_TASKS_BY_STATUS, (status, limit, offset))
        else:
            return self.execute_query(queries.SELECT_ALL_TASKS, (limit, offset))

    # Configuration related methods
    def set_setting(
        self,
        key: str,
        value: str,
        setting_type: str = "string",
        description: Optional[str] = None,
    ) -> int:
        """Set configuration item"""
        params = (key, value, setting_type, description)
        return self.execute_insert(queries.INSERT_OR_REPLACE_SETTING, params)

    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get configuration item"""
        results = self.execute_query(queries.SELECT_SETTING_BY_KEY, (key,))
        if results:
            return results[0]["value"]
        return default

    def get_all_settings(self) -> Dict[str, Any]:
        """Get all configuration items"""
        results = self.execute_query(queries.SELECT_ALL_SETTINGS)
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
        return self.execute_delete(queries.DELETE_SETTING, (key,))

    # Conversation related methods
    def insert_conversation(
        self,
        conversation_id: str,
        title: str,
        related_activity_ids: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Insert conversation"""
        params = (
            conversation_id,
            title,
            json.dumps(related_activity_ids or []),
            json.dumps(metadata or {}),
        )
        return self.execute_insert(queries.INSERT_CONVERSATION, params)

    def get_conversations(
        self, limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get conversation list (ordered by update time DESC)"""
        return self.execute_query(queries.SELECT_CONVERSATIONS, (limit, offset))

    def get_conversation_by_id(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation by ID"""
        results = self.execute_query(queries.SELECT_CONVERSATION_BY_ID, (conversation_id,))
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
        return self.execute_delete(queries.DELETE_CONVERSATION, (conversation_id,))

    # Message related methods
    def insert_message(
        self,
        message_id: str,
        conversation_id: str,
        role: str,
        content: str,
        timestamp: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        images: Optional[List[str]] = None,
    ) -> int:
        """Insert message"""
        params = (
            message_id,
            conversation_id,
            role,
            content,
            timestamp or datetime.now().isoformat(),
            json.dumps(metadata or {}),
            json.dumps(images or []),
        )
        return self.execute_insert(queries.INSERT_MESSAGE, params)

    def get_messages(
        self, conversation_id: str, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get conversation message list (ordered by time ASC)"""
        return self.execute_query(queries.SELECT_MESSAGES_BY_CONVERSATION, (conversation_id, limit, offset))

    def get_message_by_id(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Get message by ID"""
        results = self.execute_query(queries.SELECT_MESSAGE_BY_ID, (message_id,))
        return results[0] if results else None

    def delete_message(self, message_id: str) -> int:
        """Delete message"""
        return self.execute_delete(queries.DELETE_MESSAGE, (message_id,))

    def get_message_count(self, conversation_id: str) -> int:
        """Get message count for conversation"""
        results = self.execute_query(queries.SELECT_MESSAGE_COUNT, (conversation_id,))
        return results[0]["count"] if results else 0

    # LLM model management related methods
    def get_active_llm_model(self) -> Optional[Dict[str, Any]]:
        """Get currently active LLM model configuration"""
        results = self.execute_query(queries.SELECT_ACTIVE_LLM_MODEL)
        return results[0] if results else None

    def get_llm_model_by_id(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Get model configuration by ID (includes API key and test status)"""
        results = self.execute_query(queries.SELECT_LLM_MODEL_BY_ID, (model_id,))
        return results[0] if results else None

    def update_model_test_result(
        self, model_id: str, success: bool, error: Optional[str] = None
    ) -> None:
        """Update model test result"""
        now = datetime.now().isoformat()
        self.execute_update(queries.UPDATE_MODEL_TEST_RESULT, (1 if success else 0, now, error, now, model_id))


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
