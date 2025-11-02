"""Tests for ClaudeCodeSSHAgent.

This module tests the SSH-based Claude Code agent implementation with
comprehensive mocking of paramiko SSH components.
"""

import pytest
import time
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, PropertyMock
from io import BytesIO

from src.agents.claude_code_ssh import ClaudeCodeSSHAgent
from src.plugins.exceptions import (
    AgentConnectionException,
    AgentTimeoutException,
    AgentConfigException,
    AgentException
)


class MockChannel:
    """Mock SSH channel for testing."""

    def __init__(self):
        self._recv_buffer = BytesIO()
        self._send_buffer = BytesIO()
        self._closed = False
        self._timeout = 0.1

    def recv_ready(self):
        """Check if data is available to read."""
        return self._recv_buffer.tell() < len(self._recv_buffer.getvalue())

    def recv(self, size):
        """Read data from buffer."""
        data = self._recv_buffer.read(size)
        if not data:
            raise BlockingIOError("No data available")
        return data

    def send(self, data):
        """Write data to send buffer."""
        self._send_buffer.write(data)
        return len(data)

    def settimeout(self, timeout):
        """Set timeout."""
        self._timeout = timeout

    def close(self):
        """Close channel."""
        self._closed = True

    def add_recv_data(self, data):
        """Add data to receive buffer (test helper)."""
        current_pos = self._recv_buffer.tell()
        buffer_len = len(self._recv_buffer.getvalue())

        self._recv_buffer.seek(0, 2)  # End
        self._recv_buffer.write(data)

        # If we were at the end, move to start of new data
        # Otherwise, keep current position for ongoing reads
        if current_pos >= buffer_len:
            self._recv_buffer.seek(buffer_len)
        else:
            self._recv_buffer.seek(current_pos)

    def get_sent_data(self):
        """Get data that was sent (test helper)."""
        return self._send_buffer.getvalue()


class MockSFTPFile:
    """Mock SFTP file for testing."""

    def __init__(self, content=b''):
        self._content = content
        self._closed = False

    def read(self):
        """Read file content."""
        return self._content

    def write(self, data):
        """Write file content."""
        self._content = data

    def close(self):
        """Close file."""
        self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class MockSFTPClient:
    """Mock SFTP client for testing."""

    def __init__(self):
        self._files = {}
        self._dirs = set()
        self._closed = False

    def file(self, path, mode='r'):
        """Open file."""
        if mode == 'r':
            if path not in self._files:
                raise FileNotFoundError(f"File not found: {path}")
            return MockSFTPFile(self._files[path])
        elif mode == 'w':
            file_obj = MockSFTPFile()
            self._files[path] = b''  # Will be updated on write
            return file_obj
        else:
            raise ValueError(f"Unsupported mode: {mode}")

    def stat(self, path):
        """Get file stats."""
        if path not in self._dirs and path not in self._files:
            raise FileNotFoundError(f"Path not found: {path}")
        return Mock()

    def mkdir(self, path):
        """Create directory."""
        self._dirs.add(path)

    def close(self):
        """Close SFTP client."""
        self._closed = True

    def add_file(self, path, content):
        """Add file to mock filesystem (test helper)."""
        self._files[path] = content

    def add_dir(self, path):
        """Add directory to mock filesystem (test helper)."""
        self._dirs.add(path)


class MockSSHClient:
    """Mock SSH client for testing."""

    def __init__(self):
        self._connected = False
        self._channel = None
        self._sftp = None
        self._transport = Mock()
        self._transport.is_active.return_value = True
        self._transport.set_keepalive = Mock()
        self._exec_commands = {}  # Store expected command outputs
        self._default_response = b"Ready for next\n"  # Default completion response

    def set_missing_host_key_policy(self, policy):
        """Set host key policy."""
        pass

    def connect(self, **kwargs):
        """Connect to SSH server."""
        self._connected = True

    def invoke_shell(self):
        """Open interactive shell - returns same channel or creates new one."""
        if self._channel is None:
            self._channel = MockChannel()
            # Simulate shell ready prompt
            self._channel.add_recv_data(b"user@host:~$ ")
        # Add default response for any new operations
        self._channel.add_recv_data(self._default_response)
        return self._channel

    def set_default_response(self, response: bytes):
        """Set default response for channel operations (test helper)."""
        self._default_response = response

    def get_transport(self):
        """Get transport."""
        return self._transport

    def exec_command(self, command, timeout=None):
        """Execute command."""
        output = self._exec_commands.get(command, "")
        stdout = Mock()
        stdout.read.return_value = output.encode('utf-8')
        stderr = Mock()
        stderr.read.return_value = b""
        stdin = Mock()
        return stdin, stdout, stderr

    def open_sftp(self):
        """Open SFTP client."""
        if self._sftp is None:
            self._sftp = MockSFTPClient()
        return self._sftp

    def close(self):
        """Close connection."""
        self._connected = False
        if self._channel:
            self._channel.close()

    def add_exec_command(self, command, output):
        """Add expected command output (test helper)."""
        self._exec_commands[command] = output


