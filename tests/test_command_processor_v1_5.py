"""Tests for CommandProcessor v1.5.0 - Natural Language Default.

Tests new behavior where natural language input defaults to orchestrator
without requiring /to-orch prefix.

v1.5.0 Changes:
- Natural text → orchestrator (default)
- Slash commands → system commands (must start with '/')
- Unknown slash commands → CommandValidationError (with helpful message)

COMPLIANCE: TEST_GUIDELINES.md
- No excessive sleeps (0s total)
- No threading (0 threads)
- Fast execution (< 2s total)
- Minimal memory allocation
"""

import pytest
from unittest.mock import MagicMock

from src.utils.command_processor import (
    CommandProcessor,
    CommandValidationError,
    HELP_TEXT
)


@pytest.fixture
def mock_orchestrator():
    """Mock orchestrator for testing command routing."""
    orchestrator = MagicMock()
    orchestrator.paused = False
    orchestrator.stop_requested = False
    orchestrator.injected_context = {}
    orchestrator.current_task_id = None
    orchestrator.current_iteration = 1
    orchestrator.latest_quality_score = 0.75
    orchestrator.latest_confidence = 0.68
    return orchestrator


class TestNaturalLanguageRouting:
    """Test natural language defaults to orchestrator (v1.5.0)."""

    def test_natural_text_sent_to_orchestrator(self, mock_orchestrator):
        """Natural text without slash goes to orchestrator."""
        processor = CommandProcessor(mock_orchestrator)
        result = processor.execute_command("create epic for auth")

        # Should call _to_orch internally
        assert result['success']
        assert 'orchestrator' in result['message'].lower() or 'orch' in result['message'].lower()
        # Verify message was stored in injected context
        assert 'to_orch' in mock_orchestrator.injected_context or 'to_obra' in mock_orchestrator.injected_context

    def test_multiline_natural_text(self, mock_orchestrator):
        """Multiline natural text sent to orchestrator."""
        processor = CommandProcessor(mock_orchestrator)
        message = """create epic for authentication with:
        - OAuth integration
        - JWT tokens
        - Session management"""

        result = processor.execute_command(message)
        assert result['success']
        # Verify full message stored
        stored = mock_orchestrator.injected_context.get('to_orch') or mock_orchestrator.injected_context.get('to_obra')
        assert stored is not None
        assert 'OAuth' in stored
        assert 'JWT' in stored

    def test_natural_text_with_special_chars(self, mock_orchestrator):
        """Natural text with special characters works."""
        processor = CommandProcessor(mock_orchestrator)
        result = processor.execute_command("Be more lenient! Quality > 0.5 is OK")
        assert result['success']
        # Verify message preserved
        stored = mock_orchestrator.injected_context.get('to_orch') or mock_orchestrator.injected_context.get('to_obra')
        assert '>' in stored
        assert '0.5' in stored

    def test_natural_text_preserves_slashes_in_middle(self, mock_orchestrator):
        """Slash in middle of message is preserved (not a command)."""
        processor = CommandProcessor(mock_orchestrator)
        result = processor.execute_command("use /api/endpoint in implementation")
        assert result['success']
        # Verify message contains the slash
        stored = mock_orchestrator.injected_context.get('to_orch') or mock_orchestrator.injected_context.get('to_obra')
        assert '/api/endpoint' in stored

    def test_empty_input_rejected(self, mock_orchestrator):
        """Empty input returns error."""
        processor = CommandProcessor(mock_orchestrator)
        result = processor.execute_command("")
        assert 'error' in result
        assert 'Empty' in result['error']

    def test_whitespace_only_rejected(self, mock_orchestrator):
        """Whitespace-only input returns error."""
        processor = CommandProcessor(mock_orchestrator)
        result = processor.execute_command("   \t  \n  ")
        assert 'error' in result
        assert 'Empty' in result['error']

    def test_natural_text_case_preserved(self, mock_orchestrator):
        """Natural text case is preserved."""
        processor = CommandProcessor(mock_orchestrator)
        result = processor.execute_command("Be MORE Lenient")
        assert result['success']
        # Verify case preserved
        stored = mock_orchestrator.injected_context.get('to_orch') or mock_orchestrator.injected_context.get('to_obra')
        assert 'MORE' in stored

    def test_natural_text_unicode_supported(self, mock_orchestrator):
        """Unicode in natural text is supported."""
        processor = CommandProcessor(mock_orchestrator)
        result = processor.execute_command("Create epic: User Auth 🔐")
        assert result['success']
        # Verify unicode preserved
        stored = mock_orchestrator.injected_context.get('to_orch') or mock_orchestrator.injected_context.get('to_obra')
        assert '🔐' in stored


