"""
滑动窗口存储
实现 20 秒临时滑动窗口，超时自动删除
"""

import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from collections import deque
from threading import Lock
from core.models import RawRecord, RecordType
from core.logger import get_logger

logger = get_logger(__name__)


class SlidingWindowStorage:
    """滑动窗口存储管理器"""
    
    def __init__(self, window_size: int = 20):
        """
        初始化滑动窗口存储
        
        Args:
            window_size: 窗口大小（秒）
        """
        self.window_size = window_size
        self.records: deque = deque()
        self.lock = Lock()
        self._last_cleanup = time.time()
        self._cleanup_interval = 5.0  # 每5秒清理一次过期数据
        
    def add_record(self, record: RawRecord) -> None:
        """添加记录到滑动窗口"""
        try:
            with self.lock:
                self.records.append(record)
                
                # 定期清理过期数据
                current_time = time.time()
                if current_time - self._last_cleanup > self._cleanup_interval:
                    self._cleanup_expired_records()
                    self._last_cleanup = current_time
                
        except Exception as e:
            logger.error(f"添加记录到滑动窗口失败: {e}")
    
    def get_records(self, 
                   event_type: Optional[RecordType] = None,
                   start_time: Optional[datetime] = None,
                   end_time: Optional[datetime] = None) -> List[RawRecord]:
        """
        获取记录
        
        Args:
            event_type: 事件类型过滤
            start_time: 开始时间过滤
            end_time: 结束时间过滤
            
        Returns:
            过滤后的记录列表
        """
        try:
            with self.lock:
                # 先清理过期数据
                self._cleanup_expired_records()
                
                filtered_records = []
                for record in self.records:
                    # 类型过滤
                    if event_type and record.type != event_type:
                        continue
                    
                    # 时间过滤
                    if start_time and record.timestamp < start_time:
                        continue
                    if end_time and record.timestamp > end_time:
                        continue
                    
                    filtered_records.append(record)
                
                return filtered_records
                
        except Exception as e:
            logger.error(f"获取记录失败: {e}")
            return []
    
    def get_latest_records(self, count: int = 10) -> List[RawRecord]:
        """获取最新的 N 条记录"""
        try:
            with self.lock:
                self._cleanup_expired_records()
                return list(self.records)[-count:]
        except Exception as e:
            logger.error(f"获取最新记录失败: {e}")
            return []
    
    def get_records_by_type(self, event_type: RecordType) -> List[RawRecord]:
        """根据事件类型获取记录"""
        return self.get_records(event_type=event_type)
    
    def get_records_in_timeframe(self, start_time: datetime, end_time: datetime) -> List[RawRecord]:
        """获取指定时间范围内的记录"""
        return self.get_records(start_time=start_time, end_time=end_time)
    
    def _cleanup_expired_records(self) -> None:
        """清理过期记录"""
        try:
            current_time = datetime.now()
            cutoff_time = current_time - timedelta(seconds=self.window_size)
            
            # 从左侧删除过期记录
            while self.records and self.records[0].timestamp < cutoff_time:
                self.records.popleft()
                
        except Exception as e:
            logger.error(f"清理过期记录失败: {e}")
    
    def clear(self) -> None:
        """清空所有记录"""
        try:
            with self.lock:
                self.records.clear()
                logger.info("滑动窗口存储已清空")
        except Exception as e:
            logger.error(f"清空存储失败: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取存储统计信息"""
        try:
            with self.lock:
                self._cleanup_expired_records()
                
                # 统计各类型记录数量
                type_counts = {}
                for record in self.records:
                    type_name = record.type.value
                    type_counts[type_name] = type_counts.get(type_name, 0) + 1
                
                return {
                    "total_records": len(self.records),
                    "window_size_seconds": self.window_size,
                    "type_counts": type_counts,
                    "oldest_record": self.records[0].timestamp if self.records else None,
                    "newest_record": self.records[-1].timestamp if self.records else None,
                    "last_cleanup": self._last_cleanup
                }
        except Exception as e:
            logger.error(f"获取存储统计失败: {e}")
            return {"error": str(e)}


class EventBuffer:
    """事件缓冲区，用于临时存储和批量处理"""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.buffer: List[RawRecord] = []
        self.lock = Lock()
    
    def add(self, record: RawRecord) -> None:
        """添加事件到缓冲区"""
        try:
            with self.lock:
                self.buffer.append(record)
                
                # 如果缓冲区满了，移除最旧的记录
                if len(self.buffer) > self.max_size:
                    self.buffer.pop(0)
                    
        except Exception as e:
            logger.error(f"添加事件到缓冲区失败: {e}")
    
    def get_all(self) -> List[RawRecord]:
        """获取所有事件并清空缓冲区"""
        try:
            with self.lock:
                events = self.buffer.copy()
                self.buffer.clear()
                return events
        except Exception as e:
            logger.error(f"获取缓冲区事件失败: {e}")
            return []
    
    def peek(self) -> List[RawRecord]:
        """查看缓冲区内容但不清空"""
        try:
            with self.lock:
                return self.buffer.copy()
        except Exception as e:
            logger.error(f"查看缓冲区失败: {e}")
            return []
    
    def clear(self) -> None:
        """清空缓冲区"""
        try:
            with self.lock:
                self.buffer.clear()
        except Exception as e:
            logger.error(f"清空缓冲区失败: {e}")
    
    def size(self) -> int:
        """获取缓冲区大小"""
        try:
            with self.lock:
                return len(self.buffer)
        except Exception as e:
            logger.error(f"获取缓冲区大小失败: {e}")
            return 0
