"""
Agent-related API handlers
"""

from typing import Dict, Any, List
from core.logger import get_logger
from models.requests import (
    CreateTaskRequest,
    ExecuteTaskRequest,
    DeleteTaskRequest,
    GetTasksRequest,
    GetAvailableAgentsRequest,
)
from agents.manager import task_manager
from . import api_handler

logger = get_logger(__name__)


@api_handler(
    body=CreateTaskRequest,
    method="POST",
    path="/agents/create-task",
    tags=["agents"],
    summary="Create new agent task",
    description="Create a new agent task with specified agent type and task description",
)
async def create_task(body: CreateTaskRequest) -> Dict[str, Any]:
    """Create new agent task"""
    try:
        logger.info(f"Create task request: {body.agent} - {body.plan_description}")

        task = task_manager.create_task(body.agent, body.plan_description)

        return {
            "success": True,
            "data": task.to_dict(),
            "message": "Task created successfully",
        }
    except Exception as e:
        logger.error(f"Failed to create task: {str(e)}")
        return {"success": False, "error": str(e), "message": "Task creation failed"}


@api_handler(
    body=ExecuteTaskRequest,
    method="POST",
    path="/agents/execute-task",
    tags=["agents"],
    summary="Execute agent task",
    description="Execute the specified agent task",
)
async def execute_task(body: ExecuteTaskRequest) -> Dict[str, Any]:
    """Execute agent task"""
    try:
        logger.info(f"Execute task request: {body.task_id}")

        success = await task_manager.execute_task(body.task_id)

        if success:
            return {"success": True, "message": "Task execution started"}
        else:
            return {
                "success": False,
                "error": "Task execution failed",
                "message": "Unable to execute task",
            }
    except Exception as e:
        logger.error(f"Task execution failed: {str(e)}")
        return {"success": False, "error": str(e), "message": "Task execution failed"}


@api_handler(
    body=DeleteTaskRequest,
    method="POST",
    path="/agents/delete-task",
    tags=["agents"],
    summary="Delete agent task",
    description="Delete the specified agent task",
)
async def delete_task(body: DeleteTaskRequest) -> Dict[str, Any]:
    """Delete agent task"""
    try:
        logger.info(f"Delete task request: {body.task_id}")

        success = task_manager.delete_task(body.task_id)

        if success:
            return {"success": True, "message": "Task deleted successfully"}
        else:
            return {
                "success": False,
                "error": "Task does not exist",
                "message": "Unable to delete task",
            }
    except Exception as e:
        logger.error(f"Failed to delete task: {str(e)}")
        return {"success": False, "error": str(e), "message": "Task deletion failed"}


@api_handler(
    body=GetTasksRequest,
    method="POST",
    path="/agents/get-tasks",
    tags=["agents"],
    summary="Get agent task list",
    description="Get agent task list with status filtering support",
)
async def get_tasks(body: GetTasksRequest) -> Dict[str, Any]:
    """Get agent task list"""
    try:
        logger.info(f"Get task list request: limit={body.limit}, status={body.status}")

        tasks = task_manager.get_tasks(body.limit, body.status)
        tasks_data = [task.to_dict() for task in tasks]

        return {
            "success": True,
            "data": tasks_data,
            "message": f"Retrieved {len(tasks_data)} tasks",
        }
    except Exception as e:
        logger.error(f"Failed to get task list: {str(e)}")
        return {"success": False, "error": str(e), "message": "Failed to get task list"}


@api_handler(
    body=GetAvailableAgentsRequest,
    method="POST",
    path="/agents/get-available-agents",
    tags=["agents"],
    summary="Get available agent list",
    description="Get all available agent types and configurations",
)
async def get_available_agents(body: GetAvailableAgentsRequest) -> Dict[str, Any]:
    """Get available agent list"""
    try:
        logger.info("Get available agent list request")

        agents = task_manager.get_available_agents()
        agents_data = [agent.to_dict() for agent in agents]

        return {
            "success": True,
            "data": agents_data,
            "message": f"Retrieved {len(agents_data)} available agents",
        }
    except Exception as e:
        logger.error(f"Failed to get available agent list: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to get available agent list",
        }


@api_handler(
    body=ExecuteTaskRequest,
    method="POST",
    path="/agents/get-task-status",
    tags=["agents"],
    summary="Get task status",
    description="Get current status of specified task",
)
async def get_task_status(body: ExecuteTaskRequest) -> Dict[str, Any]:
    """Get task status"""
    try:
        logger.info(f"Get task status request: {body.task_id}")

        task = task_manager.get_task(body.task_id)

        if task:
            return {
                "success": True,
                "data": task.to_dict(),
                "message": "Task status retrieved successfully",
            }
        else:
            return {
                "success": False,
                "error": "Task does not exist",
                "message": "Unable to get task status",
            }
    except Exception as e:
        logger.error(f"Failed to get task status: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to get task status",
        }
