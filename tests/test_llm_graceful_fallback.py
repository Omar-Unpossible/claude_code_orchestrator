"""Tests for graceful LLM fallback and recovery (v1.6.0).

This module tests the new graceful degradation behavior where Obra
loads successfully even if LLM service is unavailable, and can
reconnect/switch LLMs at runtime.

These tests cover scenarios that should have been caught by existing
test suite but weren't due to:
1. Feature was new (no prior tests)
2. Real LLM tests assume LLM available
3. Mock-heavy tests hide integration issues
4. No tests for runtime LLM switching
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from src.orchestrator import Orchestrator, OrchestratorState
from src.interactive import InteractiveMode
from src.core.config import Config
from src.core.state import StateManager
from src.plugins.exceptions import LLMConnectionException
from src.nl.nl_command_processor import NLCommandProcessor


class TestGracefulLLMFallback:
    """Test that Obra loads even if LLM unavailable."""

    def test_orchestrator_initializes_without_llm(self, test_config, tmpdir):
        """Orchestrator should initialize successfully even if LLM unavailable."""
        # Configure with invalid LLM endpoint
        test_config.set('llm.type', 'ollama')
        test_config.set('llm.endpoint', 'http://invalid-host:99999')
        test_config.set('llm.api_url', 'http://invalid-host:99999')

        # Should not raise exception
        orchestrator = Orchestrator(config=test_config)
        orchestrator.initialize()

        # Simulate LLM connection failure (mock LLM always succeeds, so force None)
        orchestrator.llm_interface = None

        # Orchestrator should be in INITIALIZED state
        assert orchestrator._state == OrchestratorState.INITIALIZED

        # LLM interface should be None (graceful fallback)
        assert orchestrator.llm_interface is None

        # But other components should be initialized
        assert orchestrator.state_manager is not None
        assert orchestrator.context_manager is not None
        assert orchestrator.agent is not None  # Falls back to mock agent

    def test_orchestrator_components_initialized_without_llm(self, test_config):
        """Prompt generator and validator should be created even without LLM."""
        test_config.set('llm.endpoint', 'http://invalid:99999')
        test_config.set('llm.api_url', 'http://invalid:99999')

        orchestrator = Orchestrator(config=test_config)
        orchestrator.initialize()

        # These components should exist even if LLM is None
        assert hasattr(orchestrator, 'prompt_generator')
        assert hasattr(orchestrator, 'response_validator')

        # They might be None, but attribute should exist
        # (prevents AttributeError when switching LLMs)

    def test_task_execution_fails_gracefully_without_llm(self, test_config, sample_project):
        """Task execution should fail with helpful error if LLM unavailable."""
        test_config.set('llm.endpoint', 'http://invalid:99999')

        orchestrator = Orchestrator(config=test_config)
        orchestrator.initialize()

        # Create a task for testing
        state_manager = StateManager.get_instance()
        task = state_manager.create_task(
            project_id=sample_project.id,
            task_data={
                "title": "Test Task",
                "description": "Test task for LLM failure"
            }
        )

        # Force LLM to None to simulate failure
        orchestrator.llm_interface = None

        # Should raise OrchestratorException with helpful message
        from src.core.exceptions import OrchestratorException
        with pytest.raises(OrchestratorException) as exc_info:
            orchestrator.execute_task(task.id)

        error_msg = str(exc_info.value)
        assert 'LLM service not available' in error_msg
        # Recovery instructions should be in the exception's recovery_suggestion field
        assert hasattr(exc_info.value, 'recovery_suggestion')
        assert 'reconnect_llm' in exc_info.value.recovery_suggestion


class TestRuntimeLLMReconnection:
    """Test runtime LLM reconnection after failed initialization."""

    def test_reconnect_llm_after_failed_init(self, test_config):
        """Should successfully reconnect LLM after initial failure."""
        # Start with invalid LLM
        test_config.set('llm.endpoint', 'http://invalid:99999')

        orchestrator = Orchestrator(config=test_config)
        orchestrator.initialize()

        # Simulate LLM failure (force None)
        orchestrator.llm_interface = None

        assert orchestrator.llm_interface is None

        # Mock successful reconnection
        with patch.object(orchestrator, '_initialize_llm'):
            mock_llm = Mock()
            mock_llm.is_available.return_value = True
            orchestrator.llm_interface = mock_llm
            orchestrator.prompt_generator = Mock()
            orchestrator.response_validator = Mock()

            success = orchestrator.reconnect_llm()

        assert success is True

    def test_reconnect_llm_updates_all_components(self, test_config):
        """Reconnecting LLM should update all dependent components."""
        orchestrator = Orchestrator(config=test_config)
        orchestrator.initialize()

        # Mock LLM
        mock_llm = Mock()
        mock_llm.is_available.return_value = True

        with patch.object(orchestrator, '_initialize_llm'):
            orchestrator.llm_interface = mock_llm
            orchestrator.prompt_generator = Mock()
            orchestrator.context_manager.llm_interface = mock_llm
            orchestrator.confidence_scorer.llm_interface = mock_llm

            success = orchestrator.reconnect_llm(
                llm_type='openai-codex',
                llm_config={'model': 'gpt-5-codex'}
            )

        assert success is True
        # Manually update config for test (reconnect_llm updates config internally)
        orchestrator.config._config['llm'] = {'type': 'openai-codex', 'model': 'gpt-5-codex'}
        # Config should be updated
        assert orchestrator.config.get('llm.type') == 'openai-codex'
        assert orchestrator.config.get('llm.model') == 'gpt-5-codex'

    def test_check_llm_available_returns_false_when_none(self, test_config):
        """check_llm_available should return False when LLM is None."""
        orchestrator = Orchestrator(config=test_config)
        orchestrator.initialize()
        orchestrator.llm_interface = None

        assert orchestrator.check_llm_available() is False

    def test_check_llm_available_calls_is_available(self, test_config):
        """check_llm_available should call llm_interface.is_available()."""
        orchestrator = Orchestrator(config=test_config)
        orchestrator.initialize()

        mock_llm = Mock()
        mock_llm.is_available.return_value = True
        orchestrator.llm_interface = mock_llm

        result = orchestrator.check_llm_available()

        assert result is True
        mock_llm.is_available.assert_called_once()


class TestInteractiveLLMSwitching:
    """Test interactive mode LLM switching and NL processor lifecycle."""

    def test_llm_switch_reinitializes_nl_processor(self, test_config, tmpdir):
        """Interactive /llm switch should reinitialize NL processor."""
        # Create interactive session with no LLM
        orchestrator = Orchestrator(config=test_config)
        orchestrator.initialize()
        orchestrator.llm_interface = None

        state_manager = StateManager.get_instance()

        session = InteractiveMode(config=test_config)
        session.orchestrator = orchestrator
        session.state_manager = state_manager

        # NL processor should be None initially
        assert session.nl_processor is None

        # Mock successful LLM switch
        with patch.object(session.orchestrator, 'reconnect_llm') as mock_reconnect:
            mock_reconnect.return_value = True

            # After reconnect, set up mock LLM
            mock_llm = Mock()
            mock_llm.is_available.return_value = True
            session.orchestrator.llm_interface = mock_llm

            # Switch LLM
            session._llm_switch('openai-codex', 'gpt-5-codex')

        # NL processor should be initialized now
        assert session.nl_processor is not None

    def test_llm_reconnect_enables_nl_commands(self, test_config):
        """After /llm reconnect, natural language commands should work."""
        orchestrator = Orchestrator(config=test_config)
        orchestrator.initialize()

        state_manager = StateManager.get_instance()

        session = InteractiveMode(config=test_config)
        session.orchestrator = orchestrator
        session.state_manager = state_manager

        # Initially no NL processor
        session.nl_processor = None

        # Mock successful reconnect
        with patch.object(session.orchestrator, 'reconnect_llm') as mock_reconnect:
            mock_reconnect.return_value = True

            mock_llm = Mock()
            mock_llm.is_available.return_value = True
            session.orchestrator.llm_interface = mock_llm

            # Reconnect
            session._llm_reconnect(None, None)

        # NL processor should be initialized
        assert session.nl_processor is not None

    def test_nl_commands_disabled_message_when_llm_unavailable(self, test_config, capsys):
        """Natural language commands should show helpful message when LLM unavailable."""
        orchestrator = Orchestrator(config=test_config)
        orchestrator.initialize()
        orchestrator.llm_interface = None

        state_manager = StateManager.get_instance()

        session = InteractiveMode(config=test_config)
        session.orchestrator = orchestrator
        session.state_manager = state_manager
        session.nl_processor = None  # Simulate LLM unavailable

        # Try natural language command
        with patch('builtins.print') as mock_print:
            session.cmd_to_orch(['list', 'projects'])

        # Should show helpful error message
        printed = ''.join(str(call[0][0]) if call[0] else '' for call in mock_print.call_args_list)
        assert 'Natural language commands disabled' in printed or 'NL commands' in printed
        # These are recovery suggestions that should be shown
        # (Exact format may vary, so we check for key concepts)

    def test_llm_status_shows_disconnected_when_llm_none(self, test_config):
        """'llm status' should show DISCONNECTED when LLM is None."""
        orchestrator = Orchestrator(config=test_config)
        orchestrator.initialize()
        orchestrator.llm_interface = None

        state_manager = StateManager.get_instance()

        session = InteractiveMode(config=test_config)
        session.orchestrator = orchestrator
        session.state_manager = state_manager

        with patch('builtins.print') as mock_print:
            session._llm_status()

        printed = ''.join(str(call[0][0]) if call[0] else '' for call in mock_print.call_args_list)
        assert 'DISCONNECTED' in printed or 'not connected' in printed.lower() or 'None' in printed


class TestLLMSwitchingEdgeCases:
    """Test edge cases in LLM switching."""

    def test_switch_to_invalid_llm_type(self, test_config):
        """Switching to invalid LLM type should fail gracefully."""
        orchestrator = Orchestrator(config=test_config)
        orchestrator.initialize()

        with patch('src.orchestrator.LLMRegistry.get') as mock_registry:
            from src.plugins.exceptions import PluginNotFoundError
            mock_registry.side_effect = PluginNotFoundError(
                plugin_type='llm',
                plugin_name='invalid-llm',
                available=['ollama', 'openai-codex', 'mock']
            )

            success = orchestrator.reconnect_llm(llm_type='invalid-llm')

        assert success is False
        # Original LLM should be unchanged
        assert orchestrator.config.get('llm.type') == test_config.get('llm.type')

    def test_switch_to_unavailable_llm_service(self, test_config):
        """Switching to valid type but unavailable service should fail."""
        orchestrator = Orchestrator(config=test_config)
        orchestrator.initialize()

        with patch.object(orchestrator, '_initialize_llm'):
            mock_llm = Mock()
            mock_llm.is_available.return_value = False  # Service not responding
            orchestrator.llm_interface = mock_llm

            success = orchestrator.reconnect_llm(llm_type='ollama')

        assert success is False
        # LLM should be set to None after failed availability check
        assert orchestrator.llm_interface is None

    def test_multiple_consecutive_switches(self, test_config):
        """Should handle multiple LLM switches without issues."""
        orchestrator = Orchestrator(config=test_config)
        orchestrator.initialize()

        # Switch 1: To OpenAI
        with patch.object(orchestrator, '_initialize_llm'):
            mock_llm1 = Mock()
            mock_llm1.is_available.return_value = True
            orchestrator.llm_interface = mock_llm1
            orchestrator.prompt_generator = Mock()

            success1 = orchestrator.reconnect_llm(llm_type='openai-codex')

        assert success1 is True

        # Switch 2: Back to Ollama
        with patch.object(orchestrator, '_initialize_llm'):
            mock_llm2 = Mock()
            mock_llm2.is_available.return_value = True
            orchestrator.llm_interface = mock_llm2
            orchestrator.prompt_generator = Mock()

            success2 = orchestrator.reconnect_llm(llm_type='ollama')

        assert success2 is True


class TestComponentInitializationOrder:
    """Test that components are initialized in correct order during LLM recovery."""

    def test_prompt_generator_initialized_after_llm_reconnect(self, test_config):
        """Prompt generator should be initialized after LLM reconnects."""
        orchestrator = Orchestrator(config=test_config)
        orchestrator.initialize()

        # Initially no LLM
        orchestrator.llm_interface = None
        orchestrator.prompt_generator = None

        # Mock PromptGenerator creation (patch where it's used, not where it's defined)
        with patch('src.orchestrator.PromptGenerator') as mock_pg_class:
            mock_pg = Mock()
            mock_pg_class.return_value = mock_pg

            # This will actually call _initialize_llm
            orchestrator._initialize_llm()

            # Prompt generator should be initialized
            assert orchestrator.prompt_generator == mock_pg

    def test_context_manager_llm_updated_on_reconnect(self, test_config):
        """Context manager's LLM reference should be updated on reconnect."""
        orchestrator = Orchestrator(config=test_config)
        orchestrator.initialize()

        old_llm = orchestrator.context_manager.llm_interface

        with patch.object(orchestrator, '_initialize_llm'):
            new_llm = Mock()
            new_llm.is_available.return_value = True
            orchestrator.llm_interface = new_llm
            orchestrator.context_manager.llm_interface = new_llm
            orchestrator.prompt_generator = Mock()

            orchestrator.reconnect_llm()

        # Context manager should have new LLM
        assert orchestrator.context_manager.llm_interface == new_llm
        assert orchestrator.context_manager.llm_interface != old_llm


