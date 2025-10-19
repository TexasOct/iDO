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
        self._setup_client()
    
    def _setup_client(self):
        """设置客户端"""
        llm_config = self.config.get('llm', {})
        provider_config = llm_config.get(self.provider, {})
        
        self.api_key = provider_config.get('api_key')
        self.model = provider_config.get('model')
        self.base_url = provider_config.get('base_url')
        
        if not all([self.api_key, self.model, self.base_url]):
            raise ValueError(f"LLM 配置不完整: {self.provider}")
        
        logger.info(f"初始化 {self.provider} LLM 客户端: {self.model}")
    
    async def chat_completion(self, messages: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """聊天完成 API"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "messages": messages,
                "max_tokens": kwargs.get("max_tokens", 2000),
                "temperature": kwargs.get("temperature", 0.7),
                "stream": False
            }
            
            # 添加其他参数
            for key, value in kwargs.items():
                if key not in ["max_tokens", "temperature", "stream"]:
                    payload[key] = value
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                
                result = response.json()
                
                # 提取回复内容
                if "choices" in result and len(result["choices"]) > 0:
                    choice = result["choices"][0]
                    content = choice.get("message", {}).get("content", "")
                    return {
                        "content": content,
                        "usage": result.get("usage", {}),
                        "model": result.get("model", self.model)
                    }
                else:
                    logger.error(f"LLM API 响应格式错误: {result}")
                    return {"content": "API 响应格式错误", "usage": {}, "model": self.model}
                    
        except httpx.HTTPError as e:
            logger.error(f"LLM API 请求失败: {e}")
            return {"content": f"API 请求失败: {str(e)}", "usage": {}, "model": self.model}
        except Exception as e:
            logger.error(f"LLM API 调用异常: {e}")
            return {"content": f"API 调用异常: {str(e)}", "usage": {}, "model": self.model}
    
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
