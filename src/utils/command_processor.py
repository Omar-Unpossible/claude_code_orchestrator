"""Command processor for interactive mode.

This module provides command parsing and execution for interactive orchestration,
allowing users to inject context, override decisions, and control execution flow.

v1.5.0: Natural language defaults to orchestrator (no slash prefix needed).
All system commands require '/' prefix as first character.

Part of Interactive Streaming Interface (Phase 2) + NL Commands (v1.3).
"""

import logging
from typing import Dict, Callable, Tuple, Any, Optional, TYPE_CHECKING

# Avoid circular import
if TYPE_CHECKING:
    from src.orchestrator import Orchestrator

logger = logging.getLogger(__name__)


class CommandValidationError(Exception):
    """Raised when slash command is invalid.

    Attributes:
        message: Error message
        available_commands: List of valid slash commands
    """

    def __init__(self, message: str, available_commands: list):
        super().__init__(message)
        self.message = message
        self.available_commands = available_commands

# Maximum length for injected text (~1250 tokens)
MAX_INJECTED_TEXT_LENGTH = 5000

# Valid decision types that can be overridden
VALID_DECISIONS = ['proceed', 'retry', 'clarify', 'escalate', 'checkpoint']

# Help text for all commands (v1.5.0)
HELP_TEXT = """
Interactive Mode Commands (v1.5.0):

DEFAULT BEHAVIOR:
  <natural text>              Send message to orchestrator (no prefix needed)

SLASH COMMANDS (must start with '/'):
  /help                       Show this help message
  /status                     Show current task status, iteration, quality score
  /pause                      Pause execution (before next checkpoint)
  /resume                     Resume paused execution
  /stop                       Stop execution gracefully (completes turn, saves state)
  /to-impl <message>          Send message to implementer (Claude Code)
                              Aliases: /to-claude, /to-implementer
                              Max 5000 chars. Example: /to-impl Add unit tests
  /override-decision <choice> Override orchestrator's decision
                              Valid: proceed, retry, clarify, escalate, checkpoint

EXAMPLES:
  Be more lenient with quality scores                 → Sent to orchestrator
  Should I retry or escalate this task?               → Sent to orchestrator
  /to-impl fix the type error in src/auth.py          → Sent to Claude
  /status                                              → Show status
  /pause                                               → Pause before next checkpoint

NOTE: Messages starting with '/' must be valid commands. To send natural
      language to the orchestrator, do not start with '/'.

ORCHESTRATOR CAPABILITIES:
  Natural language messages can:
  - Provide validation guidance (affects quality scoring)
  - Request decision advice (get recommendations)
  - Ask for feedback (orchestrator analyzes and provides suggestions)
  - General orchestration questions
"""


