"""
Base model configuration for PyTauri
PyTauri 的基础模型配置
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel as PydanticBaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class BaseModel(PydanticBaseModel):
    """Base model with camelCase conversion for JavaScript compatibility.

    This base model configuration:
    - Accepts camelCase js ipc arguments for snake_case python fields
    - Forbids unknown fields to ensure type safety
    """

    model_config = ConfigDict(
        # Accepts camelCase js ipc arguments for snake_case python fields.
        #
        # See: <https://docs.pydantic.dev/2.10/concepts/alias/#using-an-aliasgenerator>
        alias_generator=to_camel,
        # By default, pydantic allows unknown fields,
        # which results in TypeScript types having `[key: string]: unknown`.
        #
        # See: <https://docs.pydantic.dev/2.10/concepts/models/#extra-data>
        extra="forbid",
    )


class LLMTokenUsage(BaseModel):
    """LLM Token Usage Statistics Model"""
    id: int | None = None
    timestamp: str  # ISO datetime string
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost: float | None = None
    request_type: str  # 'summarization', 'agent', 'chat', etc.


class LLMUsageStats(BaseModel):
    """LLM Usage Statistics Internal Model"""
    total_tokens: int
    total_calls: int
    total_cost: float
    models_used: list[str]
    period: str
    daily_usage: list[dict]


class LLMUsageResponse(BaseModel):
    """LLM Usage Statistics Response Model for frontend (camelCase)"""
    totalTokens: int
    totalCalls: int
    totalCost: float
    modelsUsed: list[str]
    period: str
    dailyUsage: list[dict]
    modelDetails: Optional[Dict[str, Any]] = None
