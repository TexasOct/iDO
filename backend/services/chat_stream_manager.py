"""
Chat Stream Manager
管理每个会话的流式任务，确保会话之间的流式处理互不干扰
"""

import asyncio
from typing import Dict, Optional

from core.logger import get_logger

logger = get_logger(__name__)


class ChatStreamManager:
    """
    管理每个会话的流式任务

    确保：
    1. 每个会话的流式请求独立运行
    2. 不同会话的流式请求可以并发
    3. 会话切换时不影响正在进行的流式输出
    """

    def __init__(self):
        # conversation_id -> asyncio.Task
        self._active_streams: Dict[str, asyncio.Task] = {}

    def is_streaming(self, conversation_id: str) -> bool:
        """检查会话是否正在流式输出"""
        task = self._active_streams.get(conversation_id)
        return task is not None and not task.done()

    def register_stream(self, conversation_id: str, task: asyncio.Task) -> None:
        """
        注册会话的流式任务

        Args:
            conversation_id: 会话 ID
            task: 流式处理的 asyncio.Task
        """
        # 如果该会话已有正在运行的流式任务，取消它
        if conversation_id in self._active_streams:
            old_task = self._active_streams[conversation_id]
            if not old_task.done():
                logger.warning(
                    f"会话 {conversation_id} 已有流式任务正在运行，取消旧任务"
                )
                old_task.cancel()

        self._active_streams[conversation_id] = task
        logger.debug(f"注册会话 {conversation_id} 的流式任务")

        # 任务完成后自动清理
        task.add_done_callback(lambda t: self._cleanup_stream(conversation_id, t))

    def _cleanup_stream(self, conversation_id: str, task: asyncio.Task) -> None:
        """清理已完成的流式任务"""
        if self._active_streams.get(conversation_id) == task:
            del self._active_streams[conversation_id]
            logger.debug(f"清理会话 {conversation_id} 的流式任务")

    def cancel_stream(self, conversation_id: str) -> bool:
        """
        取消会话的流式任务

        Args:
            conversation_id: 会话 ID

        Returns:
            True 如果成功取消，False 如果没有正在运行的任务
        """
        task = self._active_streams.get(conversation_id)
        if task and not task.done():
            task.cancel()
            logger.info(f"取消会话 {conversation_id} 的流式任务")
            return True
        return False

    def get_active_streams_count(self) -> int:
        """获取当前活跃的流式任务数量"""
        return sum(1 for task in self._active_streams.values() if not task.done())

    def get_active_conversation_ids(self) -> list[str]:
        """获取所有正在流式输出的会话 ID 列表"""
        return [
            conv_id
            for conv_id, task in self._active_streams.items()
            if not task.done()
        ]


# 全局单例
_stream_manager: Optional[ChatStreamManager] = None


def get_stream_manager() -> ChatStreamManager:
    """获取全局流管理器实例"""
    global _stream_manager
    if _stream_manager is None:
        _stream_manager = ChatStreamManager()
    return _stream_manager