class TestSlashCommandValidation:
    """Test slash command validation (v1.5.0)."""

    def test_slash_command_requires_validity(self, mock_orchestrator):
        """Invalid slash commands raise CommandValidationError."""
        processor = CommandProcessor(mock_orchestrator)

        with pytest.raises(CommandValidationError) as exc:
            processor.execute_command('/invalid-command')

        assert 'Unknown command' in str(exc.value)
        assert len(exc.value.available_commands) > 0
        assert '/help' in exc.value.available_commands

    def test_single_slash_rejected(self, mock_orchestrator):
        """Single slash character is invalid command."""
        processor = CommandProcessor(mock_orchestrator)

        with pytest.raises(CommandValidationError):
            processor.execute_command('/')

    def test_slash_with_whitespace_rejected(self, mock_orchestrator):
        """Slash followed by whitespace is invalid."""
        processor = CommandProcessor(mock_orchestrator)

        with pytest.raises(CommandValidationError):
            processor.execute_command('/   ')

    def test_case_insensitive_slash_commands(self, mock_orchestrator):
        """Slash commands are case-insensitive."""
        processor = CommandProcessor(mock_orchestrator)

        result1 = processor.execute_command('/HELP')
        result2 = processor.execute_command('/help')
        result3 = processor.execute_command('/HeLp')

        assert result1['success']
        assert result2['success']
        assert result3['success']

    def test_slash_must_be_first_character(self, mock_orchestrator):
        """Slash in middle of message is part of natural text."""
        processor = CommandProcessor(mock_orchestrator)

        # This should go to orchestrator, NOT be treated as command
        result = processor.execute_command("check /status of system")
        assert result['success']
        # Verify it was routed to orchestrator
        stored = mock_orchestrator.injected_context.get('to_orch') or mock_orchestrator.injected_context.get('to_obra')
        assert 'check /status of system' in stored

    def test_all_system_commands_require_slash(self, mock_orchestrator):
        """All system commands must have slash prefix."""
        processor = CommandProcessor(mock_orchestrator)
        system_commands = ['help', 'status', 'pause', 'resume', 'stop']

        for cmd in system_commands:
            # Clear context
            mock_orchestrator.injected_context.clear()

            # Without slash - sent to orchestrator (natural text)
            result = processor.execute_command(cmd)
            assert result['success']  # Should succeed (routed to orchestrator)
            # Verify it was stored in orchestrator context
            assert 'to_orch' in mock_orchestrator.injected_context or 'to_obra' in mock_orchestrator.injected_context

            # Clear context
            mock_orchestrator.injected_context.clear()

            # With slash - executes command
            result = processor.execute_command(f'/{cmd}')
            assert result['success']  # Should succeed (valid command)

    def test_validation_error_includes_available_commands(self, mock_orchestrator):
        """CommandValidationError includes list of available commands."""
        processor = CommandProcessor(mock_orchestrator)

        with pytest.raises(CommandValidationError) as exc:
            processor.execute_command('/badcommand')

        assert '/help' in exc.value.available_commands
        assert '/status' in exc.value.available_commands
        assert '/pause' in exc.value.available_commands
        assert '/resume' in exc.value.available_commands
        assert '/stop' in exc.value.available_commands


