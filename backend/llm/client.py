"""
通用 LLM 客户端
支持多配置（不同 model/base_url/key）
"""

from typing import Dict, Any, Optional, List
import httpx
import json
import asyncio
from core.logger import get_logger
from config.loader import get_config
from .prompt_manager import get_prompt_manager

logger = get_logger(__name__)


class LLMClient:
    """LLM 客户端基类"""
    
    def __init__(self, provider: str = "qwen3vl"):
        self.provider = provider
        self.config = get_config()
        self.prompt_manager = get_prompt_manager()
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
    
    def _setup_client(self):
        """设置客户端"""
        llm_config = self.config.get('llm', {})
        provider_config = llm_config.get(self.provider, {})
        
        self.api_key = provider_config.get('api_key')
        self.model = provider_config.get('model')
        self.base_url = provider_config.get('base_url')
        self.endpoint = provider_config.get('endpoint', "/chat/completions")
        self.extra_headers = provider_config.get('headers', {})
        self.timeout = self._parse_timeout(provider_config.get('timeout', 30.0))
        self.max_retries = max(int(provider_config.get('max_retries', 2)), 0)
        self.retry_backoff = float(provider_config.get('retry_backoff', 1.5))
        self.verify_ssl = bool(provider_config.get('verify_ssl', True))
        self.use_http2 = bool(provider_config.get('http2', False))
        non_retry_status = provider_config.get('non_retry_status')
        if isinstance(non_retry_status, list):
            self.non_retry_status = set(int(code) for code in non_retry_status if isinstance(code, int))
        
        if not all([self.api_key, self.model, self.base_url]):
            raise ValueError(f"LLM 配置不完整: {self.provider}")
        
        logger.info(f"初始化 {self.provider} LLM 客户端: {self.model}")

    def _parse_timeout(self, timeout_config: Any) -> httpx.Timeout:
        """解析超时配置"""
        if isinstance(timeout_config, (int, float)):
            return httpx.Timeout(float(timeout_config))
        if isinstance(timeout_config, dict):
            return httpx.Timeout(
                connect=float(timeout_config.get("connect", 10.0)),
                read=float(timeout_config.get("read", 30.0)),
                write=float(timeout_config.get("write", 30.0)),
                pool=float(timeout_config.get("pool", 5.0)),
            )
        return httpx.Timeout(30.0)

    def _build_url(self) -> str:
        """构建请求 URL"""
        if self.endpoint.startswith("http"):
            return self.endpoint
        base = self.base_url.rstrip("/")
        path = self.endpoint.lstrip("/")
        return f"{base}/{path}"

    def _summarize_messages(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """构建用于日志的精简消息摘要"""
        total_messages = len(messages)
        image_messages = 0
        text_preview: List[str] = []
        for message in messages:
            content = message.get("content")
            if isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and part.get("type") in {"image", "image_url"}:
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
            "text_preview": text_preview[:3]
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
        """记录请求错误详情"""
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
        level(f"LLM API 请求失败: {json.dumps(summary, ensure_ascii=False)}")

    def _should_retry(self, response: Optional[httpx.Response]) -> bool:
        """判断是否继续重试"""
        if response is None:
            return True
        return response.status_code >= 500 and response.status_code not in self.non_retry_status

    def _build_error_result(self, error: Optional[Exception]) -> Dict[str, Any]:
        """构建错误返回结果"""
        if error is None:
            return {"content": "API 请求失败: 未知错误", "usage": {}, "model": self.model}
        if isinstance(error, httpx.TimeoutException):
            message = "请求超时，请检查网络连接或模型服务可用性"
        elif isinstance(error, httpx.HTTPStatusError):
            response = error.response
            if response is not None:
                message = f"HTTP {response.status_code}: {response.text[:200]}"
            else:
                message = "HTTP 状态错误（响应为空）"
        elif isinstance(error, httpx.RequestError):
            message = f"网络请求异常: {str(error) or error.__class__.__name__}"
        else:
            message = str(error) or error.__class__.__name__
        return {"content": f"API 请求失败: {message}", "usage": {}, "model": self.model}
    
    async def chat_completion(self, messages: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """聊天完成 API"""
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
            "stream": False
        }

        for key, value in kwargs.items():
            if key not in ["max_tokens", "temperature", "stream"]:
                payload[key] = value

        url = self._build_url()
        last_error: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 2):
            response: Optional[httpx.Response] = None
            try:
                async with httpx.AsyncClient(timeout=self.timeout, verify=self.verify_ssl, http2=self.use_http2) as client:
                    response = await client.post(
                        url,
                        headers=headers,
                        json=payload
                    )
                response.raise_for_status()

                result = response.json()
                if "choices" in result and result["choices"]:
                    choice = result["choices"][0]
                    content = choice.get("message", {}).get("content", "")
                    return {
                        "content": content,
                        "usage": result.get("usage", {}),
                        "model": result.get("model", self.model)
                    }

                logger.error(f"LLM API 响应格式错误: {json.dumps(result, ensure_ascii=False)[:500]}")
                return {"content": "API 响应格式错误", "usage": {}, "model": self.model}

            except httpx.HTTPStatusError as exc:
                last_error = exc
                response = exc.response
                final_attempt = attempt > self.max_retries or not self._should_retry(response)
                self._log_request_error(exc, attempt, url, payload, response, final_attempt)
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
    
    async def generate_summary(self, content: str, **kwargs) -> str:
        """生成总结"""
        messages = self.prompt_manager.build_messages("general_summary")
        if messages and len(messages) > 1:
            messages[1]["content"] = content
        
        # 获取配置参数
        config_params = self.prompt_manager.get_config_params("general_summary")
        config_params.update(kwargs)
        
        result = await self.chat_completion(messages, **config_params)
        return result.get("content", "总结生成失败")


def get_llm_client(provider: str = None) -> LLMClient:
    """获取 LLM 客户端实例"""
    if provider is None:
        config = get_config()
        provider = config.get('llm.default_provider', 'qwen3vl')
    
    return LLMClient(provider)
