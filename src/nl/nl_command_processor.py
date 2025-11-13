"""Natural Language Command Processor.

This module orchestrates the entire NL command pipeline:
- Intent classification (COMMAND, QUESTION, CLARIFICATION_NEEDED)
- 5-stage command processing (ADR-016):
  1. OperationClassifier: Classify operation (CREATE/UPDATE/DELETE/QUERY)
  2. EntityTypeClassifier: Classify entity type (project/epic/story/task/milestone)
  3. EntityIdentifierExtractor: Extract entity identifier (name or ID)
  4. ParameterExtractor: Extract operation-specific parameters
  5. Build OperationContext → validate → execute
- Question handling via QuestionHandler
- Command validation against business rules
- Command execution via StateManager
- Response formatting with color coding

Classes:
    NLResponse: Dataclass holding NL processing results
    NLCommandProcessor: Main orchestrator for NL command pipeline

Example:
    >>> from core.state import StateManager
    >>> from plugins.registry import LLMRegistry
    >>> llm_plugin = LLMRegistry.get('ollama')()
    >>> state = StateManager(db_url)
    >>> processor = NLCommandProcessor(llm_plugin, state, config)
    >>> response = processor.process("Mark the manual tetris test as INACTIVE")
    >>> print(response.response)  # Formatted response
"""

import logging
import warnings
import time
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from colorama import Fore, Style
from core.state import StateManager
from core.config import Config
from core.metrics import get_metrics_collector
from plugins.base import LLMPlugin
from nl.intent_classifier import IntentClassifier
from nl.command_validator import CommandValidator
from nl.command_executor import CommandExecutor, ExecutionResult
from nl.response_formatter import ResponseFormatter
from src.nl.types import OperationContext, OperationType, EntityType, QueryType, ParsedIntent

# New ADR-016 components
from src.nl.operation_classifier import OperationClassifier
from src.nl.entity_type_classifier import EntityTypeClassifier
from src.nl.entity_identifier_extractor import EntityIdentifierExtractor
from src.nl.parameter_extractor import ParameterExtractor
from src.nl.question_handler import QuestionHandler
from src.nl.fast_path_matcher import FastPathMatcher
from src.nl.query_cache import QueryCache

# Legacy component (deprecated)
try:
    from nl.entity_extractor import EntityExtractor
    LEGACY_ENTITY_EXTRACTOR = True
except ImportError:
    LEGACY_ENTITY_EXTRACTOR = False

logger = logging.getLogger(__name__)


@dataclass
class NLResponse:
    """Result of NL command processing.

    Attributes:
        response: Formatted response string for user display
        intent: Classified intent (COMMAND, QUESTION, CLARIFICATION_NEEDED)
        success: True if command executed successfully
        updated_context: Updated conversation context
        forwarded_to_claude: True if question forwarded to Claude Code
        execution_result: Optional ExecutionResult from command execution
    """
    response: str
    intent: str
    success: bool
    updated_context: Dict[str, Any] = field(default_factory=dict)
    forwarded_to_claude: bool = False
    execution_result: Optional['ExecutionResult'] = None


@dataclass
class PendingOperation:
    """Pending operation awaiting user confirmation.

    Attributes:
        context: OperationContext for the pending operation
        project_id: Project ID for the operation
        timestamp: Timestamp when confirmation was requested
        original_message: Original user message that triggered confirmation
    """
    context: OperationContext
    project_id: int
    timestamp: float
    original_message: str


