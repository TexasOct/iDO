"""
FastAPI 服务器
初始化 FastAPI 应用，加载路由与 WebSocket
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from core.logger import get_logger
from config.loader import load_config
from .websocket import websocket_router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info("Rewind Backend 服务启动中...")
    
    # 加载配置
    config = load_config()
    logger.info("配置加载完成")
    
    # TODO: 初始化数据库
    # TODO: 启动监控服务
    # TODO: 启动处理管道
    
    yield
    
    # 关闭时执行
    logger.info("Rewind Backend 服务关闭中...")
    # TODO: 清理资源


def create_app() -> FastAPI:
    """创建 FastAPI 应用"""
    app = FastAPI(
        title="Rewind Backend API",
        description="智能用户行为监控和分析系统后端 API",
        version="1.0.0",
        lifespan=lifespan
    )
    
    # 添加 CORS 中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 生产环境应该限制具体域名
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 注册路由
    register_routes(app)
    
    # 注册 WebSocket 路由
    app.include_router(websocket_router)
    
    return app


def register_routes(app: FastAPI):
    """注册所有路由"""
    # 导入并注册各个模块的路由
    from .routes import perception, processing
    # TODO: 导入其他路由模块
    # from .routes import events, activities, tasks, agents, system
    
    # 注册路由
    app.include_router(perception.router)
    app.include_router(processing.router)
    
    # 基础健康检查路由
    @app.get("/")
    async def root():
        return {"message": "Rewind Backend API", "status": "running"}
    
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": "rewind-backend"}
    
    logger.info("路由注册完成")


# 创建应用实例
app = create_app()


if __name__ == "__main__":
    # 直接运行时的配置
    config = load_config()
    host = config.get('server.host', '0.0.0.0')
    port = config.get('server.port', 8000)
    debug = config.get('server.debug', False)
    
    uvicorn.run(
        "api.server:app",
        host=host,
        port=port,
        reload=debug,
        log_level="debug" if debug else "info"
    )
