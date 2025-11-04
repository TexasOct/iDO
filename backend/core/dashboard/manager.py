"""
Dashboard Manager

Handles all dashboard-related business logic, including:
- LLM usage statistics queries
- Usage summary calculations
- Data aggregation and analysis
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from ..logger import get_logger
from ..db import get_db
from models.base import LLMUsageResponse

logger = get_logger(__name__)


@dataclass
class UsageStatsSummary:
    """Usage summary data structure"""

    activities_total: int
    tasks_total: int
    tasks_completed: int
    tasks_pending: int
    llm_tokens_last_7_days: int
    llm_calls_last_7_days: int
    llm_cost_last_7_days: float


class DashboardManager:
    """Dashboard manager

    Responsible for handling all dashboard-related data queries and statistical calculations
    """

    def __init__(self):
        self.db = get_db()

    def get_llm_statistics(
        self,
        days: int = 30,
        model_filter: Optional[str] = None,
        model_details: Optional[Dict[str, Any]] = None,
    ) -> LLMUsageResponse:
        """Get LLM usage statistics

        Args:
            days: Number of days for statistics, default 30 days
            model_filter: Optional model filter (filter statistics by model name)
            model_details: Model details used when filtering by model

        Returns:
            LLMUsageResponse: LLM usage statistics data

        Raises:
            Exception: Database query exception
        """
        try:
            # Calculate time range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            # Build query conditions
            where_clauses = ["timestamp >= ?", "timestamp <= ?"]
            params: List[Any] = [start_date.isoformat(), end_date.isoformat()]

            if model_filter:
                where_clauses.append("model = ?")
                params.append(model_filter)

            where_sql = " AND ".join(where_clauses)

            # Query overall statistics
            stats_query = f"""
            SELECT
                COUNT(*) as total_calls,
                SUM(total_tokens) as total_tokens,
                SUM(prompt_tokens) as prompt_tokens,
                SUM(completion_tokens) as completion_tokens,
                SUM(cost) as total_cost,
                GROUP_CONCAT(DISTINCT model) as models_used
            FROM llm_token_usage
            WHERE {where_sql}
            """

            stats_results = self.db.execute_query(stats_query, tuple(params))

            # Query daily usage (last 7 days)
            daily_query = f"""
            SELECT
                DATE(timestamp) as date,
                SUM(total_tokens) as daily_tokens,
                SUM(prompt_tokens) as daily_prompt_tokens,
                SUM(completion_tokens) as daily_completion_tokens,
                COUNT(*) as daily_calls,
                SUM(cost) as daily_cost
            FROM llm_token_usage
            WHERE {where_sql}
            GROUP BY DATE(timestamp)
            ORDER BY date DESC
            LIMIT 7
            """

            daily_results = self.db.execute_query(daily_query, tuple(params))

            # Build result data
            result = stats_results[0] if stats_results else {}
            total_calls = int(result.get("total_calls", 0) or 0)
            total_tokens = int(result.get("total_tokens", 0) or 0)
            prompt_tokens = int(result.get("prompt_tokens", 0) or 0)
            completion_tokens = int(result.get("completion_tokens", 0) or 0)
            recorded_total_cost = result.get("total_cost", 0.0) or 0.0
            models_used_str = result.get("models_used", "") or ""

            # Process model list
            models_list = models_used_str.split(",") if models_used_str else []
            models_list = [model.strip() for model in models_list if model.strip()]
            if not model_details:
                # Remove duplicates while preserving original order
                seen = set()
                unique_models = []
                for model in models_list:
                    if model not in seen:
                        seen.add(model)
                        unique_models.append(model)
                models_list = unique_models
            if model_details:
                display_name = (
                    model_details.get("name")
                    or model_details.get("model")
                    or model_filter
                )
                if display_name:
                    models_list = [display_name]
            elif model_filter and not models_list:
                models_list = [model_filter]

            total_cost = recorded_total_cost
            if model_details:
                total_cost = self._calculate_cost_from_tokens(
                    prompt_tokens,
                    completion_tokens,
                    float(model_details.get("inputTokenPrice") or 0.0),
                    float(model_details.get("outputTokenPrice") or 0.0),
                )

            # Build daily usage data
            daily_usage = []
            for row in daily_results:
                daily_tokens = int(row.get("daily_tokens", 0) or 0)
                daily_calls = int(row.get("daily_calls", 0) or 0)
                daily_prompt = int(row.get("daily_prompt_tokens", 0) or 0)
                daily_completion = int(row.get("daily_completion_tokens", 0) or 0)
                daily_usage.append(
                    {
                        "date": row["date"],
                        "tokens": daily_tokens,
                        "calls": daily_calls,
                        "cost": self._calculate_daily_cost(
                            row.get("daily_cost", 0.0) or 0.0,
                            daily_prompt,
                            daily_completion,
                            model_details,
                        ),
                    }
                )

            # Create frontend response model (camelCase format)
            stats = LLMUsageResponse(
                totalTokens=total_tokens,
                totalCalls=total_calls,
                totalCost=total_cost,
                modelsUsed=models_list,
                period=f"{days}days",
                dailyUsage=daily_usage,
                modelDetails=model_details,
            )

            logger.info(
                f"LLM statistics retrieval completed: {stats.totalTokens} tokens, {stats.totalCalls} calls"
            )
            return stats

        except Exception as e:
            logger.error(f"Failed to get LLM statistics: {e}", exc_info=True)
            # Return default values
            return LLMUsageResponse(
                totalTokens=0,
                totalCalls=0,
                totalCost=0.0,
                modelsUsed=[],
                period=f"{days}days",
                dailyUsage=[],
                modelDetails=model_details,
            )

    def get_llm_statistics_by_model(
        self, model_id: str, days: int = 30
    ) -> LLMUsageResponse:
        """Get LLM usage statistics by model with model details"""
        try:
            model_query = """
            SELECT
                id,
                name,
                provider,
                api_url,
                model,
                currency,
                input_token_price,
                output_token_price
            FROM llm_models
            WHERE id = ?
            """
            model_results = self.db.execute_query(model_query, (model_id,))

            if not model_results:
                raise ValueError(f"Model configuration does not exist: {model_id}")

            model_row = model_results[0]
            model_details = {
                "id": model_row["id"],
                "name": model_row["name"],
                "provider": model_row["provider"],
                "apiUrl": model_row["api_url"],
                "model": model_row["model"],
                "currency": model_row["currency"],
                "inputTokenPrice": model_row["input_token_price"],
                "outputTokenPrice": model_row["output_token_price"],
            }

            # Use model field as filter condition
            model_filter = model_row["model"]

            stats = self.get_llm_statistics(
                days=days, model_filter=model_filter, model_details=model_details
            )

            return stats

        except Exception as e:
            logger.error(f"Failed to get LLM statistics by model: {e}", exc_info=True)
            return LLMUsageResponse(
                totalTokens=0,
                totalCalls=0,
                totalCost=0.0,
                modelsUsed=[],
                period=f"{days}days",
                dailyUsage=[],
                modelDetails=None,
            )

    @staticmethod
    def _calculate_cost_from_tokens(
        prompt_tokens: int,
        completion_tokens: int,
        input_price_per_million: float,
        output_price_per_million: float,
    ) -> float:
        """Calculate cost based on token count and unit price"""
        try:
            prompt_tokens = prompt_tokens or 0
            completion_tokens = completion_tokens or 0
            input_price_per_million = input_price_per_million or 0.0
            output_price_per_million = output_price_per_million or 0.0

            total_cost = (prompt_tokens / 1_000_000) * input_price_per_million + (
                completion_tokens / 1_000_000
            ) * output_price_per_million
            return round(total_cost, 6)
        except Exception:
            return 0.0

    def _calculate_daily_cost(
        self,
        recorded_cost: float,
        prompt_tokens: int,
        completion_tokens: int,
        model_details: Optional[Dict[str, Any]],
    ) -> float:
        """Calculate daily cost (recalculate based on pricing in single model view)"""
        if model_details:
            return self._calculate_cost_from_tokens(
                prompt_tokens,
                completion_tokens,
                float(model_details.get("inputTokenPrice") or 0.0),
                float(model_details.get("outputTokenPrice") or 0.0),
            )
        return recorded_cost or 0.0

    def record_llm_usage(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        cost: float = 0.0,
        request_type: str = "unknown",
    ) -> bool:
        """Record LLM usage

        Args:
            model: LLM model name
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            total_tokens: Total number of tokens
            cost: Usage cost
            request_type: Request type

        Returns:
            bool: Whether recording was successful
        """
        try:
            insert_query = """
            INSERT INTO llm_token_usage
            (timestamp, model, prompt_tokens, completion_tokens, total_tokens, cost, request_type)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """

            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    insert_query,
                    (
                        datetime.now().isoformat(),
                        model,
                        prompt_tokens,
                        completion_tokens,
                        total_tokens,
                        cost,
                        request_type,
                    ),
                )
                conn.commit()

            logger.info(
                f"LLM usage recorded successfully: {model} - {total_tokens} tokens - ${cost:.6f}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to record LLM usage: {e}", exc_info=True)
            return False

    def get_usage_summary(self) -> UsageStatsSummary:
        """Get overall usage summary

        Returns:
            UsageStatsSummary: Usage summary data
        """
        try:
            # Get activity statistics
            activity_count_results = self.db.execute_query(
                "SELECT COUNT(*) as count FROM activities"
            )
            activities_total = (
                activity_count_results[0]["count"] if activity_count_results else 0
            )

            # Get task statistics
            task_stats_query = """
            SELECT
                COUNT(*) as total_tasks,
                COUNT(CASE WHEN status = 'done' THEN 1 END) as completed_tasks,
                COUNT(CASE WHEN status = 'todo' THEN 1 END) as pending_tasks
            FROM tasks
            """
            task_results = self.db.execute_query(task_stats_query)

            # Get LLM statistics (last 7 days)
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
                tasks_total=task_result.get("total_tasks", 0) or 0,
                tasks_completed=task_result.get("completed_tasks", 0) or 0,
                tasks_pending=task_result.get("pending_tasks", 0) or 0,
                llm_tokens_last_7_days=llm_result.get("tokens_last_7_days", 0) or 0,
                llm_calls_last_7_days=llm_result.get("calls_last_7_days", 0) or 0,
                llm_cost_last_7_days=llm_result.get("cost_last_7_days", 0.0) or 0.0,
            )

            logger.info("Usage summary retrieval completed")
            return summary

        except Exception as e:
            logger.error(f"Failed to get usage summary: {e}", exc_info=True)
            # Return default values
            return UsageStatsSummary(
                activities_total=0,
                tasks_total=0,
                tasks_completed=0,
                tasks_pending=0,
                llm_tokens_last_7_days=0,
                llm_calls_last_7_days=0,
                llm_cost_last_7_days=0.0,
            )

    def get_daily_llm_usage(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get daily LLM usage

        Args:
            days: Number of days to query, default 7 days

        Returns:
            List[Dict]: Daily usage data list
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
                daily_data.append(
                    {
                        "date": row["date"],
                        "model": row["model"],
                        "tokens": row["daily_tokens"] or 0,
                        "calls": row["daily_calls"] or 0,
                        "cost": row["daily_cost"] or 0.0,
                    }
                )

            return daily_data

        except Exception as e:
            logger.error(f"Failed to get daily LLM usage: {e}", exc_info=True)
            return []

    def get_model_usage_distribution(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get model usage distribution statistics

        Args:
            days: Number of days for statistics, default 30 days

        Returns:
            List[Dict]: Model usage distribution data
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
                model_data.append(
                    {
                        "model": row["model"],
                        "calls": row["calls"] or 0,
                        "total_tokens": row["total_tokens"] or 0,
                        "total_cost": row["total_cost"] or 0.0,
                        "avg_tokens_per_call": row["avg_tokens_per_call"] or 0.0,
                    }
                )

            return model_data

        except Exception as e:
            logger.error(f"Failed to get model usage distribution: {e}", exc_info=True)
            return []


# Global DashboardManager instance
_dashboard_manager: Optional[DashboardManager] = None


def get_dashboard_manager() -> DashboardManager:
    """Get global DashboardManager instance

    Returns:
        DashboardManager: Global dashboard manager instance
    """
    global _dashboard_manager

    if _dashboard_manager is None:
        _dashboard_manager = DashboardManager()

    return _dashboard_manager
