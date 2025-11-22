"""
Conversations and Messages Repository - Handles chat conversations and messages
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.logger import get_logger

from .base import BaseRepository

logger = get_logger(__name__)


class ConversationsRepository(BaseRepository):
    """Repository for managing chat conversations"""

    def __init__(self, db_path: Path):
        super().__init__(db_path)

    def insert(
        self,
        conversation_id: str,
        title: str,
        related_activity_ids: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        model_id: Optional[str] = None,
    ) -> int:
        """Insert a new conversation"""
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO conversations (id, title, related_activity_ids, metadata, model_id)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        conversation_id,
                        title,
                        json.dumps(related_activity_ids or []),
                        json.dumps(metadata or {}),
                        model_id,
                    ),
                )
                conn.commit()
                logger.debug(f"Inserted conversation: {conversation_id}")
                return cursor.lastrowid or 0
        except Exception as e:
            logger.error(f"Failed to insert conversation {conversation_id}: {e}", exc_info=True)
            raise

    def get_all(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get conversation list ordered by update time DESC"""
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    SELECT id, title, related_activity_ids, metadata, created_at, updated_at, model_id
                    FROM conversations
                    ORDER BY updated_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    (limit, offset),
                )
                rows = cursor.fetchall()

            return [
                {
                    "id": row["id"],
                    "title": row["title"],
                    "related_activity_ids": json.loads(row["related_activity_ids"])
                    if row["related_activity_ids"]
                    else [],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "model_id": row["model_id"],
                }
                for row in rows
            ]

        except Exception as e:
            logger.error(f"Failed to get conversations: {e}", exc_info=True)
            return []

    def get_by_id(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation by ID"""
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    SELECT id, title, related_activity_ids, metadata, created_at, updated_at, model_id
                    FROM conversations
                    WHERE id = ?
                    """,
                    (conversation_id,),
                )
                row = cursor.fetchone()

            if row:
                return {
                    "id": row["id"],
                    "title": row["title"],
                    "related_activity_ids": json.loads(row["related_activity_ids"])
                    if row["related_activity_ids"]
                    else [],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "model_id": row["model_id"],
                }
            return None

        except Exception as e:
            logger.error(f"Failed to get conversation {conversation_id}: {e}", exc_info=True)
            return None

    def update(
        self,
        conversation_id: str,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Update conversation"""
        try:
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

            with self._get_conn() as conn:
                cursor = conn.execute(query, tuple(params))
                conn.commit()
                logger.debug(f"Updated conversation: {conversation_id}")
                return cursor.rowcount

        except Exception as e:
            logger.error(f"Failed to update conversation {conversation_id}: {e}", exc_info=True)
            raise

    def delete(self, conversation_id: str) -> int:
        """Delete conversation (cascades to delete messages)"""
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    "DELETE FROM conversations WHERE id = ?",
                    (conversation_id,),
                )
                conn.commit()
                logger.debug(f"Deleted conversation: {conversation_id}")
                return cursor.rowcount
        except Exception as e:
            logger.error(f"Failed to delete conversation {conversation_id}: {e}", exc_info=True)
            raise


class MessagesRepository(BaseRepository):
    """Repository for managing chat messages"""

    def __init__(self, db_path: Path):
        super().__init__(db_path)

    def insert(
        self,
        message_id: str,
        conversation_id: str,
        role: str,
        content: str,
        timestamp: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        images: Optional[List[str]] = None,
    ) -> int:
        """Insert a new message"""
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO messages (id, conversation_id, role, content, timestamp, metadata, images)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        message_id,
                        conversation_id,
                        role,
                        content,
                        timestamp or datetime.now().isoformat(),
                        json.dumps(metadata or {}),
                        json.dumps(images or []),
                    ),
                )
                conn.commit()
                logger.debug(f"Inserted message: {message_id}")
                return cursor.lastrowid or 0
        except Exception as e:
            logger.error(f"Failed to insert message {message_id}: {e}", exc_info=True)
            raise

    def get_by_conversation(
        self, conversation_id: str, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get messages for a conversation ordered by time ASC"""
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    SELECT id, conversation_id, role, content, timestamp, metadata, images
                    FROM messages
                    WHERE conversation_id = ?
                    ORDER BY timestamp ASC
                    LIMIT ? OFFSET ?
                    """,
                    (conversation_id, limit, offset),
                )
                rows = cursor.fetchall()

            return [
                {
                    "id": row["id"],
                    "conversation_id": row["conversation_id"],
                    "role": row["role"],
                    "content": row["content"],
                    "timestamp": row["timestamp"],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                    "images": json.loads(row["images"]) if row["images"] else [],
                }
                for row in rows
            ]

        except Exception as e:
            logger.error(
                f"Failed to get messages for conversation {conversation_id}: {e}",
                exc_info=True,
            )
            return []

    def get_by_id(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Get message by ID"""
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    SELECT id, conversation_id, role, content, timestamp, metadata, images
                    FROM messages
                    WHERE id = ?
                    """,
                    (message_id,),
                )
                row = cursor.fetchone()

            if row:
                return {
                    "id": row["id"],
                    "conversation_id": row["conversation_id"],
                    "role": row["role"],
                    "content": row["content"],
                    "timestamp": row["timestamp"],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                    "images": json.loads(row["images"]) if row["images"] else [],
                }
            return None

        except Exception as e:
            logger.error(f"Failed to get message {message_id}: {e}", exc_info=True)
            return None

    def delete(self, message_id: str) -> int:
        """Delete a message"""
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    "DELETE FROM messages WHERE id = ?",
                    (message_id,),
                )
                conn.commit()
                logger.debug(f"Deleted message: {message_id}")
                return cursor.rowcount
        except Exception as e:
            logger.error(f"Failed to delete message {message_id}: {e}", exc_info=True)
            raise

    def get_count(self, conversation_id: str) -> int:
        """Get message count for a conversation"""
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    "SELECT COUNT(*) as count FROM messages WHERE conversation_id = ?",
                    (conversation_id,),
                )
                row = cursor.fetchone()
                return row["count"] if row else 0
        except Exception as e:
            logger.error(
                f"Failed to get message count for conversation {conversation_id}: {e}",
                exc_info=True,
            )
            return 0
