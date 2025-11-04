"""
Chat API handlers
Handle chat-related API requests
"""

from typing import List, Optional, Dict, Any
from models.base import BaseModel
from . import api_handler
from services.chat_service import get_chat_service
from core.logger import get_logger

logger = get_logger(__name__)


# ============ Request Models ============


class CreateConversationRequest(BaseModel):
    """Create conversation request"""

    title: str
    related_activity_ids: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class CreateConversationFromActivitiesRequest(BaseModel):
    """Create conversation from activities request"""

    activity_ids: List[str]


class SendMessageRequest(BaseModel):
    """Send message request"""

    conversation_id: str
    content: str


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

    Args:
        body: Containing conversation ID and message content

    Returns:
        Operation status
    """
    try:
        chat_service = get_chat_service()

        # Start streaming output (executed asynchronously in background)
        # Use await here to ensure streaming output starts execution
        await chat_service.send_message_stream(
            conversation_id=body.conversation_id, user_message=body.content
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
