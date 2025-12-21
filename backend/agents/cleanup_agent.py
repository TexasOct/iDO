"""
CleanupAgent - Periodic cleanup of soft-deleted records and orphaned images

Automatically cleans up:
- Soft-deleted records older than configured retention period
- Orphaned screenshot images not referenced by any action
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from core.db import get_db
from core.logger import get_logger
from perception.image_manager import ImageManager

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
        image_manager: Optional[ImageManager] = None,
        image_cleanup_safety_window_minutes: int = 30,
    ):
        """
        Initialize CleanupAgent

        Args:
            cleanup_interval: How often to run cleanup (seconds, default 24h)
            retention_days: Days to keep soft-deleted records (default 30)
            image_manager: Image manager instance for cleaning orphaned images
            image_cleanup_safety_window_minutes: Safety window for image cleanup (default 30)
        """
        self.cleanup_interval = cleanup_interval
        self.retention_days = retention_days
        self.image_manager = image_manager
        self.image_cleanup_safety_window_minutes = image_cleanup_safety_window_minutes

        # Initialize components
        self.db = get_db()

        # Running state
        self.is_running = False
        self.is_paused = False
        self.cleanup_task: Optional[asyncio.Task] = None

        # Statistics
        self.stats: Dict[str, Any] = {
            "total_cleanups": 0,
            "last_cleanup_time": None,
            "last_cleanup_counts": {},
            "total_orphaned_images_cleaned": 0,
            "last_orphaned_images_count": 0,
        }

        logger.debug(
            f"CleanupAgent initialized (interval: {cleanup_interval}s, "
            f"retention: {retention_days} days, "
            f"image_cleanup_safety_window: {image_cleanup_safety_window_minutes}min)"
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
        self.is_paused = False

        # Cancel cleanup task
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass

        logger.info("CleanupAgent stopped")

    def pause(self):
        """Pause the cleanup agent (system sleep)"""
        if not self.is_running:
            return

        self.is_paused = True
        logger.debug("CleanupAgent paused")

    def resume(self):
        """Resume the cleanup agent (system wake)"""
        if not self.is_running:
            return

        self.is_paused = False
        logger.debug("CleanupAgent resumed")

    async def _periodic_cleanup(self):
        """Scheduled task: cleanup soft-deleted records periodically"""
        while self.is_running:
            try:
                await asyncio.sleep(self.cleanup_interval)

                # Skip processing if paused (system sleep)
                if self.is_paused:
                    logger.debug("CleanupAgent paused, skipping cleanup")
                    continue

                await self._cleanup_old_data()
            except asyncio.CancelledError:
                logger.debug("Cleanup task cancelled")
                break
            except Exception as e:
                logger.error(f"Cleanup task exception: {e}", exc_info=True)

    async def _cleanup_old_data(self):
        """Clean up old soft-deleted records and orphaned images"""
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

            # Clean up orphaned images
            if self.image_manager:
                logger.info("Starting cleanup of orphaned screenshot images")
                try:
                    # Get function to retrieve referenced hashes
                    def get_referenced_hashes():
                        return self.db.actions.get_all_referenced_image_hashes()

                    # Clean up orphaned images
                    cleaned_images = self.image_manager.cleanup_orphaned_images(
                        get_referenced_hashes,
                        safety_window_minutes=self.image_cleanup_safety_window_minutes
                    )

                    # Update statistics
                    self.stats["total_orphaned_images_cleaned"] += cleaned_images
                    self.stats["last_orphaned_images_count"] = cleaned_images

                    if cleaned_images > 0:
                        logger.info(
                            f"Orphaned image cleanup completed: {cleaned_images} images removed"
                        )
                except Exception as e:
                    logger.error(f"Failed to cleanup orphaned images: {e}", exc_info=True)

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
