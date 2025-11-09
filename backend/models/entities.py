"""
Data entity model definitions
Define core data structures in the system
"""

from datetime import datetime
from typing import List, Optional

from .base import BaseModel

# ============ Base Models ============


class Event(BaseModel):
    """Event model - extracted from raw_records"""

    id: str
    title: str
    description: str
    keywords: List[str]
    timestamp: datetime
    created_at: Optional[datetime] = None


class Knowledge(BaseModel):
    """Knowledge model - original knowledge extracted from raw_records"""

    id: str
    title: str
    description: str
    keywords: List[str]
    created_at: datetime
    deleted: bool = False


class Todo(BaseModel):
    """Todo model - original todos extracted from raw_records"""

    id: str
    title: str
    description: str
    keywords: List[str]
    created_at: datetime
    completed: bool = False
    deleted: bool = False
    scheduled_date: Optional[str] = None  # YYYY-MM-DD format for calendar scheduling


# ============ Combined Models ============


class CombinedKnowledge(BaseModel):
    """Combined knowledge - merges related knowledge every 20 minutes"""

    id: str
    title: str
    description: str
    keywords: List[str]
    merged_from_ids: List[str]  # Source knowledge IDs for merging
    created_at: datetime
    deleted: bool = False


class CombinedTodo(BaseModel):
    """Combined todo - merges related todos every 20 minutes"""

    id: str
    title: str
    description: str
    keywords: List[str]
    merged_from_ids: List[str]  # Source todo IDs for merging
    created_at: datetime
    completed: bool = False
    deleted: bool = False
    scheduled_date: Optional[str] = None  # YYYY-MM-DD format for calendar scheduling


# ============ Activity and Diary Models ============


class Activity(BaseModel):
    """Activity model - aggregated from events"""

    id: str
    title: str
    description: str
    start_time: datetime
    end_time: datetime
    source_event_ids: List[str]  # List of referenced event IDs
    created_at: datetime
    deleted: bool = False


class Diary(BaseModel):
    """Diary model - summarized from activities"""

    id: str
    date: str  # YYYY-MM-DD format
    content: str  # Diary content (includes references to activities)
    source_activity_ids: List[str]  # List of referenced activity IDs
    created_at: datetime
    deleted: bool = False
