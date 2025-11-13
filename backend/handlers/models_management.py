"""
Model management handlers (complete version)
Support passing all parameters through request body to avoid URL parameter issues
"""

import uuid
from datetime import datetime
from typing import Any, Dict

import httpx
from core.coordinator import get_coordinator
from core.db import get_db
from core.logger import get_logger
from models.requests import (
    CreateModelRequest,
    DeleteModelRequest,
    SelectModelRequest,
    TestModelRequest,
    UpdateModelRequest,
)
from system.runtime import start_runtime, stop_runtime

from . import api_handler

logger = get_logger(__name__)


@api_handler(body=CreateModelRequest)
async def create_model(body: CreateModelRequest) -> Dict[str, Any]:
    """Create new model configuration

    @param body Model configuration information (includes API key)
    @returns Created model information
    """
    try:
        db = get_db()

        # Generate unique ID
        model_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        # Use repository to insert model
        db.models.insert(
            model_id=model_id,
            name=body.name,
            provider=body.provider,
            api_url=body.api_url,
            model=body.model,
            api_key=body.api_key,
            input_token_price=body.input_token_price,
            output_token_price=body.output_token_price,
            currency=body.currency,
            is_active=False,
        )

        logger.info(f"Model created: {model_id} ({body.name})")

        return {
            "success": True,
            "message": "Model created successfully",
            "data": {
                "id": model_id,
                "name": body.name,
                "provider": body.provider,
                "model": body.model,
                "currency": body.currency,
                "createdAt": now,
                "isActive": False,
            },
            "timestamp": now,
        }

    except Exception as e:
        logger.error(f"Failed to create model: {e}")
        return {
            "success": False,
            "message": f"Failed to create model: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        }


@api_handler(body=UpdateModelRequest)
async def update_model(body: UpdateModelRequest) -> Dict[str, Any]:
    """Update model configuration

    @param body Model information to update (only update provided fields)
    @returns Updated model information
    """
    try:
        db = get_db()

        # Verify model exists
        existing_model = db.models.get_by_id(body.model_id)

        if not existing_model:
            return {
                "success": False,
                "message": f"Model does not exist: {body.model_id}",
                "timestamp": datetime.now().isoformat(),
            }

        now = datetime.now().isoformat()

        # Update model using repository
        db.models.update(
            model_id=body.model_id,
            name=body.name,
            provider=body.provider,
            api_url=body.api_url,
            model=body.model,
            api_key=body.api_key,
            input_token_price=body.input_token_price,
            output_token_price=body.output_token_price,
            currency=body.currency,
        )

        logger.info(
            f"Model updated: {body.model_id} ({body.name or existing_model['name']})"
        )

        # Get updated model information
        row = db.models.get_by_id(body.model_id)

        if row:
            return {
                "success": True,
                "message": "Model updated successfully",
                "data": {
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
                "timestamp": now,
            }

        return {
            "success": True,
            "message": "Model updated successfully",
            "timestamp": now,
        }

    except Exception as e:
        logger.error(f"Failed to update model: {e}")
        return {
            "success": False,
            "message": f"Failed to update model: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        }


@api_handler(body=DeleteModelRequest)
async def delete_model(body: DeleteModelRequest) -> Dict[str, Any]:
    """Delete model configuration

    @param body Model ID to delete
    @returns Deletion result
    """
    try:
        db = get_db()

        # Verify model exists
        model = db.models.get_by_id(body.model_id)

        if not model:
            return {
                "success": False,
                "message": f"Model does not exist: {body.model_id}",
                "timestamp": datetime.now().isoformat(),
            }

        was_active = bool(model["is_active"])

        # Delete model (if active model is deleted, there will be no active model after deletion)
        db.models.delete(body.model_id)

        if was_active:
            logger.info(
                f"Active model deleted and activation status cleared: {body.model_id} ({model['name']})"
            )
        else:
            logger.info(f"Model deleted: {body.model_id} ({model['name']})")

        return {
            "success": True,
            "message": f"Model deleted: {model['name']}",
            "data": {"modelId": body.model_id, "modelName": model["name"]},
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to delete model: {e}")
        return {
            "success": False,
            "message": f"Failed to delete model: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        }


@api_handler()
async def list_models() -> Dict[str, Any]:
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

        return {
            "success": True,
            "data": {"models": models, "count": len(models)},
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to get model list: {e}")
        return {
            "success": False,
            "message": f"Failed to get model list: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        }


@api_handler()
async def get_active_model() -> Dict[str, Any]:
    """Get currently active model information

    @returns Active model detailed information (without API key)
    """
    try:
        db = get_db()

        row = db.models.get_active()

        if not row:
            return {
                "success": False,
                "message": "No active model",
                "timestamp": datetime.now().isoformat(),
            }

        return {
            "success": True,
            "data": {
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
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to get active model: {e}")
        return {
            "success": False,
            "message": f"Failed to get active model: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        }


@api_handler(body=SelectModelRequest)
async def select_model(body: SelectModelRequest) -> Dict[str, Any]:
    """Select/activate specified model

    @param body Contains the model ID to activate
    @returns Activation result and new model information
    """
    try:
        db = get_db()

        # Validate model exists
        model = db.models.get_by_id(body.model_id)

        if not model:
            return {
                "success": False,
                "message": f"Model does not exist: {body.model_id}",
                "timestamp": datetime.now().isoformat(),
            }

        # Activate specified model (this also deactivates all others)
        now = datetime.now().isoformat()
        db.models.set_active(body.model_id)

        logger.info(f"Switched to model: {body.model_id} ({model['name']})")

        return {
            "success": True,
            "message": f"Switched to model: {model['name']}",
            "data": {"modelId": body.model_id, "modelName": model["name"]},
            "timestamp": now,
        }

    except Exception as e:
        logger.error(f"Failed to select model: {e}")
        return {
            "success": False,
            "message": f"Failed to select model: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        }


# Common handling for updates and deletions (through special request formats)
class _ModelUpdateBody:
    """Internal update request model"""

    pass


class _ModelDeleteBody:
    """Internal delete request model"""

    pass


@api_handler(body=TestModelRequest)
async def test_model(body: TestModelRequest) -> Dict[str, Any]:
    """Test if the specified model's API connection is available"""

    db = get_db()
    model = db.models.get_by_id(body.model_id)

    if not model:
        return {
            "success": False,
            "message": f"Model does not exist: {body.model_id}",
            "timestamp": datetime.now().isoformat(),
        }

    provider = (model.get("provider") or "").lower()
    api_url = (model.get("api_url") or "").strip()
    api_key = model.get("api_key") or ""

    if not api_url or not api_key:
        return {
            "success": False,
            "message": "Model configuration missing API URL or key, cannot execute test",
            "timestamp": datetime.now().isoformat(),
        }

    base_url = api_url.rstrip("/")
    if base_url.endswith("/chat/completions") or base_url.endswith("/completions"):
        url = base_url
    else:
        url = f"{base_url}/chat/completions"

    headers = {"Content-Type": "application/json"}
    if provider == "anthropic":
        headers["x-api-key"] = api_key
        headers.setdefault("anthropic-version", "2023-06-01")
    else:
        headers["Authorization"] = f"Bearer {api_key}"

    # Build minimal test request
    if provider == "anthropic":
        payload: Dict[str, Any] = {
            "model": model.get("model"),
            "max_tokens": 32,
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": "Respond with OK"}],
                }
            ],
        }
    else:
        payload = {
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

    return {
        "success": success,
        "message": status_message,
        "data": {
            "modelId": model.get("id"),
            "provider": model.get("provider"),
            "testedAt": tested_at,
            "error": error_detail,
            "runtimeMessage": runtime_message,
        },
        "timestamp": tested_at,
    }
