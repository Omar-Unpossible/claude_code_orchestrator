"""Local subprocess-based Claude Code agent implementation (headless mode).

This module provides ClaudeCodeLocalAgent, which manages Claude Code CLI
using headless --print mode for reliable, stateless operation.
"""

import hashlib
import json
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
        # 2-hour timeout (7200s) allows complex workflows to complete without interruption
        # For shorter tasks, override via config.yaml: agent.local.response_timeout
        self.response_timeout: int = 7200
        self.environment_vars: Dict[str, str] = {}

        # Session management
        self.use_session_persistence: bool = False  # Disabled by default (locks cause issues)

        # Retry configuration for session-in-use errors
        self.max_retries: int = 5  # More retries
        self.retry_initial_delay: float = 2.0  # Start with 2s
        self.retry_backoff: float = 1.5  # Exponential backoff multiplier

        # Dangerous mode (bypass permissions for automated orchestration)
        self.bypass_permissions: bool = True  # Enabled by default for Obra

        # JSON metadata from last response (Phase 1, Task 1.3)
        self.last_metadata: Optional[Dict[str, Any]] = None

        logger.info('ClaudeCodeLocalAgent initialized (headless mode)')

    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize agent with configuration.

        Args:
            config: Configuration dict containing:
                - workspace_path or workspace_dir: Path to workspace directory (required)
                - claude_command or command: Command to run (default: 'claude')
                - response_timeout or timeout_response: Seconds to wait (default: 7200 = 2 hours)
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
        # Default is 7200s (2 hours) to support complex workflows
        self.response_timeout = (
            config.get('response_timeout') or
            config.get('timeout_response', 7200)
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

        # Generate session ID (prefer explicitly set, otherwise fresh)
        # BUG-PHASE4-005 FIX: Always use session_id if explicitly set (by orchestrator)
        if self.session_id:
            # Explicitly set session_id (e.g., by orchestrator for tracking)
            session_id = self.session_id
            logger.debug(f'SESSION ASSIGNED: session_id={session_id[:8]}... (externally set)')
        else:
            # Generate fresh session ID
            session_id = str(uuid.uuid4())
            if self.use_session_persistence:
                # Save for next call if persistence enabled
                self.session_id = session_id
                logger.debug(f'SESSION FRESH_PERSIST: session_id={session_id[:8]}...')
            else:
                logger.debug(f'SESSION FRESH: session_id={session_id[:8]}...')

        # Build arguments for --print mode with session and JSON output
        args = [
            '--print',
            '--session-id', session_id,
            '--output-format', 'json'  # Phase 1, Task 1.3: Enable JSON responses
        ]

        # Add max_turns if provided in context (Phase 4, Task 4.2)
        max_turns = None
        if context and 'max_turns' in context:
            max_turns = context['max_turns']
            args.extend(['--max-turns', str(max_turns)])
            logger.info(f'CLAUDE_ARGS: max_turns={max_turns} (from context)')

        # Add dangerous mode flag if enabled
        if self.bypass_permissions:
            args.append('--dangerously-skip-permissions')

        # Add prompt as final argument
        args.append(prompt)

        logger.info(
            f'CLAUDE_SEND: prompt_chars={len(prompt):,}, '
            f'session={session_id[:8]}..., max_turns={max_turns or "default"}'
        )
        logger.debug(f'CLAUDE_PROMPT: {prompt[:100]}...')

        # Retry logic for session-in-use errors
        retry_delay = self.retry_initial_delay

        for attempt in range(self.max_retries):
            # Execute command
            result = self._run_claude(args)

            # Check result
            if result.returncode == 0:
                # Success! Parse JSON response (Phase 1, Task 1.3)
                raw_response = result.stdout.strip()

                try:
                    # Parse JSON response
                    json_response = json.loads(raw_response)

                    # Extract the actual result text
                    result_text = json_response.get('result', '')

                    # Extract and store metadata
                    self.last_metadata = self._extract_metadata(json_response)

                    # Phase 4, Task 4.2: Check for error_max_turns
                    if self.last_metadata.get('subtype') == 'error_max_turns':
                        num_turns = self.last_metadata.get('num_turns', 0)
                        max_turns_limit = context.get('max_turns') if context else None

                        logger.error(
                            f'CLAUDE_ERROR_MAX_TURNS: session_id={session_id[:8]}..., '
                            f'turns_used={num_turns}, max_turns_limit={max_turns_limit}'
                        )

                        raise AgentException(
                            f'Task exceeded max_turns limit ({num_turns}/{max_turns_limit})',
                            context={
                                'subtype': 'error_max_turns',
                                'num_turns': num_turns,
                                'max_turns': max_turns_limit,
                                'session_id': session_id,
                                'result_text': result_text[:500]  # Truncated error message
                            },
                            recovery='Retry with increased max_turns or break task into smaller pieces'
                        )

                    # Log detailed metadata
                    total_tokens = self.last_metadata.get("total_tokens", 0)
                    num_turns = self.last_metadata.get("num_turns", 0)
                    duration_ms = self.last_metadata.get("duration_ms", 0)
                    cache_hit_rate = self.last_metadata.get("cache_hit_rate", 0.0)
                    input_tokens = self.last_metadata.get("input_tokens", 0)
                    cache_read_tokens = self.last_metadata.get("cache_read_tokens", 0)
                    output_tokens = self.last_metadata.get("output_tokens", 0)

                    logger.info(
                        f'CLAUDE_RESPONSE: session_id={session_id[:8]}..., '
                        f'result_chars={len(result_text):,}, '
                        f'attempt={attempt + 1}/{self.max_retries}'
                    )

                    logger.info(
                        f'CLAUDE_JSON_METADATA: '
                        f'tokens={total_tokens:,} '
                        f'(input={input_tokens:,}, cache_read={cache_read_tokens:,}, output={output_tokens:,}), '
                        f'turns={num_turns}, duration={duration_ms}ms, '
                        f'cache_efficiency={cache_hit_rate:.1%}'
                    )

                    logger.debug(f'CLAUDE_RESPONSE_TEXT: {result_text[:100]}...')
                    logger.debug(f'CLAUDE_FULL_METADATA: {self.last_metadata}')

                    return result_text

                except json.JSONDecodeError as e:
                    # JSON parsing failed - log warning but don't fail
                    # (fallback to plain text for backward compatibility)
                    logger.warning(f'CLAUDE_JSON_PARSE_FAILED: {e}')
                    logger.warning(f'CLAUDE_RAW_RESPONSE: {raw_response[:200]}...')
                    self.last_metadata = None
                    return raw_response

            # Check if it's a session-in-use error
            if 'already in use' in result.stderr.lower():
                if attempt < self.max_retries - 1:
                    logger.warning(
                        f'CLAUDE_SESSION_IN_USE: session_id={session_id[:8]}..., '
                        f'attempt={attempt + 1}/{self.max_retries}, '
                        f'retry_delay={retry_delay:.1f}s'
                    )
                    time.sleep(retry_delay)
                    retry_delay *= self.retry_backoff  # Exponential backoff
                    continue
                else:
                    total_wait_time = sum(
                        self.retry_initial_delay * (self.retry_backoff ** i)
                        for i in range(self.max_retries - 1)
                    )
                    logger.error(
                        f'CLAUDE_SESSION_LOCKED: session_id={session_id[:8]}..., '
                        f'max_retries={self.max_retries} exhausted, '
                        f'total_wait_time={total_wait_time:.1f}s'
                    )
                    raise AgentException(
                        f'Session still in use after {self.max_retries} retries',
                        context={
                            'session_id': self.session_id,
                            'stderr': result.stderr,
                            'total_wait_time': total_wait_time
                        },
                        recovery='Wait longer between calls or use fresh sessions'
                    )

            # Other error - fail immediately
            logger.error(
                f'CLAUDE_COMMAND_FAILED: exit_code={result.returncode}, '
                f'session_id={session_id[:8]}..., stderr={result.stderr[:200]}'
            )
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

    def _extract_metadata(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata from Claude Code JSON response.

        Args:
            response: JSON response from Claude Code

        Returns:
            Dict with normalized metadata fields

        Note:
            This is based on the JSON schema documented in:
            docs/research/claude-code-json-response-schema.md
        """
        usage = response.get('usage', {})
        model_usage = response.get('modelUsage', {})

        # Calculate total tokens (input + cache_creation + cache_read + output)
        total_tokens = (
            usage.get('input_tokens', 0) +
            usage.get('cache_creation_input_tokens', 0) +
            usage.get('cache_read_input_tokens', 0) +
            usage.get('output_tokens', 0)
        )

        # Calculate cache hit rate (for efficiency tracking)
        cache_denominator = (
            usage.get('input_tokens', 0) +
            usage.get('cache_creation_input_tokens', 0) +
            usage.get('cache_read_input_tokens', 0)
        )
        cache_hit_rate = (
            usage.get('cache_read_input_tokens', 0) / cache_denominator
            if cache_denominator > 0 else 0.0
        )

        return {
            # Response status
            'type': response.get('type'),  # "result"
            'subtype': response.get('subtype'),  # "success", "error_max_turns", etc.
            'is_error': response.get('is_error', False),

            # Session info
            'session_id': response.get('session_id'),
            'uuid': response.get('uuid'),

            # Token usage
            'input_tokens': usage.get('input_tokens', 0),
            'cache_creation_tokens': usage.get('cache_creation_input_tokens', 0),
            'cache_read_tokens': usage.get('cache_read_input_tokens', 0),
            'output_tokens': usage.get('output_tokens', 0),
            'total_tokens': total_tokens,
            'cache_hit_rate': cache_hit_rate,

            # Performance metrics
            'duration_ms': response.get('duration_ms', 0),
            'duration_api_ms': response.get('duration_api_ms', 0),
            'num_turns': response.get('num_turns', 0),

            # Cost tracking
            'cost_usd': response.get('total_cost_usd', 0.0),

            # Error handling
            'error_subtype': response.get('subtype') if response.get('subtype') != 'success' else None,
            'permission_denials': response.get('permission_denials', []),
            'errors': response.get('errors', []),

            # Model usage (per-model breakdown)
            'model_usage': model_usage,
        }

    def get_last_metadata(self) -> Optional[Dict[str, Any]]:
        """Get metadata from the last send_prompt() call.

        Returns:
            Dict with metadata fields, or None if no metadata available

        Example:
            >>> response = agent.send_prompt("Task...")
            >>> metadata = agent.get_last_metadata()
            >>> print(f"Used {metadata['total_tokens']} tokens")
            >>> print(f"Cache hit rate: {metadata['cache_hit_rate']:.1%}")
        """
        return self.last_metadata

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
