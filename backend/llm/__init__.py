"""
LLM module

Provides centralized LLM request management through LLMManager.
All services should use get_llm_manager() instead of creating LLMClient instances directly.
"""

from .client import LLMClient, get_llm_client  # Keep for backward compatibility
from .manager import LLMManager, get_llm_manager, reset_llm_manager

__all__ = [
    "LLMManager",
    "get_llm_manager",
    "reset_llm_manager",
    "LLMClient",
    "get_llm_client",
]
