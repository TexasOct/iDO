"""
macOS 权限检查和管理
"""

import sys
import subprocess
import platform
from core.logger import get_logger
from models.permissions import (
    PermissionType,
    PermissionStatus,
    PermissionInfo,
    PermissionsCheckResponse
)

logger = get_logger(__name__)


class PermissionChecker:
    """权限检查器"""

    def __init__(self):
        self.platform = platform.system()

    def check_all_permissions(self) -> PermissionsCheckResponse:
        """检查所有必需权限"""
        if self.platform == "Darwin":  # macOS
            return self._check_macos_permissions()
        elif self.platform == "Windows":
            return self._check_windows_permissions()
        elif self.platform == "Linux":
            return self._check_linux_permissions()
        else:
            # 未知平台,返回默认值
            return PermissionsCheckResponse(
                all_granted=True,
                permissions={},
                platform=self.platform,
                needs_restart=False
            )

    def _check_macos_permissions(self) -> PermissionsCheckResponse:
        """检查 macOS 权限"""
        permissions = {}

        # 检查辅助功能权限
        accessibility_status = self._check_macos_accessibility()
        permissions["accessibility"] = PermissionInfo(
            type=PermissionType.ACCESSIBILITY,
            status=accessibility_status,
            name="辅助功能权限",
            description="用于监听键盘和鼠标事件，记录您的活动轨迹",
            required=True,
            system_settings_path="系统设置 → 隐私与安全性 → 辅助功能"
        )

        # 检查屏幕录制权限
        screen_recording_status = self._check_macos_screen_recording()
        permissions["screen_recording"] = PermissionInfo(
            type=PermissionType.SCREEN_RECORDING,
            status=screen_recording_status,
            name="屏幕录制权限",
            description="用于定期截取屏幕快照，帮助您回顾工作内容",
            required=True,
            system_settings_path="系统设置 → 隐私与安全性 → 屏幕录制"
        )

        # 检查是否所有必需权限都已授予
        all_granted = all(
            p.status == PermissionStatus.GRANTED
            for p in permissions.values()
            if p.required
        )

        # 如果有权限从未确定状态变为授予,可能需要重启
        needs_restart = any(
            p.status == PermissionStatus.NOT_DETERMINED
            for p in permissions.values()
        )

        return PermissionsCheckResponse(
            all_granted=all_granted,
            permissions=permissions,
            platform="macOS",
            needs_restart=needs_restart
        )

    def _check_macos_accessibility(self) -> PermissionStatus:
        """检查 macOS 辅助功能权限"""
        try:
            # 尝试使用 PyObjC 检查权限
            if sys.platform == "darwin":
                try:
                    from ApplicationServices import (
                        AXIsProcessTrustedWithOptions,
                        kAXTrustedCheckOptionPrompt
                    )

                    # 检查是否受信任（不弹出提示）
                    is_trusted = AXIsProcessTrustedWithOptions({
                        kAXTrustedCheckOptionPrompt: False
                    })

                    if is_trusted:
                        return PermissionStatus.GRANTED
                    else:
                        return PermissionStatus.NOT_DETERMINED

                except ImportError:
                    logger.warning("PyObjC ApplicationServices 未安装，无法检查辅助功能权限")
                    # 降级处理:假设未授权
                    return PermissionStatus.NOT_DETERMINED
        except Exception as e:
            logger.error(f"检查辅助功能权限失败: {e}")
            return PermissionStatus.NOT_DETERMINED

    def _check_macos_screen_recording(self) -> PermissionStatus:
        """检查 macOS 屏幕录制权限"""
        try:
            # 屏幕录制权限较难直接检测
            # 一种方法是尝试截图并检查是否为黑屏
            # 这里简化处理,通过 tccutil 检查

            # 先尝试简单的启发式检查
            import mss

            with mss.mss() as sct:
                # 截取主显示器
                monitor = sct.monitors[1]
                screenshot = sct.grab(monitor)

                # 检查截图是否全黑（可能表示权限被拒绝）
                # 这不是完美的检测,但可以作为启发式判断
                from PIL import Image
                img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")

                # 计算图像的平均亮度
                import numpy as np
                img_array = np.array(img)
                avg_brightness = img_array.mean()

                # 如果平均亮度极低（< 5），可能是权限问题
                if avg_brightness < 5:
                    logger.warning("屏幕截图疑似全黑，可能缺少屏幕录制权限")
                    return PermissionStatus.DENIED
                else:
                    return PermissionStatus.GRANTED

        except ImportError:
            logger.warning("缺少依赖库，无法检查屏幕录制权限")
            return PermissionStatus.NOT_DETERMINED
        except Exception as e:
            logger.error(f"检查屏幕录制权限失败: {e}")
            return PermissionStatus.NOT_DETERMINED

    def _check_windows_permissions(self) -> PermissionsCheckResponse:
        """检查 Windows 权限（简化版）"""
        # Windows 通常不需要特殊权限,但可能需要管理员权限
        permissions = {}

        # Windows 不需要辅助功能权限
        permissions["accessibility"] = PermissionInfo(
            type=PermissionType.ACCESSIBILITY,
            status=PermissionStatus.GRANTED,
            name="输入监听",
            description="Windows 系统无需额外权限",
            required=False,
            system_settings_path=""
        )

        permissions["screen_recording"] = PermissionInfo(
            type=PermissionType.SCREEN_RECORDING,
            status=PermissionStatus.GRANTED,
            name="屏幕截图",
            description="Windows 系统无需额外权限",
            required=False,
            system_settings_path=""
        )

        return PermissionsCheckResponse(
            all_granted=True,
            permissions=permissions,
            platform="Windows",
            needs_restart=False
        )

    def _check_linux_permissions(self) -> PermissionsCheckResponse:
        """检查 Linux 权限（简化版）"""
        # Linux 权限检查取决于显示服务器（X11/Wayland）
        permissions = {}

        permissions["accessibility"] = PermissionInfo(
            type=PermissionType.ACCESSIBILITY,
            status=PermissionStatus.GRANTED,
            name="输入监听",
            description="Linux 系统可能需要 X11 权限",
            required=False,
            system_settings_path=""
        )

        permissions["screen_recording"] = PermissionInfo(
            type=PermissionType.SCREEN_RECORDING,
            status=PermissionStatus.GRANTED,
            name="屏幕截图",
            description="Linux 系统可能需要 X11 权限",
            required=False,
            system_settings_path=""
        )

        return PermissionsCheckResponse(
            all_granted=True,
            permissions=permissions,
            platform="Linux",
            needs_restart=False
        )

    def open_system_settings(self, permission_type: PermissionType) -> bool:
        """打开系统设置对应的权限页面"""
        if self.platform != "Darwin":
            logger.warning(f"{self.platform} 不支持自动打开系统设置")
            return False

        try:
            if permission_type == PermissionType.ACCESSIBILITY:
                # 打开辅助功能设置
                subprocess.run([
                    "open",
                    "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
                ])
                return True
            elif permission_type == PermissionType.SCREEN_RECORDING:
                # 打开屏幕录制设置
                subprocess.run([
                    "open",
                    "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture"
                ])
                return True
            else:
                logger.warning(f"未知的权限类型: {permission_type}")
                return False

        except Exception as e:
            logger.error(f"打开系统设置失败: {e}")
            return False

    def request_accessibility_permission(self) -> bool:
        """请求辅助功能权限（会弹出系统提示）"""
        if self.platform != "Darwin":
            return True

        try:
            from ApplicationServices import (
                AXIsProcessTrustedWithOptions,
                kAXTrustedCheckOptionPrompt
            )

            # 检查并请求权限（带提示）
            is_trusted = AXIsProcessTrustedWithOptions({
                kAXTrustedCheckOptionPrompt: True
            })

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
