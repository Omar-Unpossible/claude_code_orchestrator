"""Local subprocess-based Claude Code agent implementation.

This module provides ClaudeCodeLocalAgent, which manages Claude Code CLI
as a local subprocess for same-machine deployment scenarios.
"""

import json
import logging
import os
import subprocess
import threading
import time
from enum import Enum
from pathlib import Path
from queue import Queue, Empty
from typing import Any, Dict, Optional

from src.plugins.base import AgentPlugin
from src.plugins.exceptions import AgentException
from src.plugins.registry import register_agent

logger = logging.getLogger(__name__)


class ProcessState(Enum):
    """States for the Claude Code subprocess lifecycle."""
    STOPPED = "stopped"
    STARTING = "starting"
    READY = "ready"
    BUSY = "busy"
    ERROR = "error"
    STOPPING = "stopping"


@register_agent('claude-code-local')
class ClaudeCodeLocalAgent(AgentPlugin):
    """Claude Code agent running as local subprocess.

    Spawns Claude Code CLI as a child process and communicates via
    stdin/stdout pipes. Designed for same-machine deployment where
    Obra and Claude Code run in the same environment (e.g., WSL2).

    Key Features:
    - Direct subprocess communication (no SSH overhead)
    - Non-blocking I/O with thread-based output reading
    - Process health monitoring and automatic recovery
    - Graceful shutdown with fallback termination

    Attributes:
        claude_command: Command to launch Claude Code CLI
        workspace_path: Path to workspace directory
        startup_timeout: Seconds to wait for process startup
        process: Subprocess.Popen instance
        state: Current process state
    """

    # Prompt indicator in Claude Code interactive mode
    PROMPT_INDICATOR = "⏵⏵"

    # Alternative prompt patterns
    PROMPT_PATTERNS = [
        "⏵⏵",
        "> ",
        "──────",  # Line separators that often appear before prompt
    ]

    # Error markers in Claude Code output
    ERROR_MARKERS = [
        "✗",
        "Error:",
        "Failed:",
        "Exception:",
    ]

    # Rate limit markers
    RATE_LIMIT_MARKERS = [
        "rate limit",
        "too many requests",
        "try again later",
    ]

    def __init__(self):
        """Initialize the local Claude Code agent."""
        self.claude_command: str = "claude"
        self.workspace_path: Optional[Path] = None
        self.startup_timeout: int = 30
        self.response_timeout: int = 300

        self.process: Optional[subprocess.Popen] = None
        self.state: ProcessState = ProcessState.STOPPED
        self._lock = threading.RLock()

        # Output reading threads and queues
        self._stdout_queue: Queue = Queue()
        self._stderr_queue: Queue = Queue()
        self._stdout_thread: Optional[threading.Thread] = None
        self._stderr_thread: Optional[threading.Thread] = None
        self._stop_reading = threading.Event()

        # Hook-based completion detection
        self._completion_signal_file: Optional[Path] = None
        self._completion_marker_count: int = 0

        logger.info("ClaudeCodeLocalAgent initialized")

    def initialize(self, config: Dict[str, Any]) -> None:
        """Start Claude Code CLI subprocess.

        Args:
            config: Configuration dict containing:
                - workspace_path: Path to workspace directory (required)
                - claude_command: Command to run (default: 'claude')
                - startup_timeout: Seconds to wait for startup (default: 30)
                - response_timeout: Seconds to wait for responses (default: 300)

        Raises:
            AgentException: If subprocess fails to start
        """
        with self._lock:
            if self.state != ProcessState.STOPPED:
                logger.warning(f"Cannot initialize: agent already in state {self.state}")
                return

            # Extract configuration
            self.workspace_path = Path(config.get('workspace_path', '/tmp/claude-workspace'))
            self.claude_command = config.get('claude_command', 'claude')
            self.startup_timeout = config.get('startup_timeout', 30)
            self.response_timeout = config.get('response_timeout', 300)

            # Ensure workspace exists
            self.workspace_path.mkdir(parents=True, exist_ok=True)

            # Set up hook configuration BEFORE starting Claude Code
            # (Claude reads settings at startup)
            self._prepare_completion_hook()

            logger.info(f"Starting Claude Code CLI: {self.claude_command}")
            logger.info(f"Workspace: {self.workspace_path}")

            try:
                self.state = ProcessState.STARTING

                # Start subprocess with pipes
                self.process = subprocess.Popen(
                    [self.claude_command],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,  # Line buffered
                    cwd=str(self.workspace_path),
                )

                # Start output reading threads
                self._stop_reading.clear()
                self._stdout_thread = threading.Thread(
                    target=self._read_output,
                    args=(self.process.stdout, self._stdout_queue),
                    daemon=True,
                    name="claude-stdout-reader"
                )
                self._stderr_thread = threading.Thread(
                    target=self._read_output,
                    args=(self.process.stderr, self._stderr_queue),
                    daemon=True,
                    name="claude-stderr-reader"
                )

                self._stdout_thread.start()
                self._stderr_thread.start()

                # Wait for startup (look for ready indicators)
                if self._wait_for_ready():
                    self.state = ProcessState.READY
                    logger.info("Claude Code CLI started successfully")
                else:
                    self.state = ProcessState.ERROR
                    raise AgentException(
                        "Claude Code CLI failed to become ready",
                        context={
                            'command': self.claude_command,
                            'timeout': self.startup_timeout,
                        },
                        recovery="Check that Claude Code CLI is installed and ANTHROPIC_API_KEY is set"
                    )

            except FileNotFoundError:
                self.state = ProcessState.ERROR
                raise AgentException(
                    f"Claude Code CLI not found: {self.claude_command}",
                    context={'command': self.claude_command},
                    recovery="Install Claude Code CLI or specify correct path in config"
                )
            except Exception as e:
                self.state = ProcessState.ERROR
                raise AgentException(
                    f"Failed to start Claude Code CLI: {e}",
                    context={'command': self.claude_command, 'error': str(e)},
                    recovery="Check logs and ensure Claude Code CLI is properly configured"
                )

    def _read_output(self, stream, queue: Queue) -> None:
        """Read lines from output stream and put in queue.

        Runs in separate thread to avoid blocking on I/O.

        Args:
            stream: stdout or stderr stream from subprocess
            queue: Queue to put lines into
        """
        try:
            for line in iter(stream.readline, ''):
                if self._stop_reading.is_set():
                    break
                queue.put(line.rstrip('\n'))
        except Exception as e:
            logger.error(f"Error reading output stream: {e}")
        finally:
            logger.debug("Output reading thread exiting")

    def _wait_for_ready(self) -> bool:
        """Wait for Claude Code to become ready after startup.

        Claude Code in interactive mode doesn't output a traditional "ready" signal.
        Instead, we verify the process started successfully and is stable.

        Returns:
            True if ready, False if timeout or crash
        """
        logger.info("Waiting for Claude Code process stability...")

        # Wait for process to stabilize (2 seconds)
        stability_wait = 2.0
        check_interval = 0.2
        checks = int(stability_wait / check_interval)

        for i in range(checks):
            # Check if process died
            if self.process.poll() is not None:
                exit_code = self.process.poll()
                logger.error(f"Claude Code process exited during startup with code {exit_code}")

                # Capture any error output
                try:
                    stderr_output = []
                    while not self._stderr_queue.empty():
                        stderr_output.append(self._stderr_queue.get_nowait())
                    if stderr_output:
                        logger.error(f"Error output: {' '.join(stderr_output)}")
                except Empty:
                    pass

                return False

            time.sleep(check_interval)

            # Log progress every second
            if (i + 1) % 5 == 0:
                logger.debug(f"Process stability check {(i+1)//5}/{checks//5}")

        # Process is alive and stable
        logger.info("Claude Code process started and stable - ready for input")
        return True

    def _prepare_completion_hook(self) -> None:
        """Prepare Claude Code Stop hook configuration BEFORE process starts.

        Creates a completion signal file and writes hook configuration to
        workspace settings.json. Claude Code will load this at startup and
        write to the signal file when finishing each response.

        Must be called before starting Claude Code process.
        """
        # Create unique completion signal file
        pid = os.getpid()
        self._completion_signal_file = Path(f"/tmp/obra_claude_completion_{pid}")
        self._completion_signal_file.write_text("")  # Initialize empty
        self._completion_marker_count = 0

        logger.info(f"Created completion signal file: {self._completion_signal_file}")

        # Create .claude directory in workspace
        claude_dir = self.workspace_path / ".claude"
        claude_dir.mkdir(exist_ok=True)

        # Configure Stop hook in settings.json
        settings_file = claude_dir / "settings.json"

        hook_config = {
            "hooks": {
                "Stop": [{
                    "matcher": "*",
                    "hooks": [{
                        "type": "command",
                        "command": f"echo 'COMPLETE' >> {self._completion_signal_file}"
                    }]
                }]
            }
        }

        settings_file.write_text(json.dumps(hook_config, indent=2))
        logger.info(f"Configured Stop hook in {settings_file}")

    def send_prompt(self, prompt: str, context: Optional[Dict] = None) -> str:
        """Send prompt to Claude Code stdin and read response.

        Args:
            prompt: The prompt text to send
            context: Optional context dict (not used by subprocess agent)

        Returns:
            Complete response from Claude Code

        Raises:
            AgentException: If agent is not ready or communication fails
        """
        with self._lock:
            if self.state != ProcessState.READY:
                raise AgentException(
                    f"Cannot send prompt: agent in state {self.state}",
                    context={'state': self.state.value},
                    recovery="Ensure agent is initialized and healthy"
                )

            if not self.process or self.process.poll() is not None:
                raise AgentException(
                    "Claude Code process is not running",
                    recovery="Reinitialize agent to restart process"
                )

            try:
                self.state = ProcessState.BUSY

                logger.info(f"Sending prompt to Claude Code ({len(prompt)} chars)")
                logger.debug(f"Prompt: {prompt[:100]}...")

                # Write prompt to stdin
                self.process.stdin.write(prompt + "\n")
                self.process.stdin.flush()

                # Read response until completion
                response = self._read_response()

                self.state = ProcessState.READY
                logger.info(f"Received response ({len(response)} chars)")

                return response

            except Exception as e:
                self.state = ProcessState.ERROR
                raise AgentException(
                    f"Failed to send prompt: {e}",
                    context={'error': str(e)},
                    recovery="Check process health and reinitialize if needed"
                )

    def _read_response(self) -> str:
        """Read response from stdout until Stop hook signals completion.

        Uses Claude Code's Stop hook which writes to a completion signal file
        when Claude finishes responding. This provides definitive completion
        detection without arbitrary timeouts.

        Returns:
            Complete response text

        Raises:
            AgentException: If process dies or rate limit detected
        """
        response_lines = []
        start_time = time.time()

        # Track starting marker count
        starting_marker_count = self._completion_marker_count

        logger.debug(f"Waiting for Stop hook signal (starting markers: {starting_marker_count})")

        # Read output until hook signals completion
        while time.time() - start_time < self.response_timeout:
            # Check for new completion marker from hook
            if self._completion_signal_file and self._completion_signal_file.exists():
                content = self._completion_signal_file.read_text()
                current_markers = content.count("COMPLETE")

                if current_markers > starting_marker_count:
                    # New completion marker detected!
                    self._completion_marker_count = current_markers
                    logger.info(f"Stop hook signaled completion (markers: {current_markers})")
                    break

            # Read any available output (non-blocking)
            try:
                line = self._stdout_queue.get(timeout=0.1)
                response_lines.append(line)
                logger.debug(f"Response line: {line}")

                # Check for error markers
                if any(marker in line for marker in self.ERROR_MARKERS):
                    logger.warning(f"Error marker detected: {line}")
                    # Continue reading to get full error message

                # Check for rate limit
                if any(marker in line.lower() for marker in self.RATE_LIMIT_MARKERS):
                    raise AgentException(
                        "Rate limit detected",
                        context={'last_line': line},
                        recovery="Wait before retrying"
                    )

            except Empty:
                # No output right now, check process health
                if self.process.poll() is not None:
                    raise AgentException(
                        "Claude Code process terminated during response",
                        context={'exit_code': self.process.returncode},
                        recovery="Check logs and reinitialize agent"
                    )
                continue

        # Check for timeout
        if time.time() - start_time >= self.response_timeout:
            raise AgentException(
                f"Timeout waiting for Stop hook signal ({self.response_timeout}s)",
                context={
                    'partial_response': '\n'.join(response_lines),
                    'markers_detected': self._completion_marker_count - starting_marker_count
                },
                recovery="Increase response_timeout or check if Stop hook is configured correctly"
            )

        # Drain any remaining output in queue
        try:
            while True:
                line = self._stdout_queue.get_nowait()
                response_lines.append(line)
        except Empty:
            pass

        return '\n'.join(response_lines)

    def is_healthy(self) -> bool:
        """Check if Claude Code process is running and responsive.

        Returns:
            True if healthy, False otherwise
        """
        with self._lock:
            # Check state
            if self.state in [ProcessState.STOPPED, ProcessState.ERROR]:
                return False

            # Check process is alive
            if not self.process or self.process.poll() is not None:
                logger.warning("Claude Code process is not running")
                self.state = ProcessState.ERROR
                return False

            # Check threads are alive
            if self._stdout_thread and not self._stdout_thread.is_alive():
                logger.warning("stdout reader thread died")
                return False

            if self._stderr_thread and not self._stderr_thread.is_alive():
                logger.warning("stderr reader thread died")
                return False

            return True

    def get_status(self) -> Dict[str, Any]:
        """Get current agent status.

        Returns:
            Dict with status information
        """
        with self._lock:
            return {
                'agent_type': 'claude-code-local',
                'state': self.state.value,
                'healthy': self.is_healthy(),
                'pid': self.process.pid if self.process else None,
                'workspace': str(self.workspace_path) if self.workspace_path else None,
                'command': self.claude_command,
            }

    def get_workspace_files(self) -> list:
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
                    if any(p in parts for p in ['.git', '__pycache__', 'node_modules', '.venv', 'venv']):
                        continue
                    files.append(item)
            return files
        except Exception as e:
            raise AgentException(
                f"Failed to list workspace files: {e}",
                context={'workspace': str(self.workspace_path)},
                recovery="Check workspace path and permissions"
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
            path = self.workspace_path / path

        try:
            return path.read_text()
        except FileNotFoundError:
            raise
        except Exception as e:
            raise AgentException(
                f"Failed to read file: {e}",
                context={'path': str(path)},
                recovery="Check file path and permissions"
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
            path = self.workspace_path / path

        try:
            # Create parent directories
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        except Exception as e:
            raise AgentException(
                f"Failed to write file: {e}",
                context={'path': str(path)},
                recovery="Check file path and permissions"
            )

    def get_file_changes(self, since: Optional[float] = None) -> list:
        """Get files modified since timestamp.

        Args:
            since: Unix timestamp, or None for all changes since last check

        Returns:
            List of dictionaries with keys:
                - 'path': Path object for changed file
                - 'change_type': 'created', 'modified', or 'deleted'
                - 'timestamp': Unix timestamp of change
                - 'hash': File content hash (for change detection)
                - 'size': File size in bytes
        """
        # For local agent, we track file changes by modification time
        import hashlib

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
                    'change_type': 'modified',  # Simplified - assumes modified
                    'timestamp': mtime,
                    'hash': file_hash,
                    'size': stat.st_size
                })

            return changes
        except Exception as e:
            logger.error(f"Error getting file changes: {e}")
            return []

    def cleanup(self) -> None:
        """Gracefully shutdown Claude Code process.

        Attempts graceful shutdown (SIGINT), then SIGTERM, then SIGKILL.
        """
        with self._lock:
            if self.state == ProcessState.STOPPED:
                return

            logger.info("Cleaning up Claude Code agent")
            self.state = ProcessState.STOPPING

            # Stop reading threads
            self._stop_reading.set()

            if self.process:
                try:
                    # Try graceful shutdown first (Ctrl+C)
                    logger.info("Sending SIGINT to Claude Code process")
                    self.process.send_signal(subprocess.signal.SIGINT)

                    # Wait up to 5s for graceful exit
                    try:
                        self.process.wait(timeout=5)
                        logger.info("Claude Code exited gracefully")
                    except subprocess.TimeoutExpired:
                        # Force terminate
                        logger.warning("Graceful shutdown timeout, terminating")
                        self.process.terminate()

                        try:
                            self.process.wait(timeout=3)
                        except subprocess.TimeoutExpired:
                            # Last resort: kill
                            logger.error("Terminate timeout, killing process")
                            self.process.kill()
                            self.process.wait()

                except Exception as e:
                    logger.error(f"Error during cleanup: {e}")
                finally:
                    self.process = None

            # Wait for threads to finish
            if self._stdout_thread:
                self._stdout_thread.join(timeout=2.0)
            if self._stderr_thread:
                self._stderr_thread.join(timeout=2.0)

            # Clean up completion signal file
            if self._completion_signal_file and self._completion_signal_file.exists():
                try:
                    self._completion_signal_file.unlink()
                    logger.debug(f"Removed completion signal file: {self._completion_signal_file}")
                except Exception as e:
                    logger.warning(f"Failed to remove signal file: {e}")

            self.state = ProcessState.STOPPED
            logger.info("Claude Code agent cleanup complete")
