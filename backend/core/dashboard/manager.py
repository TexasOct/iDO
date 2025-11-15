"""
Dashboard Manager

Handles all dashboard-related business logic, including:
- LLM usage statistics queries
- Usage summary calculations
- Data aggregation and analysis
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from models.base import LLMUsageResponse

from ..db import get_db
from ..logger import get_logger
from ..protocols import DashboardDatabaseProtocol

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
        self.db: DashboardDatabaseProtocol = get_db()

    def get_llm_statistics(
        self,
        days: int = 30,
        model_filter: Optional[str] = None,
        model_config_id: Optional[str] = None,
        model_details: Optional[Dict[str, Any]] = None,
    ) -> LLMUsageResponse:
        """Get LLM usage statistics

        Args:
            days: Number of days for statistics, default 30 days
            model_filter: Optional model filter (filter statistics by model name) - DEPRECATED
            model_config_id: Optional model configuration ID (filter by specific config)
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

            # Prefer model_config_id over model_filter for more accurate filtering
            if model_config_id:
                where_clauses.append("model_config_id = ?")
                params.append(model_config_id)
            elif model_filter:
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

            # Use model_config_id as filter condition (filter by configuration ID, not model name)
            # This allows different configurations using the same model to have separate statistics
            stats = self.get_llm_statistics(
                days=days, model_config_id=model_id, model_details=model_details
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
        model_config_id: Optional[str] = None,
    ) -> bool:
        """Record LLM usage

        Args:
            model: LLM model name
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            total_tokens: Total number of tokens
            cost: Usage cost
            request_type: Request type
            model_config_id: Model configuration ID (optional, for filtering by config)

        Returns:
            bool: Whether recording was successful
        """
        try:
            insert_query = """
            INSERT INTO llm_token_usage
            (timestamp, model, model_config_id, prompt_tokens, completion_tokens, total_tokens, cost, request_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """

            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    insert_query,
                    (
                        datetime.now().isoformat(),
                        model,
                        model_config_id,
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

    def record_llm_request(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: Optional[int] = None,
        cost: float = 0.0,
        request_type: str = "unknown",
    ) -> bool:
        """Convenience wrapper used by services to track token usage."""
        calculated_total = total_tokens
        if calculated_total is None:
            calculated_total = (prompt_tokens or 0) + (completion_tokens or 0)
        return self.record_llm_usage(
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=calculated_total,
            cost=cost,
            request_type=request_type,
        )

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

    def get_llm_usage_trend(
        self,
        dimension: str = "day",
        days: int = 30,
        model_config_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Get LLM usage trend data with configurable time dimension

        Args:
            dimension: Time dimension ('day', 'week', 'month', 'custom')
            days: Number of days to query when start/end are not provided
            model_config_id: Optional model configuration ID filter
            start_date: Optional explicit range start
            end_date: Optional explicit range end

        Returns:
            List of trend data points with date, tokens, calls, and cost
        """
        try:
            def _strip_timezone(value: Optional[datetime]) -> Optional[datetime]:
                if value is None:
                    return None
                if value.tzinfo:
                    return value.astimezone(timezone.utc).replace(tzinfo=None)
                return value

            # Normalize time range (default to trailing N days when range not provided)
            range_end = _strip_timezone(end_date) or datetime.now()
            range_start = _strip_timezone(start_date) or (range_end - timedelta(days=days))

            if range_start > range_end:
                range_start, range_end = range_end, range_start

            # Snap to appropriate boundaries
            if dimension == "day":
                range_start = range_start.replace(hour=0, minute=0, second=0, microsecond=0)
                range_end = range_end.replace(hour=23, minute=59, second=59, microsecond=999999)
            else:
                range_start = range_start.replace(hour=0, minute=0, second=0, microsecond=0)
                range_end = range_end.replace(hour=23, minute=59, second=59, microsecond=999999)

            # Build query conditions
            where_clauses = ["timestamp >= ?", "timestamp <= ?"]
            params: List[Any] = [range_start.isoformat(), range_end.isoformat()]

            if model_config_id:
                where_clauses.append("model_config_id = ?")
                params.append(model_config_id)

            where_sql = " AND ".join(where_clauses)

            # Determine bucket strategy
            if dimension == "day":
                bucket_duration = timedelta(hours=1)
                bucket_expression = "strftime('%Y-%m-%d %H:00:00', timestamp)"
                bucket_key_format = "%Y-%m-%d %H:00:00"
            elif dimension == "week":
                bucket_duration = timedelta(days=1)
                bucket_expression = "DATE(timestamp)"
                bucket_key_format = "%Y-%m-%d"
            else:
                bucket_duration = timedelta(days=1)
                bucket_expression = "DATE(timestamp)"
                bucket_key_format = "%Y-%m-%d"

            def align_start(value: datetime) -> datetime:
                aligned = value.replace(minute=0, second=0, microsecond=0)
                if dimension in ("month", "custom", "week", "day"):
                    aligned = aligned.replace(hour=0)
                return aligned

            def align_end(value: datetime) -> datetime:
                aligned = value.replace(minute=0, second=0, microsecond=0)
                if dimension == "day":
                    aligned = aligned.replace(hour=aligned.hour)
                    return aligned + timedelta(hours=1)
                if dimension == "week":
                    aligned = aligned.replace(hour=0)
                    return aligned + timedelta(days=1)
                aligned = aligned.replace(hour=0)
                return aligned + timedelta(days=1)

            bucket_start = align_start(range_start)
            bucket_end_exclusive = align_end(range_end)
            if bucket_end_exclusive <= bucket_start:
                bucket_end_exclusive = bucket_start + bucket_duration

            # Query aggregated data
            query = f"""
            SELECT
                {bucket_expression} as bucket_start,
                SUM(total_tokens) as tokens,
                SUM(prompt_tokens) as prompt_tokens,
                SUM(completion_tokens) as completion_tokens,
                COUNT(*) as calls,
                SUM(cost) as cost
            FROM llm_token_usage
            WHERE {where_sql}
            GROUP BY bucket_start
            ORDER BY bucket_start ASC
            """

            results = self.db.execute_query(query, tuple(params))

            aggregated = {row["bucket_start"]: row for row in results}

            def make_bucket_entry(start_ts: datetime, row: Optional[Dict[str, Any]]) -> Dict[str, Any]:
                end_ts = start_ts + bucket_duration
                return {
                    "date": start_ts.strftime(bucket_key_format),
                    "bucketStart": start_ts.isoformat(),
                    "bucketEnd": end_ts.isoformat(),
                    "tokens": int((row or {}).get("tokens") or 0),
                    "promptTokens": int((row or {}).get("prompt_tokens") or 0),
                    "completionTokens": int((row or {}).get("completion_tokens") or 0),
                    "calls": int((row or {}).get("calls") or 0),
                    "cost": float((row or {}).get("cost") or 0.0),
                }

            trend_data: List[Dict[str, Any]] = []
            cursor = bucket_start
            while cursor < bucket_end_exclusive:
                bucket_key = cursor.strftime(bucket_key_format)
                row = aggregated.get(bucket_key)
                trend_data.append(make_bucket_entry(cursor, row))
                cursor += bucket_duration

            logger.info(
                f"LLM usage trend retrieval completed: {len(trend_data)} data points, dimension={dimension}"
            )
            return trend_data

        except Exception as e:
            logger.error(f"Failed to get LLM usage trend: {e}", exc_info=True)
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
