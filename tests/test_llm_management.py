"""Tests for LLM management and graceful fallback functionality.

This module tests:
- Graceful LLM initialization failures
- LLM reconnection functionality
- LLM availability checking
- CLI LLM management commands
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from src.orchestrator import Orchestrator, OrchestratorState
from src.core.config import Config
from src.core.exceptions import OrchestratorException
from src.plugins.exceptions import (
    LLMConnectionException,
    LLMModelNotFoundException,
    PluginNotFoundError
)


class TestGracefulLLMInitialization:
    """Test graceful handling of LLM initialization failures."""

    def test_llm_unavailable_allows_initialization(self, test_config):
        """Test that Obra initializes even if LLM service is unavailable."""
        # Configure with non-existent LLM endpoint
        test_config.set('llm.type', 'ollama')
        test_config.set('llm.endpoint', 'http://invalid-host:99999')
        test_config.set('llm.api_url', 'http://invalid-host:99999')

        orchestrator = Orchestrator(config=test_config)

        # Should not raise exception during initialization
        orchestrator.initialize()

        # Orchestrator should be in INITIALIZED state
        assert orchestrator._state == OrchestratorState.INITIALIZED

        # LLM interface should be None
        assert orchestrator.llm_interface is None

    def test_invalid_llm_type_allows_initialization(self, test_config):
        """Test that Obra initializes even with invalid LLM type."""
        # Configure with non-existent LLM type
        test_config.set('llm.type', 'nonexistent-llm-provider')

        orchestrator = Orchestrator(config=test_config)

        # Should not raise exception during initialization
        orchestrator.initialize()

        # Orchestrator should be in INITIALIZED state
        assert orchestrator._state == OrchestratorState.INITIALIZED

        # LLM interface should be None
        assert orchestrator.llm_interface is None

    def test_llm_connection_exception_allows_initialization(self, test_config):
        """Test that LLM connection exceptions don't crash initialization."""
        # Use mock LLM that raises connection exception
        with patch('src.orchestrator.LLMRegistry.get') as mock_registry:
            mock_llm_class = Mock()
            mock_llm_instance = Mock()
            mock_llm_instance.initialize.side_effect = LLMConnectionException(
                provider='test-llm',
                url='http://test',
                details='Connection refused'
            )
            mock_llm_class.return_value = mock_llm_instance
            mock_registry.return_value = mock_llm_class

            orchestrator = Orchestrator(config=test_config)
            orchestrator.initialize()

            # Should complete initialization
            assert orchestrator._state == OrchestratorState.INITIALIZED
            assert orchestrator.llm_interface is None

    def test_llm_model_not_found_allows_initialization(self, test_config):
        """Test that missing model doesn't crash initialization."""
        # Use mock LLM that raises model not found exception
        with patch('src.orchestrator.LLMRegistry.get') as mock_registry:
            mock_llm_class = Mock()
            mock_llm_instance = Mock()
            mock_llm_instance.initialize.side_effect = LLMModelNotFoundException(
                provider='test-llm',
                model='nonexistent-model'
            )
            mock_llm_class.return_value = mock_llm_instance
            mock_registry.return_value = mock_llm_class

            orchestrator = Orchestrator(config=test_config)
            orchestrator.initialize()

            # Should complete initialization
            assert orchestrator._state == OrchestratorState.INITIALIZED
            assert orchestrator.llm_interface is None


