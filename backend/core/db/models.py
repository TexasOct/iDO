"""
LLM Models Repository - Handles LLM model configuration and management
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.logger import get_logger

from .base import BaseRepository

logger = get_logger(__name__)


class LLMModelsRepository(BaseRepository):
    """Repository for managing LLM model configurations"""

    def __init__(self, db_path: Path):
        super().__init__(db_path)

    def get_active(self) -> Optional[Dict[str, Any]]:
        """Get currently active LLM model configuration"""
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    SELECT id, name, provider, api_url, model, api_key,
                           input_token_price, output_token_price, currency,
                           is_active, last_test_status, last_tested_at, last_test_error,
                           created_at, updated_at
                    FROM llm_models
                    WHERE is_active = 1
                    LIMIT 1
                    """
                )
                row = cursor.fetchone()

            if row:
                return dict(row)
            return None

        except Exception as e:
            logger.error(f"Failed to get active LLM model: {e}", exc_info=True)
            return None

    def get_by_id(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Get model configuration by ID (includes API key and test status)"""
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    SELECT id, name, provider, api_url, model, api_key,
                           input_token_price, output_token_price, currency,
                           is_active, last_test_status, last_tested_at, last_test_error,
                           created_at, updated_at
                    FROM llm_models
                    WHERE id = ?
                    """,
                    (model_id,),
                )
                row = cursor.fetchone()

            if row:
                return dict(row)
            return None

        except Exception as e:
            logger.error(f"Failed to get LLM model {model_id}: {e}", exc_info=True)
            return None

    def update_test_result(
        self, model_id: str, success: bool, error: Optional[str] = None
    ) -> None:
        """Update model test result"""
        try:
            now = datetime.now().isoformat()
            with self._get_conn() as conn:
                conn.execute(
                    """
                    UPDATE llm_models
                    SET last_test_status = ?,
                        last_tested_at = ?,
                        last_test_error = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (1 if success else 0, now, error, now, model_id),
                )
                conn.commit()
                logger.debug(f"Updated test result for model {model_id}: {'success' if success else 'failed'}")

        except Exception as e:
            logger.error(f"Failed to update test result for model {model_id}: {e}", exc_info=True)
            raise

    def get_all(self) -> List[Dict[str, Any]]:
        """Get all LLM models"""
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    SELECT id, name, provider, api_url, model, api_key,
                           input_token_price, output_token_price, currency,
                           is_active, last_test_status, last_tested_at, last_test_error,
                           created_at, updated_at
                    FROM llm_models
                    ORDER BY created_at DESC
                    """
                )
                rows = cursor.fetchall()

            return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get all LLM models: {e}", exc_info=True)
            return []

    def set_active(self, model_id: str) -> None:
        """Set a model as active (deactivates all others)"""
        try:
            now = datetime.now().isoformat()
            with self._get_conn() as conn:
                # Deactivate all models
                conn.execute("UPDATE llm_models SET is_active = 0")

                # Activate the specified model
                conn.execute(
                    "UPDATE llm_models SET is_active = 1, updated_at = ? WHERE id = ?",
                    (now, model_id),
                )
                conn.commit()
                logger.info(f"Set model {model_id} as active")

        except Exception as e:
            logger.error(f"Failed to set model {model_id} as active: {e}", exc_info=True)
            raise

    def insert(
        self,
        model_id: str,
        name: str,
        provider: str,  # Should always be 'openai' for OpenAI-compatible APIs
        api_url: str,
        model: str,
        api_key: str,
        input_token_price: float = 0.0,
        output_token_price: float = 0.0,
        currency: str = "USD",
        is_active: bool = False,
    ) -> int:
        """Insert a new LLM model"""
        try:
            now = datetime.now().isoformat()
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO llm_models (
                        id, name, provider, api_url, model, api_key,
                        input_token_price, output_token_price, currency,
                        is_active, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        model_id, name, provider, api_url, model, api_key,
                        input_token_price, output_token_price, currency,
                        1 if is_active else 0, now, now
                    ),
                )
                conn.commit()
                logger.debug(f"Inserted LLM model: {model_id}")
                return cursor.lastrowid or 0
        except Exception as e:
            logger.error(f"Failed to insert LLM model {model_id}: {e}", exc_info=True)
            raise

    def update(
        self,
        model_id: str,
        name: Optional[str] = None,
        provider: Optional[str] = None,
        api_url: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        input_token_price: Optional[float] = None,
        output_token_price: Optional[float] = None,
        currency: Optional[str] = None,
    ) -> int:
        """Update an LLM model"""
        try:
            updates = []
            params = []

            if name is not None:
                updates.append("name = ?")
                params.append(name)
            if provider is not None:
                updates.append("provider = ?")
                params.append(provider)
            if api_url is not None:
                updates.append("api_url = ?")
                params.append(api_url)
            if model is not None:
                updates.append("model = ?")
                params.append(model)
            if api_key is not None:
                updates.append("api_key = ?")
                params.append(api_key)
            if input_token_price is not None:
                updates.append("input_token_price = ?")
                params.append(input_token_price)
            if output_token_price is not None:
                updates.append("output_token_price = ?")
                params.append(output_token_price)
            if currency is not None:
                updates.append("currency = ?")
                params.append(currency)

            if not updates:
                return 0

            now = datetime.now().isoformat()
            updates.append("updated_at = ?")
            params.append(now)
            params.append(model_id)

            query = f"""
                UPDATE llm_models
                SET {", ".join(updates)}
                WHERE id = ?
            """

            with self._get_conn() as conn:
                cursor = conn.execute(query, tuple(params))
                conn.commit()
                logger.debug(f"Updated LLM model: {model_id}")
                return cursor.rowcount

        except Exception as e:
            logger.error(f"Failed to update LLM model {model_id}: {e}", exc_info=True)
            raise

    def delete(self, model_id: str) -> int:
        """Delete an LLM model"""
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    "DELETE FROM llm_models WHERE id = ?",
                    (model_id,),
                )
                conn.commit()
                logger.debug(f"Deleted LLM model: {model_id}")
                return cursor.rowcount
        except Exception as e:
            logger.error(f"Failed to delete LLM model {model_id}: {e}", exc_info=True)
            raise

    def exists(self, model_id: str) -> bool:
        """Check if a model exists"""
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    "SELECT 1 FROM llm_models WHERE id = ? LIMIT 1",
                    (model_id,),
                )
                return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Failed to check if model {model_id} exists: {e}", exc_info=True)
            return False
