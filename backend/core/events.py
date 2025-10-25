"""
Tauri 事件发送管理器
用于从后端发送事件通知到前端
"""

from typing import Any, Dict, Optional

from pydantic import RootModel

try:
    from pytauri import AppHandle, Emitter
except ImportError:  # pragma: no cover - 在非 Tauri 环境（如离线脚本、测试）下可能无法导入
    AppHandle = Any  # type: ignore[assignment]
    Emitter = None  # type: ignore[assignment]
from core._event_state import event_state
from core.logger import get_logger

logger = get_logger(__name__)

class _RawEventPayload(RootModel[Dict[str, Any]]):
    """包装事件负载以便通过 PyTauri 进行 JSON 序列化。"""


def register_emit_handler(app_handle: AppHandle):
    """注册 Tauri AppHandle，用于通过 PyTauri Emitter 发送事件。"""
    if Emitter is None:
        logger.warning("未安装 PyTauri，事件通知功能不可用")
        return

    event_state.app_handle = app_handle
    logger.info("已注册 Tauri AppHandle 用于事件发送")


def _emit(event_name: str, payload: Dict[str, Any]) -> bool:
    """通过 PyTauri 向前端发送事件。"""
    if Emitter is None:
        logger.debug(f"[events] PyTauri Emitter 不可用，跳过事件发送: {event_name}")
        return False

    if event_state.app_handle is None:
        logger.warning(f"[events] AppHandle 未注册，无法发送事件: {event_name}")
        return False

    try:
        Emitter.emit(event_state.app_handle, event_name, _RawEventPayload(payload))
        return True
    except Exception as exc:  # pragma: no cover - 运行时异常记录日志
        logger.error(f"❌ [events] 发送事件失败: {event_name}", exc_info=True)
        return False


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
    logger.debug(
        "[emit_activity_created] 尝试发送活动创建事件，AppHandle已注册: %s",
        event_state.app_handle is not None,
    )

    payload = {
        "type": "activity_created",
        "data": activity_data,
        "timestamp": activity_data.get("createdAt")
    }

    success = _emit("activity-created", payload)
    if success:
        logger.info(f"✅ [emit_activity_created] 成功发送活动创建事件: {activity_data.get('id')}")
    return success


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
    payload = {
        "type": "activity_updated",
        "data": activity_data,
        "timestamp": activity_data.get("createdAt")
    }

    success = _emit("activity-updated", payload)
    if success:
        logger.debug(f"✅ 已发送活动更新事件: {activity_data.get('id')}")
    return success


def emit_activity_deleted(activity_id: str, timestamp: Optional[str] = None) -> bool:
    """
    发送"活动删除"事件到前端

    Args:
        activity_id: 被删除的活动 ID
        timestamp: 删除时间戳

    Returns:
        True if sent successfully, False otherwise
    """
    from datetime import datetime

    resolved_timestamp = timestamp or datetime.now().isoformat()
    payload = {
        "type": "activity_deleted",
        "data": {
            "id": activity_id,
            "deletedAt": resolved_timestamp
        },
        "timestamp": resolved_timestamp
    }

    success = _emit("activity-deleted", payload)
    if success:
        logger.debug(f"✅ 已发送活动删除事件: {activity_id}")
    return success


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
    from datetime import datetime

    resolved_timestamp = timestamp or datetime.now().isoformat()
    payload = {
        "type": "bulk_update_completed",
        "data": {
            "updatedCount": updated_count,
            "timestamp": resolved_timestamp
        },
        "timestamp": resolved_timestamp
    }

    success = _emit("bulk-update-completed", payload)
    if success:
        logger.debug(f"✅ 已发送批量更新完成事件: {updated_count} 个活动")
    return success


def emit_agent_task_update(
    task_id: str,
    status: str,
    progress: Optional[int] = None,
    result: Optional[Any] = None,
    error: Optional[str] = None
) -> bool:
    """
    发送"Agent任务更新"事件到前端

    Args:
        task_id: 任务 ID
        status: 任务状态 (todo/processing/done/failed)
        progress: 任务进度（可选）
        result: 任务结果（可选）
        error: 错误信息（可选）

    Returns:
        True if sent successfully, False otherwise
    """
    payload = {
        "taskId": task_id,
        "status": status,
    }

    if progress is not None:
        payload["progress"] = progress
    if result is not None:
        payload["result"] = result
    if error is not None:
        payload["error"] = error

    success = _emit("agent-task-update", payload)
    if success:
        logger.info(f"✅ 已发送Agent任务更新事件: {task_id} -> {status}")
    return success
