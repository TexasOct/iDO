"""
Base model configuration for PyTauri
Base model configuration for PyTauri
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict
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
        # Allow populating by both field name and alias
        # This allows using snake_case in Python code while accepting camelCase from JS
        populate_by_name=True,
        # By default, pydantic allows unknown fields,
        # which results in TypeScript types having `[key: string]: unknown`.
        #
        # See: <https://docs.pydantic.dev/2.10/concepts/models/#extra-data>
        extra="forbid",
    )

    def model_dump(self, **kwargs):
        """Override model_dump to always use aliases (camelCase) by default."""
        # Set by_alias=True by default for JavaScript compatibility
        kwargs.setdefault("by_alias", True)
        return super().model_dump(**kwargs)

    def model_dump_json(self, **kwargs):
        """Override model_dump_json to always use aliases (camelCase) by default."""
        # Set by_alias=True by default for JavaScript compatibility
        kwargs.setdefault("by_alias", True)
        return super().model_dump_json(**kwargs)


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


class OperationResponse(BaseModel):
    """Common base response for handlers that return operation status."""

    success: bool
    message: str = ""
    error: str = ""


class OperationDataResponse(OperationResponse):
    """Operation response that includes an optional data payload."""

    data: Any | None = None


class TimedOperationResponse(OperationDataResponse):
    """Operation response with timestamp."""

    timestamp: str = ""
