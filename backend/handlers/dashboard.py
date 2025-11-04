"""
Dashboard module command handlers
Dashboard module commands handlers
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
    summary="Get LLM usage statistics",
    description="Get LLM token consumption, call count, and cost statistics for the past 30 days",
)
async def get_llm_stats() -> Dict[str, Any]:
    """Get LLM usage statistics

    @returns LLM token consumption statistics and call count
    """
    try:
        dashboard_manager = get_dashboard_manager()
        stats = dashboard_manager.get_llm_statistics(days=30)

        return {
            "success": True,
            "data": stats.model_dump(),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to get LLM statistics: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Failed to get LLM statistics: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        }


@api_handler(
    body=GetLLMStatsByModelRequest,
    method="POST",
    path="/dashboard/llm-stats/by-model",
    tags=["dashboard"],
    summary="Get LLM usage statistics by model",
    description="Get LLM token consumption, call count, and cost statistics for the past 30 days by model ID, including model price information",
)
async def get_llm_stats_by_model(body: GetLLMStatsByModelRequest) -> Dict[str, Any]:
    """Get LLM usage statistics by model"""
    try:
        dashboard_manager = get_dashboard_manager()
        stats = dashboard_manager.get_llm_statistics_by_model(
            model_id=body.model_id, days=30
        )

        return {
            "success": True,
            "data": stats.model_dump(),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to get LLM statistics by model: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Failed to get LLM statistics by model: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        }


@api_handler(
    body=RecordLLMUsageRequest,
    method="POST",
    path="/dashboard/record-llm-usage",
    tags=["dashboard"],
    summary="Record LLM usage statistics",
    description="Record token consumption, cost and other information for a single LLM call",
)
async def record_llm_usage(body: RecordLLMUsageRequest) -> Dict[str, Any]:
    """Record LLM usage statistics

    @param body LLM usage information
    @returns Recording result
    """
    try:
        dashboard_manager = get_dashboard_manager()
        success = dashboard_manager.record_llm_usage(
            model=body.model,
            prompt_tokens=body.prompt_tokens,
            completion_tokens=body.completion_tokens,
            total_tokens=body.total_tokens,
            cost=body.cost,
            request_type=body.request_type,
        )

        if success:
            return {
                "success": True,
                "message": "LLM usage record saved",
                "timestamp": datetime.now().isoformat(),
            }
        else:
            return {
                "success": False,
                "message": "Failed to save LLM usage record",
                "timestamp": datetime.now().isoformat(),
            }

    except Exception as e:
        logger.error(f"Failed to save LLM usage record: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Failed to save LLM usage record: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        }


@api_handler(
    method="GET",
    path="/dashboard/usage-summary",
    tags=["dashboard"],
    summary="Get usage summary",
    description="Get overall usage summary statistics",
)
async def get_usage_summary() -> Dict[str, Any]:
    """Get overall usage summary statistics

    @returns Overall summary including activities, tasks, and LLM usage
    """
    try:
        dashboard_manager = get_dashboard_manager()
        summary = dashboard_manager.get_usage_summary()

        # Convert to dictionary format for serialization
        summary_data = {
            "activities": {"total": summary.activities_total},
            "tasks": {
                "total": summary.tasks_total,
                "completed": summary.tasks_completed,
                "pending": summary.tasks_pending,
            },
            "llm": {
                "tokensLast7Days": summary.llm_tokens_last_7_days,
                "callsLast7Days": summary.llm_calls_last_7_days,
                "costLast7Days": summary.llm_cost_last_7_days,
            },
        }

        logger.info("Usage summary statistics retrieval completed")

        return {
            "success": True,
            "data": summary_data,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to get usage summary: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Failed to get usage summary: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        }


@api_handler(
    method="GET",
    path="/dashboard/daily-llm-usage",
    tags=["dashboard"],
    summary="Get daily LLM usage",
    description="Get detailed daily LLM usage data for the past 7 days",
)
async def get_daily_llm_usage() -> Dict[str, Any]:
    """Get daily LLM usage

    @returns Daily LLM usage data list
    """
    try:
        dashboard_manager = get_dashboard_manager()
        daily_usage = dashboard_manager.get_daily_llm_usage(days=7)

        return {
            "success": True,
            "data": daily_usage,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to get daily LLM usage: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Failed to get daily LLM usage: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        }


@api_handler(
    method="GET",
    path="/dashboard/model-distribution",
    tags=["dashboard"],
    summary="Get model usage distribution",
    description="Get model usage distribution statistics for the past 30 days",
)
async def get_model_distribution() -> Dict[str, Any]:
    """Get model usage distribution statistics

    @returns Model usage distribution data
    """
    try:
        dashboard_manager = get_dashboard_manager()
        model_distribution = dashboard_manager.get_model_usage_distribution(days=30)

        return {
            "success": True,
            "data": model_distribution,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to get model usage distribution: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Failed to get model usage distribution: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        }
