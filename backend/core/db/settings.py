"""
Settings Repository - Handles all settings-related database operations
"""

from pathlib import Path
from typing import Any, Dict, Optional

from core.logger import get_logger

from .base import BaseRepository

logger = get_logger(__name__)


class SettingsRepository(BaseRepository):
    """Repository for managing application settings in the database"""

    def __init__(self, db_path: Path):
        super().__init__(db_path)

    def set(
        self,
        key: str,
        value: str,
        setting_type: str = "string",
        description: Optional[str] = None,
    ) -> int:
        """
        Set a configuration item
        
        Args:
            key: Setting key
            value: Setting value (stored as string)
            setting_type: Type of the setting (string, bool, int, etc.)
            description: Optional description
            
        Returns:
            Last row ID
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    INSERT OR REPLACE INTO settings (key, value, type, description)
                    VALUES (?, ?, ?, ?)
                    """,
                    (key, value, setting_type, description),
                )
                conn.commit()
                logger.debug(f"Set setting: {key} = {value}")
                return cursor.lastrowid or 0
        except Exception as e:
            logger.error(f"Failed to set setting {key}: {e}", exc_info=True)
            raise

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get a configuration item
        
        Args:
            key: Setting key
            default: Default value if key not found
            
        Returns:
            Setting value or default
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    "SELECT value FROM settings WHERE key = ?",
                    (key,),
                )
                row = cursor.fetchone()
                if row:
                    return row["value"]
                return default
        except Exception as e:
            logger.error(f"Failed to get setting {key}: {e}", exc_info=True)
            return default

    def get_all(self) -> Dict[str, Any]:
        """
        Get all configuration items with type conversion
        
        Returns:
            Dictionary of all settings with proper type conversion
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    "SELECT key, value, type FROM settings"
                )
                rows = cursor.fetchall()

            settings = {}
            for row in rows:
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

        except Exception as e:
            logger.error(f"Failed to get all settings: {e}", exc_info=True)
            return {}

    def delete(self, key: str) -> int:
        """
        Delete a configuration item
        
        Args:
            key: Setting key to delete
            
        Returns:
            Number of rows affected
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    "DELETE FROM settings WHERE key = ?",
                    (key,),
                )
                conn.commit()
                logger.debug(f"Deleted setting: {key}")
                return cursor.rowcount
        except Exception as e:
            logger.error(f"Failed to delete setting {key}: {e}", exc_info=True)
            raise
