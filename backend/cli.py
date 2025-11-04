"""
Rewind Backend CLI Interface
Command line interface implemented using Typer
"""

import typer
from typing import Optional
import uvicorn

from config.loader import load_config
from core.logger import get_logger
from system.runtime import start_runtime, stop_runtime

logger = get_logger(__name__)


def start(
    host: str = typer.Option("0.0.0.0", help="Server host address"),
    port: int = typer.Option(8000, help="Server port"),
    config_file: Optional[str] = typer.Option(None, help="Configuration file path"),
    debug: bool = typer.Option(False, help="Enable debug mode"),
):
    """Start Rewind Backend service"""
    try:
        # Load configuration
        config = load_config(config_file)

        logger.info(f"Starting Rewind Backend service...")
        logger.info(f"Host: {host}, Port: {port}")
        logger.info(f"Debug mode: {debug}")

        # Start FastAPI service
        uvicorn.run(
            "api.server:app",
            host=host,
            port=port,
            reload=debug,
            log_level="debug" if debug else "info",
        )

    except Exception as e:
        logger.error(f"Failed to start service: {e}")
        raise typer.Exit(1)


def init_db():
    """Initialize database"""
    logger.info("Initializing database...")
    # TODO: Implement database initialization logic
    pass


def test():
    """Run tests"""
    logger.info("Running tests...")
    # TODO: Implement test running logic
    pass


def run(
    config_file: Optional[str] = typer.Option(None, help="Configuration file path"),
):
    """Run backend monitoring pipeline (terminal mode only)"""
    import asyncio
    import signal

    async def run_pipeline():
        try:
            # Start coordinator
            await start_runtime(config_file)
            logger.info("Monitoring pipeline started, press Ctrl+C to stop")

            # Wait for stop signal
            stop_event = asyncio.Event()

            def signal_handler(sig, frame):
                logger.info("Stop signal received...")
                stop_event.set()

            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)

            # Block and wait
            await stop_event.wait()

            # Stop coordinator
            await stop_runtime(quiet=True)
            logger.info("Monitoring pipeline stopped")

        except Exception as e:
            logger.error(f"Run failed: {e}")
            raise typer.Exit(1)

    # Run async task
    asyncio.run(run_pipeline())


def main():
    """Main function"""
    app = typer.Typer()

    app.command()(start)  # Start FastAPI server
    app.command()(run)  # Run in terminal mode
    app.command()(init_db)  # Initialize database

    app()


if __name__ == "__main__":
    main()
