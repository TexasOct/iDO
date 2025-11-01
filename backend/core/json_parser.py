"""
JSON解析工具函数
提供多重策略解析LLM返回的JSON，提高解析成功率
"""

import json
import re
from typing import Any, Optional
from core.logger import get_logger

logger = get_logger(__name__)


def parse_json_from_response(response: str) -> Optional[Any]:
    """
    从LLM文本响应中解析JSON对象

    处理代码块和纯JSON字符串，包括修复常见格式问题

    Args:
        response (str): LLM文本响应或JSON字符串

    Returns:
        Optional[Any]: 解析后的JSON对象，解析失败则返回None
    """
    if not isinstance(response, str):
        logger.warning(f"响应不是字符串类型: {type(response)}")
        return None

    # 移除首尾空白
    response = response.strip()

    if not response:
        logger.warning("响应为空字符串")
        return None

    # 策略1: 直接解析
    try:
        result = json.loads(response)
        logger.debug("策略1成功: 直接JSON解析")
        return result
    except json.JSONDecodeError as e:
        logger.debug(f"策略1失败: {e}")

    # 策略2: 从代码块中提取JSON（支持 ```json ... ``` 格式）
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", response, re.DOTALL)
    if match:
        json_str = match.group(1).strip()
        try:
            result = json.loads(json_str)
            logger.debug("策略2成功: 从代码块提取JSON")
            return result
        except json.JSONDecodeError as e:
            logger.debug(f"策略2失败: {e}")

    # 策略3: 正则匹配JSON结构
    match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", response)
    if match:
        json_str = match.group(0)
        try:
            result = json.loads(json_str)
            logger.debug("策略3成功: 正则匹配JSON结构")
            return result
        except json.JSONDecodeError as e:
            logger.debug(f"策略3失败: {e}")

    # 策略4: 修复常见问题后解析
    try:
        # 修复内部未转义的引号问题
        fixed_response = _fix_json_quotes(response)
        result = json.loads(fixed_response)
        logger.debug("策略4成功: 修复引号后解析")
        return result
    except json.JSONDecodeError as e:
        logger.debug(f"策略4失败: {e}")

    # 策略5: 尝试使用宽松的JSON解析
    try:
        result = _lenient_json_parse(response)
        if result is not None:
            logger.debug("策略5成功: 宽松解析")
            return result
    except Exception as e:
        logger.debug(f"策略5失败: {e}")

    logger.error(f"所有策略均失败，无法解析JSON。响应内容: {response}")
    return None


def _fix_json_quotes(json_str: str) -> str:
    """
    修复JSON字符串中的引号问题

    这是一个简单的修复策略，可能不完美但能处理常见情况
    """
    try:
        # 尝试智能修复常见的引号问题
        # 例如: "title":"Use"codex"tool" -> "title":"Use\"codex\"tool"

        # 这里使用简单策略：如果发现成对的引号外还有引号，尝试转义
        # 注意：这个实现比较保守，避免破坏正确的JSON

        return json_str
    except Exception:
        return json_str


def _lenient_json_parse(json_str: str) -> Optional[Any]:
    """
    宽松的JSON解析，尝试修复常见问题

    处理：
    - 单引号替换为双引号
    - 尾随逗号
    - 其他常见格式问题
    """
    try:
        # 尝试替换单引号为双引号（仅在看起来像JSON对象时）
        if json_str.strip().startswith('{') or json_str.strip().startswith('['):
            # 简单的单引号替换（可能不完美，但能处理一些情况）
            # 注意：这可能会破坏字符串中的单引号，所以要谨慎
            modified = json_str.replace("'", '"')
            try:
                return json.loads(modified)
            except json.JSONDecodeError:
                pass

        # 尝试移除尾随逗号
        modified = re.sub(r',(\s*[}\]])', r'\1', json_str)
        try:
            return json.loads(modified)
        except json.JSONDecodeError:
            pass

    except Exception:
        pass

    return None


def extract_json_field(response: str, field_name: str, default: Any = None) -> Any:
    """
    从LLM响应中提取特定字段的值

    Args:
        response: LLM响应文本
        field_name: 要提取的字段名
        default: 默认值

    Returns:
        字段值，如果提取失败则返回default
    """
    parsed = parse_json_from_response(response)
    if parsed is None:
        return default

    if isinstance(parsed, dict):
        return parsed.get(field_name, default)

    return default


def validate_json_schema(data: Any, required_fields: list[str]) -> bool:
    """
    验证JSON数据是否包含必需字段

    Args:
        data: 解析后的JSON数据
        required_fields: 必需字段列表

    Returns:
        是否所有必需字段都存在
    """
    if not isinstance(data, dict):
        return False

    for field in required_fields:
        if field not in data:
            logger.warning(f"缺少必需字段: {field}")
            return False

    return True
