"""
Monitoring module API handlers

This module consolidates handlers for:
- Screen/monitor management: Monitor discovery, screen settings, preview capture
- Perception layer control: Perception module lifecycle, records management
- System permissions: Permission checks, system settings access, app restart
"""

import asyncio
import base64
import io
import os
import sys
from datetime import datetime
from datetime import datetime as dt
from typing import Any, Dict, List, Optional, Protocol, Sequence, cast

import mss
from core.events import emit_monitors_changed
from core.logger import get_logger
from core.settings import get_settings
from models import GetRecordsRequest
from models.base import BaseModel, OperationResponse
from models.permissions import (
    OpenSystemSettingsRequest,
    PermissionsCheckResponse,
    RestartAppRequest,
)
from PIL import Image
from system.permissions import get_permission_checker

from . import api_handler

logger = get_logger(__name__)


# ============================================================================
# Screen Management - Models and State
# ============================================================================

# Auto-refresh state
_auto_refresh_task: Optional[asyncio.Task] = None
_last_monitors_signature: Optional[str] = None
_refresh_interval_seconds: float = 10.0


class StartMonitorsAutoRefreshRequest(BaseModel):
    """Request to start monitors auto refresh."""

    interval_seconds: float | None = None


class ScreenSetting(BaseModel):
    """Single screen setting."""

    monitor_index: int
    monitor_name: str = ""
    is_enabled: bool = False
    resolution: str = ""
    is_primary: bool = False


class UpdateScreenSettingsRequest(BaseModel):
    """Request to update screen capture settings."""

    screens: List[ScreenSetting]


class UpdatePerceptionSettingsRequest(BaseModel):
    """Request to update perception settings."""

    keyboard_enabled: bool | None = None
    mouse_enabled: bool | None = None


# ============================================================================
# Screen Management - Helper Functions
# ============================================================================


def _signature_for_monitors(monitors: List[Dict[str, Any]]) -> str:
    """Generate a stable signature for current monitor layout."""
    # Normalize and sort by index to create a compact signature
    normalized = [
        (
            int(m.get("index", 0)),
            int(m.get("width", 0)),
            int(m.get("height", 0)),
            int(m.get("left", 0)),
            int(m.get("top", 0)),
        )
        for m in monitors
    ]
    normalized.sort(key=lambda x: x[0])
    return repr(tuple(normalized))


async def _auto_refresh_loop() -> None:
    """Background loop that polls monitors and emits change events."""
    global _last_monitors_signature
    # Initialize signature on first run to avoid spurious "change" events at startup
    first_run = True
    while True:
        try:
            monitors = _list_monitors()
            signature = _signature_for_monitors(monitors)
            if first_run:
                _last_monitors_signature = signature
                first_run = False
                logger.debug(f"Monitor auto-refresh started, current signature: {signature}")
            elif signature != _last_monitors_signature:
                _last_monitors_signature = signature
                emit_monitors_changed(monitors)
                logger.debug("Monitors changed detected, event emitted")
        except Exception as exc:
            logger.error(f"Monitor auto-refresh loop error: {exc}")
        await asyncio.sleep(max(1.0, float(_refresh_interval_seconds)))


def _list_monitors() -> List[Dict[str, Any]]:
    """Enumerate monitors using mss and return normalized info list."""
    info: List[Dict[str, Any]] = []
    with mss.mss() as sct:
        # mss.monitors[0] is the virtual bounding box of all monitors
        for idx, m in enumerate(sct.monitors[1:], start=1):
            width = int(m.get("width", 0))
            height = int(m.get("height", 0))
            left = int(m.get("left", 0))
            top = int(m.get("top", 0))
            # mss doesn't provide names; synthesize a friendly one
            name = f"Display {idx}"
            is_primary = idx == 1
            info.append(
                {
                    "index": idx,
                    "name": name,
                    "width": width,
                    "height": height,
                    "left": left,
                    "top": top,
                    "is_primary": is_primary,
                    "resolution": f"{width}x{height}",
                }
            )
    return info


