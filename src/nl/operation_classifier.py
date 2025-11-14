"""Operation Classification for Natural Language Commands (ADR-016).

This module provides operation type classification to determine whether a command
is CREATE, UPDATE, DELETE, or QUERY. This is the first stage of the decomposed
NL entity extraction pipeline.

Classes:
    OperationClassifier: LLM-based operation classifier

Example:
    >>> from plugins.ollama import OllamaLLMPlugin
    >>> llm = OllamaLLMPlugin()
    >>> llm.initialize({'model': 'qwen2.5-coder:32b'})
    >>> classifier = OperationClassifier(llm, confidence_threshold=0.7)
    >>> result = classifier.classify("Create an epic for auth")
    >>> print(result.operation_type)
    OperationType.CREATE
    >>> print(result.confidence)
    0.95
"""

import json
import logging
import re
import time
from pathlib import Path
from typing import Optional
from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from plugins.base import LLMPlugin
from core.exceptions import OrchestratorException
from src.core.metrics import get_metrics_collector
from src.nl.base import OperationClassifierInterface
from src.nl.types import OperationType, OperationResult

logger = logging.getLogger(__name__)

# PHASE 3 FIX C: Define operation synonyms for better recognition
OPERATION_SYNONYMS = {
    OperationType.CREATE: [
        # Primary
        "create", "add", "make", "new",
        # Construction
        "build", "construct", "assemble", "craft",
        # Generation
        "generate", "produce", "develop",
        # Setup
        "establish", "initialize", "set up", "setup",
        # Preparation
        "prepare", "design", "form",
        # Initiation
        "start", "begin", "launch", "spin up",
        # Other
        "put together"
    ],
    OperationType.UPDATE: [
        # Primary
        "update", "modify", "change", "edit",
        # Adjustment
        "alter", "revise", "adjust", "refine",
        # Correction
        "amend", "correct", "fix",
        # Setting
        "set", "configure", "tweak"
    ],
    OperationType.DELETE: [
        # Primary
        "delete", "remove", "drop",
        # Destruction
        "erase", "clear", "purge", "eliminate",
        # Cancellation
        "destroy", "discard", "cancel", "archive"
    ],
    OperationType.QUERY: [
        # Primary
        "show", "list", "get", "find",
        # Search
        "search", "query", "lookup", "locate",
        # Display
        "display", "view", "see", "check",
        # Questions
        "what", "which", "where", "who",
        # Count
        "count", "how many", "number of",
        # Status
        "status", "state", "info", "details", "describe"
    ],
}


class OperationClassificationException(OrchestratorException):
    """Exception raised when operation classification fails."""
    pass


