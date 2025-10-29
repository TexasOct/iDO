"""
System module command handlers
系统模块的命令处理器
"""

from typing import Dict, Any
from datetime import datetime
from pathlib import Path

from core.coordinator import get_coordinator
from core.db import get_db
from core.settings import get_settings

from . import api_handler
from models.requests import UpdateSettingsRequest, ImageOptimizationConfigRequest, ImageCompressionConfigRequest
from system.runtime import start_runtime, stop_runtime, get_runtime_stats


@api_handler()
async def start_system() -> Dict[str, Any]:
    """启动整个后端系统（perception + processing）

    @returns Success response with message and timestamp
    """
    coordinator = get_coordinator()
    if coordinator.is_running:
        return {
            "success": True,
            "message": "系统已在运行中",
            "timestamp": datetime.now().isoformat()
        }

    try:
        await start_runtime()
        return {
            "success": True,
            "message": "系统已启动",
            "timestamp": datetime.now().isoformat()
        }
    except RuntimeError as exc:
        return {
            "success": False,
            "message": str(exc),
            "timestamp": datetime.now().isoformat()
        }


@api_handler()
async def stop_system() -> Dict[str, Any]:
    """停止整个后端系统

    @returns Success response with message and timestamp
    """
    coordinator = get_coordinator()
    if not coordinator.is_running:
        return {
            "success": True,
            "message": "系统未在运行",
            "timestamp": datetime.now().isoformat()
        }

    await stop_runtime()
    return {
        "success": True,
        "message": "系统已停止",
        "timestamp": datetime.now().isoformat()
    }


@api_handler()
async def get_system_stats() -> Dict[str, Any]:
    """获取系统整体状态

    @returns System statistics with perception and processing info
    """
    stats = await get_runtime_stats()
    return {
        "success": True,
        "data": stats,
        "timestamp": datetime.now().isoformat()
    }


@api_handler()
async def get_database_path() -> Dict[str, Any]:
    """获取后端正在使用的数据库绝对路径"""
    db = get_db()
    db_path = Path(db.db_path).resolve()
    return {
        "success": True,
        "data": {
            "path": str(db_path)
        },
        "timestamp": datetime.now().isoformat()
    }


@api_handler()
async def get_settings_info() -> Dict[str, Any]:
    """获取所有应用配置

    注意: LLM 配置已迁移到多模型管理系统
    参见 models_management.py 中的 get_active_model()

    @returns 应用配置信息
    """
    settings = get_settings()
    all_settings = settings.get_all()

    return {
        "success": True,
        "data": {
            "settings": all_settings,
            "database": {
                "path": settings.get_database_path()
            },
            "screenshot": {
                "savePath": settings.get_screenshot_path()
            },
            "image": {
                # 暴露图片内存缓存配置，前端或管理界面可用于展示/调整
                "memoryCacheSize": int(settings.get('image.memory_cache_size', 500))
            }
        },
        "timestamp": datetime.now().isoformat()
    }


@api_handler(body=UpdateSettingsRequest)
async def update_settings(body: UpdateSettingsRequest) -> Dict[str, Any]:
    """更新应用配置

    注意: LLM 配置已迁移到多模型管理系统
    参见 models_management.py 中的 create_model() 和 select_model()

    @param body 包含要更新的配置项
    @returns 更新结果
    """
    settings = get_settings()

    # 更新数据库路径
    if body.database_path:
        if not settings.set_database_path(body.database_path):
            return {
                "success": False,
                "message": "更新数据库路径失败",
                "timestamp": datetime.now().isoformat()
            }

    # 更新截屏保存路径
    if body.screenshot_save_path:
        if not settings.set_screenshot_path(body.screenshot_save_path):
            return {
                "success": False,
                "message": "更新截屏保存路径失败",
                "timestamp": datetime.now().isoformat()
            }

    return {
        "success": True,
        "message": "配置更新成功",
        "data": settings.get_all(),
        "timestamp": datetime.now().isoformat()
    }


