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
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from core.state import StateManager
from core.config import Config
from plugins.base import LLMPlugin
from nl.intent_classifier import IntentClassifier
from nl.command_validator import CommandValidator
from nl.command_executor import CommandExecutor, ExecutionResult
from nl.response_formatter import ResponseFormatter
from src.nl.types import OperationContext, OperationType, EntityType, QueryType

# New ADR-016 components
from src.nl.operation_classifier import OperationClassifier
from src.nl.entity_type_classifier import EntityTypeClassifier
from src.nl.entity_identifier_extractor import EntityIdentifierExtractor
from src.nl.parameter_extractor import ParameterExtractor
from src.nl.question_handler import QuestionHandler

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
    ) -> NLResponse:
        """Process natural language message through pipeline.

        Args:
            message: User's natural language message
            context: Optional conversation context
            project_id: Optional project ID (uses default if not specified)
            confirmed: True if user confirmed destructive operation

        Returns:
            NLResponse with formatted response and metadata

        Example:
            >>> response = processor.process("Create epic for user auth")
            >>> if response.success:
            ...     print(response.response)
        """
        if not message or not message.strip():
            return NLResponse(
                response="Please provide a message",
                intent="INVALID",
                success=False
            )

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
                return self._handle_clarification(message, intent_result, conv_context)
            elif intent_result.intent == 'QUESTION':
                return self._handle_question(message, intent_result, conv_context)
            elif intent_result.intent == 'COMMAND':
                return self._handle_command(
                    message,
                    intent_result,
                    conv_context,
                    project_id,
                    confirmed
                )
            else:
                logger.warning(f"Unknown intent: {intent_result.intent}")
                return NLResponse(
                    response=f"Unrecognized intent: {intent_result.intent}",
                    intent=intent_result.intent,
                    success=False
                )

        except Exception as e:
            logger.exception(f"NL processing failed: {e}")
            return NLResponse(
                response=f"Processing error: {str(e)}",
                intent="ERROR",
                success=False
            )

    def _handle_command(
        self,
        message: str,
        intent_result: Any,
        context: Dict[str, Any],
        project_id: Optional[int],
        confirmed: bool
    ) -> NLResponse:
        """Handle COMMAND intent through 5-stage pipeline (ADR-016).

        Pipeline stages:
        1. OperationClassifier → OperationType (CREATE/UPDATE/DELETE/QUERY)
        2. EntityTypeClassifier → EntityType (project/epic/story/task/milestone)
        3. EntityIdentifierExtractor → identifier (name or ID)
        4. ParameterExtractor → parameters (status, priority, etc.)
        5. Build OperationContext → validate → execute

        Args:
            message: User message
            intent_result: Intent classification result
            context: Conversation context
            project_id: Optional project ID
            confirmed: User confirmation status

        Returns:
            NLResponse with execution results
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
                # Check for hierarchical keywords
                if any(keyword in message.lower() for keyword in ['workplan', 'hierarchy', 'hierarchical']):
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
                # Validation failed - return error with suggestions
                logger.warning(f"Validation failed: {validation_result.errors}")
                response = self.response_formatter._format_error(
                    type('ExecutionResult', (), {
                        'success': False,
                        'errors': validation_result.errors,
                        'results': {}
                    })()
                )

                # Update context with failed validation
                updated_context = self._update_conversation_context(
                    message,
                    intent_result.intent,
                    {'validation_failed': True, 'errors': validation_result.errors}
                )

                return NLResponse(
                    response=response,
                    intent='COMMAND',
                    success=False,
                    updated_context=updated_context
                )

            # Step 7: Execute validated command
            logger.debug(f"Step 7: Executing command")
            execution_result = self.command_executor.execute(
                operation_context,
                project_id=project_id,
                confirmed=confirmed
            )

            logger.info(
                f"Execution complete: success={execution_result.success}, "
                f"created_ids={execution_result.created_ids}"
            )

            # Step 8: Format response
            response = self.response_formatter.format(
                execution_result,
                intent='COMMAND',
                operation=operation_context.operation.value
            )

            # Update conversation context
            updated_context = self._update_conversation_context(
                message,
                intent_result.intent,
                {
                    'execution_success': execution_result.success,
                    'created_ids': execution_result.created_ids,
                    'entity_type': operation_context.entity_type.value,
                    'operation': operation_context.operation.value
                }
            )

            return NLResponse(
                response=response,
                intent='COMMAND',
                success=execution_result.success,
                updated_context=updated_context,
                execution_result=execution_result
            )

        except ValueError as e:
            # OperationContext validation error (e.g., UPDATE without identifier)
            logger.warning(f"OperationContext validation error: {e}")
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

        except Exception as e:
            logger.exception(f"Command handling failed at pipeline stage: {e}")
            error_response = self.response_formatter._format_error(
                type('ExecutionResult', (), {
                    'success': False,
                    'errors': [f"Pipeline error: {str(e)}"],
                    'results': {}
                })()
            )
            return NLResponse(
                response=error_response,
                intent='COMMAND',
                success=False
            )

    def _handle_question(
        self,
        message: str,
        intent_result: Any,
        context: Dict[str, Any]
    ) -> NLResponse:
        """Handle QUESTION intent via QuestionHandler (ADR-016).

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
            NLResponse with informational answer
        """
        try:
            logger.debug(f"Handling QUESTION: {message}")

            # Use QuestionHandler to process the question
            question_response = self.question_handler.handle(message)

            logger.info(
                f"Question handled: type={question_response.question_type.value}, "
                f"confidence={question_response.confidence:.2f}"
            )

            # Update conversation context
            updated_context = self._update_conversation_context(
                message,
                intent_result.intent,
                {
                    'question_type': question_response.question_type.value,
                    'entities': question_response.entities
                }
            )

            return NLResponse(
                response=question_response.answer,
                intent='QUESTION',
                success=True,
                updated_context=updated_context,
                forwarded_to_claude=False  # Handled internally
            )

        except Exception as e:
            logger.exception(f"Question handling failed: {e}")

            # Fallback behavior - suggest rephrasing as command
            fallback_response = (
                f"I couldn't answer that question: {str(e)}\n\n"
                f"Try rephrasing as a command like:\n"
                f"  • 'Show me tasks for project X'\n"
                f"  • 'List next steps'\n"
                f"  • 'What's the status of epic Y'"
            )

            return NLResponse(
                response=fallback_response,
                intent='QUESTION',
                success=False
            )

    def _handle_clarification(
        self,
        message: str,
        intent_result: Any,
        context: Dict[str, Any]
    ) -> NLResponse:
        """Handle CLARIFICATION_NEEDED intent - ask user for clarification.

        Args:
            message: User message
            intent_result: Intent classification result
            context: Conversation context

        Returns:
            NLResponse with clarification request
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

        response = self.response_formatter.format_clarification_request(
            "I'm not sure what you'd like to do. Did you mean:",
            suggestions=suggestions if suggestions else None
        )

        updated_context = self._update_conversation_context(
            message,
            intent_result.intent,
            {'clarification_requested': True}
        )

        return NLResponse(
            response=response,
            intent='CLARIFICATION_NEEDED',
            success=False,
            updated_context=updated_context
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
