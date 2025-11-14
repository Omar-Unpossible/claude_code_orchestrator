"""Parameter Extraction for Natural Language Commands (ADR-016).

This module provides parameter extraction to extract operation-specific parameters
(status, priority, dependencies, etc.) from user commands. This is the fifth stage
of the decomposed NL entity extraction pipeline.

Classes:
    ParameterExtractor: LLM-based parameter extractor with operation/entity context

Example:
    >>> from plugins.ollama import OllamaLLMPlugin
    >>> llm = OllamaLLMPlugin()
    >>> llm.initialize({'model': 'qwen2.5-coder:32b'})
    >>> extractor = ParameterExtractor(llm, confidence_threshold=0.7)
    >>> result = extractor.extract(
    ...     "Mark project as INACTIVE",
    ...     operation=OperationType.UPDATE,
    ...     entity_type=EntityType.PROJECT
    ... )
    >>> print(result.parameters)
    {'status': 'INACTIVE'}
    >>> print(result.confidence)
    0.95
"""

import json
import logging
import re
import time
from pathlib import Path
from typing import Dict, Any, Optional
from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from plugins.base import LLMPlugin
from core.exceptions import OrchestratorException
from src.core.metrics import get_metrics_collector
from src.nl.base import ParameterExtractorInterface
from src.nl.types import OperationType, EntityType, ParameterResult

logger = logging.getLogger(__name__)


class ParameterExtractionException(OrchestratorException):
    """Exception raised when parameter extraction fails."""
    pass


