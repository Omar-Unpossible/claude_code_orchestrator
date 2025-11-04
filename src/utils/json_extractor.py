"""JSON extraction utilities for LLM responses.

Provides robust JSON parsing with multiple fallback strategies for handling
LLM responses that may include preambles, explanations, or markdown formatting.
"""

import json
import logging
import re
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)


def extract_json(response: str) -> Optional[Dict[str, Any]]:
    """Extract JSON from LLM response that may have extra text.

    Tries multiple strategies:
    1. Parse response directly
    2. Find JSON block with regex
    3. Find content between first { and last }
    4. Extract from markdown code block

    Args:
        response: LLM response text

    Returns:
        Parsed JSON dict or None if extraction fails

    Example:
        >>> extract_json('Sure! {"key": "value"}')
        {'key': 'value'}
        >>> extract_json('```json\\n{"key": "value"}\\n```')
        {'key': 'value'}
    """
    if not response:
        return None

    response = response.strip()

    # Strategy 1: Direct parse
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass

    # Strategy 2: Find JSON with regex (greedy, captures outermost braces)
    # This pattern handles nested braces
    json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
    matches = re.findall(json_pattern, response, re.DOTALL)
    if matches:
        # Try each match (usually just one)
        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue

    # Strategy 3: Find content between first { and last }
    try:
        first_brace = response.index('{')
        last_brace = response.rindex('}')
        json_str = response[first_brace:last_brace + 1]
        return json.loads(json_str)
    except (ValueError, json.JSONDecodeError):
        pass

    # Strategy 4: Extract from markdown code block
    code_block_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
    match = re.search(code_block_pattern, response, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    logger.warning(f"Failed to extract JSON from response: {response[:200]}...")
    return None


def validate_json_structure(
    data: Dict[str, Any],
    required_keys: list,
    optional_keys: Optional[list] = None
) -> Tuple[bool, Optional[str]]:
    """Validate JSON structure has required keys.

    Args:
        data: Parsed JSON data
        required_keys: List of required key names
        optional_keys: List of optional key names (not validated)

    Returns:
        Tuple of (is_valid, error_message)

    Example:
        >>> validate_json_structure({'a': 1}, ['a', 'b'])
        (False, "Missing required keys: ['b']")
        >>> validate_json_structure({'a': 1, 'b': 2}, ['a', 'b'])
        (True, None)
    """
    if not isinstance(data, dict):
        return False, "Response is not a JSON object"

    missing = [key for key in required_keys if key not in data]
    if missing:
        return False, f"Missing required keys: {missing}"

    return True, None


def ensure_json_keys(
    data: Dict[str, Any],
    required_keys: Dict[str, Any]
) -> Dict[str, Any]:
    """Ensure JSON has required keys with default values.

    Adds missing keys with default values rather than failing.

    Args:
        data: JSON data to validate
        required_keys: Dict mapping key names to default values

    Returns:
        Updated JSON with all required keys present

    Example:
        >>> ensure_json_keys({'a': 1}, {'a': 0, 'b': 'default'})
        {'a': 1, 'b': 'default'}
    """
    if not isinstance(data, dict):
        logger.error("Data is not a dict, returning defaults")
        return required_keys.copy()

    result = data.copy()
    for key, default_value in required_keys.items():
        if key not in result:
            logger.warning(f"Adding missing key '{key}' with default: {default_value}")
            result[key] = default_value

    return result
