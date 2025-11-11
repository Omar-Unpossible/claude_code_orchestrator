"""Natural Language Command Processor.

This module orchestrates the entire NL command pipeline:
- Intent classification (COMMAND, QUESTION, CLARIFICATION_NEEDED)
- Entity extraction with schema awareness
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
    >>> response = processor.process("Create an epic for user authentication")
    >>> print(response.response)  # Formatted response
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from core.state import StateManager
from core.config import Config
from plugins.base import LLMPlugin
from nl.intent_classifier import IntentClassifier
from nl.entity_extractor import EntityExtractor
from nl.command_validator import CommandValidator
from nl.command_executor import CommandExecutor
from nl.response_formatter import ResponseFormatter

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
        execution_result: Optional execution result details
    """
    response: str
    intent: str
    success: bool
    updated_context: Dict[str, Any] = field(default_factory=dict)
    forwarded_to_claude: bool = False
    execution_result: Optional[Dict[str, Any]] = None


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

        # Get schema path from config or use default
        schema_path = config.get('nl_commands.schema_path', 'src/nl/schemas/obra_schema.json')
        self.entity_extractor = EntityExtractor(
            llm_plugin=llm_plugin,
            schema_path=schema_path
        )

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
        """Handle COMMAND intent through extraction → validation → execution.

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
            # Step 2: Extract entities
            extracted = self.entity_extractor.extract(message, intent_result.intent)
            logger.info(
                f"Extracted {len(extracted.entities)} {extracted.entity_type}(s) "
                f"(confidence={extracted.confidence:.2f})"
            )

            # Step 3: Validate entities
            validation_result = self.command_validator.validate(extracted)

            if not validation_result.valid:
                # Validation failed - return error with suggestions
                error_msg = '; '.join(validation_result.errors)
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

            # Step 4: Execute validated command
            execution_result = self.command_executor.execute(
                validation_result.validated_command,
                project_id=project_id,
                confirmed=confirmed
            )

            # Step 5: Format response
            response = self.response_formatter.format(
                execution_result,
                intent='COMMAND'
            )

            # Update conversation context
            updated_context = self._update_conversation_context(
                message,
                intent_result.intent,
                {
                    'execution_success': execution_result.success,
                    'created_ids': execution_result.created_ids,
                    'entity_type': extracted.entity_type
                }
            )

            return NLResponse(
                response=response,
                intent='COMMAND',
                success=execution_result.success,
                updated_context=updated_context,
                execution_result={
                    'created_ids': execution_result.created_ids,
                    'entity_type': extracted.entity_type
                }
            )

        except Exception as e:
            logger.exception(f"Command handling failed: {e}")
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

    def _handle_question(
        self,
        message: str,
        intent_result: Any,
        context: Dict[str, Any]
    ) -> NLResponse:
        """Handle QUESTION intent - forward to Claude Code or provide info.

        Args:
            message: User message
            intent_result: Intent classification result
            context: Conversation context

        Returns:
            NLResponse indicating question forwarding
        """
        # Check if fallback_to_info is enabled
        fallback_to_info = self.config.get('nl_commands.fallback_to_info', True)

        if fallback_to_info:
            # Forward to Claude Code for informational response
            response = (
                f"Forwarding question to Claude Code: {message}\n"
                f"(This would integrate with Claude Code's conversational interface)"
            )

            updated_context = self._update_conversation_context(
                message,
                intent_result.intent,
                {'forwarded': True}
            )

            return NLResponse(
                response=response,
                intent='QUESTION',
                success=True,
                updated_context=updated_context,
                forwarded_to_claude=True
            )
        else:
            # Suggest rephrasing as command
            response = (
                "I can help with commands like 'create epic' or 'list tasks'. "
                "Could you rephrase as an action?"
            )
            return NLResponse(
                response=response,
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
