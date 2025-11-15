"""
Model Management Handler
Provides API endpoints for multi-model configuration, selection, and management

Features:
- Create, list, update, delete model configurations
- Select and switch active models
- Get active model information
- Validate model connections (optional)
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.db import get_db
from core.logger import get_logger
from core.settings import get_settings
from models.requests import (
    CreateModelRequest,
    ModelConfig,
    SelectModelRequest,
    UpdateModelRequest,
)

from . import api_handler

logger = get_logger(__name__)


@api_handler(body=CreateModelRequest)
async def create_model(body: CreateModelRequest) -> Dict[str, Any]:
    """Create new model configuration

    @param body Model configuration information (including API key)
    @returns Created model information
    """
    try:
        db = get_db()

        # Generate unique ID
        model_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        # Insert into database using repository (provider always set to 'openai' for OpenAI-compatible APIs)
        db.models.insert(
            model_id=model_id,
            name=body.name,
            provider="openai",  # Always use 'openai' for OpenAI-compatible APIs
            api_url=body.api_url,
            model=body.model,
            input_token_price=body.input_token_price,
            output_token_price=body.output_token_price,
            currency=body.currency,
            api_key=body.api_key,
            is_active=False,  # Newly created models are not active by default
        )

        logger.info(f"Model created: {model_id} ({body.name})")

        return {
            "success": True,
            "message": "Model created successfully",
            "data": {
                "id": model_id,
                "name": body.name,
                "provider": "openai",  # Always 'openai' for OpenAI-compatible APIs
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


@api_handler()
async def list_models() -> Dict[str, Any]:
    """Get all model configuration list

    @returns Model list (without API keys)
    """
    try:
        db = get_db()

        # Query all models using repository
        rows = db.models.get_all()
        models = []

        for row in rows:
            models.append(
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
                    "createdAt": row["created_at"],
                    "updatedAt": row["updated_at"],
                }
            )

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

        # Verify model exists
        model = db.models.get_by_id(body.model_id)

        if not model:
            return {
                "success": False,
                "message": f"Model does not exist: {body.model_id}",
                "timestamp": datetime.now().isoformat(),
            }

        # Set model as active (deactivates all others)
        db.models.set_active(body.model_id)
        now = datetime.now().isoformat()

        logger.info(f"Switched to model: {model['name']}")

        return {
            "success": True,
            "message": f"Switched to model: {model['name']}",
            "data": {"modelId": body.model_id, "modelName": model['name']},
            "timestamp": now,
        }

    except Exception as e:
        logger.error(f"Failed to select model: {e}")
        return {
            "success": False,
            "message": f"Failed to select model: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        }


@api_handler(body=UpdateModelRequest)
async def update_model(
    body: UpdateModelRequest, model_id: Optional[str] = None
) -> Dict[str, Any]:
    """Update model configuration

    Note: This handler accepts model_id from URL parameters
    Actual calls need to be handled through custom endpoints

    @param body Fields to update
    @param model_id Model ID
    @returns Update result
    """
    # Due to PyTauri limitations, this method needs special handling
    # See update_model_with_id below
    return {
        "success": False,
        "message": "Please use update_model_with_id endpoint",
        "timestamp": datetime.now().isoformat(),
    }


async def _update_model_helper(
    model_id: str, body: UpdateModelRequest
) -> Dict[str, Any]:
    """Helper method for updating model configuration"""
    try:
        db = get_db()

        # Verify model exists
        model = db.models.get_by_id(model_id)

        if not model:
            return {
                "success": False,
                "message": f"Model does not exist: {model_id}",
                "timestamp": datetime.now().isoformat(),
            }

        # Check if any fields to update
        has_updates = any([
            body.name is not None,
            body.input_token_price is not None,
            body.output_token_price is not None,
            body.currency is not None,
            body.api_key is not None,
        ])

        if not has_updates:
            return {
                "success": False,
                "message": "No fields to update",
                "timestamp": datetime.now().isoformat(),
            }

        # Update using repository
        db.models.update(
            model_id=model_id,
            name=body.name,
            input_token_price=body.input_token_price,
            output_token_price=body.output_token_price,
            currency=body.currency,
            api_key=body.api_key,
        )

        logger.info(f"Model updated: {model_id}")

        # Get updated data
        row = db.models.get_by_id(model_id)

        if not row:
            row = {}

        now = datetime.now().isoformat()
        return {
            "success": True,
            "message": "Model updated successfully",
            "data": {
                "id": row.get("id"),
                "name": row.get("name"),
                "provider": row.get("provider"),
                "apiUrl": row.get("api_url"),
                "model": row.get("model"),
                "inputTokenPrice": row.get("input_token_price"),
                "outputTokenPrice": row.get("output_token_price"),
                "currency": row.get("currency"),
                "isActive": bool(row.get("is_active")),
                "createdAt": row.get("created_at"),
                "updatedAt": row.get("updated_at"),
            },
            "timestamp": now,
        }

    except Exception as e:
        logger.error(f"Failed to update model: {e}")
        return {
            "success": False,
            "message": f"Failed to update model: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        }


async def _delete_model_helper(model_id: str) -> Dict[str, Any]:
    """Helper method for deleting model configuration"""
    try:
        db = get_db()

        # Validate model exists
        model = db.models.get_by_id(model_id)

        if not model:
            return {
                "success": False,
                "message": f"Model does not exist: {model_id}",
                "timestamp": datetime.now().isoformat(),
            }

        was_active = bool(model["is_active"])

        # Delete model using repository (deleting active model will leave no active model)
        db.models.delete(model_id)

        if was_active:
            logger.info(
                f"Active model deleted and activation status cleared: {model_id}"
            )
        else:
            logger.info(f"Model deleted: {model_id}")

        return {
            "success": True,
            "message": "Model deleted successfully",
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to delete model: {e}")
        return {
            "success": False,
            "message": f"Failed to delete model: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        }


# Note: PyTauri's api_handler decorator does not support URL parameters
# To support updating and deleting specific models, we use the following approach:
# 1. Manually register these handlers in handlers/__init__.py
# 2. Or use specific request formats when calling from frontend


@api_handler(body=UpdateModelRequest)
async def update_model_by_id(body: UpdateModelRequest) -> Dict[str, Any]:
    """Update model configuration (through model_id in request body)

    @param body Contains model_id and fields to update
    @returns Update result
    """
    # This is a workspace, actual implementation needs modification
    return {
        "success": False,
        "message": "Model_id needs to be passed from frontend",
        "timestamp": datetime.now().isoformat(),
    }


@api_handler()
async def delete_model(model_id: str) -> Dict[str, Any]:
    """Delete model configuration

    @param model_id Model ID to delete
    @returns Deletion result
    """
    try:
        return await _delete_model_helper(model_id)
    except Exception as e:
        logger.error(f"Model deletion exception: {e}")
        return {
            "success": False,
            "message": str(e),
            "timestamp": datetime.now().isoformat(),
        }
