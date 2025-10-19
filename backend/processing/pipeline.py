"""
处理管道
实现 raw_records → events → activity 的完整处理流程
"""

import asyncio
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from core.models import RawRecord, Event, Activity, RecordType
from core.logger import get_logger
from .filter_rules import EventFilter
from .summarizer import EventSummarizer
from .merger import ActivityMerger
from .persistence import ProcessingPersistence

logger = get_logger(__name__)


class ProcessingPipeline:
    """处理管道"""
    
    def __init__(self, 
                 processing_interval: int = 10,
                 persistence: Optional[ProcessingPersistence] = None):
        """
        初始化处理管道
        
        Args:
            processing_interval: 处理间隔（秒）
            persistence: 持久化处理器
        """
        self.processing_interval = processing_interval
        self.persistence = persistence or ProcessingPersistence()
        
        # 初始化处理器
        self.event_filter = EventFilter()
        self.summarizer = EventSummarizer()
        self.merger = ActivityMerger()
        
        # 运行状态
        self.is_running = False
        self.current_activity = None
        self.last_processing_time = None
        
        # 统计信息
        self.stats = {
            "total_processed": 0,
            "events_created": 0,
            "activities_created": 0,
            "activities_merged": 0,
            "last_processing_time": None
        }
    
    async def start(self):
        """启动处理管道"""
        if self.is_running:
            logger.warning("处理管道已在运行中")
            return
        
        self.is_running = True
        logger.info(f"处理管道已启动，处理间隔: {self.processing_interval} 秒")
    
    async def stop(self):
        """停止处理管道"""
        if not self.is_running:
            return
        
        self.is_running = False
        logger.info("处理管道已停止")
    
    async def process_raw_records(self, raw_records: List[RawRecord]) -> Dict[str, Any]:
        """处理原始记录"""
        if not raw_records:
            return {"events": [], "activities": [], "merged": False}
        
        try:
            logger.info(f"开始处理 {len(raw_records)} 条原始记录")
            
            # 1. 事件筛选
            filtered_records = self.event_filter.filter_all_events(raw_records)
            logger.debug(f"筛选后剩余 {len(filtered_records)} 条记录")
            
            if not filtered_records:
                logger.info("筛选后无有效记录")
                return {"events": [], "activities": [], "merged": False}
            
            # 2. 创建事件
            events = await self._create_events(filtered_records)
            logger.debug(f"创建了 {len(events)} 个事件")
            
            # 3. 处理活动
            activity_result = await self._process_activities(events)
            
            # 4. 更新统计
            self._update_stats(len(raw_records), len(events), activity_result)
            
            logger.info(f"处理完成: {len(events)} 个事件, {len(activity_result.get('activities', []))} 个活动")
            
            return {
                "events": events,
                "activities": activity_result.get("activities", []),
                "merged": activity_result.get("merged", False)
            }
            
        except Exception as e:
            logger.error(f"处理原始记录失败: {e}")
            return {"events": [], "activities": [], "merged": False}
    
    async def _create_events(self, filtered_records: List[RawRecord]) -> List[Event]:
        """创建事件"""
        events = []
        
        # 按时间分组记录（每10秒一组）
        grouped_records = self._group_records_by_time(filtered_records, 10)
        
        for group in grouped_records:
            if not group:
                continue
            
            # 为每组记录创建一个事件
            event = await self._create_single_event(group)
            if event:
                events.append(event)
        
        return events
    
    def _group_records_by_time(self, records: List[RawRecord], interval_seconds: int) -> List[List[RawRecord]]:
        """按时间间隔分组记录"""
        if not records:
            return []
        
        # 按时间排序
        sorted_records = sorted(records, key=lambda x: x.timestamp)
        
        groups = []
        current_group = []
        group_start_time = sorted_records[0].timestamp
        
        for record in sorted_records:
            time_diff = (record.timestamp - group_start_time).total_seconds()
            
            if time_diff <= interval_seconds:
                current_group.append(record)
            else:
                if current_group:
                    groups.append(current_group)
                current_group = [record]
                group_start_time = record.timestamp
        
        if current_group:
            groups.append(current_group)
        
        return groups
    
    async def _create_single_event(self, records: List[RawRecord]) -> Optional[Event]:
        """创建单个事件"""
        if not records:
            return None
        
        try:
            # 确定事件类型（取最常见的类型）
            type_counts = {}
            for record in records:
                type_name = record.type.value
                type_counts[type_name] = type_counts.get(type_name, 0) + 1
            
            most_common_type = max(type_counts, key=type_counts.get)
            event_type = RecordType(most_common_type)
            
            # 计算时间范围
            start_time = min(record.timestamp for record in records)
            end_time = max(record.timestamp for record in records)

            # 生成事件摘要
            summary = await self.summarizer.summarize_events(records)
            
            # 创建事件
            event = Event(
                id=str(uuid.uuid4()),
                start_time=start_time,
                end_time=end_time,
                type=event_type,
                summary=summary,
                source_data=records
            )
            
            # 持久化事件
            await self.persistence.save_event(event)
            
            return event
            
        except Exception as e:
            logger.error(f"创建事件失败: {e}")
            return None
    
    async def _process_activities(self, events: List[Event]) -> Dict[str, Any]:
        """处理活动 - 顺序遍历events，逐个判断是否合并"""
        if not events:
            return {"activities": [], "merged": False}
        
        activities = []
        merged = False
        
        # 顺序遍历所有events
        for event in events:
            if not self.current_activity:
                # 没有当前活动，创建第一个活动
                self.current_activity = await self._create_activity_from_event(event)
                logger.info(f"创建第一个活动: {self.current_activity['id']}")
            else:
                # 有当前活动，判断是否合并
                should_merge, confidence, merged_description = await self.merger._llm_judge_merge(
                    self.current_activity, event
                )
                
                if should_merge:
                    # 合并到当前活动
                    self.current_activity = await self.merger.merge_activity_with_event(
                        self.current_activity, event, merged_description
                    )
                    merged = True
                    logger.info(f"事件已合并到当前活动，置信度: {confidence:.2f}")
                else:
                    # 不合并，保存当前活动并创建新活动
                    await self.persistence.save_activity(self.current_activity)
                    activities.append(self.current_activity)
                    logger.info(f"保存活动: {self.current_activity['id']}")
                    
                    # 创建新活动
                    self.current_activity = await self._create_activity_from_event(event)
                    logger.info(f"创建新活动: {self.current_activity['id']}")
        
        activities.append(self.current_activity)
        
        return {"activities": activities, "merged": merged}
    
    async def _create_activity_from_event(self, event: Event) -> Dict[str, Any]:
        """从单个事件创建活动"""
        try:
            activity = {
                "id": str(uuid.uuid4()),
                "description": event.summary,  # 使用event的summary作为activity的description
                "start_time": event.start_time,
                "end_time": event.end_time,
                "source_events": [event],  # 将event添加到source_events
                "event_count": 1,
                "created_at": datetime.now()
            }
            
            logger.info(f"从事件创建活动: {activity['id']} - {event.summary}")
            return activity
            
        except Exception as e:
            logger.error(f"从事件创建活动失败: {e}")
            raise
    
    async def _create_new_activity(self, events: List[Event]) -> Optional[Dict[str, Any]]:
        """创建新活动"""
        if not events:
            return None
        
        try:
            # 计算时间范围
            all_records = []
            for event in events:
                all_records.extend(event.source_data)
            
            start_time = min(record.timestamp for record in all_records)
            end_time = max(record.timestamp for record in all_records)
            
            # 生成活动描述
            description = await self.summarizer.summarize_activity(all_records)
            
            # 创建活动
            activity = {
                "id": str(uuid.uuid4()),
                "description": description,
                "start_time": start_time,
                "end_time": end_time,
                "source_events": events,
                "event_count": len(all_records),
                "created_at": datetime.now()
            }
            
            logger.info(f"创建新活动: {activity['id']} - {description}")
            return activity
            
        except Exception as e:
            logger.error(f"创建新活动失败: {e}")
            return None
    
    def _update_stats(self, raw_count: int, event_count: int, activity_result: Dict[str, Any]):
        """更新统计信息"""
        self.stats["total_processed"] += raw_count
        self.stats["events_created"] += event_count
        self.stats["last_processing_time"] = datetime.now()
        
        activities = activity_result.get("activities", [])
        if activity_result.get("merged", False):
            self.stats["activities_merged"] += 1
        else:
            self.stats["activities_created"] += len(activities)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "is_running": self.is_running,
            "processing_interval": self.processing_interval,
            "current_activity": self.current_activity is not None,
            "stats": self.stats.copy()
        }
    
    def set_processing_interval(self, interval: int):
        """设置处理间隔"""
        self.processing_interval = max(1, interval)
        logger.info(f"处理间隔设置为: {self.processing_interval} 秒")
    
    async def force_finalize_activity(self):
        """强制完成当前活动"""
        if self.current_activity:
            try:
                await self.persistence.save_activity(self.current_activity)
                logger.info(f"强制完成活动: {self.current_activity['id']}")
                self.current_activity = None
            except Exception as e:
                logger.error(f"强制完成活动失败: {e}")
    
    async def get_recent_activities(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取最近的活动"""
        try:
            return await self.persistence.get_recent_activities(limit)
        except Exception as e:
            logger.error(f"获取最近活动失败: {e}")
            return []
    
    async def get_recent_events(self, limit: int = 50) -> List[Event]:
        """获取最近的事件"""
        try:
            return await self.persistence.get_recent_events(limit)
        except Exception as e:
            logger.error(f"获取最近事件失败: {e}")
            return []
