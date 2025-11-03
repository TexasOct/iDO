"""
权限管理相关的 API handlers
"""

import os
import sys
import asyncio
from typing import Optional
from . import api_handler
from models.permissions import (
    PermissionsCheckResponse,
    OpenSystemSettingsRequest,
    RestartAppRequest
)
from system.permissions import get_permission_checker
from core.logger import get_logger

logger = get_logger(__name__)


@api_handler(
    method="GET",
    path="/permissions/check",
    tags=["permissions"]
)
async def check_permissions(body: None) -> PermissionsCheckResponse:
    """
    检查所有必需的系统权限

    Returns:
        权限检查结果，包含每个权限的状态
    """
    try:
        checker = get_permission_checker()
        result = checker.check_all_permissions()

        logger.info(f"权限检查完成: all_granted={result.all_granted}")
        return result

    except Exception as e:
        logger.error(f"检查权限失败: {e}")
        raise


@api_handler(
    body=OpenSystemSettingsRequest,
    method="POST",
    path="/permissions/open-settings",
    tags=["permissions"]
)
async def open_system_settings(body: OpenSystemSettingsRequest) -> dict:
    """
    打开系统设置对应的权限页面

    Args:
        body: 包含要打开的权限类型

    Returns:
        操作结果
    """
    try:
        checker = get_permission_checker()
        success = checker.open_system_settings(body.permission_type)

        if success:
            logger.info(f"已打开系统设置: {body.permission_type}")
            return {
                "success": True,
                "message": f"已打开 {body.permission_type} 权限设置页面"
            }
        else:
            return {
                "success": False,
                "message": "打开系统设置失败"
            }

    except Exception as e:
        logger.error(f"打开系统设置失败: {e}")
        return {
            "success": False,
            "message": str(e)
        }


@api_handler(
    method="POST",
    path="/permissions/request-accessibility",
    tags=["permissions"]
)
async def request_accessibility_permission(body: None) -> dict:
    """
    请求辅助功能权限（仅 macOS）

    这将触发系统权限对话框

    Returns:
        请求结果
    """
    try:
        checker = get_permission_checker()
        granted = checker.request_accessibility_permission()

        if granted:
            logger.info("辅助功能权限已授予")
            return {
                "success": True,
                "granted": True,
                "message": "辅助功能权限已授予"
            }
        else:
            logger.warning("辅助功能权限未授予")
            return {
                "success": True,
                "granted": False,
                "message": "请在系统设置中手动授予权限"
            }

    except Exception as e:
        logger.error(f"请求辅助功能权限失败: {e}")
        return {
            "success": False,
            "granted": False,
            "message": str(e)
        }


@api_handler(
    body=RestartAppRequest,
    method="POST",
    path="/permissions/restart-app",
    tags=["permissions"]
)
async def restart_app(body: RestartAppRequest) -> dict:
    """
    重启应用程序

    Args:
        body: 包含延迟时间的请求

    Returns:
        操作结果
    """
    try:
        delay = max(0, min(10, body.delay_seconds))  # 限制在 0-10 秒

        logger.info(f"应用将在 {delay} 秒后重启...")

        # 异步执行重启
        asyncio.create_task(_restart_app_delayed(delay))

        return {
            "success": True,
            "message": f"应用将在 {delay} 秒后重启",
            "delay_seconds": delay
        }

    except Exception as e:
        logger.error(f"重启应用失败: {e}")
        return {
            "success": False,
            "message": str(e)
        }


async def _restart_app_delayed(delay: float):
    """延迟重启应用"""
    try:
        await asyncio.sleep(delay)

        logger.info("正在重启应用...")

        # 获取当前可执行文件路径
        if getattr(sys, 'frozen', False):
            # 打包后的应用
            executable = sys.executable
        else:
            # 开发环境
            executable = sys.executable

        # macOS 特殊处理
        if sys.platform == "darwin":
            # 如果在 .app bundle 中运行
            if ".app/Contents/MacOS/" in executable:
                # 提取 .app 路径
                app_path = executable.split(".app/Contents/MacOS/")[0] + ".app"
                logger.info(f"重新打开应用: {app_path}")

                # 使用 open 命令重新启动应用
                import subprocess
                subprocess.Popen(["open", "-n", app_path])
            else:
                # 直接可执行文件
                import subprocess
                subprocess.Popen([executable] + sys.argv)
        else:
            # Windows/Linux
            import subprocess
            subprocess.Popen([executable] + sys.argv)

        # 退出当前进程
        await asyncio.sleep(0.5)
        os._exit(0)

    except Exception as e:
        logger.error(f"延迟重启失败: {e}")
