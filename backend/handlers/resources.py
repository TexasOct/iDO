"""
Resource Management API Handlers

This module handles three main categories of resources:
1. Image Management - Image caching, cleanup, optimization, and statistics
2. LLM Model Management - Model configurations, activation, testing, and API connections
3. Dashboard & Statistics - LLM usage tracking, trends, and system statistics
"""

import base64
import os
import uuid
from datetime import datetime
from typing import Any, Dict

import httpx
from core.coordinator import get_coordinator
from core.dashboard.manager import get_dashboard_manager
from core.db import get_db
from core.logger import get_logger
from core.settings import get_settings
from models.base import OperationResponse, TimedOperationResponse
from models.requests import (
    CleanupImagesRequest,
    CreateModelRequest,
    DeleteModelRequest,
    GetImagesRequest,
    GetLLMStatsByModelRequest,
    GetLLMUsageTrendRequest,
    ImageOptimizationConfigRequest,
    ReadImageFileRequest,
    RecordLLMUsageRequest,
    SelectModelRequest,
    TestModelRequest,
    UpdateModelRequest,
)
from models.responses import (
    CachedImagesResponse,
    CleanupImagesResponse,
    ClearMemoryCacheResponse,
    ImageOptimizationConfigResponse,
    ImageOptimizationStatsResponse,
    ImageStatsResponse,
    ReadImageFileResponse,
    UpdateImageOptimizationConfigResponse,
)
from processing.image_manager import get_image_manager
from processing.image_processing import get_image_processor
from system.runtime import start_runtime, stop_runtime

from . import api_handler

logger = get_logger(__name__)


# ============================================================================
# Response Models
# ============================================================================


class ModelOperationResponse(OperationResponse):
    """Generic model management response with optional payload and timestamp."""

    data: Dict[str, Any] | list[Dict[str, Any]] | None = None
    timestamp: str | None = None


class DashboardResponse(TimedOperationResponse):
    """Standard dashboard response with optional data payload."""


class LLMUsageTrendResponse(TimedOperationResponse):
    """Dashboard trend response with dimension metadata."""

    dimension: str | None = None
    days: int | None = None


# ============================================================================
# Image Management
# ============================================================================


@api_handler(body=None, method="GET", path="/image/stats", tags=["image"])
async def get_image_stats() -> ImageStatsResponse:
    """
    Get image cache statistics

    Returns:
        Image cache and disk usage statistics
    """
    try:
        image_manager = get_image_manager()
        stats = image_manager.get_cache_stats()
        return ImageStatsResponse(success=True, stats=stats)
    except Exception as e:
        logger.error(f"Failed to get image statistics: {e}")
        return ImageStatsResponse(success=False, error=str(e))


@api_handler(
    body=GetImagesRequest, method="POST", path="/image/get-cached", tags=["image"]
)
async def get_cached_images(body: GetImagesRequest) -> CachedImagesResponse:
    """
    Batch get images from memory (base64 format)

    Args:
        body: Request containing image hash list

    Returns:
        Response containing base64 image data
    """
    try:
        image_manager = get_image_manager()
        images = image_manager.get_multiple_from_cache(body.hashes)
        missing_hashes = [
            img_hash for img_hash in body.hashes if img_hash not in images
        ]

        # Fallback: try to load thumbnails from disk
        if missing_hashes:
            for img_hash in missing_hashes:
                try:
                    base64_data = image_manager.load_thumbnail_base64(img_hash)
                    if base64_data:
                        images[img_hash] = base64_data
                except Exception as e:
                    logger.warning(
                        f"Failed to load image from disk: {img_hash[:8]} - {e}"
                    )

        return CachedImagesResponse(
            success=True,
            images=images,
            found_count=len(images),
            requested_count=len(body.hashes),
        )
    except Exception as e:
        logger.error(f"Failed to get cached images: {e}")
        return CachedImagesResponse(
            success=False,
            images={},
            found_count=0,
            requested_count=len(body.hashes),
            error=str(e),
        )


