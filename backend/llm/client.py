"""
Universal LLM client
Only uses activated model configuration from database
"""

from typing import Dict, Any, Optional, List, AsyncGenerator
import httpx
import json
import asyncio
from core.logger import get_logger
from .prompt_manager import get_prompt_manager
from core.dashboard.manager import get_dashboard_manager
from core.db import get_db

logger = get_logger(__name__)


class LLMClient:
    """LLM client base class"""

    def __init__(self, provider: Optional[str] = None):
        self.prompt_manager = get_prompt_manager()
        self.active_model_config: Optional[Dict[str, Any]] = None

        # Only allow using activated model configuration from database
        self.active_model_config = self._fetch_active_model_config()
        if not self.active_model_config:
            raise RuntimeError(
                "No activated LLM model configuration found, please add and activate model in settings."
            )

        active_provider = self.active_model_config.get("provider")
        if provider and provider != active_provider:
            logger.warning(
                f"Specified provider {provider} does not match activated model {active_provider}, will use activated model configuration"
            )

        self.provider = active_provider
        self.api_key = None
        self.model = None
        self.base_url = None
        self.endpoint = "/chat/completions"
        self.extra_headers: Dict[str, str] = {}
        self.timeout: httpx.Timeout = httpx.Timeout(30.0)
        self.max_retries = 2
        self.retry_backoff = 1.5
        self.non_retry_status = {400, 401, 403, 404, 422}
        self.verify_ssl = True
        self.use_http2 = False
        self._setup_client()

    def _fetch_active_model_config(self) -> Optional[Dict[str, Any]]:
        """Read currently activated model configuration from database"""
        try:
            db = get_db()
            result = db.get_active_llm_model()
            if result:
                self.active_model_config = result
                return result
        except Exception as exc:
            logger.debug(f"Failed to read activated model configuration: {exc}")
        return None

    def _setup_client(self):
        """Set up client using activated model configuration"""
        config = self.active_model_config or self._fetch_active_model_config()

        if not config:
            raise RuntimeError(
                "No activated LLM model configuration found, please complete model configuration in settings first."
            )

        self.api_key = config.get("api_key")
        self.model = config.get("model")
        self.base_url = config.get("api_url") or config.get("base_url")
        self.endpoint = config.get("endpoint", "/chat/completions")
        self.extra_headers = config.get("headers", {}) or {}

        if not all([self.api_key, self.model, self.base_url]):
            raise ValueError(
                "Activated LLM model configuration is incomplete, please check API Key, model name and API address."
            )

        logger.info(
            f"Using activated model configuration: provider={self.provider}, model={self.model}"
        )

    def _build_url(self) -> str:
        """Build request URL"""
        if self.endpoint.startswith("http"):
            return self.endpoint
        if not self.base_url:
            raise ValueError("base_url not set")
        base = self.base_url.rstrip("/")
        path = self.endpoint.lstrip("/")
        return f"{base}/{path}"

    def _summarize_messages(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build concise message summary for logging"""
        total_messages = len(messages)
        image_messages = 0
        text_preview: List[str] = []
        for message in messages:
            content = message.get("content")
            if isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and part.get("type") in {
                        "image",
                        "image_url",
                    }:
                        image_messages += 1
                    elif isinstance(part, dict) and part.get("type") == "text":
                        text = part.get("text", "")
                        if text:
                            text_preview.append(text[:80])
            elif isinstance(content, str):
                if content:
                    text_preview.append(content[:80])
        return {
            "total_messages": total_messages,
            "image_parts": image_messages,
            "text_preview": text_preview[:3],
        }

    def _log_request_error(
        self,
        exc: Exception,
        attempt: int,
        url: str,
        payload: Dict[str, Any],
        response: Optional[httpx.Response],
        final_attempt: bool,
    ) -> None:
        """Log request error details"""
        level = logger.error if final_attempt else logger.warning
        summary = {
            "provider": self.provider,
            "model": self.model,
            "attempt": attempt,
            "max_retries": self.max_retries,
            "url": url,
            "timeout": {
                "connect": getattr(self.timeout, "connect", None),
                "read": getattr(self.timeout, "read", None),
            },
            "payload_summary": {
                "max_tokens": payload.get("max_tokens"),
                "temperature": payload.get("temperature"),
                "messages": self._summarize_messages(payload.get("messages", [])),
            },
            "error_type": exc.__class__.__name__,
            "error_message": str(exc) or None,
        }
        if response is not None:
            summary["status_code"] = response.status_code
            try:
                response_text = response.text
            except Exception:
                response_text = "<unavailable>"
            summary["response_text"] = response_text[:500]
        level(f"LLM API request failed: {json.dumps(summary, ensure_ascii=False)}")

    def _should_retry(self, response: Optional[httpx.Response]) -> bool:
        """Determine whether to continue retrying"""
        if response is None:
            return True
        return (
            response.status_code >= 500
            and response.status_code not in self.non_retry_status
        )

    def _build_error_result(self, error: Optional[Exception]) -> Dict[str, Any]:
        """Build error return result"""
        if error is None:
            return {
                "content": "API request failed: Unknown error",
                "usage": {},
                "model": self.model,
            }
        if isinstance(error, httpx.TimeoutException):
            message = "Request timeout, please check network connection or model service availability"
        elif isinstance(error, httpx.HTTPStatusError):
            response = error.response
            if response is not None:
                message = f"HTTP {response.status_code}: {response.text[:200]}"
            else:
                message = "HTTP status error (empty response)"
        elif isinstance(error, httpx.RequestError):
            message = (
                f"Network request exception: {str(error) or error.__class__.__name__}"
            )
        else:
            message = str(error) or error.__class__.__name__
        return {
            "content": f"API request failed: {message}",
            "usage": {},
            "model": self.model,
        }

    def reload_config(self):
        """Reload LLM configuration (read latest configuration from config file)"""
        self._setup_client()

    async def chat_completion(
        self, messages: List[Dict[str, Any]], **kwargs
    ) -> Dict[str, Any]:
        """Chat completion API"""
        # Reload configuration before each request to ensure using latest config file content
        self.reload_config()

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if self.extra_headers:
            headers.update(self.extra_headers)

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", 2000),
            "temperature": kwargs.get("temperature", 0.7),
            "stream": False,
        }

        for key, value in kwargs.items():
            if key not in ["max_tokens", "temperature", "stream"]:
                payload[key] = value

        url = self._build_url()
        last_error: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 2):
            response: Optional[httpx.Response] = None
            try:
                async with httpx.AsyncClient(
                    timeout=self.timeout, verify=self.verify_ssl, http2=self.use_http2
                ) as client:
                    response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()

                result = response.json()
                if "choices" in result and result["choices"]:
                    choice = result["choices"][0]
                    content = choice.get("message", {}).get("content", "")

                    # Extract usage information and safely convert to integers
                    usage = result.get("usage", {}) or {}
                    try:
                        prompt_tokens = int(usage.get("prompt_tokens", 0) or 0)
                    except Exception:
                        prompt_tokens = 0
                    try:
                        completion_tokens = int(usage.get("completion_tokens", 0) or 0)
                    except Exception:
                        completion_tokens = 0
                    try:
                        total_tokens = int(
                            usage.get("total_tokens", prompt_tokens + completion_tokens)
                            or (prompt_tokens + completion_tokens)
                        )
                    except Exception:
                        total_tokens = prompt_tokens + completion_tokens

                    # Try to read cost from return (if backend/provider returned this field), otherwise 0.0
                    try:
                        cost = float(result.get("cost", 0.0) or 0.0)
                    except Exception:
                        cost = 0.0

                    # Request type used to distinguish different call scenarios, default 'chat'
                    request_type = kwargs.get("request_type", "chat")

                    # Exception protection: recording to dashboard should not affect main flow
                    try:
                        dashboard_manager = get_dashboard_manager()
                        dashboard_manager.record_llm_usage(
                            model=result.get("model", self.model),
                            prompt_tokens=prompt_tokens,
                            completion_tokens=completion_tokens,
                            total_tokens=total_tokens,
                            cost=cost,
                            request_type=request_type,
                        )
                    except Exception as e:
                        # Only log debug log, avoid throwing exceptions that affect main flow
                        logger.debug(f"Failed to record LLM usage to dashboard: {e}")

                    return {
                        "content": content,
                        "usage": usage,
                        "model": result.get("model", self.model),
                    }

                logger.error(
                    f"LLM API response format error: {json.dumps(result, ensure_ascii=False)[:500]}"
                )
                return {
                    "content": "API response format error",
                    "usage": {},
                    "model": self.model,
                }

            except httpx.HTTPStatusError as exc:
                last_error = exc
                response = exc.response
                final_attempt = attempt > self.max_retries or not self._should_retry(
                    response
                )
                self._log_request_error(
                    exc, attempt, url, payload, response, final_attempt
                )
                if final_attempt:
                    break

            except httpx.TimeoutException as exc:
                last_error = exc
                final_attempt = attempt > self.max_retries
                self._log_request_error(exc, attempt, url, payload, None, final_attempt)
                if final_attempt:
                    break

            except httpx.RequestError as exc:
                last_error = exc
                final_attempt = attempt > self.max_retries
                self._log_request_error(exc, attempt, url, payload, None, final_attempt)
                if final_attempt:
                    break

            except Exception as exc:
                last_error = exc
                self._log_request_error(exc, attempt, url, payload, None, True)
                break

            await asyncio.sleep(self.retry_backoff * attempt)

        return self._build_error_result(last_error)

    async def chat_completion_stream(
        self, messages: List[Dict[str, Any]], **kwargs
    ) -> AsyncGenerator[str, None]:
        """Chat completion API (streaming)

        Args:
            messages: Conversation message list
            **kwargs: Other parameters (max_tokens, temperature, etc.)

        Yields:
            str: Streamed text fragments
        """
        # Reload configuration before each request
        self.reload_config()

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if self.extra_headers:
            headers.update(self.extra_headers)

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", 2000),
            "temperature": kwargs.get("temperature", 0.7),
            "stream": True,  # Enable streaming output
        }

        for key, value in kwargs.items():
            if key not in ["max_tokens", "temperature", "stream"]:
                payload[key] = value

        url = self._build_url()

        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(connect=10.0, read=60.0, write=30.0, pool=5.0),
                verify=self.verify_ssl,
                http2=self.use_http2,
            ) as client:
                async with client.stream(
                    "POST", url, headers=headers, json=payload
                ) as response:
                    response.raise_for_status()

                    # Read streaming response line by line
                    async for line in response.aiter_lines():
                        # Skip empty lines
                        if not line.strip():
                            continue

                        # SSE format: data: {...}
                        if line.startswith("data: "):
                            data_str = line[6:]  # Remove "data: " prefix

                            # Check if it's the end signal
                            if data_str.strip() == "[DONE]":
                                break

                            try:
                                data = json.loads(data_str)
                                # Extract content delta
                                if "choices" in data and data["choices"]:
                                    choice = data["choices"][0]
                                    delta = choice.get("delta", {})
                                    content = delta.get("content", "")

                                    if content:
                                        yield content

                                # Check if completed
                                if data.get("choices", [{}])[0].get("finish_reason"):
                                    break

                            except json.JSONDecodeError as e:
                                logger.warning(
                                    f"Failed to parse streaming response: {data_str[:100]}, error: {e}"
                                )
                                continue

        except httpx.HTTPStatusError as exc:
            logger.error(
                f"LLM streaming API HTTP error: {exc.response.status_code}, {exc.response.text[:200]}"
            )
            yield f"[Error] HTTP {exc.response.status_code}: {exc.response.text[:100]}"
        except httpx.TimeoutException as exc:
            logger.error(f"LLM streaming API timeout: {exc}")
            yield "[Error] Request timeout, please check network connection"
        except httpx.RequestError as exc:
            logger.error(f"LLM streaming API request error: {exc}")
            yield f"[Error] Network request exception: {str(exc)[:100]}"
        except Exception as exc:
            logger.error(f"LLM streaming API unknown error: {exc}", exc_info=True)
            yield f"[Error] {str(exc)[:100]}"

    async def generate_summary(self, content: str, **kwargs) -> str:
        """Generate summary"""
        messages = self.prompt_manager.build_messages("general_summary")
        if messages and len(messages) > 1:
            messages[1]["content"] = content

        # Get configuration parameters
        config_params = self.prompt_manager.get_config_params("general_summary")
        config_params.update(kwargs)

        result = await self.chat_completion(messages, **config_params)
        return result.get("content", "Summary generation failed")


def get_llm_client(provider: Optional[str] = None) -> LLMClient:
    """Get LLM client instance"""
    return LLMClient(provider)
