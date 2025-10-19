"""
Processing API 路由
提供事件和活动处理的 REST API 接口
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime, timedelta
from core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/processing", tags=["processing"])

# 全局处理管道实例（在实际应用中应该通过依赖注入）
_processing_pipeline = None


def get_processing_pipeline():
    """获取处理管道实例"""
    global _processing_pipeline
    if _processing_pipeline is None:
        from processing.pipeline import ProcessingPipeline
        _processing_pipeline = ProcessingPipeline()
    return _processing_pipeline


@router.get("/stats")
async def get_processing_stats():
    """获取处理模块统计信息"""
    try:
        pipeline = get_processing_pipeline()
        stats = pipeline.get_stats()
        return {
            "success": True,
            "data": stats,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"获取处理统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {e}")


@router.post("/process")
async def process_raw_records(records: List[dict]):
    """处理原始记录"""
    try:
        pipeline = get_processing_pipeline()
        
        # 转换字典为 RawRecord 对象
        from core.models import RawRecord, RecordType
        raw_records = []
        
        for record_data in records:
            try:
                raw_record = RawRecord(
                    timestamp=datetime.fromisoformat(record_data["timestamp"]),
                    type=RecordType(record_data["type"]),
                    data=record_data["data"]
                )
                raw_records.append(raw_record)
            except Exception as e:
                logger.warning(f"跳过无效记录: {e}")
                continue
        
        # 处理记录
        result = await pipeline.process_raw_records(raw_records)
        
        # 转换结果
        events_data = []
        for event in result["events"]:
            events_data.append({
                "id": event.id,
                "start_time": event.start_time.isoformat(),
                "end_time": event.end_time.isoformat(),
                "type": event.type.value,
                "summary": event.summary,
                "source_data_count": len(event.source_data)
            })
        
        activities_data = []
        for activity in result["activities"]:
            activities_data.append({
                "id": activity["id"],
                "description": activity["description"],
                "start_time": activity["start_time"].isoformat() if isinstance(activity["start_time"], datetime) else activity["start_time"],
                "end_time": activity["end_time"].isoformat() if isinstance(activity["end_time"], datetime) else activity["end_time"],
                "event_count": activity.get("event_count", 0)
            })
        
        return {
            "success": True,
            "data": {
                "events": events_data,
                "activities": activities_data,
                "merged": result["merged"],
                "processed_count": len(raw_records)
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"处理原始记录失败: {e}")
        raise HTTPException(status_code=500, detail=f"处理记录失败: {e}")


@router.get("/events")
async def get_events(
    limit: int = Query(50, ge=1, le=500, description="返回事件数量限制"),
    event_type: Optional[str] = Query(None, description="事件类型过滤"),
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间")
):
    """获取处理后的事件"""
    try:
        pipeline = get_processing_pipeline()
        
        if event_type:
            events = await pipeline.persistence.get_events_by_type(event_type, limit)
        elif start_time and end_time:
            events = await pipeline.persistence.get_events_in_timeframe(start_time, end_time)
        else:
            events = await pipeline.get_recent_events(limit)
        
        events_data = []
        for event in events:
            events_data.append({
                "id": event.id,
                "start_time": event.start_time.isoformat(),
                "end_time": event.end_time.isoformat(),
                "type": event.type.value,
                "summary": event.summary,
                "source_data_count": len(event.source_data)
            })
        
        return {
            "success": True,
            "data": {
                "events": events_data,
                "count": len(events_data),
                "filters": {
                    "limit": limit,
                    "event_type": event_type,
                    "start_time": start_time.isoformat() if start_time else None,
                    "end_time": end_time.isoformat() if end_time else None
                }
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取事件失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取事件失败: {e}")


@router.get("/activities")
async def get_activities(
    limit: int = Query(20, ge=1, le=100, description="返回活动数量限制"),
):
    """获取处理后的活动"""
    try:
        pipeline = get_processing_pipeline()
        
        activities = await pipeline.get_recent_activities(limit)
        
        activities_data = []
        for activity in activities:
            activities_data.append({
                "id": activity["id"],
                "description": activity["description"],
                "start_time": activity["start_time"].isoformat() if isinstance(activity["start_time"], datetime) else activity["start_time"],
                "end_time": activity["end_time"].isoformat() if isinstance(activity["end_time"], datetime) else activity["end_time"],
                "event_count": activity.get("event_count", 0),
                "created_at": activity.get("created_at", datetime.now()).isoformat()
            })
        
        return {
            "success": True,
            "data": {
                "activities": activities_data,
                "count": len(activities_data),
                "filters": {
                    "limit": limit,
                }
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取活动失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取活动失败: {e}")


@router.get("/events/{event_id}")
async def get_event_by_id(event_id: str):
    """根据ID获取事件详情"""
    try:
        pipeline = get_processing_pipeline()
        
        # 从数据库获取事件详情
        events_data = pipeline.persistence.db.execute_query(
            "SELECT * FROM events WHERE id = ?",
            (event_id,)
        )
        
        if not events_data:
            raise HTTPException(status_code=404, detail="事件不存在")
        
        event_data = events_data[0]
        
        # 解析源数据
        source_data = []
        if event_data.get("source_data"):
            import json
            source_data_json = json.loads(event_data["source_data"]) if isinstance(event_data["source_data"], str) else event_data["source_data"]
            source_data = source_data_json
        
        event_detail = {
            "id": event_data["id"],
            "start_time": event_data["start_time"],
            "end_time": event_data["end_time"],
            "type": event_data["type"],
            "summary": event_data["summary"],
            "source_data": source_data,
            "created_at": event_data.get("created_at")
        }
        
        return {
            "success": True,
            "data": event_detail,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取事件详情失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取事件详情失败: {e}")


@router.get("/activities/{activity_id}")
async def get_activity_by_id(activity_id: str):
    """根据ID获取活动详情"""
    try:
        pipeline = get_processing_pipeline()
        
        # 从数据库获取活动详情
        activities_data = pipeline.persistence.db.execute_query(
            "SELECT * FROM activities WHERE id = ?",
            (activity_id,)
        )
        
        if not activities_data:
            raise HTTPException(status_code=404, detail="活动不存在")
        
        activity_data = activities_data[0]
        
        # 解析源事件
        source_events = []
        if activity_data.get("source_events"):
            import json
            source_events_json = json.loads(activity_data["source_events"]) if isinstance(activity_data["source_events"], str) else activity_data["source_events"]
            source_events = source_events_json
        
        activity_detail = {
            "id": activity_data["id"],
            "description": activity_data["description"],
            "start_time": activity_data["start_time"],
            "end_time": activity_data["end_time"],
            "source_events": source_events,
            "created_at": activity_data.get("created_at")
        }
        
        return {
            "success": True,
            "data": activity_detail,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取活动详情失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取活动详情失败: {e}")


@router.post("/start")
async def start_processing():
    """启动处理管道"""
    try:
        pipeline = get_processing_pipeline()
        await pipeline.start()
        
        return {
            "success": True,
            "message": "处理管道已启动",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"启动处理管道失败: {e}")
        raise HTTPException(status_code=500, detail=f"启动处理管道失败: {e}")


@router.post("/stop")
async def stop_processing():
    """停止处理管道"""
    try:
        pipeline = get_processing_pipeline()
        await pipeline.stop()
        
        return {
            "success": True,
            "message": "处理管道已停止",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"停止处理管道失败: {e}")
        raise HTTPException(status_code=500, detail=f"停止处理管道失败: {e}")


@router.post("/finalize")
async def finalize_current_activity():
    """强制完成当前活动"""
    try:
        pipeline = get_processing_pipeline()
        await pipeline.force_finalize_activity()
        
        return {
            "success": True,
            "message": "当前活动已强制完成",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"强制完成活动失败: {e}")
        raise HTTPException(status_code=500, detail=f"强制完成活动失败: {e}")


@router.delete("/cleanup")
async def cleanup_old_data(days: int = Query(30, ge=1, le=365, description="保留天数")):
    """清理旧数据"""
    try:
        pipeline = get_processing_pipeline()
        result = await pipeline.persistence.delete_old_data(days)
        
        return {
            "success": True,
            "data": result,
            "message": f"已清理 {days} 天前的数据",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"清理旧数据失败: {e}")
        raise HTTPException(status_code=500, detail=f"清理旧数据失败: {e}")


@router.get("/persistence/stats")
async def get_persistence_stats():
    """获取持久化统计信息"""
    try:
        pipeline = get_processing_pipeline()
        stats = pipeline.persistence.get_stats()
        
        return {
            "success": True,
            "data": stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取持久化统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取持久化统计失败: {e}")
