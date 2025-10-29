"""
Agent相关的API处理器
"""

from typing import Dict, Any, List
from core.logger import get_logger
from models.requests import (
    CreateTaskRequest,
    ExecuteTaskRequest, 
    DeleteTaskRequest,
    GetTasksRequest,
    GetAvailableAgentsRequest
)
from agents.manager import task_manager
from . import api_handler

logger = get_logger(__name__)


@api_handler(
    body=CreateTaskRequest,
    method="POST",
    path="/agents/create-task",
    tags=["agents"],
    summary="创建新的Agent任务",
    description="创建一个新的Agent任务，指定Agent类型和任务描述"
)
async def create_task(body: CreateTaskRequest) -> Dict[str, Any]:
    """创建新的Agent任务"""
    try:
        logger.info(f"创建任务请求: {body.agent} - {body.plan_description}")
        
        task = task_manager.create_task(body.agent, body.plan_description)
        
        return {
            "success": True,
            "data": task.to_dict(),
            "message": "任务创建成功"
        }
    except Exception as e:
        logger.error(f"创建任务失败: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "message": "任务创建失败"
        }


@api_handler(
    body=ExecuteTaskRequest,
    method="POST",
    path="/agents/execute-task",
    tags=["agents"],
    summary="执行Agent任务",
    description="执行指定的Agent任务"
)
async def execute_task(body: ExecuteTaskRequest) -> Dict[str, Any]:
    """执行Agent任务"""
    try:
        logger.info(f"执行任务请求: {body.task_id}")
        
        success = await task_manager.execute_task(body.task_id)
        
        if success:
            return {
                "success": True,
                "message": "任务开始执行"
            }
        else:
            return {
                "success": False,
                "error": "任务执行失败",
                "message": "无法执行任务"
            }
    except Exception as e:
        logger.error(f"执行任务失败: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "message": "任务执行失败"
        }


@api_handler(
    body=DeleteTaskRequest,
    method="POST",
    path="/agents/delete-task",
    tags=["agents"],
    summary="删除Agent任务",
    description="删除指定的Agent任务"
)
async def delete_task(body: DeleteTaskRequest) -> Dict[str, Any]:
    """删除Agent任务"""
    try:
        logger.info(f"删除任务请求: {body.task_id}")
        
        success = task_manager.delete_task(body.task_id)
        
        if success:
            return {
                "success": True,
                "message": "任务删除成功"
            }
        else:
            return {
                "success": False,
                "error": "任务不存在",
                "message": "无法删除任务"
            }
    except Exception as e:
        logger.error(f"删除任务失败: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "message": "任务删除失败"
        }


@api_handler(
    body=GetTasksRequest,
    method="POST",
    path="/agents/get-tasks",
    tags=["agents"],
    summary="获取Agent任务列表",
    description="获取Agent任务列表，支持按状态筛选"
)
async def get_tasks(body: GetTasksRequest) -> Dict[str, Any]:
    """获取Agent任务列表"""
    try:
        logger.info(f"获取任务列表请求: limit={body.limit}, status={body.status}")
        
        tasks = task_manager.get_tasks(body.limit, body.status)
        tasks_data = [task.to_dict() for task in tasks]
        
        return {
            "success": True,
            "data": tasks_data,
            "message": f"获取到 {len(tasks_data)} 个任务"
        }
    except Exception as e:
        logger.error(f"获取任务列表失败: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "message": "获取任务列表失败"
        }


@api_handler(
    body=GetAvailableAgentsRequest,
    method="POST",
    path="/agents/get-available-agents",
    tags=["agents"],
    summary="获取可用的Agent列表",
    description="获取所有可用的Agent类型和配置"
)
async def get_available_agents(body: GetAvailableAgentsRequest) -> Dict[str, Any]:
    """获取可用的Agent列表"""
    try:
        logger.info("获取可用Agent列表请求")
        
        agents = task_manager.get_available_agents()
        agents_data = [agent.to_dict() for agent in agents]
        
        return {
            "success": True,
            "data": agents_data,
            "message": f"获取到 {len(agents_data)} 个可用Agent"
        }
    except Exception as e:
        logger.error(f"获取可用Agent列表失败: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "message": "获取可用Agent列表失败"
        }


@api_handler(
    body=ExecuteTaskRequest,
    method="POST",
    path="/agents/get-task-status",
    tags=["agents"],
    summary="获取任务状态",
    description="获取指定任务的当前状态"
)
async def get_task_status(body: ExecuteTaskRequest) -> Dict[str, Any]:
    """获取任务状态"""
    try:
        logger.info(f"获取任务状态请求: {body.task_id}")
        
        task = task_manager.get_task(body.task_id)
        
        if task:
            return {
                "success": True,
                "data": task.to_dict(),
                "message": "获取任务状态成功"
            }
        else:
            return {
                "success": False,
                "error": "任务不存在",
                "message": "无法获取任务状态"
            }
    except Exception as e:
        logger.error(f"获取任务状态失败: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "message": "获取任务状态失败"
        }
