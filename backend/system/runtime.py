"""Backend runtime control utility

Provides startup, stop and status query logic for reuse between CLI and PyTauri.
"""

from __future__ import annotations

import asyncio
import atexit
import signal
import threading
from typing import Optional

from config.loader import get_config
from core.coordinator import PipelineCoordinator, get_coordinator
from core.db import get_db
from core.logger import get_logger

logger = get_logger(__name__)

# Global flags to prevent duplicate cleanup
_cleanup_done = False
_exit_handlers_registered = False


def _cleanup_on_exit():
    """Cleanup function on process exit (sync version for atexit)"""
    global _cleanup_done

    if _cleanup_done:
        return

    _cleanup_done = True
    logger.debug("Executing exit cleanup...")

    try:
        coordinator = get_coordinator()
        if not coordinator.is_running:
            logger.debug("Coordinator not running, skipping cleanup")
            return

        # Run async stop function in sync context
        try:
            # Try to get current event loop
            loop = asyncio.get_event_loop()

            # Event loop is running, use new thread to execute cleanup
            logger.debug("Event loop is running, using new thread to execute cleanup")
            if loop.is_running():
                # Event loop is running, cannot use run_until_complete
                # Create new thread to run stop function
                logger.debug("Event loop is running, using new thread to execute cleanup")
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, coordinator.stop(quiet=True))
                    future.result(timeout=5.0)  # Wait at most 5 seconds
            else:
                # Event loop not running, use directly
                logger.debug("Using existing event loop to execute cleanup")
                loop.run_until_complete(coordinator.stop(quiet=True))

        except RuntimeError:
            # No event loop, create new one
            logger.debug("Creating new event loop to execute cleanup")
            asyncio.run(coordinator.stop(quiet=True))

        logger.debug("Exit cleanup completed")

    except Exception as e:
        logger.error(f"Exit cleanup failed: {e}", exc_info=True)


def _signal_handler(signum, frame):
    """Signal handler"""
    global _cleanup_done

    signal_name = signal.Signals(signum).name
    logger.debug(f"Received signal {signal_name}, preparing to exit...")

    # 执行清理
    _cleanup_on_exit()

    # Exit program
    import sys

    sys.exit(0)


def _is_main_thread() -> bool:
    """Check if current is main thread"""
    return threading.current_thread() is threading.main_thread()


def _register_exit_handlers():
    """Register exit handlers (thread-safe)"""
    global _exit_handlers_registered

    # Prevent duplicate registration
    if _exit_handlers_registered:
        logger.debug("Exit handlers already registered, skipping")
        return

    # Register atexit cleanup function (thread-safe)
    atexit.register(_cleanup_on_exit)
    logger.debug("atexit cleanup function registered")

    # Only register signal handlers in main thread
    if _is_main_thread():
        try:
            signal.signal(signal.SIGINT, _signal_handler)  # Ctrl+C
            signal.signal(signal.SIGTERM, _signal_handler)  # kill command
            logger.debug("Signal handlers registered (main thread)")
        except ValueError as e:
            logger.warning(f"Cannot register signal handlers: {e}")
    else:
        logger.debug("Current thread is not main, skipping signal handler registration (will use atexit)")

    _exit_handlers_registered = True


async def start_runtime(config_file: Optional[str] = None) -> PipelineCoordinator:
    """Start backend monitoring process, returns coordinator instance if already running."""

    # Load config file (auto-create default config if not exists)
    config_loader = get_config(config_file)
    config_loader.load()
    logger.debug(f"✓ Config file: {config_loader.config_file}")

    # Initialize database (using database.path from config.toml)
    db = get_db()

    # Initialize Settings manager (database persistence, TOML as fallback)
    from core.db import switch_database
    from core.settings import get_settings, init_settings

    init_settings(config_loader, db)

    # Check if different database path is configured in config.toml, switch if so
    settings = get_settings()
    try:
        from processing.image_manager import get_image_manager

        image_manager = get_image_manager()
        image_manager.update_storage_path(settings.get_screenshot_path())
    except Exception as exc:
        logger.warning(f"Failed to sync screenshot storage directory: {exc}")

    configured_db_path = settings.get_database_path()
    current_db_path = db.db_path

    if configured_db_path and str(configured_db_path) != str(current_db_path):
        logger.debug(f"Detected configured database path: {configured_db_path}")
        if switch_database(configured_db_path):
            logger.debug("✓ Switched to configured database path")
            # Update reference
            db = get_db()
        else:
            logger.warning(f"✗ Failed to switch to configured database path, continuing with: {current_db_path}")

    # Register exit handlers (only once)
    _register_exit_handlers()

    coordinator = get_coordinator()
    if coordinator.is_running:
        logger.debug("Pipeline coordinator is already running, no need to start again")
        return coordinator

    logger.info("Starting pipeline coordinator...")
    try:
        await coordinator.start()
    except RuntimeError as exc:
        logger.error(f"Failed to start pipeline coordinator: {exc}")
        raise

    if coordinator.is_running:
        logger.info("Pipeline coordinator started successfully")
    else:
        if coordinator.mode == "requires_model":
            logger.warning("Pipeline coordinator is in restricted mode (no active LLM model configuration detected)")
            if coordinator.last_error:
                logger.warning(coordinator.last_error)
        elif coordinator.mode == "error" and coordinator.last_error:
            logger.error(f"Pipeline coordinator entered error state after startup: {coordinator.last_error}")
        else:
            logger.debug(f"Pipeline coordinator current status: {coordinator.mode}")

    # Initialize friendly chat service
    try:
        from services.friendly_chat_service import init_friendly_chat_service

        await init_friendly_chat_service()
        logger.info("✓ Friendly chat service initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize friendly chat service: {e}")

    return coordinator


async def stop_runtime(*, quiet: bool = False) -> PipelineCoordinator:
    """Stop backend monitoring process, returns directly if not running.

    Args:
        quiet: When True, only log debug messages, avoid terminal shutdown messages.
    """

    coordinator = get_coordinator()
    if not coordinator.is_running:
        if not quiet:
            logger.info("Pipeline coordinator is not currently running")
        return coordinator

    if not quiet:
        logger.info("Stopping pipeline coordinator...")

    # Stop friendly chat service first
    try:
        from services.friendly_chat_service import get_friendly_chat_service

        chat_service = get_friendly_chat_service()
        await chat_service.stop()
        if not quiet:
            logger.info("✓ Friendly chat service stopped")
    except Exception as e:
        if not quiet:
            logger.warning(f"Failed to stop friendly chat service: {e}")

    try:
        # Add timeout protection: wait at most 5 seconds to stop coordinator
        await asyncio.wait_for(coordinator.stop(quiet=quiet), timeout=5.0)
    except asyncio.TimeoutError:
        if not quiet:
            logger.warning("Pipeline coordinator stop timeout, forcing stop")
    except Exception as e:
        if not quiet:
            logger.error(f"Exception while stopping pipeline coordinator: {e}", exc_info=True)

    if not quiet:
        logger.info("Pipeline coordinator stopped")
    return coordinator


async def get_runtime_stats() -> dict:
    """Get current coordinator statistics."""

    coordinator = get_coordinator()
    return coordinator.get_stats()