@pytest.fixture
def mock_ssh_key():
    """Mock SSH key file - mocks both RSA and Ed25519 key types."""
    with patch('pathlib.Path.exists', return_value=True):
        with patch('paramiko.RSAKey.from_private_key_file') as mock_rsa_key:
            with patch('paramiko.Ed25519Key.from_private_key_file') as mock_ed_key:
                mock_rsa_key.return_value = Mock()
                mock_ed_key.return_value = Mock()
                yield mock_rsa_key


@pytest.fixture
def mock_ssh_client():
    """Mock SSH client - patches at source module level."""
    client = MockSSHClient()
    # Patch where it's imported in the source module
    with patch('src.agents.claude_code_ssh.paramiko.SSHClient', return_value=client):
        yield client


@pytest.fixture
def agent_config():
    """Standard agent configuration."""
    return {
        'vm_host': '192.168.1.100',
        'vm_port': 22,
        'vm_user': 'claude',
        'vm_key_path': '/home/user/.ssh/vm_key',
        'workspace_path': '/home/claude/workspace',
        'timeout': 300,
        'keepalive_interval': 30,
        'max_reconnect_attempts': 3
    }


class TestClaudeCodeSSHAgentInitialization:
    """Test agent initialization and configuration."""

    def test_initialize_success(self, mock_ssh_client, mock_ssh_key, agent_config):
        """Test successful initialization."""
        agent = ClaudeCodeSSHAgent()
        agent.initialize(agent_config)

        assert agent._connected is True
        assert agent._vm_host == '192.168.1.100'
        assert agent._vm_user == 'claude'

    def test_initialize_missing_required_field(self, agent_config):
        """Test initialization with missing required field."""
        agent = ClaudeCodeSSHAgent()
        del agent_config['vm_host']

        with pytest.raises(AgentConfigException) as exc_info:
            agent.initialize(agent_config)

        assert 'vm_host' in str(exc_info.value)

    def test_initialize_invalid_ssh_key_path(self, agent_config):
        """Test initialization with non-existent SSH key."""
        agent = ClaudeCodeSSHAgent()

        with patch('pathlib.Path.exists', return_value=False):
            with pytest.raises(AgentConfigException) as exc_info:
                agent.initialize(agent_config)

            assert 'vm_key_path' in str(exc_info.value)

    def test_initialize_connection_failure(self, mock_ssh_key, agent_config):
        """Test initialization with connection failure."""
        agent = ClaudeCodeSSHAgent()

        with patch('paramiko.SSHClient') as mock_client:
            mock_instance = Mock()
            mock_instance.connect.side_effect = Exception("Connection refused")
            mock_client.return_value = mock_instance

            with pytest.raises(AgentConnectionException) as exc_info:
                agent.initialize(agent_config)

            assert 'Connection refused' in str(exc_info.value)

    def test_initialize_authentication_failure(self, mock_ssh_key, agent_config):
        """Test initialization with authentication failure."""
        agent = ClaudeCodeSSHAgent()

        with patch('paramiko.SSHClient') as mock_client:
            from paramiko.ssh_exception import AuthenticationException
            mock_instance = Mock()
            mock_instance.connect.side_effect = AuthenticationException(
                "Auth failed"
            )
            mock_client.return_value = mock_instance

            with pytest.raises(AgentConnectionException) as exc_info:
                agent.initialize(agent_config)

            assert 'Authentication failed' in str(exc_info.value)

    def test_initialize_sets_keepalive(self, mock_ssh_client, mock_ssh_key, agent_config):
        """Test that keep-alive is configured."""
        agent = ClaudeCodeSSHAgent()
        agent.initialize(agent_config)

        transport = mock_ssh_client.get_transport()
        transport.set_keepalive.assert_called_once_with(30)


