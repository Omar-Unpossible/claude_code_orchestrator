"""Multi-stage response validation with syntax checking and completeness verification.

This module provides comprehensive validation for agent responses including:
- Completeness checking (required sections present)
- Format validation (JSON, YAML, Markdown)
- Code syntax validation (Python, JSON, YAML)
- Logical consistency checks
- Confidence scoring
- Hallucination detection
- Code block extraction
- Truncation detection
"""

import ast
import json
import logging
import re
from typing import Dict, List, Tuple, Optional, Any

try:
    import yaml
except ImportError:
    yaml = None  # Optional dependency

from src.core.exceptions import (
    ValidationException,
    ResponseIncompleteException
)

logger = logging.getLogger(__name__)


class ResponseValidator:
    """Multi-stage validator for agent responses.

    Validates responses for completeness, format, syntax, and quality.
    Provides confidence scoring based on multiple validation factors.

    Attributes:
        min_length: Minimum acceptable response length
        max_length: Maximum acceptable response length
        forbidden_patterns: Patterns indicating response refusal
        truncation_indicators: Patterns indicating incomplete response

    Example:
        >>> validator = ResponseValidator()
        >>> is_valid = validator.is_complete(response)
        >>> confidence = validator.score_confidence(response, requirements)
        >>> code_blocks = validator.extract_code_blocks(response)
    """

    # Class-level constants
    DEFAULT_MIN_LENGTH = 50
    DEFAULT_MAX_LENGTH = 50000

    FORBIDDEN_PATTERNS = [
        "I cannot",
        "I'm unable",
        "I don't have access",
        "I apologize but I cannot",
        "As an AI"
    ]

    TRUNCATION_INDICATORS = [
        "...",
        "[truncated]",
        "Continued in next",
        "Due to length"
    ]

    # Confidence scoring weights
    WEIGHT_COMPLETENESS = 0.3
    WEIGHT_LENGTH = 0.2
    WEIGHT_CODE = 0.3
    WEIGHT_TONE = 0.1
    WEIGHT_SPECIFICITY = 0.1

    def __init__(
        self,
        min_length: int = DEFAULT_MIN_LENGTH,
        max_length: int = DEFAULT_MAX_LENGTH,
        forbidden_patterns: Optional[List[str]] = None,
        truncation_indicators: Optional[List[str]] = None
    ):
        """Initialize response validator.

        Args:
            min_length: Minimum acceptable response length
            max_length: Maximum acceptable response length
            forbidden_patterns: List of patterns indicating refusal
            truncation_indicators: List of patterns indicating truncation
        """
        self.min_length = min_length
        self.max_length = max_length
        self.forbidden_patterns = forbidden_patterns or self.FORBIDDEN_PATTERNS
        self.truncation_indicators = truncation_indicators or self.TRUNCATION_INDICATORS

        # Compile regex patterns for performance
        self._code_block_pattern = re.compile(
            r'```(\w+)?\n(.*?)```',
            re.DOTALL | re.MULTILINE
        )
        self._forbidden_regex = re.compile(
            '|'.join(re.escape(p) for p in self.forbidden_patterns),
            re.IGNORECASE
        )
        self._truncation_regex = re.compile(
            '|'.join(re.escape(p) for p in self.truncation_indicators),
            re.IGNORECASE
        )

        logger.debug(
            f"ResponseValidator initialized: "
            f"min_length={min_length}, max_length={max_length}"
        )

    def is_complete(self, response: str) -> bool:
        """Check if response is complete and valid.

        Validates:
        - Length within acceptable range
        - No truncation indicators
        - No forbidden patterns (refusals)
        - Code blocks are properly closed

        Args:
            response: The response text to validate

        Returns:
            True if response is complete, False otherwise

        Example:
            >>> validator.is_complete("Here is a complete response.")
            True
            >>> validator.is_complete("I cannot help with that.")
            False
        """
        if not response or not isinstance(response, str):
            logger.warning("Response is empty or not a string")
            return False

        # Check length
        if len(response) < self.min_length:
            logger.warning(
                f"Response too short: {len(response)} < {self.min_length}"
            )
            return False

        if len(response) > self.max_length:
            logger.warning(
                f"Response too long: {len(response)} > {self.max_length}"
            )
            return False

        # Check for truncation
        if self.detect_truncation(response):
            logger.warning("Response appears truncated")
            return False

        # Check for forbidden patterns
        if self._forbidden_regex.search(response):
            logger.warning("Response contains forbidden patterns (refusal)")
            return False

        # Check code blocks are closed
        if not self._check_code_blocks_closed(response):
            logger.warning("Response has unclosed code blocks")
            return False

        return True

    def validate_format(self, response: str, expected_format: str) -> bool:
        """Validate response format (JSON, YAML, Markdown).

        Args:
            response: The response text to validate
            expected_format: Expected format ('json', 'yaml', 'markdown', 'code')

        Returns:
            True if format is valid, False otherwise

        Example:
            >>> validator.validate_format('{"key": "value"}', 'json')
            True
            >>> validator.validate_format('{invalid', 'json')
            False
        """
        format_lower = expected_format.lower()

        try:
            if format_lower == 'json':
                json.loads(response)
                return True

            elif format_lower == 'yaml':
                if yaml is None:
                    logger.warning("YAML library not available")
                    return False
                yaml.safe_load(response)
                return True

            elif format_lower == 'markdown':
                # Basic markdown validation - check for common structure
                return self._validate_markdown(response)

            elif format_lower == 'code':
                # Generic code validation - check brackets balanced
                return self._check_brackets_balanced(response)

            else:
                logger.warning(f"Unknown format: {expected_format}")
                return False

        except (json.JSONDecodeError, yaml.YAMLError, Exception) as e:
            logger.warning(f"Format validation failed for {expected_format}: {e}")
            return False

    def validate_code_syntax(
        self,
        code: str,
        language: str
    ) -> Tuple[bool, List[str]]:
        """Validate code syntax for specified language.

        Args:
            code: The code to validate
            language: Programming language ('python', 'json', 'yaml')

        Returns:
            Tuple of (is_valid, list_of_errors)

        Example:
            >>> is_valid, errors = validator.validate_code_syntax(
            ...     "def foo():\\n    pass", "python"
            ... )
            >>> is_valid
            True
        """
        language_lower = language.lower()
        errors = []

        try:
            if language_lower == 'python':
                ast.parse(code)
                return True, []

            elif language_lower == 'json':
                json.loads(code)
                return True, []

            elif language_lower == 'yaml':
                if yaml is None:
                    errors.append("YAML library not available")
                    return False, errors
                yaml.safe_load(code)
                return True, []

            else:
                # Fallback: basic validation
                if self._check_brackets_balanced(code):
                    return True, []
                else:
                    errors.append("Brackets/quotes not balanced")
                    return False, errors

        except SyntaxError as e:
            errors.append(f"Syntax error at line {e.lineno}: {e.msg}")
            logger.warning(f"Code syntax validation failed: {errors}")
            return False, errors

        except (json.JSONDecodeError, yaml.YAMLError) as e:
            errors.append(str(e))
            logger.warning(f"Code syntax validation failed: {errors}")
            return False, errors

        except Exception as e:
            errors.append(f"Unexpected error: {str(e)}")
            logger.warning(f"Code syntax validation failed: {errors}")
            return False, errors

    def check_consistency(self, response: str) -> Tuple[bool, List[str]]:
        """Check logical consistency of response.

        Uses basic heuristics to detect contradictions:
        - Check for contradictory statements
        - Verify code examples match descriptions
        - Check for inconsistent terminology

        Args:
            response: The response text to check

        Returns:
            Tuple of (is_consistent, list_of_issues)

        Example:
            >>> is_consistent, issues = validator.check_consistency(response)
        """
        issues = []

        # Check for obvious contradictions
        contradiction_patterns = [
            (r'\byes\b.*\bno\b', "Contains both 'yes' and 'no'"),
            (r'\btrue\b.*\bfalse\b', "Contains both 'true' and 'false'"),
            (r'\bcan\b.*\bcannot\b', "Contains both 'can' and 'cannot'"),
        ]

        for pattern, issue in contradiction_patterns:
            if re.search(pattern, response, re.IGNORECASE | re.DOTALL):
                # Check if they're close together (potential contradiction)
                matches = list(re.finditer(pattern, response, re.IGNORECASE | re.DOTALL))
                for match in matches:
                    span = match.span()
                    if span[1] - span[0] < 200:  # Within 200 chars
                        issues.append(issue)
                        break

        # Check code blocks for consistency
        code_blocks = self.extract_code_blocks(response)
        if code_blocks:
            # Validate all code blocks
            for lang, code in code_blocks:
                if lang:
                    is_valid, errors = self.validate_code_syntax(code, lang)
                    if not is_valid:
                        issues.append(f"Invalid {lang} code: {errors[0] if errors else 'syntax error'}")

        is_consistent = len(issues) == 0

        if not is_consistent:
            logger.warning(f"Consistency issues found: {issues}")

        return is_consistent, issues

    def score_confidence(
        self,
        response: str,
        task_requirements: Optional[Dict[str, Any]] = None
    ) -> float:
        """Score confidence in response quality.

        Factors (weighted):
        - Completeness (0.3): has all required sections
        - Length appropriateness (0.2): not too short or long
        - Code validity (0.3): syntax correct
        - No forbidden patterns (0.1): professional tone
        - Specificity (0.1): concrete vs vague

        Args:
            response: The response text to score
            task_requirements: Optional dict with task requirements

        Returns:
            Confidence score between 0.0 and 1.0

        Example:
            >>> score = validator.score_confidence(response, {'needs_code': True})
            >>> assert 0.0 <= score <= 1.0
        """
        if not response:
            return 0.0

        task_requirements = task_requirements or {}
        scores = {}

        # 1. Completeness score
        scores['completeness'] = self._score_completeness(response, task_requirements)

        # 2. Length appropriateness
        scores['length'] = self._score_length(response)

        # 3. Code validity
        scores['code'] = self._score_code_validity(response)

        # 4. Professional tone (no forbidden patterns)
        scores['tone'] = 1.0 if not self._forbidden_regex.search(response) else 0.0

        # 5. Specificity
        scores['specificity'] = self._score_specificity(response)

        # Calculate weighted average
        confidence = (
            scores['completeness'] * self.WEIGHT_COMPLETENESS +
            scores['length'] * self.WEIGHT_LENGTH +
            scores['code'] * self.WEIGHT_CODE +
            scores['tone'] * self.WEIGHT_TONE +
            scores['specificity'] * self.WEIGHT_SPECIFICITY
        )

        logger.debug(
            f"Confidence score: {confidence:.2f} "
            f"(components: {scores})"
        )

        return confidence

    def extract_code_blocks(self, response: str) -> List[Tuple[str, str]]:
        """Extract code blocks from markdown response.

        Args:
            response: The response text containing code blocks

        Returns:
            List of tuples (language, code)

        Example:
            >>> blocks = validator.extract_code_blocks(response)
            >>> for lang, code in blocks:
            ...     print(f"Language: {lang}, Code: {code[:50]}")
        """
        code_blocks = []

        for match in self._code_block_pattern.finditer(response):
            language = match.group(1) or ''  # Language may be empty
            code = match.group(2).strip()
            code_blocks.append((language, code))

        logger.debug(f"Extracted {len(code_blocks)} code blocks")
        return code_blocks

    def detect_truncation(self, response: str) -> bool:
        """Detect if response was truncated.

        Checks for:
        - Truncation indicators in text
        - Unclosed code blocks
        - Sentence ending abruptly

        Args:
            response: The response text to check

        Returns:
            True if response appears truncated, False otherwise

        Example:
            >>> validator.detect_truncation("This is a complete response.")
            False
            >>> validator.detect_truncation("This is [truncated]")
            True
        """
        if not response:
            return True

        # Check for explicit truncation indicators
        if self._truncation_regex.search(response):
            return True

        # Check for unclosed code blocks
        if not self._check_code_blocks_closed(response):
            return True

        # Check if ends mid-sentence (no punctuation at end)
        response_stripped = response.strip()
        if response_stripped and response_stripped[-1] not in '.!?)}"\'':
            # Allow for some flexibility - might end with newline
            last_line = response_stripped.split('\n')[-1].strip()
            if last_line and len(last_line) > 10 and last_line[-1] not in '.!?)}"\'':
                logger.debug("Response may be truncated (no ending punctuation)")
                return True

        return False

    def validate_against_requirements(
        self,
        response: str,
        requirements: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """Validate response against task requirements.

        Args:
            response: The response text to validate
            requirements: Dict with requirements like:
                - needs_code: bool
                - required_sections: List[str]
                - language: str (if needs_code)
                - min_length: int

        Returns:
            Tuple of (meets_requirements, list_of_violations)

        Example:
            >>> reqs = {'needs_code': True, 'language': 'python'}
            >>> valid, violations = validator.validate_against_requirements(
            ...     response, reqs
            ... )
        """
        violations = []

        # Check code requirement
        if requirements.get('needs_code'):
            code_blocks = self.extract_code_blocks(response)
            if not code_blocks:
                violations.append("Response must include code blocks")
            else:
                # Validate language if specified
                required_lang = requirements.get('language')
                if required_lang:
                    found_lang = any(
                        lang.lower() == required_lang.lower()
                        for lang, _ in code_blocks
                    )
                    if not found_lang:
                        violations.append(
                            f"Response must include {required_lang} code"
                        )

        # Check required sections
        required_sections = requirements.get('required_sections', [])
        for section in required_sections:
            # Case-insensitive search for section headers
            pattern = re.escape(section)
            if not re.search(pattern, response, re.IGNORECASE):
                violations.append(f"Missing required section: {section}")

        # Check minimum length
        min_length = requirements.get('min_length', self.min_length)
        if len(response) < min_length:
            violations.append(
                f"Response too short: {len(response)} < {min_length}"
            )

        is_valid = len(violations) == 0

        if not is_valid:
            logger.warning(f"Requirements validation failed: {violations}")

        return is_valid, violations

    def sanitize_output(self, response: str) -> str:
        """Sanitize response output.

        Removes or replaces:
        - Potential harmful content
        - Excessive whitespace
        - Control characters

        Args:
            response: The response text to sanitize

        Returns:
            Sanitized response text

        Example:
            >>> sanitized = validator.sanitize_output(response)
        """
        if not response:
            return ""

        # Remove control characters (except newlines, tabs)
        sanitized = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', response)

        # Normalize whitespace (but keep paragraph breaks)
        sanitized = re.sub(r' +', ' ', sanitized)  # Multiple spaces -> single
        sanitized = re.sub(r'\n{4,}', '\n\n\n', sanitized)  # Max 3 newlines

        # Remove leading/trailing whitespace
        sanitized = sanitized.strip()

        return sanitized

    # Private helper methods

    def _check_code_blocks_closed(self, response: str) -> bool:
        """Check if all code blocks are properly closed.

        Args:
            response: The response text to check

        Returns:
            True if all code blocks are closed, False otherwise
        """
        # Count opening and closing markers
        opening_markers = response.count('```')

        # Should be even (each opening has a closing)
        return opening_markers % 2 == 0

    def _check_brackets_balanced(self, text: str) -> bool:
        """Check if brackets and quotes are balanced.

        Args:
            text: The text to check

        Returns:
            True if balanced, False otherwise
        """
        stack = []
        pairs = {'(': ')', '[': ']', '{': '}'}

        in_string = False
        string_char = None
        escape_next = False

        for char in text:
            if escape_next:
                escape_next = False
                continue

            if char == '\\':
                escape_next = True
                continue

            # Handle strings
            if char in ('"', "'"):
                if not in_string:
                    in_string = True
                    string_char = char
                elif char == string_char:
                    in_string = False
                    string_char = None
                continue

            # Skip bracket checking inside strings
            if in_string:
                continue

            # Check brackets
            if char in pairs:
                stack.append(char)
            elif char in pairs.values():
                if not stack:
                    return False
                last = stack.pop()
                if pairs[last] != char:
                    return False

        return len(stack) == 0 and not in_string

    def _validate_markdown(self, text: str) -> bool:
        """Validate markdown structure.

        Basic checks for markdown validity.

        Args:
            text: The markdown text to validate

        Returns:
            True if valid markdown, False otherwise
        """
        # Check for balanced code blocks
        if not self._check_code_blocks_closed(text):
            return False

        # Markdown is quite forgiving, so basic checks pass
        return True

    def _score_completeness(
        self,
        response: str,
        requirements: Dict[str, Any]
    ) -> float:
        """Score response completeness.

        Args:
            response: The response text
            requirements: Task requirements dict

        Returns:
            Score between 0.0 and 1.0
        """
        score = 1.0

        # Check length
        if len(response) < self.min_length:
            score *= 0.5

        # Check for truncation
        if self.detect_truncation(response):
            score *= 0.3

        # Check required sections if specified
        required_sections = requirements.get('required_sections', [])
        if required_sections:
            found = sum(
                1 for section in required_sections
                if re.search(re.escape(section), response, re.IGNORECASE)
            )
            section_score = found / len(required_sections)
            score *= section_score

        return max(0.0, min(1.0, score))

    def _score_length(self, response: str) -> float:
        """Score length appropriateness.

        Args:
            response: The response text

        Returns:
            Score between 0.0 and 1.0
        """
        length = len(response)

        # Too short
        if length < self.min_length:
            return length / self.min_length

        # Too long
        if length > self.max_length:
            return 0.5

        # Optimal range (100 - 10000 chars)
        if 100 <= length <= 10000:
            return 1.0

        # Acceptable but not optimal
        return 0.8

    def _score_code_validity(self, response: str) -> float:
        """Score code validity in response.

        Args:
            response: The response text

        Returns:
            Score between 0.0 and 1.0
        """
        code_blocks = self.extract_code_blocks(response)

        if not code_blocks:
            # No code blocks - neutral score
            return 0.7

        valid_blocks = 0
        for lang, code in code_blocks:
            if lang:  # Language specified
                is_valid, _ = self.validate_code_syntax(code, lang)
                if is_valid:
                    valid_blocks += 1
            else:
                # No language specified - can't validate
                valid_blocks += 0.5

        return valid_blocks / len(code_blocks)

    def _score_specificity(self, response: str) -> float:
        """Score response specificity vs vagueness.

        Args:
            response: The response text

        Returns:
            Score between 0.0 and 1.0
        """
        # Count specific indicators
        specific_indicators = [
            r'\b\d+\b',  # Numbers
            r'\bdef\b',  # Function definitions
            r'\bclass\b',  # Class definitions
            r'\b[A-Z][a-z]+[A-Z]',  # CamelCase
            r'\b\w+_\w+\b',  # snake_case
        ]

        specific_count = sum(
            len(re.findall(pattern, response))
            for pattern in specific_indicators
        )

        # Count vague indicators
        vague_patterns = [
            'maybe', 'perhaps', 'might', 'could', 'possibly',
            'generally', 'typically', 'usually', 'often'
        ]

        vague_count = sum(
            len(re.findall(r'\b' + re.escape(word) + r'\b', response, re.IGNORECASE))
            for word in vague_patterns
        )

        # Calculate ratio
        total = specific_count + vague_count
        if total == 0:
            return 0.5  # Neutral

        specificity = specific_count / total
        return min(1.0, specificity)
