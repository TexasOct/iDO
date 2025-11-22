"""
LLM Manager - Centralized LLM request management
Ensures all services use the latest activated model configuration
"""

from typing import Any, AsyncGenerator, Dict, List, Optional

from core.logger import get_logger

from .client import LLMClient

logger = get_logger(__name__)


class LLMManager:
    """
    Centralized LLM request manager

    Provides a singleton interface that always uses the latest activated model.
    All LLM requests should go through this manager instead of creating
    LLMClient instances directly.
    """

    _instance: Optional["LLMManager"] = None
    _client: Optional[LLMClient] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # Only initialize once
        if not hasattr(self, "_initialized"):
            self._initialized = True
            self._client = None
            logger.info("LLMManager initialized")

    def _ensure_client(self, reload: bool = False) -> LLMClient:
        """
        Ensure we have a valid LLM client with the latest configuration

        Args:
            reload: If True, force reload configuration. Default False to avoid
                   interrupting concurrent streaming requests.

        Returns:
            LLMClient instance with latest activated model config
        """
        if self._client is None:
            self._client = LLMClient()
            logger.debug("Created new LLMClient instance")
        elif reload:
            # Only reload if explicitly requested (e.g., after model change)
            self._client.reload_config()
            logger.debug("Reloaded LLMClient configuration")

        return self._client

    async def chat_completion(
        self, messages: List[Dict[str, Any]], **kwargs
    ) -> Dict[str, Any]:
        """
        Send chat completion request using latest activated model

        Args:
            messages: Conversation message list
            **kwargs: Additional parameters (max_tokens, temperature, etc.)

        Returns:
            LLM response
        """
        client = self._ensure_client()
        return await client.chat_completion(messages, **kwargs)

    async def chat_completion_stream(
        self, messages: List[Dict[str, Any]], **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        Send streaming chat completion request using latest activated model or specified model

        Args:
            messages: Conversation message list
            **kwargs: Additional parameters (model_id, max_tokens, temperature, etc.)
                     If model_id is provided, use that specific model instead of activated model

        Yields:
            Streaming response chunks
        """
        client = self._ensure_client()
        async for chunk in client.chat_completion_stream(messages, **kwargs):
            yield chunk

    def get_active_model_info(self) -> Dict[str, Any]:
        """
        Get information about currently activated model

        Returns:
            Model configuration dict
        """
        client = self._ensure_client()
        return {
            "provider": client.provider,
            "model": client.model,
            "base_url": client.base_url,
        }

    def force_reload(self):
        """
        Force reload configuration from database
        Useful after model changes to ensure immediate effect
        """
        if self._client:
            self._client.reload_config()
            logger.info("Forced reload of LLM configuration")
        else:
            logger.debug("No client to reload, will create on next request")

    def reload_on_next_request(self):
        """
        Mark client for reload on next request
        This allows safe reload without interrupting active streaming requests
        """
        # Simply clear the client, it will be recreated with new config on next use
        self._client = None
        logger.info("Marked LLM client for reload on next request")


# Global singleton instance
_llm_manager: Optional[LLMManager] = None


def get_llm_manager() -> LLMManager:
    """
    Get the global LLM manager instance

    Returns:
        LLMManager singleton
    """
    global _llm_manager
    if _llm_manager is None:
        _llm_manager = LLMManager()
    return _llm_manager


def reset_llm_manager():
    """
    Reset the LLM manager (mainly for testing)
    Forces creation of new client on next request
    """
    global _llm_manager
    if _llm_manager:
        _llm_manager._client = None
        logger.info("LLM manager reset")