class ParameterExtractor(ParameterExtractorInterface):
    """LLM-based parameter extractor with operation and entity context.

    Extracts operation-specific parameters from natural language commands:
    - UPDATE: status, priority, description
    - CREATE: priority, dependencies, epic_id, story_id
    - QUERY: limit, order, filter, query_type
    - DELETE: cascade, force (rarely used)

    The operation type and entity type determine expected parameters:
        "Mark project as INACTIVE"
        + UPDATE + PROJECT → {status: "INACTIVE"}

        "Create task with priority HIGH depends on task 3"
        + CREATE + TASK → {priority: "HIGH", dependencies: [3]}

    This is the fifth stage of the NL command pipeline (after EntityIdentifierExtractor).
    It provides the final piece of context before validation and execution.

    Args:
        llm_plugin: LLM provider implementing LLMPlugin interface
        confidence_threshold: Minimum confidence for extraction (default 0.7)
        template_path: Path to Jinja2 template directory (default: prompts/)

    Example:
        >>> extractor = ParameterExtractor(llm_plugin, confidence_threshold=0.7)
        >>> result = extractor.extract(
        ...     "Show top 5 tasks",
        ...     operation=OperationType.QUERY,
        ...     entity_type=EntityType.TASK
        ... )
        >>> print(result.parameters)  # {limit: 5, order: "priority"}
    """

    def __init__(
        self,
        llm_plugin: LLMPlugin,
        confidence_threshold: float = 0.7,
        template_path: Optional[Path] = None
    ):
        """Initialize parameter extractor.

        Args:
            llm_plugin: LLM provider for extraction
            confidence_threshold: Minimum confidence for extraction (0.0 to 1.0)
            template_path: Path to prompt templates (default: prompts/)

        Raises:
            ValueError: If confidence_threshold not in [0.0, 1.0]
            ParameterExtractionException: If template not found
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
            self.template = self.jinja_env.get_template('parameter_extraction.j2')
        except TemplateNotFound as e:
            raise ParameterExtractionException(
                f"Parameter extraction template not found: {e}",
                context={'template_path': str(template_path)},
                recovery="Ensure prompts/parameter_extraction.j2 exists"
            )

        logger.info(
            f"ParameterExtractor initialized with threshold={confidence_threshold}, "
            f"template_path={template_path}"
        )

    def extract(
        self,
        user_input: str,
        operation: OperationType,
        entity_type: EntityType
    ) -> ParameterResult:
        """Extract operation-specific parameters from command.

        Args:
            user_input: Raw user command string
            operation: Operation type from OperationClassifier
            entity_type: Entity type from EntityTypeClassifier

        Returns:
            ParameterResult with parameters dict and confidence

        Raises:
            ValueError: If user_input is empty
            ParameterExtractionException: If LLM call fails or response unparseable
        """
        metrics = get_metrics_collector()
        start = time.time()

        if not user_input or not user_input.strip():
            raise ValueError("user_input cannot be empty")

        # Detect bulk operation keywords
        bulk_keywords = ['all', 'every', 'each', 'entire']
        detected_bulk = any(keyword in user_input.lower() for keyword in bulk_keywords)

        # Detect scope keywords
        scope = None
        if 'this project' in user_input.lower() or 'current project' in user_input.lower():
            scope = 'current_project'
        elif 'all projects' in user_input.lower():
            scope = 'all_projects'

        # Build prompt with full context
        prompt = self._build_prompt(user_input, operation, entity_type)

        try:
            # Call LLM
            logger.debug(
                f"Calling LLM for parameter extraction: {user_input[:50]}... "
                f"(operation={operation.value}, entity={entity_type.value})"
            )
            response = self.llm.generate(
                prompt,
                max_tokens=150,  # Reduced from 300 (parameters may be longer)
                temperature=0.1,
                stop=["\n```", "}\n", "}\r\n"]
            )
            logger.debug(f"LLM response: {response[:200]}...")

            # Parse response
            parameters = self._parse_response(response)
            confidence = self._calculate_confidence(response)

            # Add detected bulk and scope parameters
            if detected_bulk:
                parameters['bulk'] = True
                parameters['all'] = True

            if scope:
                parameters['scope'] = scope

            # Extract reasoning from response
            reasoning = self._extract_reasoning(response)

            result = ParameterResult(
                parameters=parameters,
                confidence=confidence,
                raw_response=response,
                reasoning=reasoning
            )

            logger.info(
                f"Extracted parameters: {parameters} "
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
            raise ParameterExtractionException(
                f"Failed to extract parameters: {e}",
                context={
                    'user_input': user_input,
                    'operation': operation.value,
                    'entity_type': entity_type.value
                },
                recovery="Check LLM availability and prompt template"
            ) from e

    def _build_prompt(
        self,
        user_input: str,
        operation: OperationType,
        entity_type: EntityType
    ) -> str:
        """Build prompt for LLM extraction with full context.

        Args:
            user_input: Raw user command
            operation: Operation type from OperationClassifier
            entity_type: Entity type from EntityTypeClassifier

        Returns:
            Formatted prompt string
        """
        # Get expected parameters description
        expected_params = self._get_expected_params(operation, entity_type)
        expected_params_desc = ", ".join([f"{k}: {v}" for k, v in expected_params.items()])

        return self.template.render(
            user_command=user_input,
            operation_type=operation.value.upper(),
            entity_type=entity_type.value.upper(),
            expected_parameters_description=expected_params_desc or "No specific parameters expected"
        )

    def _parse_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response into parameters dictionary.

        Extracts parameters from JSON response or returns empty dict.

        Args:
            response: Raw LLM response string

        Returns:
            Dictionary of parameters

        Raises:
            ParameterExtractionException: If response format is invalid
        """
        try:
            # Try to parse entire response as JSON first
            try:
                response_json = json.loads(response)
            except json.JSONDecodeError:
                # Try to extract JSON block from response (handle nested objects)
                # This regex handles nested braces better
                json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response, re.DOTALL)
                if json_match:
                    response_json = json.loads(json_match.group(0))
                else:
                    # No JSON found, return empty parameters
                    logger.info("No JSON parameters found in response, returning empty dict")
                    return {}

            if response_json:
                parameters = response_json.get('parameters', {})

                # Ensure parameters is a dictionary
                if not isinstance(parameters, dict):
                    logger.warning(f"Parameters is not a dict: {type(parameters)}, using empty dict")
                    return {}

                return parameters
            else:
                return {}

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            # Don't raise exception, just return empty dict and log
            logger.warning(f"Failed to parse parameters: {e}, returning empty dict")
            return {}

    def _get_expected_params(
        self,
        operation: OperationType,
        entity_type: EntityType
    ) -> Dict[str, str]:
        """Get expected parameters for operation + entity type combination.

        Returns dictionary mapping parameter names to descriptions.

        Args:
            operation: Operation type
            entity_type: Entity type

        Returns:
            Dictionary of expected parameters with descriptions
        """
        params = {}

        if operation == OperationType.UPDATE:
            # UPDATE operations: status, priority, description
            params["status"] = "Entity status (ACTIVE, INACTIVE, COMPLETED, PAUSED, BLOCKED)"
            params["priority"] = "Priority level (HIGH, MEDIUM, LOW)"
            params["description"] = "Updated description text"
            params["title"] = "Updated title/name"

        elif operation == OperationType.CREATE:
            # CREATE operations: priority, dependencies, parent IDs
            params["priority"] = "Priority level (HIGH, MEDIUM, LOW)"
            params["dependencies"] = "List of task/story IDs this depends on"

            if entity_type in [EntityType.STORY, EntityType.TASK]:
                params["epic_id"] = "Parent epic ID"

            if entity_type == EntityType.TASK:
                params["story_id"] = "Parent story ID"

            params["description"] = "Detailed description"
            params["title"] = "Entity title/name"

        elif operation == OperationType.QUERY:
            # QUERY operations: limit, order, filter, query_type
            params["limit"] = "Number of results to return"
            params["order"] = "Sorting order (priority, date, status)"
            params["filter"] = "Filter criteria"
            params["query_type"] = "Type of query (hierarchical, next_steps, backlog, roadmap)"

        elif operation == OperationType.DELETE:
            # DELETE operations: rarely have parameters
            params["cascade"] = "Whether to delete child entities"
            params["force"] = "Skip confirmation"

        return params

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
    "ParameterExtractor",
    "ParameterExtractionException",
]
