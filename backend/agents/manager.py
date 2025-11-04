"""
Agent task manager
Responsible for managing Agent task creation, execution and status updates
"""

import asyncio
import json
from typing import Dict, List, Optional
from datetime import datetime
from core.models import AgentTask, AgentTaskStatus, AgentConfig
from core.logger import get_logger
from .base import AgentFactory, TaskResult
from .simple_agent import (
    SimpleAgent,
    WritingAgent,
    ResearchAgent,
    AnalysisAgent,
    AVAILABLE_AGENTS,
)

logger = get_logger(__name__)


class AgentTaskManager:
    """Agent task manager"""

    def __init__(self):
        self.tasks: Dict[str, AgentTask] = {}
        self.factory = AgentFactory()
        self._register_agents()
        self._running_tasks: Dict[str, asyncio.Task] = {}

    def _register_agents(self):
        """Register all available agents"""
        self.factory.register_agent("SimpleAgent", SimpleAgent)
        self.factory.register_agent("WritingAgent", WritingAgent)
        self.factory.register_agent("ResearchAgent", ResearchAgent)
        self.factory.register_agent("AnalysisAgent", AnalysisAgent)
        logger.info("Agent registration completed")

    def create_task(self, agent: str, plan_description: str) -> AgentTask:
        """Create new agent task"""
        task_id = f"task_{int(datetime.now().timestamp() * 1000)}"

        task = AgentTask(
            id=task_id,
            agent=agent,
            plan_description=plan_description,
            status=AgentTaskStatus.TODO,
            created_at=datetime.now(),
        )

        self.tasks[task_id] = task
        logger.info(f"Created task: {task_id} - {agent}")

        return task

    def get_task(self, task_id: str) -> Optional[AgentTask]:
        """Get task"""
        return self.tasks.get(task_id)

    def get_tasks(
        self, limit: int = 50, status: Optional[str] = None
    ) -> List[AgentTask]:
        """Get task list"""
        tasks = list(self.tasks.values())

        if status:
            tasks = [task for task in tasks if task.status.value == status]

        # Sort by creation time in descending order
        tasks.sort(key=lambda x: x.created_at, reverse=True)

        return tasks[:limit]

    def delete_task(self, task_id: str) -> bool:
        """Delete task"""
        if task_id in self.tasks:
            # If task is running, stop it first
            if task_id in self._running_tasks:
                self._running_tasks[task_id].cancel()
                del self._running_tasks[task_id]

            del self.tasks[task_id]
            logger.info(f"Deleted task: {task_id}")
            return True
        return False

    async def execute_task(self, task_id: str) -> bool:
        """Execute task"""
        task = self.get_task(task_id)
        if not task:
            logger.error(f"Task does not exist: {task_id}")
            return False

        if task.status != AgentTaskStatus.TODO:
            logger.warning(
                f"Task status is not TODO, cannot execute: {task_id} - {task.status}"
            )
            return False

        # Create agent instance
        agent_instance = self.factory.create_agent(task.agent)
        if not agent_instance:
            logger.error(f"Cannot create agent: {task.agent}")
            self._update_task_status(
                task_id, AgentTaskStatus.FAILED, error="Cannot create agent instance"
            )
            return False

        # Check if agent can handle this task
        if not agent_instance.can_handle(task):
            logger.warning(f"Agent cannot handle this task: {task.agent} - {task_id}")
            self._update_task_status(
                task_id, AgentTaskStatus.FAILED, error="Agent cannot handle this task"
            )
            return False

        # Update task status to processing
        self._update_task_status(
            task_id, AgentTaskStatus.PROCESSING, started_at=datetime.now()
        )

        # Create async task
        async_task = asyncio.create_task(self._run_task(task, agent_instance))
        self._running_tasks[task_id] = async_task

        logger.info(f"Starting task execution: {task_id}")
        return True

    async def _run_task(self, task: AgentTask, agent_instance):
        """Run task"""
        try:
            # Execute task
            result = await agent_instance.execute(task)

            if result.success:
                # Task completed successfully
                completed_at = datetime.now()
                duration = (
                    int((completed_at - task.started_at).total_seconds())
                    if task.started_at
                    else 0
                )

                self._update_task_status(
                    task.id,
                    AgentTaskStatus.DONE,
                    completed_at=completed_at,
                    duration=duration,
                    result=result.data.get("result"),
                )
                logger.info(f"Task executed successfully: {task.id}")
            else:
                # Task execution failed
                self._update_task_status(
                    task.id, AgentTaskStatus.FAILED, error=result.message
                )
                logger.error(f"Task execution failed: {task.id} - {result.message}")

        except asyncio.CancelledError:
            # Task was cancelled
            self._update_task_status(
                task.id, AgentTaskStatus.FAILED, error="Task was cancelled"
            )
            logger.info(f"Task was cancelled: {task.id}")
        except Exception as e:
            # Task execution exception
            self._update_task_status(task.id, AgentTaskStatus.FAILED, error=str(e))
            logger.error(f"Task execution exception: {task.id} - {str(e)}")
        finally:
            # Clean up running task record
            if task.id in self._running_tasks:
                del self._running_tasks[task.id]

    def _update_task_status(self, task_id: str, status: AgentTaskStatus, **kwargs):
        """Update task status"""
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

            logger.debug(f"Updated task status: {task_id} - {status.value}")

            # Send task update event to frontend
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
                logger.error(f"Failed to send task update event: {str(e)}")

    def get_available_agents(self) -> List[AgentConfig]:
        """Get available agent list"""
        return AVAILABLE_AGENTS.copy()

    def stop_task(self, task_id: str) -> bool:
        """Stop task"""
        if task_id in self._running_tasks:
            self._running_tasks[task_id].cancel()
            del self._running_tasks[task_id]
            self._update_task_status(
                task_id, AgentTaskStatus.FAILED, error="Task was manually stopped"
            )
            logger.info(f"Stopped task: {task_id}")
            return True
        return False


# Global task manager instance
task_manager = AgentTaskManager()
