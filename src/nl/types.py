"""Core data structures for Natural Language Command Pipeline (ADR-016).

This module defines enums and dataclasses used throughout the five-stage
NL command processing pipeline:
    1. IntentClassifier (COMMAND vs QUESTION)
    2. OperationClassifier (CREATE/UPDATE/DELETE/QUERY)
    3. EntityTypeClassifier (project/epic/story/task/milestone)
    4. EntityIdentifierExtractor (name or ID)
    5. ParameterExtractor (status, priority, dependencies, etc.)

These types enable single-responsibility components with explicit context passing
and progressive refinement through the pipeline.

See docs/decisions/ADR-016-decompose-nl-entity-extraction.md for architecture.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional, Union, List


class OperationType(Enum):
    """Type of operation being performed on an entity.

    Attributes:
        CREATE: Making something new (create, add, new, make)
        UPDATE: Changing existing entity (update, modify, change, mark, set, edit)
        DELETE: Removing something (delete, remove, cancel)
        QUERY: Asking for information (show, list, display, get, find, what, how)
    """
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    QUERY = "query"

    def __str__(self) -> str:
        return self.value


class QueryType(Enum):
    """Type of query being performed.

    Attributes:
        SIMPLE: Basic entity listing (show all projects, list tasks)
        HIERARCHICAL: Show task hierarchies (epics → stories → tasks)
        NEXT_STEPS: Show next pending tasks for a project
        BACKLOG: Show all pending tasks
        ROADMAP: Show milestones and associated epics
        WORKPLAN: Synonym for HIERARCHICAL (user-facing term)
    """
    SIMPLE = "simple"
    HIERARCHICAL = "hierarchical"
    NEXT_STEPS = "next_steps"
    BACKLOG = "backlog"
    ROADMAP = "roadmap"
    WORKPLAN = "workplan"  # Maps to HIERARCHICAL

    def __str__(self) -> str:
        return self.value


class EntityType(Enum):
    """Type of entity in Obra's work hierarchy.

    Attributes:
        PROJECT: Top-level project/product
        EPIC: Large feature requiring 3-15 orchestration sessions
        STORY: User deliverable requiring 1 orchestration session
        TASK: Technical work (default, atomic unit of work)
        SUBTASK: Sub-component of a task (via parent_task_id)
        MILESTONE: Checkpoint/release marker (zero-duration)
    """
    PROJECT = "project"
    EPIC = "epic"
    STORY = "story"
    TASK = "task"
    SUBTASK = "subtask"
    MILESTONE = "milestone"

    def __str__(self) -> str:
        return self.value


class QuestionType(Enum):
    """Type of informational question being asked.

    Attributes:
        NEXT_STEPS: What's next, Next tasks for project
        STATUS: What's the status, How's progress, Is it done
        BLOCKERS: What's blocking, Any issues, What's stuck
        PROGRESS: Show progress, How far along, Completion percentage
        GENERAL: Catch-all for other questions
    """
    NEXT_STEPS = "next_steps"
    STATUS = "status"
    BLOCKERS = "blockers"
    PROGRESS = "progress"
    GENERAL = "general"

    def __str__(self) -> str:
        return self.value


@dataclass
class OperationContext:
    """Context object holding all information about a command operation.

    This dataclass aggregates results from multiple pipeline stages:
        - OperationClassifier → operation
        - EntityTypeClassifier → entity_type
        - EntityIdentifierExtractor → identifier
        - ParameterExtractor → parameters

    It's passed to CommandValidator and CommandExecutor for validation and execution.

    Attributes:
        operation: Type of operation (CREATE/UPDATE/DELETE/QUERY)
        entity_types: List of entity types (project/epic/story/task/milestone)
        identifier: Entity identifier (name string or ID integer)
        parameters: Operation-specific parameters (status, priority, dependencies, etc.)
        query_type: Type of query (for QUERY operations only)
        confidence: Aggregate confidence score from all pipeline stages (0.0 to 1.0)
        raw_input: Original user input string

    Example:
        >>> context = OperationContext(
        ...     operation=OperationType.UPDATE,
        ...     entity_types=[EntityType.PROJECT],
        ...     identifier="manual tetris test",
        ...     parameters={"status": "INACTIVE"},
        ...     confidence=0.95,
        ...     raw_input="Mark the manual tetris test as INACTIVE"
        ... )
    """
    operation: OperationType
    entity_types: List[EntityType]
    identifier: Optional[Union[str, int]] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    query_type: Optional[QueryType] = None
    confidence: float = 0.0
    raw_input: str = ""

    @property
    def entity_type(self) -> EntityType:
        """Backward compatibility: return first entity type."""
        return self.entity_types[0] if self.entity_types else None

    def __post_init__(self):
        """Validate confidence score and operation-specific requirements."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")

        # UPDATE and DELETE operations require an identifier OR bulk flag
        if self.operation in [OperationType.UPDATE, OperationType.DELETE]:
            is_bulk = (
                self.identifier == "__ALL__" or
                (self.parameters and self.parameters.get('bulk') is True) or
                (self.parameters and self.parameters.get('all') is True)
            )

            if self.identifier is None and not is_bulk:
                raise ValueError(
                    f"{self.operation.value} operation requires an identifier or bulk flag. "
                    f"To operate on all items, use 'all' keyword (e.g., 'delete all tasks')."
                )

        # QUERY operations should have a query_type
        if self.operation == OperationType.QUERY and self.query_type is None:
            # Default to SIMPLE if not specified
            self.query_type = QueryType.SIMPLE


