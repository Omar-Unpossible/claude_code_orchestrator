"""Command processor for interactive mode.

This module provides command parsing and execution for interactive orchestration,
allowing users to inject context, override decisions, and control execution flow.

Part of Interactive Streaming Interface (Phase 2).
"""

import logging
from typing import Dict, Callable, Tuple, Any, Optional, TYPE_CHECKING

# Avoid circular import
if TYPE_CHECKING:
    from src.orchestrator import Orchestrator

logger = logging.getLogger(__name__)

# Maximum length for injected text (~1250 tokens)
MAX_INJECTED_TEXT_LENGTH = 5000

# Valid decision types that can be overridden
VALID_DECISIONS = ['proceed', 'retry', 'clarify', 'escalate', 'checkpoint']

# Help text for all commands
HELP_TEXT = {
    '/pause': 'Pause execution after current turn. Resume with /resume.',
    '/resume': 'Resume paused execution.',
    '/to-impl': 'Send message to implementer (Claude Code). Aliases: /to-claude, /to-implementer. Max 5000 chars. Example: /to-impl Add unit tests',
    '/to-orch': '''Send message to orchestrator (Qwen/Codex). Aliases: /to-obra, /to-orchestrator. Purpose depends on message content. Examples:
  - Validation guidance: /to-orch Be more lenient with quality scores
  - Decision override: /to-orch Accept this response even if quality is low
  - Feedback request: /to-orch Analyze this code and suggest improvements to implementer''',
    '/override-decision': 'Override current decision. Valid: proceed, retry, clarify, escalate, checkpoint. Example: /override-decision retry',
    '/status': 'Show current task status, iteration, quality score, token usage.',
    '/help': 'Show this help message or help for specific command.',
    '/stop': 'Stop execution gracefully (completes current turn, saves state).',

    # Deprecated (show but indicate aliases)
    '/to-claude': 'DEPRECATED: Use /to-impl instead. Alias for /to-impl.',
    '/to-obra': 'DEPRECATED: Use /to-orch instead. Alias for /to-orch.',
}


class CommandProcessor:
    """Process user commands during interactive orchestration.

    Parses and executes commands like /pause, /resume, /to-claude, /override-decision, etc.
    Thread-safe for concurrent access from input thread.

    Attributes:
        orchestrator: Reference to Orchestrator instance
        commands: Registry of available commands mapped to handlers

    Example:
        >>> processor = CommandProcessor(orchestrator)
        >>> result = processor.execute_command('/pause')
        >>> print(result['message'])
        'Execution will pause after current turn'
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

    def execute_command(self, input_str: str) -> Dict[str, Any]:
        """Execute a command.

        Args:
            input_str: User input string

        Returns:
            Result dict with 'success' or 'error' key and 'message'

        Example:
            >>> result = processor.execute_command('/pause')
            >>> if 'success' in result:
            ...     print(result['message'])
        """
        command, args = self.parse_command(input_str)

        if not command:
            return {'error': 'Empty command'}

        if command not in self.commands:
            return {
                'error': f'Unknown command: {command}',
                'message': 'Type /help for available commands'
            }

        try:
            return self.commands[command](args)
        except Exception as e:
            self.logger.error(f"Command execution failed: {e}", exc_info=True)
            return {
                'error': f'Command failed: {str(e)}'
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
        command = args.get('command')

        if command:
            # Show help for specific command
            if not command.startswith('/'):
                command = '/' + command

            if command in HELP_TEXT:
                return {
                    'success': True,
                    'message': f'{command}: {HELP_TEXT[command]}'
                }
            else:
                return {
                    'error': f'Unknown command: {command}',
                    'message': 'Type /help for all commands'
                }
        else:
            # Show help for all commands
            help_lines = ['Available commands:']
            for cmd, help_text in HELP_TEXT.items():
                help_lines.append(f'  {cmd}: {help_text}')

            return {
                'success': True,
                'message': '\n'.join(help_lines)
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