# ============================================================================
# Screen Management - API Handlers
# ============================================================================


@api_handler()
async def get_monitors() -> Dict[str, Any]:
    """Get available monitors information.

    Returns information about all available monitors including resolution and position.

    @returns Monitors data with success flag and timestamp
    """
    monitors = _list_monitors()
    return {
        "success": True,
        "data": {"monitors": monitors, "count": len(monitors)},
        "timestamp": datetime.now().isoformat(),
    }


@api_handler(body=StartMonitorsAutoRefreshRequest)
async def start_monitors_auto_refresh(
    body: StartMonitorsAutoRefreshRequest,
) -> Dict[str, Any]:
    """Start background auto-refresh for monitors detection.

    Body:
      - interval_seconds: float (optional, default 10.0)
    """
    global _auto_refresh_task, _refresh_interval_seconds

    interval = body.interval_seconds
    if interval is not None:
        try:
            _refresh_interval_seconds = max(1.0, float(interval))
        except Exception:
            return {
                "success": False,
                "error": "interval_seconds must be a number",
                "timestamp": datetime.now().isoformat(),
            }

    # Restart if already running
    task = _auto_refresh_task
    if task is not None and not task.done():
        task.cancel()
        try:
            await asyncio.sleep(0)
        except Exception:
            pass
        _auto_refresh_task = None

    _auto_refresh_task = asyncio.create_task(_auto_refresh_loop())
    return {
        "success": True,
        "data": {
            "running": True,
            "intervalSeconds": _refresh_interval_seconds,
        },
        "timestamp": datetime.now().isoformat(),
    }


@api_handler()
async def stop_monitors_auto_refresh() -> Dict[str, Any]:
    """Stop background auto-refresh for monitors detection."""
    global _auto_refresh_task
    task = _auto_refresh_task
    if task is not None and not task.done():
        task.cancel()
        try:
            await asyncio.sleep(0)
        except Exception:
            pass
    _auto_refresh_task = None
    return {
        "success": True,
        "data": {"running": False},
        "timestamp": datetime.now().isoformat(),
    }


@api_handler()
async def get_monitors_auto_refresh_status() -> Dict[str, Any]:
    """Get background auto-refresh status."""
    running = _auto_refresh_task is not None and not _auto_refresh_task.done()
    return {
        "success": True,
        "data": {
            "running": running,
            "intervalSeconds": _refresh_interval_seconds,
        },
        "timestamp": datetime.now().isoformat(),
    }


@api_handler()
async def get_screen_settings() -> Dict[str, Any]:
    """Get screen capture settings.

    Returns current screen capture settings from config.
    """
    settings = get_settings()
    screens = settings.get("screenshot.screen_settings", []) or []
    return {
        "success": True,
        "data": {"screens": screens, "count": len(screens)},
        "timestamp": datetime.now().isoformat(),
    }


@api_handler()
async def capture_all_previews() -> Dict[str, Any]:
    """Capture preview thumbnails for all monitors.

    Generates small preview images for all connected monitors to help users
    identify which screen is which when configuring screenshot settings.
    """
    previews: List[Dict[str, Any]] = []
    total = 0
    try:
        with mss.mss() as sct:
            for idx, m in enumerate(sct.monitors[1:], start=1):
                shot = sct.grab(m)
                img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
                # Downscale to a reasonable thumbnail height
                target_h = 240
                if img.height > target_h:
                    ratio = target_h / img.height
                    img = img.resize(
                        (int(img.width * ratio), target_h), Image.Resampling.LANCZOS
                    )
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=70)
                b64 = base64.b64encode(buf.getvalue()).decode("ascii")
                previews.append(
                    {
                        "monitor_index": idx,
                        "width": img.width,
                        "height": img.height,
                        "image_base64": b64,
                    }
                )
                total += 1
        return {
            "success": True,
            "data": {"total_count": total, "previews": previews},
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to capture previews: {e}",
            "timestamp": datetime.now().isoformat(),
        }


