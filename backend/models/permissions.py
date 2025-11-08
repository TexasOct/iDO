"""
Permission-related Pydantic models
"""

from enum import Enum
from typing import Dict

from pydantic import ConfigDict

from .base import BaseModel


class PermissionType(str, Enum):
    """Permission type enumeration"""

    ACCESSIBILITY = (
        "accessibility"  # Accessibility permissions (keyboard and mouse monitoring)
    )
    SCREEN_RECORDING = "screen_recording"  # Screen recording permissions


class PermissionStatus(str, Enum):
    """Permission status"""

    GRANTED = "granted"  # Granted
    DENIED = "denied"  # Denied
    NOT_DETERMINED = "not_determined"  # Not determined (not requested yet)
    RESTRICTED = "restricted"  # Restricted


class PermissionInfo(BaseModel):
    """Single permission information"""

    # Merge parent config with use_enum_values=True to serialize enums as strings
    model_config = ConfigDict(
        **BaseModel.model_config,
        use_enum_values=True
    )

    type: PermissionType
    status: PermissionStatus
    name: str  # Permission display name
    description: str  # Permission description
    required: bool  # Whether required
    system_settings_path: str  # System settings path hint


class PermissionsCheckResponse(BaseModel):
    """Permission check response"""

    # Merge parent config with use_enum_values=True to serialize enums as strings
    model_config = ConfigDict(
        **BaseModel.model_config,
        use_enum_values=True
    )

    all_granted: bool
    permissions: Dict[str, PermissionInfo]
    platform: str
    needs_restart: bool  # Whether restart is needed


class OpenSystemSettingsRequest(BaseModel):
    """Open system settings request"""

    permission_type: PermissionType


class RestartAppRequest(BaseModel):
    """Restart app request"""

    delay_seconds: int = 1  # Delay in seconds
