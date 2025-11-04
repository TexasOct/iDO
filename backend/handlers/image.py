"""
Image Management API Handler
Provides APIs for image caching, cleanup, statistics, and optimization
"""

from . import api_handler
from models import BaseModel
from processing.image_manager import get_image_manager
from processing.image_optimization import get_image_filter
from core.logger import get_logger
from core.settings import get_settings
from typing import List

logger = get_logger(__name__)


class CleanupImagesRequest(BaseModel):
    """Clean up images request model"""

    max_age_hours: int = 24


class GetImagesRequest(BaseModel):
    """Get images request model"""

    hashes: List[str]


@api_handler(body=None, method="GET", path="/image/stats", tags=["image"])
async def get_image_stats() -> dict:
    """
    Get image cache statistics

    Returns:
        Image cache and disk usage statistics
    """
    try:
        image_manager = get_image_manager()
        stats = image_manager.get_cache_stats()
        return {"success": True, "stats": stats}
    except Exception as e:
        logger.error(f"Failed to get image statistics: {e}")
        return {"success": False, "error": str(e)}


@api_handler(
    body=GetImagesRequest, method="POST", path="/image/get-cached", tags=["image"]
)
async def get_cached_images(body: GetImagesRequest) -> dict:
    """
    Batch get images from memory (base64 format)

    Args:
        body: Request containing image hash list

    Returns:
        Dictionary containing base64 data
    """
    try:
        image_manager = get_image_manager()
        images = image_manager.get_multiple_from_cache(body.hashes)
        missing_hashes = [
            img_hash for img_hash in body.hashes if img_hash not in images
        ]

        # Fallback: try to load thumbnails from disk
        if missing_hashes:
            for img_hash in missing_hashes:
                try:
                    base64_data = image_manager.load_thumbnail_base64(img_hash)
                    if base64_data:
                        images[img_hash] = base64_data
                except Exception as e:
                    logger.warning(
                        f"Failed to load image from disk: {img_hash[:8]} - {e}"
                    )

        return {
            "success": True,
            "images": images,
            "found_count": len(images),
            "requested_count": len(body.hashes),
        }
    except Exception as e:
        logger.error(f"Failed to get cached images: {e}")
        return {"success": False, "error": str(e), "images": {}}


@api_handler(
    body=CleanupImagesRequest, method="POST", path="/image/cleanup", tags=["image"]
)
async def cleanup_old_images(body: CleanupImagesRequest) -> dict:
    """
    Clean up old image files

    Args:
        body: Request containing maximum retention time

    Returns:
        Cleanup result statistics
    """
    try:
        image_manager = get_image_manager()
        cleaned_count = image_manager.cleanup_old_files(body.max_age_hours)

        return {
            "success": True,
            "cleaned_count": cleaned_count,
            "message": f"Cleaned up {cleaned_count} old image files",
        }
    except Exception as e:
        logger.error(f"Failed to clean up images: {e}")
        return {"success": False, "error": str(e)}


@api_handler(body=None, method="POST", path="/image/clear-cache", tags=["image"])
async def clear_memory_cache() -> dict:
    """
    Clear memory cache

    Returns:
        Cleanup result
    """
    try:
        image_manager = get_image_manager()
        count = image_manager.clear_memory_cache()

        return {
            "success": True,
            "cleared_count": count,
            "message": f"Cleared {count} memory cached images",
        }
    except Exception as e:
        logger.error(f"Failed to clear memory cache: {e}")
        return {"success": False, "error": str(e)}


@api_handler(
    body=None,
    method="GET",
    path="/image/optimization/config",
    tags=["image", "optimization"],
)
async def get_image_optimization_config() -> dict:
    """
    Get image optimization configuration

    Returns:
        Current image optimization configuration
    """
    try:
        settings = get_settings()
        config = settings.get_image_optimization_config()

        return {"success": True, "config": config}
    except Exception as e:
        logger.error(f"Failed to get image optimization configuration: {e}")
        return {"success": False, "error": str(e)}


@api_handler(
    body=None,
    method="GET",
    path="/image/optimization/stats",
    tags=["image", "optimization"],
)
async def get_image_optimization_stats() -> dict:
    """
    Get image optimization statistics

    Returns:
        Information including sampling statistics, skip reason distribution, etc.
    """
    try:
        image_filter = get_image_filter()
        stats_summary = image_filter.get_stats_summary()

        # Get configuration
        settings = get_settings()
        config = settings.get_image_optimization_config()

        return {
            "success": True,
            "stats": {
                "optimization": stats_summary.get("optimization", {}),
                "diff_analyzer": stats_summary.get("diff_analyzer", {}),
                "content_analyzer": stats_summary.get("content_analyzer", {}),
                "sampler": stats_summary.get("sampler", {}),
            },
            "config": config,
        }
    except Exception as e:
        logger.error(f"Failed to get image optimization statistics: {e}")
        return {"success": False, "error": str(e)}


class ImageOptimizationConfigRequest(BaseModel):
    """Image optimization configuration update request"""

    enabled: bool = True
    strategy: str = "hybrid"  # none, sampling, content_aware, hybrid
    phash_threshold: float = 0.15
    min_interval: float = 2.0
    max_images: int = 8
    enable_content_analysis: bool = True
    enable_text_detection: bool = False


@api_handler(
    body=ImageOptimizationConfigRequest,
    method="POST",
    path="/image/optimization/config",
    tags=["image", "optimization"],
)
async def update_image_optimization_config(
    body: ImageOptimizationConfigRequest,
) -> dict:
    """
    Update image optimization configuration

    Args:
        body: Request body containing optimization configuration

    Returns:
        Update result and current configuration
    """
    try:
        settings = get_settings()
        config_dict = {
            "enabled": body.enabled,
            "strategy": body.strategy,
            "phash_threshold": body.phash_threshold,
            "min_interval": body.min_interval,
            "max_images": body.max_images,
            "enable_content_analysis": body.enable_content_analysis,
            "enable_text_detection": body.enable_text_detection,
        }

        success = settings.set_image_optimization_config(config_dict)

        if success:
            # Reinitialize image filter to apply new configuration
            try:
                from processing.image_optimization import get_image_filter

                get_image_filter(reset=True)
                logger.info("Image filter has been reinitialized")
            except Exception as e:
                logger.warning(f"Failed to reinitialize image filter: {e}")

            return {
                "success": True,
                "message": "Image optimization configuration updated",
                "config": config_dict,
            }
        else:
            return {"success": False, "error": "Configuration update failed"}
    except Exception as e:
        logger.error(f"Failed to update image optimization configuration: {e}")
        return {"success": False, "error": str(e)}
