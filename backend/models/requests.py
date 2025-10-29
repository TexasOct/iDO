"""
Request models for PyTauri commands
PyTauri 命令的请求模型
"""

from typing import Optional
from pydantic import Field

from .base import BaseModel


# ============================================================================
# Demo Request Models
# ============================================================================

class Person(BaseModel):
    """A simple model representing a person.

    @property name - The name of the person.
    """
    name: str


# ============================================================================
# Perception Module Request Models
# ============================================================================

class GetRecordsRequest(BaseModel):
    """Request parameters for getting records.

    @property limit - Maximum number of records to return (1-1000).
    @property eventType - Optional event type filter.
    @property startTime - Optional start time filter (ISO format).
    @property endTime - Optional end time filter (ISO format).
    """
    limit: int = Field(default=100, ge=1, le=1000)
    event_type: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None


# ============================================================================
# Processing Module Request Models
# ============================================================================

class GetEventsRequest(BaseModel):
    """Request parameters for getting events.

    @property limit - Maximum number of events to return (1-500).
    @property eventType - Optional event type filter.
    @property startTime - Optional start time filter (ISO format).
    @property endTime - Optional end time filter (ISO format).
    """
    limit: int = Field(default=50, ge=1, le=500)
    event_type: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None


class GetActivitiesRequest(BaseModel):
    """Request parameters for getting activities.

    @property limit - Maximum number of activities to return (1-100).
    """
    limit: int = Field(default=20, ge=1, le=100)


class GetEventByIdRequest(BaseModel):
    """Request parameters for getting event by ID.

    @property eventId - The event ID.
    """
    event_id: str


class GetActivityByIdRequest(BaseModel):
    """Request parameters for getting activity by ID.

    @property activityId - The activity ID.
    """
    activity_id: str


class CleanupOldDataRequest(BaseModel):
    """Request parameters for cleaning up old data.

    @property days - Number of days to keep (1-365).
    """
    days: int = Field(default=30, ge=1, le=365)


class GetActivitiesIncrementalRequest(BaseModel):
    """Request parameters for incremental activity updates.

    @property version - The current version number from client (starts at 0).
    @property limit - Maximum number of new activities to return (1-100).
    """
    version: int = Field(default=0, ge=0)
    limit: int = Field(default=50, ge=1, le=100)


class GetActivityCountByDateRequest(BaseModel):
    """Request parameters for getting activity count by date.

    Returns the total activity count for each date (不分页，获取所有日期的总数).
    """
    pass  # No parameters needed


# ============================================================================
# Agent Module Request Models
# ============================================================================

class CreateTaskRequest(BaseModel):
    """Request parameters for creating a new agent task.

    @property agent - The agent type to use.
    @property planDescription - The task description/plan.
    """
    agent: str
    plan_description: str


class ExecuteTaskRequest(BaseModel):
    """Request parameters for executing a task.

    @property taskId - The task ID to execute.
    """
    task_id: str


class DeleteTaskRequest(BaseModel):
    """Request parameters for deleting a task.

    @property taskId - The task ID to delete.
    """
    task_id: str


class GetTasksRequest(BaseModel):
    """Request parameters for getting tasks.

    @property limit - Maximum number of tasks to return (1-100).
    @property status - Optional status filter.
    """
    limit: int = Field(default=50, ge=1, le=100)
    status: Optional[str] = None


class GetAvailableAgentsRequest(BaseModel):
    """Request parameters for getting available agents.

    No parameters needed.
    """
    pass


# ============================================================================
# Settings Module Request Models
# ============================================================================

class LLMSettingsModel(BaseModel):
    """LLM configuration model.

    @property provider - The LLM provider (e.g., 'openai', 'qwen').
    @property apiKey - The API key for the LLM provider.
    @property model - The model name to use.
    @property baseUrl - The base URL for the LLM API.
    """
    provider: str
    api_key: str
    model: str
    base_url: str


class UpdateSettingsRequest(BaseModel):
    """Request parameters for updating application settings.

    @property llm - LLM configuration to update (optional).
    @property databasePath - Path to the database file (optional).
    @property screenshotSavePath - Path to save screenshots (optional).
    """
    llm: Optional[LLMSettingsModel] = None
    database_path: Optional[str] = None
    screenshot_save_path: Optional[str] = None


class ImageOptimizationConfigRequest(BaseModel):
    """Request parameters for updating image optimization configuration.

    @property enabled - Whether image optimization is enabled.
    @property strategy - Optimization strategy ('phash', 'sampling', 'hybrid').
    @property phashThreshold - Perceptual hash similarity threshold (0.0-1.0).
    @property minInterval - Minimum time interval between images (seconds).
    @property maxImages - Maximum number of images per event.
    @property enableContentAnalysis - Enable content-based importance analysis.
    @property enableTextDetection - Enable text detection for OCR-capable images.
    """
    enabled: Optional[bool] = None
    strategy: Optional[str] = None
    phash_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    min_interval: Optional[float] = Field(default=None, ge=0.0)
    max_images: Optional[int] = Field(default=None, ge=1, le=50)
    enable_content_analysis: Optional[bool] = None
    enable_text_detection: Optional[bool] = None


class ImageCompressionConfigRequest(BaseModel):
    """Request parameters for updating image compression configuration.

    @property compressionLevel - Compression level ('ultra', 'aggressive', 'balanced', 'quality').
    @property enableRegionCropping - Whether to enable region-based cropping.
    @property cropThreshold - Crop threshold percentage (0-100).
    """
    compression_level: Optional[str] = Field(default=None, pattern='^(ultra|aggressive|balanced|quality)$')
    enable_region_cropping: Optional[bool] = None
    crop_threshold: Optional[int] = Field(default=None, ge=0, le=100)


# ============================================================================
# LLM Statistics Module Request Models
# ============================================================================

class RecordLLMUsageRequest(BaseModel):
    """Request parameters for recording LLM usage statistics.

    @property model - The LLM model name used.
    @property promptTokens - Number of prompt tokens consumed.
    @property completionTokens - Number of completion tokens consumed.
    @property totalTokens - Total number of tokens consumed.
    @property cost - Cost of the request (optional).
    @property requestType - Type of request (e.g., 'summarization', 'agent', 'chat').
    """
    model: str
    prompt_tokens: int = Field(default=0, ge=0)
    completion_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)
    cost: float = Field(default=0.0, ge=0.0)
    request_type: str
