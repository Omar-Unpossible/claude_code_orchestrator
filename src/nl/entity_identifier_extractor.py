"""Entity Identifier Extraction for Natural Language Commands (ADR-016).

This module provides entity identifier extraction to extract entity names or IDs
from user commands. This is the fourth stage of the decomposed NL entity
extraction pipeline, using both operation and entity type context.

Classes:
    EntityIdentifierExtractor: LLM-based identifier extractor with context

Example:
    >>> from plugins.ollama import OllamaLLMPlugin
    >>> llm = OllamaLLMPlugin()
    >>> llm.initialize({'model': 'qwen2.5-coder:32b'})
    >>> extractor = EntityIdentifierExtractor(llm, confidence_threshold=0.7)
    >>> result = extractor.extract(
    ...     "Mark the manual tetris test as INACTIVE",
    ...     entity_type=EntityType.PROJECT,
    ...     operation=OperationType.UPDATE
    ... )
    >>> print(result.identifier)
    "manual tetris test"
    >>> print(result.confidence)
    0.95
"""

import json
import logging
import re
import time
from pathlib import Path
from typing import Optional, Union
from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from plugins.base import LLMPlugin
from core.exceptions import OrchestratorException
from src.core.metrics import get_metrics_collector
from src.nl.base import EntityIdentifierExtractorInterface
from src.nl.types import OperationType, EntityType, IdentifierResult

logger = logging.getLogger(__name__)

# Bulk operation constants
BULK_KEYWORDS = ['all', 'every', 'each', 'entire']
BULK_SENTINEL = "__ALL__"


class EntityIdentifierExtractionException(OrchestratorException):
    """Exception raised when entity identifier extraction fails."""
    pass