class TestLLMReconnection:
    """Test LLM reconnection functionality."""

    def test_reconnect_llm_without_changes(self, test_config):
        """Test reconnecting to same LLM configuration."""
        orchestrator = Orchestrator(config=test_config)
        orchestrator.initialize()

        # Mock successful reconnection
        with patch.object(orchestrator, '_initialize_llm') as mock_init:
            # Set up mock LLM interface
            mock_llm = Mock()
            mock_llm.is_available.return_value = True

            def set_llm_interface():
                orchestrator.llm_interface = mock_llm

            mock_init.side_effect = set_llm_interface

            result = orchestrator.reconnect_llm()

            assert result is True
            mock_init.assert_called_once()

    def test_reconnect_llm_with_new_type(self, test_config):
        """Test switching to different LLM type."""
        orchestrator = Orchestrator(config=test_config)
        orchestrator.initialize()

        # Mock successful reconnection with new type
        with patch.object(orchestrator, '_initialize_llm') as mock_init:
            mock_llm = Mock()
            mock_llm.is_available.return_value = True

            def set_llm_interface():
                orchestrator.llm_interface = mock_llm

            mock_init.side_effect = set_llm_interface

            result = orchestrator.reconnect_llm(
                llm_type='openai-codex',
                llm_config={'model': 'gpt-5-codex'}
            )

            assert result is True
            # Config should be updated
            assert orchestrator.config.get('llm.type') == 'openai-codex'
            assert orchestrator.config.get('llm.model') == 'gpt-5-codex'

    def test_reconnect_llm_failure_returns_false(self, test_config):
        """Test that failed reconnection returns False."""
        orchestrator = Orchestrator(config=test_config)
        orchestrator.initialize()

        # Mock failed reconnection
        with patch.object(orchestrator, '_initialize_llm') as mock_init:
            def set_llm_none():
                orchestrator.llm_interface = None

            mock_init.side_effect = set_llm_none

            result = orchestrator.reconnect_llm()

            assert result is False

    def test_reconnect_llm_unavailable_returns_false(self, test_config):
        """Test that unavailable LLM after reconnection returns False."""
        orchestrator = Orchestrator(config=test_config)
        orchestrator.initialize()

        # Mock LLM that initializes but is not available
        with patch.object(orchestrator, '_initialize_llm') as mock_init:
            mock_llm = Mock()
            mock_llm.is_available.return_value = False

            def set_llm_interface():
                orchestrator.llm_interface = mock_llm

            mock_init.side_effect = set_llm_interface

            result = orchestrator.reconnect_llm()

            assert result is False
            # LLM should be set to None
            assert orchestrator.llm_interface is None

    def test_reconnect_llm_exception_returns_false(self, test_config):
        """Test that exceptions during reconnection are handled."""
        orchestrator = Orchestrator(config=test_config)
        orchestrator.initialize()

        # Mock exception during initialization
        with patch.object(orchestrator, '_initialize_llm') as mock_init:
            mock_init.side_effect = Exception("Connection failed")

            result = orchestrator.reconnect_llm()

            assert result is False
            assert orchestrator.llm_interface is None


class TestLLMAvailabilityCheck:
    """Test LLM availability checking."""

    def test_check_llm_available_when_connected(self, test_config):
        """Test availability check with connected LLM."""
        orchestrator = Orchestrator(config=test_config)
        orchestrator.initialize()

        # Mock connected LLM
        mock_llm = Mock()
        mock_llm.is_available.return_value = True
        orchestrator.llm_interface = mock_llm

        assert orchestrator.check_llm_available() is True

    def test_check_llm_available_when_not_connected(self, test_config):
        """Test availability check with no LLM."""
        orchestrator = Orchestrator(config=test_config)
        orchestrator.initialize()

        # Set LLM to None
        orchestrator.llm_interface = None

        assert orchestrator.check_llm_available() is False

    def test_check_llm_available_when_service_down(self, test_config):
        """Test availability check when service is down."""
        orchestrator = Orchestrator(config=test_config)
        orchestrator.initialize()

        # Mock LLM that is not available
        mock_llm = Mock()
        mock_llm.is_available.return_value = False
        orchestrator.llm_interface = mock_llm

        assert orchestrator.check_llm_available() is False

    def test_check_llm_available_handles_exception(self, test_config):
        """Test availability check handles exceptions gracefully."""
        orchestrator = Orchestrator(config=test_config)
        orchestrator.initialize()

        # Mock LLM that raises exception
        mock_llm = Mock()
        mock_llm.is_available.side_effect = Exception("Network error")
        orchestrator.llm_interface = mock_llm

        assert orchestrator.check_llm_available() is False


