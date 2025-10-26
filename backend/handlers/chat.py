"""
Chat API handlers
处理聊天相关的 API 请求
"""

from typing import List, Optional, Dict, Any
from models.base import BaseModel
from . import api_handler
from services.chat_service import get_chat_service
from core.logger import get_logger

logger = get_logger(__name__)


# ============ Request Models ============

class CreateConversationRequest(BaseModel):
    """创建对话请求"""
    title: str
    related_activity_ids: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class CreateConversationFromActivitiesRequest(BaseModel):
    """从活动创建对话请求"""
    activity_ids: List[str]


class SendMessageRequest(BaseModel):
    """发送消息请求"""
    conversation_id: str
    content: str


class GetMessagesRequest(BaseModel):
    """获取消息列表请求"""
    conversation_id: str
    limit: Optional[int] = 100
    offset: Optional[int] = 0


class GetConversationsRequest(BaseModel):
    """获取对话列表请求"""
    limit: Optional[int] = 50
    offset: Optional[int] = 0


class DeleteConversationRequest(BaseModel):
    """删除对话请求"""
    conversation_id: str


# ============ API Handlers ============

@api_handler(
    body=CreateConversationRequest,
    method="POST",
    path="/chat/create-conversation",
    tags=["chat"]
)
async def create_conversation(body: CreateConversationRequest) -> Dict[str, Any]:
    """
    创建新对话

    Args:
        body: 包含标题、关联活动等信息

    Returns:
        创建的对话信息
    """
    try:
        chat_service = get_chat_service()
        conversation = await chat_service.create_conversation(
            title=body.title,
            related_activity_ids=body.related_activity_ids,
            metadata=body.metadata
        )

        return {
            "success": True,
            "data": conversation.to_dict(),
            "message": "对话创建成功"
        }
    except Exception as e:
        logger.error(f"创建对话失败: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"创建对话失败: {str(e)}"
        }


@api_handler(
    body=CreateConversationFromActivitiesRequest,
    method="POST",
    path="/chat/create-from-activities",
    tags=["chat"]
)
async def create_conversation_from_activities(
    body: CreateConversationFromActivitiesRequest
) -> Dict[str, Any]:
    """
    从活动创建对话，自动生成上下文

    Args:
        body: 包含活动 ID 列表

    Returns:
        创建的对话信息和上下文
    """
    try:
        chat_service = get_chat_service()
        result = await chat_service.create_conversation_from_activities(
            activity_ids=body.activity_ids
        )

        return {
            "success": True,
            "data": result,
            "message": "从活动创建对话成功"
        }
    except Exception as e:
        logger.error(f"从活动创建对话失败: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"从活动创建对话失败: {str(e)}"
        }


@api_handler(
    body=SendMessageRequest,
    method="POST",
    path="/chat/send-message",
    tags=["chat"]
)
async def send_message(body: SendMessageRequest) -> Dict[str, Any]:
    """
    发送消息（流式输出）

    此接口会启动流式输出，通过 Tauri Events 实时发送消息块。
    前端应监听 'chat-message-chunk' 事件来接收流式内容。

    Args:
        body: 包含对话 ID 和消息内容

    Returns:
        操作状态
    """
    try:
        chat_service = get_chat_service()

        # 启动流式输出（在后台异步执行）
        # 这里使用 await 是为了确保流式输出开始执行
        await chat_service.send_message_stream(
            conversation_id=body.conversation_id,
            user_message=body.content
        )

        return {
            "success": True,
            "message": "消息发送成功"
        }
    except Exception as e:
        logger.error(f"发送消息失败: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"发送消息失败: {str(e)}"
        }


@api_handler(
    body=GetConversationsRequest,
    method="POST",
    path="/chat/get-conversations",
    tags=["chat"]
)
async def get_conversations(body: GetConversationsRequest) -> Dict[str, Any]:
    """
    获取对话列表

    Args:
        body: 包含分页参数

    Returns:
        对话列表
    """
    try:
        chat_service = get_chat_service()
        conversations = await chat_service.get_conversations(
            limit=body.limit or 50,
            offset=body.offset or 0
        )

        return {
            "success": True,
            "data": [conv.to_dict() for conv in conversations],
            "message": "获取对话列表成功"
        }
    except Exception as e:
        logger.error(f"获取对话列表失败: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"获取对话列表失败: {str(e)}"
        }


@api_handler(
    body=GetMessagesRequest,
    method="POST",
    path="/chat/get-messages",
    tags=["chat"]
)
async def get_messages(body: GetMessagesRequest) -> Dict[str, Any]:
    """
    获取对话的消息列表

    Args:
        body: 包含对话 ID 和分页参数

    Returns:
        消息列表
    """
    try:
        chat_service = get_chat_service()
        messages = await chat_service.get_messages(
            conversation_id=body.conversation_id,
            limit=body.limit or 100,
            offset=body.offset or 0
        )

        return {
            "success": True,
            "data": [msg.to_dict() for msg in messages],
            "message": "获取消息列表成功"
        }
    except Exception as e:
        logger.error(f"获取消息列表失败: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"获取消息列表失败: {str(e)}"
        }


@api_handler(
    body=DeleteConversationRequest,
    method="POST",
    path="/chat/delete-conversation",
    tags=["chat"]
)
async def delete_conversation(body: DeleteConversationRequest) -> Dict[str, Any]:
    """
    删除对话（级联删除所有消息）

    Args:
        body: 包含对话 ID

    Returns:
        操作状态
    """
    try:
        chat_service = get_chat_service()
        success = await chat_service.delete_conversation(body.conversation_id)

        return {
            "success": success,
            "message": "删除对话成功" if success else "对话不存在"
        }
    except Exception as e:
        logger.error(f"删除对话失败: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"删除对话失败: {str(e)}"
        }
