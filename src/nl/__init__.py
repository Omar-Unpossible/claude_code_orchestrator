"""Natural Language Command Interface Module.

This module provides natural language processing capabilities for Obra,
enabling users to interact with the orchestrator using conversational commands
instead of rigid syntax.

Components:
    - IntentClassifier: Classifies user intent (COMMAND/QUESTION/CLARIFICATION)
    - EntityExtractor: Extracts structured entities from natural language
    - CommandValidator: Validates extracted entities against business rules
    - CommandExecutor: Executes validated commands via StateManager
    - NLQueryHelper: Query-only helper for NL queries (ADR-017)
    - ResponseFormatter: Formats responses with color and helpful messages
    - NLCommandProcessor: Orchestrates the entire NL processing pipeline

Design:
    - Plugin-agnostic: Works with any LLM (Qwen, OpenAI, Claude, etc.)
    - Schema-aware: Understands Obra's epic/story/task/subtask model
    - Hybrid auto-detection: Automatically detects commands vs questions
    - Graceful degradation: Asks for clarification when uncertain

See docs/development/NL_COMMAND_INTERFACE_SPEC.json for complete specification.
"""

__version__ = "1.0.0"
__author__ = "Obra Development Team"

# Version will be populated as components are implemented
__all__ = [
    # Story 1
    "IntentClassifier",
    "IntentResult",

    # Story 2
    "EntityExtractor",
    "ExtractedEntities",

    # Story 3
    "CommandValidator",
    "CommandExecutor",
    "NLQueryHelper",  # ADR-017 Story 3
    "QueryResult",  # ADR-017 Story 3
    "ValidationResult",
    "ExecutionResult",

    # Story 4
    "ResponseFormatter",

    # Story 5
    "NLCommandProcessor",
    "NLResponse",
    "ParsedIntent",  # ADR-017 Story 4
]