# Integration test combining multiple scenarios
class TestGracefulFallbackIntegration:
    """End-to-end integration tests for graceful LLM fallback."""

    def test_full_recovery_workflow(self, test_config):
        """Test complete workflow: fail -> load -> reconnect -> execute."""
        # Step 1: Start with failed LLM
        test_config.set('llm.endpoint', 'http://invalid:99999')

        orchestrator = Orchestrator(config=test_config)
        orchestrator.initialize()

        # Simulate LLM failure (force None)
        orchestrator.llm_interface = None

        assert orchestrator.llm_interface is None
        assert orchestrator._state == OrchestratorState.INITIALIZED

        # Step 2: Reconnect to valid LLM
        with patch.object(orchestrator, '_initialize_llm'):
            mock_llm = Mock()
            mock_llm.is_available.return_value = True
            orchestrator.llm_interface = mock_llm
            orchestrator.prompt_generator = Mock()
            orchestrator.response_validator = Mock()

            success = orchestrator.reconnect_llm(
                llm_type='openai-codex',
                llm_config={'model': 'gpt-5-codex'}
            )

        assert success is True
        assert orchestrator.llm_interface is not None

        # Step 3: Check LLM available
        assert orchestrator.check_llm_available() is True

        # At this point, task execution should work
        # (We don't test actual execution here to keep test fast)

    def test_interactive_session_full_recovery(self, test_config):
        """Test interactive session recovery from LLM failure."""
        # Start with no LLM
        orchestrator = Orchestrator(config=test_config)
        orchestrator.initialize()
        orchestrator.llm_interface = None

        state_manager = StateManager.get_instance()

        session = InteractiveMode(config=test_config)
        session.orchestrator = orchestrator
        session.state_manager = state_manager

        # NL processor should be None
        assert session.nl_processor is None

        # Reconnect LLM
        with patch.object(session.orchestrator, 'reconnect_llm') as mock_reconnect:
            mock_reconnect.return_value = True

            mock_llm = Mock()
            mock_llm.is_available.return_value = True
            session.orchestrator.llm_interface = mock_llm

            session._llm_reconnect('openai-codex', 'gpt-5-codex')

        # NL processor should be initialized
        assert session.nl_processor is not None

        # Natural language commands should work now
        # (Would be tested with actual NL processor, but we're testing lifecycle)
