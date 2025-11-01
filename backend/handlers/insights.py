"""
Insights module command handlers (新架构)
洞察模块的命令处理器 - 处理 events, knowledge, todos, diaries
"""

from typing import Dict, Any, List
from datetime import datetime
from core.logger import get_logger
from . import api_handler
from core.coordinator import get_coordinator
from models.requests import (
    GetRecentEventsRequest,
    DeleteItemRequest,
    GenerateDiaryRequest,
    GetTodoListRequest,
    GetDiaryListRequest
)

logger = get_logger(__name__)

def get_pipeline():
    """获取新架构处理管道实例"""
    coordinator = get_coordinator()
    coordinator.ensure_managers_initialized()
    pipeline = getattr(coordinator, "processing_pipeline", None)

    if pipeline is None:
        logger.error("未能获取处理管道实例")
        raise RuntimeError("processing pipeline not available")

    return pipeline


# ============ Event 相关接口 ============

@api_handler(
    body=GetRecentEventsRequest,
    method="POST",
    path="/insights/recent-events",
    tags=["insights"],
    summary="获取最近的events",
    description="获取最近N条events记录"
)
async def get_recent_events(body: GetRecentEventsRequest) -> Dict[str, Any]:
    """获取最近的events

    @param body - 请求参数，包含limit
    @returns events列表和元数据
    """
    try:
        pipeline = get_pipeline()
        limit = body.limit if hasattr(body, 'limit') else 50

        events = await pipeline.get_recent_events(limit)

        return {
            "success": True,
            "data": {
                "events": events,
                "count": len(events)
            },
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"获取最近events失败: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"获取最近events失败: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }


# ============ Knowledge 相关接口 ============

@api_handler(
    method="GET",
    path="/insights/knowledge",
    tags=["insights"],
    summary="获取knowledge列表",
    description="获取所有knowledge，优先返回combined_knowledge"
)
async def get_knowledge_list() -> Dict[str, Any]:
    """获取knowledge列表

    @returns knowledge列表（优先返回combined）
    """
    try:
        pipeline = get_pipeline()
        knowledge_list = await pipeline.get_knowledge_list()

        return {
            "success": True,
            "data": {
                "knowledge": knowledge_list,
                "count": len(knowledge_list)
            },
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"获取knowledge列表失败: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"获取knowledge列表失败: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }


@api_handler(
    body=DeleteItemRequest,
    method="POST",
    path="/insights/delete-knowledge",
    tags=["insights"],
    summary="删除knowledge",
    description="软删除指定的knowledge（包括combined_knowledge）"
)
async def delete_knowledge(body: DeleteItemRequest) -> Dict[str, Any]:
    """删除knowledge（软删除）

    @param body - 包含要删除的knowledge ID
    @returns 删除结果
    """
    try:
        pipeline = get_pipeline()
        await pipeline.delete_knowledge(body.id)

        return {
            "success": True,
            "message": "Knowledge已删除",
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"删除knowledge失败: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"删除knowledge失败: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }


# ============ Todo 相关接口 ============

@api_handler(
    body=GetTodoListRequest,
    method="POST",
    path="/insights/todos",
    tags=["insights"],
    summary="获取todo列表",
    description="获取所有todos，优先返回combined_todos，可选包含已完成的"
)
async def get_todo_list(body: GetTodoListRequest) -> Dict[str, Any]:
    """获取todo列表

    @param body - 请求参数，包含include_completed
    @returns todo列表（优先返回combined）
    """
    try:
        pipeline = get_pipeline()
        include_completed = body.include_completed if hasattr(body, 'include_completed') else False

        todo_list = await pipeline.get_todo_list(include_completed)

        return {
            "success": True,
            "data": {
                "todos": todo_list,
                "count": len(todo_list)
            },
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"获取todo列表失败: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"获取todo列表失败: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }


@api_handler(
    body=DeleteItemRequest,
    method="POST",
    path="/insights/delete-todo",
    tags=["insights"],
    summary="删除todo",
    description="软删除指定的todo（包括combined_todo）"
)
async def delete_todo(body: DeleteItemRequest) -> Dict[str, Any]:
    """删除todo（软删除）

    @param body - 包含要删除的todo ID
    @returns 删除结果
    """
    try:
        pipeline = get_pipeline()
        await pipeline.delete_todo(body.id)

        return {
            "success": True,
            "message": "Todo已删除",
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"删除todo失败: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"删除todo失败: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }


# ============ Diary 相关接口 ============

@api_handler(
    body=GenerateDiaryRequest,
    method="POST",
    path="/insights/generate-diary",
    tags=["insights"],
    summary="生成日记",
    description="为指定日期生成日记，基于该日期的所有activities"
)
async def generate_diary(body: GenerateDiaryRequest) -> Dict[str, Any]:
    """生成日记

    @param body - 包含日期（YYYY-MM-DD格式）
    @returns 生成的日记内容
    """
    try:
        pipeline = get_pipeline()
        diary = await pipeline.generate_diary_for_date(body.date)

        if "error" in diary:
            return {
                "success": False,
                "message": diary["error"],
                "timestamp": datetime.now().isoformat()
            }

        return {
            "success": True,
            "data": diary,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"生成日记失败: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"生成日记失败: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }


@api_handler(
    body=GetDiaryListRequest,
    method="POST",
    path="/insights/diaries",
    tags=["insights"],
    summary="获取日记列表",
    description="获取最近的日记记录"
)
async def get_diary_list(body: GetDiaryListRequest) -> Dict[str, Any]:
    """获取日记列表"""
    try:
        pipeline = get_pipeline()
        diaries = await pipeline.get_diary_list(body.limit)

        return {
            "success": True,
            "data": {
                "diaries": diaries,
                "count": len(diaries)
            },
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"获取diary列表失败: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"获取diary列表失败: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }


@api_handler(
    body=DeleteItemRequest,
    method="POST",
    path="/insights/delete-diary",
    tags=["insights"],
    summary="删除日记",
    description="删除指定的日记"
)
async def delete_diary(body: DeleteItemRequest) -> Dict[str, Any]:
    """删除日记

    @param body - 包含要删除的diary ID
    @returns 删除结果
    """
    try:
        pipeline = get_pipeline()
        await pipeline.delete_diary(body.id)

        return {
            "success": True,
            "message": "日记已删除",
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"删除日记失败: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"删除日记失败: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }


# ============ 统计信息接口 ============

@api_handler(
    method="GET",
    path="/insights/stats",
    tags=["insights"],
    summary="获取pipeline统计信息",
    description="获取当前pipeline的运行状态和统计数据"
)
async def get_pipeline_stats() -> Dict[str, Any]:
    """获取pipeline统计信息

    @returns pipeline运行状态和统计数据
    """
    try:
        pipeline = get_pipeline()
        stats = pipeline.get_stats()

        return {
            "success": True,
            "data": stats,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"获取pipeline统计失败: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"获取pipeline统计失败: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }
