"""后端运行时控制工具

提供在 CLI 与 PyTauri 之间复用的启动、停止与状态查询逻辑。
"""

from __future__ import annotations

import atexit
import signal
import asyncio
import threading
from typing import Optional

from config.loader import load_config
from core.db import get_db
from core.coordinator import get_coordinator, PipelineCoordinator
from core.logger import get_logger

logger = get_logger(__name__)

# 全局标志，防止重复清理
_cleanup_done = False
_exit_handlers_registered = False


def _cleanup_on_exit():
    """进程退出时的清理函数（同步版本，用于 atexit）"""
    global _cleanup_done

    if _cleanup_done:
        return

    _cleanup_done = True
    logger.info("正在执行退出清理...")

    try:
        coordinator = get_coordinator()
        if not coordinator.is_running:
            logger.debug("协调器未运行，跳过清理")
            return

        # 在同步上下文中运行异步停止函数
        try:
            # 尝试获取当前事件循环
            loop = asyncio.get_event_loop()

            # 检查事件循环是否正在运行
            if loop.is_running():
                # 事件循环正在运行，不能使用 run_until_complete
                # 创建一个新的线程来运行停止函数
                logger.debug("事件循环正在运行，使用新线程执行清理")
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, coordinator.stop())
                    future.result(timeout=5.0)  # 最多等待 5 秒
            else:
                # 事件循环未运行，直接使用
                logger.debug("使用现有事件循环执行清理")
                loop.run_until_complete(coordinator.stop())

        except RuntimeError:
            # 没有事件循环，创建新的
            logger.debug("创建新事件循环执行清理")
            asyncio.run(coordinator.stop())

        logger.info("退出清理完成")

    except Exception as e:
        logger.error(f"退出清理失败: {e}", exc_info=True)


def _signal_handler(signum, frame):
    """信号处理器"""
    global _cleanup_done

    signal_name = signal.Signals(signum).name
    logger.info(f"收到信号 {signal_name}，准备退出...")

    # 执行清理
    _cleanup_on_exit()

    # 退出程序
    import sys
    sys.exit(0)


def _is_main_thread() -> bool:
    """检查当前是否为主线程"""
    return threading.current_thread() is threading.main_thread()


def _register_exit_handlers():
    """注册退出处理器（线程安全）"""
    global _exit_handlers_registered

    # 防止重复注册
    if _exit_handlers_registered:
        logger.debug("退出处理器已注册，跳过")
        return

    # 注册 atexit 清理函数（线程安全）
    atexit.register(_cleanup_on_exit)
    logger.debug("atexit 清理函数已注册")

    # 只在主线程中注册信号处理器
    if _is_main_thread():
        try:
            signal.signal(signal.SIGINT, _signal_handler)   # Ctrl+C
            signal.signal(signal.SIGTERM, _signal_handler)  # kill 命令
            logger.debug("信号处理器已注册（主线程）")
        except ValueError as e:
            logger.warning(f"无法注册信号处理器: {e}")
    else:
        logger.debug("当前为子线程，跳过信号处理器注册（将使用 atexit）")

    _exit_handlers_registered = True


async def start_runtime(config_file: Optional[str] = None) -> PipelineCoordinator:
    """启动后台监听流程，如已运行则直接返回协调器实例。"""

    # 确保配置与数据库初始化
    load_config(config_file)
    get_db()

    # 注册退出处理器（只注册一次）
    _register_exit_handlers()

    coordinator = get_coordinator()
    if coordinator.is_running:
        logger.info("流程协调器已在运行中，无需重复启动")
        return coordinator

    logger.info("正在启动流程协调器...")
    await coordinator.start()
    logger.info("流程协调器启动成功")
    return coordinator


async def stop_runtime() -> PipelineCoordinator:
    """停止后台监听流程，如果尚未运行则直接返回。"""

    coordinator = get_coordinator()
    if not coordinator.is_running:
        logger.info("流程协调器当前未运行")
        return coordinator

    logger.info("正在停止流程协调器...")
    await coordinator.stop()
    logger.info("流程协调器已停止")
    return coordinator


async def get_runtime_stats() -> dict:
    """获取当前协调器的统计信息。"""

    coordinator = get_coordinator()
    return coordinator.get_stats()