class CommandProcessor:
    """Process user commands during interactive orchestration.

    Parses and executes slash commands (/pause, /resume, etc.) and routes
    non-slash-command input through the Natural Language Command Interface.

    Thread-safe for concurrent access from input thread.

    Attributes:
        orchestrator: Reference to Orchestrator instance
        commands: Registry of slash commands mapped to handlers
        nl_processor: Optional NLCommandProcessor for natural language input

    Example:
        >>> processor = CommandProcessor(orchestrator)
        >>> # Slash command
        >>> result = processor.execute_command('/pause')
        >>> print(result['message'])
        'Execution will pause after current turn'
        >>> # Natural language command
        >>> result = processor.execute_command('Create an epic for user auth')
        >>> print(result['message'])
        '✓ Created Epic #5: User Auth'
    """

    def __init__(self, orchestrator: 'Orchestrator'):
        """Initialize command processor.

        Args:
            orchestrator: Orchestrator instance to control
        """
        self.orchestrator = orchestrator
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # Register commands (with aliases for backward compatibility)
        self.commands: Dict[str, Callable] = {
            '/pause': self._pause,
            '/resume': self._resume,
            '/to-impl': self._to_impl,          # Primary
            '/to-orch': self._to_orch,          # Primary
            '/to-claude': self._to_impl,        # Alias (backward compat)
            '/to-obra': self._to_orch,          # Alias (backward compat)
            '/to-implementer': self._to_impl,   # Formal alias
            '/to-orchestrator': self._to_orch,  # Formal alias
            '/override-decision': self._override_decision,
            '/status': self._status,
            '/help': self._help,
            '/stop': self._stop,
        }

        # Initialize NL processor if enabled
        self.nl_processor: Optional[Any] = None
        self._initialize_nl_processor()

    def parse_command(self, input_str: str) -> Tuple[str, Dict[str, Any]]:
        """Parse command string into command name and arguments.

        Args:
            input_str: User input string

        Returns:
            Tuple of (command_name, arguments_dict)

        Example:
            >>> parse_command('/to-claude Add tests')
            ('/to-claude', {'message': 'Add tests'})
        """
        input_str = input_str.strip()

        if not input_str:
            return ('', {})

        # Split into command and args
        parts = input_str.split(maxsplit=1)
        command = parts[0].lower()
        args_str = parts[1] if len(parts) > 1 else ''

        # Build args dict based on command
        args: Dict[str, Any] = {}

        if command in ['/to-impl', '/to-orch', '/to-implementer', '/to-orchestrator',
                       '/to-claude', '/to-obra']:  # Include all aliases
            args['message'] = args_str
        elif command == '/override-decision':
            args['decision'] = args_str.lower()
        elif command == '/help':
            args['command'] = args_str.lower() if args_str else None

        return (command, args)

    def _initialize_nl_processor(self) -> None:
        """Initialize NL command processor if enabled in config."""
        try:
            # Check if NL commands are enabled
            config = getattr(self.orchestrator, 'config', None)
            if not config:
                self.logger.debug("No config available, NL processor disabled")
                return

            nl_enabled = config.get('nl_commands.enabled', False)
            if not nl_enabled:
                self.logger.info("NL commands disabled in config")
                return

            # Import here to avoid circular dependencies
            from nl.nl_command_processor import NLCommandProcessor
            from plugins.registry import LLMRegistry

            # Get LLM plugin
            llm_type = config.get('nl_commands.llm_provider') or config.get('llm.type', 'ollama')
            llm_plugin = LLMRegistry.get(llm_type)()

            # Get StateManager
            state_manager = getattr(self.orchestrator, 'state_manager', None)
            if not state_manager:
                self.logger.warning("No StateManager available, NL processor disabled")
                return

            # Initialize NL processor
            confidence_threshold = config.get('nl_commands.confidence_threshold', 0.7)
            max_context_turns = config.get('nl_commands.max_context_turns', 10)

            self.nl_processor = NLCommandProcessor(
                llm_plugin=llm_plugin,
                state_manager=state_manager,
                config=config,
                confidence_threshold=confidence_threshold,
                max_context_turns=max_context_turns
            )

            self.logger.info("NL command processor initialized successfully")

        except Exception as e:
            self.logger.warning(f"Failed to initialize NL processor: {e}")
            self.nl_processor = None

    def execute_command(self, input_str: str) -> Dict[str, Any]:
        """Execute a command (slash command or natural language).

        Routes input to appropriate handler (v1.5.0 behavior):
        - Slash commands (/pause, /resume, etc.) → slash command handler
        - Non-slash commands → Send to orchestrator (default)

        Args:
            input_str: User input string

        Returns:
            Result dict with 'success' or 'error' key and 'message'

        Raises:
            CommandValidationError: If slash command is invalid

        Example:
            >>> # Slash command
            >>> result = processor.execute_command('/pause')
            >>> if 'success' in result:
            ...     print(result['message'])

            >>> # Natural language (new default behavior)
            >>> result = processor.execute_command('Be more lenient with quality')
            >>> print(result['message'])
        """
        input_str = input_str.strip()

        if not input_str:
            return {'error': 'Empty command'}

        # Check if it's a slash command
        if input_str.startswith('/'):
            return self._execute_slash_command(input_str)
        else:
            # Default: Send to orchestrator
            return self._send_to_orchestrator(input_str)

    def _execute_slash_command(self, input_str: str) -> Dict[str, Any]:
        """Execute slash command with validation.

        Args:
            input_str: Slash command string

        Returns:
            Result dict with 'success' or 'error' key and 'message'

        Raises:
            CommandValidationError: If slash command is invalid
        """
        # Remove leading slash and parse
        parts = input_str[1:].split(maxsplit=1)

        if not parts or not parts[0]:
            raise CommandValidationError(
                "Invalid command: slash with no command name",
                available_commands=list(self.commands.keys())
            )

        command = '/' + parts[0].lower()
        args_str = parts[1] if len(parts) > 1 else ''

        if command not in self.commands:
            raise CommandValidationError(
                f"Unknown command: {command}",
                available_commands=list(self.commands.keys())
            )

        # Build args dict based on command (reuse existing logic)
        args: Dict[str, Any] = {}

        if command in ['/to-impl', '/to-orch', '/to-implementer', '/to-orchestrator',
                       '/to-claude', '/to-obra']:
            args['message'] = args_str
        elif command == '/override-decision':
            args['decision'] = args_str.lower()
        elif command == '/help':
            args['command'] = args_str.lower() if args_str else None

        try:
            return self.commands[command](args)
        except Exception as e:
            self.logger.error(f"Command execution failed: {e}", exc_info=True)
            return {
                'error': f'Command failed: {str(e)}'
            }

    def _send_to_orchestrator(self, message: str) -> Dict[str, Any]:
        """Send natural language message to orchestrator.

        This is the default action for non-slash input (v1.5.0).

        Args:
            message: Natural language text from user

        Returns:
            Result dict with orchestrator response
        """
        self.logger.debug(f"Routing natural language to orchestrator: {message[:50]}...")

        # Reuse existing _to_orch logic
        return self._to_orch({'message': message})

    def _execute_nl_command(self, input_str: str) -> Dict[str, Any]:
        """Execute natural language command via NL processor.

        NOTE: This method is deprecated in v1.5.0. Natural language input
        now routes to orchestrator by default. NL processor functionality
        is preserved for backward compatibility if explicitly enabled.

        Args:
            input_str: Natural language input

        Returns:
            Result dict with 'success' or 'error' key and 'message'
        """
        try:
            # Get project_id from orchestrator if available
            project_id = getattr(self.orchestrator, 'current_project_id', None)

            # Process through NL pipeline
            nl_response = self.nl_processor.process(
                message=input_str,
                context={},
                project_id=project_id
            )

            # Convert NLResponse to command result format
            result = {
                'message': nl_response.response,
                'intent': nl_response.intent
            }

            if nl_response.success:
                result['success'] = True
                if nl_response.execution_result:
                    result['execution_result'] = nl_response.execution_result
            else:
                result['error'] = nl_response.response

            return result

        except Exception as e:
            self.logger.exception(f"NL command execution failed: {e}")
            return {
                'error': f'NL processing failed: {str(e)}'
            }

    def _pause(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Pause execution after current turn.

        Args:
            args: Command arguments (unused)

        Returns:
            Success result
        """
        self.orchestrator.paused = True
        return {
            'success': True,
            'message': 'Execution will pause after current turn completes'
        }

    def _resume(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Resume paused execution.

        Args:
            args: Command arguments (unused)

        Returns:
            Success result
        """
        if not self.orchestrator.paused:
            return {
                'error': 'Execution is not paused',
                'message': 'Use /pause to pause execution first'
            }

        self.orchestrator.paused = False
        return {
            'success': True,
            'message': 'Execution resumed'
        }

    def _to_impl(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Inject message into implementer's next prompt (last-wins policy).

        Args:
            args: Command arguments with 'message' key

        Returns:
            Success result or error

        Example:
            >>> processor.execute_command('/to-impl Add unit tests for validation logic')
            {'success': True, 'message': 'Will send to implementer: Add unit tests for validation logic'}
        """
        message = args.get('message', '').strip()

        # Validation
        if not message:
            return {'error': '/to-impl requires a message'}

        if len(message) > MAX_INJECTED_TEXT_LENGTH:
            return {
                'error': f'Message too long ({len(message)} chars, max {MAX_INJECTED_TEXT_LENGTH})'
            }

        # Warn if overwriting existing context
        if self.orchestrator.injected_context.get('to_impl'):
            self.logger.warning(
                "Replacing previous /to-impl message with new one (last-wins)"
            )

        # Store with both new and legacy keys (for transition period)
        self.orchestrator.injected_context['to_impl'] = message
        self.orchestrator.injected_context['to_claude'] = message  # Legacy key for compatibility

        # Show preview (first 50 chars)
        preview = message[:50] + '...' if len(message) > 50 else message

        return {
            'success': True,
            'message': f'Will send to implementer: {preview}'
        }

    def _to_orch(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Send message to orchestrator (validation LLM).

        Message behavior depends on content:
        - Validation guidance: Injected into quality scoring prompt
        - Decision hints: Affects decision thresholds temporarily
        - Feedback requests: Orch generates feedback sent to implementer

        Args:
            args: Command arguments with 'message' key

        Returns:
            Success result or error

        Examples:
            >>> # Validation guidance
            >>> processor.execute_command('/to-orch Be more lenient with code quality')

            >>> # Decision hint
            >>> processor.execute_command('/to-orch Accept this even if quality is borderline')

            >>> # Feedback request
            >>> processor.execute_command('/to-orch Review the code and suggest 3 improvements')
        """
        message = args.get('message', '').strip()

        # Validation
        if not message:
            return {'error': '/to-orch requires a message'}

        if len(message) > MAX_INJECTED_TEXT_LENGTH:
            return {
                'error': f'Message too long ({len(message)} chars, max {MAX_INJECTED_TEXT_LENGTH})'
            }

        # Warn if overwriting existing context
        if self.orchestrator.injected_context.get('to_orch'):
            self.logger.warning(
                "Replacing previous /to-orch message with new one (last-wins)"
            )

        # Store with both new and legacy keys (for transition period)
        self.orchestrator.injected_context['to_orch'] = message
        self.orchestrator.injected_context['to_obra'] = message  # Legacy key for compatibility

        # Classify message intent (simple heuristics)
        message_lower = message.lower()
        intent = 'general'

        if any(word in message_lower for word in ['quality', 'score', 'validate', 'lenient', 'strict']):
            intent = 'validation_guidance'
        elif any(word in message_lower for word in ['accept', 'proceed', 'approve', 'override']):
            intent = 'decision_hint'
        elif any(word in message_lower for word in ['review', 'analyze', 'suggest', 'feedback', 'tell']):
            intent = 'feedback_request'

        # Store intent for downstream use
        self.orchestrator.injected_context['to_orch_intent'] = intent

        # Show preview with detected intent
        preview = message[:50] + '...' if len(message) > 50 else message
        intent_label = {
            'validation_guidance': '→ Will influence quality scoring',
            'decision_hint': '→ Will affect decision thresholds',
            'feedback_request': '→ Will generate feedback for implementer',
            'general': '→ General guidance'
        }[intent]

        return {
            'success': True,
            'message': f'Will send to orchestrator: {preview}\n{intent_label}'
        }

    def _override_decision(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Override Obra's current decision.

        Args:
            args: Command arguments with 'decision' key

        Returns:
            Success result or error
        """
        decision = args.get('decision', '').strip().lower()

        # Validation
        if not decision:
            return {
                'error': '/override-decision requires a decision type',
                'message': f'Valid decisions: {", ".join(VALID_DECISIONS)}'
            }

        if decision not in VALID_DECISIONS:
            return {
                'error': f'Invalid decision: {decision}',
                'message': f'Valid decisions: {", ".join(VALID_DECISIONS)}'
            }

        self.orchestrator.injected_context['override_decision'] = decision

        return {
            'success': True,
            'message': f'Will override decision to: {decision.upper()}'
        }

    def _status(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Show current task status and metrics.

        Args:
            args: Command arguments (unused)

        Returns:
            Success result with status information
        """
        # Gather status information from orchestrator
        status_lines = ['📊 Task Status:']

        if hasattr(self.orchestrator, 'current_task_id'):
            status_lines.append(f'   Task ID: {self.orchestrator.current_task_id}')

        if hasattr(self.orchestrator, 'current_iteration'):
            max_turns = getattr(self.orchestrator, 'max_turns', '?')
            status_lines.append(f'   Iteration: {self.orchestrator.current_iteration}/{max_turns}')

        if hasattr(self.orchestrator, 'latest_quality_score'):
            status_lines.append(f'   Quality: {self.orchestrator.latest_quality_score:.2f}')

        if hasattr(self.orchestrator, 'latest_confidence'):
            status_lines.append(f'   Confidence: {self.orchestrator.latest_confidence:.2f}')

        # Add pause status
        if self.orchestrator.paused:
            status_lines.append('   Status: ⏸️  PAUSED')
        else:
            status_lines.append('   Status: ▶️  RUNNING')

        # Add injected context status
        if self.orchestrator.injected_context:
            status_lines.append('   Pending commands:')
            for key, value in self.orchestrator.injected_context.items():
                preview = str(value)[:30] + '...' if len(str(value)) > 30 else str(value)
                status_lines.append(f'     - {key}: {preview}')

        return {
            'success': True,
            'message': '\n'.join(status_lines)
        }

    def _help(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Show help for all commands or specific command.

        Args:
            args: Command arguments with optional 'command' key

        Returns:
            Success result with help text
        """
        # v1.5.0: HELP_TEXT is now a single formatted string
        return {
            'success': True,
            'message': HELP_TEXT
        }

    def _stop(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Stop execution gracefully.

        Args:
            args: Command arguments (unused)

        Returns:
            Success result
        """
        self.orchestrator.stop_requested = True
        return {
            'success': True,
            'message': 'Stopping after current turn completes...'
        }
