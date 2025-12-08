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
    scheduled_time: Optional[str] = None  # HH:MM format for start time
    scheduled_end_time: Optional[str] = None  # HH:MM format for end time
    recurrence_rule: Optional[dict] = None  # Recurrence rule config


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
    scheduled_time: Optional[str] = None  # HH:MM format for start time
    scheduled_end_time: Optional[str] = None  # HH:MM format for end time
    recurrence_rule: Optional[dict] = None  # Recurrence rule config


# ============ Activity and Diary Models ============


class Activity(BaseModel):
    """Activity model - aggregated from events (LEGACY - kept for backward compatibility)"""

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


# ============ Three-Layer Architecture Models ============


class Action(BaseModel):
    """Action model - fine-grained operations extracted from screenshots (formerly Event)"""

    id: str
    title: str
    description: str
    keywords: List[str]
    timestamp: datetime
    aggregated_into_event_id: Optional[str] = None  # Track aggregation status
    created_at: Optional[datetime] = None


class EventV2(BaseModel):
    """Event model - medium-grained activity segments (formerly Activity)"""

    id: str
    title: str
    description: str
    start_time: datetime
    end_time: datetime
    source_action_ids: List[str]  # References to Actions
    aggregated_into_activity_id: Optional[str] = None  # Track aggregation status
    version: int = 1
    created_at: datetime
    deleted: bool = False


class ActivityV2(BaseModel):
    """Activity model - coarse-grained work sessions (NEW top layer)"""

    id: str
    title: str
    description: str
    start_time: datetime
    end_time: datetime
    source_event_ids: List[str]  # References to EventV2
    session_duration_minutes: Optional[int] = None
    topic_tags: Optional[List[str]] = None
    user_merged_from_ids: Optional[List[str]] = None  # User manual merge tracking
    user_split_into_ids: Optional[List[str]] = None  # User manual split tracking
    created_at: datetime
    updated_at: datetime
    deleted: bool = False


class SessionPreference(BaseModel):
    """Session preference model - stores learned user preferences for session aggregation"""

    id: str
    preference_type: str  # 'merge_pattern' | 'split_pattern' | 'time_threshold'
    pattern_description: Optional[str] = None
    confidence_score: float = 0.5
    times_observed: int = 1
    last_observed: datetime
    created_at: datetime