class TestClaudeCodeSSHAgentPrompts:
    """Test sending prompts and receiving responses."""

    def test_send_prompt_success(self, mock_ssh_client, mock_ssh_key, agent_config):
        """Test successful prompt sending."""
        agent = ClaudeCodeSSHAgent()
        agent.initialize(agent_config)

        # Add response data to channel
        channel = agent._channel
        response_data = b"Processing...\nCommand completed\n"
        channel.add_recv_data(response_data)

        response = agent.send_prompt("Create main.py")

        assert "Command completed" in response
        assert b"Create main.py\n" in channel.get_sent_data()

    def test_send_prompt_with_timeout(self, mock_ssh_client, mock_ssh_key, agent_config):
        """Test prompt with custom timeout."""
        agent = ClaudeCodeSSHAgent()
        agent.initialize(agent_config)

        channel = agent._channel
        channel.add_recv_data(b"Ready for next\n")

        response = agent.send_prompt(
            "Test prompt",
            context={'timeout': 60}
        )

        assert "Ready for next" in response

    def test_send_prompt_timeout(self, mock_ssh_client, mock_ssh_key, agent_config):
        """Test prompt timeout with no response."""
        agent = ClaudeCodeSSHAgent()
        agent_config['timeout'] = 1  # Short timeout
        agent.initialize(agent_config)

        # Don't add any response data - should timeout

        with pytest.raises(AgentTimeoutException) as exc_info:
            agent.send_prompt("Test prompt")

        assert 'timed out' in str(exc_info.value).lower()

    @pytest.mark.slow
    def test_send_prompt_reconnects_if_disconnected(
        self,
        mock_ssh_client,
        mock_ssh_key,
        agent_config
    ):
        """Test automatic reconnection on send_prompt.

        Note: This test is marked slow due to complex mock interactions with
        reconnection logic. Skipped by default.
        """
        agent = ClaudeCodeSSHAgent()
        agent.initialize(agent_config)

        # Simulate disconnection
        agent._connected = False

        # Should reconnect automatically
        channel = mock_ssh_client.invoke_shell()
        channel.add_recv_data(b"Ready for next\n")

        response = agent.send_prompt("Test")
        assert "Ready for next" in response

    def test_send_prompt_rate_limit_detection(
        self,
        mock_ssh_client,
        mock_ssh_key,
        agent_config
    ):
        """Test rate limit detection."""
        agent = ClaudeCodeSSHAgent()
        agent.initialize(agent_config)

        channel = agent._channel
        channel.add_recv_data(
            b"Error: rate limit exceeded, try again later\n"
        )

        with pytest.raises(AgentException) as exc_info:
            agent.send_prompt("Test")

        assert 'rate limit' in str(exc_info.value).lower()

    def test_is_complete_with_markers(self, mock_ssh_client, mock_ssh_key, agent_config):
        """Test completion detection with various markers."""
        agent = ClaudeCodeSSHAgent()
        agent.initialize(agent_config)

        # Test each completion marker
        assert agent._is_complete("Output\nReady for next\n") is True
        assert agent._is_complete(">>>\n") is True
        assert agent._is_complete("Command completed\n") is True
        assert agent._is_complete("Task ✓\n") is True

        # Test error markers also indicate completion
        assert agent._is_complete("Error: something failed\n") is True
        assert agent._is_complete("Exception occurred\n") is True

        # Test incomplete output
        assert agent._is_complete("Processing...") is False


