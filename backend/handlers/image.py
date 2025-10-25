"""
图片管理 API Handler
提供图片缓存、清理和统计相关的 API
"""

from . import api_handler
from models import BaseModel
from processing.image_manager import get_image_manager
from core.logger import get_logger
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
