"""
Response models for API handlers
Provides strongly typed response models for better type safety and auto-generation
"""

from typing import Any, Dict, List, Optional

from models.base import BaseModel, OperationResponse, TimedOperationResponse


# System responses
class SystemStatusData(BaseModel):
    """System status data"""

    is_running: bool
    status: str
    last_error: Optional[str] = None
    active_model: Optional[Dict[str, Any]] = None  # Can be a dict or None


class SystemResponse(BaseModel):
    """Common system operation response"""

    success: bool
    message: str = ""  # Make message optional with default
    data: Optional[Any] = None  # Allow Any for flexible data
    timestamp: str


class DatabasePathData(BaseModel):
    """Database path data"""

    path: str


class DatabasePathResponse(BaseModel):
    """Database path response"""

    success: bool
    data: DatabasePathData
    timestamp: str


class SettingsData(BaseModel):
    """Settings data"""

    llm_enabled: bool
    screenshot_quality: int
    screenshot_interval: float
    perception_enabled: bool
    keyboard_enabled: bool
    mouse_enabled: bool
    processing_interval: int


class SettingsInfoResponse(BaseModel):
    """Settings info response"""

    success: bool
    data: SettingsData
    timestamp: str


class UpdateSettingsResponse(BaseModel):
    """Update settings response"""

    success: bool
    message: str
    timestamp: str


# Activity responses
class ActivityCountData(BaseModel):
    """Activity count data"""

    date_count_map: Dict[str, int]
    total_dates: int
    total_activities: int


class ActivityCountResponse(BaseModel):
    """Activity count by date response"""

    success: bool
    data: ActivityCountData
    error: str = ""


class IncrementalActivitiesData(BaseModel):
    """Incremental activities data"""

    activities: List[Dict[str, Any]]
    count: int
    max_version: int


class IncrementalActivitiesResponse(BaseModel):
    """Incremental activities response"""

    success: bool
    data: IncrementalActivitiesData


# Generic data response (for handlers returning arbitrary data)
class DataResponse(TimedOperationResponse):
    """Generic response with data field and timestamp"""

    pass  # Inherits: success, message, error, data, timestamp


# Three-Layer Architecture Response Models (Activities → Events → Actions)
class EventResponse(BaseModel):
    """Event response data for three-layer architecture"""

    id: str
    title: str
    description: str
    start_time: str
    end_time: str
    source_action_ids: List[str]
    created_at: str


class GetEventsByActivityResponse(OperationResponse):
    """Response containing events for a specific activity"""

    events: List[EventResponse]


class ActionResponse(BaseModel):
    """Action response data for three-layer architecture"""

    id: str
    title: str
    description: str
    keywords: List[str]
    timestamp: str
    screenshots: List[str]
    created_at: str


class GetActionsByEventResponse(OperationResponse):
    """Response containing actions for a specific event"""

    actions: List[ActionResponse]


class MergeActivitiesResponse(OperationResponse):
    """Response after merging multiple activities"""

    merged_activity_id: str = ""


class SplitActivityResponse(OperationResponse):
    """Response after splitting an activity into multiple activities"""

    new_activity_ids: List[str] = []


# Image Management Response Models
class ImageStatsResponse(OperationResponse):
    """Response containing image cache statistics"""

    stats: Optional[Dict[str, Any]] = None


class CachedImagesResponse(OperationResponse):
    """Response containing cached images in base64 format"""

    images: Dict[str, str]
    found_count: int
    requested_count: int


class CleanupImagesResponse(OperationResponse):
    """Response after cleaning up old images"""

    cleaned_count: int = 0


class ClearMemoryCacheResponse(OperationResponse):
    """Response after clearing memory cache"""

    cleared_count: int = 0


class ImageOptimizationConfigResponse(OperationResponse):
    """Response containing image optimization configuration"""

    config: Optional[Dict[str, Any]] = None


class ImageOptimizationStatsResponse(OperationResponse):
    """Response containing image optimization statistics"""

    stats: Optional[Dict[str, Any]] = None
    config: Optional[Dict[str, Any]] = None


class UpdateImageOptimizationConfigResponse(OperationResponse):
    """Response after updating image optimization configuration"""

    config: Optional[Dict[str, Any]] = None


class ReadImageFileResponse(OperationResponse):
    """Response containing image file data as base64"""

    data_url: str = ""


