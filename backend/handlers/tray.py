"""
System tray handlers for managing tray icon and menu updates.
"""

from backend.handlers import api_handler
from backend.models.base import BaseModel


class TrayUpdateRequest(BaseModel):
    """Request to update tray menu labels with i18n translations."""

    show: str
    hide: str
    dashboard: str
    activity: str
    chat: str
    agents: str
    settings: str
    about: str
    quit: str


class TrayUpdateResponse(BaseModel):
    """Response from tray update operation."""

    success: bool
    message: str


@api_handler(
    body=TrayUpdateRequest,
    method="POST",
    path="/tray/update-menu",
    tags=["tray"]
)
async def update_tray_menu(body: TrayUpdateRequest) -> TrayUpdateResponse:
    """
    Update system tray menu labels with i18n translations.

    Note: Due to Tauri limitations, dynamic menu updates require
    rebuilding the entire menu. This is currently handled in Rust.
    This handler serves as a placeholder for future enhancements.

    Args:
        body: Translation strings for menu items

    Returns:
        Success status and message
    """
    # Store translations for potential future use
    # Currently, tray menu is built once at startup in Rust
    return TrayUpdateResponse(
        success=True,
        message="Tray menu labels noted (static menu in current implementation)"
    )


class TrayVisibilityRequest(BaseModel):
    """Request to change tray icon visibility."""

    visible: bool


class TrayVisibilityResponse(BaseModel):
    """Response from tray visibility operation."""

    success: bool
    visible: bool


@api_handler(
    body=TrayVisibilityRequest,
    method="POST",
    path="/tray/visibility",
    tags=["tray"]
)
async def set_tray_visibility(body: TrayVisibilityRequest) -> TrayVisibilityResponse:
    """
    Show or hide the system tray icon.

    Note: Tauri 2.x doesn't support hiding/showing tray icons after creation.
    This is a placeholder for documentation purposes.

    Args:
        body: Visibility state

    Returns:
        Success status and current visibility
    """
    return TrayVisibilityResponse(
        success=True,
        visible=body.visible  # Echo back the requested state
    )
