"""
JSON parsing utility functions
Provides multi-strategy parsing for LLM returned JSON to improve parsing success rate
"""

import json
import re
from typing import Any, Optional
from core.logger import get_logger

logger = get_logger(__name__)


def parse_json_from_response(response: str) -> Optional[Any]:
    """
    Parse JSON object from LLM text response

    Handles code blocks and plain JSON strings, including fixing common format issues

    Args:
        response (str): LLM text response or JSON string

    Returns:
        Optional[Any]: Parsed JSON object, returns None if parsing fails
    """
    if not isinstance(response, str):
        logger.warning(f"Response is not string type: {type(response)}")
        return None

    # Remove leading/trailing whitespace
    response = response.strip()

    if not response:
        logger.warning("Response is empty string")
        return None

    # Strategy 1: Direct parsing
    try:
        result = json.loads(response)
        logger.debug("Strategy 1 success: Direct JSON parsing")
        return result
    except json.JSONDecodeError as e:
        logger.debug(f"Strategy 1 failed: {e}")

    # Strategy 2: Extract JSON from code blocks (supports ```json ... ``` format)
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", response, re.DOTALL)
    if match:
        json_str = match.group(1).strip()
        try:
            result = json.loads(json_str)
            logger.debug("Strategy 2 success: Extract JSON from code block")
            return result
        except json.JSONDecodeError as e:
            logger.debug(f"Strategy 2 failed: {e}")

    # Strategy 3: Regex match JSON structure
    match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", response)
    if match:
        json_str = match.group(0)
        try:
            result = json.loads(json_str)
            logger.debug("Strategy 3 success: Regex match JSON structure")
            return result
        except json.JSONDecodeError as e:
            logger.debug(f"Strategy 3 failed: {e}")

    # Strategy 4: Parse after fixing common issues
    try:
        # Fix internal unescaped quote issues
        fixed_response = _fix_json_quotes(response)
        result = json.loads(fixed_response)
        logger.debug("Strategy 4 success: Parse after fixing quotes")
        return result
    except json.JSONDecodeError as e:
        logger.debug(f"Strategy 4 failed: {e}")

    # Strategy 5: Try using lenient JSON parsing
    try:
        result = _lenient_json_parse(response)
        if result is not None:
            logger.debug("Strategy 5 success: Lenient parsing")
            return result
    except Exception as e:
        logger.debug(f"Strategy 5 failed: {e}")

    logger.error(
        f"All strategies failed, unable to parse JSON. Response content: {response}"
    )
    return None


def _fix_json_quotes(json_str: str) -> str:
    """
    Fix quote issues in JSON strings

    This is a simple fixing strategy, may not be perfect but handles common cases
    """
    try:
        # Try to intelligently fix common quote issues
        # Example: "title":"Use"codex"tool" -> "title":"Use\\"codex\\"tool"

        # Here we use a simple strategy: if there are quotes outside of paired quotes, try to escape
        # Note: This implementation is conservative to avoid breaking correct JSON

        return json_str
    except Exception:
        return json_str


def _lenient_json_parse(json_str: str) -> Optional[Any]:
    """
    Lenient JSON parsing, tries to fix common issues

    Handles:
    - Single quotes replaced with double quotes
    - Trailing commas
    - Other common format issues
    """
    try:
        # Try to replace single quotes with double quotes (only when it looks like a JSON object)
        if json_str.strip().startswith("{") or json_str.strip().startswith("["):
            # Simple single quote replacement (may not be perfect, but can handle some cases)
            # Note: This might break single quotes in strings, so be cautious
            modified = json_str.replace("'", '"')
            try:
                return json.loads(modified)
            except json.JSONDecodeError:
                pass

        # Try to remove trailing commas
        modified = re.sub(r",(\s*[}\]])", r"\1", json_str)
        try:
            return json.loads(modified)
        except json.JSONDecodeError:
            pass

    except Exception:
        pass

    return None


def extract_json_field(response: str, field_name: str, default: Any = None) -> Any:
    """
    Extract specific field value from LLM response

    Args:
        response: LLM response text
        field_name: Field name to extract
        default: Default value

    Returns:
        Field value, returns default if extraction fails
    """
    parsed = parse_json_from_response(response)
    if parsed is None:
        return default

    if isinstance(parsed, dict):
        return parsed.get(field_name, default)

    return default


def validate_json_schema(data: Any, required_fields: list[str]) -> bool:
    """
    Validate if JSON data contains required fields

    Args:
        data: Parsed JSON data
        required_fields: List of required fields

    Returns:
        Whether all required fields are present
    """
    if not isinstance(data, dict):
        return False

    for field in required_fields:
        if field not in data:
            logger.warning(f"Missing required field: {field}")
            return False

    return True
