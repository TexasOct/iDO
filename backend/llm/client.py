"""
通用 LLM 客户端
仅使用数据库中激活的模型配置
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
    """LLM 客户端基类"""

    def __init__(self, provider: Optional[str] = None):
        self.prompt_manager = get_prompt_manager()
        self.active_model_config: Optional[Dict[str, Any]] = None

        # 仅允许使用数据库中的激活模型配置
        self.active_model_config = self._fetch_active_model_config()
        if not self.active_model_config:
            raise RuntimeError("未找到激活的 LLM 模型配置，请在设置中添加并激活模型。")

        active_provider = self.active_model_config.get('provider')
        if provider and provider != active_provider:
            logger.warning(
                f"指定的 provider {provider} 与激活模型 {active_provider} 不一致，将使用激活模型配置"
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
        """从数据库中读取当前激活的模型配置"""
        try:
            db = get_db()
            result = db.get_active_llm_model()
            if result:
                self.active_model_config = result
                return result
        except Exception as exc:
            logger.debug(f"读取激活模型配置失败: {exc}")
        return None

    def _setup_client(self):
        """设置客户端，使用激活模型配置"""
        config = self.active_model_config or self._fetch_active_model_config()

        if not config:
            raise RuntimeError("未找到激活的 LLM 模型配置，请先在设置中完成模型配置。")

        self.api_key = config.get('api_key')
        self.model = config.get('model')
        self.base_url = config.get('api_url') or config.get('base_url')
        self.endpoint = config.get('endpoint', "/chat/completions")
        self.extra_headers = config.get('headers', {}) or {}

        if not all([self.api_key, self.model, self.base_url]):
            raise ValueError("激活的 LLM 模型配置不完整，请检查 API Key、模型名称和 API 地址。")

        logger.info(f"使用激活模型配置: provider={self.provider}, model={self.model}")

    def _build_url(self) -> str:
        """构建请求 URL"""
        if self.endpoint.startswith("http"):
            return self.endpoint
        if not self.base_url:
            raise ValueError("base_url 未设置")
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

    def reload_config(self):
        """重新加载 LLM 配置（从配置文件读取最新配置）"""
        self._setup_client()

    async def chat_completion(self, messages: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """聊天完成 API"""
        # 每次请求前重新加载配置，确保使用最新的配置文件内容
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

                    # 提取 usage 信息并安全转换为整数
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
                        total_tokens = int(usage.get("total_tokens", prompt_tokens + completion_tokens) or (prompt_tokens + completion_tokens))
                    except Exception:
                        total_tokens = prompt_tokens + completion_tokens

                    # 尝试从返回中读取 cost（如果后端/提供者返回了该字段），否则为 0.0
                    try:
                        cost = float(result.get("cost", 0.0) or 0.0)
                    except Exception:
                        cost = 0.0

                    # 请求类型用于区分不同调用场景，默认 'chat'
                    request_type = kwargs.get("request_type", "chat")

                    # 异常保护：记录到仪表盘不应影响主流程
                    try:
                        dashboard_manager = get_dashboard_manager()
                        dashboard_manager.record_llm_usage(
                            model=result.get("model", self.model),
                            prompt_tokens=prompt_tokens,
                            completion_tokens=completion_tokens,
                            total_tokens=total_tokens,
                            cost=cost,
                            request_type=request_type
                        )
                    except Exception as e:
                        # 只记录调试日志，避免抛出影响主流程
                        logger.debug(f"记录LLM使用到仪表盘失败: {e}")

                    return {
                        "content": content,
                        "usage": usage,
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

    async def chat_completion_stream(
        self,
        messages: List[Dict[str, Any]],
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """聊天完成 API（流式）

        Args:
            messages: 对话消息列表
            **kwargs: 其他参数（max_tokens, temperature 等）

        Yields:
            str: 流式返回的文本片段
        """
        # 每次请求前重新加载配置
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
            "stream": True  # 启用流式输出
        }

        for key, value in kwargs.items():
            if key not in ["max_tokens", "temperature", "stream"]:
                payload[key] = value

        url = self._build_url()

        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(connect=10.0, read=60.0, write=30.0, pool=5.0),
                verify=self.verify_ssl,
                http2=self.use_http2
            ) as client:
                async with client.stream(
                    "POST",
                    url,
                    headers=headers,
                    json=payload
                ) as response:
                    response.raise_for_status()

                    # 逐行读取流式响应
                    async for line in response.aiter_lines():
                        # 跳过空行
                        if not line.strip():
                            continue

                        # SSE 格式：data: {...}
                        if line.startswith("data: "):
                            data_str = line[6:]  # 移除 "data: " 前缀

                            # 检查是否为结束信号
                            if data_str.strip() == "[DONE]":
                                break

                            try:
                                data = json.loads(data_str)
                                # 提取 content delta
                                if "choices" in data and data["choices"]:
                                    choice = data["choices"][0]
                                    delta = choice.get("delta", {})
                                    content = delta.get("content", "")

                                    if content:
                                        yield content

                                # 检查是否完成
                                if data.get("choices", [{}])[0].get("finish_reason"):
                                    break

                            except json.JSONDecodeError as e:
                                logger.warning(f"解析流式响应失败: {data_str[:100]}, 错误: {e}")
                                continue

        except httpx.HTTPStatusError as exc:
            logger.error(f"LLM 流式 API HTTP 错误: {exc.response.status_code}, {exc.response.text[:200]}")
            yield f"[错误] HTTP {exc.response.status_code}: {exc.response.text[:100]}"

        except httpx.TimeoutException as exc:
            logger.error(f"LLM 流式 API 超时: {exc}")
            yield "[错误] 请求超时，请检查网络连接"

        except httpx.RequestError as exc:
            logger.error(f"LLM 流式 API 请求错误: {exc}")
            yield f"[错误] 网络请求异常: {str(exc)[:100]}"

        except Exception as exc:
            logger.error(f"LLM 流式 API 未知错误: {exc}", exc_info=True)
            yield f"[错误] {str(exc)[:100]}"

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


def get_llm_client(provider: Optional[str] = None) -> LLMClient:
    """获取 LLM 客户端实例"""
    return LLMClient(provider)