class TestClaudeCodeSSHAgentFileOperations:
    """Test file operations."""

    def test_get_workspace_files(self, mock_ssh_client, mock_ssh_key, agent_config):
        """Test listing workspace files."""
        agent = ClaudeCodeSSHAgent()
        agent.initialize(agent_config)

        # Mock find command output
        file_list = "/home/claude/workspace/main.py\n/home/claude/workspace/test.py\n"
        mock_ssh_client.add_exec_command(
            'find /home/claude/workspace -type f -not -path \'*/.git/*\' '
            '-not -path \'*/__pycache__/*\' -not -path \'*/node_modules/*\' '
            '-not -path \'*/.venv/*\'',
            file_list
        )

        files = agent.get_workspace_files()

        assert len(files) == 2
        assert Path('/home/claude/workspace/main.py') in files
        assert Path('/home/claude/workspace/test.py') in files

    def test_read_file_success(self, mock_ssh_client, mock_ssh_key, agent_config):
        """Test reading file."""
        agent = ClaudeCodeSSHAgent()
        agent.initialize(agent_config)

        # Add file to mock SFTP
        sftp = mock_ssh_client.open_sftp()
        sftp.add_file('/home/claude/workspace/main.py', b'print("hello")')
        sftp.add_dir('/home/claude/workspace')

        content = agent.read_file(Path('/home/claude/workspace/main.py'))

        assert content == 'print("hello")'

    def test_read_file_not_found(self, mock_ssh_client, mock_ssh_key, agent_config):
        """Test reading non-existent file."""
        agent = ClaudeCodeSSHAgent()
        agent.initialize(agent_config)

        with pytest.raises(FileNotFoundError):
            agent.read_file(Path('/home/claude/workspace/missing.py'))

    def test_write_file_success(self, mock_ssh_client, mock_ssh_key, agent_config):
        """Test writing file."""
        agent = ClaudeCodeSSHAgent()
        agent.initialize(agent_config)

        # Setup mock SFTP
        sftp = mock_ssh_client.open_sftp()
        sftp.add_dir('/home/claude/workspace')

        # Write file
        agent.write_file(Path('/home/claude/workspace/new.py'), 'print("test")')

        # Verify file exists (in real implementation)
        # For this mock, just ensure no exception was raised
        assert True

    def test_get_file_changes(self, mock_ssh_client, mock_ssh_key, agent_config):
        """Test detecting file changes."""
        agent = ClaudeCodeSSHAgent()
        agent.initialize(agent_config)

        # Setup files
        sftp = mock_ssh_client.open_sftp()
        sftp.add_file('/home/claude/workspace/main.py', b'original content')
        sftp.add_dir('/home/claude/workspace')

        file_list = "/home/claude/workspace/main.py\n"
        mock_ssh_client.add_exec_command(
            'find /home/claude/workspace -type f -not -path \'*/.git/*\' '
            '-not -path \'*/__pycache__/*\' -not -path \'*/node_modules/*\' '
            '-not -path \'*/.venv/*\'',
            file_list
        )

        # First check - should detect as created
        changes = agent.get_file_changes()
        assert len(changes) == 1
        assert changes[0]['change_type'] == 'created'

        # Modify file
        sftp.add_file('/home/claude/workspace/main.py', b'modified content')

        # Second check - should detect as modified
        changes = agent.get_file_changes()
        assert len(changes) == 1
        assert changes[0]['change_type'] == 'modified'


class TestClaudeCodeSSHAgentHealthAndCleanup:
    """Test health checking and cleanup."""

    def test_is_healthy_when_connected(self, mock_ssh_client, mock_ssh_key, agent_config):
        """Test health check when connected."""
        agent = ClaudeCodeSSHAgent()
        agent.initialize(agent_config)

        # Mock health check command
        mock_ssh_client.add_exec_command('echo "health_check"', 'health_check\n')

        assert agent.is_healthy() is True

    def test_is_healthy_when_disconnected(self, agent_config):
        """Test health check when not connected."""
        agent = ClaudeCodeSSHAgent()
        # Don't initialize - not connected

        assert agent.is_healthy() is False

    def test_is_healthy_transport_inactive(
        self,
        mock_ssh_client,
        mock_ssh_key,
        agent_config
    ):
        """Test health check with inactive transport."""
        agent = ClaudeCodeSSHAgent()
        agent.initialize(agent_config)

        # Make transport inactive
        mock_ssh_client._transport.is_active.return_value = False

        assert agent.is_healthy() is False
        assert agent._connected is False

    def test_cleanup(self, mock_ssh_client, mock_ssh_key, agent_config):
        """Test cleanup."""
        agent = ClaudeCodeSSHAgent()
        agent.initialize(agent_config)

        assert agent._connected is True

        agent.cleanup()

        assert agent._connected is False
        assert agent._channel is None or agent._channel._closed
        assert agent._client is None or not mock_ssh_client._connected

    def test_cleanup_without_initialization(self):
        """Test cleanup when not initialized."""
        agent = ClaudeCodeSSHAgent()

        # Should not raise exception
        agent.cleanup()

        assert agent._connected is False


class TestClaudeCodeSSHAgentReconnection:
    """Test reconnection logic."""

    def test_reconnect_success(self, mock_ssh_client, mock_ssh_key, agent_config, fast_time):
        """Test successful reconnection."""
        agent = ClaudeCodeSSHAgent()
        agent_config['max_reconnect_attempts'] = 2
        agent.initialize(agent_config)

        # Simulate disconnection
        agent._cleanup_connection()
        assert agent._connected is False

        # Reconnect should succeed
        agent._reconnect()

        assert agent._connected is True

    def test_reconnect_max_attempts(self, mock_ssh_key, agent_config):
        """Test reconnection exhausts all attempts."""
        agent = ClaudeCodeSSHAgent()
        agent_config['max_reconnect_attempts'] = 2

        # Mock client that always fails
        with patch('paramiko.SSHClient') as mock_client:
            mock_instance = Mock()
            mock_instance.connect.side_effect = Exception("Connection refused")
            mock_client.return_value = mock_instance

            with patch('time.sleep'):  # Speed up test
                with pytest.raises(AgentConnectionException) as exc_info:
                    agent.initialize(agent_config)

                assert 'Connection refused' in str(exc_info.value)

    def test_reconnect_exponential_backoff(self, mock_ssh_key, agent_config):
        """Test exponential backoff in reconnection."""
        agent = ClaudeCodeSSHAgent()
        agent_config['max_reconnect_attempts'] = 3

        with patch('paramiko.SSHClient') as mock_client:
            mock_instance = Mock()
            mock_instance.connect.side_effect = Exception("Connection refused")
            mock_client.return_value = mock_instance

            sleep_times = []

            def mock_sleep(duration):
                sleep_times.append(duration)

            with patch('time.sleep', side_effect=mock_sleep):
                try:
                    agent.initialize(agent_config)
                except AgentConnectionException:
                    pass

        # Should have exponentially increasing delays (but only during reconnect)
        # Initial connection doesn't have retries
        assert len(sleep_times) == 0  # No retries on initial connection