@dataclass
class OperationResult:
    """Result of operation classification.

    Attributes:
        operation_type: Classified operation (CREATE/UPDATE/DELETE/QUERY)
        confidence: Confidence score from 0.0 to 1.0
        raw_response: Raw LLM response for debugging
        reasoning: Brief explanation of classification decision
    """
    operation_type: OperationType
    confidence: float
    raw_response: str = ""
    reasoning: str = ""

    def __post_init__(self):
        """Validate confidence score."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")


@dataclass
class EntityTypeResult:
    """Result of entity type classification.

    Attributes:
        entity_type: Classified entity type (project/epic/story/task/milestone)
        confidence: Confidence score from 0.0 to 1.0
        raw_response: Raw LLM response for debugging
        reasoning: Brief explanation of classification decision
    """
    entity_type: EntityType
    confidence: float
    raw_response: str = ""
    reasoning: str = ""

    def __post_init__(self):
        """Validate confidence score."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")


@dataclass
class IdentifierResult:
    """Result of entity identifier extraction.

    Attributes:
        identifier: Extracted identifier (name string, ID integer, or None for "show all" queries)
        confidence: Confidence score from 0.0 to 1.0
        raw_response: Raw LLM response for debugging
        reasoning: Brief explanation of extraction decision
    """
    identifier: Union[str, int, None]
    confidence: float
    raw_response: str = ""
    reasoning: str = ""

    def __post_init__(self):
        """Validate confidence score and identifier type."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")

        if self.identifier is not None and not isinstance(self.identifier, (str, int)):
            raise TypeError(f"Identifier must be str, int, or None, got {type(self.identifier)}")


@dataclass
class ParameterResult:
    """Result of parameter extraction.

    Attributes:
        parameters: Extracted parameters as dictionary (status, priority, dependencies, etc.)
        confidence: Confidence score from 0.0 to 1.0
        raw_response: Raw LLM response for debugging
        reasoning: Brief explanation of extraction decision
    """
    parameters: Dict[str, Any]
    confidence: float
    raw_response: str = ""
    reasoning: str = ""

    def __post_init__(self):
        """Validate confidence score."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")


@dataclass
class ParsedIntent:
    """Parsed intent from NL command processor (ADR-017).

    After ADR-017, NLCommandProcessor returns ParsedIntent instead of
    executing commands. This enables routing through orchestrator for
    validation and quality control.

    Attributes:
        intent_type: "COMMAND" or "QUESTION"
        operation_context: OperationContext for COMMAND intents
        original_message: User's original NL input
        confidence: Aggregate confidence from pipeline stages
        requires_execution: True for COMMAND, False for QUESTION
        question_context: Context for QUESTION intents
        metadata: Additional metadata (classification scores, etc.)
    """
    intent_type: str  # "COMMAND" or "QUESTION"
    operation_context: Optional['OperationContext']
    original_message: str
    confidence: float
    requires_execution: bool
    question_context: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate intent structure."""
        if self.intent_type not in ["COMMAND", "QUESTION"]:
            raise ValueError(f"intent_type must be 'COMMAND' or 'QUESTION', got {self.intent_type}")

        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")

        # COMMAND intents must have operation_context
        if self.intent_type == "COMMAND" and self.operation_context is None:
            raise ValueError("COMMAND intent requires operation_context")

        # QUESTION intents should have question_context
        if self.intent_type == "QUESTION" and self.question_context is None:
            # Initialize empty context if not provided
            self.question_context = {}

    def is_command(self) -> bool:
        """Check if this is a COMMAND intent."""
        return self.intent_type == "COMMAND"

    def is_question(self) -> bool:
        """Check if this is a QUESTION intent."""
        return self.intent_type == "QUESTION"


@dataclass
class QuestionResponse:
    """Response to a user question.

    Attributes:
        answer: Formatted response text
        question_type: Type of question answered (NEXT_STEPS/STATUS/BLOCKERS/PROGRESS/GENERAL)
        entities: Entities extracted from the question (project_id, task_id, etc.)
        data: Raw data from StateManager used to build the answer
        confidence: Confidence in the answer quality (0.0 to 1.0)
    """
    answer: str
    question_type: QuestionType
    entities: Dict[str, Any] = field(default_factory=dict)
    data: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0

    def __post_init__(self):
        """Validate confidence score."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")


# Backwards compatibility with existing code
# These can be deprecated in v1.7.0 after migration to new types
ExtractedEntityType = EntityType  # Alias for migration


__all__ = [
    # Enums
    "OperationType",
    "QueryType",
    "EntityType",
    "QuestionType",

    # Result dataclasses
    "OperationContext",
    "OperationResult",
    "EntityTypeResult",
    "IdentifierResult",
    "ParameterResult",
    "ParsedIntent",
    "QuestionResponse",

    # Backwards compatibility
    "ExtractedEntityType",
]
