"""
Model Management Handler
Provides API endpoints for multi-model configuration, selection, and management

Features:
- Create, list, update, delete model configurations
- Select and switch active models
- Get active model information
- Validate model connections (optional)
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

from core.db import get_db
from core.logger import get_logger
from core.settings import get_settings
from . import api_handler
from models.requests import (
    CreateModelRequest,
    UpdateModelRequest,
    SelectModelRequest,
    ModelConfig,
)

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

        # Insert into database
        db.execute(
            """
            INSERT INTO llm_models (
                id, name, provider, api_url, model,
                input_token_price, output_token_price, currency,
                api_key, is_active, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                model_id,
                body.name,
                body.provider,
                body.api_url,
                body.model,
                body.input_token_price,
                body.output_token_price,
                body.currency,
                body.api_key,
                False,  # Newly created models are not active by default
                now,
                now,
            ),
        )
        db.commit()

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


@api_handler()
async def list_models() -> Dict[str, Any]:
    """Get all model configuration list

    @returns Model list (without API keys)
    """
    try:
        db = get_db()

        # Query all models (without returning api_key)
        cursor = db.execute("""
            SELECT id, name, provider, api_url, model,
                   input_token_price, output_token_price, currency,
                   is_active, created_at, updated_at
            FROM llm_models
            ORDER BY created_at DESC
        """)

        rows = cursor.fetchall()
        models = []

        for row in rows:
            models.append(
                {
                    "id": row[0],
                    "name": row[1],
                    "provider": row[2],
                    "apiUrl": row[3],
                    "model": row[4],
                    "inputTokenPrice": row[5],
                    "outputTokenPrice": row[6],
                    "currency": row[7],
                    "isActive": bool(row[8]),
                    "createdAt": row[9],
                    "updatedAt": row[10],
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

        cursor = db.execute("""
            SELECT id, name, provider, api_url, model,
                   input_token_price, output_token_price, currency,
                   created_at, updated_at
            FROM llm_models
            WHERE is_active = 1
            LIMIT 1
        """)

        row = cursor.fetchone()

        if not row:
            return {
                "success": False,
                "message": "No active model",
                "timestamp": datetime.now().isoformat(),
            }

        return {
            "success": True,
            "data": {
                "id": row[0],
                "name": row[1],
                "provider": row[2],
                "apiUrl": row[3],
                "model": row[4],
                "inputTokenPrice": row[5],
                "outputTokenPrice": row[6],
                "currency": row[7],
                "createdAt": row[8],
                "updatedAt": row[9],
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
        cursor = db.execute(
            "SELECT id, name FROM llm_models WHERE id = ?", (body.model_id,)
        )

        model = cursor.fetchone()
        if not model:
            return {
                "success": False,
                "message": f"Model does not exist: {body.model_id}",
                "timestamp": datetime.now().isoformat(),
            }

        # Transaction: disable all other models, activate specified model
        now = datetime.now().isoformat()
        db.execute("UPDATE llm_models SET is_active = 0 WHERE is_active = 1")
        db.execute(
            "UPDATE llm_models SET is_active = 1, updated_at = ? WHERE id = ?",
            (now, body.model_id),
        )
        db.commit()

        logger.info(f"Switched to model: {model[1]}")

        return {
            "success": True,
            "message": f"Switched to model: {model[1]}",
            "data": {"modelId": body.model_id, "modelName": model[1]},
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
    body: UpdateModelRequest, model_id: str = None
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
        cursor = db.execute("SELECT id FROM llm_models WHERE id = ?", (model_id,))

        if not cursor.fetchone():
            return {
                "success": False,
                "message": f"Model does not exist: {model_id}",
                "timestamp": datetime.now().isoformat(),
            }

        # Build update statement
        updates = []
        params = []

        if body.name is not None:
            updates.append("name = ?")
            params.append(body.name)

        if body.input_token_price is not None:
            updates.append("input_token_price = ?")
            params.append(body.input_token_price)

        if body.output_token_price is not None:
            updates.append("output_token_price = ?")
            params.append(body.output_token_price)

        if body.currency is not None:
            updates.append("currency = ?")
            params.append(body.currency)

        if body.api_key is not None:
            updates.append("api_key = ?")
            params.append(body.api_key)

        if not updates:
            return {
                "success": False,
                "message": "No fields to update",
                "timestamp": datetime.now().isoformat(),
            }

        # Add updated_at and model_id
        now = datetime.now().isoformat()
        updates.append("updated_at = ?")
        params.append(now)
        params.append(model_id)

        # Execute update
        query = f"UPDATE llm_models SET {', '.join(updates)} WHERE id = ?"
        db.execute(query, params)
        db.commit()

        logger.info(f"Model updated: {model_id}")

        # Get updated data
        cursor = db.execute(
            """
            SELECT id, name, provider, api_url, model,
                   input_token_price, output_token_price, currency,
                   is_active, created_at, updated_at
            FROM llm_models
            WHERE id = ?
        """,
            (model_id,),
        )

        row = cursor.fetchone()

        return {
            "success": True,
            "message": "Model updated successfully",
            "data": {
                "id": row[0],
                "name": row[1],
                "provider": row[2],
                "apiUrl": row[3],
                "model": row[4],
                "inputTokenPrice": row[5],
                "outputTokenPrice": row[6],
                "currency": row[7],
                "isActive": bool(row[8]),
                "createdAt": row[9],
                "updatedAt": row[10],
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
        cursor = db.execute(
            "SELECT is_active FROM llm_models WHERE id = ?", (model_id,)
        )

        row = cursor.fetchone()
        if not row:
            return {
                "success": False,
                "message": f"Model does not exist: {model_id}",
                "timestamp": datetime.now().isoformat(),
            }

        was_active = bool(row[0])

        # Delete model (deleting active model will leave no active model)
        db.execute("DELETE FROM llm_models WHERE id = ?", (model_id,))
        db.commit()

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