@api_handler()
async def get_image_optimization_config() -> Dict[str, Any]:
    """获取图像优化配置

    @returns 图像优化配置信息
    """
    settings = get_settings()
    config = settings.get_image_optimization_config()

    return {
        "success": True,
        "data": config,
        "timestamp": datetime.now().isoformat()
    }


@api_handler(body=ImageOptimizationConfigRequest)
async def update_image_optimization_config(body: ImageOptimizationConfigRequest) -> Dict[str, Any]:
    """更新图像优化配置

    @param body 包含要更新的图像优化配置项
    @returns 更新结果
    """
    settings = get_settings()

    # 获取当前配置
    current_config = settings.get_image_optimization_config()

    # 更新配置（只更新提供的字段）
    if body.enabled is not None:
        current_config['enabled'] = body.enabled
    if body.strategy is not None:
        current_config['strategy'] = body.strategy
    if body.phash_threshold is not None:
        current_config['phash_threshold'] = body.phash_threshold
    if body.min_interval is not None:
        current_config['min_interval'] = body.min_interval
    if body.max_images is not None:
        current_config['max_images'] = body.max_images
    if body.enable_content_analysis is not None:
        current_config['enable_content_analysis'] = body.enable_content_analysis
    if body.enable_text_detection is not None:
        current_config['enable_text_detection'] = body.enable_text_detection

    # 保存配置
    success = settings.set_image_optimization_config(current_config)

    if not success:
        return {
            "success": False,
            "message": "更新图像优化配置失败",
            "timestamp": datetime.now().isoformat()
        }

    return {
        "success": True,
        "message": "图像优化配置更新成功",
        "data": current_config,
        "timestamp": datetime.now().isoformat()
    }


@api_handler()
async def get_image_compression_config() -> Dict[str, Any]:
    """获取图像压缩配置

    @returns 图像压缩配置信息
    """
    settings = get_settings()
    config = settings.get_image_compression_config()

    return {
        "success": True,
        "data": config,
        "timestamp": datetime.now().isoformat()
    }


@api_handler(body=ImageCompressionConfigRequest)
async def update_image_compression_config(body: ImageCompressionConfigRequest) -> Dict[str, Any]:
    """更新图像压缩配置

    @param body 包含要更新的图像压缩配置项
    @returns 更新结果
    """
    settings = get_settings()

    # 获取当前配置
    current_config = settings.get_image_compression_config()

    # 更新配置（只更新提供的字段）
    if body.compression_level is not None:
        current_config['compression_level'] = body.compression_level
    if body.enable_region_cropping is not None:
        current_config['enable_region_cropping'] = body.enable_region_cropping
    if body.crop_threshold is not None:
        current_config['crop_threshold'] = body.crop_threshold

    # 保存配置
    success = settings.set_image_compression_config(current_config)

    if not success:
        return {
            "success": False,
            "message": "更新图像压缩配置失败",
            "timestamp": datetime.now().isoformat()
        }

    return {
        "success": True,
        "message": "图像压缩配置更新成功",
        "data": current_config,
        "timestamp": datetime.now().isoformat()
    }


@api_handler()
async def get_image_compression_stats() -> Dict[str, Any]:
    """获取图像压缩统计信息

    @returns 图像压缩统计数据
    """
    try:
        from processing.image_compression import get_image_optimizer

        optimizer = get_image_optimizer()
        stats = optimizer.get_stats()

        return {
            "success": True,
            "data": stats,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"获取图像压缩统计失败: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }


@api_handler()
async def reset_image_compression_stats() -> Dict[str, Any]:
    """重置图像压缩统计信息

    @returns 重置结果
    """
    try:
        from processing.image_compression import get_image_optimizer

        optimizer = get_image_optimizer()
        optimizer.reset()

        return {
            "success": True,
            "message": "图像压缩统计已重置",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"重置图像压缩统计失败: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }
