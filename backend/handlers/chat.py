"""
Chat API handlers
Handle chat-related API requests, friendly chat management, and Live2D configuration
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Dict, List

from core.logger import get_logger
from core.settings import get_settings
from models.base import OperationDataResponse
from models.requests import (
    CancelStreamRequest,
    CreateConversationFromActivitiesRequest,
    CreateConversationRequest,
    DeleteConversationRequest,
    GetConversationsRequest,
    GetFriendlyChatHistoryRequest,
    GetMessagesRequest,
    GetStreamingStatusRequest,
    SendMessageRequest,
    UpdateFriendlyChatSettingsRequest,
    UpdateLive2DSettingsRequest,
)
from services.chat_service import get_chat_service
from services.friendly_chat_service import get_friendly_chat_service

from . import api_handler

logger = get_logger(__name__)


class FriendlyChatResponse(OperationDataResponse):
    """Response model for friendly chat handlers."""

    data: Dict[str, Any] | None = None


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
            logger.info(f"✅ Streaming task cancelled for conversation {body.conversation_id}")
            return {
                "success": True,
                "message": "Streaming cancelled successfully",
            }
        else:
            logger.warning(f"⚠️ No active streaming task for conversation {body.conversation_id}")
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


# ============ Friendly Chat Management ============


@api_handler(method="GET")
async def get_friendly_chat_settings() -> FriendlyChatResponse:
    """Get friendly chat configuration.

    Returns the current settings for the friendly chat feature including
    interval, data window, and notification preferences.
    """
    settings = get_settings()
    chat_settings = settings.get_friendly_chat_settings()

    return FriendlyChatResponse(success=True, data=chat_settings)


@api_handler(body=UpdateFriendlyChatSettingsRequest)
async def update_friendly_chat_settings(
    body: UpdateFriendlyChatSettingsRequest,
) -> FriendlyChatResponse:
    """Update friendly chat configuration.

    Updates the friendly chat settings and restarts the service if needed.
    """
    settings = get_settings()
    chat_service = get_friendly_chat_service()

    # Update settings - use by_alias=False to get snake_case keys
    updates_dict = body.model_dump(exclude_none=True, by_alias=False)
    logger.debug(f"[FriendlyChat] Received updates: {updates_dict}")

    updated = settings.update_friendly_chat_settings(updates_dict)
    logger.debug(f"[FriendlyChat] Settings after update: {updated}")

    # Restart service based on enabled status
    if updated.get("enabled", False):
        await chat_service.stop()  # Stop if running
        await chat_service.start()  # Start with new settings
    else:
        await chat_service.stop()

    return FriendlyChatResponse(
        success=True, message="Friendly chat settings updated", data=updated
    )


@api_handler(body=GetFriendlyChatHistoryRequest)
async def get_friendly_chat_history(
    body: GetFriendlyChatHistoryRequest,
) -> FriendlyChatResponse:
    """Get friendly chat message history.

    Returns a paginated list of previously generated chat messages.
    """
    chat_service = get_friendly_chat_service()
    history = await chat_service.get_chat_history(
        limit=body.limit,
        offset=body.offset,
    )

    return FriendlyChatResponse(
        success=True,
        data={
            "messages": history,
            "count": len(history),
        },
    )


@api_handler(method="POST")
async def trigger_friendly_chat() -> FriendlyChatResponse:
    """Manually trigger a friendly chat message generation.

    Generates and sends a chat message immediately based on recent activities.
    """
    chat_service = get_friendly_chat_service()
    message = await chat_service.trigger_immediate_chat()

    if message:
        return FriendlyChatResponse(
            success=True,
            message="Chat message generated",
            data={"chat_message": message},
        )
    return FriendlyChatResponse(
        success=False,
        message="Failed to generate chat message (no recent activities or LLM error)",
    )


# ============ Live2D Management ============


def _scan_local_models(model_dir: str) -> List[Dict[str, str]]:
    """Scan local model directory for Live2D model definition files."""
    if not model_dir:
        return []

    path_obj = Path(model_dir).expanduser()
    if not path_obj.exists():
        return []

    patterns = ["**/*.model3.json", "**/*.model.json", "**/index.json"]
    results: List[Dict[str, str]] = []

    for pattern in patterns:
        for file_path in path_obj.glob(pattern):
            if not file_path.is_file():
                continue
            try:
                display_name = file_path.stem
                results.append(
                    {
                        "url": file_path.as_posix(),
                        "type": "local",
                        "name": display_name,
                    }
                )
            except Exception:
                continue

    # Remove duplicates by url while keeping order
    unique: Dict[str, Dict[str, str]] = {}
    for item in results:
        unique[item["url"]] = item
    return list(unique.values())


@api_handler(method="GET")
async def get_live2d_settings() -> Dict[str, Any]:
    """Get Live2D configuration."""
    settings = get_settings()
    live2d_settings = settings.get_live2d_settings()

    local_models = await asyncio.to_thread(
        _scan_local_models, live2d_settings.get("model_dir", "")
    )

    return {
        "success": True,
        "data": {
            "settings": live2d_settings,
            "models": {
                "local": local_models,
                "remote": [
                    {"url": url, "type": "remote", "name": url.split("/")[-1]}
                    for url in live2d_settings.get("remote_models", [])
                ],
            },
        },
    }


@api_handler(body=UpdateLive2DSettingsRequest)
async def update_live2d_settings(body: UpdateLive2DSettingsRequest) -> Dict[str, Any]:
    """Update Live2D configuration values."""
    settings = get_settings()
    # Persist settings using snake_case keys expected by SettingsManager
    payload = body.model_dump(exclude_none=True, by_alias=False)
    updated = settings.update_live2d_settings(payload)

    local_models = await asyncio.to_thread(
        _scan_local_models, updated.get("model_dir", "")
    )

    return {
        "success": True,
        "message": "Live2D settings updated",
        "data": {
            "settings": updated,
            "models": {
                "local": local_models,
                "remote": [
                    {"url": url, "type": "remote", "name": url.split("/")[-1]}
                    for url in updated.get("remote_models", [])
                ],
            },
        },
    }
