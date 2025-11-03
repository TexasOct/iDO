"""
权限相关的 Pydantic 模型
"""

from enum import Enum
from typing import Dict
from .base import BaseModel


class PermissionType(str, Enum):
    """权限类型枚举"""
    ACCESSIBILITY = "accessibility"  # 辅助功能权限 (键盘和鼠标监听)
    SCREEN_RECORDING = "screen_recording"  # 屏幕录制权限


class PermissionStatus(str, Enum):
    """权限状态"""
    GRANTED = "granted"  # 已授权
    DENIED = "denied"  # 已拒绝
    NOT_DETERMINED = "not_determined"  # 未确定（未请求过）
    RESTRICTED = "restricted"  # 受限制


class PermissionInfo(BaseModel):
    """单个权限信息"""
    type: PermissionType
    status: PermissionStatus
    name: str  # 权限显示名称
    description: str  # 权限描述
    required: bool  # 是否必需
    system_settings_path: str  # 系统设置路径提示


class PermissionsCheckResponse(BaseModel):
    """权限检查响应"""
    all_granted: bool
    permissions: Dict[str, PermissionInfo]
    platform: str
    needs_restart: bool  # 是否需要重启


class OpenSystemSettingsRequest(BaseModel):
    """打开系统设置请求"""
    permission_type: PermissionType


class RestartAppRequest(BaseModel):
    """重启应用请求"""
    delay_seconds: int = 1  # 延迟秒数