@api_handler(body=UpdateScreenSettingsRequest)
async def update_screen_settings(
    body: UpdateScreenSettingsRequest,
) -> Dict[str, Any]:
    """Update screen capture settings.

    Updates which screens should be captured for screenshots.
    """
    screens = body.screens
    # Basic normalization: keep needed fields only
    normalized: List[Dict[str, Any]] = []
    for s in screens:
        try:
            normalized.append(
                {
                    "monitor_index": int(s.monitor_index),
                    "monitor_name": s.monitor_name,
                    "is_enabled": bool(s.is_enabled),
                    "resolution": s.resolution,
                    "is_primary": bool(s.is_primary),
                }
            )
        except Exception:
            # skip invalid entry
            continue

    settings = get_settings()
    settings.set("screenshot.screen_settings", normalized)
    return {
        "success": True,
        "message": "Screen settings updated",
        "data": {"count": len(normalized)},
        "timestamp": datetime.now().isoformat(),
    }


@api_handler()
async def get_perception_settings() -> Dict[str, Any]:
    """Get perception settings.

    Returns current keyboard and mouse perception settings.
    """
    settings = get_settings()
    keyboard_enabled = settings.get("perception.keyboard_enabled", True)
    mouse_enabled = settings.get("perception.mouse_enabled", True)

    return {
        "success": True,
        "data": {
            "keyboard_enabled": keyboard_enabled,
            "mouse_enabled": mouse_enabled,
        },
        "timestamp": datetime.now().isoformat(),
    }


@api_handler(body=UpdatePerceptionSettingsRequest)
async def update_perception_settings(
    body: UpdatePerceptionSettingsRequest,
) -> Dict[str, Any]:
    """Update perception settings.

    Updates which perception inputs (keyboard/mouse) should be monitored.
    """
    keyboard_enabled = body.keyboard_enabled
    mouse_enabled = body.mouse_enabled

    if keyboard_enabled is None and mouse_enabled is None:
        return {
            "success": False,
            "error": "No settings provided",
            "timestamp": datetime.now().isoformat(),
        }

    settings = get_settings()

    if keyboard_enabled is not None:
        settings.set("perception.keyboard_enabled", bool(keyboard_enabled))

    if mouse_enabled is not None:
        settings.set("perception.mouse_enabled", bool(mouse_enabled))

    return {
        "success": True,
        "message": "Perception settings updated",
        "data": {
            "keyboard_enabled": settings.get("perception.keyboard_enabled", True),
            "mouse_enabled": settings.get("perception.mouse_enabled", True),
        },
        "timestamp": datetime.now().isoformat(),
    }


# ============================================================================
# Perception Control - Protocol and Helper
# ============================================================================


class PerceptionManagerProtocol(Protocol):
    is_running: bool
    storage: Any

    def get_stats(self) -> Dict[str, Any]: ...

    def get_records_by_type(self, event_type: str) -> Sequence[Any]: ...

    def get_records_in_timeframe(
        self, start: datetime, end: datetime
    ) -> Sequence[Any]: ...

    def get_recent_records(self, limit: int) -> Sequence[Any]: ...

    async def start(self) -> None: ...

    async def stop(self) -> None: ...

    def clear_buffer(self) -> None: ...

    def get_buffered_events(self) -> Sequence[Any]: ...


def _get_perception_manager() -> PerceptionManagerProtocol:
    from core.coordinator import get_coordinator

    coordinator = get_coordinator()
    manager = getattr(coordinator, "perception_manager", None)
    if manager is None:
        raise RuntimeError("Perception manager is not initialized")
    return cast(PerceptionManagerProtocol, manager)