class TestTaskExecutionWithoutLLM:
    """Test task execution validation when LLM unavailable."""

    def test_execute_task_fails_without_llm(self, test_config, project, task):
        """Test that task execution fails gracefully without LLM."""
        orchestrator = Orchestrator(config=test_config)
        orchestrator.initialize()

        # Set LLM to None (simulating unavailable LLM)
        orchestrator.llm_interface = None

        # Task execution should raise OrchestratorException
        with pytest.raises(OrchestratorException) as exc_info:
            orchestrator.execute_task(task.id)

        # Error message should mention LLM unavailability
        assert "LLM service not available" in str(exc_info.value)

    def test_execute_task_checks_llm_before_running(self, test_config, project, task):
        """Test that execute_task validates LLM before running."""
        orchestrator = Orchestrator(config=test_config)
        orchestrator.initialize()

        # Mock LLM that becomes unavailable
        mock_llm = Mock()
        mock_llm.is_available.return_value = False
        orchestrator.llm_interface = mock_llm

        # Should fail with appropriate error
        with pytest.raises(OrchestratorException) as exc_info:
            orchestrator.execute_task(task.id)

        assert "LLM service not available" in str(exc_info.value)


class TestLLMCLICommands:
    """Test CLI commands for LLM management."""

    @pytest.fixture
    def cli_runner(self):
        """Create CLI test runner."""
        from click.testing import CliRunner
        return CliRunner()

    def test_llm_status_command(self, cli_runner, test_config):
        """Test 'obra llm status' command."""
        from src.cli import cli

        # Mock config to avoid file dependencies
        with patch('src.cli.Config.load') as mock_config:
            mock_config.return_value = test_config

            result = cli_runner.invoke(cli, ['llm', 'status'])

            # Should not crash
            assert result.exit_code in [0, 1]  # May fail but shouldn't crash
            assert 'LLM Connection Status' in result.output

    def test_llm_list_command(self, cli_runner, test_config):
        """Test 'obra llm list' command."""
        from src.cli import cli

        with patch('src.cli.Config.load') as mock_config:
            mock_config.return_value = test_config

            result = cli_runner.invoke(cli, ['llm', 'list'])

            # Should succeed
            assert result.exit_code == 0
            assert 'Available LLM Providers' in result.output

    def test_llm_reconnect_command_without_args(self, cli_runner, test_config):
        """Test 'obra llm reconnect' without arguments."""
        from src.cli import cli

        with patch('src.cli.Config.load') as mock_config:
            mock_config.return_value = test_config

            # Mock orchestrator
            with patch('src.cli.Orchestrator') as mock_orch_class:
                mock_orch = Mock()
                mock_orch.reconnect_llm.return_value = True
                mock_orch_class.return_value = mock_orch

                result = cli_runner.invoke(cli, ['llm', 'reconnect'])

                # Should call reconnect
                mock_orch.reconnect_llm.assert_called_once()

    def test_llm_reconnect_command_with_type(self, cli_runner, test_config):
        """Test 'obra llm reconnect --type openai-codex'."""
        from src.cli import cli

        with patch('src.cli.Config.load') as mock_config:
            mock_config.return_value = test_config

            with patch('src.cli.Orchestrator') as mock_orch_class:
                mock_orch = Mock()
                mock_orch.reconnect_llm.return_value = True
                mock_orch_class.return_value = mock_orch

                result = cli_runner.invoke(cli, [
                    'llm', 'reconnect',
                    '--type', 'openai-codex',
                    '--model', 'gpt-5-codex'
                ])

                # Should call reconnect with correct args
                mock_orch.reconnect_llm.assert_called_once()
                call_args = mock_orch.reconnect_llm.call_args
                assert call_args[1]['llm_type'] == 'openai-codex'
                assert call_args[1]['llm_config']['model'] == 'gpt-5-codex'

    def test_llm_switch_command(self, cli_runner, test_config):
        """Test 'obra llm switch' command."""
        from src.cli import cli

        with patch('src.cli.Config.load') as mock_config:
            mock_config.return_value = test_config

            with patch('src.cli.Orchestrator') as mock_orch_class:
                mock_orch = Mock()
                mock_orch.reconnect_llm.return_value = True
                mock_orch_class.return_value = mock_orch

                result = cli_runner.invoke(cli, [
                    'llm', 'switch', 'openai-codex'
                ])

                # Should call reconnect
                mock_orch.reconnect_llm.assert_called_once()


