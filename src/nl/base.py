"""Abstract base classes for NL command pipeline components (ADR-016).

This module defines interfaces for the five-stage NL command processing pipeline.
Each component has a single, well-defined responsibility and clear input/output contracts.

Pipeline Stages:
    1. IntentClassifier: COMMAND vs QUESTION (existing, unchanged)
    2. OperationClassifier: CREATE/UPDATE/DELETE/QUERY (new)
    3. EntityTypeClassifier: project/epic/story/task/milestone (new)
    4. EntityIdentifierExtractor: name or ID (new)
    5. ParameterExtractor: status, priority, dependencies (new)
    6. QuestionHandler: informational responses (new)

Design Principles:
    - Single Responsibility: Each component does one thing well
    - Explicit Context Passing: Operation type flows explicitly through pipeline
    - Progressive Refinement: Each stage narrows down classification
    - Fail-Fast Validation: Validate at each stage, not just at end

See docs/decisions/ADR-016-decompose-nl-entity-extraction.md for architecture.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from plugins.base import LLMPlugin
from src.nl.types import (
    OperationType,
    EntityType,
    QueryType,
    QuestionType,
    OperationResult,
    EntityTypeResult,
    IdentifierResult,
    ParameterResult,
    QuestionResponse,
)


class BaseClassifier(ABC):
    """Abstract base class for all LLM-based classifiers.

    All classifiers follow the same pattern:
        1. Accept LLM plugin in constructor
        2. Load prompt template
        3. Build prompt with context
        4. Call LLM
        5. Parse response
        6. Calculate confidence
        7. Return typed result

    This base class provides common functionality for LLM interaction
    and error handling.

    Args:
        llm_plugin: LLM provider implementing LLMPlugin interface
        confidence_threshold: Minimum confidence score for acceptance (default: 0.7)
    """

    def __init__(self, llm_plugin: LLMPlugin, confidence_threshold: float = 0.7):
        """Initialize classifier with LLM plugin.

        Args:
            llm_plugin: LLM provider implementing LLMPlugin interface
            confidence_threshold: Minimum confidence score (0.0 to 1.0)

        Raises:
            ValueError: If confidence_threshold not in range [0.0, 1.0]
        """
        if not 0.0 <= confidence_threshold <= 1.0:
            raise ValueError(
                f"confidence_threshold must be between 0.0 and 1.0, got {confidence_threshold}"
            )

        self.llm = llm_plugin
        self.confidence_threshold = confidence_threshold

    @abstractmethod
    def _build_prompt(self, *args, **kwargs) -> str:
        """Build prompt for LLM classification.

        Each classifier implements this to construct its specific prompt.

        Returns:
            Formatted prompt string
        """
        pass

    @abstractmethod
    def _parse_response(self, response: str) -> Any:
        """Parse LLM response into structured result.

        Each classifier implements this to extract its specific output type.

        Args:
            response: Raw LLM response string

        Returns:
            Parsed result (type varies by classifier)
        """
        pass

    def _calculate_confidence(self, response: str) -> float:
        """Calculate confidence score from LLM response.

        Default implementation uses simple heuristics:
            - Length of response (longer = more confident)
            - Presence of uncertainty markers ("maybe", "possibly", "not sure")

        Subclasses can override for more sophisticated confidence calculation.

        Args:
            response: Raw LLM response string

        Returns:
            Confidence score from 0.0 to 1.0
        """
        confidence = 0.8  # Default baseline

        # Check for uncertainty markers
        uncertainty_markers = ["maybe", "possibly", "not sure", "unclear", "uncertain"]
        for marker in uncertainty_markers:
            if marker.lower() in response.lower():
                confidence -= 0.2
                break

        # Check for explicit confidence indicators
        if "confident" in response.lower() or "certain" in response.lower():
            confidence += 0.1

        # Clamp to [0.0, 1.0]
        return max(0.0, min(1.0, confidence))


class OperationClassifierInterface(BaseClassifier):
    """Abstract interface for operation classification.

    Responsibility: Classify user command into CREATE/UPDATE/DELETE/QUERY

    Example:
        "Create epic for auth" → CREATE
        "Mark project as inactive" → UPDATE
        "Delete task 5" → DELETE
        "Show me all projects" → QUERY
    """

    @abstractmethod
    def classify(self, user_input: str) -> OperationResult:
        """Classify operation type from user input.

        Args:
            user_input: Raw user command string

        Returns:
            OperationResult with operation type and confidence

        Raises:
            ValueError: If user_input is empty
            OrchestratorException: If LLM call fails or response unparseable
        """
        pass


class EntityTypeClassifierInterface(BaseClassifier):
    """Abstract interface for entity type classification.

    Responsibility: Classify entity type given operation context

    The operation type provides critical context. For example:
        "Mark the manual tetris test as INACTIVE" + UPDATE → PROJECT
        (Not TASK, because "mark as inactive" suggests updating project status)

    Example:
        user_input="Create epic for auth", operation=CREATE → EPIC
        user_input="Show tasks for project 1", operation=QUERY → TASK
    """

    @abstractmethod
    def classify(self, user_input: str, operation: OperationType) -> EntityTypeResult:
        """Classify entity type given operation context.

        Args:
            user_input: Raw user command string
            operation: Operation type from OperationClassifier

        Returns:
            EntityTypeResult with entity type and confidence

        Raises:
            ValueError: If user_input is empty
            OrchestratorException: If LLM call fails or response unparseable
        """
        pass


class EntityIdentifierExtractorInterface(BaseClassifier):
    """Abstract interface for entity identifier extraction.

    Responsibility: Extract entity identifier (name or ID) from command

    Identifiers can be:
        - Names (string): "manual tetris test", "user authentication"
        - IDs (integer): 1, 5, 42, "project 3", "epic #7"

    The entity type and operation provide context for extraction.

    Example:
        user_input="Mark the manual tetris test as INACTIVE",
        entity_type=PROJECT, operation=UPDATE → "manual tetris test"

        user_input="Show tasks for project 1",
        entity_type=TASK, operation=QUERY → 1
    """

    @abstractmethod
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
            OrchestratorException: If LLM call fails or no identifier found
        """
        pass


