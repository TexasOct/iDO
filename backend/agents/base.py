"""
Agent 系统基础类
定义 BaseAgent 和注册机制
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from core.models import Task


class TaskResult:
    """任务执行结果"""
    
    def __init__(self, success: bool, message: str = "", data: Optional[Dict[str, Any]] = None):
        self.success = success
        self.message = message
        self.data = data or {}


class BaseAgent(ABC):
    """Agent 基类"""
    
    def __init__(self, agent_type: str):
        self.agent_type = agent_type
    
    @abstractmethod
    def execute(self, task: Task) -> TaskResult:
        """执行任务"""
        pass
    
    @abstractmethod
    def can_handle(self, task: Task) -> bool:
        """判断是否能处理该任务"""
        pass
    
    def get_capabilities(self) -> Dict[str, Any]:
        """获取 Agent 能力描述"""
        return {
            "agent_type": self.agent_type,
            "description": "基础 Agent",
            "capabilities": []
        }


class AgentFactory:
    """Agent 工厂类"""
    
    def __init__(self):
        self._agents: Dict[str, type] = {}
    
    def register_agent(self, agent_type: str, agent_class: type):
        """注册 Agent 类"""
        self._agents[agent_type] = agent_class
    
    def create_agent(self, agent_type: str) -> Optional[BaseAgent]:
        """创建 Agent 实例"""
        if agent_type in self._agents:
            return self._agents[agent_type](agent_type)
        return None
    
    def get_available_agents(self) -> list:
        """获取可用的 Agent 类型列表"""
        return list(self._agents.keys())


# 全局 Agent 工厂实例
agent_factory = AgentFactory()
