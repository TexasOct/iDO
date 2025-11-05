"""Friendly Chat handlers."""

from __future__ import annotations

from typing import Dict, Any

from core.settings import get_settings
from services.friendly_chat_service import get_friendly_chat_service

from . import api_handler
from models.requests import (
    UpdateFriendlyChatSettingsRequest,
    GetFriendlyChatHistoryRequest,
)


@api_handler(method="GET")
async def get_friendly_chat_settings() -> Dict[str, Any]:
    """Get friendly chat configuration.

    Returns the current settings for the friendly chat feature including
    interval, data window, and notification preferences.
    """
    settings = get_settings()
    chat_settings = settings.get_friendly_chat_settings()

    return {
        "success": True,
        "data": chat_settings,
    }


@api_handler(body=UpdateFriendlyChatSettingsRequest)
async def update_friendly_chat_settings(
    body: UpdateFriendlyChatSettingsRequest,
) -> Dict[str, Any]:
    """Update friendly chat configuration.

    Updates the friendly chat settings and restarts the service if needed.
    """
    settings = get_settings()
    chat_service = get_friendly_chat_service()

    # Update settings
    updated = settings.update_friendly_chat_settings(body.model_dump(exclude_none=True))

    # Restart service based on enabled status
    if updated.get("enabled", False):
        await chat_service.stop()  # Stop if running
        await chat_service.start()  # Start with new settings
    else:
        await chat_service.stop()

    return {
        "success": True,
        "message": "Friendly chat settings updated",
        "data": updated,
    }


@api_handler(body=GetFriendlyChatHistoryRequest)
async def get_friendly_chat_history(
    body: GetFriendlyChatHistoryRequest,
) -> Dict[str, Any]:
    """Get friendly chat message history.

    Returns a paginated list of previously generated chat messages.
    """
    chat_service = get_friendly_chat_service()
    history = await chat_service.get_chat_history(
        limit=body.limit,
        offset=body.offset,
    )

    return {
        "success": True,
        "data": {
            "messages": history,
            "count": len(history),
        },
    }


@api_handler(method="POST")
async def trigger_friendly_chat() -> Dict[str, Any]:
    """Manually trigger a friendly chat message generation.

    Generates and sends a chat message immediately based on recent activities.
    """
    chat_service = get_friendly_chat_service()
    message = await chat_service.trigger_immediate_chat()

    if message:
        return {
            "success": True,
            "message": "Chat message generated",
            "data": {"chat_message": message},
        }
    else:
        return {
            "success": False,
            "message": "Failed to generate chat message (no recent activities or LLM error)",
        }
