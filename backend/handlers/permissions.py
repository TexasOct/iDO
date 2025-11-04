"""
Permission management related API handlers
"""

import os
import sys
import asyncio
from typing import Optional
from . import api_handler
from models.permissions import (
    PermissionsCheckResponse,
    OpenSystemSettingsRequest,
    RestartAppRequest,
)
from system.permissions import get_permission_checker
from core.logger import get_logger

logger = get_logger(__name__)


@api_handler(method="GET", path="/permissions/check", tags=["permissions"])
async def check_permissions(body: None) -> dict:
    """
    Check all required system permissions

    Returns:
        Permission check results, including status of each permission
    """
    try:
        checker = get_permission_checker()
        result = checker.check_all_permissions()

        logger.info(f"Permission check completed: all_granted={result.all_granted}")

        # Explicitly convert to camelCase dictionary
        return result.model_dump(by_alias=True)

    except Exception as e:
        logger.error(f"Permission check failed: {e}")
        raise


@api_handler(
    body=OpenSystemSettingsRequest,
    method="POST",
    path="/permissions/open-settings",
    tags=["permissions"],
)
async def open_system_settings(body: OpenSystemSettingsRequest) -> dict:
    """
    Open system settings permission page

    Args:
        body: Contains the permission type to open

    Returns:
        Operation result
    """
    try:
        checker = get_permission_checker()
        success = checker.open_system_settings(body.permission_type)

        if success:
            logger.info(f"Opened system settings: {body.permission_type}")
            return {
                "success": True,
                "message": f"Opened {body.permission_type} permission settings page",
            }
        else:
            return {"success": False, "message": "Failed to open system settings"}

    except Exception as e:
        logger.error(f"Failed to open system settings: {e}")
        return {"success": False, "message": str(e)}


@api_handler(path="/permissions/request-accessibility", tags=["permissions"])
async def request_accessibility_permission(body: None) -> dict:
    """
    Request accessibility permission (macOS only)

    This will trigger system permission dialog

    Returns:
        Request result
    """
    try:
        checker = get_permission_checker()
        granted = checker.request_accessibility_permission()

        if granted:
            logger.info("Accessibility permission granted")
            return {
                "success": True,
                "granted": True,
                "message": "Accessibility permission granted",
            }
        else:
            logger.warning("Accessibility permission not granted")
            return {
                "success": True,
                "granted": False,
                "message": "Please manually grant permission in system settings",
            }

    except Exception as e:
        logger.error(f"Failed to request accessibility permission: {e}")
        return {"success": False, "granted": False, "message": str(e)}


@api_handler(
    body=RestartAppRequest,
    method="POST",
    path="/permissions/restart-app",
    tags=["permissions"],
)
async def restart_app(body: RestartAppRequest) -> dict:
    """
    Restart application

    Args:
        body: Request containing delay time

    Returns:
        Operation result
    """
    try:
        delay = max(0, min(10, body.delay_seconds))  # Limit to 0-10 seconds

        logger.info(f"Application will restart in {delay} seconds...")

        # Execute restart asynchronously
        asyncio.create_task(_restart_app_delayed(delay))

        return {
            "success": True,
            "message": f"Application will restart in {delay} seconds",
            "delay_seconds": delay,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to restart application: {e}")
        return {"success": False, "message": str(e)}


async def _restart_app_delayed(delay: float):
    """Delayed restart application"""
    try:
        await asyncio.sleep(delay)

        logger.info("Restarting application...")

        # Get current executable path
        if getattr(sys, "frozen", False):
            # Packaged application
            executable = sys.executable
        else:
            # Development environment
            executable = sys.executable

        # macOS special handling
        if sys.platform == "darwin":
            # If running in .app bundle
            if ".app/Contents/MacOS/" in executable:
                # Extract .app path
                app_path = executable.split(".app/Contents/MacOS/")[0] + ".app"
                logger.info(f"Reopening application: {app_path}")

                # Use open command to restart application
                import subprocess

                subprocess.Popen(["open", "-n", app_path])
            else:
                # Direct executable
                import subprocess

                subprocess.Popen([executable] + sys.argv)
        else:
            # Windows/Linux
            import subprocess

            subprocess.Popen([executable] + sys.argv)

            # Exit current process
            await asyncio.sleep(0.5)
            os._exit(0)

    except Exception as e:
        logger.error(f"Delayed restart failed: {e}")