# ============================================================================
# Perception Control - API Handlers
# ============================================================================


@api_handler()
async def get_perception_stats() -> Dict[str, Any]:
    """Get perception module statistics.

    Returns statistics about the perception module including record counts and status.

    @returns Statistics data with success flag and timestamp
    """
    manager = _get_perception_manager()
    stats = manager.get_stats()

    return {"success": True, "data": stats, "timestamp": datetime.now().isoformat()}


@api_handler(body=GetRecordsRequest)
async def get_records(body: GetRecordsRequest) -> Dict[str, Any]:
    """Get perception records with optional filters.

    @param body - Request parameters including limit and filters.
    @returns Records data with success flag and timestamp
    """
    manager = _get_perception_manager()

    # Parse datetime if provided
    start_dt = datetime.fromisoformat(body.start_time) if body.start_time else None
    end_dt = datetime.fromisoformat(body.end_time) if body.end_time else None

    if body.event_type:
        records = manager.get_records_by_type(body.event_type)
    elif start_dt and end_dt:
        records = manager.get_records_in_timeframe(start_dt, end_dt)
    else:
        records = manager.get_recent_records(body.limit)

    # Convert to dict format
    records_data = []
    for record in records:
        record_dict = {
            "timestamp": record.timestamp.isoformat(),
            "type": record.type.value,
            "data": record.data,
        }
        records_data.append(record_dict)

    return {
        "success": True,
        "data": {
            "records": records_data,
            "count": len(records_data),
            "filters": {
                "limit": body.limit,
                "eventType": body.event_type,
                "startTime": body.start_time,
                "endTime": body.end_time,
            },
        },
        "timestamp": datetime.now().isoformat(),
    }


@api_handler()
async def start_perception() -> Dict[str, Any]:
    """Start the perception module.

    Starts monitoring keyboard, mouse, and screenshots.

    @returns Success response with message and timestamp
    """
    manager = _get_perception_manager()

    if manager.is_running:
        return {
            "success": True,
            "message": "Perception module is already running",
            "timestamp": datetime.now().isoformat(),
        }

    await manager.start()
    return {
        "success": True,
        "message": "Perception module started",
        "timestamp": datetime.now().isoformat(),
    }


@api_handler()
async def stop_perception() -> Dict[str, Any]:
    """Stop the perception module.

    Stops monitoring keyboard, mouse, and screenshots.

    @returns Success response with message and timestamp
    """
    manager = _get_perception_manager()

    if not manager.is_running:
        return {
            "success": True,
            "message": "Perception module not running",
            "timestamp": datetime.now().isoformat(),
        }

    await manager.stop()
    return {
        "success": True,
        "message": "Perception module stopped",
        "timestamp": datetime.now().isoformat(),
    }


@api_handler()
async def clear_records() -> Dict[str, Any]:
    """Clear all perception records.

    Removes all stored records and clears the buffer.

    @returns Success response with message and timestamp
    """
    manager = _get_perception_manager()

    manager.storage.clear()
    manager.clear_buffer()

    return {
        "success": True,
        "message": "All records cleared",
        "timestamp": datetime.now().isoformat(),
    }


@api_handler()
async def get_buffered_events() -> Dict[str, Any]:
    """Get buffered events.

    Returns events currently in the buffer waiting to be processed.

    @returns Buffered events data with success flag and timestamp
    """
    manager = _get_perception_manager()

    events = manager.get_buffered_events()

    events_data = []
    for event in events:
        event_dict = {
            "timestamp": event.timestamp.isoformat(),
            "type": event.type.value,
            "data": event.data,
        }
        events_data.append(event_dict)

    return {
        "success": True,
        "data": {"events": events_data, "count": len(events_data)},
        "timestamp": datetime.now().isoformat(),
    }


# ============================================================================
# Permissions - Models
# ============================================================================


class OpenSystemSettingsResponse(OperationResponse):
    """Response for opening system settings"""


