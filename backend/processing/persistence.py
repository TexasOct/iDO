"""
数据持久化接口
处理 events 和 activities 的数据库存储
"""

import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from core.models import Event, Activity
from core.logger import get_logger
from core.db import get_db

logger = get_logger(__name__)


class ProcessingPersistence:
    """处理数据持久化器"""
    
    def __init__(self):
        self.db = get_db()
    
    def _convert_event_type(self, event_type_str: str) -> 'RecordType':
        """转换事件类型字符串为新的 RecordType 枚举"""
        from core.models import RecordType
        type_mapping = {
            "keyboard_event": RecordType.KEYBOARD_RECORD,
            "mouse_event": RecordType.MOUSE_RECORD,
            "screenshot": RecordType.SCREENSHOT_RECORD,
            # 新格式
            "keyboard_record": RecordType.KEYBOARD_RECORD,
            "mouse_record": RecordType.MOUSE_RECORD,
            "screenshot_record": RecordType.SCREENSHOT_RECORD,
        }
        return type_mapping.get(event_type_str, RecordType.KEYBOARD_RECORD)
    
    async def save_event(self, event: Event) -> bool:
        """保存事件到数据库"""
        try:
            # 准备事件数据
            event_data = {
                "id": event.id,
                "start_time": event.start_time.isoformat(),
                "end_time": event.end_time.isoformat(),
                "type": event.type.value,
                "summary": event.summary,
                "source_data": [record.to_dict() for record in event.source_data]
            }
            
            # 插入到数据库
            self.db.insert_event(
                event_id=event.id,
                start_time=event_data["start_time"],
                end_time=event_data["end_time"],
                event_type=event.type.value,
                summary=event.summary,
                source_data=event_data["source_data"]
            )
            
            logger.debug(f"事件已保存: {event.id}")
            return True
            
        except Exception as e:
            logger.error(f"保存事件失败: {e}")
            return False
    
    async def save_activity(self, activity: Dict[str, Any]) -> bool:
        """保存活动到数据库"""
        try:
            # 准备活动数据
            activity_data = {
                "id": activity["id"],
                "description": activity["description"],
                "start_time": activity["start_time"].isoformat() if isinstance(activity["start_time"], datetime) else activity["start_time"],
                "end_time": activity["end_time"].isoformat() if isinstance(activity["end_time"], datetime) else activity["end_time"],
                "source_events": [event.to_dict() for event in activity.get("source_events", [])],
                "event_count": activity.get("event_count", 0),
                "created_at": activity.get("created_at", datetime.now()).isoformat()
            }
            
            # 插入到数据库
            self.db.insert_activity(
                activity_id=activity["id"],
                description=activity["description"],
                start_time=activity_data["start_time"],
                end_time=activity_data["end_time"],
                source_events=activity_data["source_events"]
            )
            
            logger.debug(f"活动已保存: {activity['id']}")
            return True
            
        except Exception as e:
            logger.error(f"保存活动失败: {e}")
            return False
    
    async def get_recent_events(self, limit: int = 50) -> List[Event]:
        """获取最近的事件"""
        try:
            # 从数据库获取事件数据
            events_data = self.db.get_events(limit=limit)
            
            events = []
            for event_data in events_data:
                try:
                    # 解析源数据
                    source_data = []
                    if event_data.get("source_data"):
                        source_data_json = json.loads(event_data["source_data"]) if isinstance(event_data["source_data"], str) else event_data["source_data"]
                        for record_data in source_data_json:
                            from core.models import RawRecord, RecordType
                            source_data.append(RawRecord(
                                timestamp=datetime.fromisoformat(record_data["timestamp"]),
                                type=RecordType(record_data["type"]),
                                data=record_data["data"]
                            ))
                    
                    # 创建事件对象
                    event = Event(
                        id=event_data["id"],
                        start_time=datetime.fromisoformat(event_data["start_time"]),
                        end_time=datetime.fromisoformat(event_data["end_time"]),
                        type=self._convert_event_type(event_data["type"]),
                        summary=event_data["summary"],
                        source_data=source_data
                    )
                    events.append(event)
                    
                except Exception as e:
                    logger.error(f"解析事件数据失败: {e}")
                    continue
            
            logger.debug(f"获取到 {len(events)} 个事件")
            return events
            
        except Exception as e:
            logger.error(f"获取最近事件失败: {e}")
            return []
    
    async def get_recent_activities(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取最近的活动"""
        try:
            # 从数据库获取活动数据
            activities_data = self.db.get_activities(limit=limit)
            
            activities = []
            for activity_data in activities_data:
                try:
                    # 解析源事件
                    source_events = []
                    if activity_data.get("source_events"):
                        source_events_json = json.loads(activity_data["source_events"]) if isinstance(activity_data["source_events"], str) else activity_data["source_events"]
                        for event_data in source_events_json:
                            # 这里简化处理，实际应该重建完整的 Event 对象
                            source_events.append(event_data)
                    
                    # 创建活动字典
                    activity = {
                        "id": activity_data["id"],
                        "description": activity_data["description"],
                        "start_time": datetime.fromisoformat(activity_data["start_time"]),
                        "end_time": datetime.fromisoformat(activity_data["end_time"]),
                        "source_events": source_events,
                        "created_at": datetime.fromisoformat(activity_data["created_at"]) if activity_data.get("created_at") else datetime.now()
                    }
                    activities.append(activity)
                    
                except Exception as e:
                    logger.error(f"解析活动数据失败: {e}")
                    continue
            
            logger.debug(f"获取到 {len(activities)} 个活动")
            return activities
            
        except Exception as e:
            logger.error(f"获取最近活动失败: {e}")
            return []
    
    async def get_events_by_type(self, event_type: str, limit: int = 50) -> List[Event]:
        """根据类型获取事件"""
        try:
            # 从数据库获取指定类型的事件
            events_data = self.db.execute_query(
                "SELECT * FROM events WHERE type = ? ORDER BY start_time DESC LIMIT ?",
                (event_type, limit)
            )
            
            events = []
            for event_data in events_data:
                try:
                    # 解析源数据
                    source_data = []
                    if event_data.get("source_data"):
                        source_data_json = json.loads(event_data["source_data"]) if isinstance(event_data["source_data"], str) else event_data["source_data"]
                        for record_data in source_data_json:
                            from core.models import RawRecord, RecordType
                            source_data.append(RawRecord(
                                timestamp=datetime.fromisoformat(record_data["timestamp"]),
                                type=RecordType(record_data["type"]),
                                data=record_data["data"]
                            ))
                    
                    # 创建事件对象
                    event = Event(
                        id=event_data["id"],
                        start_time=datetime.fromisoformat(event_data["start_time"]),
                        end_time=datetime.fromisoformat(event_data["end_time"]),
                        type=self._convert_event_type(event_data["type"]),
                        summary=event_data["summary"],
                        source_data=source_data
                    )
                    events.append(event)
                    
                except Exception as e:
                    logger.error(f"解析事件数据失败: {e}")
                    continue
            
            logger.debug(f"获取到 {len(events)} 个 {event_type} 事件")
            return events
            
        except Exception as e:
            logger.error(f"获取 {event_type} 事件失败: {e}")
            return []
    
    
    async def get_events_in_timeframe(self, start_time: datetime, end_time: datetime) -> List[Event]:
        """获取指定时间范围内的事件"""
        try:
            # 从数据库获取时间范围内的事件
            events_data = self.db.execute_query(
                "SELECT * FROM events WHERE start_time >= ? AND end_time <= ? ORDER BY start_time DESC",
                (start_time.isoformat(), end_time.isoformat())
            )
            
            events = []
            for event_data in events_data:
                try:
                    # 解析源数据
                    source_data = []
                    if event_data.get("source_data"):
                        source_data_json = json.loads(event_data["source_data"]) if isinstance(event_data["source_data"], str) else event_data["source_data"]
                        for record_data in source_data_json:
                            from core.models import RawRecord, RecordType
                            source_data.append(RawRecord(
                                timestamp=datetime.fromisoformat(record_data["timestamp"]),
                                type=RecordType(record_data["type"]),
                                data=record_data["data"]
                            ))
                    
                    # 创建事件对象
                    event = Event(
                        id=event_data["id"],
                        start_time=datetime.fromisoformat(event_data["start_time"]),
                        end_time=datetime.fromisoformat(event_data["end_time"]),
                        type=self._convert_event_type(event_data["type"]),
                        summary=event_data["summary"],
                        source_data=source_data
                    )
                    events.append(event)
                    
                except Exception as e:
                    logger.error(f"解析事件数据失败: {e}")
                    continue
            
            logger.debug(f"获取到 {len(events)} 个时间范围内的事件")
            return events
            
        except Exception as e:
            logger.error(f"获取时间范围内事件失败: {e}")
            return []
    
    async def delete_old_data(self, days: int = 30):
        """删除旧数据"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            cutoff_str = cutoff_date.isoformat()
            
            # 删除旧事件
            deleted_events = self.db.execute_delete(
                "DELETE FROM events WHERE start_time < ?",
                (cutoff_str,)
            )
            
            # 删除旧活动
            deleted_activities = self.db.execute_delete(
                "DELETE FROM activities WHERE start_time < ?",
                (cutoff_str,)
            )
            
            logger.info(f"删除了 {deleted_events} 个旧事件和 {deleted_activities} 个旧活动")
            return {"events": deleted_events, "activities": deleted_activities}
            
        except Exception as e:
            logger.error(f"删除旧数据失败: {e}")
            return {"events": 0, "activities": 0}
    
    def get_stats(self) -> Dict[str, Any]:
        """获取持久化统计信息"""
        try:
            # 获取事件统计
            event_count = self.db.execute_query("SELECT COUNT(*) as count FROM events")[0]["count"]
            
            # 获取活动统计
            activity_count = self.db.execute_query("SELECT COUNT(*) as count FROM activities")[0]["count"]
            
            # 获取最近事件时间
            recent_event = self.db.execute_query(
                "SELECT start_time FROM events ORDER BY start_time DESC LIMIT 1"
            )
            last_event_time = recent_event[0]["start_time"] if recent_event else None
            
            # 获取最近活动时间
            recent_activity = self.db.execute_query(
                "SELECT start_time FROM activities ORDER BY start_time DESC LIMIT 1"
            )
            last_activity_time = recent_activity[0]["start_time"] if recent_activity else None
            
            return {
                "total_events": event_count,
                "total_activities": activity_count,
                "last_event_time": last_event_time,
                "last_activity_time": last_activity_time
            }
            
        except Exception as e:
            logger.error(f"获取持久化统计失败: {e}")
            return {
                "total_events": 0,
                "total_activities": 0,
                "last_event_time": None,
                "last_activity_time": None
            }
