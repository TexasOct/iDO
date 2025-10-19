"""
Rewind Backend CLI 接口
使用 Typer 实现命令行界面
"""

import typer
from typing import Optional
import uvicorn
from config.loader import load_config
from core.logger import get_logger

app = typer.Typer(help="Rewind Backend CLI")
logger = get_logger(__name__)


@app.command()
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


@app.command()
def init_db():
    """初始化数据库"""
    logger.info("初始化数据库...")
    # TODO: 实现数据库初始化逻辑
    pass


@app.command()
def test():
    """运行测试"""
    logger.info("运行测试...")
    # TODO: 实现测试运行逻辑
    pass


def main():
    """主函数"""
    app()

if __name__ == "__main__":
    main()
