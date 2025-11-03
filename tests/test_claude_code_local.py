"""Tests for ClaudeCodeLocalAgent subprocess management."""

import os
import subprocess
import threading
import time
from pathlib import Path
from queue import Queue
from unittest.mock import Mock, MagicMock, patch, call

import pytest

from src.agents.claude_code_local import ClaudeCodeLocalAgent, ProcessState
from src.plugins.exceptions import AgentException


class TestClaudeCodeLocalAgent:
    """Test ClaudeCodeLocalAgent subprocess management."""

    def test_initialization(self):
        """Test agent initializes in STOPPED state."""
        agent = ClaudeCodeLocalAgent()

        assert agent.state == ProcessState.STOPPED
        assert agent.process is None
        assert agent.claude_command == "claude"
        assert agent.startup_timeout == 30

    def test_initialize_creates_workspace(self, tmp_path):
        """Test initialize creates workspace directory."""
        agent = ClaudeCodeLocalAgent()
        workspace = tmp_path / "workspace"

        config = {
            'workspace_path': str(workspace),
            'claude_command': 'echo',
        }

        # Mock subprocess to avoid actually running claude
        with patch('subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_process.poll.return_value = None
            mock_process.stdout = MagicMock()
            mock_process.stderr = MagicMock()
            mock_process.stdout.readline = lambda: ''  # Empty output
            mock_process.stderr.readline = lambda: ''
            mock_popen.return_value = mock_process

            # Mock _wait_for_ready to skip startup check
            with patch.object(agent, '_wait_for_ready', return_value=True):
                agent.initialize(config)

        assert workspace.exists()
        assert agent.workspace_path == workspace

    def test_initialize_starts_subprocess(self, tmp_path):
        """Test initialize spawns Claude Code subprocess."""
        agent = ClaudeCodeLocalAgent()

        config = {
            'workspace_path': str(tmp_path),
            'claude_command': 'python',
        }

        with patch('subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_process.poll.return_value = None
            mock_popen.return_value = mock_process

            with patch.object(agent, '_wait_for_ready', return_value=True):
                agent.initialize(config)

            # Verify Popen was called correctly
            mock_popen.assert_called_once()
            args, kwargs = mock_popen.call_args

            assert args[0] == ['python']
            assert kwargs['stdin'] == subprocess.PIPE
            assert kwargs['stdout'] == subprocess.PIPE
            assert kwargs['stderr'] == subprocess.PIPE
            assert kwargs['text'] is True
            assert kwargs['cwd'] == str(tmp_path)

    def test_initialize_starts_reader_threads(self, tmp_path):
        """Test initialize starts stdout/stderr reader threads."""
        agent = ClaudeCodeLocalAgent()

        config = {
            'workspace_path': str(tmp_path),
            'claude_command': 'echo',
        }

        with patch('subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_process.poll.return_value = None
            mock_popen.return_value = mock_process

            with patch.object(agent, '_wait_for_ready', return_value=True):
                agent.initialize(config)

        assert agent._stdout_thread is not None
        assert agent._stderr_thread is not None
        assert agent._stdout_thread.is_alive()
        assert agent._stderr_thread.is_alive()

        # Cleanup
        agent._stop_reading.set()
        agent._stdout_thread.join(timeout=1.0)
        agent._stderr_thread.join(timeout=1.0)

    def test_initialize_transitions_to_ready_on_success(self, tmp_path):
        """Test state transitions STARTING -> READY on successful startup."""
        agent = ClaudeCodeLocalAgent()

        config = {
            'workspace_path': str(tmp_path),
            'claude_command': 'echo',
        }

        with patch('subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_process.poll.return_value = None
            mock_popen.return_value = mock_process

            with patch.object(agent, '_wait_for_ready', return_value=True):
                agent.initialize(config)

        assert agent.state == ProcessState.READY

    def test_initialize_transitions_to_error_on_failure(self, tmp_path):
        """Test state transitions to ERROR if startup fails."""
        agent = ClaudeCodeLocalAgent()

        config = {
            'workspace_path': str(tmp_path),
            'claude_command': 'nonexistent_command',
        }

        with pytest.raises(AgentException, match="Claude Code CLI not found"):
            agent.initialize(config)

        assert agent.state == ProcessState.ERROR

    def test_initialize_raises_on_command_not_found(self, tmp_path):
        """Test initialize raises AgentException if command not found."""
        agent = ClaudeCodeLocalAgent()

        config = {
            'workspace_path': str(tmp_path),
            'claude_command': 'nonexistent_command_xyz123',
        }

        with pytest.raises(AgentException) as exc_info:
            agent.initialize(config)

        assert "not found" in str(exc_info.value)
        assert exc_info.value.context_data['command'] == 'nonexistent_command_xyz123'
        assert "Install Claude Code CLI" in exc_info.value.recovery_suggestion

    def test_wait_for_ready_detects_ready_signal(self, tmp_path):
        """Test _wait_for_ready detects 'Ready' in output."""
        agent = ClaudeCodeLocalAgent()
        agent.process = MagicMock()
        agent.process.poll.return_value = None

        # Simulate "Ready" output
        agent._stdout_queue.put("Claude Code CLI v1.0")
        agent._stdout_queue.put("Ready")

        result = agent._wait_for_ready()

        assert result is True

    def test_wait_for_ready_detects_prompt_signal(self, tmp_path):
        """Test _wait_for_ready detects prompt '>' in output."""
        agent = ClaudeCodeLocalAgent()
        agent.process = MagicMock()
        agent.process.poll.return_value = None

        # Simulate prompt output
        agent._stdout_queue.put("claude>")

        result = agent._wait_for_ready()

        assert result is True

    def test_wait_for_ready_returns_false_on_process_exit(self):
        """Test _wait_for_ready returns False if process exits during startup."""
        agent = ClaudeCodeLocalAgent()
        agent.process = MagicMock()
        agent.process.poll.return_value = 1  # Process exited

        result = agent._wait_for_ready()

        assert result is False

    def test_wait_for_ready_timeout(self):
        """Test _wait_for_ready times out if no ready signal."""
        agent = ClaudeCodeLocalAgent()
        agent.startup_timeout = 1  # 1 second timeout
        agent.process = MagicMock()
        agent.process.poll.return_value = None

        # No output - should timeout
        result = agent._wait_for_ready()

        assert result is False

    def test_send_prompt_requires_ready_state(self):
        """Test send_prompt raises if not in READY state."""
        agent = ClaudeCodeLocalAgent()
        agent.state = ProcessState.STOPPED

        with pytest.raises(AgentException, match="agent in state"):
            agent.send_prompt("test")

    def test_send_prompt_writes_to_stdin(self, tmp_path):
        """Test send_prompt writes prompt to process stdin."""
        agent = ClaudeCodeLocalAgent()
        agent.state = ProcessState.READY

        mock_stdin = MagicMock()
        agent.process = MagicMock()
        agent.process.stdin = mock_stdin
        agent.process.poll.return_value = None

        # Mock response reading
        with patch.object(agent, '_read_response', return_value="response"):
            agent.send_prompt("test prompt")

        mock_stdin.write.assert_called_once_with("test prompt\n")
        mock_stdin.flush.assert_called_once()

    def test_send_prompt_reads_response(self, tmp_path):
        """Test send_prompt reads response from stdout."""
        agent = ClaudeCodeLocalAgent()
        agent.state = ProcessState.READY

        agent.process = MagicMock()
        agent.process.poll.return_value = None

        with patch.object(agent, '_read_response', return_value="test response") as mock_read:
            response = agent.send_prompt("prompt")

        mock_read.assert_called_once()
        assert response == "test response"

    def test_send_prompt_transitions_busy_then_ready(self, tmp_path):
        """Test send_prompt transitions READY -> BUSY -> READY."""
        agent = ClaudeCodeLocalAgent()
        agent.state = ProcessState.READY
        agent.process = MagicMock()
        agent.process.poll.return_value = None

        states = []

        def capture_state():
            states.append(agent.state)
            return "response"

        with patch.object(agent, '_read_response', side_effect=capture_state):
            agent.send_prompt("prompt")

        assert states[0] == ProcessState.BUSY
        assert agent.state == ProcessState.READY

    def test_read_response_detects_completion_marker(self):
        """Test _read_response stops at completion marker."""
        agent = ClaudeCodeLocalAgent()
        agent.process = MagicMock()
        agent.process.poll.return_value = None

        # Simulate response with completion
        agent._stdout_queue.put("Line 1")
        agent._stdout_queue.put("Line 2")
        agent._stdout_queue.put("✓ Done")

        response = agent._read_response()

        assert "Line 1" in response
        assert "Line 2" in response
        assert "✓ Done" in response

    def test_read_response_detects_rate_limit(self):
        """Test _read_response raises on rate limit marker."""
        agent = ClaudeCodeLocalAgent()
        agent.process = MagicMock()
        agent.process.poll.return_value = None

        # Simulate rate limit
        agent._stdout_queue.put("Error: rate limit exceeded")

        with pytest.raises(AgentException, match="Rate limit detected"):
            agent._read_response()

    def test_read_response_timeout(self):
        """Test _read_response times out if no completion."""
        agent = ClaudeCodeLocalAgent()
        agent.response_timeout = 1  # 1 second timeout
        agent.process = MagicMock()
        agent.process.poll.return_value = None

        # No output - should timeout
        with pytest.raises(AgentException, match="Timeout waiting for response"):
            agent._read_response()

    def test_is_healthy_returns_false_when_stopped(self):
        """Test is_healthy returns False when STOPPED."""
        agent = ClaudeCodeLocalAgent()
        agent.state = ProcessState.STOPPED

        assert agent.is_healthy() is False

    def test_is_healthy_returns_false_when_error(self):
        """Test is_healthy returns False when ERROR."""
        agent = ClaudeCodeLocalAgent()
        agent.state = ProcessState.ERROR

        assert agent.is_healthy() is False

    def test_is_healthy_checks_process_alive(self):
        """Test is_healthy checks if process is alive."""
        agent = ClaudeCodeLocalAgent()
        agent.state = ProcessState.READY
        agent.process = MagicMock()
        agent.process.poll.return_value = 1  # Process exited

        assert agent.is_healthy() is False
        assert agent.state == ProcessState.ERROR

    def test_is_healthy_checks_threads_alive(self):
        """Test is_healthy checks if reader threads are alive."""
        agent = ClaudeCodeLocalAgent()
        agent.state = ProcessState.READY
        agent.process = MagicMock()
        agent.process.poll.return_value = None

        # Dead thread
        agent._stdout_thread = MagicMock()
        agent._stdout_thread.is_alive.return_value = False

        assert agent.is_healthy() is False

    def test_get_status_returns_agent_info(self):
        """Test get_status returns correct information."""
        agent = ClaudeCodeLocalAgent()
        agent.state = ProcessState.READY
        agent.workspace_path = Path("/test/workspace")
        agent.process = MagicMock()
        agent.process.pid = 12345

        with patch.object(agent, 'is_healthy', return_value=True):
            status = agent.get_status()

        assert status['agent_type'] == 'claude-code-local'
        assert status['state'] == 'ready'
        assert status['healthy'] is True
        assert status['pid'] == 12345
        assert status['workspace'] == '/test/workspace'
        assert status['command'] == 'claude'

    def test_cleanup_stops_reading_threads(self, tmp_path):
        """Test cleanup stops reader threads."""
        agent = ClaudeCodeLocalAgent()

        config = {
            'workspace_path': str(tmp_path),
            'claude_command': 'echo',
        }

        with patch('subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_process.poll.return_value = None
            mock_popen.return_value = mock_process

            with patch.object(agent, '_wait_for_ready', return_value=True):
                agent.initialize(config)

        # Threads should be running
        assert agent._stdout_thread.is_alive()

        agent.cleanup()

        # Threads should be stopped
        assert agent._stop_reading.is_set()

    def test_cleanup_graceful_shutdown(self):
        """Test cleanup attempts graceful shutdown first."""
        agent = ClaudeCodeLocalAgent()
        agent.state = ProcessState.READY

        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_process.wait.return_value = None  # Exits gracefully
        agent.process = mock_process

        agent.cleanup()

        # Should send SIGINT
        mock_process.send_signal.assert_called_once_with(subprocess.signal.SIGINT)
        mock_process.wait.assert_called()

    def test_cleanup_force_terminate_on_timeout(self):
        """Test cleanup terminates if graceful shutdown times out."""
        agent = ClaudeCodeLocalAgent()
        agent.state = ProcessState.READY

        mock_process = MagicMock()
        mock_process.poll.return_value = None

        # First wait times out, second succeeds
        mock_process.wait.side_effect = [
            subprocess.TimeoutExpired('cmd', 5),
            None
        ]
        agent.process = mock_process

        agent.cleanup()

        # Should try SIGINT, then terminate
        mock_process.send_signal.assert_called_once()
        mock_process.terminate.assert_called_once()

    def test_cleanup_force_kill_on_terminate_timeout(self):
        """Test cleanup kills process if terminate times out."""
        agent = ClaudeCodeLocalAgent()
        agent.state = ProcessState.READY

        mock_process = MagicMock()
        mock_process.poll.return_value = None

        # Both waits time out
        mock_process.wait.side_effect = [
            subprocess.TimeoutExpired('cmd', 5),
            subprocess.TimeoutExpired('cmd', 3),
            None
        ]
        agent.process = mock_process

        agent.cleanup()

        # Should try SIGINT, terminate, then kill
        mock_process.send_signal.assert_called_once()
        mock_process.terminate.assert_called_once()
        mock_process.kill.assert_called_once()

    def test_cleanup_transitions_to_stopped(self):
        """Test cleanup transitions state to STOPPED."""
        agent = ClaudeCodeLocalAgent()
        agent.state = ProcessState.READY
        agent.process = MagicMock()
        agent.process.poll.return_value = None
        agent.process.wait.return_value = None

        agent.cleanup()

        assert agent.state == ProcessState.STOPPED

    def test_cleanup_idempotent(self):
        """Test cleanup can be called multiple times safely."""
        agent = ClaudeCodeLocalAgent()
        agent.state = ProcessState.STOPPED

        # Should not raise
        agent.cleanup()
        agent.cleanup()

        assert agent.state == ProcessState.STOPPED

    def test_thread_safety_send_prompt(self):
        """Test send_prompt is thread-safe."""
        agent = ClaudeCodeLocalAgent()
        agent.state = ProcessState.READY
        agent.process = MagicMock()
        agent.process.poll.return_value = None

        errors = []

        def send_multiple():
            try:
                for _ in range(3):
                    with patch.object(agent, '_read_response', return_value="ok"):
                        agent.send_prompt("test")
                        agent.state = ProcessState.READY  # Reset for next iteration
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=send_multiple) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5.0)

        assert len(errors) == 0

    def test_plugin_registration(self):
        """Test agent is registered in plugin system."""
        # Force re-import to trigger decorator registration
        import importlib
        import src.agents.claude_code_local
        importlib.reload(src.agents.claude_code_local)

        from src.plugins.registry import AgentRegistry
        from src.agents.claude_code_local import ClaudeCodeLocalAgent

        assert 'claude-code-local' in AgentRegistry._agents
        assert AgentRegistry.get('claude-code-local') == ClaudeCodeLocalAgent


class TestProcessStateEnum:
    """Test ProcessState enum."""

    def test_all_states_defined(self):
        """Test all expected states are defined."""
        expected_states = {'STOPPED', 'STARTING', 'READY', 'BUSY', 'ERROR', 'STOPPING'}
        actual_states = {state.name for state in ProcessState}

        assert actual_states == expected_states

    def test_state_values(self):
        """Test state string values."""
        assert ProcessState.STOPPED.value == "stopped"
        assert ProcessState.STARTING.value == "starting"
        assert ProcessState.READY.value == "ready"
        assert ProcessState.BUSY.value == "busy"
        assert ProcessState.ERROR.value == "error"
        assert ProcessState.STOPPING.value == "stopping"
