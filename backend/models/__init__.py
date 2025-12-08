"""
Models for PyTauri command communication
Data models for PyTauri command communication
"""

from .base import (
    BaseModel,
    OperationDataResponse,
    OperationResponse,
    TimedOperationResponse,
)
from .requests import (
    CleanupOldDataRequest,
    DeleteActivitiesByDateRequest,
    DeleteActivityRequest,
    DeleteDiariesByDateRequest,
    DeleteEventRequest,
    DeleteKnowledgeByDateRequest,
    DeleteTodosByDateRequest,
    GetActivitiesIncrementalRequest,
    GetActivitiesRequest,
    GetActivityByIdRequest,
    GetActivityCountByDateRequest,
    GetEventByIdRequest,
    # Processing
    GetEventsRequest,
    # Perception
    GetRecordsRequest,
    # Demo
    Person,
)
from .responses import (
    ActivityCountData,
    ActivityCountResponse,
    DatabasePathData,
    DatabasePathResponse,
    DataResponse,
    IncrementalActivitiesData,
    IncrementalActivitiesResponse,
    SettingsData,
    SettingsInfoResponse,
    SystemResponse,
    SystemStatusData,
    UpdateSettingsResponse,
)

__all__ = [
    # Base
    "BaseModel",
    "OperationResponse",
    "OperationDataResponse",
    "TimedOperationResponse",
    # Responses
    "SystemResponse",
    "SystemStatusData",
    "DatabasePathResponse",
    "DatabasePathData",
    "SettingsInfoResponse",
    "SettingsData",
    "UpdateSettingsResponse",
    "ActivityCountResponse",
    "ActivityCountData",
    "IncrementalActivitiesResponse",
    "IncrementalActivitiesData",
    "DataResponse",
    # Demo
    "Person",
    # Perception
    "GetRecordsRequest",
    # Processing
    "GetEventsRequest",
    "GetActivitiesRequest",
    "GetEventByIdRequest",
    "GetActivityByIdRequest",
    "DeleteActivityRequest",
    "DeleteEventRequest",
    "DeleteActivitiesByDateRequest",
    "DeleteKnowledgeByDateRequest",
    "DeleteTodosByDateRequest",
    "DeleteDiariesByDateRequest",
    "CleanupOldDataRequest",
    "GetActivitiesIncrementalRequest",
    "GetActivityCountByDateRequest",
]
