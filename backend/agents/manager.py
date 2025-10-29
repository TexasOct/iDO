"""
Agent任务管理器
负责管理Agent任务的创建、执行和状态更新
"""

import asyncio
import json
from typing import Dict, List, Optional
from datetime import datetime
from core.models import AgentTask, AgentTaskStatus, AgentConfig
from core.logger import get_logger
from .base import AgentFactory, TaskResult
from .simple_agent import SimpleAgent, WritingAgent, ResearchAgent, AnalysisAgent, AVAILABLE_AGENTS

logger = get_logger(__name__)


class AgentTaskManager:
    """Agent任务管理器"""
    
    def __init__(self):
        self.tasks: Dict[str, AgentTask] = {}
        self.factory = AgentFactory()
        self._register_agents()
        self._running_tasks: Dict[str, asyncio.Task] = {}
    
    def _register_agents(self):
        """注册所有可用的Agent"""
        self.factory.register_agent("SimpleAgent", SimpleAgent)
        self.factory.register_agent("WritingAgent", WritingAgent)
        self.factory.register_agent("ResearchAgent", ResearchAgent)
        self.factory.register_agent("AnalysisAgent", AnalysisAgent)
        logger.info("Agent注册完成")
    
    def create_task(self, agent: str, plan_description: str) -> AgentTask:
        """创建新的Agent任务"""
        task_id = f"task_{int(datetime.now().timestamp() * 1000)}"
        
        task = AgentTask(
            id=task_id,
            agent=agent,
            plan_description=plan_description,
            status=AgentTaskStatus.TODO,
            created_at=datetime.now()
        )
        
        self.tasks[task_id] = task
        logger.info(f"创建任务: {task_id} - {agent}")
        
        return task
    
    def get_task(self, task_id: str) -> Optional[AgentTask]:
        """获取任务"""
        return self.tasks.get(task_id)
    
    def get_tasks(self, limit: int = 50, status: Optional[str] = None) -> List[AgentTask]:
        """获取任务列表"""
        tasks = list(self.tasks.values())
        
        if status:
            tasks = [task for task in tasks if task.status.value == status]
        
        # 按创建时间倒序排列
        tasks.sort(key=lambda x: x.created_at, reverse=True)
        
        return tasks[:limit]
    
    def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        if task_id in self.tasks:
            # 如果任务正在运行，先停止
            if task_id in self._running_tasks:
                self._running_tasks[task_id].cancel()
                del self._running_tasks[task_id]
            
            del self.tasks[task_id]
            logger.info(f"删除任务: {task_id}")
            return True
        return False
    
    async def execute_task(self, task_id: str) -> bool:
        """执行任务"""
        task = self.get_task(task_id)
        if not task:
            logger.error(f"任务不存在: {task_id}")
            return False
        
        if task.status != AgentTaskStatus.TODO:
            logger.warning(f"任务状态不是TODO，无法执行: {task_id} - {task.status}")
            return False
        
        # 创建Agent实例
        agent_instance = self.factory.create_agent(task.agent)
        if not agent_instance:
            logger.error(f"无法创建Agent: {task.agent}")
            self._update_task_status(task_id, AgentTaskStatus.FAILED, error="无法创建Agent实例")
            return False
        
        # 检查Agent是否能处理该任务
        if not agent_instance.can_handle(task):
            logger.warning(f"Agent无法处理该任务: {task.agent} - {task_id}")
            self._update_task_status(task_id, AgentTaskStatus.FAILED, error="Agent无法处理该任务")
            return False
        
        # 更新任务状态为处理中
        self._update_task_status(task_id, AgentTaskStatus.PROCESSING, started_at=datetime.now())
        
        # 创建异步任务
        async_task = asyncio.create_task(self._run_task(task, agent_instance))
        self._running_tasks[task_id] = async_task
        
        logger.info(f"开始执行任务: {task_id}")
        return True
    
    async def _run_task(self, task: AgentTask, agent_instance):
        """运行任务"""
        try:
            # 执行任务
            result = await agent_instance.execute(task)
            
            if result.success:
                # 任务成功完成
                completed_at = datetime.now()
                duration = int((completed_at - task.started_at).total_seconds()) if task.started_at else 0
                
                self._update_task_status(
                    task.id, 
                    AgentTaskStatus.DONE,
                    completed_at=completed_at,
                    duration=duration,
                    result=result.data.get("result")
                )
                logger.info(f"任务执行成功: {task.id}")
            else:
                # 任务执行失败
                self._update_task_status(
                    task.id,
                    AgentTaskStatus.FAILED,
                    error=result.message
                )
                logger.error(f"任务执行失败: {task.id} - {result.message}")
                
        except asyncio.CancelledError:
            # 任务被取消
            self._update_task_status(task.id, AgentTaskStatus.FAILED, error="任务被取消")
            logger.info(f"任务被取消: {task.id}")
        except Exception as e:
            # 任务执行异常
            self._update_task_status(task.id, AgentTaskStatus.FAILED, error=str(e))
            logger.error(f"任务执行异常: {task.id} - {str(e)}")
        finally:
            # 清理运行中的任务记录
            if task.id in self._running_tasks:
                del self._running_tasks[task.id]
    
    def _update_task_status(self, task_id: str, status: AgentTaskStatus, **kwargs):
        """更新任务状态"""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.status = status

            if "started_at" in kwargs:
                task.started_at = kwargs["started_at"]
            if "completed_at" in kwargs:
                task.completed_at = kwargs["completed_at"]
            if "duration" in kwargs:
                task.duration = kwargs["duration"]
            if "result" in kwargs:
                task.result = kwargs["result"]
            if "error" in kwargs:
                task.error = kwargs["error"]

            logger.debug(f"更新任务状态: {task_id} - {status.value}")

            # 发送任务更新事件到前端
            try:
                from core.events import emit_agent_task_update
                emit_agent_task_update(
                    task_id=task_id,
                    status=status.value,
                    progress=kwargs.get("duration"),
                    result=kwargs.get("result"),
                    error=kwargs.get("error")
                )
            except Exception as e:
                logger.error(f"发送任务更新事件失败: {str(e)}")
    
    def get_available_agents(self) -> List[AgentConfig]:
        """获取可用的Agent列表"""
        return AVAILABLE_AGENTS.copy()
    
    def stop_task(self, task_id: str) -> bool:
        """停止任务"""
        if task_id in self._running_tasks:
            self._running_tasks[task_id].cancel()
            del self._running_tasks[task_id]
            self._update_task_status(task_id, AgentTaskStatus.FAILED, error="任务被手动停止")
            logger.info(f"停止任务: {task_id}")
            return True
        return False


# 全局任务管理器实例
task_manager = AgentTaskManager()
