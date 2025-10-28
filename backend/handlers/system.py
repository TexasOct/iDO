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
from models.requests import UpdateSettingsRequest
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

    await start_runtime()
    return {
        "success": True,
        "message": "系统已启动",
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

    @returns 应用配置信息
    """
    settings = get_settings()
    all_settings = settings.get_all()

    return {
        "success": True,
        "data": {
            "settings": all_settings,
            "llm": settings.get_llm_settings(),
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

    @param body 包含要更新的配置项
    @returns 更新结果
    """
    settings = get_settings()

    # 更新 LLM 配置
    if body.llm:
        success = settings.set_llm_settings(
            provider=body.llm.provider,
            api_key=body.llm.api_key,
            model=body.llm.model,
            base_url=body.llm.base_url
        )
        if not success:
            return {
                "success": False,
                "message": "更新 LLM 配置失败",
                "timestamp": datetime.now().isoformat()
            }

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