class OperationClassifier(OperationClassifierInterface):
    """LLM-based operation classifier for natural language commands.

    Uses a prompt template and LLM to classify user command into:
    - CREATE: Making something new (create, add, new, make)
    - UPDATE: Changing existing entity (update, modify, change, mark, set, edit)
    - DELETE: Removing something (delete, remove, cancel)
    - QUERY: Asking for information (show, list, display, get, find, what, how)

    The classifier is plugin-agnostic and works with any LLM that implements
    the LLMPlugin interface (Ollama, OpenAI, Claude, etc.).

    This is the second stage of the NL command pipeline (after IntentClassifier).
    It provides explicit operation type context to downstream components
    (EntityTypeClassifier, EntityIdentifierExtractor, ParameterExtractor).

    Args:
        llm_plugin: LLM provider implementing LLMPlugin interface
        confidence_threshold: Minimum confidence for classification (default 0.7)
        template_path: Path to Jinja2 template directory (default: prompts/)

    Example:
        >>> classifier = OperationClassifier(llm_plugin, confidence_threshold=0.7)
        >>> result = classifier.classify("Mark the manual tetris test as INACTIVE")
        >>> print(result.operation_type)  # OperationType.UPDATE
        >>> print(result.reasoning)  # "Status change operation on existing entity"
    """

    def __init__(
        self,
        llm_plugin: LLMPlugin,
        confidence_threshold: float = 0.7,
        template_path: Optional[Path] = None
    ):
        """Initialize operation classifier.

        Args:
            llm_plugin: LLM provider for classification
            confidence_threshold: Minimum confidence for classification (0.0 to 1.0)
            template_path: Path to prompt templates (default: prompts/)

        Raises:
            ValueError: If confidence_threshold not in [0.0, 1.0]
            OperationClassificationException: If template not found
        """
        super().__init__(llm_plugin, confidence_threshold)

        # Set up Jinja2 template environment
        if template_path is None:
            # Default to prompts/ directory relative to project root
            template_path = Path(__file__).parent.parent.parent / 'prompts'

        try:
            self.jinja_env = Environment(
                loader=FileSystemLoader(str(template_path)),
                trim_blocks=True,
                lstrip_blocks=True
            )
            # Verify template exists
            self.template = self.jinja_env.get_template('operation_classification.j2')
        except TemplateNotFound as e:
            raise OperationClassificationException(
                f"Operation classification template not found: {e}",
                context={'template_path': str(template_path)},
                recovery="Ensure prompts/operation_classification.j2 exists"
            )

        logger.info(
            f"OperationClassifier initialized with threshold={confidence_threshold}, "
            f"template_path={template_path}"
        )

    def classify(self, user_input: str) -> OperationResult:
        """Classify operation type from user input.

        Args:
            user_input: Raw user command string

        Returns:
            OperationResult with operation type and confidence

        Raises:
            ValueError: If user_input is empty
            OperationClassificationException: If LLM call fails or response unparseable
        """
        metrics = get_metrics_collector()
        start = time.time()

        if not user_input or not user_input.strip():
            raise ValueError("user_input cannot be empty")

        # Build prompt
        prompt = self._build_prompt(user_input)

        try:
            # Call LLM
            logger.debug(f"Calling LLM for operation classification: {user_input[:50]}...")
            response = self.llm.generate(
                prompt,
                max_tokens=100,  # Reduced from 200
                temperature=0.1,
                stop=["\n```", "}\n", "}\r\n"]
            )
            logger.debug(f"LLM response: {response[:200]}...")

            # Parse response
            operation_type = self._parse_response(response)
            confidence = self._calculate_confidence(response)

            # Extract reasoning from response
            reasoning = self._extract_reasoning(response)

            result = OperationResult(
                operation_type=operation_type,
                confidence=confidence,
                raw_response=response,
                reasoning=reasoning
            )

            logger.info(
                f"Classified operation: {operation_type.value} "
                f"(confidence={confidence:.2f})"
            )

            # Record metrics BEFORE return
            latency_ms = (time.time() - start) * 1000
            metrics.record_llm_request(
                provider='ollama',
                latency_ms=latency_ms,
                success=True,
                model=self.llm.model if hasattr(self.llm, 'model') else 'unknown'
            )

            return result

        except Exception as e:
            raise OperationClassificationException(
                f"Failed to classify operation: {e}",
                context={'user_input': user_input},
                recovery="Check LLM availability and prompt template"
            ) from e

    def _build_prompt(self, user_input: str) -> str:
        """Build prompt for LLM classification.

        PHASE 3 FIX C: Includes explicit synonym mappings in prompt to improve
        recognition of common operation variations (build, craft, show, etc.).

        Args:
            user_input: Raw user command

        Returns:
            Formatted prompt string
        """
        # Format synonyms for template
        synonym_strings = {
            'create_synonyms': ', '.join(OPERATION_SYNONYMS[OperationType.CREATE]),
            'update_synonyms': ', '.join(OPERATION_SYNONYMS[OperationType.UPDATE]),
            'delete_synonyms': ', '.join(OPERATION_SYNONYMS[OperationType.DELETE]),
            'query_synonyms': ', '.join(OPERATION_SYNONYMS[OperationType.QUERY]),
        }

        return self.template.render(
            user_command=user_input,
            **synonym_strings
        )

    def _parse_response(self, response: str) -> OperationType:
        """Parse LLM response into OperationType.

        Extracts operation type from JSON response or falls back to text parsing.

        Args:
            response: Raw LLM response string

        Returns:
            OperationType enum value

        Raises:
            OperationClassificationException: If response cannot be parsed
        """
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{[^}]+\}', response, re.DOTALL)
            if json_match:
                response_json = json.loads(json_match.group(0))
                operation_str = response_json.get('operation_type', '').upper()
            else:
                # Fallback: Look for operation type in text
                response_upper = response.upper()
                if 'CREATE' in response_upper:
                    operation_str = 'CREATE'
                elif 'UPDATE' in response_upper:
                    operation_str = 'UPDATE'
                elif 'DELETE' in response_upper:
                    operation_str = 'DELETE'
                elif 'QUERY' in response_upper:
                    operation_str = 'QUERY'
                else:
                    raise ValueError("No operation type found in response")

            # Map string to OperationType enum
            try:
                return OperationType(operation_str.lower())
            except ValueError:
                raise ValueError(f"Invalid operation type: {operation_str}")

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            raise OperationClassificationException(
                f"Failed to parse operation type from response: {e}",
                context={'response': response[:500]},
                recovery="Check LLM response format and prompt template"
            ) from e

    def _calculate_confidence(self, response: str) -> float:
        """Calculate confidence score from LLM response.

        Extracts confidence from JSON response or uses heuristics.

        Args:
            response: Raw LLM response string

        Returns:
            Confidence score from 0.0 to 1.0
        """
        try:
            # Try to extract confidence from JSON
            json_match = re.search(r'\{[^}]+\}', response, re.DOTALL)
            if json_match:
                response_json = json.loads(json_match.group(0))
                confidence = float(response_json.get('confidence', 0.8))
                return max(0.0, min(1.0, confidence))  # Clamp to [0.0, 1.0]
        except (json.JSONDecodeError, ValueError, KeyError):
            pass

        # Fallback: Use heuristic confidence calculation from base class
        return super()._calculate_confidence(response)

    def _extract_reasoning(self, response: str) -> str:
        """Extract reasoning explanation from LLM response.

        Args:
            response: Raw LLM response string

        Returns:
            Reasoning string (empty if not found)
        """
        try:
            json_match = re.search(r'\{[^}]+\}', response, re.DOTALL)
            if json_match:
                response_json = json.loads(json_match.group(0))
                return response_json.get('reasoning', '')
        except (json.JSONDecodeError, ValueError, KeyError):
            pass

        return ""


__all__ = [
    "OperationClassifier",
    "OperationClassificationException",
]
