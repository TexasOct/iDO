"""
数据模型定义
包含 RawRecord, Event, Activity, Task 等核心数据模型
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass
import json


class RecordType(Enum):
    """记录类型枚举"""
    KEYBOARD_RECORD = "keyboard_record"
    MOUSE_RECORD = "mouse_record"
    SCREENSHOT_RECORD = "screenshot_record"


class TaskStatus(Enum):
    """任务状态枚举"""
    TODO = "todo"
    DOING = "doing"
    DONE = "done"
    CANCELLED = "cancelled"


@dataclass
class RawRecord:
    """原始记录数据模型"""
    timestamp: datetime
    type: RecordType
    data: Dict[str, Any]
    screenshot_path: Optional[str] = None  # 截图文件路径
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "type": self.type.value,
            "data": self.data,
            "screenshot_path": self.screenshot_path
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RawRecord':
        """从字典创建实例"""
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            type=RecordType(data["type"]),
            data=data["data"],
            screenshot_path=data.get("screenshot_path")
        )


@dataclass
class Event:
    """事件数据模型"""
    id: str
    start_time: datetime
    end_time: datetime
    type: RecordType
    summary: str
    source_data: List[RawRecord]  # 10s 内的所有筛选过后留下的record按照时间顺序排列
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "type": self.type.value,
            "summary": self.summary,
            "source_data": [record.to_dict() for record in self.source_data]
        }


@dataclass
class Activity:
    """活动数据模型"""
    id: str
    description: str
    start_time: datetime
    end_time: datetime
    source_events: List[Event]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "description": self.description,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "source_events": [event.to_dict() for event in self.source_events]
        }


@dataclass
class Task:
    """任务数据模型"""
    id: str
    title: str
    description: str
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    agent_type: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "agent_type": self.agent_type,
            "parameters": self.parameters or {}
        }
