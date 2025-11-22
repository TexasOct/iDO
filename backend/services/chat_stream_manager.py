"""
Chat Stream Manager
Keeps streaming tasks isolated per conversation so they do not interfere.
"""

import asyncio
from typing import Dict, Optional

from core.logger import get_logger

logger = get_logger(__name__)


class ChatStreamManager:
    """
    Manage streaming tasks on a per-conversation basis.

    Guarantees:
    1. Each conversation runs its streaming request independently.
    2. Different conversations can stream concurrently.
    3. Switching conversations does not interrupt an in-progress stream.
    """

    def __init__(self):
        # conversation_id -> asyncio.Task
        self._active_streams: Dict[str, asyncio.Task] = {}

    def is_streaming(self, conversation_id: str) -> bool:
        """Return True when the conversation currently has an active stream."""
        task = self._active_streams.get(conversation_id)
        return task is not None and not task.done()

    def register_stream(self, conversation_id: str, task: asyncio.Task) -> None:
        """
        Register the streaming task for a conversation.

        Args:
            conversation_id: Conversation identifier.
            task: asyncio.Task performing the streaming work.
        """
        # Cancel any existing streaming task for this conversation
        if conversation_id in self._active_streams:
            old_task = self._active_streams[conversation_id]
            if not old_task.done():
                logger.warning(
                    f"Conversation {conversation_id} already has an active task. Canceling the old task."
                )
                old_task.cancel()

        self._active_streams[conversation_id] = task
        logger.debug(f"Registered streaming task for conversation {conversation_id}")

        # Clean up automatically when the task finishes
        task.add_done_callback(lambda t: self._cleanup_stream(conversation_id, t))

    def _cleanup_stream(self, conversation_id: str, task: asyncio.Task) -> None:
        """Remove a completed streaming task."""
        if self._active_streams.get(conversation_id) == task:
            del self._active_streams[conversation_id]
            logger.debug(f"Cleared streaming task for conversation {conversation_id}")

    def cancel_stream(self, conversation_id: str) -> bool:
        """
        Cancel the streaming task for a conversation.

        Args:
            conversation_id: Conversation identifier.

        Returns:
            True if a running task was canceled, False otherwise.
        """
        task = self._active_streams.get(conversation_id)
        if task and not task.done():
            task.cancel()
            logger.info(f"Canceled streaming task for conversation {conversation_id}")
            return True
        return False

    def get_active_streams_count(self) -> int:
        """Return the number of currently active streaming tasks."""
        return sum(1 for task in self._active_streams.values() if not task.done())

    def get_active_conversation_ids(self) -> list[str]:
        """Return a list of conversation IDs that are streaming."""
        return [
            conv_id
            for conv_id, task in self._active_streams.items()
            if not task.done()
        ]


# Global singleton
_stream_manager: Optional[ChatStreamManager] = None


def get_stream_manager() -> ChatStreamManager:
    """Get the global stream manager instance."""
    global _stream_manager
    if _stream_manager is None:
        _stream_manager = ChatStreamManager()
    return _stream_manager
