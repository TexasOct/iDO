"""
macOS permission checking and management
"""

import platform
import subprocess
import sys
from datetime import datetime
from importlib import import_module
from typing import Any, Callable, Dict, Optional, Tuple

from core.logger import get_logger
from models.permissions import (
    PermissionInfo,
    PermissionsCheckResponse,
    PermissionStatus,
    PermissionType,
)

logger = get_logger(__name__)


def _load_accessibility_api() -> Tuple[
    Optional[Callable[[Dict[str, Any]], Any]], Optional[Any]
]:
    """Safely load ApplicationServices accessibility helpers."""
    try:
        module = import_module("ApplicationServices")
        checker = getattr(module, "AXIsProcessTrustedWithOptions", None)
        prompt_key = getattr(module, "kAXTrustedCheckOptionPrompt", None)
        if callable(checker) and prompt_key is not None:
            return checker, prompt_key
    except Exception as exc:
        logger.debug(f"Failed to import ApplicationServices helpers: {exc}")
    return None, None


def _load_screen_capture_api() -> Optional[Callable[[], bool]]:
    """Safely load CoreGraphics screen capture permission checker."""
    try:
        module = import_module("Quartz")
        checker = getattr(module, "CGPreflightScreenCaptureAccess", None)
        if callable(checker):
            return checker
    except Exception as exc:
        logger.debug(f"Failed to import Quartz CGPreflightScreenCaptureAccess: {exc}")
    return None


def _check_tcc_database(service: str, bundle_id: Optional[str] = None) -> Optional[bool]:
    """
    Check TCC database for permission status (macOS).

    Args:
        service: TCC service name (e.g., 'kTCCServiceAccessibility', 'kTCCServiceScreenCapture')
        bundle_id: Optional bundle identifier (auto-detected if None)

    Returns:
        True if allowed, False if denied, None if not determined
    """
    try:
        import os
        import sqlite3

        # Get bundle ID if not provided
        if bundle_id is None:
            try:
                foundation = import_module("Foundation")
                NSBundle = getattr(foundation, "NSBundle", None)
                if NSBundle:
                    main_bundle = NSBundle.mainBundle()
                    bundle_id = main_bundle.bundleIdentifier()
                if not bundle_id:
                    # Fallback for development/non-bundled apps
                    bundle_id = os.path.basename(sys.executable)
            except Exception as e:
                logger.debug(f"Failed to get bundle ID: {e}")
                bundle_id = os.path.basename(sys.executable)

        # TCC database location
        tcc_db = os.path.expanduser("~/Library/Application Support/com.apple.TCC/TCC.db")

        if not os.path.exists(tcc_db):
            logger.debug(f"TCC database not found at {tcc_db}")
            return None

        # Query TCC database
        conn = sqlite3.connect(tcc_db)
        cursor = conn.cursor()

        # Query format varies by macOS version
        try:
            # macOS 10.14+
            cursor.execute(
                "SELECT allowed FROM access WHERE service = ? AND client = ?",
                (service, bundle_id)
            )
        except sqlite3.OperationalError:
            try:
                # Older macOS versions
                cursor.execute(
                    "SELECT allowed FROM access WHERE service = ? AND client = ?",
                    (service, bundle_id)
                )
            except Exception as e:
                logger.debug(f"Failed to query TCC database: {e}")
                conn.close()
                return None

        result = cursor.fetchone()
        conn.close()

        if result is None:
            return None  # Not determined

        return bool(result[0])

    except Exception as e:
        logger.debug(f"Failed to check TCC database: {e}")
        return None