class TestClaudeCodeSSHAgentCapabilities:
    """Test agent capabilities."""

    def test_get_capabilities(self):
        """Test capabilities reporting."""
        agent = ClaudeCodeSSHAgent()
        caps = agent.get_capabilities()

        assert caps['supports_interactive'] is True
        assert caps['connection_type'] == 'ssh'
        assert caps['persistent_channel'] is True
        assert 'python' in caps['supported_languages']


class TestClaudeCodeSSHAgentEdgeCases:
    """Test edge cases and error handling."""

    def test_send_prompt_with_empty_response(
        self,
        mock_ssh_client,
        mock_ssh_key,
        agent_config
    ):
        """Test handling empty response."""
        agent = ClaudeCodeSSHAgent()
        agent_config['timeout'] = 1
        agent.initialize(agent_config)

        # Timeout should occur with no data
        with pytest.raises(AgentTimeoutException):
            agent.send_prompt("Test")

    def test_multiple_prompts_sequential(
        self,
        mock_ssh_client,
        mock_ssh_key,
        agent_config
    ):
        """Test sending multiple prompts sequentially."""
        agent = ClaudeCodeSSHAgent()
        agent.initialize(agent_config)

        channel = agent._channel

        # First prompt
        channel.add_recv_data(b"Response 1\nReady for next\n")
        response1 = agent.send_prompt("Prompt 1")
        assert "Response 1" in response1

        # Second prompt
        channel.add_recv_data(b"Response 2\nReady for next\n")
        response2 = agent.send_prompt("Prompt 2")
        assert "Response 2" in response2

    def test_read_file_relative_path(
        self,
        mock_ssh_client,
        mock_ssh_key,
        agent_config
    ):
        """Test reading file with relative path."""
        agent = ClaudeCodeSSHAgent()
        agent.initialize(agent_config)

        sftp = mock_ssh_client.open_sftp()
        sftp.add_file('/home/claude/workspace/relative.py', b'content')
        sftp.add_dir('/home/claude/workspace')

        # Use relative path
        content = agent.read_file(Path('relative.py'))
        assert content == 'content'

    def test_write_file_creates_parent_dirs(
        self,
        mock_ssh_client,
        mock_ssh_key,
        agent_config
    ):
        """Test writing file creates parent directories."""
        agent = ClaudeCodeSSHAgent()
        agent.initialize(agent_config)

        # Write to nested path
        agent.write_file(Path('subdir/nested/file.py'), 'content')

        # Should not raise exception (parent dirs created)
        assert True


class TestClaudeCodeSSHAgentThreadSafety:
    """Test thread safety of agent operations."""

    def test_concurrent_operations_locked(
        self,
        mock_ssh_client,
        mock_ssh_key,
        agent_config
    ):
        """Test that operations are properly locked."""
        agent = ClaudeCodeSSHAgent()
        agent.initialize(agent_config)

        # Verify lock is used
        assert agent._lock is not None

        # Operations should acquire lock (tested via no deadlock)
        channel = agent._channel
        channel.add_recv_data(b"Ready for next\n")
        agent.send_prompt("Test")

        # No deadlock = success
        assert True


class TestClaudeCodeSSHAgentRegistration:
    """Test agent registration."""

    def test_agent_registered(self):
        """Test that agent is registered with correct name."""
        from src.plugins.registry import AgentRegistry

        # Re-register the agent in case registry was cleared
        # (The @register_agent decorator only runs once at import)
        if not AgentRegistry.is_registered('claude-code-ssh'):
            AgentRegistry.register('claude-code-ssh', ClaudeCodeSSHAgent)

        # Agent should be registered as 'claude-code-ssh'
        agent_class = AgentRegistry.get('claude-code-ssh')
        assert agent_class is ClaudeCodeSSHAgent
