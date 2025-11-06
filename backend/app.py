"""
FastAPI Application Entry Point
Rewind Backend API Server

Usage:
    # Development with auto-reload
    uvicorn app:app --reload

    # Production
    uvicorn app:app --host 0.0.0.0 --port 8000

    # With custom config
    uv run python app.py
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add backend directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from backend.config.loader import get_config
from backend.core.logger import get_logger
from backend.handlers import register_fastapi_routes

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI application lifecycle management"""
    logger.info("========== Rewind Backend Starting ==========")

    try:
        # Load configuration (auto-creates default config if not exists)
        config_loader = get_config()
        config_loader.load()
        logger.info(f"✓ Configuration loaded: {config_loader.config_file}")

        # Initialize database
        from backend.core.db import get_db
        db = get_db()
        logger.info("✓ Database initialized")

        # Initialize Settings manager (database-backed with TOML fallback)
        from backend.core.db import switch_database
        from backend.core.settings import get_settings, init_settings

        init_settings(config_loader, db)
        logger.info("✓ Settings manager initialized")

        # Check if there's a configured database path in config.toml and switch to it
        settings = get_settings()
        configured_db_path = settings.get_database_path()
        current_db_path = db.db_path

        if configured_db_path and str(configured_db_path) != str(current_db_path):
            logger.info(f"Detected configured database path: {configured_db_path}")
            if switch_database(configured_db_path):
                logger.info("✓ Switched to configured database path")
                # Update reference
                db = get_db()
            else:
                logger.warning(f"Failed to switch database, continuing with: {current_db_path}")

        # Initialize coordinator (but don't auto-start monitoring)
        from backend.core.coordinator import get_coordinator
        coordinator = get_coordinator()
        logger.info("✓ Pipeline coordinator initialized")

        logger.info("========== Rewind Backend Ready ==========")

    except Exception as e:
        logger.error(f"Failed to initialize backend: {e}", exc_info=True)
        raise

    yield

    # Shutdown: clean up resources
    logger.info("========== Rewind Backend Shutting Down ==========")
    try:
        from backend.core.coordinator import get_coordinator
        coordinator = get_coordinator()
        if coordinator.is_running:
            await coordinator.stop()
            logger.info("✓ Coordinator stopped")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}", exc_info=True)


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    app = FastAPI(
        title="Rewind Backend API",
        description="Intelligent user activity monitoring and analysis system",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, restrict to specific origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register API routes using the universal @api_handler decorator
    register_fastapi_routes(app, prefix="/api")

    # Health check endpoint
    @app.get("/")
    async def root():
        """Root endpoint with API information"""
        return {
            "service": "Rewind Backend API",
            "version": "1.0.0",
            "status": "running",
            "docs": "/docs",
            "redoc": "/redoc"
        }

    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        try:
            from backend.core.coordinator import get_coordinator
            coordinator = get_coordinator()
            return {
                "status": "healthy",
                "service": "rewind-backend",
                "coordinator_running": coordinator.is_running
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "service": "rewind-backend",
                "error": str(e)
            }

    logger.info("✓ FastAPI application created with routes")
    return app


# Create application instance
app = create_app()


if __name__ == "__main__":
    # Run with uvicorn when executed directly
    config = get_config()
    host = config.get('server.host', '0.0.0.0')
    port = config.get('server.port', 8000)
    debug = config.get('server.debug', False)

    logger.info(f"Starting server at http://{host}:{port}")

    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=debug,
        log_level="debug" if debug else "info"
    )
