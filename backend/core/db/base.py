"""
Base repository class for database operations
Provides common database connection and utility methods
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

from core.logger import get_logger

logger = get_logger(__name__)


class BaseRepository:
    """
    Base repository class providing common database operations

    All repository classes should inherit from this base class
    to ensure consistent database connection handling and error management.
    """

    def __init__(self, db_path: Path):
        """
        Initialize repository with database path

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        logger.debug(f"Initialized {self.__class__.__name__} with db_path: {db_path}")

    @contextmanager
    def _get_conn(self) -> Generator[sqlite3.Connection, None, None]:
        """
        Get database connection with Row factory for dict-like access

        Yields:
            SQLite connection with row factory configured

        Example:
            with self._get_conn() as conn:
                cursor = conn.execute("SELECT * FROM table")
                rows = cursor.fetchall()
        """
        conn = sqlite3.connect(
            str(self.db_path),
            timeout=30.0,
            check_same_thread=False,
        )
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _execute_query(
        self,
        query: str,
        params: Optional[tuple] = None,
        fetch_one: bool = False,
        fetch_all: bool = False,
    ) -> Optional[Any]:
        """
        Execute a SQL query with error handling

        Args:
            query: SQL query string
            params: Query parameters (optional)
            fetch_one: Whether to fetch one result
            fetch_all: Whether to fetch all results

        Returns:
            Query results if fetch_one or fetch_all is True, otherwise None
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(query, params or ())

                if fetch_one:
                    return cursor.fetchone()
                elif fetch_all:
                    return cursor.fetchall()

                conn.commit()
                return None

        except sqlite3.Error as e:
            logger.error(f"Database error in {self.__class__.__name__}: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Params: {params}")
            raise

    def _row_to_dict(self, row: Optional[sqlite3.Row]) -> Optional[Dict[str, Any]]:
        """
        Convert SQLite Row to dictionary

        Args:
            row: SQLite Row object

        Returns:
            Dictionary representation of the row, or None if row is None
        """
        if row is None:
            return None
        return dict(row)

    def _rows_to_dicts(self, rows: List[sqlite3.Row]) -> List[Dict[str, Any]]:
        """
        Convert list of SQLite Rows to list of dictionaries

        Args:
            rows: List of SQLite Row objects

        Returns:
            List of dictionary representations
        """
        return [dict(row) for row in rows]
