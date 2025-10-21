"""
Rewind Backend CLI 接口
使用 Typer 实现命令行界面
"""

import typer
from typing import Optional
import uvicorn
from config.loader import load_config
from core.logger import get_logger
logger = get_logger(__name__)


def start(
    host: str = typer.Option("0.0.0.0", help="服务器主机地址"),
    port: int = typer.Option(8000, help="服务器端口"),
    config_file: Optional[str] = typer.Option(None, help="配置文件路径"),
    debug: bool = typer.Option(False, help="启用调试模式")
):
    """启动 Rewind Backend 服务"""
    try:
        # 加载配置
        config = load_config(config_file)
        
        logger.info(f"正在启动 Rewind Backend 服务...")
        logger.info(f"主机: {host}, 端口: {port}")
        logger.info(f"调试模式: {debug}")
        
        # 启动 FastAPI 服务
        uvicorn.run(
            "api.server:app",
            host=host,
            port=port,
            reload=debug,
            log_level="debug" if debug else "info"
        )
        
    except Exception as e:
        logger.error(f"启动服务失败: {e}")
        raise typer.Exit(1)


def init_db():
    """初始化数据库"""
    logger.info("初始化数据库...")
    # TODO: 实现数据库初始化逻辑
    pass


def test():
    """运行测试"""
    logger.info("运行测试...")
    # TODO: 实现测试运行逻辑
    pass


def run(
    config_file: Optional[str] = typer.Option(None, help="配置文件路径"),
):
    """运行后端监听流程（纯终端模式）"""
    import asyncio
    import signal
    
    async def run_pipeline():
        try:
            # 加载配置
            config = load_config(config_file)
            logger.info("配置加载完成")
            
            # 初始化数据库
            from core.db import get_db
            get_db()
            logger.info("数据库初始化完成")
            
            # 获取协调器
            from core.coordinator import get_coordinator
            coordinator = get_coordinator()
            
            # 启动协调器
            logger.info("正在启动监听流程...")
            await coordinator.start()
            logger.info("监听流程已启动，按 Ctrl+C 停止")
            
            # 等待停止信号
            stop_event = asyncio.Event()
            
            def signal_handler(sig, frame):
                logger.info("收到停止信号...")
                stop_event.set()
            
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
            
            # 阻塞等待
            await stop_event.wait()
            
            # 停止协调器
            logger.info("正在停止监听流程...")
            await coordinator.stop()
            logger.info("监听流程已停止")
            
        except Exception as e:
            logger.error(f"运行失败: {e}")
            raise typer.Exit(1)
    
    # 运行异步任务
    asyncio.run(run_pipeline())


def main():
    """主函数"""
    app = typer.Typer()
    
    app.command()(start)    # 启动 FastAPI 服务器
    app.command()(run)      # 纯终端模式运行
    app.command()(init_db)  # 初始化数据库
    
    app()

if __name__ == "__main__":
    main()
