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

from .activities import ActivitiesRepository
from .base import BaseRepository
from .conversations import ConversationsRepository, MessagesRepository
from .diaries import DiariesRepository
from .events import EventsRepository
from .knowledge import KnowledgeRepository
from .models import LLMModelsRepository
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

        # Initialize all repositories
        self.activities = ActivitiesRepository(db_path)
        self.events = EventsRepository(db_path)
        self.knowledge = KnowledgeRepository(db_path)
        self.todos = TodosRepository(db_path)
        self.diaries = DiariesRepository(db_path)
        self.settings = SettingsRepository(db_path)
        self.conversations = ConversationsRepository(db_path)
        self.messages = MessagesRepository(db_path)
        self.models = LLMModelsRepository(db_path)

        logger.info(f"✓ DatabaseManager initialized with path: {db_path}")

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
        logger.info(f"✓ Global DatabaseManager initialized: {db_path}")

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
            logger.info(f"New path is same as current, no switch needed: {new_db_path}")
            return True

        # Create directory for new path if it doesn't exist
        new_path.parent.mkdir(parents=True, exist_ok=True)

        # Create new DatabaseManager with new path
        _db_manager = DatabaseManager(new_path)
        logger.info(f"✓ Database switched to: {new_db_path}")
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
    # Unified manager
    "DatabaseManager",
    # Global access functions
    "get_db",
    "switch_database",
]
