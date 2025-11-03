"""Local subprocess-based Claude Code agent implementation (headless mode).

This module provides ClaudeCodeLocalAgent, which manages Claude Code CLI
using headless --print mode for reliable, stateless operation.
"""

import hashlib
import logging
import os
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.plugins.base import AgentPlugin
from src.plugins.exceptions import AgentException
from src.plugins.registry import register_agent

logger = logging.getLogger(__name__)


@register_agent('claude-code-local')
class ClaudeCodeLocalAgent(AgentPlugin):
    """Claude Code agent running in headless --print mode.

    Uses subprocess.run() to execute Claude Code CLI with --print flag for
    non-interactive, stateless operation. Session persistence is maintained
    via --session-id flag.

    Key Features:
    - Stateless subprocess calls (no persistent process)
    - Reliable completion detection (subprocess return)
    - Session persistence via --session-id (optional)
    - Dangerous mode for automated orchestration (bypasses permissions)
    - Retry logic with exponential backoff
    - Simple error handling (exit codes)
    - Minimal resource usage

    Attributes:
        claude_command: Command to launch Claude Code CLI
        workspace_path: Path to workspace directory
        session_id: UUID for session persistence across calls
        response_timeout: Timeout in seconds for Claude responses
        environment_vars: Environment variables for Claude subprocess
        bypass_permissions: Enable dangerous mode (default: True for automation)
        use_session_persistence: Reuse session ID (default: False, fresh per call)
    """

    def __init__(self):
        """Initialize the local Claude Code agent (headless mode)."""
        # Configuration attributes (set in initialize)
        self.claude_command: str = 'claude'
        self.workspace_path: Optional[Path] = None
        self.session_id: Optional[str] = None
        self.response_timeout: int = 60
        self.environment_vars: Dict[str, str] = {}

        # Session management
        self.use_session_persistence: bool = False  # Disabled by default (locks cause issues)

        # Retry configuration for session-in-use errors
        self.max_retries: int = 5  # More retries
        self.retry_initial_delay: float = 2.0  # Start with 2s
        self.retry_backoff: float = 1.5  # Exponential backoff multiplier

        # Dangerous mode (bypass permissions for automated orchestration)
        self.bypass_permissions: bool = True  # Enabled by default for Obra

        logger.info('ClaudeCodeLocalAgent initialized (headless mode)')

    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize agent with configuration.

        Args:
            config: Configuration dict containing:
                - workspace_path or workspace_dir: Path to workspace directory (required)
                - claude_command or command: Command to run (default: 'claude')
                - response_timeout or timeout_response: Seconds to wait (default: 60)
                - use_session_persistence: Reuse session ID (default: False)
                - bypass_permissions: Enable dangerous mode (default: True)
                Can also accept nested 'local' dict with these keys.

        Raises:
            AgentException: If configuration is invalid
        """
        # Handle nested config structure (agent.local.*)
        if 'local' in config and isinstance(config['local'], dict):
            config = config['local']

        # Extract workspace path (support both workspace_path and workspace_dir)
        workspace = config.get('workspace_path') or config.get('workspace_dir')
        if not workspace:
            raise AgentException(
                'Missing required config: workspace_path or workspace_dir',
                context={'config': config},
                recovery='Provide workspace_path or workspace_dir in agent configuration'
            )

        self.workspace_path = Path(workspace)

        # Extract command (support both claude_command and command)
        self.claude_command = config.get('claude_command') or config.get('command', 'claude')

        # Extract timeout (support both response_timeout and timeout_response)
        self.response_timeout = (
            config.get('response_timeout') or
            config.get('timeout_response', 60)
        )

        # Extract session persistence preference
        self.use_session_persistence = config.get('use_session_persistence', False)

        # Extract bypass permissions preference (default: True for Obra)
        self.bypass_permissions = config.get('bypass_permissions', True)

        # Generate unique session ID for context persistence (if enabled)
        if self.use_session_persistence:
            self.session_id = str(uuid.uuid4())
            logger.info(f'Session persistence enabled: {self.session_id}')
        else:
            self.session_id = None  # Will generate per-call
            logger.info('Session persistence disabled (fresh session per call)')

        if self.bypass_permissions:
            logger.info('Dangerous mode enabled - permissions bypassed for automation')

        # Create workspace directory if needed
        self.workspace_path.mkdir(parents=True, exist_ok=True)

        # Prepare environment variables
        self.environment_vars = {
            'DISABLE_AUTOUPDATER': '1',
            'CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC': 'true',
            'TERM': os.environ.get('TERM', 'xterm-256color'),
            'PATH': os.environ.get('PATH', '')
        }

        logger.info(
            f'Initialized headless agent: workspace={self.workspace_path}, '
            f'session={self.session_id}'
        )

    def _run_claude(self, args: List[str]) -> subprocess.CompletedProcess:
        """Run claude command with timeout and error handling.

        Args:
            args: Arguments to pass to claude command

        Returns:
            CompletedProcess object with stdout, stderr, returncode

        Raises:
            AgentException: If command fails or times out
        """
        # Build full command
        command = [self.claude_command] + args

        # Prepare environment
        env = os.environ.copy()
        env.update(self.environment_vars)

        try:
            logger.debug(f'Running command: {" ".join(command)}')

            # Run subprocess
            result = subprocess.run(
                command,
                cwd=str(self.workspace_path),
                capture_output=True,
                text=True,
                timeout=self.response_timeout,
                env=env,
                check=False  # Don't raise on non-zero exit
            )

            return result

        except subprocess.TimeoutExpired as e:
            raise AgentException(
                f'Timeout after {self.response_timeout}s',
                context={
                    'timeout': self.response_timeout,
                    'command': command
                },
                recovery='Increase response_timeout in config'
            )

        except FileNotFoundError:
            raise AgentException(
                f'Claude command not found: {self.claude_command}',
                context={'command': self.claude_command},
                recovery='Install Claude Code CLI or specify correct path'
            )

        except Exception as e:
            raise AgentException(
                f'Failed to run claude: {e}',
                context={'command': command, 'error': str(e)}
            )

    def send_prompt(self, prompt: str, context: Optional[Dict] = None) -> str:
        """Send prompt to Claude Code and return response.

        Uses --print mode with --session-id for stateless operation with
        optional context persistence. Implements retry logic for session-in-use errors.

        Args:
            prompt: The prompt text to send
            context: Optional context dict (unused in headless mode)

        Returns:
            Complete response from Claude Code

        Raises:
            AgentException: If Claude fails or returns error
        """
        if self.workspace_path is None:
            raise AgentException(
                'Agent not initialized',
                recovery='Call initialize() before sending prompts'
            )

        # Generate session ID (fresh or persistent)
        if self.use_session_persistence and self.session_id:
            session_id = self.session_id  # Reuse session
        else:
            session_id = str(uuid.uuid4())  # Fresh session per call
            logger.debug(f'Using fresh session: {session_id}')

        # Build arguments for --print mode with session
        args = ['--print', '--session-id', session_id]

        # Add dangerous mode flag if enabled
        if self.bypass_permissions:
            args.append('--dangerously-skip-permissions')

        # Add prompt as final argument
        args.append(prompt)

        logger.info(
            f'Sending prompt ({len(prompt)} chars) with session {session_id[:8]}...'
        )
        logger.debug(f'Prompt: {prompt[:100]}...')

        # Retry logic for session-in-use errors
        retry_delay = self.retry_initial_delay

        for attempt in range(self.max_retries):
            # Execute command
            result = self._run_claude(args)

            # Check result
            if result.returncode == 0:
                # Success!
                response = result.stdout.strip()

                if attempt > 0:
                    logger.info(
                        f'Received response ({len(response)} chars) '
                        f'after {attempt + 1} attempts'
                    )
                else:
                    logger.info(f'Received response ({len(response)} chars)')

                logger.debug(f'Response: {response[:100]}...')
                return response

            # Check if it's a session-in-use error
            if 'already in use' in result.stderr.lower():
                if attempt < self.max_retries - 1:
                    logger.warning(
                        f'Session {self.session_id} in use, '
                        f'retrying in {retry_delay:.1f}s (attempt {attempt + 1}/{self.max_retries})'
                    )
                    time.sleep(retry_delay)
                    retry_delay *= self.retry_backoff  # Exponential backoff
                    continue
                else:
                    raise AgentException(
                        f'Session still in use after {self.max_retries} retries',
                        context={
                            'session_id': self.session_id,
                            'stderr': result.stderr,
                            'total_wait_time': sum(
                                self.retry_initial_delay * (self.retry_backoff ** i)
                                for i in range(self.max_retries - 1)
                            )
                        },
                        recovery='Wait longer between calls or use fresh sessions'
                    )

            # Other error - fail immediately
            raise AgentException(
                f'Claude failed with exit code {result.returncode}',
                context={
                    'exit_code': result.returncode,
                    'stderr': result.stderr,
                    'stdout': result.stdout[:500] if result.stdout else None
                },
                recovery='Check Claude Code logs and ensure API key is set'
            )

        # Should never reach here, but just in case
        raise AgentException('Unexpected error in send_prompt retry loop')

    def is_healthy(self) -> bool:
        """Check if Claude Code is available and responsive.

        Tests Claude availability by running a simple command.

        Returns:
            True if Claude is available, False otherwise
        """
        if not self.workspace_path:
            return False

        try:
            # Try to get version (quick test)
            result = subprocess.run(
                [self.claude_command, '--version'],
                capture_output=True,
                text=True,
                timeout=5,
                check=False
            )

            return result.returncode == 0

        except Exception as e:
            logger.debug(f'Health check failed: {e}')
            return False

    def get_status(self) -> Dict[str, Any]:
        """Get current agent status.

        Returns:
            Dict with status information including:
                - agent_type: 'claude-code-local'
                - mode: 'headless'
                - session_id: Current session UUID
                - workspace: Workspace path
                - command: Claude command
                - healthy: Health check result
        """
        return {
            'agent_type': 'claude-code-local',
            'mode': 'headless',
            'session_id': self.session_id,
            'workspace': str(self.workspace_path) if self.workspace_path else None,
            'command': self.claude_command,
            'healthy': self.is_healthy()
        }

    def get_workspace_files(self) -> List[Path]:
        """Get list of all files in agent's workspace.

        Returns:
            List of Path objects for all workspace files

        Raises:
            AgentException: If unable to list files
        """
        if not self.workspace_path or not self.workspace_path.exists():
            return []

        try:
            files = []
            for item in self.workspace_path.rglob('*'):
                if item.is_file():
                    # Skip common ignore patterns
                    parts = item.parts
                    if any(
                        p in parts
                        for p in ['.git', '__pycache__', 'node_modules', '.venv', 'venv']
                    ):
                        continue
                    files.append(item)
            return files

        except Exception as e:
            raise AgentException(
                f'Failed to list workspace files: {e}',
                context={'workspace': str(self.workspace_path)},
                recovery='Check workspace path and permissions'
            )

    def read_file(self, path: Path) -> str:
        """Read contents of file from workspace.

        Args:
            path: Path to file (relative to workspace root or absolute)

        Returns:
            File contents as string

        Raises:
            FileNotFoundError: If file doesn't exist
            AgentException: If unable to read file
        """
        # Make path absolute if relative
        if not path.is_absolute():
            if not self.workspace_path:
                raise AgentException(
                    'Agent not initialized',
                    recovery='Call initialize() before reading files'
                )
            path = self.workspace_path / path

        try:
            return path.read_text()
        except FileNotFoundError:
            raise
        except Exception as e:
            raise AgentException(
                f'Failed to read file: {e}',
                context={'path': str(path)},
                recovery='Check file path and permissions'
            )

    def write_file(self, path: Path, content: str) -> None:
        """Write content to file in workspace.

        Args:
            path: Path to file (relative to workspace root or absolute)
            content: Content to write

        Raises:
            AgentException: If unable to write file
        """
        # Make path absolute if relative
        if not path.is_absolute():
            if not self.workspace_path:
                raise AgentException(
                    'Agent not initialized',
                    recovery='Call initialize() before writing files'
                )
            path = self.workspace_path / path

        try:
            # Create parent directories
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        except Exception as e:
            raise AgentException(
                f'Failed to write file: {e}',
                context={'path': str(path)},
                recovery='Check file path and permissions'
            )

    def get_file_changes(self, since: Optional[float] = None) -> List[Dict]:
        """Get files modified since timestamp.

        Args:
            since: Unix timestamp, or None for all files

        Returns:
            List of dictionaries with keys:
                - 'path': Path object for file
                - 'change_type': 'modified' (simplified detection)
                - 'timestamp': Unix timestamp of modification
                - 'hash': SHA256 hash of file contents
                - 'size': File size in bytes
        """
        changes = []

        if not self.workspace_path or not self.workspace_path.exists():
            return changes

        try:
            for file_path in self.get_workspace_files():
                stat = file_path.stat()
                mtime = stat.st_mtime

                # Filter by timestamp if provided
                if since is not None and mtime < since:
                    continue

                # Calculate file hash
                try:
                    content = file_path.read_bytes()
                    file_hash = hashlib.sha256(content).hexdigest()
                except Exception:
                    file_hash = 'unknown'

                changes.append({
                    'path': file_path,
                    'change_type': 'modified',
                    'timestamp': mtime,
                    'hash': file_hash,
                    'size': stat.st_size
                })

            return changes

        except Exception as e:
            logger.error(f'Error getting file changes: {e}')
            return []

    def cleanup(self) -> None:
        """Clean up agent resources.

        Headless mode has no persistent process, so cleanup is a no-op.
        """
        logger.info('Cleanup complete - headless mode requires no process management')
