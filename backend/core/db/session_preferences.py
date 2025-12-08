"""
SessionPreferences Repository - Handles user preference learning for session aggregation
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from core.logger import get_logger

from .base import BaseRepository

logger = get_logger(__name__)


class SessionPreferencesRepository(BaseRepository):
    """Repository for managing session preferences in the database"""

    def __init__(self, db_path: Path):
        super().__init__(db_path)

    async def save_pattern(
        self,
        pattern_id: str,
        preference_type: str,
        pattern_description: str,
        confidence_score: float = 0.5,
        times_observed: int = 1,
        last_observed: Optional[str] = None,
    ) -> None:
        """
        Save or update a learned pattern

        Args:
            pattern_id: Unique pattern identifier
            preference_type: Type of preference ('merge_pattern' | 'split_pattern' | 'time_threshold')
            pattern_description: Human-readable description of the pattern
            confidence_score: Confidence score (0.0 to 1.0)
            times_observed: Number of times this pattern was observed
            last_observed: ISO timestamp of last observation
        """
        try:
            with self._get_conn() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO session_preferences (
                        id, preference_type, pattern_description, confidence_score,
                        times_observed, last_observed, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    (
                        pattern_id,
                        preference_type,
                        pattern_description,
                        confidence_score,
                        times_observed,
                        last_observed or "CURRENT_TIMESTAMP",
                    ),
                )
                conn.commit()
                logger.debug(
                    f"Saved session preference: {pattern_id} (type: {preference_type})"
                )

        except Exception as e:
            logger.error(
                f"Failed to save session preference {pattern_id}: {e}", exc_info=True
            )
            raise

    async def increment_observation(
        self, pattern_id: str, last_observed: str
    ) -> None:
        """
        Increment observation count for a pattern

        Args:
            pattern_id: Pattern identifier
            last_observed: ISO timestamp of this observation
        """
        try:
            with self._get_conn() as conn:
                conn.execute(
                    """
                    UPDATE session_preferences
                    SET times_observed = times_observed + 1,
                        last_observed = ?
                    WHERE id = ?
                    """,
                    (last_observed, pattern_id),
                )
                conn.commit()
                logger.debug(f"Incremented observation for pattern: {pattern_id}")

        except Exception as e:
            logger.error(
                f"Failed to increment observation for pattern {pattern_id}: {e}",
                exc_info=True,
            )
            raise

    async def update_confidence(self, pattern_id: str, confidence_score: float) -> None:
        """
        Update confidence score for a pattern

        Args:
            pattern_id: Pattern identifier
            confidence_score: New confidence score (0.0 to 1.0)
        """
        try:
            with self._get_conn() as conn:
                conn.execute(
                    """
                    UPDATE session_preferences
                    SET confidence_score = ?
                    WHERE id = ?
                    """,
                    (confidence_score, pattern_id),
                )
                conn.commit()
                logger.debug(
                    f"Updated confidence for pattern {pattern_id}: {confidence_score}"
                )

        except Exception as e:
            logger.error(
                f"Failed to update confidence for pattern {pattern_id}: {e}",
                exc_info=True,
            )
            raise

    async def get_by_type(self, preference_type: str) -> List[Dict[str, Any]]:
        """
        Get all patterns of a specific type

        Args:
            preference_type: Type to filter by

        Returns:
            List of pattern dictionaries
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    SELECT id, preference_type, pattern_description, confidence_score,
                           times_observed, last_observed, created_at
                    FROM session_preferences
                    WHERE preference_type = ?
                    ORDER BY confidence_score DESC, times_observed DESC
                    """,
                    (preference_type,),
                )
                rows = cursor.fetchall()

            return [
                {
                    "id": row["id"],
                    "preference_type": row["preference_type"],
                    "pattern_description": row["pattern_description"],
                    "confidence_score": row["confidence_score"],
                    "times_observed": row["times_observed"],
                    "last_observed": row["last_observed"],
                    "created_at": row["created_at"],
                }
                for row in rows
            ]

        except Exception as e:
            logger.error(
                f"Failed to get preferences by type {preference_type}: {e}",
                exc_info=True,
            )
            return []

    async def get_all(
        self, min_confidence: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Get all patterns with minimum confidence threshold

        Args:
            min_confidence: Minimum confidence score to include

        Returns:
            List of pattern dictionaries
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    SELECT id, preference_type, pattern_description, confidence_score,
                           times_observed, last_observed, created_at
                    FROM session_preferences
                    WHERE confidence_score >= ?
                    ORDER BY preference_type, confidence_score DESC
                    """,
                    (min_confidence,),
                )
                rows = cursor.fetchall()

            return [
                {
                    "id": row["id"],
                    "preference_type": row["preference_type"],
                    "pattern_description": row["pattern_description"],
                    "confidence_score": row["confidence_score"],
                    "times_observed": row["times_observed"],
                    "last_observed": row["last_observed"],
                    "created_at": row["created_at"],
                }
                for row in rows
            ]

        except Exception as e:
            logger.error(f"Failed to get all preferences: {e}", exc_info=True)
            return []

    async def get_by_id(self, pattern_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific pattern by ID

        Args:
            pattern_id: Pattern identifier

        Returns:
            Pattern dictionary or None
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    SELECT id, preference_type, pattern_description, confidence_score,
                           times_observed, last_observed, created_at
                    FROM session_preferences
                    WHERE id = ?
                    """,
                    (pattern_id,),
                )
                row = cursor.fetchone()

            if not row:
                return None

            return {
                "id": row["id"],
                "preference_type": row["preference_type"],
                "pattern_description": row["pattern_description"],
                "confidence_score": row["confidence_score"],
                "times_observed": row["times_observed"],
                "last_observed": row["last_observed"],
                "created_at": row["created_at"],
            }

        except Exception as e:
            logger.error(f"Failed to get preference {pattern_id}: {e}", exc_info=True)
            return None

    async def delete(self, pattern_id: str) -> None:
        """
        Delete a pattern

        Args:
            pattern_id: Pattern identifier
        """
        try:
            with self._get_conn() as conn:
                conn.execute(
                    "DELETE FROM session_preferences WHERE id = ?", (pattern_id,)
                )
                conn.commit()
                logger.debug(f"Deleted session preference: {pattern_id}")

        except Exception as e:
            logger.error(
                f"Failed to delete session preference {pattern_id}: {e}", exc_info=True
            )
            raise

    async def delete_by_type(self, preference_type: str) -> int:
        """
        Delete all patterns of a specific type

        Args:
            preference_type: Type to delete

        Returns:
            Number of patterns deleted
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    "DELETE FROM session_preferences WHERE preference_type = ?",
                    (preference_type,),
                )
                conn.commit()
                deleted_count = cursor.rowcount
                logger.debug(
                    f"Deleted {deleted_count} session preferences of type {preference_type}"
                )
                return deleted_count

        except Exception as e:
            logger.error(
                f"Failed to delete preferences by type {preference_type}: {e}",
                exc_info=True,
            )
            return 0
