"""
Dashboard module command handlers
仪表盘模块的命令处理器
"""

from typing import Dict, Any
from datetime import datetime
from core.logger import get_logger
from core.dashboard.manager import get_dashboard_manager
from . import api_handler
from models.requests import RecordLLMUsageRequest, GetLLMStatsByModelRequest

logger = get_logger(__name__)


@api_handler(
    method="GET",
    path="/dashboard/llm-stats",
    tags=["dashboard"],
    summary="获取LLM使用统计",
    description="获取过去30天的LLM token消耗、调用次数和费用统计"
)
async def get_llm_stats() -> Dict[str, Any]:
    """获取LLM使用统计信息

    @returns LLM token消耗统计和调用次数
    """
    try:
        dashboard_manager = get_dashboard_manager()
        stats = dashboard_manager.get_llm_statistics(days=30)

        return {
            "success": True,
            "data": stats.model_dump(),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"获取LLM统计失败: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"获取LLM统计失败: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }


@api_handler(
    body=GetLLMStatsByModelRequest,
    method="POST",
    path="/dashboard/llm-stats/by-model",
    tags=["dashboard"],
    summary="按模型获取LLM使用统计",
    description="根据模型ID获取过去30天的LLM token消耗、调用次数和费用统计，并包含模型价格信息"
)
async def get_llm_stats_by_model(body: GetLLMStatsByModelRequest) -> Dict[str, Any]:
    """按模型获取LLM使用统计信息"""
    try:
        dashboard_manager = get_dashboard_manager()
        stats = dashboard_manager.get_llm_statistics_by_model(model_id=body.model_id, days=30)

        return {
            "success": True,
            "data": stats.model_dump(),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"按模型获取LLM统计失败: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"按模型获取LLM统计失败: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }


@api_handler(
    body=RecordLLMUsageRequest,
    method="POST",
    path="/dashboard/record-llm-usage",
    tags=["dashboard"],
    summary="记录LLM使用统计",
    description="记录单次LLM调用的token消耗、费用等信息"
)
async def record_llm_usage(body: RecordLLMUsageRequest) -> Dict[str, Any]:
    """记录LLM使用统计

    @param body LLM使用信息
    @returns 记录结果
    """
    try:
        dashboard_manager = get_dashboard_manager()
        success = dashboard_manager.record_llm_usage(
            model=body.model,
            prompt_tokens=body.prompt_tokens,
            completion_tokens=body.completion_tokens,
            total_tokens=body.total_tokens,
            cost=body.cost,
            request_type=body.request_type
        )

        if success:
            return {
                "success": True,
                "message": "LLM使用记录已保存",
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "success": False,
                "message": "LLM使用记录保存失败",
                "timestamp": datetime.now().isoformat()
            }

    except Exception as e:
        logger.error(f"保存LLM使用记录失败: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"保存LLM使用记录失败: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }


@api_handler(
    method="GET",
    path="/dashboard/usage-summary",
    tags=["dashboard"],
    summary="获取使用量摘要",
    description="获取整体使用量摘要统计"
)
async def get_usage_summary() -> Dict[str, Any]:
    """获取整体使用量摘要统计

    @returns 包括活动、任务、LLM使用的总体摘要
    """
    try:
        dashboard_manager = get_dashboard_manager()
        summary = dashboard_manager.get_usage_summary()

        # 转换为字典格式以便序列化
        summary_data = {
            "activities": {
                "total": summary.activities_total
            },
            "tasks": {
                "total": summary.tasks_total,
                "completed": summary.tasks_completed,
                "pending": summary.tasks_pending
            },
            "llm": {
                "tokensLast7Days": summary.llm_tokens_last_7_days,
                "callsLast7Days": summary.llm_calls_last_7_days,
                "costLast7Days": summary.llm_cost_last_7_days
            }
        }

        logger.info("获取使用摘要统计完成")

        return {
            "success": True,
            "data": summary_data,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"获取使用摘要失败: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"获取使用摘要失败: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }


@api_handler(
    method="GET",
    path="/dashboard/daily-llm-usage",
    tags=["dashboard"],
    summary="获取每日LLM使用情况",
    description="获取过去7天的每日LLM使用详细数据"
)
async def get_daily_llm_usage() -> Dict[str, Any]:
    """获取每日LLM使用情况

    @returns 每日LLM使用数据列表
    """
    try:
        dashboard_manager = get_dashboard_manager()
        daily_usage = dashboard_manager.get_daily_llm_usage(days=7)

        return {
            "success": True,
            "data": daily_usage,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"获取每日LLM使用失败: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"获取每日LLM使用失败: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }


@api_handler(
    method="GET",
    path="/dashboard/model-distribution",
    tags=["dashboard"],
    summary="获取模型使用分布",
    description="获取过去30天的模型使用分布统计"
)
async def get_model_distribution() -> Dict[str, Any]:
    """获取模型使用分布统计

    @returns 模型使用分布数据
    """
    try:
        dashboard_manager = get_dashboard_manager()
        model_distribution = dashboard_manager.get_model_usage_distribution(days=30)

        return {
            "success": True,
            "data": model_distribution,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"获取模型使用分布失败: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"获取模型使用分布失败: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }
