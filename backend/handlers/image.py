"""
图片管理 API Handler
提供图片缓存、清理、统计和优化相关的 API
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
    """清理图片请求模型"""
    max_age_hours: int = 24


class GetImagesRequest(BaseModel):
    """获取图片请求模型"""
    hashes: List[str]


@api_handler(
    body=None,
    method="GET",
    path="/image/stats",
    tags=["image"]
)
async def get_image_stats() -> dict:
    """
    获取图片缓存统计信息

    Returns:
        图片缓存和磁盘使用统计
    """
    try:
        image_manager = get_image_manager()
        stats = image_manager.get_cache_stats()
        return {
            "success": True,
            "stats": stats
        }
    except Exception as e:
        logger.error(f"获取图片统计失败: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@api_handler(
    body=GetImagesRequest,
    method="POST",
    path="/image/get-cached",
    tags=["image"]
)
async def get_cached_images(body: GetImagesRequest) -> dict:
    """
    批量获取内存中的图片（base64格式）

    Args:
        body: 包含图片 hash 列表的请求

    Returns:
        包含 base64 数据的字典
    """
    try:
        image_manager = get_image_manager()
        images = image_manager.get_multiple_from_cache(body.hashes)
        missing_hashes = [img_hash for img_hash in body.hashes if img_hash not in images]

        # 回退：尝试从磁盘加载缩略图
        if missing_hashes:
            for img_hash in missing_hashes:
                try:
                    base64_data = image_manager.load_thumbnail_base64(img_hash)
                    if base64_data:
                        images[img_hash] = base64_data
                except Exception as e:
                    logger.warning(f"从磁盘加载图片失败: {img_hash[:8]} - {e}")

        return {
            "success": True,
            "images": images,
            "found_count": len(images),
            "requested_count": len(body.hashes)
        }
    except Exception as e:
        logger.error(f"获取缓存图片失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "images": {}
        }


@api_handler(
    body=CleanupImagesRequest,
    method="POST",
    path="/image/cleanup",
    tags=["image"]
)
async def cleanup_old_images(body: CleanupImagesRequest) -> dict:
    """
    清理旧的图片文件

    Args:
        body: 包含最大保留时间的请求

    Returns:
        清理结果统计
    """
    try:
        image_manager = get_image_manager()
        cleaned_count = image_manager.cleanup_old_files(body.max_age_hours)

        return {
            "success": True,
            "cleaned_count": cleaned_count,
            "message": f"已清理 {cleaned_count} 个旧图片文件"
        }
    except Exception as e:
        logger.error(f"清理图片失败: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@api_handler(
    body=None,
    method="POST",
    path="/image/clear-cache",
    tags=["image"]
)
async def clear_memory_cache() -> dict:
    """
    清空内存缓存

    Returns:
        清理结果
    """
    try:
        image_manager = get_image_manager()
        count = image_manager.clear_memory_cache()

        return {
            "success": True,
            "cleared_count": count,
            "message": f"已清空 {count} 个内存缓存的图片"
        }
    except Exception as e:
        logger.error(f"清空内存缓存失败: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@api_handler(
    body=None,
    method="GET",
    path="/image/optimization/config",
    tags=["image", "optimization"]
)
async def get_image_optimization_config() -> dict:
    """
    获取图像优化配置

    Returns:
        当前的图像优化配置
    """
    try:
        settings = get_settings()
        config = settings.get_image_optimization_config()

        return {
            "success": True,
            "config": config
        }
    except Exception as e:
        logger.error(f"获取图像优化配置失败: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@api_handler(
    body=None,
    method="GET",
    path="/image/optimization/stats",
    tags=["image", "optimization"]
)
async def get_image_optimization_stats() -> dict:
    """
    获取图像优化统计信息

    Returns:
        包含采样统计、跳过原因分布等信息
    """
    try:
        image_filter = get_image_filter()
        stats_summary = image_filter.get_stats_summary()

        # 获取配置
        settings = get_settings()
        config = settings.get_image_optimization_config()

        return {
            "success": True,
            "stats": {
                "optimization": stats_summary.get('optimization', {}),
                "diff_analyzer": stats_summary.get('diff_analyzer', {}),
                "content_analyzer": stats_summary.get('content_analyzer', {}),
                "sampler": stats_summary.get('sampler', {})
            },
            "config": config
        }
    except Exception as e:
        logger.error(f"获取图像优化统计失败: {e}")
        return {
            "success": False,
            "error": str(e)
        }


class ImageOptimizationConfigRequest(BaseModel):
    """图像优化配置更新请求"""
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
    tags=["image", "optimization"]
)
async def update_image_optimization_config(body: ImageOptimizationConfigRequest) -> dict:
    """
    更新图像优化配置

    Args:
        body: 包含新配置的请求体

    Returns:
        更新结果
    """
    try:
        settings = get_settings()
        config_dict = {
            'enabled': body.enabled,
            'strategy': body.strategy,
            'phash_threshold': body.phash_threshold,
            'min_interval': body.min_interval,
            'max_images': body.max_images,
            'enable_content_analysis': body.enable_content_analysis,
            'enable_text_detection': body.enable_text_detection
        }

        success = settings.set_image_optimization_config(config_dict)

        if success:
            # 重新初始化图像过滤器以应用新配置
            try:
                from processing.image_optimization import get_image_filter
                get_image_filter(reset=True)
                logger.info("图像过滤器已重新初始化")
            except Exception as e:
                logger.warning(f"重新初始化图像过滤器失败: {e}")

            return {
                "success": True,
                "message": "图像优化配置已更新",
                "config": config_dict
            }
        else:
            return {
                "success": False,
                "error": "配置更新失败"
            }
    except Exception as e:
        logger.error(f"更新图像优化配置失败: {e}")
        return {
            "success": False,
            "error": str(e)
        }