class TestLLMConfigurationMerging:
    """Test LLM configuration merging during reconnection."""

    def test_reconnect_merges_config(self, test_config):
        """Test that reconnect_llm merges new config with existing."""
        # Set initial config
        test_config.set('llm.type', 'ollama')
        test_config.set('llm.model', 'qwen2.5-coder:32b')
        test_config.set('llm.temperature', 0.7)

        orchestrator = Orchestrator(config=test_config)
        orchestrator.initialize()

        # Reconnect with partial config (should merge, not replace)
        with patch.object(orchestrator, '_initialize_llm'):
            mock_llm = Mock()
            mock_llm.is_available.return_value = True
            orchestrator.llm_interface = mock_llm

            orchestrator.reconnect_llm(
                llm_config={'model': 'qwen2.5-coder:7b'}
            )

        # Original settings should be preserved
        assert orchestrator.config.get('llm.type') == 'ollama'
        assert orchestrator.config.get('llm.temperature') == 0.7
        # New setting should be applied
        assert orchestrator.config.get('llm.model') == 'qwen2.5-coder:7b'

    def test_reconnect_updates_type_and_config(self, test_config):
        """Test reconnecting with both type and config changes."""
        orchestrator = Orchestrator(config=test_config)
        orchestrator.initialize()

        with patch.object(orchestrator, '_initialize_llm'):
            mock_llm = Mock()
            mock_llm.is_available.return_value = True
            orchestrator.llm_interface = mock_llm

            orchestrator.reconnect_llm(
                llm_type='openai-codex',
                llm_config={
                    'model': 'gpt-5-codex',
                    'timeout': 120
                }
            )

        # All settings should be updated
        assert orchestrator.config.get('llm.type') == 'openai-codex'
        assert orchestrator.config.get('llm.model') == 'gpt-5-codex'
        assert orchestrator.config.get('llm.timeout') == 120


class TestLLMInitializationWarnings:
    """Test that appropriate warnings are displayed during initialization."""

    def test_warning_message_on_connection_failure(self, test_config, caplog):
        """Test that helpful warning is logged on connection failure."""
        import logging

        # Configure invalid endpoint
        test_config.set('llm.endpoint', 'http://invalid:99999')
        test_config.set('llm.api_url', 'http://invalid:99999')

        orchestrator = Orchestrator(config=test_config)

        with caplog.at_level(logging.WARNING):
            orchestrator.initialize()

        # Should log warning about LLM initialization failure
        assert any('LLM initialization failed' in record.message
                   for record in caplog.records)

    def test_warning_includes_recovery_instructions(self, test_config):
        """Test that warning includes instructions for recovery."""
        # This is tested via the _print_obra calls in orchestrator.py
        # We verify the method was called with appropriate messages

        test_config.set('llm.endpoint', 'http://invalid:99999')
        test_config.set('llm.api_url', 'http://invalid:99999')

        orchestrator = Orchestrator(config=test_config)

        # Mock _print_obra to capture warnings
        with patch.object(orchestrator, '_print_obra') as mock_print:
            orchestrator.initialize()

            # Should have called _print_obra with warning messages
            assert mock_print.call_count > 0

            # Check that helpful messages were printed
            messages = [call[0][0] for call in mock_print.call_args_list]
            message_text = ' '.join(messages)

            assert any('Could not connect to LLM' in msg for msg in messages)
            # Should mention configuration options
            assert any('ollama' in msg or 'openai-codex' in msg for msg in messages)