class AccessibilityPermissionResponse(OperationResponse):
    """Response for requesting accessibility permission"""

    granted: bool | None = None


class RestartAppResponse(OperationResponse):
    """Response for restarting the application"""

    delay_seconds: int | None = None
    timestamp: str = ""


# ============================================================================
# Permissions - API Handlers
# ============================================================================


@api_handler(method="GET", path="/permissions/check", tags=["permissions"])
async def check_permissions() -> PermissionsCheckResponse:
    """
    Check all required system permissions

    Returns:
        Permission check results, including status of each permission
    """
    try:
        checker = get_permission_checker()
        result = checker.check_all_permissions()

        logger.debug(f"Permission check completed: all_granted={result.all_granted}")

        return result

    except Exception as e:
        logger.error(f"Permission check failed: {e}")
        raise


@api_handler(
    body=OpenSystemSettingsRequest,
    method="POST",
    path="/permissions/open-settings",
    tags=["permissions"],
)
async def open_system_settings(
    body: OpenSystemSettingsRequest,
) -> OpenSystemSettingsResponse:
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
            logger.debug(f"Opened system settings: {body.permission_type}")
            return OpenSystemSettingsResponse(
                success=True,
                message=f"Opened {body.permission_type} permission settings page",
            )

        return OpenSystemSettingsResponse(
            success=False, message="Failed to open system settings"
        )

    except Exception as e:
        logger.error(f"Failed to open system settings: {e}")
        return OpenSystemSettingsResponse(success=False, message=str(e))


@api_handler(path="/permissions/request-accessibility", tags=["permissions"])
async def request_accessibility_permission() -> AccessibilityPermissionResponse:
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
            logger.debug("Accessibility permission granted")
            return AccessibilityPermissionResponse(
                success=True,
                granted=True,
                message="Accessibility permission granted",
            )

        logger.warning("Accessibility permission not granted")
        return AccessibilityPermissionResponse(
            success=True,
            granted=False,
            message="Please manually grant permission in system settings",
        )

    except Exception as e:
        logger.error(f"Failed to request accessibility permission: {e}")
        return AccessibilityPermissionResponse(
            success=False, granted=False, message=str(e)
        )


@api_handler(
    body=RestartAppRequest,
    method="POST",
    path="/permissions/restart-app",
    tags=["permissions"],
)
async def restart_app(body: RestartAppRequest) -> RestartAppResponse:
    """
    Restart application

    Args:
        body: Request containing delay time

    Returns:
        Operation result
    """
    try:
        delay = max(0, min(10, body.delay_seconds))  # Limit to 0-10 seconds

        logger.debug(f"Application will restart in {delay} seconds...")

        # Execute restart asynchronously
        asyncio.create_task(_restart_app_delayed(delay))

        return RestartAppResponse(
            success=True,
            message=f"Application will restart in {delay} seconds",
            delay_seconds=delay,
            timestamp=dt.now().isoformat(),
        )

    except Exception as e:
        logger.error(f"Failed to restart application: {e}")
        return RestartAppResponse(success=False, message=str(e))


async def _restart_app_delayed(delay: float):
    """Delayed restart application"""
    try:
        await asyncio.sleep(delay)

        logger.debug("Restarting application...")

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
                logger.debug(f"Reopening application: {app_path}")

                # Use open command to restart application
                import subprocess

                subprocess.Popen(["open", "-n", app_path])
            else:
                # Direct executable
                import subprocess

                subprocess.Popen([executable] + sys.argv)

            # Exit the current process after relaunch to ensure the restart is visible
            await asyncio.sleep(0.5)
            os._exit(0)
        else:
            # Windows/Linux
            import subprocess

            subprocess.Popen([executable] + sys.argv)

            # Exit current process
            await asyncio.sleep(0.5)
            os._exit(0)

    except Exception as e:
        logger.error(f"Delayed restart failed: {e}")