class ParameterExtractorInterface(BaseClassifier):
    """Abstract interface for parameter extraction.

    Responsibility: Extract operation-specific parameters (status, priority, dependencies, etc.)

    Parameters vary by operation type:
        - UPDATE: status, priority, description, etc.
        - CREATE: priority, dependencies, epic_id, story_id, etc.
        - QUERY: limit, order, filters, etc.
        - DELETE: (typically no parameters)

    Example:
        user_input="Mark project as INACTIVE",
        operation=UPDATE, entity_type=PROJECT
        → {"status": "INACTIVE"}

        user_input="Create task with priority HIGH depends on task 3",
        operation=CREATE, entity_type=TASK
        → {"priority": "HIGH", "dependencies": [3]}
    """

    @abstractmethod
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
            OrchestratorException: If LLM call fails or response unparseable
        """
        pass

    @abstractmethod
    def _get_expected_params(
        self,
        operation: OperationType,
        entity_type: EntityType
    ) -> Dict[str, str]:
        """Get expected parameters for operation + entity type combination.

        Returns dictionary mapping parameter names to descriptions.

        Example:
            operation=UPDATE, entity_type=PROJECT
            → {"status": "Project status (ACTIVE, INACTIVE, COMPLETED, PAUSED)"}

            operation=CREATE, entity_type=TASK
            → {
                "priority": "Task priority (HIGH, MEDIUM, LOW)",
                "dependencies": "List of task IDs this task depends on",
                "description": "Detailed task description"
            }

        Args:
            operation: Operation type
            entity_type: Entity type

        Returns:
            Dictionary of expected parameters with descriptions
        """
        pass


class QuestionHandlerInterface(ABC):
    """Abstract interface for question handling.

    Responsibility: Handle informational questions gracefully

    Question types:
        - NEXT_STEPS: "What's next?", "Next tasks for project 1?"
        - STATUS: "What's the status?", "How's progress?"
        - BLOCKERS: "What's blocking?", "Any issues?"
        - PROGRESS: "Show progress", "How far along?", "Completion %?"
        - GENERAL: Catch-all for other questions

    Approach:
        1. Classify question type using LLM
        2. Extract entities from question (project name, etc.)
        3. Query StateManager for relevant data
        4. Format helpful response

    Example:
        "What's next for the tetris game development"
        → Query pending tasks for tetris project
        → Format actionable list: "Next steps for Tetris Game: 1. Implement scoring (PENDING), 2. Add sound effects (PENDING)"
    """

    def __init__(self, state_manager, llm_plugin: LLMPlugin):
        """Initialize question handler with StateManager and LLM.

        Args:
            state_manager: StateManager instance for querying data
            llm_plugin: LLM provider for question classification
        """
        self.state = state_manager
        self.llm = llm_plugin

    @abstractmethod
    def handle(self, user_input: str) -> QuestionResponse:
        """Handle a user question and return informational response.

        Args:
            user_input: User's question string

        Returns:
            QuestionResponse with formatted answer

        Raises:
            ValueError: If user_input is empty
            OrchestratorException: If question handling fails
        """
        pass

    @abstractmethod
    def _classify_question_type(self, question: str) -> QuestionType:
        """Classify question into NEXT_STEPS/STATUS/BLOCKERS/PROGRESS/GENERAL.

        Args:
            question: User's question string

        Returns:
            QuestionType enum value
        """
        pass

    @abstractmethod
    def _extract_question_entities(self, question: str) -> Dict[str, Any]:
        """Extract entities from question (project name, task ID, etc.).

        Args:
            question: User's question string

        Returns:
            Dictionary of extracted entities (e.g., {"project_id": 1, "epic_id": 3})
        """
        pass

    @abstractmethod
    def _query_relevant_data(
        self,
        question_type: QuestionType,
        entities: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Query StateManager for data relevant to question type.

        Args:
            question_type: Type of question being asked
            entities: Entities extracted from question

        Returns:
            Dictionary of relevant data (e.g., {"tasks": [...], "project": {...}})
        """
        pass

    @abstractmethod
    def _format_response(
        self,
        question_type: QuestionType,
        data: Dict[str, Any]
    ) -> str:
        """Format informational response based on question type and data.

        Args:
            question_type: Type of question being asked
            data: Data from StateManager

        Returns:
            Formatted response string
        """
        pass


__all__ = [
    # Base classes
    "BaseClassifier",

    # Interfaces
    "OperationClassifierInterface",
    "EntityTypeClassifierInterface",
    "EntityIdentifierExtractorInterface",
    "ParameterExtractorInterface",
    "QuestionHandlerInterface",
]
