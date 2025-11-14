"""Entity Type Classification for Natural Language Commands (ADR-016).

This module provides entity type classification to determine whether a command
refers to a PROJECT, EPIC, STORY, TASK, SUBTASK, or MILESTONE. This is the third
stage of the decomposed NL entity extraction pipeline, using operation context
from the previous stage.

Classes:
    EntityTypeClassifier: LLM-based entity type classifier with operation context

Example:
    >>> from plugins.ollama import OllamaLLMPlugin
    >>> llm = OllamaLLMPlugin()
    >>> llm.initialize({'model': 'qwen2.5-coder:32b'})
    >>> classifier = EntityTypeClassifier(llm, confidence_threshold=0.7)
    >>> result = classifier.classify(
    ...     "Mark the manual tetris test as INACTIVE",
    ...     operation=OperationType.UPDATE
    ... )
    >>> print(result.entity_type)
    EntityType.PROJECT
    >>> print(result.confidence)
    0.92
"""

import json
import logging
import re
import time
from pathlib import Path
from typing import Optional
from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from typing import List
from plugins.base import LLMPlugin
from core.exceptions import OrchestratorException
from src.core.metrics import get_metrics_collector
from src.nl.base import EntityTypeClassifierInterface
from src.nl.types import OperationType, EntityType, EntityTypeResult

logger = logging.getLogger(__name__)

# Keywords for detecting multiple entity types
ENTITY_KEYWORDS = {
    'epic': EntityType.EPIC,
    'epics': EntityType.EPIC,
    'story': EntityType.STORY,
    'stories': EntityType.STORY,
    'task': EntityType.TASK,
    'tasks': EntityType.TASK,
    'subtask': EntityType.SUBTASK,
    'subtasks': EntityType.SUBTASK,
    'milestone': EntityType.MILESTONE,
    'milestones': EntityType.MILESTONE,
    'project': EntityType.PROJECT,
    'projects': EntityType.PROJECT
}


class EntityTypeClassificationException(OrchestratorException):
    """Exception raised when entity type classification fails."""
    pass


