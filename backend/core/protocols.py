"""
Type protocols for database and repository operations

This module provides Protocol classes that define the interfaces for database operations.
Using Protocols allows for proper type checking without circular dependencies.
"""

from typing import Any, Dict, List, Optional, Protocol, Tuple

# ==================== Repository Protocols ====================


class SettingsRepositoryProtocol(Protocol):
    """Protocol for settings repository operations"""

    def get_all(self) -> Dict[str, Any]:
        """Get all settings with type conversion"""
        ...

    def set(
        self, key: str, value: str, setting_type: str, description: str | None = None
    ) -> int:
        """Set a setting value"""
        ...

    def get(self, key: str, default: str | None = None) -> str | None:
        """Get a setting value"""
        ...

    def delete(self, key: str) -> int:
        """Delete a setting"""
        ...


class ActivitiesRepositoryProtocol(Protocol):
    """Protocol for activities repository operations"""

    async def get_by_id(self, activity_id: str) -> Optional[Dict[str, Any]]:
        """Get activity by ID"""
        ...

    async def get_recent(
        self, limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get recent activities"""
        ...


class ConversationsRepositoryProtocol(Protocol):
    """Protocol for conversations repository operations"""

    def insert(
        self,
        conversation_id: str,
        title: str,
        related_activity_ids: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        model_id: Optional[str] = None,
    ) -> int:
        """Insert a new conversation"""
        ...

    def get_by_id(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation by ID"""
        ...

    def get_all(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get all conversations"""
        ...

    def update(
        self,
        conversation_id: str,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Update conversation"""
        ...

    def delete(self, conversation_id: str) -> int:
        """Delete conversation"""
        ...


class MessagesRepositoryProtocol(Protocol):
    """Protocol for messages repository operations"""

    def insert(
        self,
        message_id: str,
        conversation_id: str,
        role: str,
        content: str,
        timestamp: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        images: Optional[List[str]] = None,
    ) -> int:
        """Insert a new message"""
        ...

    def get_by_conversation(
        self, conversation_id: str, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get messages for a conversation"""
        ...


class EventsRepositoryProtocol(Protocol):
    """Protocol for events repository operations"""

    async def insert(self, event_data: Dict[str, Any]) -> int:
        """Insert a new event"""
        ...

    async def get_recent(
        self, limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get recent events"""
        ...


class TodosRepositoryProtocol(Protocol):
    """Protocol for todos repository operations"""

    async def insert(self, todo_data: Dict[str, Any]) -> int:
        """Insert a new todo"""
        ...

    async def get_all(
        self, limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get all todos"""
        ...


class KnowledgeRepositoryProtocol(Protocol):
    """Protocol for knowledge repository operations"""

    async def insert(self, knowledge_data: Dict[str, Any]) -> int:
        """Insert new knowledge"""
        ...

    async def search(
        self, query: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search knowledge"""
        ...


class LLMModelsRepositoryProtocol(Protocol):
    """Protocol for LLM models repository operations"""

    def get_active(self) -> Optional[Dict[str, Any]]:
        """Get active LLM model"""
        ...

    def get_all(self) -> List[Dict[str, Any]]:
        """Get all LLM models"""
        ...


# ==================== Database Manager Protocols ====================


class DatabaseManagerProtocol(Protocol):
    """Protocol for the unified database manager with all repositories"""

    settings: SettingsRepositoryProtocol
    activities: ActivitiesRepositoryProtocol
    conversations: ConversationsRepositoryProtocol
    messages: MessagesRepositoryProtocol
    events: EventsRepositoryProtocol
    todos: TodosRepositoryProtocol
    knowledge: KnowledgeRepositoryProtocol
    models: LLMModelsRepositoryProtocol

    def execute_query(
        self, query: str, params: Optional[Tuple[Any, ...]] = None
    ) -> List[Dict[str, Any]]:
        """Execute a raw SQL query (legacy compatibility)"""
        ...

    def get_connection(self) -> Any:
        """Get database connection (legacy compatibility)"""
        ...


# ==================== Specialized Database Protocols ====================


class ChatDatabaseProtocol(Protocol):
    """Protocol for database operations used in ChatService"""

    activities: ActivitiesRepositoryProtocol
    conversations: ConversationsRepositoryProtocol
    messages: MessagesRepositoryProtocol


class DashboardDatabaseProtocol(Protocol):
    """Protocol for database operations used in DashboardManager"""

    def execute_query(
        self, query: str, params: Optional[Tuple[Any, ...]] = None
    ) -> List[Dict[str, Any]]:
        """Execute a raw SQL query"""
        ...

    def get_connection(self) -> Any:
        """Get database connection"""
        ...


# ==================== Other Protocols ====================


class PerceptionManagerProtocol(Protocol):
    """Protocol for perception manager operations"""

    def start(self) -> None:
        """Start perception"""
        ...

    def stop(self) -> None:
        """Stop perception"""
        ...

    def is_running(self) -> bool:
        """Check if perception is running"""
        ...