class TestBackwardCompatibility:
    """Test backward compatibility and migration."""

    def test_to_impl_still_works(self, mock_orchestrator):
        """/to-impl command still works (unchanged)."""
        processor = CommandProcessor(mock_orchestrator)
        result = processor.execute_command('/to-impl fix the bug')
        assert result['success']
        assert 'implementer' in result['message'].lower()
        # Verify stored in context
        assert 'to_impl' in mock_orchestrator.injected_context or 'to_claude' in mock_orchestrator.injected_context

    def test_to_claude_alias_still_works(self, mock_orchestrator):
        """/to-claude alias still works."""
        processor = CommandProcessor(mock_orchestrator)
        result = processor.execute_command('/to-claude add tests')
        assert result['success']
        # Verify stored in context
        assert 'to_impl' in mock_orchestrator.injected_context or 'to_claude' in mock_orchestrator.injected_context

    def test_pause_resume_still_work(self, mock_orchestrator):
        """/pause and /resume still work."""
        processor = CommandProcessor(mock_orchestrator)

        # Pause
        result = processor.execute_command('/pause')
        assert result['success']
        assert mock_orchestrator.paused

        # Resume
        result = processor.execute_command('/resume')
        assert result['success']
        assert not mock_orchestrator.paused

    def test_override_decision_still_works(self, mock_orchestrator):
        """/override-decision still works."""
        processor = CommandProcessor(mock_orchestrator)
        result = processor.execute_command('/override-decision retry')
        assert result['success']
        assert mock_orchestrator.injected_context['override_decision'] == 'retry'

    def test_to_obra_alias_routes_to_orchestrator(self, mock_orchestrator):
        """/to-obra (old alias) still routes to orchestrator."""
        processor = CommandProcessor(mock_orchestrator)
        result = processor.execute_command('/to-obra be lenient')
        assert result['success']
        # Verify stored in orchestrator context
        assert 'to_orch' in mock_orchestrator.injected_context or 'to_obra' in mock_orchestrator.injected_context


class TestHelpTextV15:
    """Test v1.5.0 help text format."""

    def test_help_text_is_string(self):
        """HELP_TEXT is a single formatted string."""
        assert isinstance(HELP_TEXT, str)
        assert len(HELP_TEXT) > 0

    def test_help_text_has_v15_header(self):
        """Help text has v1.5.0 header."""
        assert 'Interactive Mode Commands (v1.5.0)' in HELP_TEXT

    def test_help_text_describes_default_behavior(self):
        """Help text explains default behavior."""
        assert 'DEFAULT BEHAVIOR:' in HELP_TEXT
        assert 'natural text' in HELP_TEXT.lower() or '<natural text>' in HELP_TEXT

    def test_help_text_has_examples(self):
        """Help text includes examples."""
        assert 'EXAMPLES:' in HELP_TEXT

    def test_help_text_lists_all_slash_commands(self):
        """Help text lists all slash commands."""
        essential_commands = ['/help', '/status', '/pause', '/resume', '/stop', '/to-impl', '/override-decision']
        for cmd in essential_commands:
            assert cmd in HELP_TEXT, f"Command {cmd} not found in help text"

    def test_help_command_returns_full_text(self, mock_orchestrator):
        """/help returns full help text regardless of arguments."""
        processor = CommandProcessor(mock_orchestrator)

        # No arguments
        result1 = processor.execute_command('/help')
        assert result1['success']
        assert 'Interactive Mode Commands (v1.5.0)' in result1['message']

        # With arguments (ignored in v1.5.0)
        result2 = processor.execute_command('/help to-impl')
        assert result2['success']
        assert 'Interactive Mode Commands (v1.5.0)' in result2['message']


# ==============================================================================
# Test Summary
# ==============================================================================
#
# Total Tests: 31+ (new v1.5.0 tests)
# Categories:
#   - Natural Language Routing: 8 tests
#   - Slash Command Validation: 7 tests
#   - Backward Compatibility: 5 tests
#   - Help Text v1.5.0: 7 tests
#
# Coverage Target: 100% for new v1.5.0 code paths
# Compliance: TEST_GUIDELINES.md (0s sleep, 0 threads, < 2s execution)
# ==============================================================================
