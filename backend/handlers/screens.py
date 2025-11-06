"""
Screen/monitor related command handlers
Provide monitor list, screen settings CRUD, and preview capture
"""

from typing import Dict, Any, List
from datetime import datetime
import base64
import io

from PIL import Image
import mss

from . import api_handler
from core.settings import get_settings


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
                    img = img.resize((int(img.width * ratio), target_h), Image.Resampling.LANCZOS)
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

