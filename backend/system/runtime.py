"""Backend runtime control utility

Provides startup, stop and status query logic for reuse between CLI and PyTauri.
"""

from __future__ import annotations

import atexit
import signal
import asyncio
import threading
from typing import Optional

from config.loader import get_config
from core.db import get_db
from core.coordinator import get_coordinator, PipelineCoordinator
from core.logger import get_logger

logger = get_logger(__name__)

# 全局标志，防止重复清理
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
                # 事件循环正在运行，不能使用 run_until_complete
                # 创建一个新的线程来运行停止函数
                logger.debug("事件循环正在运行，使用新线程执行清理")
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, coordinator.stop(quiet=True))
                    future.result(timeout=5.0)  # 最多等待 5 秒
            else:
                # Event loop not running, use directly
                logger.debug("Using existing event loop to execute cleanup")
                loop.run_until_complete(coordinator.stop(quiet=True))

        except RuntimeError:
            # 没有事件循环，创建新的
            logger.debug("创建新事件循环执行清理")
            asyncio.run(coordinator.stop(quiet=True))

        logger.debug("Exit cleanup completed")

    except Exception as e:
        logger.error(f"退出清理失败: {e}", exc_info=True)


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

    # 注册 atexit 清理函数（线程安全）
    atexit.register(_cleanup_on_exit)
    logger.debug("atexit 清理函数已注册")

    # 只在主线程中注册信号处理器
    if _is_main_thread():
        try:
            signal.signal(signal.SIGINT, _signal_handler)  # Ctrl+C
            signal.signal(signal.SIGTERM, _signal_handler)  # kill 命令
            logger.debug("信号处理器已注册（主线程）")
        except ValueError as e:
            logger.warning(f"无法注册信号处理器: {e}")
    else:
        logger.debug("当前为子线程，跳过信号处理器注册（将使用 atexit）")

    _exit_handlers_registered = True


async def start_runtime(config_file: Optional[str] = None) -> PipelineCoordinator:
    """启动后台监听流程，如已运行则直接返回协调器实例。"""

    # 加载配置文件（自动创建默认配置如果不存在）
    config_loader = get_config(config_file)
    config_loader.load()
    logger.info(f"✓ 配置文件: {config_loader.config_file}")

    # 初始化数据库（使用 config.toml 中的 database.path）
    db = get_db()

    # 初始化 Settings 管理器（直接编辑 config.toml）
    from core.settings import init_settings, get_settings
    from core.db import switch_database

    init_settings(config_loader)

    # 检查 config.toml 中是否配置了不同的数据库路径，如果有则切换
    settings = get_settings()
    try:
        from processing.image_manager import get_image_manager

        image_manager = get_image_manager()
        image_manager.update_storage_path(settings.get_screenshot_path())
    except Exception as exc:
        logger.warning(f"同步截图存储目录失败: {exc}")

    configured_db_path = settings.get_database_path()
    current_db_path = db.db_path

    if configured_db_path and str(configured_db_path) != str(current_db_path):
        logger.info(f"检测到已配置的数据库路径: {configured_db_path}")
        if switch_database(configured_db_path):
            logger.info(f"✓ 已切换到配置的数据库路径")
            # 更新引用
            db = get_db()
        else:
            logger.warning(f"✗ 切换到配置的数据库路径失败，继续使用: {current_db_path}")

    # 注册退出处理器（只注册一次）
    _register_exit_handlers()

    coordinator = get_coordinator()
    if coordinator.is_running:
        logger.info("流程协调器已在运行中，无需重复启动")
        return coordinator

    logger.info("正在启动流程协调器...")
    try:
        await coordinator.start()
    except RuntimeError as exc:
        logger.error(f"流程协调器启动失败: {exc}")
        raise

    if coordinator.is_running:
        logger.info("流程协调器启动成功")
    else:
        if coordinator.mode == "requires_model":
            logger.warning("流程协调器处于受限模式（未检测到激活的 LLM 模型配置）")
            if coordinator.last_error:
                logger.warning(coordinator.last_error)
        elif coordinator.mode == "error" and coordinator.last_error:
            logger.error(f"流程协调器启动后进入错误状态: {coordinator.last_error}")
        else:
            logger.info(f"流程协调器当前状态: {coordinator.mode}")

    # Initialize friendly chat service
    try:
        from services.friendly_chat_service import init_friendly_chat_service

        await init_friendly_chat_service()
        logger.info("✓ Friendly chat service initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize friendly chat service: {e}")

    return coordinator


async def stop_runtime(*, quiet: bool = False) -> PipelineCoordinator:
    """停止后台监听流程，如果尚未运行则直接返回。

    Args:
        quiet: 当为 True 时仅记录调试日志，避免在终端输出停机信息。
    """

    coordinator = get_coordinator()
    if not coordinator.is_running:
        if not quiet:
            logger.info("流程协调器当前未运行")
        return coordinator

    if not quiet:
        logger.info("正在停止流程协调器...")

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
        # 添加超时保护：最多等待 5 秒停止协调器
        await asyncio.wait_for(coordinator.stop(quiet=quiet), timeout=5.0)
    except asyncio.TimeoutError:
        if not quiet:
            logger.warning("停止流程协调器超时，强制停止")
    except Exception as e:
        if not quiet:
            logger.error(f"停止流程协调器异常: {e}", exc_info=True)

    if not quiet:
        logger.info("流程协调器已停止")
    return coordinator


async def get_runtime_stats() -> dict:
    """获取当前协调器的统计信息。"""

    coordinator = get_coordinator()
    return coordinator.get_stats()
