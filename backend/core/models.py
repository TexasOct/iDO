"""
Data model definitions
Contains core data models like RawRecord, Event, Activity, Task
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class RecordType(Enum):
    """Record type enumeration"""

    KEYBOARD_RECORD = "keyboard_record"
    MOUSE_RECORD = "mouse_record"
    SCREENSHOT_RECORD = "screenshot_record"


class TaskStatus(Enum):
    """Task status enumeration"""

    TODO = "todo"
    DOING = "doing"
    DONE = "done"
    CANCELLED = "cancelled"


@dataclass
class RawRecord:
    """Raw record data model"""

    timestamp: datetime
    type: RecordType
    data: Dict[str, Any]
    screenshot_path: Optional[str] = None  # Screenshot file path

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "type": self.type.value,
            "data": self.data,
            "screenshot_path": self.screenshot_path,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RawRecord":
        """Create instance from dictionary"""
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            type=RecordType(data["type"]),
            data=data["data"],
            screenshot_path=data.get("screenshot_path"),
        )


@dataclass
class Event:
    """Event data model"""

    id: str
    start_time: datetime
    end_time: datetime
    summary: str
    source_data: List[
        RawRecord
    ]  # All filtered records within 10 seconds arranged in chronological order

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "summary": self.summary,
            "source_data": [record.to_dict() for record in self.source_data],
        }


@dataclass
class Activity:
    """Activity data model"""

    id: str
    title: str
    description: str
    start_time: datetime
    end_time: datetime
    source_events: List[Event]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "source_events": [event.to_dict() for event in self.source_events],
        }


@dataclass
class Task:
    """Task data model"""

    id: str
    title: str
    description: str
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    agent_type: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "agent_type": self.agent_type,
            "parameters": self.parameters or {},
        }


class AgentTaskStatus(Enum):
    """Agent task status enumeration"""

    PENDING = "pending"  # Pending in the inbox, not scheduled yet
    TODO = "todo"  # Scheduled for a specific date
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"


@dataclass
class AgentTask:
    """Agent task data model"""

    id: str
    agent: str
    plan_description: str
    status: AgentTaskStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration: Optional[int] = None  # Runtime (seconds)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    scheduled_date: Optional[str] = (
        None  # Scheduled date in YYYY-MM-DD format, None for pending tasks
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "agent": self.agent,
            "planDescription": self.plan_description,
            "status": self.status.value,
            "createdAt": int(self.created_at.timestamp() * 1000),
            "startedAt": int(self.started_at.timestamp() * 1000)
            if self.started_at
            else None,
            "completedAt": int(self.completed_at.timestamp() * 1000)
            if self.completed_at
            else None,
            "duration": self.duration,
            "result": self.result,
            "error": self.error,
            "scheduledDate": self.scheduled_date,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentTask":
        """Create instance from dictionary"""
        return cls(
            id=data["id"],
            agent=data["agent"],
            plan_description=data["planDescription"],
            status=AgentTaskStatus(data["status"]),
            created_at=datetime.fromtimestamp(data["createdAt"] / 1000),
            started_at=datetime.fromtimestamp(data["startedAt"] / 1000)
            if data.get("startedAt")
            else None,
            completed_at=datetime.fromtimestamp(data["completedAt"] / 1000)
            if data.get("completedAt")
            else None,
            duration=data.get("duration"),
            result=data.get("result"),
            error=data.get("error"),
            scheduled_date=data.get("scheduledDate"),
        )


@dataclass
class AgentConfig:
    """Agent configuration data model"""

    name: str
    description: str
    icon: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {"name": self.name, "description": self.description, "icon": self.icon}


class MessageRole(Enum):
    """Message role enumeration"""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass
class Message:
    """Chat message data model"""

    id: str
    conversation_id: str
    role: MessageRole
    content: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None
    images: Optional[List[str]] = None  # Base64 encoded images

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "conversationId": self.conversation_id,
            "role": self.role.value,
            "content": self.content,
            "timestamp": int(self.timestamp.timestamp() * 1000),
            "metadata": self.metadata or {},
            "images": self.images or [],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """Create instance from dictionary"""
        return cls(
            id=data["id"],
            conversation_id=data["conversationId"],
            role=MessageRole(data["role"]),
            content=data["content"],
            timestamp=datetime.fromtimestamp(data["timestamp"] / 1000),
            metadata=data.get("metadata"),
            images=data.get("images"),
        )


@dataclass
class Conversation:
    """Conversation data model"""

    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    related_activity_ids: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    model_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "title": self.title,
            "createdAt": int(self.created_at.timestamp() * 1000),
            "updatedAt": int(self.updated_at.timestamp() * 1000),
            "relatedActivityIds": self.related_activity_ids or [],
            "metadata": self.metadata or {},
            "modelId": self.model_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Conversation":
        """Create instance from dictionary"""
        return cls(
            id=data["id"],
            title=data["title"],
            created_at=datetime.fromtimestamp(data["createdAt"] / 1000),
            updated_at=datetime.fromtimestamp(data["updatedAt"] / 1000),
            related_activity_ids=data.get("relatedActivityIds"),
            metadata=data.get("metadata"),
            model_id=data.get("modelId"),
        )
