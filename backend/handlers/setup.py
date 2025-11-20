"""
Initial Setup Handler
Provides API endpoints for checking and managing initial setup requirements
"""

from datetime import datetime
from typing import Any, Dict

from core.db import get_db
from core.logger import get_logger

from . import api_handler

logger = get_logger(__name__)


@api_handler()
async def check_initial_setup() -> Dict[str, Any]:
    """Check if initial setup is required

    Returns status indicating whether the application needs initial configuration:
    - has_models: Whether any LLM models are configured
    - has_active_model: Whether an active model is selected
    - needs_setup: Whether initial setup flow should be shown

    @returns Setup status with detailed configuration state
    """
    try:
        db = get_db()

        # Check if any models are configured
        models = db.models.get_all()
        has_models = len(models) > 0

        # Check if there's an active model
        active_model = db.models.get_active()
        has_active_model = active_model is not None

        # Determine if setup is needed
        # Setup is required if there are no models configured
        needs_setup = not has_models

        logger.debug(
            f"Initial setup check: has_models={has_models}, "
            f"has_active_model={has_active_model}, needs_setup={needs_setup}"
        )

        return {
            "success": True,
            "data": {
                "has_models": has_models,
                "has_active_model": has_active_model,
                "needs_setup": needs_setup,
                "model_count": len(models),
            },
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to check initial setup: {e}")
        return {
            "success": False,
            "message": f"Failed to check initial setup: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        }
