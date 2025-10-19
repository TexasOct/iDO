"""
Perception API 路由
提供感知数据的 REST API 接口
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime, timedelta
from core.models import RawRecord, RecordType
from core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/perception", tags=["perception"])

# 全局感知管理器实例（在实际应用中应该通过依赖注入）
_perception_manager = None


def get_perception_manager():
    """获取感知管理器实例"""
    global _perception_manager
    if _perception_manager is None:
        from perception.manager import PerceptionManager
        _perception_manager = PerceptionManager()
    return _perception_manager


@router.get("/stats")
async def get_perception_stats():
    """获取感知模块统计信息"""
    try:
        manager = get_perception_manager()
        stats = manager.get_stats()
        return {
            "success": True,
            "data": stats,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"获取感知统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {e}")


@router.get("/records")
async def get_records(
    limit: int = Query(100, ge=1, le=1000, description="返回记录数量限制"),
    event_type: Optional[str] = Query(None, description="事件类型过滤"),
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间")
):
    """获取感知记录"""
    try:
        manager = get_perception_manager()
        
        if event_type:
            # 按类型获取
            records = manager.get_records_by_type(event_type)
        elif start_time and end_time:
            # 按时间范围获取
            records = manager.get_records_in_timeframe(start_time, end_time)
        else:
            # 获取最近记录
            records = manager.get_recent_records(limit)
        
        # 转换为字典格式
        records_data = []
        for record in records:
            record_dict = {
                "timestamp": record.timestamp.isoformat(),
                "type": record.type.value,
                "data": record.data
            }
            records_data.append(record_dict)
        
        return {
            "success": True,
            "data": {
                "records": records_data,
                "count": len(records_data),
                "filters": {
                    "limit": limit,
                    "event_type": event_type,
                    "start_time": start_time.isoformat() if start_time else None,
                    "end_time": end_time.isoformat() if end_time else None
                }
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"无效的参数: {e}")
    except Exception as e:
        logger.error(f"获取感知记录失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取记录失败: {e}")


@router.get("/records/keyboard")
async def get_keyboard_records(
    limit: int = Query(50, ge=1, le=500, description="返回记录数量限制")
):
    """获取键盘事件记录"""
    try:
        manager = get_perception_manager()
        records = manager.get_records_by_type("keyboard_event")
        
        # 限制数量
        records = records[-limit:] if len(records) > limit else records
        
        records_data = []
        for record in records:
            record_dict = {
                "timestamp": record.timestamp.isoformat(),
                "key": record.data.get("key", "unknown"),
                "action": record.data.get("action", "unknown"),
                "modifiers": record.data.get("modifiers", []),
                "key_type": record.data.get("key_type", "unknown")
            }
            records_data.append(record_dict)
        
        return {
            "success": True,
            "data": {
                "records": records_data,
                "count": len(records_data)
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取键盘记录失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取键盘记录失败: {e}")


@router.get("/records/mouse")
async def get_mouse_records(
    limit: int = Query(50, ge=1, le=500, description="返回记录数量限制")
):
    """获取鼠标事件记录"""
    try:
        manager = get_perception_manager()
        records = manager.get_records_by_type("mouse_event")
        
        # 限制数量
        records = records[-limit:] if len(records) > limit else records
        
        records_data = []
        for record in records:
            record_dict = {
                "timestamp": record.timestamp.isoformat(),
                "action": record.data.get("action", "unknown"),
                "button": record.data.get("button", "unknown"),
                "position": record.data.get("position"),
                "start_position": record.data.get("start_position"),
                "end_position": record.data.get("end_position"),
                "duration": record.data.get("duration")
            }
            records_data.append(record_dict)
        
        return {
            "success": True,
            "data": {
                "records": records_data,
                "count": len(records_data)
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取鼠标记录失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取鼠标记录失败: {e}")


@router.get("/records/screenshots")
async def get_screenshot_records(
    limit: int = Query(20, ge=1, le=100, description="返回记录数量限制")
):
    """获取屏幕截图记录"""
    try:
        manager = get_perception_manager()
        records = manager.get_records_by_type("screenshot")
        
        # 限制数量
        records = records[-limit:] if len(records) > limit else records
        
        records_data = []
        for record in records:
            record_dict = {
                "timestamp": record.timestamp.isoformat(),
                "width": record.data.get("width", 0),
                "height": record.data.get("height", 0),
                "size_bytes": record.data.get("size_bytes", 0),
                "hash": record.data.get("hash", ""),
                "format": record.data.get("format", "unknown"),
                "monitor": record.data.get("monitor", {})
            }
            records_data.append(record_dict)
        
        return {
            "success": True,
            "data": {
                "records": records_data,
                "count": len(records_data)
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取屏幕截图记录失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取屏幕截图记录失败: {e}")


@router.post("/start")
async def start_perception():
    """启动感知模块"""
    try:
        manager = get_perception_manager()
        if manager.is_running:
            return {
                "success": True,
                "message": "感知模块已在运行中",
                "timestamp": datetime.now().isoformat()
            }
        
        await manager.start()
        return {
            "success": True,
            "message": "感知模块已启动",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"启动感知模块失败: {e}")
        raise HTTPException(status_code=500, detail=f"启动感知模块失败: {e}")


@router.post("/stop")
async def stop_perception():
    """停止感知模块"""
    try:
        manager = get_perception_manager()
        if not manager.is_running:
            return {
                "success": True,
                "message": "感知模块未在运行",
                "timestamp": datetime.now().isoformat()
            }
        
        await manager.stop()
        return {
            "success": True,
            "message": "感知模块已停止",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"停止感知模块失败: {e}")
        raise HTTPException(status_code=500, detail=f"停止感知模块失败: {e}")


@router.delete("/records")
async def clear_records():
    """清空所有记录"""
    try:
        manager = get_perception_manager()
        manager.storage.clear()
        manager.clear_buffer()
        
        return {
            "success": True,
            "message": "所有记录已清空",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"清空记录失败: {e}")
        raise HTTPException(status_code=500, detail=f"清空记录失败: {e}")


@router.get("/buffer")
async def get_buffer():
    """获取缓冲区中的事件"""
    try:
        manager = get_perception_manager()
        events = manager.get_buffered_events()
        
        events_data = []
        for event in events:
            event_dict = {
                "timestamp": event.timestamp.isoformat(),
                "type": event.type.value,
                "data": event.data
            }
            events_data.append(event_dict)
        
        return {
            "success": True,
            "data": {
                "events": events_data,
                "count": len(events_data)
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取缓冲区事件失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取缓冲区事件失败: {e}")
