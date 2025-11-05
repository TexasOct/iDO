"""Live2D configuration handlers."""

from __future__ import annotations

from typing import Any, Dict, List
from pathlib import Path
import asyncio

from core.settings import get_settings

from . import api_handler
from models.requests import UpdateLive2DSettingsRequest


def _scan_local_models(model_dir: str) -> List[Dict[str, str]]:
    """Scan local model directory for Live2D model definition files."""
    if not model_dir:
        return []

    path_obj = Path(model_dir).expanduser()
    if not path_obj.exists():
        return []

    patterns = ["**/*.model3.json", "**/*.model.json", "**/index.json"]
    results: List[Dict[str, str]] = []

    for pattern in patterns:
        for file_path in path_obj.glob(pattern):
            if not file_path.is_file():
                continue
            try:
                display_name = file_path.stem
                results.append(
                    {
                        "url": file_path.as_posix(),
                        "type": "local",
                        "name": display_name,
                    }
                )
            except Exception:
                continue

    # Remove duplicates by url while keeping order
    unique: Dict[str, Dict[str, str]] = {}
    for item in results:
        unique[item["url"]] = item
    return list(unique.values())


@api_handler(method="GET")
async def get_live2d_settings() -> Dict[str, Any]:
    """Get Live2D configuration."""
    settings = get_settings()
    live2d_settings = settings.get_live2d_settings()

    local_models = await asyncio.to_thread(
        _scan_local_models, live2d_settings.get("model_dir", "")
    )

    return {
        "success": True,
        "data": {
            "settings": live2d_settings,
            "models": {
                "local": local_models,
                "remote": [
                    {"url": url, "type": "remote", "name": url.split("/")[-1]}
                    for url in live2d_settings.get("remote_models", [])
                ],
            },
        },
    }


@api_handler(body=UpdateLive2DSettingsRequest)
async def update_live2d_settings(body: UpdateLive2DSettingsRequest) -> Dict[str, Any]:
    """Update Live2D configuration values."""
    settings = get_settings()
    updated = settings.update_live2d_settings(body.model_dump(exclude_none=True))

    local_models = await asyncio.to_thread(
        _scan_local_models, updated.get("model_dir", "")
    )

    return {
        "success": True,
        "message": "Live2D settings updated",
        "data": {
            "settings": updated,
            "models": {
                "local": local_models,
                "remote": [
                    {"url": url, "type": "remote", "name": url.split("/")[-1]}
                    for url in updated.get("remote_models", [])
                ],
            },
        },
    }
