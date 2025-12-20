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


# Insights Module Response Models
class DiaryData(BaseModel):
    """Diary data"""

    id: str
    date: str
    content: str
    source_activity_ids: List[str]
    created_at: str


class GenerateDiaryResponse(OperationResponse):
    """Response after generating a diary"""

    data: Optional[DiaryData] = None
    timestamp: str = ""


class DiaryListData(BaseModel):
    """Diary list data"""

    diaries: List[DiaryData]
    count: int


class GetDiaryListResponse(OperationResponse):
    """Response containing diary list"""

    data: Optional[DiaryListData] = None
    timestamp: str = ""


class DeleteDiaryResponse(OperationResponse):
    """Response after deleting a diary"""

    timestamp: str = ""


# System Settings Response Models
class SettingsInfoData(BaseModel):
    """Settings info data structure"""

    settings: Dict[str, Any]
    database: Dict[str, str]
    screenshot: Dict[str, str]
    language: str
    image: Dict[str, Any]


class GetSettingsInfoResponse(TimedOperationResponse):
    """Response for get_settings_info handler"""

    data: Optional[SettingsInfoData] = None


class ImageOptimizationConfigData(BaseModel):
    """Image optimization configuration data"""

    enabled: bool = True
    strategy: str = "phash"
    phash_threshold: int = 10
    min_interval: float = 0.5
    max_images: int = 10
    enable_content_analysis: bool = True
    enable_text_detection: bool = True


class GetImageOptimizationConfigResponse(TimedOperationResponse):
    """Response for get_image_optimization_config handler"""

    data: Optional[ImageOptimizationConfigData] = None


class UpdateImageOptimizationConfigResponseV2(TimedOperationResponse):
    """Response for update_image_optimization_config handler"""

    data: Optional[ImageOptimizationConfigData] = None


class ImageCompressionConfigData(BaseModel):
    """Image compression configuration data"""

    compression_level: int = 85
    enable_region_cropping: bool = False
    crop_threshold: float = 0.8


class GetImageCompressionConfigResponse(TimedOperationResponse):
    """Response for get_image_compression_config handler"""

    data: Optional[ImageCompressionConfigData] = None


class UpdateImageCompressionConfigResponseV2(TimedOperationResponse):
    """Response for update_image_compression_config handler"""

    data: Optional[ImageCompressionConfigData] = None


class ImageCompressionStatsData(BaseModel):
    """Image compression statistics data"""

    total_processed: int = 0
    total_saved_bytes: int = 0
    average_compression_ratio: float = 0.0


class GetImageCompressionStatsResponse(TimedOperationResponse):
    """Response for get_image_compression_stats handler"""

    data: Optional[ImageCompressionStatsData] = None


class InitialSetupData(BaseModel):
    """Initial setup check data"""

    has_models: bool
    has_active_model: bool
    has_completed_setup: bool
    needs_setup: bool
    model_count: int


class CheckInitialSetupResponse(TimedOperationResponse):
    """Response for check_initial_setup handler"""

    data: Optional[InitialSetupData] = None


class CompleteInitialSetupResponse(TimedOperationResponse):
    """Response for complete_initial_setup handler"""

    pass


