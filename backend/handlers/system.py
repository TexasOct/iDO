"""
System module command handlers
System module command handlers
"""

from typing import Dict, Any
from datetime import datetime
from pathlib import Path

from core.coordinator import get_coordinator
from core.db import get_db
from core.settings import get_settings

from . import api_handler
from models.requests import (
    UpdateSettingsRequest,
    ImageOptimizationConfigRequest,
    ImageCompressionConfigRequest,
)
from system.runtime import start_runtime, stop_runtime, get_runtime_stats


@api_handler()
async def start_system() -> Dict[str, Any]:
    """Start the entire backend system (perception + processing)

    @returns Success response with message and timestamp
    """
    coordinator = get_coordinator()
    if coordinator.is_running:
        return {
            "success": True,
            "message": "System is already running",
            "timestamp": datetime.now().isoformat(),
        }

    try:
        coordinator = await start_runtime()
        status_payload = {
            "isRunning": coordinator.is_running,
            "status": coordinator.mode,
            "lastError": coordinator.last_error,
            "activeModel": coordinator.active_model,
        }

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

        return {
            "success": success,
            "message": message,
            "data": status_payload,
            "timestamp": datetime.now().isoformat(),
        }
    except RuntimeError as exc:
        return {
            "success": False,
            "message": str(exc),
            "timestamp": datetime.now().isoformat(),
        }


@api_handler()
async def stop_system() -> Dict[str, Any]:
    """Stop the entire backend system

    @returns Success response with message and timestamp
    """
    coordinator = get_coordinator()
    if not coordinator.is_running:
        return {
            "success": True,
            "message": "System is not running",
            "timestamp": datetime.now().isoformat(),
        }

    await stop_runtime()
    return {
        "success": True,
        "message": "System stopped",
        "timestamp": datetime.now().isoformat(),
    }


@api_handler()
async def get_system_stats() -> Dict[str, Any]:
    """Get overall system status

    @returns System statistics with perception and processing info
    """
    stats = await get_runtime_stats()
    return {"success": True, "data": stats, "timestamp": datetime.now().isoformat()}


@api_handler()
async def get_database_path() -> Dict[str, Any]:
    """Get the absolute path of the database being used by the backend"""
    db = get_db()
    db_path = Path(db.db_path).resolve()
    return {
        "success": True,
        "data": {"path": str(db_path)},
        "timestamp": datetime.now().isoformat(),
    }


@api_handler()
async def get_settings_info() -> Dict[str, Any]:
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
async def update_settings(body: UpdateSettingsRequest) -> Dict[str, Any]:
    """Update application configuration

    Note: LLM configuration has been migrated to multi-model management system
    See create_model() and select_model() in models_management.py

    @param body Contains configuration items to update
    @returns Update result
    """
    settings = get_settings()

    # Update database path
    if body.database_path:
        if not settings.set_database_path(body.database_path):
            return {
                "success": False,
                "message": "Failed to update database path",
                "timestamp": datetime.now().isoformat(),
            }

    # Update screenshot save path
    if body.screenshot_save_path:
        if not settings.set_screenshot_path(body.screenshot_save_path):
            return {
                "success": False,
                "message": "Failed to update screenshot save path",
                "timestamp": datetime.now().isoformat(),
            }

    return {
        "success": True,
        "message": "Configuration updated successfully",
        "data": settings.get_all(),
        "timestamp": datetime.now().isoformat(),
    }


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
        from processing.image_compression import get_image_optimizer

        optimizer = get_image_optimizer()
        stats = optimizer.get_stats()

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
        from processing.image_compression import get_image_optimizer

        optimizer = get_image_optimizer()
        stats = optimizer.reset_stats()

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
