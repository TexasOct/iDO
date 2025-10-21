"""
System module command handlers
系统模块的命令处理器
"""

from typing import Dict, Any
from datetime import datetime
from . import api_handler


@api_handler()
async def start_system() -> Dict[str, Any]:
    """启动整个后端系统（perception + processing）

    @returns Success response with message and timestamp
    """
    from core.coordinator import get_coordinator
    
    coordinator = get_coordinator()
    if coordinator.is_running:
        return {
            "success": True,
            "message": "系统已在运行中",
            "timestamp": datetime.now().isoformat()
        }
    
    await coordinator.start()
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
    from core.coordinator import get_coordinator
    
    coordinator = get_coordinator()
    if not coordinator.is_running:
        return {
            "success": True,
            "message": "系统未在运行",
            "timestamp": datetime.now().isoformat()
        }
    
    await coordinator.stop()
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
    from core.coordinator import get_coordinator
    
    coordinator = get_coordinator()
    stats = coordinator.get_stats()
    return {
        "success": True,
        "data": stats,
        "timestamp": datetime.now().isoformat()
    }