class EntityTypeClassifier(EntityTypeClassifierInterface):
    """LLM-based entity type classifier with operation context.

    Uses a prompt template and LLM to classify entity type as:
    - PROJECT: Top-level project/product
    - EPIC: Large feature (3-15 sessions)
    - STORY: User deliverable (1 session)
    - TASK: Technical work (default, atomic unit)
    - SUBTASK: Sub-component of a task
    - MILESTONE: Checkpoint/release marker

    The operation type provides critical context. For example:
        "Mark the manual tetris test as INACTIVE" + UPDATE → PROJECT
        (Not TASK, because "mark as inactive" suggests updating project status)

    This is the third stage of the NL command pipeline (after OperationClassifier).
    It provides entity type context to downstream components
    (EntityIdentifierExtractor, ParameterExtractor).

    Args:
        llm_plugin: LLM provider implementing LLMPlugin interface
        confidence_threshold: Minimum confidence for classification (default 0.7)
        template_path: Path to Jinja2 template directory (default: prompts/)

    Example:
        >>> classifier = EntityTypeClassifier(llm_plugin, confidence_threshold=0.7)
        >>> result = classifier.classify(
        ...     "Create epic for auth",
        ...     operation=OperationType.CREATE
        ... )
        >>> print(result.entity_type)  # EntityType.EPIC
        >>> print(result.reasoning)  # "Explicit 'epic' entity type mentioned"
    """

    def __init__(
        self,
        llm_plugin: LLMPlugin,
        confidence_threshold: float = 0.7,
        template_path: Optional[Path] = None
    ):
        """Initialize entity type classifier.

        Args:
            llm_plugin: LLM provider for classification
            confidence_threshold: Minimum confidence for classification (0.0 to 1.0)
            template_path: Path to prompt templates (default: prompts/)

        Raises:
            ValueError: If confidence_threshold not in [0.0, 1.0]
            EntityTypeClassificationException: If template not found
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
            self.template = self.jinja_env.get_template('entity_type_classification.j2')
        except TemplateNotFound as e:
            raise EntityTypeClassificationException(
                f"Entity type classification template not found: {e}",
                context={'template_path': str(template_path)},
                recovery="Ensure prompts/entity_type_classification.j2 exists"
            )

        logger.info(
            f"EntityTypeClassifier initialized with threshold={confidence_threshold}, "
            f"template_path={template_path}"
        )

    def _detect_multiple_entity_types(self, user_input: str) -> List[EntityType]:
        """Detect multiple entity types mentioned in input.

        Args:
            user_input: Raw user command

        Returns:
            List of entity types detected (may be empty)
        """
        tokens = user_input.lower().split()
        detected = []

        for keyword, entity_type in ENTITY_KEYWORDS.items():
            if keyword in tokens:
                if entity_type not in detected:
                    detected.append(entity_type)

        return detected

    def classify(self, user_input: str, operation: OperationType) -> tuple:
        """Classify entity type(s) from user input.

        Args:
            user_input: Raw user command string
            operation: Operation type from OperationClassifier

        Returns:
            (entity_types: List[EntityType], confidence: float)

        Raises:
            ValueError: If user_input is empty
            EntityTypeClassificationException: If LLM call fails or response unparseable
        """
        metrics = get_metrics_collector()
        start = time.time()

        if not user_input or not user_input.strip():
            raise ValueError("user_input cannot be empty")

        # First try multi-entity detection
        detected_types = self._detect_multiple_entity_types(user_input)

        if len(detected_types) > 1:
            logger.info(f"Detected multiple entity types: {detected_types}")
            # High confidence for explicit mentions
            latency_ms = (time.time() - start) * 1000
            metrics.record_llm_request(
                provider='keyword_match',
                latency_ms=latency_ms,
                success=True,
                model='rule_based'
            )
            return (detected_types, 0.85)

        elif len(detected_types) == 1:
            logger.info(f"Detected single entity type: {detected_types[0]}")
            # High confidence for explicit mention
            latency_ms = (time.time() - start) * 1000
            metrics.record_llm_request(
                provider='keyword_match',
                latency_ms=latency_ms,
                success=True,
                model='rule_based'
            )
            return ([detected_types[0]], 0.90)

        else:
            # Fallback to LLM classification for single entity
            return self._llm_classify_single(user_input, operation)

    def _llm_classify_single(self, user_input: str, operation: OperationType) -> tuple:
        """Classify single entity type using LLM.

        Args:
            user_input: Raw user command
            operation: Operation type

        Returns:
            (entity_types: List[EntityType], confidence: float)

        Raises:
            EntityTypeClassificationException: If LLM call fails
        """
        metrics = get_metrics_collector()
        start = time.time()

        # Build prompt with operation context
        prompt = self._build_prompt(user_input, operation)

        try:
            # Call LLM
            logger.debug(
                f"Calling LLM for entity type classification: {user_input[:50]}... "
                f"(operation={operation.value})"
            )
            response = self.llm.generate(
                prompt,
                max_tokens=100,
                temperature=0.1,
                stop=["\n```", "}\n", "}\r\n"]
            )
            logger.debug(f"LLM response: {response[:200]}...")

            # Parse response
            entity_type = self._parse_response(response)
            confidence = self._calculate_confidence(response)

            logger.info(
                f"Classified entity type: {entity_type.value} "
                f"(confidence={confidence:.2f}, operation={operation.value})"
            )

            # Record metrics
            latency_ms = (time.time() - start) * 1000
            metrics.record_llm_request(
                provider='ollama',
                latency_ms=latency_ms,
                success=True,
                model=self.llm.model if hasattr(self.llm, 'model') else 'unknown'
            )

            return ([entity_type], confidence)

        except Exception as e:
            raise EntityTypeClassificationException(
                f"Failed to classify entity type: {e}",
                context={'user_input': user_input, 'operation': operation.value},
                recovery="Check LLM availability and prompt template"
            ) from e

    def _build_prompt(self, user_input: str, operation: OperationType) -> str:
        """Build prompt for LLM classification with operation context.

        Args:
            user_input: Raw user command
            operation: Operation type from OperationClassifier

        Returns:
            Formatted prompt string
        """
        return self.template.render(
            user_command=user_input,
            operation_type=operation.value.upper()
        )

    def _parse_response(self, response: str) -> EntityType:
        """Parse LLM response into EntityType.

        Extracts entity type from JSON response or falls back to text parsing.

        Args:
            response: Raw LLM response string

        Returns:
            EntityType enum value

        Raises:
            EntityTypeClassificationException: If response cannot be parsed
        """
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{[^}]+\}', response, re.DOTALL)
            if json_match:
                response_json = json.loads(json_match.group(0))
                entity_str = response_json.get('entity_type', '').upper()
            else:
                # Fallback: Look for entity type in text
                response_upper = response.upper()
                if 'MILESTONE' in response_upper:
                    entity_str = 'MILESTONE'
                elif 'SUBTASK' in response_upper:
                    entity_str = 'SUBTASK'
                elif 'PROJECT' in response_upper:
                    entity_str = 'PROJECT'
                elif 'EPIC' in response_upper:
                    entity_str = 'EPIC'
                elif 'STORY' in response_upper:
                    entity_str = 'STORY'
                elif 'TASK' in response_upper:
                    entity_str = 'TASK'
                else:
                    raise ValueError("No entity type found in response")

            # Map string to EntityType enum
            try:
                return EntityType(entity_str.lower())
            except ValueError:
                raise ValueError(f"Invalid entity type: {entity_str}")

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            raise EntityTypeClassificationException(
                f"Failed to parse entity type from response: {e}",
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
    "EntityTypeClassifier",
    "EntityTypeClassificationException",
]
