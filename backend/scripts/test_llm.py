#!/usr/bin/env python3
"""
Test LLM API configuration
"""

import asyncio
import sys
import os

# Add project root directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm.client import get_llm_client
from llm.prompt_manager import get_test_prompt
from core.logger import get_logger

logger = get_logger(__name__)


async def test_llm_api():
    """Test LLM API"""
    try:
        # 获取 LLM 客户端
        client = get_llm_client()
        logger.info(f"使用 LLM 提供商: {client.provider}")
        logger.info(f"模型: {client.model}")
        logger.info(f"API URL: {client.base_url}")

        # 测试简单对话
        messages = get_test_prompt()

        logger.info("发送测试消息...")
        result = await client.chat_completion(messages)

        logger.info(f"API 响应: {result}")

        if result.get("content"):
            print(f"✅ LLM API 测试成功!")
            print(f"回复: {result['content']}")
        else:
            print(f"❌ LLM API 测试失败: {result}")

    except Exception as e:
        logger.error(f"LLM API 测试失败: {e}")
        print(f"❌ LLM API 测试失败: {e}")


if __name__ == "__main__":
    print("开始测试 LLM API 配置...")
    asyncio.run(test_llm_api())
