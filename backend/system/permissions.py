"""
macOS permission checking and management
"""

import sys
import subprocess
import platform
from core.logger import get_logger
from models.permissions import (
    PermissionType,
    PermissionStatus,
    PermissionInfo,
    PermissionsCheckResponse,
)

logger = get_logger(__name__)


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
        """Check macOS accessibility permission"""
        try:
            # Try to check permissions using PyObjC
            if sys.platform == "darwin":
                try:
                    from ApplicationServices import (
                        AXIsProcessTrustedWithOptions,
                        kAXTrustedCheckOptionPrompt,
                    )

                    # Check if trusted (without prompt)
                    is_trusted = AXIsProcessTrustedWithOptions(
                        {kAXTrustedCheckOptionPrompt: False}
                    )

                    if is_trusted:
                        return PermissionStatus.GRANTED
                    else:
                        return PermissionStatus.NOT_DETERMINED

                except ImportError:
                    logger.warning(
                        "PyObjC ApplicationServices not installed, cannot check accessibility permission"
                    )
                    # Fallback handling: assume unauthorized
                    return PermissionStatus.NOT_DETERMINED
        except Exception as e:
            logger.error(f"Failed to check accessibility permission: {e}")
            return PermissionStatus.NOT_DETERMINED

    def _check_macos_screen_recording(self) -> PermissionStatus:
        """Check macOS screen recording permission"""
        try:
            # Screen recording permission is difficult to detect directly
            # One method is to try taking screenshots and check if it's black screen
            # Here we simplify by checking through tccutil

            # First try simple heuristic check
            import mss

            with mss.mss() as sct:
                # Capture main display
                monitor = sct.monitors[1]
                screenshot = sct.grab(monitor)

                # Check if screenshot is completely black (may indicate permission denied)
                # This is not perfect detection, but can serve as heuristic judgment
                from PIL import Image

                img = Image.frombytes(
                    "RGB", screenshot.size, screenshot.bgra, "raw", "BGRX"
                )

                # Calculate average brightness of image
                import numpy as np

                img_array = np.array(img)
                avg_brightness = img_array.mean()

                # If average brightness is extremely low (< 5), may be permission issue
                if avg_brightness < 5:
                    logger.warning(
                        "Screenshot appears to be completely black, may be missing screen recording permission"
                    )
                    return PermissionStatus.DENIED
                else:
                    return PermissionStatus.GRANTED

        except ImportError:
            logger.warning(
                "Missing dependency library, cannot check screen recording permission"
            )
            return PermissionStatus.NOT_DETERMINED
        except Exception as e:
            logger.error(f"Failed to check screen recording permission: {e}")
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
            from ApplicationServices import (
                AXIsProcessTrustedWithOptions,
                kAXTrustedCheckOptionPrompt,
            )

            # Check and request permission (with prompt)
            is_trusted = AXIsProcessTrustedWithOptions(
                {kAXTrustedCheckOptionPrompt: True}
            )

            return is_trusted

        except ImportError:
            logger.warning("PyObjC ApplicationServices 未安装，无法请求辅助功能权限")
            return False
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
