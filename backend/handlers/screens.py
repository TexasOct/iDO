"""
Screen/monitor related command handlers
Provide monitor list, screen settings CRUD, and preview capture
"""

import asyncio
import base64
import io
from datetime import datetime
from typing import Any, Dict, List, Optional

import mss
from core.events import emit_monitors_changed
from core.logger import get_logger
from core.settings import get_settings
from PIL import Image

from . import api_handler

logger = get_logger(__name__)

# Auto-refresh state
_auto_refresh_task: Optional[asyncio.Task] = None
_last_monitors_signature: Optional[str] = None
_refresh_interval_seconds: float = 10.0


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
    while True:
        try:
            monitors = _list_monitors()
            signature = _signature_for_monitors(monitors)
            if signature != _last_monitors_signature:
                _last_monitors_signature = signature
                emit_monitors_changed(monitors)
                logger.info("Monitors changed detected, event emitted")
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


@api_handler()
async def start_monitors_auto_refresh(body: Dict[str, Any]) -> Dict[str, Any]:
    """Start background auto-refresh for monitors detection.

    Body:
      - interval_seconds: float (optional, default 10.0)
    """
    global _auto_refresh_task, _refresh_interval_seconds

    interval = body.get("interval_seconds")
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


@api_handler()
async def update_screen_settings(body: Dict[str, Any]) -> Dict[str, Any]:
    """Update screen capture settings.

    Updates which screens should be captured for screenshots.
    """
    screens = body.get("screens") or []
    if not isinstance(screens, list):
        return {
            "success": False,
            "error": "Invalid payload: screens must be a list",
            "timestamp": datetime.now().isoformat(),
        }

    # Basic normalization: keep needed fields only
    normalized: List[Dict[str, Any]] = []
    for s in screens:
        try:
            normalized.append(
                {
                    "monitor_index": int(s.get("monitor_index")),
                    "monitor_name": str(s.get("monitor_name", "")),
                    "is_enabled": bool(s.get("is_enabled", False)),
                    "resolution": str(s.get("resolution", "")),
                    "is_primary": bool(s.get("is_primary", False)),
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


@api_handler()
async def update_perception_settings(body: Dict[str, Any]) -> Dict[str, Any]:
    """Update perception settings.

    Updates which perception inputs (keyboard/mouse) should be monitored.
    """
    keyboard_enabled = body.get("keyboard_enabled")
    mouse_enabled = body.get("mouse_enabled")

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
