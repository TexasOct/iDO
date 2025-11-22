"""
Chat API handlers
Handle chat-related API requests
"""

from typing import Any, Dict, List, Optional

from core.logger import get_logger
from models.base import BaseModel
from services.chat_service import get_chat_service

from . import api_handler

logger = get_logger(__name__)


# ============ Request Models ============


class CreateConversationRequest(BaseModel):
    """Create conversation request"""

    title: str
    related_activity_ids: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    model_id: Optional[str] = None  # Model ID for this conversation


class CreateConversationFromActivitiesRequest(BaseModel):
    """Create conversation from activities request"""

    activity_ids: List[str]


class SendMessageRequest(BaseModel):
    """Send message request"""

    conversation_id: str
    content: str
    images: Optional[List[str]] = None  # Base64 encoded images or file paths
    model_id: Optional[str] = None  # LLM model ID to use for this message


class GetMessagesRequest(BaseModel):
    """Get message list request"""

    conversation_id: str
    limit: Optional[int] = 100
    offset: Optional[int] = 0


class GetConversationsRequest(BaseModel):
    """Get conversation list request"""

    limit: Optional[int] = 50
    offset: Optional[int] = 0


class DeleteConversationRequest(BaseModel):
    """Delete conversation request"""

    conversation_id: str


class GetStreamingStatusRequest(BaseModel):
    """Get streaming status request"""

    conversation_ids: Optional[List[str]] = None  # If None, get all active streams


class CancelStreamRequest(BaseModel):
    """Cancel streaming request"""

    conversation_id: str


# ============ API Handlers ============


@api_handler(
    body=CreateConversationRequest,
    method="POST",
    path="/chat/create-conversation",
    tags=["chat"],
)
async def create_conversation(body: CreateConversationRequest) -> Dict[str, Any]:
    """
    Create new conversation

    Args:
        body: Contains title, related activities and other information

    Returns:
        Created conversation information
    """
    try:
        chat_service = get_chat_service()
        conversation = await chat_service.create_conversation(
            title=body.title,
            related_activity_ids=body.related_activity_ids,
            metadata=body.metadata,
            model_id=body.model_id,
        )

        return {
            "success": True,
            "data": conversation.to_dict(),
            "message": "Conversation created successfully",
        }
    except Exception as e:
        logger.error(f"Failed to create conversation: {e}", exc_info=True)
        return {"success": False, "message": f"Failed to create conversation: {str(e)}"}


@api_handler(
    body=CreateConversationFromActivitiesRequest,
    method="POST",
    path="/chat/create-from-activities",
    tags=["chat"],
)
async def create_conversation_from_activities(
    body: CreateConversationFromActivitiesRequest,
) -> Dict[str, Any]:
    """
    Create conversation from activities, automatically generate context

    Args:
        body: Contains activity ID list

    Returns:
        Created conversation information and auto-generated context messages
    """
    try:
        chat_service = get_chat_service()
        result = await chat_service.create_conversation_from_activities(
            activity_ids=body.activity_ids
        )

        return {
            "success": True,
            "data": result,
            "message": "Conversation created from activities successfully",
        }
    except Exception as e:
        logger.error(
            f"Failed to create conversation from activities: {e}", exc_info=True
        )
        return {
            "success": False,
            "message": f"Failed to create conversation from activities: {str(e)}",
        }


@api_handler(
    body=SendMessageRequest, method="POST", path="/chat/send-message", tags=["chat"]
)
async def send_message(body: SendMessageRequest) -> Dict[str, Any]:
    """
    Send message (streaming output)

    This endpoint starts streaming output, sending message blocks in real-time through Tauri Events.
    The frontend should listen to 'chat-message-chunk' events to receive streaming content.
    Supports multimodal messages (text + images).

    Args:
        body: Containing conversation ID, message content, and optional images

    Returns:
        Operation status
    """
    try:
        chat_service = get_chat_service()

        # Start streaming output (executed asynchronously in background)
        # Use await here to ensure streaming output starts execution
        await chat_service.send_message_stream(
            conversation_id=body.conversation_id,
            user_message=body.content,
            images=body.images,
            model_id=body.model_id,
        )

        return {"success": True, "message": "Message sent successfully"}
    except Exception as e:
        logger.error(f"Failed to send message: {e}", exc_info=True)
        return {"success": False, "message": f"Failed to send message: {str(e)}"}