class PermissionChecker:
    """Permission checker"""

    def __init__(self):
        self.platform = platform.system()

    def check_all_permissions(self) -> PermissionsCheckResponse:
        """Check all required permissions"""
        if self.platform == "Darwin":  # macOS
            return self._check_macos_permissions()
        elif self.platform == "Windows":
            return self._check_windows_permissions()
        elif self.platform == "Linux":
            return self._check_linux_permissions()
        else:
            # Unknown platform, return default values
            return PermissionsCheckResponse(
                all_granted=True,
                permissions={},
                platform=self.platform,
                needs_restart=False,
            )

    def _check_macos_permissions(self) -> PermissionsCheckResponse:
        """Check macOS permissions"""
        permissions = {}

        # Check accessibility permission
        accessibility_status = self._check_macos_accessibility()
        permissions["accessibility"] = PermissionInfo(
            type=PermissionType.ACCESSIBILITY,
            status=accessibility_status,
            name="permissions.accessibility.name",
            description="permissions.accessibility.description",
            required=True,
            system_settings_path="permissions.accessibility.settingsPath",
        )

        # Check screen recording permission
        screen_recording_status = self._check_macos_screen_recording()
        permissions["screen_recording"] = PermissionInfo(
            type=PermissionType.SCREEN_RECORDING,
            status=screen_recording_status,
            name="permissions.screenRecording.name",
            description="permissions.screenRecording.description",
            required=True,
            system_settings_path="permissions.screenRecording.settingsPath",
        )

        # Check if all required permissions are granted
        all_granted = all(
            p.status == PermissionStatus.GRANTED for p in permissions.values()
        )

        # If permissions change from undetermined to granted, may need restart
        needs_restart = any(
            p.status == PermissionStatus.NOT_DETERMINED for p in permissions.values()
        )

        return PermissionsCheckResponse(
            all_granted=all_granted,
            permissions=permissions,
            platform="macOS",
            needs_restart=needs_restart,
        )

    def _check_macos_accessibility(self) -> PermissionStatus:
        """Check macOS accessibility permission using multiple methods for accuracy"""
        try:
            if sys.platform != "darwin":
                return PermissionStatus.NOT_DETERMINED

            # Method 1: Try PyObjC AXIsProcessTrustedWithOptions (most reliable for runtime check)
            ax_checker, prompt_key = _load_accessibility_api()
            if ax_checker and prompt_key is not None:
                # Check if trusted (without prompt)
                is_trusted = ax_checker({prompt_key: False})

                if is_trusted:
                    logger.debug("Accessibility permission granted (via AXIsProcessTrusted)")
                    return PermissionStatus.GRANTED
                else:
                    # Not trusted - could be denied or not determined
                    # Use TCC database to differentiate
                    logger.debug("AXIsProcessTrusted returned False, checking TCC database...")
            else:
                logger.warning(
                    "PyObjC ApplicationServices not available, falling back to TCC check"
                )

            # Method 2: Check TCC database to differentiate DENIED vs NOT_DETERMINED
            tcc_result = _check_tcc_database("kTCCServiceAccessibility")

            if tcc_result is True:
                logger.debug("Accessibility permission granted (via TCC database)")
                return PermissionStatus.GRANTED
            elif tcc_result is False:
                logger.debug("Accessibility permission denied (via TCC database)")
                return PermissionStatus.DENIED
            else:
                # Not in database = never requested
                logger.debug("Accessibility permission not determined (not in TCC database)")
                return PermissionStatus.NOT_DETERMINED

        except Exception as e:
            logger.error(f"Failed to check accessibility permission: {e}", exc_info=True)
            return PermissionStatus.NOT_DETERMINED

    def _check_macos_screen_recording(self) -> PermissionStatus:
        """Check macOS screen recording permission using multiple methods for accuracy"""
        try:
            if sys.platform != "darwin":
                return PermissionStatus.NOT_DETERMINED

            # Method 1: Try CGPreflightScreenCaptureAccess (macOS 10.15+)
            # This is the most reliable method
            screen_capture_checker = _load_screen_capture_api()
            if screen_capture_checker:
                has_access = screen_capture_checker()

                if has_access:
                    logger.debug("Screen recording permission granted (via CGPreflightScreenCaptureAccess)")
                    return PermissionStatus.GRANTED
                else:
                    logger.debug("CGPreflightScreenCaptureAccess returned False, checking TCC database...")
            else:
                logger.debug(
                    "CGPreflightScreenCaptureAccess not available, falling back to TCC check"
                )

            # Method 2: Check TCC database
            tcc_result = _check_tcc_database("kTCCServiceScreenCapture")

            if tcc_result is True:
                logger.debug("Screen recording permission granted (via TCC database)")
                return PermissionStatus.GRANTED
            elif tcc_result is False:
                logger.debug("Screen recording permission denied (via TCC database)")
                return PermissionStatus.DENIED
            else:
                # Not in database = never requested
                logger.debug("Screen recording permission not determined (not in TCC database)")
                return PermissionStatus.NOT_DETERMINED

        except Exception as e:
            logger.error(f"Failed to check screen recording permission: {e}", exc_info=True)
            return PermissionStatus.NOT_DETERMINED

    def _check_windows_permissions(self) -> PermissionsCheckResponse:
        """Check Windows permissions (simplified version)"""
        # Windows usually doesn't need special permissions, but may need admin rights
        permissions = {}

        # Windows doesn't need accessibility permission
        permissions["accessibility"] = PermissionInfo(
            type=PermissionType.ACCESSIBILITY,
            status=PermissionStatus.GRANTED,
            name="Input Monitoring",
            description="Windows system does not require additional permissions",
            required=False,
            system_settings_path="",
        )

        permissions["screen_recording"] = PermissionInfo(
            type=PermissionType.SCREEN_RECORDING,
            status=PermissionStatus.GRANTED,
            name="Screen Screenshot",
            description="Windows system does not require additional permissions",
            required=False,
            system_settings_path="",
        )

        return PermissionsCheckResponse(
            all_granted=True,
            permissions=permissions,
            platform="Windows",
            needs_restart=False,
        )

    def _check_linux_permissions(self) -> PermissionsCheckResponse:
        """Check Linux permissions (simplified version)"""
        # Linux permission checking depends on display server (X11/Wayland)
        permissions = {}

        permissions["accessibility"] = PermissionInfo(
            type=PermissionType.ACCESSIBILITY,
            status=PermissionStatus.GRANTED,
            name="Input Monitoring",
            description="Linux system may need X11 permissions",
            required=False,
            system_settings_path="",
        )

        permissions["screen_recording"] = PermissionInfo(
            type=PermissionType.SCREEN_RECORDING,
            status=PermissionStatus.GRANTED,
            name="Screen Screenshot",
            description="Linux system may need X11 permissions",
            required=False,
            system_settings_path="",
        )

        return PermissionsCheckResponse(
            all_granted=True,
            permissions=permissions,
            platform="Linux",
            needs_restart=False,
        )

    def open_system_settings(self, permission_type: PermissionType) -> bool:
        """Open system settings permission page"""
        if self.platform != "Darwin":
            logger.warning(
                f"{self.platform} does not support automatic opening of system settings"
            )
            return False

        try:
            if permission_type == PermissionType.ACCESSIBILITY:
                # Open accessibility settings
                subprocess.run(
                    [
                        "open",
                        "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility",
                    ]
                )
                return True
            elif permission_type == PermissionType.SCREEN_RECORDING:
                # Open screen recording settings
                subprocess.run(
                    [
                        "open",
                        "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture",
                    ]
                )
                return True
            else:
                logger.warning(f"Unknown permission type: {permission_type}")
                return False

        except Exception as e:
            logger.error(f"Failed to open system settings: {e}")
            return False

    def request_accessibility_permission(self) -> bool:
        """Request accessibility permission (will show system prompt)"""
        if self.platform != "Darwin":
            return True

        try:
            ax_checker, prompt_key = _load_accessibility_api()
            if not ax_checker or prompt_key is None:
                logger.warning(
                    "PyObjC ApplicationServices 未安装，无法请求辅助功能权限"
                )
                return False

            # Check and request permission (with prompt)
            is_trusted = ax_checker({prompt_key: True})

            return is_trusted

        except Exception as e:
            logger.error(f"请求辅助功能权限失败: {e}")
            return False


# 全局实例
_permission_checker = None


def get_permission_checker() -> PermissionChecker:
    """获取全局权限检查器实例"""
    global _permission_checker
    if _permission_checker is None:
        _permission_checker = PermissionChecker()
    return _permission_checker