@api_handler(
    body=CleanupImagesRequest, method="POST", path="/image/cleanup", tags=["image"]
)
async def cleanup_old_images(body: CleanupImagesRequest) -> CleanupImagesResponse:
    """
    Clean up old image files

    Args:
        body: Request containing maximum retention time

    Returns:
        Cleanup result statistics
    """
    try:
        image_manager = get_image_manager()
        cleaned_count = image_manager.cleanup_old_files(body.max_age_hours)

        return CleanupImagesResponse(
            success=True,
            cleaned_count=cleaned_count,
            message=f"Cleaned up {cleaned_count} old image files",
        )
    except Exception as e:
        logger.error(f"Failed to clean up images: {e}")
        return CleanupImagesResponse(success=False, error=str(e))


@api_handler(body=None, method="POST", path="/image/clear-cache", tags=["image"])
async def clear_memory_cache() -> ClearMemoryCacheResponse:
    """
    Clear memory cache

    Returns:
        Cleanup result
    """
    try:
        image_manager = get_image_manager()
        count = image_manager.clear_memory_cache()

        return ClearMemoryCacheResponse(
            success=True,
            cleared_count=count,
            message=f"Cleared {count} memory cached images",
        )
    except Exception as e:
        logger.error(f"Failed to clear memory cache: {e}")
        return ClearMemoryCacheResponse(success=False, error=str(e))


@api_handler(
    body=None,
    method="GET",
    path="/image/optimization/config",
    tags=["image", "optimization"],
)
async def get_image_optimization_config() -> ImageOptimizationConfigResponse:
    """
    Get image optimization configuration

    Returns:
        Current image optimization configuration
    """
    try:
        settings = get_settings()
        config = settings.get_image_optimization_config()

        return ImageOptimizationConfigResponse(success=True, config=config)
    except Exception as e:
        logger.error(f"Failed to get image optimization configuration: {e}")
        return ImageOptimizationConfigResponse(success=False, error=str(e))


@api_handler(
    body=None,
    method="GET",
    path="/image/optimization/stats",
    tags=["image", "optimization"],
)
async def get_image_optimization_stats() -> ImageOptimizationStatsResponse:
    """
    Get image optimization statistics

    Returns:
        Information including sampling statistics, skip reason distribution, etc.
    """
    try:
        image_processor = get_image_processor()
        stats_summary = image_processor.get_stats()

        # Get configuration
        settings = get_settings()
        config = settings.get_image_optimization_config()

        # Map new stats format to old format for backward compatibility
        optimization_stats = {
            "total_images": stats_summary.get("images_processed", 0),
            "included_images": stats_summary.get("images_included", 0),
            "skipped_images": stats_summary.get("images_skipped", 0),
            "skip_breakdown": stats_summary.get("skip_reasons", {}),
        }
        if "tokens" in stats_summary:
            optimization_stats["estimated_tokens_saved"] = stats_summary["tokens"].get("saved", 0)

        return ImageOptimizationStatsResponse(
            success=True,
            stats={
                "optimization": optimization_stats,
                "diff_analyzer": stats_summary.get("deduplication", {}),
                "content_analyzer": stats_summary.get("content_analysis", {}),
                "sampler": stats_summary.get("sampling", {}),
            },
            config=config,
        )
    except Exception as e:
        logger.error(f"Failed to get image optimization statistics: {e}")
        return ImageOptimizationStatsResponse(success=False, error=str(e))


@api_handler(
    body=ImageOptimizationConfigRequest,
    method="POST",
    path="/image/optimization/config",
    tags=["image", "optimization"],
)
async def update_image_optimization_config(
    body: ImageOptimizationConfigRequest,
) -> UpdateImageOptimizationConfigResponse:
    """
    Update image optimization configuration

    Args:
        body: Request body containing optimization configuration

    Returns:
        Update result and current configuration
    """
    try:
        settings = get_settings()
        config_dict = {
            "enabled": body.enabled,
            "strategy": body.strategy,
            "phash_threshold": body.phash_threshold,
            "min_interval": body.min_interval,
            "max_images": body.max_images,
            "enable_content_analysis": body.enable_content_analysis,
            "enable_text_detection": body.enable_text_detection,
        }

        success = settings.set_image_optimization_config(config_dict)

        if success:
            # Reinitialize image processor to apply new configuration
            try:
                from processing.image_processing import get_image_processor

                get_image_processor(reset=True)
                logger.debug("Image processor has been reinitialized")
            except Exception as e:
                logger.warning(f"Failed to reinitialize image processor: {e}")

            return UpdateImageOptimizationConfigResponse(
                success=True,
                message="Image optimization configuration updated",
                config=config_dict,
            )

        return UpdateImageOptimizationConfigResponse(
            success=False, error="Configuration update failed"
        )
    except Exception as e:
        logger.error(f"Failed to update image optimization configuration: {e}")
        return UpdateImageOptimizationConfigResponse(success=False, error=str(e))


@api_handler(
    body=ReadImageFileRequest,
    method="POST",
    path="/image/read-file",
    tags=["image"],
)
async def read_image_file(body: ReadImageFileRequest) -> ReadImageFileResponse:
    """
    Read image file and return as base64 encoded data URL

    Args:
        body: Request containing file path

    Returns:
        Response with base64 data URL
    """
    try:
        file_path = body.file_path

        # Check if file exists
        if not os.path.exists(file_path):
            logger.warning(f"Image file not found: {file_path}")
            return ReadImageFileResponse(
                success=False, error=f"File not found: {file_path}"
            )

        # Read file and convert to base64
        with open(file_path, "rb") as f:
            file_data = f.read()
            base64_data = base64.b64encode(file_data).decode("utf-8")

            # Detect MIME type from extension
            ext = file_path.split(".")[-1].lower()
            mime_type_map = {
                "png": "image/png",
                "jpg": "image/jpeg",
                "jpeg": "image/jpeg",
                "gif": "image/gif",
                "webp": "image/webp",
            }
            mime_type = mime_type_map.get(ext, "image/png")

            # Return as data URL
            data_url = f"data:{mime_type};base64,{base64_data}"
            logger.debug(f"Read image file: {file_path}")

            return ReadImageFileResponse(success=True, data_url=data_url)
    except Exception as e:
        logger.error(f"Failed to read image file: {e}")
        return ReadImageFileResponse(success=False, error=str(e))


# ============================================================================
# Model Management
# ============================================================================


@api_handler(body=CreateModelRequest)
async def create_model(body: CreateModelRequest) -> ModelOperationResponse:
    """Create new model configuration

    @param body Model configuration information (includes API key)
    @returns Created model information
    """
    try:
        db = get_db()

        # Generate unique ID
        model_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        # Use repository to insert model (provider always set to 'openai' for OpenAI-compatible APIs)
        db.models.insert(
            model_id=model_id,
            name=body.name,
            provider="openai",  # Always use 'openai' for OpenAI-compatible APIs
            api_url=body.api_url,
            model=body.model,
            api_key=body.api_key,
            input_token_price=body.input_token_price,
            output_token_price=body.output_token_price,
            currency=body.currency,
            is_active=False,
        )

        logger.debug(f"Model created: {model_id} ({body.name})")

        return ModelOperationResponse(
            success=True,
            message="Model created successfully",
            data={
                "id": model_id,
                "name": body.name,
                "provider": "openai",  # Always 'openai' for OpenAI-compatible APIs
                "model": body.model,
                "currency": body.currency,
                "createdAt": now,
                "isActive": False,
            },
            timestamp=now,
        )

    except Exception as e:
        logger.error(f"Failed to create model: {e}")
        return ModelOperationResponse(
            success=False,
            message=f"Failed to create model: {str(e)}",
            timestamp=datetime.now().isoformat(),
        )


@api_handler(body=UpdateModelRequest)
async def update_model(body: UpdateModelRequest) -> ModelOperationResponse:
    """Update model configuration

    @param body Model information to update (only update provided fields)
    @returns Updated model information
    """
    try:
        db = get_db()

        # Verify model exists
        existing_model = db.models.get_by_id(body.model_id)

        if not existing_model:
            return ModelOperationResponse(
                success=False,
                message=f"Model does not exist: {body.model_id}",
                timestamp=datetime.now().isoformat(),
            )

        now = datetime.now().isoformat()

        # Update model using repository (provider field not updated - always 'openai')
        db.models.update(
            model_id=body.model_id,
            name=body.name,
            provider=None,  # Don't update provider - always keep as 'openai'
            api_url=body.api_url,
            model=body.model,
            api_key=body.api_key,
            input_token_price=body.input_token_price,
            output_token_price=body.output_token_price,
            currency=body.currency,
        )

        logger.debug(
            f"Model updated: {body.model_id} ({body.name or existing_model['name']})"
        )

        # Get updated model information
        row = db.models.get_by_id(body.model_id)

        if row:
            return ModelOperationResponse(
                success=True,
                message="Model updated successfully",
                data={
                    "id": row["id"],
                    "name": row["name"],
                    "provider": row["provider"],
                    "apiUrl": row["api_url"],
                    "model": row["model"],
                    "inputTokenPrice": row["input_token_price"],
                    "outputTokenPrice": row["output_token_price"],
                    "currency": row["currency"],
                    "isActive": bool(row["is_active"]),
                    "lastTestStatus": bool(row.get("last_test_status")),
                    "lastTestedAt": row.get("last_tested_at"),
                    "lastTestError": row.get("last_test_error"),
                    "createdAt": row["created_at"],
                    "updatedAt": row["updated_at"],
                },
                timestamp=now,
            )

        return ModelOperationResponse(
            success=True,
            message="Model updated successfully",
            timestamp=now,
        )

    except Exception as e:
        logger.error(f"Failed to update model: {e}")
        return ModelOperationResponse(
            success=False,
            message=f"Failed to update model: {str(e)}",
            timestamp=datetime.now().isoformat(),
        )


@api_handler(body=DeleteModelRequest)
async def delete_model(body: DeleteModelRequest) -> ModelOperationResponse:
    """Delete model configuration

    @param body Model ID to delete
    @returns Deletion result
    """
    try:
        db = get_db()

        # Verify model exists
        model = db.models.get_by_id(body.model_id)

        if not model:
            return ModelOperationResponse(
                success=False,
                message=f"Model does not exist: {body.model_id}",
                timestamp=datetime.now().isoformat(),
            )

        was_active = bool(model["is_active"])

        # Delete model (if active model is deleted, there will be no active model after deletion)
        db.models.delete(body.model_id)

        if was_active:
            logger.debug(
                f"Active model deleted and activation status cleared: {body.model_id} ({model['name']})"
            )
        else:
            logger.debug(f"Model deleted: {body.model_id} ({model['name']})")

        return ModelOperationResponse(
            success=True,
            message=f"Model deleted: {model['name']}",
            data={"modelId": body.model_id, "modelName": model["name"]},
            timestamp=datetime.now().isoformat(),
        )

    except Exception as e:
        logger.error(f"Failed to delete model: {e}")
        return ModelOperationResponse(
            success=False,
            message=f"Failed to delete model: {str(e)}",
            timestamp=datetime.now().isoformat(),
        )


@api_handler()
async def list_models() -> ModelOperationResponse:
    """Get all model configuration list

    @returns Model list (without API keys)
    """
    try:
        db = get_db()

        results = db.models.get_all()

        models = [
            {
                "id": row["id"],
                "name": row["name"],
                "provider": row["provider"],
                "apiUrl": row["api_url"],
                "model": row["model"],
                "inputTokenPrice": row["input_token_price"],
                "outputTokenPrice": row["output_token_price"],
                "currency": row["currency"],
                "isActive": bool(row["is_active"]),
                "lastTestStatus": bool(row.get("last_test_status")),
                "lastTestedAt": row.get("last_tested_at"),
                "lastTestError": row.get("last_test_error"),
                "createdAt": row["created_at"],
                "updatedAt": row["updated_at"],
            }
            for row in results
        ]

        return ModelOperationResponse(
            success=True,
            data={"models": models, "count": len(models)},
            timestamp=datetime.now().isoformat(),
        )

    except Exception as e:
        logger.error(f"Failed to get model list: {e}")
        return ModelOperationResponse(
            success=False,
            message=f"Failed to get model list: {str(e)}",
            timestamp=datetime.now().isoformat(),
        )


@api_handler()
async def get_active_model() -> ModelOperationResponse:
    """Get currently active model information

    @returns Active model detailed information (without API key)
    """
    try:
        db = get_db()

        row = db.models.get_active()

        if not row:
            return ModelOperationResponse(
                success=False,
                message="No active model",
                timestamp=datetime.now().isoformat(),
            )

        return ModelOperationResponse(
            success=True,
            data={
                "id": row["id"],
                "name": row["name"],
                "provider": row["provider"],
                "apiUrl": row["api_url"],
                "model": row["model"],
                "inputTokenPrice": row["input_token_price"],
                "outputTokenPrice": row["output_token_price"],
                "currency": row["currency"],
                "lastTestStatus": bool(row.get("last_test_status")),
                "lastTestedAt": row.get("last_tested_at"),
                "lastTestError": row.get("last_test_error"),
                "createdAt": row["created_at"],
                "updatedAt": row["updated_at"],
            },
            timestamp=datetime.now().isoformat(),
        )

    except Exception as e:
        logger.error(f"Failed to get active model: {e}")
        return ModelOperationResponse(
            success=False,
            message=f"Failed to get active model: {str(e)}",
            timestamp=datetime.now().isoformat(),
        )


@api_handler(body=SelectModelRequest)
async def select_model(body: SelectModelRequest) -> ModelOperationResponse:
    """Select/activate specified model

    @param body Contains the model ID to activate
    @returns Activation result and new model information
    """
    try:
        db = get_db()

        # Validate model exists
        model = db.models.get_by_id(body.model_id)

        if not model:
            return ModelOperationResponse(
                success=False,
                message=f"Model does not exist: {body.model_id}",
                timestamp=datetime.now().isoformat(),
            )

        # Activate specified model (this also deactivates all others)
        now = datetime.now().isoformat()
        db.models.set_active(body.model_id)

        logger.debug(f"Switched to model: {body.model_id} ({model['name']})")

        return ModelOperationResponse(
            success=True,
            message=f"Switched to model: {model['name']}",
            data={"modelId": body.model_id, "modelName": model["name"]},
            timestamp=now,
        )

    except Exception as e:
        logger.error(f"Failed to select model: {e}")
        return ModelOperationResponse(
            success=False,
            message=f"Failed to select model: {str(e)}",
            timestamp=datetime.now().isoformat(),
        )


@api_handler(body=TestModelRequest)
async def test_model(body: TestModelRequest) -> ModelOperationResponse:
    """Test if the specified model's API connection is available"""

    db = get_db()
    model = db.models.get_by_id(body.model_id)

    if not model:
        return ModelOperationResponse(
            success=False,
            message=f"Model does not exist: {body.model_id}",
            timestamp=datetime.now().isoformat(),
        )

    _provider = (model.get("provider") or "").lower()
    api_url = (model.get("api_url") or "").strip()
    api_key = model.get("api_key") or ""

    if not api_url or not api_key:
        return ModelOperationResponse(
            success=False,
            message="Model configuration missing API URL or key, cannot execute test",
            timestamp=datetime.now().isoformat(),
        )

    base_url = api_url.rstrip("/")
    if base_url.endswith("/chat/completions") or base_url.endswith("/completions"):
        url = base_url
    else:
        url = f"{base_url}/chat/completions"

    # Use OpenAI-compatible format for all models
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    # Build minimal test request (OpenAI-compatible format)
    payload: Dict[str, Any] = {
        "model": model.get("model"),
        "messages": [{"role": "user", "content": "Respond with OK"}],
        "max_tokens": 16,
        "temperature": 0,
    }

    success = False
    status_message = ""
    error_detail = None

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(15.0)) as client:
            response = await client.post(url, headers=headers, json=payload)
        if 200 <= response.status_code < 400:
            success = True
            status_message = "Model API test passed"
        else:
            error_detail = (
                response.text[:500] if response.text else f"HTTP {response.status_code}"
            )
            status_message = f"Model API test failed: HTTP {response.status_code}"
    except Exception as exc:
        error_detail = str(exc)
        status_message = f"Model API test exception: {exc.__class__.__name__}"

    # Update test results in database
    db.models.update_test_result(body.model_id, success, error_detail)

    tested_at = datetime.now().isoformat()
    runtime_message = None

    if bool(model.get("is_active")):
        coordinator = get_coordinator()
        if success:
            try:
                coordinator.last_error = None
                await start_runtime()
                runtime_message = "Attempted to start background process"
            except Exception as exc:
                runtime_message = f"Background startup failed: {exc}"
        else:
            try:
                await stop_runtime(quiet=True)
            except Exception as exc:
                logger.warning(f"Failed to stop background process: {exc}")
            coordinator.last_error = error_detail or status_message
            coordinator._set_state(mode="requires_model", error=coordinator.last_error)

    return ModelOperationResponse(
        success=success,
        message=status_message,
        data={
            "modelId": model.get("id"),
            "provider": model.get("provider"),
            "testedAt": tested_at,
            "error": error_detail,
            "runtimeMessage": runtime_message,
        },
        timestamp=tested_at,
    )


@api_handler()
async def migrate_models_to_openai() -> ModelOperationResponse:
    """Migrate all existing models to use 'openai' provider.

    This is a one-time migration to standardize all models to OpenAI-compatible format.

    @returns Migration result with count of updated models
    """
    try:
        db = get_db()

        # Get all models that don't have provider='openai'
        all_models = db.models.get_all()
        non_openai_models = [m for m in all_models if m.get("provider") != "openai"]

        if not non_openai_models:
            return ModelOperationResponse(
                success=True,
                message="All models already using 'openai' provider",
                data={"updatedCount": 0, "totalCount": len(all_models)},
                timestamp=datetime.now().isoformat(),
            )

        # Update each model to use 'openai' provider
        updated_count = 0
        for model in non_openai_models:
            try:
                db.models.update(
                    model_id=model["id"],
                    provider="openai",
                    name=None,
                    api_url=None,
                    model=None,
                    api_key=None,
                    input_token_price=None,
                    output_token_price=None,
                    currency=None,
                )
                updated_count += 1
                logger.debug(
                    f"Migrated model {model['id']} ({model['name']}) from '{model['provider']}' to 'openai'"
                )
            except Exception as e:
                logger.error(f"Failed to migrate model {model['id']}: {e}")

        return ModelOperationResponse(
            success=True,
            message=f"Migrated {updated_count} models to 'openai' provider",
            data={
                "updatedCount": updated_count,
                "totalCount": len(all_models),
                "skippedCount": len(non_openai_models) - updated_count,
            },
            timestamp=datetime.now().isoformat(),
        )

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return ModelOperationResponse(
            success=False,
            message=f"Migration failed: {str(e)}",
            timestamp=datetime.now().isoformat(),
        )


# ============================================================================
# Dashboard & Statistics
# ============================================================================


@api_handler(
    method="GET",
    path="/dashboard/llm-stats",
    tags=["dashboard"],
    summary="Get LLM usage statistics",
    description="Get LLM token consumption, call count, and cost statistics for the past 30 days",
)
async def get_llm_stats() -> DashboardResponse:
    """Get LLM usage statistics

    @returns LLM token consumption statistics and call count
    """
    try:
        dashboard_manager = get_dashboard_manager()
        stats = dashboard_manager.get_llm_statistics(days=30)

        return DashboardResponse(
            success=True,
            data=stats.model_dump(),
            timestamp=datetime.now().isoformat(),
        )

    except Exception as e:
        logger.error(f"Failed to get LLM statistics: {e}", exc_info=True)
        return DashboardResponse(
            success=False,
            message=f"Failed to get LLM statistics: {str(e)}",
            timestamp=datetime.now().isoformat(),
        )


@api_handler(
    body=GetLLMStatsByModelRequest,
    method="POST",
    path="/dashboard/llm-stats/by-model",
    tags=["dashboard"],
    summary="Get LLM usage statistics by model",
    description="Get LLM token consumption, call count, and cost statistics for the past 30 days by model ID, including model price information",
)
async def get_llm_stats_by_model(
    body: GetLLMStatsByModelRequest,
) -> DashboardResponse:
    """Get LLM usage statistics by model"""
    try:
        dashboard_manager = get_dashboard_manager()
        stats = dashboard_manager.get_llm_statistics_by_model(
            model_id=body.model_id, days=30
        )

        return DashboardResponse(
            success=True,
            data=stats.model_dump(),
            timestamp=datetime.now().isoformat(),
        )

    except Exception as e:
        logger.error(f"Failed to get LLM statistics by model: {e}", exc_info=True)
        return DashboardResponse(
            success=False,
            message=f"Failed to get LLM statistics by model: {str(e)}",
            timestamp=datetime.now().isoformat(),
        )


@api_handler(
    body=RecordLLMUsageRequest,
    method="POST",
    path="/dashboard/record-llm-usage",
    tags=["dashboard"],
    summary="Record LLM usage statistics",
    description="Record token consumption, cost and other information for a single LLM call",
)
async def record_llm_usage(body: RecordLLMUsageRequest) -> DashboardResponse:
    """Record LLM usage statistics

    @param body LLM usage information
    @returns Recording result
    """
    try:
        dashboard_manager = get_dashboard_manager()
        success = dashboard_manager.record_llm_usage(
            model=body.model,
            prompt_tokens=body.prompt_tokens,
            completion_tokens=body.completion_tokens,
            total_tokens=body.total_tokens,
            cost=body.cost,
            request_type=body.request_type,
        )

        if success:
            return DashboardResponse(
                success=True,
                message="LLM usage record saved",
                timestamp=datetime.now().isoformat(),
            )
        return DashboardResponse(
            success=False,
            message="Failed to save LLM usage record",
            timestamp=datetime.now().isoformat(),
        )

    except Exception as e:
        logger.error(f"Failed to save LLM usage record: {e}", exc_info=True)
        return DashboardResponse(
            success=False,
            message=f"Failed to save LLM usage record: {str(e)}",
            timestamp=datetime.now().isoformat(),
        )


@api_handler(
    method="GET",
    path="/dashboard/usage-summary",
    tags=["dashboard"],
    summary="Get usage summary",
    description="Get overall usage summary statistics",
)
async def get_usage_summary() -> DashboardResponse:
    """Get overall usage summary statistics

    @returns Overall summary including activities, tasks, and LLM usage
    """
    try:
        dashboard_manager = get_dashboard_manager()
        summary = dashboard_manager.get_usage_summary()

        # Convert to dictionary format for serialization
        summary_data = {
            "activities": {"total": summary.activities_total},
            "tasks": {
                "total": summary.tasks_total,
                "completed": summary.tasks_completed,
                "pending": summary.tasks_pending,
            },
            "llm": {
                "tokensLast7Days": summary.llm_tokens_last_7_days,
                "callsLast7Days": summary.llm_calls_last_7_days,
                "costLast7Days": summary.llm_cost_last_7_days,
            },
        }

        logger.debug("Usage summary statistics retrieval completed")

        return DashboardResponse(
            success=True,
            data=summary_data,
            timestamp=datetime.now().isoformat(),
        )

    except Exception as e:
        logger.error(f"Failed to get usage summary: {e}", exc_info=True)
        return DashboardResponse(
            success=False,
            message=f"Failed to get usage summary: {str(e)}",
            timestamp=datetime.now().isoformat(),
        )


@api_handler(
    method="GET",
    path="/dashboard/daily-llm-usage",
    tags=["dashboard"],
    summary="Get daily LLM usage",
    description="Get detailed daily LLM usage data for the past 7 days",
)
async def get_daily_llm_usage() -> DashboardResponse:
    """Get daily LLM usage

    @returns Daily LLM usage data list
    """
    try:
        dashboard_manager = get_dashboard_manager()
        daily_usage = dashboard_manager.get_daily_llm_usage(days=7)

        return DashboardResponse(
            success=True,
            data=daily_usage,
            timestamp=datetime.now().isoformat(),
        )

    except Exception as e:
        logger.error(f"Failed to get daily LLM usage: {e}", exc_info=True)
        return DashboardResponse(
            success=False,
            message=f"Failed to get daily LLM usage: {str(e)}",
            timestamp=datetime.now().isoformat(),
        )


@api_handler(
    method="GET",
    path="/dashboard/model-distribution",
    tags=["dashboard"],
    summary="Get model usage distribution",
    description="Get model usage distribution statistics for the past 30 days",
)
async def get_model_distribution() -> DashboardResponse:
    """Get model usage distribution statistics

    @returns Model usage distribution data
    """
    try:
        dashboard_manager = get_dashboard_manager()
        model_distribution = dashboard_manager.get_model_usage_distribution(days=30)

        return DashboardResponse(
            success=True,
            data=model_distribution,
            timestamp=datetime.now().isoformat(),
        )

    except Exception as e:
        logger.error(f"Failed to get model usage distribution: {e}", exc_info=True)
        return DashboardResponse(
            success=False,
            message=f"Failed to get model usage distribution: {str(e)}",
            timestamp=datetime.now().isoformat(),
        )


@api_handler(
    body=GetLLMUsageTrendRequest,
    method="POST",
    path="/dashboard/llm-usage-trend",
    tags=["dashboard"],
    summary="Get LLM usage trend data",
    description="Get LLM usage trend data aggregated by day, week, or month",
)
async def get_llm_usage_trend(
    body: GetLLMUsageTrendRequest,
) -> LLMUsageTrendResponse:
    """Get LLM usage trend data with configurable time dimension

    @param body Request parameters including dimension (day/week/month), days range, and optional model filter
    @returns Trend data points with date, tokens, calls, and cost
    """
    try:
        dashboard_manager = get_dashboard_manager()
        trend_data = dashboard_manager.get_llm_usage_trend(
            dimension=body.dimension,
            days=body.days,
            model_config_id=body.model_config_id,
            start_date=body.start_date,
            end_date=body.end_date,
        )

        return LLMUsageTrendResponse(
            success=True,
            data=trend_data,
            dimension=body.dimension,
            days=body.days,
            timestamp=datetime.now().isoformat(),
        )

    except Exception as e:
        logger.error(f"Failed to get LLM usage trend: {e}", exc_info=True)
        return LLMUsageTrendResponse(
            success=False,
            message=f"Failed to get LLM usage trend: {str(e)}",
            timestamp=datetime.now().isoformat(),
        )