@api_handler(
    body=GetConversationsRequest,
    method="POST",
    path="/chat/get-conversations",
    tags=["chat"],
)
async def get_conversations(body: GetConversationsRequest) -> Dict[str, Any]:
    """
    Get conversation list

    Args:
        body: Contains pagination parameters

    Returns:
        Conversation list
    """
    try:
        chat_service = get_chat_service()
        conversations = await chat_service.get_conversations(
            limit=body.limit or 50, offset=body.offset or 0
        )

        return {
            "success": True,
            "data": [conv.to_dict() for conv in conversations],
            "message": "Conversation list retrieved successfully",
        }
    except Exception as e:
        logger.error(f"Failed to get conversation list: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Failed to get conversation list: {str(e)}",
        }


@api_handler(
    body=GetMessagesRequest, method="POST", path="/chat/get-messages", tags=["chat"]
)
async def get_messages(body: GetMessagesRequest) -> Dict[str, Any]:
    """
    Get message list

    Args:
        body: Contains conversation ID and pagination parameters

    Returns:
        Message list
    """
    try:
        chat_service = get_chat_service()
        messages = await chat_service.get_messages(
            conversation_id=body.conversation_id,
            limit=body.limit or 100,
            offset=body.offset or 0,
        )

        return {
            "success": True,
            "data": [msg.to_dict() for msg in messages],
            "message": "Message list retrieved successfully",
        }
    except Exception as e:
        logger.error(f"Failed to get message list: {e}", exc_info=True)
        return {"success": False, "message": f"Failed to get message list: {str(e)}"}


@api_handler(
    body=DeleteConversationRequest,
    method="POST",
    path="/chat/delete-conversation",
    tags=["chat"],
)
async def delete_conversation(body: DeleteConversationRequest) -> Dict[str, Any]:
    """
    Delete conversation (cascade delete all messages)

    Args:
        body: Containing conversation ID

    Returns:
        Operation status
    """
    try:
        chat_service = get_chat_service()
        success = await chat_service.delete_conversation(body.conversation_id)

        return {
            "success": success,
            "message": "Conversation deleted successfully"
            if success
            else "Conversation does not exist",
        }
    except Exception as e:
        logger.error(f"Failed to delete conversation: {e}", exc_info=True)
        return {"success": False, "message": f"Failed to delete conversation: {str(e)}"}


@api_handler(
    body=GetStreamingStatusRequest,
    method="POST",
    path="/chat/get-streaming-status",
    tags=["chat"],
)
async def get_streaming_status(body: GetStreamingStatusRequest) -> Dict[str, Any]:
    """
    Get streaming status for conversations

    Args:
        body: Optional list of conversation IDs to check. If None, returns all active streams.

    Returns:
        Dict containing:
        - activeStreams: List of conversation IDs that are currently streaming
        - streamingStatus: Dict mapping conversation_id -> boolean (whether it's streaming)
    """
    try:
        chat_service = get_chat_service()

        # Get all active streaming conversation IDs
        active_conversation_ids = chat_service.stream_manager.get_active_conversation_ids()

        # If specific conversation IDs requested, filter the status
        if body.conversation_ids:
            streaming_status = {
                conv_id: chat_service.stream_manager.is_streaming(conv_id)
                for conv_id in body.conversation_ids
            }
        else:
            # Return all active streams
            streaming_status = {
                conv_id: True for conv_id in active_conversation_ids
            }

        return {
            "success": True,
            "data": {
                "activeStreams": active_conversation_ids,
                "streamingStatus": streaming_status,
                "activeCount": len(active_conversation_ids),
            },
            "message": "Streaming status retrieved successfully",
        }
    except Exception as e:
        logger.error(f"Failed to get streaming status: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Failed to get streaming status: {str(e)}",
        }


@api_handler(
    body=CancelStreamRequest,
    method="POST",
    path="/chat/cancel-stream",
    tags=["chat"],
)
async def cancel_stream(body: CancelStreamRequest) -> Dict[str, Any]:
    """
    Cancel streaming output for a conversation

    Args:
        body: Containing conversation ID

    Returns:
        Operation status
    """
    try:
        chat_service = get_chat_service()

        # Cancel the streaming task
        cancelled = chat_service.stream_manager.cancel_stream(body.conversation_id)

        if cancelled:
            logger.info(f"✅ 取消会话 {body.conversation_id} 的流式任务")
            return {
                "success": True,
                "message": "Streaming cancelled successfully",
            }
        else:
            logger.warning(f"⚠️ 会话 {body.conversation_id} 没有正在运行的流式任务")
            return {
                "success": True,
                "message": "No active streaming task found",
            }
    except Exception as e:
        logger.error(f"Failed to cancel stream: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Failed to cancel stream: {str(e)}",
        }
