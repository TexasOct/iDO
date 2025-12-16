"""
Database module - Repository pattern implementation

This module provides:
1. Individual Repository classes for each domain (Activities, Events, etc.)
2. Unified DatabaseManager that aggregates all repositories
3. Global get_db() and switch_database() functions for easy access
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.logger import get_logger
from core.sqls import queries

# Three-layer architecture repositories
from .actions import ActionsRepository
from .activities import ActivitiesRepository
from .base import BaseRepository
from .conversations import ConversationsRepository, MessagesRepository
from .diaries import DiariesRepository
from .events import EventsRepository
from .knowledge import KnowledgeRepository
from .models import LLMModelsRepository
from .session_preferences import SessionPreferencesRepository
from .settings import SettingsRepository
from .todos import TodosRepository

logger = get_logger(__name__)


class DatabaseManager:
    """
    Unified database manager that provides access to all repositories

    This class aggregates all domain-specific repositories and provides
    a single entry point for database operations.

    Example:
        db = get_db()
        activities = db.activities.get_recent(limit=10)
        settings = db.settings.get_all()
    """

    def __init__(self, db_path: Path):
        """
        Initialize DatabaseManager with all repositories

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path

        # Ensure database tables exist
        self._initialize_database()

        # Initialize all repositories
        # Canonical repositories
        self.activities = ActivitiesRepository(db_path)
        self.events = EventsRepository(db_path)
        self.knowledge = KnowledgeRepository(db_path)
        self.todos = TodosRepository(db_path)
        self.diaries = DiariesRepository(db_path)
        self.settings = SettingsRepository(db_path)
        self.conversations = ConversationsRepository(db_path)
        self.messages = MessagesRepository(db_path)
        self.models = LLMModelsRepository(db_path)

        self.actions = ActionsRepository(db_path)
        self.session_preferences = SessionPreferencesRepository(db_path)

        logger.debug(f"✓ DatabaseManager initialized with path: {db_path}")

    def _initialize_database(self):
        """
        Initialize database schema - create all tables and indexes

        This is called automatically when DatabaseManager is instantiated.
        It ensures all required tables and indexes exist.
        """
        import sqlite3

        from core.sqls import migrations, schema

        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            # Create all tables
            for table_sql in schema.ALL_TABLES:
                cursor.execute(table_sql)

            # Create all indexes
            for index_sql in schema.ALL_INDEXES:
                cursor.execute(index_sql)

            # Run migrations for new columns
            self._run_migrations(cursor)

            conn.commit()
            conn.close()

            logger.debug(f"✓ Database schema initialized: {len(schema.ALL_TABLES)} tables, {len(schema.ALL_INDEXES)} indexes")

        except Exception as e:
            logger.error(f"Failed to initialize database schema: {e}", exc_info=True)
            raise

    def _run_migrations(self, cursor):
        """
        Run database migrations to add new columns to existing tables

        Args:
            cursor: Database cursor
        """
        import sqlite3

        from core.sqls import migrations

        # List of migrations to run (column name, migration SQL)
        migration_list = [
            ("actions.extract_knowledge", migrations.ADD_ACTIONS_EXTRACT_KNOWLEDGE_COLUMN),
            ("actions.knowledge_extracted", migrations.ADD_ACTIONS_KNOWLEDGE_EXTRACTED_COLUMN),
            ("knowledge.source_action_id", migrations.ADD_KNOWLEDGE_SOURCE_ACTION_ID_COLUMN),
        ]

        for column_desc, migration_sql in migration_list:
            try:
                cursor.execute(migration_sql)
                logger.info(f"✓ Migration applied: {column_desc}")
            except sqlite3.OperationalError as e:
                error_msg = str(e).lower()
                # Column might already exist, which is fine
                if "duplicate column" in error_msg or "already exists" in error_msg:
                    logger.debug(f"Column {column_desc} already exists, skipping")
                else:
                    # Real error, log as warning but continue
                    logger.warning(f"Migration failed for {column_desc}: {e}")
            except Exception as e:
                # Unexpected error
                logger.error(f"Unexpected error in migration for {column_desc}: {e}", exc_info=True)

    def get_connection(self):
        """
        Get database connection (legacy compatibility)

        For new code, use repository methods instead of direct SQL.
        This method exists for backward compatibility with old code.

        Returns:
            Context manager yielding SQLite connection
        """
        import sqlite3
        from contextlib import contextmanager

        @contextmanager
        def _connection():
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            try:
                yield conn
            finally:
                conn.close()

        return _connection()

    def execute_query(
        self, query: str, params: Optional[Tuple[Any, ...]] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute a raw SQL query and return results as list of dicts (legacy compatibility)

        For new code, use repository methods instead of direct SQL.
        This method exists for backward compatibility with old code.

        Args:
            query: SQL query string
            params: Optional query parameters

        Returns:
            List of dictionaries representing query results
        """
        import sqlite3

        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params or ())
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except sqlite3.Error as e:
            logger.error(f"Database query error: {e}", exc_info=True)
            logger.error(f"Query: {query}")
            logger.error(f"Params: {params}")
            raise

    def get_table_counts(self) -> Dict[str, int]:
        """
        Return row counts for key tables using predefined queries.

        Returns:
            Dict keyed by table name containing count values.
        """
        counts: Dict[str, int] = {}
        try:
            with self.get_connection() as conn:
                for table, query in queries.TABLE_COUNT_QUERIES.items():
                    cursor = conn.execute(query)
                    row = cursor.fetchone()
                    counts[table] = row["count"] if row else 0
            return counts
        except Exception as exc:
            logger.error(f"Failed to compute table counts: {exc}", exc_info=True)
            return counts

    async def delete_old_data(
        self, cutoff_iso: str, cutoff_date_str: str
    ) -> Dict[str, int]:
        """
        Delete or soft-delete data older than the provided cutoffs.

        Args:
            cutoff_iso: ISO timestamp boundary for timestamp-based fields
            cutoff_date_str: Date boundary (YYYY-MM-DD) for date-based fields

        Returns:
            Dict of deleted/updated row counts keyed by table grouping
        """
        deleted_counts = {
            "events": 0,
            "activities": 0,
            "knowledge": 0,
            "todos": 0,
            "combinedKnowledge": 0,
            "combinedTodos": 0,
            "diaries": 0,
        }

        try:
            with self.get_connection() as conn:
                conn.execute(
                    queries.DELETE_EVENT_IMAGES_BEFORE_TIMESTAMP, (cutoff_iso,)
                )
                cursor = conn.execute(
                    queries.DELETE_EVENTS_BEFORE_TIMESTAMP, (cutoff_iso,)
                )
                deleted_counts["events"] = cursor.rowcount

                cursor = conn.execute(
                    queries.SOFT_DELETE_ACTIVITIES_BEFORE_START_TIME, (cutoff_iso,)
                )
                deleted_counts["activities"] = cursor.rowcount

                cursor = conn.execute(
                    queries.SOFT_DELETE_KNOWLEDGE_BEFORE_CREATED_AT, (cutoff_iso,)
                )
                deleted_counts["knowledge"] = cursor.rowcount

                cursor = conn.execute(
                    queries.SOFT_DELETE_TODOS_BEFORE_CREATED_AT, (cutoff_iso,)
                )
                deleted_counts["todos"] = cursor.rowcount

                cursor = conn.execute(
                    queries.SOFT_DELETE_DIARIES_BEFORE_DATE, (cutoff_date_str,)
                )
                deleted_counts["diaries"] = cursor.rowcount

                conn.commit()

            return deleted_counts
        except Exception as exc:
            logger.error(f"Failed to delete old data: {exc}", exc_info=True)
            raise


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_db() -> DatabaseManager:
    """
    Get global DatabaseManager instance

    This function provides a singleton DatabaseManager instance.
    The database path is read from config.toml (database.path),
    or defaults to ~/.config/ido/ido.db

    Returns:
        DatabaseManager instance with all repositories

    Example:
        from core.db import get_db

        db = get_db()
        activities = db.activities.get_recent(limit=10)
        db.settings.set("key", "value")
    """
    global _db_manager

    if _db_manager is None:
        from config.loader import get_config
        from core.paths import get_db_path

        config = get_config()

        # Read database path from config.toml
        configured_path = config.get("database.path", "")

        # If path is configured and not empty, use it; otherwise use default
        if configured_path and configured_path.strip():
            db_path = Path(configured_path)
        else:
            db_path = get_db_path()

        _db_manager = DatabaseManager(db_path)
        logger.debug(f"✓ Global DatabaseManager initialized: {db_path}")

    return _db_manager


def switch_database(new_db_path: str) -> bool:
    """
    Switch database to a new path at runtime

    This creates a new DatabaseManager instance with all repositories
    pointing to the new database path.

    Args:
        new_db_path: New database path (string or Path)

    Returns:
        True if switch successful, False otherwise

    Example:
        from core.db import switch_database

        if switch_database("/path/to/new/db.db"):
            print("Database switched successfully")
    """
    global _db_manager

    if _db_manager is None:
        logger.error("DatabaseManager not initialized, cannot switch")
        return False

    try:
        new_path = Path(new_db_path)

        # Check if new path is the same as current
        if _db_manager.db_path.resolve() == new_path.resolve():
            logger.debug(f"New path is same as current, no switch needed: {new_db_path}")
            return True

        # Create directory for new path if it doesn't exist
        new_path.parent.mkdir(parents=True, exist_ok=True)

        # Create new DatabaseManager with new path
        _db_manager = DatabaseManager(new_path)
        logger.debug(f"✓ Database switched to: {new_db_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to switch database: {e}", exc_info=True)
        return False


__all__ = [
    # Repository classes (for direct instantiation if needed)
    "BaseRepository",
    "ActivitiesRepository",
    "EventsRepository",
    "KnowledgeRepository",
    "TodosRepository",
    "DiariesRepository",
    "SettingsRepository",
    "ConversationsRepository",
    "MessagesRepository",
    "LLMModelsRepository",
    "ActionsRepository",
    "SessionPreferencesRepository",
    # Unified manager
    "DatabaseManager",
    # Global access functions
    "get_db",
    "switch_database",
]
