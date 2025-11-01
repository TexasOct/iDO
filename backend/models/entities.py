"""
数据实体模型定义
定义系统中的核心数据结构
"""

from typing import List, Optional
from datetime import datetime
from .base import BaseModel


# ============ 基础模型 ============

class Event(BaseModel):
    """事件模型 - 从raw_records提取"""
    id: str
    title: str
    description: str
    keywords: List[str]
    timestamp: datetime
    created_at: Optional[datetime] = None


class Knowledge(BaseModel):
    """知识模型 - 从raw_records提取的原始知识"""
    id: str
    title: str
    description: str
    keywords: List[str]
    created_at: datetime
    deleted: bool = False


class Todo(BaseModel):
    """待办模型 - 从raw_records提取的原始待办"""
    id: str
    title: str
    description: str
    keywords: List[str]
    created_at: datetime
    completed: bool = False
    deleted: bool = False


# ============ 合并后的模型 ============

class CombinedKnowledge(BaseModel):
    """合并后的知识 - 每20分钟合并一次相关knowledge"""
    id: str
    title: str
    description: str
    keywords: List[str]
    merged_from_ids: List[str]  # 合并来源的knowledge IDs
    created_at: datetime
    deleted: bool = False


class CombinedTodo(BaseModel):
    """合并后的待办 - 每20分钟合并一次相关todo"""
    id: str
    title: str
    description: str
    keywords: List[str]
    merged_from_ids: List[str]  # 合并来源的todo IDs
    created_at: datetime
    completed: bool = False
    deleted: bool = False


# ============ 活动和日记模型 ============

class Activity(BaseModel):
    """活动模型 - 从events聚合而来"""
    id: str
    title: str
    description: str
    start_time: datetime
    end_time: datetime
    source_event_ids: List[str]  # 引用的event ID列表
    created_at: datetime
    deleted: bool = False


class Diary(BaseModel):
    """日记模型 - 从activities总结而来"""
    id: str
    date: str  # YYYY-MM-DD格式
    content: str  # 日记内容（包含对activity的引用）
    source_activity_ids: List[str]  # 引用的activity ID列表
    created_at: datetime
    deleted: bool = False
