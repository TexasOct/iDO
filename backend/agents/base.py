"""
Agent system base classes
Defines BaseAgent and registration mechanism
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from core.models import Task, AgentTask, AgentTaskStatus
from datetime import datetime
import uuid


class TaskResult:
    """Task execution result"""

    def __init__(
        self, success: bool, message: str = "", data: Optional[Dict[str, Any]] = None
    ):
        self.success = success
        self.message = message
        self.data = data or {}


class BaseAgent(ABC):
    """Agent base class"""

    def __init__(self, agent_type: str):
        self.agent_type = agent_type

    @abstractmethod
    def execute(self, task: AgentTask) -> TaskResult:
        """Execute task"""
        pass

    @abstractmethod
    def can_handle(self, task: AgentTask) -> bool:
        """Determine if this task can be handled"""
        pass

    def get_capabilities(self) -> Dict[str, Any]:
        """Get agent capabilities description"""
        return {
            "agent_type": self.agent_type,
            "description": "Base Agent",
            "capabilities": [],
        }


class AgentFactory:
    """Agent factory class"""

    def __init__(self):
        self._agents: Dict[str, type] = {}

    def register_agent(self, agent_type: str, agent_class: type):
        """Register agent class"""
        self._agents[agent_type] = agent_class

    def create_agent(self, agent_type: str) -> Optional[BaseAgent]:
        """Create agent instance"""
        if agent_type in self._agents:
            return self._agents[agent_type](agent_type)
        return None

    def get_available_agents(self) -> list:
        """Get list of available agent types"""
        return list(self._agents.keys())


# Global agent factory instance
agent_factory = AgentFactory()
