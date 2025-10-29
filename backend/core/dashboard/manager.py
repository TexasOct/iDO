"""
Dashboard Manager
仪表盘管理器

处理所有仪表盘相关的业务逻辑，包括：
- LLM 使用统计查询
- 使用量摘要计算
- 数据聚合和分析
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from ..logger import get_logger
from ..db import get_db
from models.base import LLMUsageStats, LLMUsageResponse

logger = get_logger(__name__)


@dataclass
class UsageStatsSummary:
    """使用量摘要数据结构"""
    activities_total: int
    tasks_total: int
    tasks_completed: int
    tasks_pending: int
    llm_tokens_last_7_days: int
    llm_calls_last_7_days: int
    llm_cost_last_7_days: float


class DashboardManager:
    """仪表盘管理器

    负责处理所有仪表盘相关的数据查询和统计计算
    """

    def __init__(self):
        self.db = get_db()

    def get_llm_statistics(self, days: int = 30) -> LLMUsageStats:
        """获取LLM使用统计

        Args:
            days: 统计天数，默认30天

        Returns:
            LLMUsageStats: LLM使用统计数据

        Raises:
            Exception: 数据库查询异常
        """
        try:
            # 计算时间范围
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            # 查询总体统计
            stats_query = """
            SELECT
                COUNT(*) as total_calls,
                SUM(total_tokens) as total_tokens,
                SUM(cost) as total_cost,
                GROUP_CONCAT(DISTINCT model) as models_used
            FROM llm_token_usage
            WHERE timestamp >= ? AND timestamp <= ?
            """

            stats_results = self.db.execute_query(stats_query, (start_date.isoformat(), end_date.isoformat()))

            # 查询每日使用量（最近7天）
            daily_query = """
            SELECT
                DATE(timestamp) as date,
                SUM(total_tokens) as daily_tokens,
                COUNT(*) as daily_calls,
                SUM(cost) as daily_cost
            FROM llm_token_usage
            WHERE timestamp >= ? AND timestamp <= ?
            GROUP BY DATE(timestamp)
            ORDER BY date DESC
            LIMIT 7
            """

            daily_results = self.db.execute_query(
                daily_query,
                (start_date.isoformat(), end_date.isoformat())
            )

            # 构建结果数据
            result = stats_results[0] if stats_results else {}
            total_calls = result.get('total_calls', 0) or 0
            total_tokens = result.get('total_tokens', 0) or 0
            total_cost = result.get('total_cost', 0.0) or 0.0
            models_used_str = result.get('models_used', '') or ""

            # 处理模型列表
            models_list = models_used_str.split(',') if models_used_str else []

            # 构建每日使用数据
            daily_usage = []
            for row in daily_results:
                daily_usage.append({
                    "date": row['date'],
                    "tokens": row['daily_tokens'] or 0,
                    "calls": row['daily_calls'] or 0,
                    "cost": row['daily_cost'] or 0.0
                })

            # 创建前端响应模型（camelCase格式）
            stats = LLMUsageResponse(
                totalTokens=total_tokens,
                totalCalls=total_calls,
                totalCost=total_cost,
                modelsUsed=models_list,
                period=f"{days}days",
                dailyUsage=daily_usage
            )

            logger.info(f"获取LLM统计完成: {stats.totalTokens} tokens, {stats.totalCalls} calls")
            return stats

        except Exception as e:
            logger.error(f"获取LLM统计失败: {e}", exc_info=True)
            # 返回默认值
            return LLMUsageResponse(
                totalTokens=0,
                totalCalls=0,
                totalCost=0.0,
                modelsUsed=[],
                period=f"{days}days",
                dailyUsage=[]
            )

    def record_llm_usage(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        cost: float = 0.0,
        request_type: str = "unknown"
    ) -> bool:
        """记录LLM使用情况

        Args:
            model: LLM模型名称
            prompt_tokens: 提示token数量
            completion_tokens: 完成token数量
            total_tokens: 总token数量
            cost: 使用成本
            request_type: 请求类型

        Returns:
            bool: 记录是否成功
        """
        try:
            insert_query = """
            INSERT INTO llm_token_usage
            (timestamp, model, prompt_tokens, completion_tokens, total_tokens, cost, request_type)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """

            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(insert_query, (
                    datetime.now().isoformat(),
                    model,
                    prompt_tokens,
                    completion_tokens,
                    total_tokens,
                    cost,
                    request_type
                ))
                conn.commit()

            logger.info(f"记录LLM使用成功: {model} - {total_tokens} tokens - ${cost:.6f}")
            return True

        except Exception as e:
            logger.error(f"记录LLM使用失败: {e}", exc_info=True)
            return False

    def get_usage_summary(self) -> UsageStatsSummary:
        """获取整体使用量摘要

        Returns:
            UsageStatsSummary: 使用量摘要数据
        """
        try:
            # 获取活动统计
            activity_count_results = self.db.execute_query("SELECT COUNT(*) as count FROM activities")
            activities_total = activity_count_results[0]['count'] if activity_count_results else 0

            # 获取任务统计
            task_stats_query = """
            SELECT
                COUNT(*) as total_tasks,
                COUNT(CASE WHEN status = 'done' THEN 1 END) as completed_tasks,
                COUNT(CASE WHEN status = 'todo' THEN 1 END) as pending_tasks
            FROM tasks
            """
            task_results = self.db.execute_query(task_stats_query)

            # 获取LLM统计（最近7天）
            llm_stats_query = """
            SELECT
                SUM(total_tokens) as tokens_last_7_days,
                COUNT(*) as calls_last_7_days,
                SUM(cost) as cost_last_7_days
            FROM llm_token_usage
            WHERE timestamp >= datetime('now', '-7 days')
            """
            llm_results = self.db.execute_query(llm_stats_query)

            task_result = task_results[0] if task_results else {}
            llm_result = llm_results[0] if llm_results else {}

            summary = UsageStatsSummary(
                activities_total=activities_total,
                tasks_total=task_result.get('total_tasks', 0) or 0,
                tasks_completed=task_result.get('completed_tasks', 0) or 0,
                tasks_pending=task_result.get('pending_tasks', 0) or 0,
                llm_tokens_last_7_days=llm_result.get('tokens_last_7_days', 0) or 0,
                llm_calls_last_7_days=llm_result.get('calls_last_7_days', 0) or 0,
                llm_cost_last_7_days=llm_result.get('cost_last_7_days', 0.0) or 0.0
            )

            logger.info("获取使用量摘要完成")
            return summary

        except Exception as e:
            logger.error(f"获取使用量摘要失败: {e}", exc_info=True)
            # 返回默认值
            return UsageStatsSummary(
                activities_total=0,
                tasks_total=0,
                tasks_completed=0,
                tasks_pending=0,
                llm_tokens_last_7_days=0,
                llm_calls_last_7_days=0,
                llm_cost_last_7_days=0.0
            )

    def get_daily_llm_usage(self, days: int = 7) -> List[Dict[str, Any]]:
        """获取每日LLM使用情况

        Args:
            days: 查询天数，默认7天

        Returns:
            List[Dict]: 每日使用数据列表
        """
        try:
            query = """
            SELECT
                DATE(timestamp) as date,
                model,
                SUM(total_tokens) as daily_tokens,
                COUNT(*) as daily_calls,
                SUM(cost) as daily_cost
            FROM llm_token_usage
            WHERE timestamp >= datetime('now', '-{} days')
            GROUP BY DATE(timestamp), model
            ORDER BY date DESC, model
            """.format(days)

            results = self.db.execute_query(query)

            daily_data = []
            for row in results:
                daily_data.append({
                    "date": row['date'],
                    "model": row['model'],
                    "tokens": row['daily_tokens'] or 0,
                    "calls": row['daily_calls'] or 0,
                    "cost": row['daily_cost'] or 0.0
                })

            return daily_data

        except Exception as e:
            logger.error(f"获取每日LLM使用失败: {e}", exc_info=True)
            return []

    def get_model_usage_distribution(self, days: int = 30) -> List[Dict[str, Any]]:
        """获取模型使用分布统计

        Args:
            days: 统计天数，默认30天

        Returns:
            List[Dict]: 模型使用分布数据
        """
        try:
            query = """
            SELECT
                model,
                COUNT(*) as calls,
                SUM(total_tokens) as total_tokens,
                SUM(cost) as total_cost,
                AVG(total_tokens) as avg_tokens_per_call
            FROM llm_token_usage
            WHERE timestamp >= datetime('now', '-{} days')
            GROUP BY model
            ORDER BY total_tokens DESC
            """.format(days)

            results = self.db.execute_query(query)

            model_data = []
            for row in results:
                model_data.append({
                    "model": row['model'],
                    "calls": row['calls'] or 0,
                    "total_tokens": row['total_tokens'] or 0,
                    "total_cost": row['total_cost'] or 0.0,
                    "avg_tokens_per_call": row['avg_tokens_per_call'] or 0.0
                })

            return model_data

        except Exception as e:
            logger.error(f"获取模型使用分布失败: {e}", exc_info=True)
            return []


# 全局DashboardManager实例
_dashboard_manager: Optional[DashboardManager] = None


def get_dashboard_manager() -> DashboardManager:
    """获取全局DashboardManager实例

    Returns:
        DashboardManager: 全局仪表盘管理器实例
    """
    global _dashboard_manager

    if _dashboard_manager is None:
        _dashboard_manager = DashboardManager()

    return _dashboard_manager