class EntityIdentifierExtractor(EntityIdentifierExtractorInterface):
    """LLM-based entity identifier extractor with operation and entity context.

    Extracts entity identifiers (names or IDs) from natural language commands:
    - Names (string): "manual tetris test", "User Authentication System"
    - IDs (integer): 1, 5, 42, "project 1", "epic #3"

    The operation type and entity type provide critical context:
        "Mark the manual tetris test as INACTIVE"
        + UPDATE + PROJECT → "manual tetris test"

        "Delete task 5"
        + DELETE + TASK → 5

    This is the fourth stage of the NL command pipeline (after EntityTypeClassifier).
    It provides the specific entity identifier to downstream components
    (ParameterExtractor, CommandValidator, CommandExecutor).

    Args:
        llm_plugin: LLM provider implementing LLMPlugin interface
        confidence_threshold: Minimum confidence for extraction (default 0.7)
        template_path: Path to Jinja2 template directory (default: prompts/)

    Example:
        >>> extractor = EntityIdentifierExtractor(llm_plugin, confidence_threshold=0.7)
        >>> result = extractor.extract(
        ...     "Show tasks for project 1",
        ...     entity_type=EntityType.TASK,
        ...     operation=OperationType.QUERY
        ... )
        >>> print(result.identifier)  # 1 (project ID from filter)
        >>> print(result.reasoning)  # "Project ID in query filter clause"
    """

    def __init__(
        self,
        llm_plugin: LLMPlugin,
        confidence_threshold: float = 0.7,
        template_path: Optional[Path] = None
    ):
        """Initialize entity identifier extractor.

        Args:
            llm_plugin: LLM provider for extraction
            confidence_threshold: Minimum confidence for extraction (0.0 to 1.0)
            template_path: Path to prompt templates (default: prompts/)

        Raises:
            ValueError: If confidence_threshold not in [0.0, 1.0]
            EntityIdentifierExtractionException: If template not found
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
            self.template = self.jinja_env.get_template('entity_identifier_extraction.j2')
        except TemplateNotFound as e:
            raise EntityIdentifierExtractionException(
                f"Entity identifier extraction template not found: {e}",
                context={'template_path': str(template_path)},
                recovery="Ensure prompts/entity_identifier_extraction.j2 exists"
            )

        logger.info(
            f"EntityIdentifierExtractor initialized with threshold={confidence_threshold}, "
            f"template_path={template_path}"
        )

    def _detect_bulk_operation(self, user_input: str) -> bool:
        """Detect if user wants bulk operation.

        Args:
            user_input: Raw user command string

        Returns:
            True if bulk operation detected, False otherwise
        """
        tokens = user_input.lower().split()
        return any(keyword in tokens for keyword in BULK_KEYWORDS)

    def extract(
        self,
        user_input: str,
        entity_type: EntityType,
        operation: OperationType
    ) -> IdentifierResult:
        """Extract entity identifier from command.

        Args:
            user_input: Raw user command string
            entity_type: Entity type from EntityTypeClassifier
            operation: Operation type from OperationClassifier

        Returns:
            IdentifierResult with identifier (str or int) and confidence

        Raises:
            ValueError: If user_input is empty
            EntityIdentifierExtractionException: If LLM call fails or no identifier found
        """
        metrics = get_metrics_collector()
        start = time.time()

        if not user_input or not user_input.strip():
            raise ValueError("user_input cannot be empty")

        # Check for bulk operation first
        if self._detect_bulk_operation(user_input):
            logger.info(f"Detected bulk operation with sentinel {BULK_SENTINEL}")
            result = IdentifierResult(
                identifier=BULK_SENTINEL,
                confidence=0.95,
                raw_response=f"Bulk operation detected (keywords: {BULK_KEYWORDS})",
                reasoning="Bulk operation keyword detected in user input"
            )

            # Record metrics
            latency_ms = (time.time() - start) * 1000
            metrics.record_llm_request(
                provider='rule-based',
                latency_ms=latency_ms,
                success=True,
                model='bulk-detection'
            )

            return result

        # Build prompt with full context
        prompt = self._build_prompt(user_input, entity_type, operation)

        try:
            # Call LLM
            logger.debug(
                f"Calling LLM for identifier extraction: {user_input[:50]}... "
                f"(entity={entity_type.value}, operation={operation.value})"
            )
            response = self.llm.generate(
                prompt,
                max_tokens=100,  # Reduced from 200
                temperature=0.1,
                stop=["\n```", "}\n", "}\r\n"]
            )
            logger.debug(f"LLM response: {response[:200]}...")

            # Parse response
            identifier = self._parse_response(response)
            confidence = self._calculate_confidence(response)

            # Extract reasoning from response
            reasoning = self._extract_reasoning(response)

            result = IdentifierResult(
                identifier=identifier,
                confidence=confidence,
                raw_response=response,
                reasoning=reasoning
            )

            logger.info(
                f"Extracted identifier: {identifier} (type={type(identifier).__name__}, "
                f"confidence={confidence:.2f})"
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
            raise EntityIdentifierExtractionException(
                f"Failed to extract identifier: {e}",
                context={
                    'user_input': user_input,
                    'entity_type': entity_type.value,
                    'operation': operation.value
                },
                recovery="Check LLM availability and prompt template"
            ) from e

    def _build_prompt(
        self,
        user_input: str,
        entity_type: EntityType,
        operation: OperationType
    ) -> str:
        """Build prompt for LLM extraction with full context.

        Args:
            user_input: Raw user command
            entity_type: Entity type from EntityTypeClassifier
            operation: Operation type from OperationClassifier

        Returns:
            Formatted prompt string
        """
        return self.template.render(
            user_command=user_input,
            entity_type=entity_type.value.upper(),
            operation_type=operation.value.upper()
        )

    def _parse_response(self, response: str) -> Union[str, int, None]:
        """Parse LLM response into identifier (string, integer, or None).

        Extracts identifier from JSON response or falls back to heuristic parsing.

        Args:
            response: Raw LLM response string

        Returns:
            Identifier as string, integer, or None (for "show all" queries)

        Raises:
            EntityIdentifierExtractionException: If identifier cannot be extracted
        """
        try:
            # Try to parse entire response as JSON first
            try:
                response_json = json.loads(response)
            except json.JSONDecodeError:
                # Try to extract JSON block from response
                json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response, re.DOTALL)
                if json_match:
                    response_json = json.loads(json_match.group(0))
                else:
                    response_json = None

            if response_json:
                # Check if identifier key exists
                if 'identifier' not in response_json:
                    raise ValueError("No identifier key in response JSON")

                identifier = response_json.get('identifier')
                identifier_type = response_json.get('identifier_type', 'name')

                # Handle null/none identifier (explicitly set to None by LLM)
                if identifier is None or identifier_type == 'none':
                    # For queries like "show all projects", no identifier is valid
                    return None

                # Convert to appropriate type
                if identifier_type == 'id':
                    # Try to convert to integer
                    if isinstance(identifier, int):
                        return identifier
                    elif isinstance(identifier, str):
                        # Extract number from string like "project 1" or "#3"
                        num_match = re.search(r'\d+', identifier)
                        if num_match:
                            return int(num_match.group(0))
                    return int(identifier)  # Last resort conversion
                else:
                    # Return as string name
                    return str(identifier).strip()
            else:
                # Fallback: Try to extract identifier from text
                # Look for patterns like "identifier: X" or quoted strings

                # Try quoted strings first
                quote_match = re.search(r'["\']([^"\']+)["\']', response)
                if quote_match:
                    return quote_match.group(1)

                # Try numeric IDs
                num_match = re.search(r'\b(\d+)\b', response)
                if num_match:
                    return int(num_match.group(1))

                # If no identifier found, this might be a "show all" query
                if 'null' in response.lower() or 'none' in response.lower():
                    return None

                raise ValueError("No identifier found in response")

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            raise EntityIdentifierExtractionException(
                f"Failed to parse identifier from response: {e}",
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
            # Try to parse entire response as JSON first
            try:
                response_json = json.loads(response)
            except json.JSONDecodeError:
                # Try to extract JSON block from response
                json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response, re.DOTALL)
                if json_match:
                    response_json = json.loads(json_match.group(0))
                else:
                    response_json = None

            if response_json:
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
    "EntityIdentifierExtractor",
    "EntityIdentifierExtractionException",
]
