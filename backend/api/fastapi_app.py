"""
FastAPI application with automatic route registration
使用自动路由注册的 FastAPI 应用

This demonstrates how to use the universal @api_handler decorator
to automatically register routes in FastAPI.

Usage:
    uvicorn backend.api.fastapi_app:app --reload
"""

import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from handlers import register_fastapi_routes

# Create FastAPI application
app = FastAPI(
    title="Rewind API",
    description="Rewind Backend API with automatic route registration",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该设置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ⭐ Automatically register all API handlers as FastAPI routes
# 自动注册所有被 @api_handler 装饰的函数为 FastAPI 路由
register_fastapi_routes(app, prefix="/api")


# Additional custom routes (if needed)
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Rewind API Server",
        "version": "0.1.0",
        "docs": "/docs",
        "registered_routes": len(app.routes)
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
