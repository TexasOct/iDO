"""
CleanupAgent - Periodic cleanup of soft-deleted records

Automatically cleans up soft-deleted records older than configured retention period
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from core.db import get_db
from core.logger import get_logger

logger = get_logger(__name__)


class CleanupAgent:
    """
    Cleanup agent for soft-deleted records

    Responsibilities:
    - Periodically clean up old soft-deleted records
    - Maintain database hygiene
    """

    def __init__(
        self,
        cleanup_interval: int = 86400,  # 24 hours in seconds
        retention_days: int = 30,  # Keep soft-deleted records for 30 days
    ):
        """
        Initialize CleanupAgent

        Args:
            cleanup_interval: How often to run cleanup (seconds, default 24h)
            retention_days: Days to keep soft-deleted records (default 30)
        """
        self.cleanup_interval = cleanup_interval
        self.retention_days = retention_days

        # Initialize components
        self.db = get_db()

        # Running state
        self.is_running = False
        self.cleanup_task: Optional[asyncio.Task] = None

        # Statistics
        self.stats: Dict[str, Any] = {
            "total_cleanups": 0,
            "last_cleanup_time": None,
            "last_cleanup_counts": {},
        }

        logger.debug(
            f"CleanupAgent initialized (interval: {cleanup_interval}s, "
            f"retention: {retention_days} days)"
        )

    async def start(self):
        """Start the cleanup agent"""
        if self.is_running:
            logger.warning("CleanupAgent is already running")
            return

        self.is_running = True

        # Start cleanup task
        self.cleanup_task = asyncio.create_task(self._periodic_cleanup())

        logger.info(
            f"CleanupAgent started (cleanup every {self.cleanup_interval}s, "
            f"retain {self.retention_days} days)"
        )

    async def stop(self):
        """Stop the cleanup agent"""
        if not self.is_running:
            return

        self.is_running = False

        # Cancel cleanup task
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass

        logger.info("CleanupAgent stopped")

    async def _periodic_cleanup(self):
        """Scheduled task: cleanup soft-deleted records periodically"""
        while self.is_running:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._cleanup_old_data()
            except asyncio.CancelledError:
                logger.debug("Cleanup task cancelled")
                break
            except Exception as e:
                logger.error(f"Cleanup task exception: {e}", exc_info=True)

    async def _cleanup_old_data(self):
        """Clean up old soft-deleted records"""
        try:
            cutoff = datetime.now() - timedelta(days=self.retention_days)
            cutoff_iso = cutoff.isoformat()
            cutoff_date = cutoff.strftime("%Y-%m-%d")

            logger.info(
                f"Starting cleanup of soft-deleted records older than {cutoff_date}"
            )

            # Use the database's delete_old_data method
            result = await self.db.delete_old_data(cutoff_iso, cutoff_date)

            # Update statistics
            self.stats["total_cleanups"] += 1
            self.stats["last_cleanup_time"] = datetime.now().isoformat()
            self.stats["last_cleanup_counts"] = result

            total_cleaned = sum(result.values())
            logger.info(
                f"Cleanup completed: {total_cleaned} records soft-deleted. "
                f"Details: {result}"
            )

        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}", exc_info=True)

    def get_stats(self) -> Dict[str, Any]:
        """Get cleanup statistics"""
        return {
            **self.stats,
            "is_running": self.is_running,
            "cleanup_interval": self.cleanup_interval,
            "retention_days": self.retention_days,
        }
