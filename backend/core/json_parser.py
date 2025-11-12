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

    # Pre-process: Normalize Unicode quotes to ASCII quotes
    # This is crucial for handling LLM outputs in Chinese/multilingual contexts
    response = _normalize_quotes(response)

    # Strategy 1: Direct parsing
    try:
        result = json.loads(response)
        logger.debug("Strategy 1 success: Direct JSON parsing")
        return result
    except json.JSONDecodeError as e:
        logger.debug(f"Strategy 1 failed: {e}")

    # Strategy 2: Try json-repair library early (before extraction)
    # json-repair is very good at handling malformed JSON with quote issues
    try:
        from json_repair import repair_json

        repaired = repair_json(response)
        result = json.loads(repaired)
        logger.debug("Strategy 2 success: json-repair on full response")
        return result
    except ImportError:
        logger.debug("Strategy 2 skipped: json-repair library not available")
    except Exception as e:
        logger.debug(f"Strategy 2 failed: {e}")

    # Strategy 3: Extract JSON from code blocks (supports ```json ... ``` format)
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", response, re.DOTALL)
    if match:
        json_str = match.group(1).strip()
        try:
            result = json.loads(json_str)
            logger.debug("Strategy 3 success: Extract JSON from code block")
            return result
        except json.JSONDecodeError as e:
            logger.debug(f"Strategy 3 failed: {e}")
            # Try json-repair on extracted JSON
            try:
                from json_repair import repair_json

                repaired = repair_json(json_str)
                result = json.loads(repaired)
                logger.debug("Strategy 3b success: json-repair on extracted JSON")
                return result
            except Exception as e2:
                logger.debug(f"Strategy 3b failed: {e2}")

    # Strategy 4: Regex match JSON structure
    match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", response)
    if match:
        json_str = match.group(0)
        try:
            result = json.loads(json_str)
            logger.debug("Strategy 4 success: Regex match JSON structure")
            return result
        except json.JSONDecodeError as e:
            logger.debug(f"Strategy 4 failed: {e}")
            # Try json-repair on regex-matched JSON
            try:
                from json_repair import repair_json

                repaired = repair_json(json_str)
                result = json.loads(repaired)
                logger.debug("Strategy 4b success: json-repair on regex-matched JSON")
                return result
            except Exception as e2:
                logger.debug(f"Strategy 4b failed: {e2}")

    # Strategy 5: Parse after fixing common issues
    try:
        # Fix internal unescaped quote issues
        fixed_response = _fix_json_quotes(response)
        result = json.loads(fixed_response)
        logger.debug("Strategy 5 success: Parse after fixing quotes")
        return result
    except json.JSONDecodeError as e:
        logger.debug(f"Strategy 5 failed: {e}")

    # Strategy 5: Try to recover truncated JSON
    try:
        result = _recover_truncated_json(response)
        if result is not None:
            logger.warning(
                "Strategy 5 success: Recovered truncated JSON (may be incomplete)"
            )
            return result
    except Exception as e:
        logger.debug(f"Strategy 5 failed: {e}")

    # Strategy 6: Try using lenient JSON parsing
    try:
        result = _lenient_json_parse(response)
        if result is not None:
            logger.debug("Strategy 6 success: Lenient parsing")
            return result
    except Exception as e:
        logger.debug(f"Strategy 6 failed: {e}")

    logger.error(
        f"All strategies failed, unable to parse JSON. Response content: {response}"
    )
    return None


def _normalize_quotes(text: str) -> str:
    """
    Normalize various Unicode quote characters to standard ASCII quotes

    This handles common issues where LLMs (especially in Chinese contexts)
    generate Unicode quotation marks instead of ASCII quotes.

    Args:
        text: Input text with possible Unicode quotes

    Returns:
        Text with normalized ASCII quotes
    """
    # Map of Unicode quotes to ASCII equivalents
    quote_map = {
        # Chinese/CJK quotes
        '"': '"',  # DOUBLE QUOTATION MARK
        """: "'",  # LEFT SINGLE QUOTATION MARK
        """: "'",  # RIGHT SINGLE QUOTATION MARK
        # Other Unicode quotes
        "«": '"',  # LEFT-POINTING DOUBLE ANGLE QUOTATION MARK
        "»": '"',  # RIGHT-POINTING DOUBLE ANGLE QUOTATION MARK
        "‹": "'",  # SINGLE LEFT-POINTING ANGLE QUOTATION MARK
        "›": "'",  # SINGLE RIGHT-POINTING ANGLE QUOTATION MARK
        "„": '"',  # DOUBLE LOW-9 QUOTATION MARK
        "‟": '"',  # DOUBLE HIGH-REVERSED-9 QUOTATION MARK
        "‚": "'",  # SINGLE LOW-9 QUOTATION MARK
        "‛": "'",  # SINGLE HIGH-REVERSED-9 QUOTATION MARK
        # Fullwidth quotes (often used in Asian text)
        "＂": '"',  # FULLWIDTH QUOTATION MARK
        "＇": "'",  # FULLWIDTH APOSTROPHE
    }

    for unicode_quote, ascii_quote in quote_map.items():
        text = text.replace(unicode_quote, ascii_quote)

    return text


