"""
FastAPI standalone server for testing and development
This allows testing the backend API without the Tauri desktop wrapper
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.logger import get_logger

logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Rewind API",
    description="Backend API for Rewind desktop application",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Root endpoint
@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "ok",
        "message": "Rewind API Server",
        "version": "2.0.0"
    }


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


# Register all API routes from handlers
try:
    from backend.handlers import register_fastapi_routes
    register_fastapi_routes(app, prefix="/api")
    logger.info("FastAPI routes registered successfully")
except Exception as e:
    logger.error(f"Failed to register FastAPI routes: {e}", exc_info=True)
    raise


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting Rewind API server...")
    logger.info("API documentation available at: http://localhost:8000/docs")

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
