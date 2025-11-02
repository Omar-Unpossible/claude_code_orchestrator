"""Claude Code agent implementation using SSH connection to VM.

This module provides ClaudeCodeSSHAgent, which connects to Claude Code running
in a VM via SSH and manages interactive sessions with persistent channels.

Features:
- Persistent SSH channel (not reconnecting per prompt)
- Non-blocking output reading
- Automatic reconnection with exponential backoff
- Rate limit detection from output patterns
- Process health monitoring with keep-alive
- Graceful shutdown with signal handling
- Timeout handling per operation
"""

import re
import socket
import time
import hashlib
import threading
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

try:
    import paramiko
    from paramiko.ssh_exception import SSHException, AuthenticationException
except ImportError:
    raise ImportError(
        "paramiko is required for ClaudeCodeSSHAgent. "
        "Install with: pip install paramiko"
    )

from src.plugins.base import AgentPlugin
from src.plugins.registry import register_agent
from src.plugins.exceptions import (
    AgentException,
    AgentConnectionException,
    AgentTimeoutException,
    AgentProcessException,
    AgentConfigException
)

logger = logging.getLogger(__name__)


@register_agent('claude-code-ssh')
class ClaudeCodeSSHAgent(AgentPlugin):
    """Claude Code agent accessed via SSH to VM.

    This agent connects to Claude Code running in an isolated VM via SSH,
    maintaining a persistent interactive channel for sending prompts and
    receiving responses.

    Configuration:
        vm_host: Hostname or IP address of VM
        vm_port: SSH port (default: 22)
        vm_user: SSH username
        vm_key_path: Path to SSH private key file
        workspace_path: Path to workspace directory on VM
        timeout: Default timeout for operations in seconds (default: 300)
        keepalive_interval: Keep-alive interval in seconds (default: 30)
        max_reconnect_attempts: Maximum reconnection attempts (default: 5)

    Example:
        >>> agent = ClaudeCodeSSHAgent()
        >>> agent.initialize({
        ...     'vm_host': '192.168.1.100',
        ...     'vm_user': 'claude',
        ...     'vm_key_path': '~/.ssh/vm_key',
        ...     'workspace_path': '/home/claude/workspace'
        ... })
        >>> response = agent.send_prompt("Create main.py")
        >>> agent.cleanup()

    Thread-safety:
        Thread-safe with internal locking for connection operations.
    """

    # Output detection patterns
    COMPLETION_MARKERS = [
        "Ready for next",
        ">>>",
        "Command completed",
        "✓",  # Claude Code success marker
    ]

    ERROR_MARKERS = [
        "Error:",
        "Error ",  # Match "Error " (with space)
        "Exception:",
        "Exception ",  # Match "Exception " (with space)
        "Traceback:",
        "FAILED",
        "✗",  # Claude Code error marker
    ]

    RATE_LIMIT_MARKERS = [
        "rate limit",
        "too many requests",
        "try again later",
        "quota exceeded",
    ]

    def __init__(self):
        """Initialize SSH agent (call initialize() to connect)."""
        self._client: Optional[paramiko.SSHClient] = None
        self._channel: Optional[paramiko.Channel] = None
        self._lock = threading.RLock()
        self._connected = False
        self._config: Dict[str, Any] = {}
        self._file_hashes: Dict[Path, str] = {}  # Track file changes

        # Configuration values (set in initialize)
        self._vm_host: str = ''
        self._vm_port: int = 22
        self._vm_user: str = ''
        self._vm_key_path: str = ''
        self._workspace_path: Path = Path()
        self._timeout: int = 300
        self._keepalive_interval: int = 30
        self._max_reconnect_attempts: int = 5

    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize agent with SSH configuration.

        Args:
            config: Configuration dictionary with keys:
                - vm_host: VM hostname/IP (required)
                - vm_user: SSH username (required)
                - vm_key_path: SSH key path (required)
                - workspace_path: Workspace directory (required)
                - vm_port: SSH port (default: 22)
                - timeout: Operation timeout in seconds (default: 300)
                - keepalive_interval: Keep-alive seconds (default: 30)
                - max_reconnect_attempts: Max reconnection tries (default: 5)

        Raises:
            AgentConfigException: If configuration is invalid
            AgentConnectionException: If unable to connect to VM
        """
        logger.info("Initializing ClaudeCodeSSHAgent")
        self._config = config

        # Validate required fields
        required = ['vm_host', 'vm_user', 'vm_key_path', 'workspace_path']
        for field in required:
            if field not in config:
                raise AgentConfigException(
                    agent_type='claude-code-ssh',
                    config_key=field,
                    details='Required field missing'
                )

        # Load configuration
        self._vm_host = config['vm_host']
        self._vm_port = config.get('vm_port', 22)
        self._vm_user = config['vm_user']
        self._vm_key_path = str(Path(config['vm_key_path']).expanduser())
        self._workspace_path = Path(config['workspace_path'])
        self._timeout = config.get('timeout', 300)
        self._keepalive_interval = config.get('keepalive_interval', 30)
        self._max_reconnect_attempts = config.get('max_reconnect_attempts', 5)

        # Validate SSH key exists
        if not Path(self._vm_key_path).exists():
            raise AgentConfigException(
                agent_type='claude-code-ssh',
                config_key='vm_key_path',
                details=f'SSH key file not found: {self._vm_key_path}'
            )

        # Connect to VM
        self._connect()

        logger.info(
            f"ClaudeCodeSSHAgent initialized: {self._vm_user}@{self._vm_host}"
        )

    def _connect(self) -> None:
        """Establish SSH connection and interactive channel.

        Creates persistent SSH connection with:
        - Key-based authentication
        - Keep-alive enabled
        - Interactive shell channel

        Raises:
            AgentConnectionException: If connection fails
        """
        with self._lock:
            logger.info(f"Connecting to {self._vm_user}@{self._vm_host}:{self._vm_port}")

            try:
                # Create SSH client
                self._client = paramiko.SSHClient()
                self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

                # Load private key
                try:
                    private_key = paramiko.RSAKey.from_private_key_file(
                        self._vm_key_path
                    )
                except Exception as e:
                    # Try other key types
                    try:
                        private_key = paramiko.Ed25519Key.from_private_key_file(
                            self._vm_key_path
                        )
                    except Exception:
                        raise AgentConfigException(
                            agent_type='claude-code-ssh',
                            config_key='vm_key_path',
                            details=f'Unable to load SSH key: {str(e)}'
                        )

                # Connect with timeout
                self._client.connect(
                    hostname=self._vm_host,
                    port=self._vm_port,
                    username=self._vm_user,
                    pkey=private_key,
                    timeout=30,
                    allow_agent=False,
                    look_for_keys=False
                )

                # Enable keep-alive
                transport = self._client.get_transport()
                if transport:
                    transport.set_keepalive(self._keepalive_interval)

                # Open interactive shell channel
                self._channel = self._client.invoke_shell()
                self._channel.settimeout(0.1)  # Non-blocking reads

                self._connected = True
                logger.info("SSH connection established successfully")

                # Wait for shell to be ready
                self._wait_for_ready(timeout=10)

            except AuthenticationException as e:
                raise AgentConnectionException(
                    agent_type='claude-code-ssh',
                    host=self._vm_host,
                    details=f'Authentication failed: {str(e)}'
                )
            except SSHException as e:
                raise AgentConnectionException(
                    agent_type='claude-code-ssh',
                    host=self._vm_host,
                    details=f'SSH error: {str(e)}'
                )
            except Exception as e:
                raise AgentConnectionException(
                    agent_type='claude-code-ssh',
                    host=self._vm_host,
                    details=f'Connection failed: {str(e)}'
                )

    def _reconnect(self) -> None:
        """Reconnect to SSH with exponential backoff.

        Attempts to reconnect up to max_reconnect_attempts times with
        exponentially increasing delays (2s, 4s, 8s, 16s, 32s).

        Raises:
            AgentConnectionException: If all reconnection attempts fail
        """
        logger.warning("SSH connection lost, attempting reconnection")

        # Clean up old connection
        self._cleanup_connection()

        for attempt in range(1, self._max_reconnect_attempts + 1):
            try:
                logger.info(
                    f"Reconnection attempt {attempt}/{self._max_reconnect_attempts}"
                )

                self._connect()
                logger.info("Reconnection successful")
                return

            except AgentConnectionException as e:
                if attempt == self._max_reconnect_attempts:
                    logger.error("All reconnection attempts failed")
                    raise

                # Exponential backoff before retry (except after last attempt)
                delay = min(2 ** attempt, 32)  # Cap at 32 seconds
                logger.warning(f"Attempt {attempt} failed: {e}. Retrying in {delay}s...")
                time.sleep(delay)

    def _cleanup_connection(self) -> None:
        """Clean up SSH connection (internal helper)."""
        self._connected = False

        if self._channel:
            try:
                self._channel.close()
            except Exception:
                pass
            self._channel = None

        if self._client:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None

    def _wait_for_ready(self, timeout: int) -> None:
        """Wait for shell to be ready to accept commands.

        Args:
            timeout: Timeout in seconds

        Raises:
            AgentTimeoutException: If shell doesn't become ready
        """
        start_time = time.time()
        buffer = ""

        while time.time() - start_time < timeout:
            if self._channel and self._channel.recv_ready():
                try:
                    chunk = self._channel.recv(4096).decode('utf-8', errors='ignore')
                    buffer += chunk
                except Exception:
                    pass

            # Check if we see a prompt or ready marker
            if any(marker in buffer for marker in ['$', '#', '>', 'claude']):
                return

            time.sleep(0.1)

        raise AgentTimeoutException(
            operation='wait_for_ready',
            timeout_seconds=timeout,
            agent_type='claude-code-ssh'
        )

    def send_prompt(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Send prompt to Claude Code and wait for response.

        Args:
            prompt: Text prompt to send
            context: Optional context with:
                - timeout: Override default timeout
                - task_id: Current task identifier

        Returns:
            Complete response from Claude Code

        Raises:
            AgentException: If agent encounters an error
            AgentTimeoutException: If operation times out
            AgentProcessException: If agent process crashes
        """
        with self._lock:
            if not self._connected or not self._channel:
                logger.warning("Not connected, attempting to reconnect")
                self._reconnect()

            context = context or {}
            timeout = context.get('timeout', self._timeout)

            logger.info(f"Sending prompt (timeout={timeout}s)")
            logger.debug(f"Prompt: {prompt[:100]}...")

            try:
                # Send prompt via stdin
                prompt_with_newline = prompt + '\n'
                self._channel.send(prompt_with_newline.encode('utf-8'))

                # Wait for and collect response
                response = self._read_response(timeout)

                # Check for rate limiting
                if self._is_rate_limited(response):
                    logger.warning("Rate limit detected in response")
                    raise AgentException(
                        "Rate limit hit",
                        context={'response_preview': response[:200]},
                        recovery="Wait before sending next prompt"
                    )

                logger.info(f"Received response ({len(response)} chars)")
                return response

            except socket.timeout:
                raise AgentTimeoutException(
                    operation='send_prompt',
                    timeout_seconds=timeout,
                    agent_type='claude-code-ssh'
                )
            except AgentTimeoutException:
                # Re-raise timeout exceptions without wrapping
                raise
            except Exception as e:
                logger.error(f"Error during send_prompt: {e}")
                # Try to reconnect on next call
                self._connected = False
                raise AgentException(
                    f"Failed to send prompt: {str(e)}",
                    context={'error': str(e)},
                    recovery="Check SSH connection and agent process"
                )

    def _read_response(self, timeout: int) -> str:
        """Read response from channel until completion.

        Args:
            timeout: Timeout in seconds

        Returns:
            Complete response as string

        Raises:
            AgentTimeoutException: If timeout exceeded
        """
        start_time = time.time()
        buffer = ""
        idle_count = 0
        max_idle_iterations = 10  # 1 second of no data

        while time.time() - start_time < timeout:
            if self._channel and self._channel.recv_ready():
                try:
                    chunk = self._channel.recv(4096).decode('utf-8', errors='ignore')
                    buffer += chunk
                    idle_count = 0  # Reset idle counter

                    # Check for completion
                    if self._is_complete(buffer):
                        return buffer

                except Exception as e:
                    logger.warning(f"Error reading from channel: {e}")
                    # Connection may be broken
                    self._connected = False
                    raise

            else:
                idle_count += 1
                # If we have data and it's been idle, check completion
                if buffer and idle_count >= max_idle_iterations:
                    if self._is_complete(buffer):
                        return buffer

            time.sleep(0.1)

        # Timeout - return what we have
        logger.warning(f"Timeout after {timeout}s, returning partial response")
        raise AgentTimeoutException(
            operation='read_response',
            timeout_seconds=timeout,
            agent_type='claude-code-ssh'
        )

    def _is_complete(self, output: str) -> bool:
        """Check if output appears complete.

        Args:
            output: Output buffer to check

        Returns:
            True if output appears complete
        """
        # Check for completion markers
        for marker in self.COMPLETION_MARKERS:
            if marker in output:
                return True

        # Check for error markers (also indicates completion)
        for marker in self.ERROR_MARKERS:
            if marker in output:
                return True

        return False

    def _is_rate_limited(self, output: str) -> bool:
        """Check if output indicates rate limiting.

        Args:
            output: Output to check

        Returns:
            True if rate limit detected
        """
        output_lower = output.lower()
        return any(marker in output_lower for marker in self.RATE_LIMIT_MARKERS)

    def get_workspace_files(self) -> List[Path]:
        """Get list of files in workspace.

        Returns:
            List of Path objects for workspace files

        Raises:
            AgentException: If unable to list files
        """
        with self._lock:
            if not self._connected or not self._client:
                self._reconnect()

            try:
                # Use find command to list files (exclude common ignore patterns)
                cmd = (
                    f"find {self._workspace_path} -type f "
                    f"-not -path '*/.git/*' "
                    f"-not -path '*/__pycache__/*' "
                    f"-not -path '*/node_modules/*' "
                    f"-not -path '*/.venv/*'"
                )

                stdin, stdout, stderr = self._client.exec_command(cmd, timeout=30)

                # Set channel timeout to prevent blocking reads
                stdout.channel.settimeout(30)
                stderr.channel.settimeout(30)

                output = stdout.read().decode('utf-8')
                errors = stderr.read().decode('utf-8')

                if errors:
                    logger.warning(f"Errors listing files: {errors}")

                # Parse output into Path objects
                files = [
                    Path(line.strip())
                    for line in output.strip().split('\n')
                    if line.strip()
                ]

                logger.info(f"Found {len(files)} files in workspace")
                return files

            except Exception as e:
                raise AgentException(
                    f"Failed to list workspace files: {str(e)}",
                    context={'workspace': str(self._workspace_path)},
                    recovery="Check workspace path and permissions"
                )

    def read_file(self, path: Path) -> str:
        """Read file contents from workspace.

        Args:
            path: Path to file (relative to workspace or absolute)

        Returns:
            File contents as string

        Raises:
            FileNotFoundError: If file doesn't exist
            AgentException: If unable to read file
        """
        with self._lock:
            if not self._connected or not self._client:
                self._reconnect()

            # Make path absolute relative to workspace
            if not path.is_absolute():
                path = self._workspace_path / path

            try:
                sftp = self._client.open_sftp()
                try:
                    with sftp.file(str(path), 'r') as f:
                        content = f.read().decode('utf-8')
                    logger.debug(f"Read file: {path} ({len(content)} bytes)")
                    return content
                finally:
                    sftp.close()

            except FileNotFoundError:
                raise
            except Exception as e:
                raise AgentException(
                    f"Failed to read file {path}: {str(e)}",
                    context={'path': str(path)},
                    recovery="Check file exists and is readable"
                )

    def write_file(self, path: Path, content: str) -> None:
        """Write content to file in workspace.

        Args:
            path: Path to file (relative to workspace or absolute)
            content: Content to write

        Raises:
            AgentException: If unable to write file
        """
        with self._lock:
            if not self._connected or not self._client:
                self._reconnect()

            # Make path absolute relative to workspace
            if not path.is_absolute():
                path = self._workspace_path / path

            try:
                sftp = self._client.open_sftp()
                try:
                    # Create parent directories if needed
                    parent = Path(path).parent
                    try:
                        sftp.stat(str(parent))
                    except FileNotFoundError:
                        # Create directory
                        self._create_directory(sftp, parent)

                    # Write file
                    with sftp.file(str(path), 'w') as f:
                        f.write(content.encode('utf-8'))

                    logger.debug(f"Wrote file: {path} ({len(content)} bytes)")

                finally:
                    sftp.close()

            except Exception as e:
                raise AgentException(
                    f"Failed to write file {path}: {str(e)}",
                    context={'path': str(path)},
                    recovery="Check workspace permissions"
                )

    def _create_directory(self, sftp, path: Path) -> None:
        """Recursively create directory via SFTP.

        Args:
            sftp: SFTP client
            path: Directory path to create
        """
        parent = path.parent
        if parent != path:  # Not root
            try:
                sftp.stat(str(parent))
            except FileNotFoundError:
                self._create_directory(sftp, parent)

        try:
            sftp.mkdir(str(path))
        except Exception:
            # Directory might already exist
            pass

    def get_file_changes(
        self,
        since: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """Get files modified since timestamp.

        Args:
            since: Unix timestamp, or None for all changes since last check

        Returns:
            List of change dictionaries with keys:
                - path: Path object
                - change_type: 'created', 'modified', or 'deleted'
                - timestamp: Unix timestamp
                - hash: File content hash
                - size: File size in bytes
        """
        changes = []
        current_files = self.get_workspace_files()
        current_hashes: Dict[Path, str] = {}

        # Calculate hashes for current files
        for file_path in current_files:
            try:
                content = self.read_file(file_path)
                file_hash = hashlib.sha256(content.encode()).hexdigest()
                current_hashes[file_path] = file_hash

                # Check if file is new or modified
                if file_path not in self._file_hashes:
                    changes.append({
                        'path': file_path,
                        'change_type': 'created',
                        'timestamp': time.time(),
                        'hash': file_hash,
                        'size': len(content)
                    })
                elif self._file_hashes[file_path] != file_hash:
                    changes.append({
                        'path': file_path,
                        'change_type': 'modified',
                        'timestamp': time.time(),
                        'hash': file_hash,
                        'size': len(content)
                    })

            except Exception as e:
                logger.warning(f"Error checking file {file_path}: {e}")

        # Check for deleted files
        for old_path in self._file_hashes:
            if old_path not in current_hashes:
                changes.append({
                    'path': old_path,
                    'change_type': 'deleted',
                    'timestamp': time.time(),
                    'hash': '',
                    'size': 0
                })

        # Update tracked hashes
        self._file_hashes = current_hashes

        logger.info(f"Detected {len(changes)} file changes")
        return changes

    def is_healthy(self) -> bool:
        """Check if agent is responsive.

        Returns:
            True if agent is connected and responsive
        """
        with self._lock:
            if not self._connected or not self._client:
                return False

            try:
                # Quick check: send simple command
                transport = self._client.get_transport()
                if not transport or not transport.is_active():
                    self._connected = False
                    return False

                # Try to execute a simple command
                stdin, stdout, stderr = self._client.exec_command(
                    'echo "health_check"',
                    timeout=5
                )
                # Set channel timeout to prevent blocking
                stdout.channel.settimeout(5)
                output = stdout.read().decode('utf-8').strip()
                return 'health_check' in output

            except Exception as e:
                logger.warning(f"Health check failed: {e}")
                self._connected = False
                return False

    def cleanup(self) -> None:
        """Clean up SSH connection and resources.

        Gracefully closes channel and SSH connection.
        This method does not raise exceptions.
        """
        logger.info("Cleaning up ClaudeCodeSSHAgent")

        with self._lock:
            # Try to send Ctrl+C to stop any running process
            if self._channel:
                try:
                    self._channel.send(b'\x03')  # Ctrl+C
                    time.sleep(0.5)
                except Exception:
                    pass

            self._cleanup_connection()

        logger.info("ClaudeCodeSSHAgent cleanup complete")

    def get_capabilities(self) -> Dict[str, Any]:
        """Get agent capabilities.

        Returns:
            Dictionary with capability information
        """
        return {
            'supports_streaming': False,
            'supports_interactive': True,
            'max_file_size': 100 * 1024 * 1024,  # 100 MB
            'supported_languages': [
                'python', 'javascript', 'typescript', 'java', 'go',
                'rust', 'c', 'cpp', 'ruby', 'php', 'html', 'css'
            ],
            'connection_type': 'ssh',
            'persistent_channel': True
        }