def _fix_json_quotes(json_str: str) -> str:
    """
    Fix quote issues in JSON strings

    This is a simple fixing strategy, may not be perfect but handles common cases
    Handles unescaped quotes within string values
    """
    try:
        # Strategy 1: Fix unescaped quotes in string values using regex
        # Match "key":"value" patterns and escape quotes within the value
        def fix_quotes_in_match(match):
            prefix = match.group(1)  # Everything before the value
            value = match.group(2)  # The value content
            suffix = match.group(3)  # Everything after the value

            # Escape unescaped quotes in the value
            # First, temporarily protect already escaped quotes
            value = value.replace('\\"', "\x00ESCAPED_QUOTE\x00")
            # Then escape all remaining quotes
            value = value.replace('"', '\\"')
            # Finally, restore the already escaped quotes
            value = value.replace("\x00ESCAPED_QUOTE\x00", '\\"')

            return f'{prefix}"{value}"{suffix}'

        # Pattern to match JSON string values
        # Matches: "key": "value with possible "quotes" inside"
        # This is a simplified pattern that handles most cases
        pattern = r'(:\s*)"([^"]*(?:"[^"]*)*)"([,\}\]\s])'
        fixed = re.sub(pattern, fix_quotes_in_match, json_str)

        # Strategy 2: Try using json-repair library if available
        try:
            from json_repair import repair_json

            # Only use json-repair if the basic fix didn't produce valid JSON
            try:
                json.loads(fixed)
                return fixed  # Basic fix worked
            except json.JSONDecodeError:
                # Basic fix didn't work, try json-repair
                repaired = repair_json(fixed)
                return repaired
        except ImportError:
            # json-repair not installed, use basic fix only
            logger.debug(
                "json-repair library not available, using basic quote fixing only"
            )
            return fixed
        except Exception as e:
            # json-repair failed, return basic fix
            logger.debug(f"json-repair failed: {e}, using basic fix")
            return fixed

    except Exception as e:
        logger.debug(f"Quote fixing failed: {e}")
        return json_str


def _recover_truncated_json(json_str: str) -> Optional[Any]:
    """
    Attempt to recover truncated JSON by closing incomplete structures

    This handles cases where LLM output was cut off mid-response.
    Returns partial data that was successfully parsed.
    """
    try:
        # First try to extract from code block
        match = re.search(r"```(?:json)?\s*([\s\S]*?)(?:```|$)", json_str, re.DOTALL)
        if match:
            json_str = match.group(1).strip()

        # Find the last valid JSON character position
        # Count opening/closing brackets and braces
        open_braces = 0
        open_brackets = 0
        in_string = False
        escape_next = False
        last_valid_pos = 0

        for i, char in enumerate(json_str):
            if escape_next:
                escape_next = False
                continue

            if char == "\\":
                escape_next = True
                continue

            if char == '"' and not escape_next:
                in_string = not in_string
                continue

            if in_string:
                continue

            if char == "{":
                open_braces += 1
            elif char == "}":
                open_braces -= 1
            elif char == "[":
                open_brackets += 1
            elif char == "]":
                open_brackets -= 1

            # Track last position where we had valid structure
            if open_braces >= 0 and open_brackets >= 0:
                last_valid_pos = i + 1

        # If truncated, try to close the structures
        if open_braces > 0 or open_brackets > 0:
            # Find last complete item before truncation
            truncated = json_str[:last_valid_pos]

            # Remove incomplete trailing content (likely truncated in middle of field)
            # Find last complete field by looking for last comma or opening brace/bracket
            last_comma = truncated.rfind(",")
            last_open_brace = truncated.rfind("{")
            last_open_bracket = truncated.rfind("[")

            # Use the position that appears latest
            cutoff = max(last_comma, last_open_brace, last_open_bracket)
            if cutoff > 0:
                truncated = truncated[:cutoff]

            # Close any remaining open structures
            truncated += "]" * open_brackets
            truncated += "}" * open_braces

            logger.warning(
                f"Attempting to recover truncated JSON (added {open_brackets} ']' and {open_braces} '}}')"
            )

            try:
                result = json.loads(truncated)
                return result
            except json.JSONDecodeError:
                # If that didn't work, try being more aggressive
                # Look for the last complete array/object
                for pattern in [r'(\{[^{]*"combined_\w+":\s*\[)', r"(\[[^[]*\{)"]:
                    match = re.search(pattern, json_str)
                    if match:
                        start = match.start()
                        partial = json_str[start:]
                        # Try to close it properly
                        if partial.startswith("{"):
                            partial += "]}"
                        elif partial.startswith("["):
                            partial += "]"
                        try:
                            return json.loads(partial)
                        except json.JSONDecodeError:
                            continue

    except Exception as e:
        logger.debug(f"Truncation recovery failed: {e}")

    return None


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
