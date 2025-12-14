"""
System module handlers

Provides comprehensive system management functionality including:
- System lifecycle: start/stop/stats
- Settings and configuration management
- Image optimization and compression
- Initial setup workflow
- System tray management
- Demo/greeting endpoints
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from core.coordinator import get_coordinator
from core.db import get_db
from core.logger import get_logger
from core.settings import get_settings
from models import Person
from models.base import BaseModel, OperationResponse
from models.requests import (
    ImageCompressionConfigRequest,
    ImageOptimizationConfigRequest,
    UpdateSettingsRequest,
)
from models.responses import (
    DatabasePathData,
    DatabasePathResponse,
    SystemResponse,
    SystemStatusData,
    UpdateSettingsResponse,
)
from system.runtime import get_runtime_stats, start_runtime, stop_runtime

from . import api_handler

logger = get_logger(__name__)


# ============================================================================
# System Lifecycle Management
# ============================================================================


@api_handler()
async def start_system() -> SystemResponse:
    """Start the entire backend system (perception + processing)

    @returns Success response with message and timestamp
    """
    coordinator = get_coordinator()
    timestamp = datetime.now().isoformat()

    if coordinator.is_running:
        return SystemResponse(
            success=True,
            message="System is already running",
            data=SystemStatusData(
                is_running=coordinator.is_running,
                status=coordinator.mode,
                last_error=coordinator.last_error,
                active_model=coordinator.active_model,
            ),
            timestamp=timestamp,
        )

    try:
        coordinator = await start_runtime()

        if coordinator.is_running:
            message = "System started"
            success = True
        elif coordinator.mode == "requires_model":
            message = (
                coordinator.last_error or "No active LLM model configuration detected"
            )
            success = True
        else:
            message = coordinator.last_error or "System failed to start"
            success = False

        return SystemResponse(
            success=success,
            message=message,
            data=SystemStatusData(
                is_running=coordinator.is_running,
                status=coordinator.mode,
                last_error=coordinator.last_error,
                active_model=coordinator.active_model,
            ),
            timestamp=timestamp,
        )
    except RuntimeError as exc:
        return SystemResponse(
            success=False,
            message=str(exc),
            data=None,
            timestamp=timestamp,
        )


@api_handler()
async def stop_system() -> SystemResponse:
    """Stop the entire backend system

    @returns Success response with message and timestamp
    """
    coordinator = get_coordinator()
    timestamp = datetime.now().isoformat()

    if not coordinator.is_running:
        return SystemResponse(
            success=True,
            message="System is not running",
            data=None,
            timestamp=timestamp,
        )

    await stop_runtime()
    return SystemResponse(
        success=True,
        message="System stopped",
        data=None,
        timestamp=timestamp,
    )


@api_handler()
async def get_system_stats() -> SystemResponse:
    """Get overall system status

    @returns System statistics with perception and processing info
    """
    stats = await get_runtime_stats()
    return SystemResponse(
        success=True, data=stats, timestamp=datetime.now().isoformat()  # type: ignore
    )


@api_handler()
async def get_database_path() -> DatabasePathResponse:
    """Get the absolute path of the database being used by the backend"""
    db = get_db()
    db_path = Path(db.db_path).resolve()
    return DatabasePathResponse(
        success=True,
        data=DatabasePathData(path=str(db_path)),
        timestamp=datetime.now().isoformat(),
    )


@api_handler()
async def get_settings_info() -> Dict[str, Any]:  # Keep as Dict for now due to complex structure
    """Get all application configurations

    Note: LLM configuration has been migrated to multi-model management system
    See get_active_model() in models_management.py

    @returns Application configuration information
    """
    settings = get_settings()
    all_settings = settings.get_all()

    return {
        "success": True,
        "data": {
            "settings": all_settings,
            "database": {"path": settings.get_database_path()},
            "screenshot": {"savePath": settings.get_screenshot_path()},
            "image": {
                # Expose image memory cache configuration for frontend/management interface display/adjustment
                "memoryCacheSize": int(settings.get("image.memory_cache_size", 500))
            },
        },
        "timestamp": datetime.now().isoformat(),
    }


@api_handler(body=UpdateSettingsRequest)
async def update_settings(body: UpdateSettingsRequest) -> UpdateSettingsResponse:
    """Update application configuration

    Note: LLM configuration has been migrated to multi-model management system
    See create_model() and select_model() in models_management.py

    @param body Contains configuration items to update
    @returns Update result
    """
    settings = get_settings()
    timestamp = datetime.now().isoformat()

    # Update database path
    if body.database_path:
        if not settings.set_database_path(body.database_path):
            return UpdateSettingsResponse(
                success=False,
                message="Failed to update database path",
                timestamp=timestamp,
            )

    # Update screenshot save path
    if body.screenshot_save_path:
        if not settings.set_screenshot_path(body.screenshot_save_path):
            return UpdateSettingsResponse(
                success=False,
                message="Failed to update screenshot save path",
                timestamp=timestamp,
            )

    return UpdateSettingsResponse(
        success=True,
        message="Configuration updated successfully",
        timestamp=timestamp,
    )


@api_handler()
async def get_image_optimization_config() -> Dict[str, Any]:
    """Get image optimization configuration

    @returns Current image optimization configuration
    """
    settings = get_settings()
    config = settings.get_image_optimization_config()

    return {"success": True, "data": config, "timestamp": datetime.now().isoformat()}


@api_handler(body=ImageOptimizationConfigRequest)
async def update_image_optimization_config(
    body: ImageOptimizationConfigRequest,
) -> Dict[str, Any]:
    """Update image optimization configuration

    @param body Contains image optimization configuration items to update
    @returns Success response with updated configuration
    """
    settings = get_settings()
    current_config = settings.get_image_optimization_config()

    # Update configuration (only update provided fields)
    if body.enabled is not None:
        current_config["enabled"] = body.enabled
    if body.strategy is not None:
        current_config["strategy"] = body.strategy
    if body.phash_threshold is not None:
        current_config["phash_threshold"] = body.phash_threshold
    if body.min_interval is not None:
        current_config["min_interval"] = body.min_interval
    if body.max_images is not None:
        current_config["max_images"] = body.max_images
    if body.enable_content_analysis is not None:
        current_config["enable_content_analysis"] = body.enable_content_analysis
    if body.enable_text_detection is not None:
        current_config["enable_text_detection"] = body.enable_text_detection

    # Save configuration
    success = settings.set_image_optimization_config(current_config)

    if not success:
        return {
            "success": False,
            "message": "Failed to update image optimization configuration",
            "timestamp": datetime.now().isoformat(),
        }

    return {
        "success": True,
        "message": "Image optimization configuration updated successfully",
        "data": current_config,
        "timestamp": datetime.now().isoformat(),
    }


@api_handler()
async def get_image_compression_config() -> Dict[str, Any]:
    """Get image compression configuration

    @returns Image compression configuration information
    """
    settings = get_settings()
    config = settings.get_image_compression_config()

    return {"success": True, "data": config, "timestamp": datetime.now().isoformat()}


@api_handler(body=ImageCompressionConfigRequest)
async def update_image_compression_config(
    body: ImageCompressionConfigRequest,
) -> Dict[str, Any]:
    """Update image compression configuration

    @param body Contains image compression configuration items to update
    @returns Success response with updated configuration
    """
    settings = get_settings()
    current_config = settings.get_image_compression_config()

    # Update configuration (only update provided fields)
    if body.compression_level is not None:
        current_config["compression_level"] = body.compression_level
    if body.enable_region_cropping is not None:
        current_config["enable_region_cropping"] = body.enable_region_cropping
    if body.crop_threshold is not None:
        current_config["crop_threshold"] = body.crop_threshold

    # Save configuration
    success = settings.set_image_compression_config(current_config)

    if not success:
        return {
            "success": False,
            "message": "Failed to update image compression configuration",
            "timestamp": datetime.now().isoformat(),
        }

    return {
        "success": True,
        "message": "Image compression configuration updated successfully",
        "data": current_config,
        "timestamp": datetime.now().isoformat(),
    }


@api_handler()
async def get_image_compression_stats() -> Dict[str, Any]:
    """Get image compression statistics

    @returns Image compression statistics data
    """
    try:
        from processing.image_processing import get_image_compressor

        compressor = get_image_compressor()
        stats = compressor.get_stats()

        return {"success": True, "data": stats, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to get image compression statistics: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        }


@api_handler()
async def reset_image_compression_stats() -> Dict[str, Any]:
    """Reset image compression statistics

    @returns Success response
    """
    try:
        from processing.image_processing import get_image_compressor

        # Reset by creating a new compressor instance
        _compressor = get_image_compressor(reset=True)

        return {
            "success": True,
            "message": "Image compression statistics reset",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to reset image compression statistics: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        }


# ============================================================================
# Initial Setup Management
# ============================================================================


@api_handler()
async def check_initial_setup() -> Dict[str, Any]:
    """Check if initial setup is required

    Returns status indicating whether the application needs initial configuration:
    - has_models: Whether any LLM models are configured
    - has_active_model: Whether an active model is selected
    - has_completed_setup: Whether user has completed the initial setup flow
    - needs_setup: Whether initial setup flow should be shown

    @returns Setup status with detailed configuration state
    """
    try:
        db = get_db()

        # Check if any models are configured
        models = db.models.get_all()
        has_models = len(models) > 0

        # Check if there's an active model
        active_model = db.models.get_active()
        has_active_model = active_model is not None

        # Check if user has completed the initial setup flow (persisted in settings)
        setup_completed_str = db.settings.get("has_completed_initial_setup", "false")
        has_completed_setup = (setup_completed_str or "false").lower() in ("true", "1", "yes")

        # Determine if setup is needed
        # Setup is required if user hasn't completed setup AND there are no models configured
        needs_setup = not has_completed_setup and not has_models

        logger.debug(
            f"Initial setup check: has_models={has_models}, "
            f"has_active_model={has_active_model}, "
            f"has_completed_setup={has_completed_setup}, "
            f"needs_setup={needs_setup}"
        )

        return {
            "success": True,
            "data": {
                "has_models": has_models,
                "has_active_model": has_active_model,
                "has_completed_setup": has_completed_setup,
                "needs_setup": needs_setup,
                "model_count": len(models),
            },
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to check initial setup: {e}")
        return {
            "success": False,
            "message": f"Failed to check initial setup: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        }


@api_handler()
async def complete_initial_setup() -> Dict[str, Any]:
    """Mark initial setup as completed

    Persists the setup completion status in the settings table.
    Once marked as completed, the welcome flow won't show again
    unless the setting is manually reset.

    @returns Success status
    """
    try:
        db = get_db()

        # Persist the completion status in settings
        db.settings.set(
            key="has_completed_initial_setup",
            value="true",
            setting_type="bool",
            description="Indicates whether user has completed the initial setup flow",
        )

        logger.info("Initial setup marked as completed")

        return {
            "success": True,
            "message": "Initial setup completed successfully",
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to mark setup as completed: {e}")
        return {
            "success": False,
            "message": f"Failed to mark setup as completed: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        }


# ============================================================================
# System Tray Management
# ============================================================================


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


class TrayUpdateResponse(OperationResponse):
    """Response from tray update operation."""


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
        message="Tray menu labels noted (static menu in current implementation)",
    )


class TrayVisibilityRequest(BaseModel):
    """Request to change tray icon visibility."""

    visible: bool


class TrayVisibilityResponse(OperationResponse):
    """Response from tray visibility operation."""
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
        visible=body.visible,  # Echo back the requested state
        message="Tray visibility update recorded",
    )


# ============================================================================
# Demo/Testing Endpoints
# ============================================================================


@api_handler(body=Person, method="POST", path="/greeting", tags=["demo"])
async def greeting(body: Person) -> str:
    """A simple demo command that returns a greeting message.

    @param body - The person to greet.
    """
    return f"Hello, {body.name}!"