class NLCommandProcessor:
    """Orchestrate NL command processing pipeline.

    Coordinates intent classification, entity extraction, validation,
    execution, and response formatting. Manages conversation context
    for multi-turn interactions.

    Args:
        llm_plugin: LLM plugin for intent/entity processing
        state_manager: StateManager for command execution
        config: Configuration object
        confidence_threshold: Confidence threshold for clarification (default: 0.7)
        max_context_turns: Maximum conversation turns to keep (default: 10)

    Example:
        >>> processor = NLCommandProcessor(llm_plugin, state_manager, config)
        >>> response = processor.process(
        ...     "Create an epic called User Auth",
        ...     context={'project_id': 1}
        ... )
        >>> print(response.response)
        ✓ Created Epic #5: User Auth
    """

    def __init__(
        self,
        llm_plugin: LLMPlugin,
        state_manager: StateManager,
        config: Config,
        confidence_threshold: float = 0.7,
        max_context_turns: int = 10
    ):
        """Initialize NL command processor.

        Args:
            llm_plugin: LLM plugin for NL processing
            state_manager: StateManager for execution
            config: Configuration object
            confidence_threshold: Threshold for clarification
            max_context_turns: Max conversation turns to keep
        """
        self.llm_plugin = llm_plugin
        self.state_manager = state_manager
        self.config = config
        self.confidence_threshold = confidence_threshold
        self.max_context_turns = max_context_turns

        # Initialize pipeline components
        self.intent_classifier = IntentClassifier(
            llm_plugin=llm_plugin,
            confidence_threshold=confidence_threshold
        )

        # ADR-016: 5-stage pipeline components
        self.operation_classifier = OperationClassifier(
            llm_plugin=llm_plugin,
            confidence_threshold=confidence_threshold
        )

        self.entity_type_classifier = EntityTypeClassifier(
            llm_plugin=llm_plugin,
            confidence_threshold=confidence_threshold
        )

        self.entity_identifier_extractor = EntityIdentifierExtractor(
            llm_plugin=llm_plugin,
            confidence_threshold=confidence_threshold
        )

        self.parameter_extractor = ParameterExtractor(
            llm_plugin=llm_plugin,
            confidence_threshold=confidence_threshold
        )

        self.question_handler = QuestionHandler(
            state_manager=state_manager,
            llm_plugin=llm_plugin
        )

        # Initialize fast path matcher
        self.fast_path_matcher = FastPathMatcher()

        # Initialize query cache
        self.query_cache = QueryCache(
            ttl_seconds=config.get('nl_commands.query_cache.ttl_seconds', 60),
            max_entries=config.get('nl_commands.query_cache.max_entries', 1000)
        )

        # Legacy entity extractor (deprecated, for backward compatibility)
        if LEGACY_ENTITY_EXTRACTOR:
            schema_path = config.get('nl_commands.schema_path', 'src/nl/schemas/obra_schema.json')
            self.entity_extractor = EntityExtractor(
                llm_plugin=llm_plugin,
                schema_path=schema_path
            )
        else:
            self.entity_extractor = None

        self.command_validator = CommandValidator(state_manager)

        # Get confirmation requirements from config
        require_confirmation_for = config.get(
            'nl_commands.require_confirmation_for',
            ['delete', 'update', 'execute']
        )
        default_project_id = config.get('nl_commands.default_project_id', 1)

        self.command_executor = CommandExecutor(
            state_manager,
            require_confirmation_for=require_confirmation_for,
            default_project_id=default_project_id
        )

        self.response_formatter = ResponseFormatter()

        # Conversation context tracking
        self.conversation_history: List[Dict[str, Any]] = []

        # Confirmation workflow tracking
        self.pending_confirmation: Optional[PendingOperation] = None
        self.confirmation_timeout = config.get('nl_commands.confirmation_timeout', 60)

        logger.info(
            f"NLCommandProcessor initialized (threshold={confidence_threshold}, "
            f"max_turns={max_context_turns})"
        )

    def process(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        project_id: Optional[int] = None,
        confirmed: bool = False
    ) -> ParsedIntent:
        """Process natural language message and return parsed intent (ADR-017).

        After ADR-017, this method returns ParsedIntent instead of executing.
        Caller routes to orchestrator for execution.

        Args:
            message: User's natural language message
            context: Optional conversation context
            project_id: Optional project ID (stored in metadata)
            confirmed: True if user confirmed destructive operation (stored in metadata)

        Returns:
            ParsedIntent with operation_context for COMMAND or question_context for QUESTION

        Example:
            >>> parsed_intent = processor.process("Create epic for user auth")
            >>> if parsed_intent.is_command():
            ...     # Route to orchestrator for execution
            ...     task = converter.convert(parsed_intent.operation_context, project_id=1)
        """
        metrics = get_metrics_collector()
        start = time.time()

        if not message or not message.strip():
            return ParsedIntent(
                intent_type="QUESTION",
                operation_context=None,
                original_message=message or "",
                confidence=1.0,
                requires_execution=False,
                question_context={
                    'question': message or "",
                    'question_type': 'error',
                    'answer': "Please provide a message",
                    'error': True
                },
                metadata={'invalid_input': True}
            )

        # Check for help request
        message_lower = message.lower().strip()
        if message_lower in ['help', '?', 'help me']:
            return self._show_help()

        # Check for entity-specific help
        if message_lower.startswith('help '):
            entity_type = message_lower.split()[1] if len(message_lower.split()) > 1 else None
            if entity_type:
                return self._show_entity_help(entity_type)

        # Check for confirmation response first
        if self.pending_confirmation:
            if self._is_confirmation_response(message):
                return self._handle_confirmation_response(message, project_id)
            elif self._is_cancellation_response(message):
                return self._handle_cancellation()
            # Else: treat as new command (implicit cancellation)
            self.pending_confirmation = None

        # TRY FAST PATH FIRST (bypass LLM for common queries)
        fast_path_context = self.fast_path_matcher.match(message)
        if fast_path_context:
            logger.info(f"Fast path matched: {message} → {fast_path_context.entity_type.value}")

            # Build ParsedIntent from fast path result
            parsed_intent = ParsedIntent(
                intent_type='COMMAND',
                operation_context=fast_path_context,
                original_message=message,
                confidence=1.0,
                requires_execution=True,
                metadata={'fast_path': True}
            )

            # Record metrics
            latency_ms = (time.time() - start) * 1000
            metrics.record_nl_command(
                operation=fast_path_context.operation.value,
                latency_ms=latency_ms,
                success=True
            )

            return parsed_intent

        # CHECK CACHE (before LLM pipeline)
        cached_result = self.query_cache.get(message, context)
        if cached_result:
            logger.info(f"Cache hit: {message}")

            # Record metrics
            latency_ms = (time.time() - start) * 1000
            metrics.record_nl_command(
                operation='QUERY',
                latency_ms=latency_ms,
                success=True
            )

            return cached_result

        # Fall back to full LLM pipeline
        logger.debug(f"Fast path miss and cache miss, using LLM pipeline: {message}")

        # Build conversation context
        conv_context = self._build_conversation_context(context)

        try:
            # Step 1: Classify intent
            intent_result = self.intent_classifier.classify(message, conv_context)
            logger.info(
                f"Intent classified: {intent_result.intent} "
                f"(confidence={intent_result.confidence:.2f})"
            )

            # Step 2: Route based on intent
            if intent_result.intent == 'CLARIFICATION_NEEDED':
                parsed_intent = self._handle_clarification(message, intent_result, conv_context)
            elif intent_result.intent == 'QUESTION':
                parsed_intent = self._handle_question(message, intent_result, conv_context)
            elif intent_result.intent == 'COMMAND':
                parsed_intent = self._handle_command(
                    message,
                    intent_result,
                    conv_context,
                    project_id,
                    confirmed
                )
            else:
                logger.warning(f"Unknown intent: {intent_result.intent}")
                parsed_intent = ParsedIntent(
                    intent_type="QUESTION",
                    operation_context=None,
                    original_message=message,
                    confidence=0.0,
                    requires_execution=False,
                    question_context={
                        'question': message,
                        'question_type': 'error',
                        'answer': f"Unrecognized intent: {intent_result.intent}",
                        'error': True
                    },
                    metadata={'unknown_intent': intent_result.intent}
                )

            # CACHE RESULT (only for QUERY operations)
            if (parsed_intent.operation_context and
                parsed_intent.operation_context.operation == OperationType.QUERY):
                self.query_cache.put(message, context, parsed_intent)

            # Record total NL command latency BEFORE return
            latency_ms = (time.time() - start) * 1000
            operation_type = parsed_intent.operation_context.operation.value if parsed_intent.operation_context else 'unknown'
            metrics.record_nl_command(
                operation=operation_type,
                latency_ms=latency_ms,
                success=True
            )

            return parsed_intent

        except Exception as e:
            logger.exception(f"NL processing failed: {e}")

            # Record failed NL command
            latency_ms = (time.time() - start) * 1000
            metrics.record_nl_command(
                operation='error',
                latency_ms=latency_ms,
                success=False
            )

            return ParsedIntent(
                intent_type="QUESTION",
                operation_context=None,
                original_message=message,
                confidence=0.0,
                requires_execution=False,
                question_context={
                    'question': message,
                    'question_type': 'error',
                    'answer': f"Processing error: {str(e)}",
                    'error': True
                },
                metadata={'processing_error': str(e)}
            )

    def process_and_execute(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        project_id: Optional[int] = None,
        confirmed: bool = False
    ) -> NLResponse:
        """Process and execute NL message (DEPRECATED - ADR-017).

        This method maintains backward compatibility with pre-ADR-017 code.
        New code should use process() and route through orchestrator.

        Args:
            message: Natural language message
            context: Optional conversation context
            project_id: Optional project ID
            confirmed: User confirmation status

        Returns:
            NLResponse with execution results

        Deprecated:
            Since v1.7.0: Use process() which returns ParsedIntent, then route to orchestrator
        """
        warnings.warn(
            "process_and_execute() is deprecated. Use process() and route to orchestrator.",
            DeprecationWarning,
            stacklevel=2
        )

        # Parse intent
        parsed_intent = self.process(message, context, project_id, confirmed)

        # Handle questions inline (no execution needed)
        if parsed_intent.is_question():
            answer = parsed_intent.question_context.get('answer', 'No answer available')
            return NLResponse(
                response=answer,
                intent='QUESTION',
                success=not parsed_intent.question_context.get('error', False),
                updated_context=parsed_intent.metadata
            )

        # Handle commands (need execution)
        if parsed_intent.is_command():
            # Check if already executed (confirmation workflow)
            if parsed_intent.metadata.get('executed'):
                return NLResponse(
                    response=parsed_intent.metadata.get('execution_response', 'Operation completed'),
                    intent='COMMAND',
                    success=parsed_intent.metadata.get('execution_success', True),
                    execution_result=parsed_intent.metadata.get('execution_result')
                )

            # Check if validation failed
            if parsed_intent.metadata.get('validation_failed'):
                errors = parsed_intent.metadata.get('validation_errors', ['Validation failed'])
                error_response = self.response_formatter._format_error(
                    type('ExecutionResult', (), {
                        'success': False,
                        'errors': errors,
                        'results': {}
                    })()
                )
                return NLResponse(
                    response=error_response,
                    intent='COMMAND',
                    success=False
                )

            # Execute via command_executor (old way)
            try:
                execution_result = self.command_executor.execute(
                    parsed_intent.operation_context,
                    project_id=project_id,
                    confirmed=confirmed
                )

                # Format response
                response = self.response_formatter.format(
                    execution_result,
                    intent='COMMAND',
                    operation=parsed_intent.operation_context.operation.value
                )

                return NLResponse(
                    response=response,
                    intent='COMMAND',
                    success=execution_result.success,
                    execution_result=execution_result
                )
            except Exception as e:
                logger.exception(f"Execution failed in process_and_execute: {e}")
                error_response = self.response_formatter._format_error(
                    type('ExecutionResult', (), {
                        'success': False,
                        'errors': [str(e)],
                        'results': {}
                    })()
                )
                return NLResponse(
                    response=error_response,
                    intent='COMMAND',
                    success=False
                )

        # Fallback
        return NLResponse(
            response="Unable to process message",
            intent='ERROR',
            success=False
        )

    def _handle_command(
        self,
        message: str,
        intent_result: Any,
        context: Dict[str, Any],
        project_id: Optional[int],
        confirmed: bool
    ) -> ParsedIntent:
        """Handle COMMAND intent through 5-stage pipeline (ADR-017).

        Pipeline stages:
        1. OperationClassifier → OperationType (CREATE/UPDATE/DELETE/QUERY)
        2. EntityTypeClassifier → EntityType (project/epic/story/task/milestone)
        3. EntityIdentifierExtractor → identifier (name or ID)
        4. ParameterExtractor → parameters (status, priority, etc.)
        5. Build OperationContext → validate → return ParsedIntent (NO EXECUTION!)

        Query Type Determination (for QUERY operations):
        - Priority 1: LLM-extracted query_type from ParameterExtractor (Stage 4)
        - Priority 2: Keyword matching fallback if LLM didn't extract
          - HIERARCHICAL: workplan, hierarchy, hierarchical, plan, plans
          - NEXT_STEPS: next, next steps, what's next
          - BACKLOG: backlog, pending, todo
          - ROADMAP: roadmap, milestone
          - SIMPLE: default if no matches

        This prioritization allows the LLM's semantic understanding to take precedence
        while maintaining robust fallback behavior for reliability.

        Args:
            message: User message
            intent_result: Intent classification result
            context: Conversation context
            project_id: Optional project ID (stored in metadata)
            confirmed: User confirmation status (stored in metadata)

        Returns:
            ParsedIntent with OperationContext (execution happens elsewhere)
        """
        try:
            # Stage 1: Classify operation type (CREATE/UPDATE/DELETE/QUERY)
            logger.debug(f"Stage 1: Classifying operation for: {message}")
            operation_result = self.operation_classifier.classify(message)
            logger.info(
                f"Stage 1 complete: Operation={operation_result.operation_type.value} "
                f"(confidence={operation_result.confidence:.2f})"
            )

            # Stage 2: Classify entity type (project/epic/story/task/milestone)
            logger.debug(f"Stage 2: Classifying entity type (operation={operation_result.operation_type.value})")
            entity_type_result = self.entity_type_classifier.classify(
                message,
                operation=operation_result.operation_type
            )
            logger.info(
                f"Stage 2 complete: EntityType={entity_type_result.entity_type.value} "
                f"(confidence={entity_type_result.confidence:.2f})"
            )

            # Stage 3: Extract entity identifier (name or ID)
            logger.debug(f"Stage 3: Extracting identifier")
            identifier_result = self.entity_identifier_extractor.extract(
                message,
                entity_type=entity_type_result.entity_type,
                operation=operation_result.operation_type
            )
            logger.info(
                f"Stage 3 complete: Identifier={identifier_result.identifier} "
                f"(confidence={identifier_result.confidence:.2f})"
            )

            # Stage 4: Extract parameters (status, priority, dependencies, etc.)
            logger.debug(f"Stage 4: Extracting parameters")
            parameter_result = self.parameter_extractor.extract(
                message,
                operation=operation_result.operation_type,
                entity_type=entity_type_result.entity_type
            )
            logger.info(
                f"Stage 4 complete: Parameters={list(parameter_result.parameters.keys())} "
                f"(confidence={parameter_result.confidence:.2f})"
            )

            # Stage 5: Build OperationContext
            logger.debug(f"Stage 5: Building OperationContext")

            # Calculate aggregate confidence (average of all stages)
            aggregate_confidence = (
                operation_result.confidence +
                entity_type_result.confidence +
                identifier_result.confidence +
                parameter_result.confidence
            ) / 4.0

            # Determine query type for QUERY operations
            query_type = None
            if operation_result.operation_type == OperationType.QUERY:
                # PRIORITY 1: Check if ParameterExtractor found query_type (LLM extraction)
                if 'query_type' in parameter_result.parameters:
                    query_type_str = parameter_result.parameters['query_type']
                    # Convert string to enum
                    try:
                        query_type = QueryType(query_type_str)
                        logger.debug(f"Using LLM-extracted query_type: {query_type}")
                    except ValueError:
                        logger.warning(
                            f"Invalid query_type '{query_type_str}' from LLM, "
                            f"falling back to keyword matching"
                        )

                # PRIORITY 2: Keyword fallback if LLM didn't extract or conversion failed
                if query_type is None:
                    # Check for hierarchical keywords (added 'plan' and 'plans')
                    if any(keyword in message.lower() for keyword in
                           ['workplan', 'hierarchy', 'hierarchical', 'plan', 'plans']):
                        query_type = QueryType.HIERARCHICAL
                    elif any(keyword in message.lower() for keyword in ['next', 'next steps', "what's next"]):
                        query_type = QueryType.NEXT_STEPS
                    elif any(keyword in message.lower() for keyword in ['backlog', 'pending', 'todo']):
                        query_type = QueryType.BACKLOG
                    elif any(keyword in message.lower() for keyword in ['roadmap', 'milestone']):
                        query_type = QueryType.ROADMAP
                    else:
                        query_type = QueryType.SIMPLE

            operation_context = OperationContext(
                operation=operation_result.operation_type,
                entity_type=entity_type_result.entity_type,
                identifier=identifier_result.identifier,
                parameters=parameter_result.parameters,
                query_type=query_type,
                confidence=aggregate_confidence,
                raw_input=message
            )

            logger.info(
                f"OperationContext built: {operation_context.operation.value} "
                f"{operation_context.entity_type.value} (confidence={aggregate_confidence:.2f})"
            )

            # Step 6: Validate OperationContext
            logger.debug(f"Step 6: Validating OperationContext")
            validation_result = self.command_validator.validate(operation_context)

            if not validation_result.valid:
                # Validation failed - store error in metadata
                logger.warning(f"Validation failed: {validation_result.errors}")

                return ParsedIntent(
                    intent_type="COMMAND",
                    operation_context=operation_context,
                    original_message=message,
                    confidence=aggregate_confidence,
                    requires_execution=False,  # Don't execute if validation failed
                    metadata={
                        'intent_confidence': intent_result.confidence,
                        'entity_confidence': aggregate_confidence,
                        'operation': str(operation_context.operation),
                        'entity_type': str(operation_context.entity_type),
                        'project_id': project_id,
                        'confirmed': confirmed,
                        'validation_failed': True,
                        'validation_errors': validation_result.errors
                    }
                )

            # Step 7: Return ParsedIntent (NO EXECUTION!)
            logger.info(
                f"Returning ParsedIntent for orchestrator execution: "
                f"{operation_context.operation.value} {operation_context.entity_type.value}"
            )

            return ParsedIntent(
                intent_type="COMMAND",
                operation_context=operation_context,
                original_message=message,
                confidence=aggregate_confidence,
                requires_execution=True,
                metadata={
                    'intent_confidence': intent_result.confidence,
                    'entity_confidence': aggregate_confidence,
                    'operation': str(operation_context.operation),
                    'entity_type': str(operation_context.entity_type),
                    'project_id': project_id,
                    'confirmed': confirmed
                }
            )

        except ValueError as e:
            # OperationContext validation error (e.g., UPDATE without identifier)
            logger.warning(f"OperationContext validation error: {e}")

            # Still return ParsedIntent but mark validation as failed
            return ParsedIntent(
                intent_type="COMMAND",
                operation_context=None,  # Invalid context
                original_message=message,
                confidence=0.0,
                requires_execution=False,
                metadata={
                    'validation_failed': True,
                    'validation_errors': [str(e)],
                    'project_id': project_id,
                    'confirmed': confirmed
                }
            )

        except Exception as e:
            logger.exception(f"Command handling failed at pipeline stage: {e}")

            # Return ParsedIntent with pipeline error
            return ParsedIntent(
                intent_type="COMMAND",
                operation_context=None,
                original_message=message,
                confidence=0.0,
                requires_execution=False,
                metadata={
                    'pipeline_error': True,
                    'error_message': str(e),
                    'project_id': project_id,
                    'confirmed': confirmed
                }
            )

    def _handle_question(
        self,
        message: str,
        intent_result: Any,
        context: Dict[str, Any]
    ) -> ParsedIntent:
        """Handle QUESTION intent via QuestionHandler (ADR-017).

        Routes informational questions to the QuestionHandler which:
        1. Classifies question type (NEXT_STEPS/STATUS/BLOCKERS/PROGRESS/GENERAL)
        2. Extracts entities from question (project name, task ID, etc.)
        3. Queries StateManager for relevant data
        4. Formats helpful response

        Args:
            message: User message
            intent_result: Intent classification result
            context: Conversation context

        Returns:
            ParsedIntent with question_context (execution not needed for questions)
        """
        try:
            logger.debug(f"Handling QUESTION: {message}")

            # Use QuestionHandler to process the question
            question_response = self.question_handler.handle(message)

            logger.info(
                f"Question handled: type={question_response.question_type.value}, "
                f"confidence={question_response.confidence:.2f}"
            )

            return ParsedIntent(
                intent_type="QUESTION",
                operation_context=None,
                original_message=message,
                confidence=question_response.confidence,
                requires_execution=False,
                question_context={
                    'question': message,
                    'question_type': question_response.question_type.value,
                    'answer': question_response.answer,
                    'entities': question_response.entities,
                    'data': question_response.data
                },
                metadata={
                    'intent_confidence': intent_result.confidence,
                    'question_confidence': question_response.confidence
                }
            )

        except Exception as e:
            logger.exception(f"Question handling failed: {e}")

            # Return ParsedIntent with error context
            fallback_response = (
                f"I couldn't answer that question: {str(e)}\n\n"
                f"Try rephrasing as a command like:\n"
                f"  • 'Show me tasks for project X'\n"
                f"  • 'List next steps'\n"
                f"  • 'What's the status of epic Y'"
            )

            return ParsedIntent(
                intent_type="QUESTION",
                operation_context=None,
                original_message=message,
                confidence=0.0,
                requires_execution=False,
                question_context={
                    'question': message,
                    'question_type': 'general',
                    'answer': fallback_response,
                    'error': str(e)
                },
                metadata={
                    'intent_confidence': intent_result.confidence,
                    'error': True
                }
            )

    def _handle_clarification(
        self,
        message: str,
        intent_result: Any,
        context: Dict[str, Any]
    ) -> ParsedIntent:
        """Handle CLARIFICATION_NEEDED intent - ask user for clarification (ADR-017).

        Args:
            message: User message
            intent_result: Intent classification result
            context: Conversation context

        Returns:
            ParsedIntent with clarification context (QUESTION type)
        """
        # Generate suggestions based on detected entities
        suggestions = []
        if intent_result.detected_entities:
            entity_type = intent_result.detected_entities.get('entity_type')
            if entity_type == 'epic':
                suggestions.append("Create a new epic")
                suggestions.append("List existing epics")
            elif entity_type == 'story':
                suggestions.append("Create a new story")
                suggestions.append("Show stories for an epic")
            else:
                suggestions.append("Create a work item (epic/story/task)")
                suggestions.append("List existing work items")

        clarification_message = "I'm not sure what you'd like to do. Did you mean:"
        if suggestions:
            clarification_message += "\n" + "\n".join(f"  • {s}" for s in suggestions)

        return ParsedIntent(
            intent_type="QUESTION",  # Treat clarification as a question
            operation_context=None,
            original_message=message,
            confidence=intent_result.confidence,
            requires_execution=False,
            question_context={
                'question': message,
                'question_type': 'clarification',
                'answer': clarification_message,
                'suggestions': suggestions,
                'detected_entities': intent_result.detected_entities if hasattr(intent_result, 'detected_entities') else {}
            },
            metadata={
                'intent_confidence': intent_result.confidence,
                'clarification_needed': True
            }
        )

    def _build_conversation_context(
        self,
        external_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Build conversation context from history and external context.

        Args:
            external_context: Optional external context to merge

        Returns:
            Combined conversation context
        """
        context = {
            'conversation_turns': len(self.conversation_history),
            'recent_history': self.conversation_history[-3:] if self.conversation_history else []
        }

        # Merge external context
        if external_context:
            context.update(external_context)

        return context

    def _handle_project_query(
        self,
        message: str,
        context: Dict[str, Any],
        project_id: Optional[int]
    ) -> NLResponse:
        """Handle project-level queries (show current project, list projects, etc.).

        Args:
            message: User message
            context: Current conversation context
            project_id: Project ID to query (or None for current)

        Returns:
            NLResponse with project information
        """
        try:
            # Use provided project_id or get from context
            proj_id = project_id or context.get('project_id')

            if proj_id:
                # Query specific project
                project = self.state_manager.get_project(proj_id)
                if not project:
                    response = f"✗ Project #{proj_id} not found"
                    return NLResponse(
                        response=response,
                        intent='COMMAND',
                        success=False
                    )

                # Get project stats
                epics = self.state_manager.list_tasks(
                    project_id=proj_id,
                    task_type='epic'
                )
                tasks = self.state_manager.list_tasks(project_id=proj_id)

                response = f"""✓ Current Project: {project.project_name} (ID: {proj_id})
  Status: {project.status}
  Created: {project.created_at.strftime('%Y-%m-%d')}
  Working Directory: {project.working_directory or 'Not set'}

  📊 Stats:
    • Epics: {len([e for e in epics if hasattr(e, 'task_type')])}
    • Tasks: {len(tasks)}
"""

                return NLResponse(
                    response=response,
                    intent='COMMAND',
                    success=True,
                    execution_result=None  # Query operation, no entities created
                )
            else:
                # List all projects
                projects = self.state_manager.list_projects()
                if not projects:
                    response = "✗ No projects found. Create one with '/project create <name>'"
                    return NLResponse(
                        response=response,
                        intent='COMMAND',
                        success=False
                    )

                response = "📋 Projects:\n"
                for p in projects[:10]:  # Limit to 10
                    response += f"  • #{p.id}: {p.project_name} ({p.status})\n"

                return NLResponse(
                    response=response,
                    intent='COMMAND',
                    success=True
                )

        except Exception as e:
            logger.exception(f"Project query failed: {e}")
            return NLResponse(
                response=f"✗ Error querying project: {e}",
                intent='COMMAND',
                success=False
            )

    def _is_confirmation_response(self, message: str) -> bool:
        """Check if message is yes/y/confirm/ok/proceed.

        Args:
            message: User message to check

        Returns:
            True if message is a confirmation keyword
        """
        confirmation_keywords = {'yes', 'y', 'confirm', 'ok', 'proceed', 'go ahead'}
        return message.strip().lower() in confirmation_keywords

    def _is_cancellation_response(self, message: str) -> bool:
        """Check if message is no/n/cancel/abort.

        Args:
            message: User message to check

        Returns:
            True if message is a cancellation keyword
        """
        cancellation_keywords = {'no', 'n', 'cancel', 'abort', 'stop', 'nevermind'}
        return message.strip().lower() in cancellation_keywords

    def _handle_confirmation_response(self, message: str, project_id: Optional[int] = None) -> ParsedIntent:
        """Execute pending operation after user confirms (ADR-017 - temporary execution).

        NOTE: This method still executes via command_executor for backward compatibility.
        In Story 5, confirmation will route through orchestrator.

        Args:
            message: User confirmation message
            project_id: Optional project ID override

        Returns:
            ParsedIntent with execution result in metadata
        """
        # Check timeout
        if time.time() - self.pending_confirmation.timestamp > self.confirmation_timeout:
            self.pending_confirmation = None
            return ParsedIntent(
                intent_type="QUESTION",
                operation_context=None,
                original_message=message,
                confidence=1.0,
                requires_execution=False,
                question_context={
                    'question': message,
                    'question_type': 'error',
                    'answer': f"{Fore.YELLOW}Confirmation timeout. Please try again.{Style.RESET_ALL}",
                    'error': True
                },
                metadata={'confirmation_timeout': True}
            )

        # Execute with confirmed=True (temporary - will be removed in Story 5)
        execution_result = self.command_executor.execute(
            self.pending_confirmation.context,
            project_id=self.pending_confirmation.project_id,
            confirmed=True
        )

        # Clear pending state
        operation = self.pending_confirmation.context.operation.value
        operation_context = self.pending_confirmation.context
        self.pending_confirmation = None

        # Format response
        response = self.response_formatter.format(
            execution_result,
            intent='COMMAND',
            operation=operation
        )

        return ParsedIntent(
            intent_type="COMMAND",
            operation_context=operation_context,
            original_message=message,
            confidence=1.0,
            requires_execution=False,  # Already executed
            metadata={
                'confirmed': True,
                'executed': True,
                'execution_success': execution_result.success,
                'execution_response': response,
                'execution_result': execution_result
            }
        )

    def _handle_cancellation(self) -> ParsedIntent:
        """Cancel pending operation (ADR-017).

        Returns:
            ParsedIntent confirming cancellation
        """
        operation = self.pending_confirmation.context.operation.value
        entity_type = self.pending_confirmation.context.entity_type.value
        operation_context = self.pending_confirmation.context
        self.pending_confirmation = None

        cancellation_message = f"{Fore.GREEN}✓ Cancelled {operation} {entity_type} operation{Style.RESET_ALL}"

        return ParsedIntent(
            intent_type="COMMAND",
            operation_context=operation_context,
            original_message="cancel",
            confidence=1.0,
            requires_execution=False,
            metadata={
                'cancelled': True,
                'operation': operation,
                'entity_type': entity_type,
                'cancellation_message': cancellation_message
            }
        )

    def _execute_with_retry(
        self,
        operation_context: OperationContext,
        project_id: int,
        confirmed: bool = False,
        max_retries: int = 3
    ) -> ExecutionResult:
        """Execute command with automatic retry for transient failures.

        Args:
            operation_context: OperationContext for the command
            project_id: Project ID
            confirmed: Whether operation is confirmed (for UPDATE/DELETE)
            max_retries: Maximum number of retry attempts

        Returns:
            ExecutionResult from successful execution or final attempt

        Example:
            >>> result = processor._execute_with_retry(context, project_id=1)
        """
        retryable_errors = [
            'timeout',
            'connection',
            'temporary',
            'lock',
            'busy',
        ]

        result = None
        for attempt in range(max_retries):
            try:
                result = self.command_executor.execute(
                    operation_context,
                    project_id=project_id,
                    confirmed=confirmed
                )

                # Success or non-retryable failure
                if result.success or not self._is_retryable(result, retryable_errors):
                    return result

                # Wait before retry (exponential backoff)
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # 1s, 2s, 4s
                    logger.info(f"Retrying command (attempt {attempt + 2}/{max_retries})")
                    time.sleep(wait_time)

            except Exception as e:
                if attempt == max_retries - 1:
                    # Re-raise on final attempt
                    raise
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                # Wait before retry
                wait_time = 2 ** attempt
                time.sleep(wait_time)

        # Return last result
        return result

    def _is_retryable(self, result: ExecutionResult, retryable_keywords: List[str]) -> bool:
        """Check if error is retryable based on error message.

        Args:
            result: ExecutionResult to check
            retryable_keywords: List of keywords indicating retryable errors

        Returns:
            True if error appears to be retryable

        Example:
            >>> is_retry = processor._is_retryable(result, ['timeout', 'lock'])
        """
        if not result.errors:
            return False

        error_msg = result.errors[0].lower()
        return any(keyword in error_msg for keyword in retryable_keywords)

    def _show_help(self) -> ParsedIntent:
        """Show general help message (ADR-017).

        Returns:
            ParsedIntent with help text in question_context

        Example:
            >>> parsed_intent = processor._show_help()
            >>> print(parsed_intent.question_context['answer'])  # Shows command examples
        """
        help_text = f"""
{Fore.CYAN}═══ Obra Natural Language Commands ═══{Style.RESET_ALL}

{Fore.YELLOW}Creating Entities:{Style.RESET_ALL}
  • create project 'name'
  • create epic for [description]
  • create story in epic <id>
  • create task with priority HIGH
  • create milestone 'name'

{Fore.YELLOW}Querying:{Style.RESET_ALL}
  • list projects
  • show all epics
  • list tasks for story 5
  • show project status
  • show milestone progress

{Fore.YELLOW}Updating:{Style.RESET_ALL}
  • update project 5 status to completed
  • change task 3 priority to LOW
  • mark epic 2 as blocked
  • update story 7 description

{Fore.YELLOW}Deleting:{Style.RESET_ALL}
  • delete project 3
  • remove task 7
  • delete epic 5

{Fore.CYAN}Entity-Specific Help:{Style.RESET_ALL}
  Type 'help <entity>' for more details:
  • help project
  • help epic
  • help story
  • help task
  • help milestone

{Fore.GREEN}Tips:{Style.RESET_ALL}
  • Use project/epic/story/task IDs (#5) or names ('My Project')
  • Priority: 1-10 or HIGH/MEDIUM/LOW
  • Status: PENDING/RUNNING/COMPLETED/BLOCKED/READY
  • Type 'yes' or 'no' to confirm destructive operations
"""
        return ParsedIntent(
            intent_type="QUESTION",
            operation_context=None,
            original_message="help",
            confidence=1.0,
            requires_execution=False,
            question_context={
                'question': "help",
                'question_type': 'help',
                'answer': help_text
            },
            metadata={'help_type': 'general'}
        )

    def _show_entity_help(self, entity_type: str) -> ParsedIntent:
        """Show entity-specific help (ADR-017).

        Args:
            entity_type: Entity type (project, epic, story, task, milestone)

        Returns:
            ParsedIntent with entity-specific help in question_context

        Example:
            >>> parsed_intent = processor._show_entity_help('epic')
        """
        help_map = {
            'project': f"""
{Fore.CYAN}═══ Project Commands ═══{Style.RESET_ALL}

{Fore.YELLOW}Create:{Style.RESET_ALL}
  • create project 'My New Project'
  • create project for mobile app

{Fore.YELLOW}Query:{Style.RESET_ALL}
  • list projects
  • show all projects
  • show project 5 status

{Fore.YELLOW}Update:{Style.RESET_ALL}
  • update project 5 status to completed
  • mark project 'Mobile App' as inactive

{Fore.YELLOW}Delete:{Style.RESET_ALL}
  • delete project 3
  • remove project 'Old Project'
""",
            'epic': f"""
{Fore.CYAN}═══ Epic Commands ═══{Style.RESET_ALL}

{Fore.YELLOW}Create:{Style.RESET_ALL}
  • create epic for user authentication
  • add epic 'Payment System' to project 1

{Fore.YELLOW}Query:{Style.RESET_ALL}
  • list epics
  • show all epics
  • list epics for project 1

{Fore.YELLOW}Update:{Style.RESET_ALL}
  • update epic 3 status to blocked
  • mark epic 'Auth System' as completed

{Fore.YELLOW}Delete:{Style.RESET_ALL}
  • delete epic 5
""",
            'story': f"""
{Fore.CYAN}═══ Story Commands ═══{Style.RESET_ALL}

{Fore.YELLOW}Create:{Style.RESET_ALL}
  • create story in epic 5
  • add story 'User Login' for epic 3

{Fore.YELLOW}Query:{Style.RESET_ALL}
  • list stories
  • show stories for epic 5

{Fore.YELLOW}Update:{Style.RESET_ALL}
  • update story 7 priority to high
  • mark story 2 as completed

{Fore.YELLOW}Delete:{Style.RESET_ALL}
  • delete story 4
""",
            'task': f"""
{Fore.CYAN}═══ Task Commands ═══{Style.RESET_ALL}

{Fore.YELLOW}Create:{Style.RESET_ALL}
  • create task with priority HIGH
  • add task 'Write tests' in story 3

{Fore.YELLOW}Query:{Style.RESET_ALL}
  • list tasks
  • show tasks for story 5
  • show my tasks

{Fore.YELLOW}Update:{Style.RESET_ALL}
  • update task 10 status to running
  • change task 5 priority to LOW

{Fore.YELLOW}Delete:{Style.RESET_ALL}
  • delete task 7
""",
            'milestone': f"""
{Fore.CYAN}═══ Milestone Commands ═══{Style.RESET_ALL}

{Fore.YELLOW}Create:{Style.RESET_ALL}
  • create milestone 'MVP Release'
  • add milestone for epic completion

{Fore.YELLOW}Query:{Style.RESET_ALL}
  • list milestones
  • show milestone status
  • check milestone 3 progress
""",
        }

        entity_help = help_map.get(entity_type)
        if entity_help:
            return ParsedIntent(
                intent_type="QUESTION",
                operation_context=None,
                original_message=f"help {entity_type}",
                confidence=1.0,
                requires_execution=False,
                question_context={
                    'question': f"help {entity_type}",
                    'question_type': 'help',
                    'answer': entity_help,
                    'entity_type': entity_type
                },
                metadata={'help_type': 'entity', 'entity_type': entity_type}
            )
        else:
            # Unknown entity type
            error_message = (
                f"{Fore.YELLOW}Unknown entity type '{entity_type}'{Style.RESET_ALL}\n"
                f"Available: project, epic, story, task, milestone\n"
                f"Type 'help' for general help"
            )
            return ParsedIntent(
                intent_type="QUESTION",
                operation_context=None,
                original_message=f"help {entity_type}",
                confidence=1.0,
                requires_execution=False,
                question_context={
                    'question': f"help {entity_type}",
                    'question_type': 'help',
                    'answer': error_message,
                    'error': True
                },
                metadata={'help_type': 'entity', 'entity_type': entity_type, 'unknown_entity': True}
            )

    def _update_conversation_context(
        self,
        message: str,
        intent: str,
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update conversation history with new turn.

        Args:
            message: User message
            intent: Classified intent
            result: Processing result

        Returns:
            Updated context
        """
        turn = {
            'message': message,
            'intent': intent,
            'result': result
        }

        self.conversation_history.append(turn)

        # Trim to max_context_turns
        if len(self.conversation_history) > self.max_context_turns:
            self.conversation_history = self.conversation_history[-self.max_context_turns:]

        return {
            'conversation_turns': len(self.conversation_history),
            'last_turn': turn
        }

    def clear_context(self) -> None:
        """Clear conversation context/history."""
        self.conversation_history = []
        logger.info("Conversation context cleared")

    def get_context_summary(self) -> Dict[str, Any]:
        """Get summary of current conversation context.

        Returns:
            Context summary with turn count and recent history
        """
        return {
            'total_turns': len(self.conversation_history),
            'recent_intents': [
                turn['intent'] for turn in self.conversation_history[-5:]
            ],
            'recent_messages': [
                turn['message'][:50] for turn in self.conversation_history[-3:]
            ]
        }
