"""
Tauri 事件发送管理器
用于从后端发送事件通知到前端
"""

import json
from typing import Dict, Any, Optional, Callable
from core.logger import get_logger

logger = get_logger(__name__)

# 全局事件发送函数注册
_emit_handler: Optional[Callable] = None


def register_emit_handler(emit_func: Callable):
    """注册事件发送函数（由 PyTauri 入口提供）"""
    global _emit_handler
    _emit_handler = emit_func
    logger.info("已注册 Tauri 事件发送处理器")


def emit_activity_created(activity_data: Dict[str, Any]) -> bool:
    """
    发送"活动创建"事件到前端

    Args:
        activity_data: 活动数据字典，包含:
            - id: 活动 ID
            - description: 活动描述
            - startTime: 开始时间
            - endTime: 结束时间
            - version: 版本号
            - createdAt: 创建时间

    Returns:
        True if sent successfully, False otherwise
    """
    if _emit_handler is None:
        logger.debug("事件发送处理器未注册（可能在测试模式或启动阶段），活动将通过数据库同步传递")
        return False

    try:
        payload = {
            "type": "activity_created",
            "data": activity_data,
            "timestamp": activity_data.get("createdAt")
        }
        _emit_handler("activity-created", payload)
        logger.debug(f"✅ 已发送活动创建事件: {activity_data.get('id')}")
        return True
    except Exception as e:
        logger.error(f"❌ 发送活动创建事件失败: {e}")
        return False


def emit_activity_updated(activity_data: Dict[str, Any]) -> bool:
    """
    发送"活动更新"事件到前端

    Args:
        activity_data: 更新后的活动数据，应包含:
            - id: 活动 ID
            - description: 活动描述
            - startTime: 开始时间
            - endTime: 结束时间
            - version: 版本号
            - createdAt: 创建时间

    Returns:
        True if sent successfully, False otherwise
    """
    if _emit_handler is None:
        logger.debug("事件发送处理器未注册（可能在测试模式或启动阶段），活动更新将通过数据库同步传递")
        return False

    try:
        payload = {
            "type": "activity_updated",
            "data": activity_data,
            "timestamp": activity_data.get("createdAt")
        }
        _emit_handler("activity-updated", payload)
        logger.debug(f"✅ 已发送活动更新事件: {activity_data.get('id')}")
        return True
    except Exception as e:
        logger.error(f"❌ 发送活动更新事件失败: {e}")
        return False


def emit_activity_deleted(activity_id: str, timestamp: Optional[str] = None) -> bool:
    """
    发送"活动删除"事件到前端

    Args:
        activity_id: 被删除的活动 ID
        timestamp: 删除时间戳

    Returns:
        True if sent successfully, False otherwise
    """
    if _emit_handler is None:
        logger.debug("事件发送处理器未注册（可能在测试模式或启动阶段），活动删除通知将不被发送")
        return False

    try:
        from datetime import datetime
        payload = {
            "type": "activity_deleted",
            "data": {
                "id": activity_id,
                "deletedAt": timestamp or datetime.now().isoformat()
            },
            "timestamp": timestamp or datetime.now().isoformat()
        }
        _emit_handler("activity-deleted", payload)
        logger.debug(f"✅ 已发送活动删除事件: {activity_id}")
        return True
    except Exception as e:
        logger.error(f"❌ 发送活动删除事件失败: {e}")
        return False


def emit_bulk_update_completed(updated_count: int, timestamp: Optional[str] = None) -> bool:
    """
    发送"批量更新完成"事件到前端
    用于通知前端有多个活动被批量更新

    Args:
        updated_count: 更新的活动数量
        timestamp: 操作时间戳

    Returns:
        True if sent successfully, False otherwise
    """
    if _emit_handler is None:
        logger.debug("事件发送处理器未注册（可能在测试模式或启动阶段），批量更新通知将不被发送")
        return False

    try:
        from datetime import datetime
        payload = {
            "type": "bulk_update_completed",
            "data": {
                "updatedCount": updated_count,
                "timestamp": timestamp or datetime.now().isoformat()
            },
            "timestamp": timestamp or datetime.now().isoformat()
        }
        _emit_handler("bulk-update-completed", payload)
        logger.debug(f"✅ 已发送批量更新完成事件: {updated_count} 个活动")
        return True
    except Exception as e:
        logger.error(f"❌ 发送批量更新完成事件失败: {e}")
        return False
