"""
Agent-related API handlers
"""

from typing import Any, Dict, List

from agents.manager import task_manager
from core.logger import get_logger
from models.requests import (
    CreateTaskRequest,
    DeleteTaskRequest,
    ExecuteTaskInChatRequest,
    ExecuteTaskRequest,
    GetAvailableAgentsRequest,
    GetTasksByDateRequest,
    GetTasksRequest,
    ScheduleTaskRequest,
    UnscheduleTaskRequest,
)

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


@api_handler(
    body=ScheduleTaskRequest,
    method="POST",
    path="/agents/schedule-task",
    tags=["agents"],
    summary="Schedule task to a specific date",
    description="Move a task from pending to a specific date in the calendar",
)
async def schedule_task(body: ScheduleTaskRequest) -> Dict[str, Any]:
    """Schedule task to a specific date"""
    try:
        logger.info(f"Schedule task request: {body.task_id} to {body.scheduled_date}")

        success = task_manager.schedule_task(body.task_id, body.scheduled_date)

        if success:
            task = task_manager.get_task(body.task_id)
            return {
                "success": True,
                "data": task.to_dict() if task else None,
                "message": "Task scheduled successfully",
            }
        else:
            return {
                "success": False,
                "error": "Failed to schedule task",
                "message": "Unable to schedule task",
            }
    except Exception as e:
        logger.error(f"Failed to schedule task: {str(e)}")
        return {"success": False, "error": str(e), "message": "Failed to schedule task"}


@api_handler(
    body=UnscheduleTaskRequest,
    method="POST",
    path="/agents/unschedule-task",
    tags=["agents"],
    summary="Unschedule task",
    description="Move a task back to pending inbox",
)
async def unschedule_task(body: UnscheduleTaskRequest) -> Dict[str, Any]:
    """Unschedule task (move back to pending)"""
    try:
        logger.info(f"Unschedule task request: {body.task_id}")

        success = task_manager.unschedule_task(body.task_id)

        if success:
            task = task_manager.get_task(body.task_id)
            return {
                "success": True,
                "data": task.to_dict() if task else None,
                "message": "Task unscheduled successfully",
            }
        else:
            return {
                "success": False,
                "error": "Failed to unschedule task",
                "message": "Unable to unschedule task",
            }
    except Exception as e:
        logger.error(f"Failed to unschedule task: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to unschedule task",
        }


@api_handler(
    body=GetTasksByDateRequest,
    method="POST",
    path="/agents/get-tasks-by-date",
    tags=["agents"],
    summary="Get tasks by date",
    description="Get all tasks scheduled for a specific date",
)
async def get_tasks_by_date(body: GetTasksByDateRequest) -> Dict[str, Any]:
    """Get tasks scheduled for a specific date"""
    try:
        logger.info(f"Get tasks by date request: {body.scheduled_date}")

        tasks = task_manager.get_tasks_by_date(body.scheduled_date)
        tasks_data = [task.to_dict() for task in tasks]

        return {
            "success": True,
            "data": tasks_data,
            "message": f"Retrieved {len(tasks_data)} tasks for {body.scheduled_date}",
        }
    except Exception as e:
        logger.error(f"Failed to get tasks by date: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to get tasks by date",
        }


@api_handler(
    body=ExecuteTaskInChatRequest,
    method="POST",
    path="/agents/execute-task-in-chat",
    tags=["agents"],
    summary="Execute task in chat",
    description="Execute a task by sending it to the chat interface",
)
async def execute_task_in_chat(body: ExecuteTaskInChatRequest) -> Dict[str, Any]:
    """Execute task in chat"""
    try:
        logger.info(
            f"Execute task in chat: {body.task_id}, conversation: {body.conversation_id}"
        )

        task = task_manager.get_task(body.task_id)
        if not task:
            return {
                "success": False,
                "error": "Task does not exist",
                "message": "Unable to find task",
            }

        # Import chat service to create/use conversation
        from handlers.chat import create_conversation, send_message

        conversation_id = body.conversation_id

        # Create new conversation if not provided
        if not conversation_id:
            # Create conversation with task description as title
            title = task.plan_description[:50] + (
                "..." if len(task.plan_description) > 50 else ""
            )
            from models.requests import CreateConversationRequest

            conv_result = await create_conversation(
                CreateConversationRequest(title=title)
            )
            if not conv_result.get("success"):
                return {
                    "success": False,
                    "error": "Failed to create conversation",
                    "message": "Unable to create conversation for task",
                }
            conversation_id = conv_result["data"]["id"]

        # Send task description as message
        from models.requests import SendMessageRequest

        message_result = await send_message(
            SendMessageRequest(
                conversation_id=conversation_id, content=task.plan_description
            )
        )

        if message_result.get("success"):
            # Delete the task from agents after successfully sending to chat
            task_manager.delete_task(body.task_id)

            return {
                "success": True,
                "data": {
                    "conversationId": conversation_id,
                    "taskId": task.id,
                },
                "message": "Task sent to chat successfully",
            }
        else:
            return {
                "success": False,
                "error": "Failed to send message",
                "message": "Unable to send task to chat",
            }

    except Exception as e:
        logger.error(f"Failed to execute task in chat: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to execute task in chat",
        }
