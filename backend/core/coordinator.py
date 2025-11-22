"""
Backend pipeline coordinator
Responsible for coordinating the complete lifecycle of PerceptionManager and ProcessingPipeline
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from config.loader import get_config
from core.db import get_db
from core.logger import get_logger

logger = get_logger(__name__)

# Global coordinator instance
_coordinator: Optional["PipelineCoordinator"] = None


class PipelineCoordinator:
    """Pipeline coordinator"""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize coordinator

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.processing_interval = config.get("monitoring.processing_interval", 30)
        self.window_size = config.get("monitoring.window_size", 60)
        self.capture_interval = config.get("monitoring.capture_interval", 0.2)

        # Initialize managers (lazy import to avoid circular dependencies)
        self.perception_manager = None
        self.processing_pipeline = None

        # Running state
        self.is_running = False
        self.processing_task: Optional[asyncio.Task] = None
        self.mode: str = (
            "stopped"  # running | stopped | requires_model | error | starting
        )
        self.last_error: Optional[str] = None
        self.active_model: Optional[Dict[str, Any]] = None

        # Statistics
        self.stats: Dict[str, Any] = {
            "start_time": None,
            "total_processing_cycles": 0,
            "last_processing_time": None,
            "perception_stats": {},
            "processing_stats": {},
        }
        self._last_processed_timestamp: Optional[datetime] = None

    def _set_state(self, *, mode: str, error: Optional[str] = None) -> None:
        """Update coordinator state fields"""
        self.mode = mode
        self.last_error = error
        if error:
            logger.debug("Coordinator state updated: mode=%s, error=%s", mode, error)
        else:
            logger.debug("Coordinator state updated: mode=%s", mode)

    def _sanitize_active_model(self, model: Dict[str, Any]) -> Dict[str, Any]:
        """Build active model information for frontend display, remove sensitive fields"""
        sanitized = {
            "id": model.get("id"),
            "name": model.get("name") or model.get("model"),
            "provider": model.get("provider"),
            "model": model.get("model"),
            "last_test_status": bool(model.get("last_test_status")),
            "last_tested_at": model.get("last_tested_at"),
            "last_test_error": model.get("last_test_error"),
            "updated_at": model.get("updated_at"),
        }
        return sanitized

    def _refresh_active_model(self) -> None:
        """Refresh current active model information, keep state synchronized with database"""
        try:
            db = get_db()
            active_model = db.models.get_active()
            if active_model:
                sanitized = self._sanitize_active_model(active_model)
                self.active_model = sanitized
                if not sanitized.get("last_test_status"):
                    message = (
                        sanitized.get("last_test_error")
                        or "Active model has not passed API test, please click test button in model management first."
                    )
                    if self.mode != "requires_model" or self.last_error != message:
                        self._set_state(mode="requires_model", error=message)
            else:
                self.active_model = None
        except Exception as exc:
            logger.debug("Failed to refresh active model information: %s", exc)

    def _ensure_active_model(self) -> Optional[Dict[str, Any]]:
        """Ensure active LLM model configuration exists, return None if missing"""
        try:
            db = get_db()
            active_model = db.models.get_active()
            if not active_model:
                message = "No active LLM model configuration detected, please add and activate model in settings."
                self._set_state(mode="requires_model", error=message)
                self.active_model = None
                logger.warning(message)
                return None
            required_fields = ["api_key", "api_url", "model"]
            missing = [
                field for field in required_fields if not active_model.get(field)
            ]
            if missing:
                message = f"Active model configuration missing required fields: {', '.join(missing)}, please complete in settings and restart."
                self._set_state(mode="requires_model", error=message)
                self.active_model = None
                logger.warning(message)
                return None

            sanitized = self._sanitize_active_model(active_model)
            self.active_model = sanitized

            # If model has not passed test, only log warning but still allow system to start
            if not sanitized.get("last_test_status"):
                message = (
                    sanitized.get("last_test_error")
                    or "Active model has not passed connectivity test, please click test button in model management to verify configuration."
                )
                logger.warning(message)
                # Note: No longer set to requires_model mode, allow system to continue starting

            return active_model
        except Exception as exc:
            message = f"Unable to read active LLM model configuration: {exc}"
            logger.error(message)
            self._set_state(mode="error", error=message)
            self.active_model = None
            return None

    def _init_managers(self):
        """Lazy initialization of managers"""
        if self.perception_manager is None:
            from perception.manager import PerceptionManager

            self.perception_manager = PerceptionManager(
                capture_interval=self.capture_interval, window_size=self.window_size
            )

        if self.processing_pipeline is None:
            from processing.pipeline import ProcessingPipeline

            processing_config = self.config.get("processing", {})
            language_config = self.config.get("language", {})
            self.processing_pipeline = ProcessingPipeline(
                screenshot_threshold=processing_config.get(
                    "event_extraction_threshold", 20
                ),
                activity_summary_interval=processing_config.get(
                    "activity_summary_interval", 600
                ),
                knowledge_merge_interval=processing_config.get(
                    "knowledge_merge_interval", 1200
                ),
                todo_merge_interval=processing_config.get("todo_merge_interval", 1200),
                language=language_config.get("default_language", "zh"),
                enable_screenshot_deduplication=processing_config.get(
                    "enable_screenshot_deduplication", True
                ),
                screenshot_similarity_threshold=processing_config.get(
                    "screenshot_similarity_threshold", 0.90
                ),
                screenshot_hash_cache_size=processing_config.get(
                    "screenshot_hash_cache_size", 10
                ),
                screenshot_hash_algorithms=processing_config.get(
                    "screenshot_hash_algorithms", None
                ),
                enable_adaptive_threshold=processing_config.get(
                    "enable_adaptive_threshold", True
                ),
            )

    def ensure_managers_initialized(self):
        """Exposed initialization entry point"""
        self._init_managers()

    async def start(self) -> None:
        """Start the entire pipeline"""
        if self.is_running:
            logger.warning("Coordinator is already running")
            return

        try:
            self._set_state(mode="starting", error=None)
            logger.info("Starting pipeline coordinator...")

            # Initialize managers
            active_model = self._ensure_active_model()
            if not active_model:
                # Keep limited mode when no model available, don't throw exception, allow frontend to continue rendering
                logger.warning(
                    "Pipeline coordinator not started: missing valid LLM model configuration"
                )
                self.is_running = False
                self.processing_task = None
                self.stats["start_time"] = None
                self.stats["last_processing_time"] = None
                return

            logger.info(
                "Detected active model configuration: %s (%s)",
                active_model.get("name") or active_model.get("model"),
                active_model.get("provider"),
            )
            self._init_managers()

            if not self.perception_manager:
                logger.error("Perception manager initialization failed")
                raise Exception("Perception manager initialization failed")

            if not self.processing_pipeline:
                logger.error("Processing pipeline initialization failed")
                raise Exception("Processing pipeline initialization failed")

            # Start perception manager and processing pipeline in parallel (they are independent)
            logger.debug(
                "Starting perception manager and processing pipeline in parallel..."
            )
            start_time = datetime.now()

            await asyncio.gather(
                self.perception_manager.start(), self.processing_pipeline.start()
            )

            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(
                f"Perception manager and processing pipeline started (took {elapsed:.2f}s)"
            )

            # Start scheduled processing loop
            self.is_running = True
            self._set_state(mode="running", error=None)
            self.processing_task = asyncio.create_task(self._processing_loop())
            self.stats["start_time"] = datetime.now()

            logger.info(
                f"Pipeline coordinator started, processing interval: {self.processing_interval} seconds"
            )

        except Exception as e:
            logger.error(f"Failed to start coordinator: {e}")
            await self.stop()
            raise

    async def stop(self, *, quiet: bool = False) -> None:
        """Stop the entire pipeline

        Args:
            quiet: When True, only log debug messages, avoid shutdown prompts in terminal.
        """
        if not self.is_running:
            self._set_state(mode="stopped", error=None)
            self.processing_task = None
            return

        try:
            log = logger.debug if quiet else logger.info
            log("Stopping pipeline coordinator...")

            # Stop scheduled processing loop
            self.is_running = False
            if self.processing_task and not self.processing_task.done():
                self.processing_task.cancel()
                try:
                    await self.processing_task
                except asyncio.CancelledError:
                    pass
            self.processing_task = None

            # Stop processing pipeline
            if self.processing_pipeline:
                await self.processing_pipeline.stop()
                log("Processing pipeline stopped")

            # Stop perception manager
            if self.perception_manager:
                await self.perception_manager.stop()
                log("Perception manager stopped")

            log("Pipeline coordinator stopped")

        except Exception as e:
            logger.error(f"Failed to stop coordinator: {e}")
        finally:
            self._set_state(mode="stopped", error=None)
            self.is_running = False
            self.processing_task = None
            self._last_processed_timestamp = None

    async def _processing_loop(self) -> None:
        """Scheduled processing loop"""
        try:
            # First iteration has shorter delay, then use normal interval
            first_iteration = True

            while self.is_running:
                # First iteration starts quickly (100ms), then use configured interval
                wait_time = 0.1 if first_iteration else self.processing_interval
                await asyncio.sleep(wait_time)

                if not self.is_running:
                    break

                first_iteration = False

                if not self.perception_manager:
                    logger.error("Perception manager not initialized")
                    raise Exception("Perception manager not initialized")

                if not self.processing_pipeline:
                    logger.error("Processing pipeline not initialized")
                    raise Exception("Processing pipeline not initialized")

                # Fetch records newer than the last processed timestamp to avoid duplicates
                end_time = datetime.now()
                if self._last_processed_timestamp is None:
                    start_time = end_time - timedelta(seconds=self.processing_interval)
                else:
                    start_time = self._last_processed_timestamp

                records = self.perception_manager.get_records_in_timeframe(
                    start_time, end_time
                )

                if self._last_processed_timestamp is not None:
                    records = [
                        record
                        for record in records
                        if record.timestamp > self._last_processed_timestamp
                    ]

                if records:
                    logger.debug(f"Starting to process {len(records)} records")

                    # Process records
                    result = await self.processing_pipeline.process_raw_records(records)

                    # Update last processed timestamp so future cycles skip these records
                    latest_record_time = max(
                        (record.timestamp for record in records), default=None
                    )
                    if latest_record_time:
                        self._last_processed_timestamp = latest_record_time

                    # Update statistics
                    self.stats["total_processing_cycles"] += 1
                    self.stats["last_processing_time"] = datetime.now()

                    logger.debug(
                        f"Processing completed: {len(result.get('events', []))} events, {len(result.get('activities', []))} activities"
                    )
                else:
                    logger.debug("No new records to process")

        except asyncio.CancelledError:
            logger.debug("Processing loop cancelled")
        except Exception as e:
            logger.error(f"Processing loop failed: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get coordinator statistics"""
        try:
            self._refresh_active_model()
            # Get statistics for each component
            perception_stats = {}
            processing_stats = {}

            if self.perception_manager:
                perception_stats = self.perception_manager.get_stats()

            if self.processing_pipeline:
                processing_stats = self.processing_pipeline.get_stats()

            # Merge statistics
            stats = {
                "coordinator": {
                    "is_running": self.is_running,
                    "status": self.mode,
                    "last_error": self.last_error,
                    "active_model": self.active_model,
                    "processing_interval": self.processing_interval,
                    "window_size": self.window_size,
                    "capture_interval": self.capture_interval,
                    "start_time": self.stats["start_time"].isoformat()
                    if self.stats["start_time"]
                    else None,
                    "total_processing_cycles": self.stats["total_processing_cycles"],
                    "last_processing_time": self.stats[
                        "last_processing_time"
                    ].isoformat()
                    if self.stats["last_processing_time"]
                    else None,
                },
                "perception": perception_stats,
                "processing": processing_stats,
            }

            return stats

        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {"error": str(e)}


def get_coordinator() -> PipelineCoordinator:
    """Get global coordinator singleton"""
    global _coordinator
    if _coordinator is None:
        config = get_config().load()

        _coordinator = PipelineCoordinator(config)
    return _coordinator
