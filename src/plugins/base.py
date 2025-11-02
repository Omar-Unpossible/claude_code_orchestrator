"""Abstract base classes for the plugin system.

This module defines the core plugin interfaces that enable extensibility:
- AgentPlugin: Interface for coding agents (Claude Code, Aider, etc.)
- LLMPlugin: Interface for local LLM providers (Ollama, llama.cpp, etc.)

All plugins must implement these interfaces to work with the orchestration system.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Dict, Any, Iterator


class AgentPlugin(ABC):
    """Abstract base class for all coding agents.

    This interface enables multiple agent implementations (Claude Code via SSH/Docker,
    Aider, custom agents) without changing core orchestration logic.

    Implementing a new agent:
        1. Subclass AgentPlugin
        2. Implement all @abstractmethod methods
        3. Register using @register_agent decorator
        4. Configure in config.yaml

    Example:
        >>> from src.plugins.registry import register_agent
        >>> @register_agent('my-agent')
        ... class MyAgent(AgentPlugin):
        ...     def initialize(self, config: dict) -> None:
        ...         self.config = config
        ...
        ...     def send_prompt(self, prompt: str, context=None) -> str:
        ...         return "Response from my agent"
        ...
        ...     # ... implement other methods

    Thread-safety:
        Implementations should be thread-safe or document if they're not.
        The orchestrator may call methods from different threads.
    """

    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize agent with configuration.

        Called once when agent is instantiated. Should establish connections,
        validate configuration, and prepare agent for use.

        Args:
            config: Configuration dictionary with agent-specific settings.
                Common keys:
                - 'workspace_path': Path to agent's working directory
                - 'timeout': Default timeout for operations (seconds)
                - Agent-specific keys (ssh_host, docker_image, etc.)

        Raises:
            AgentConfigException: If configuration is invalid
            AgentConnectionException: If unable to connect to agent

        Example:
            >>> agent = ClaudeCodeSSHAgent()
            >>> agent.initialize({
            ...     'ssh_host': '192.168.1.100',
            ...     'ssh_user': 'claude',
            ...     'ssh_key_path': '~/.ssh/vm_key',
            ...     'workspace_path': '/home/claude/workspace'
            ... })
        """
        pass

    @abstractmethod
    def send_prompt(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Send prompt to agent and return response.

        This is the primary interaction method. Sends a prompt to the agent,
        waits for completion, and returns the full response.

        Args:
            prompt: Text prompt to send to agent
            context: Optional context dictionary with:
                - 'task_id': Current task identifier
                - 'timeout': Override default timeout
                - 'files': List of files to focus on
                - 'constraints': List of constraints/requirements

        Returns:
            Agent's complete response as string

        Raises:
            AgentException: If agent encounters an error
            AgentTimeoutException: If operation times out
            AgentProcessException: If agent process crashes

        Example:
            >>> response = agent.send_prompt(
            ...     "Fix the bug in main.py line 42",
            ...     context={'task_id': 'task-123', 'timeout': 60}
            ... )
            >>> print(response)
            'I fixed the bug by changing...'
        """
        pass

    @abstractmethod
    def get_workspace_files(self) -> List[Path]:
        """Get list of all files in agent's workspace.

        Returns absolute paths to all files, excluding common ignore patterns
        (.git, __pycache__, node_modules, etc.).

        Returns:
            List of Path objects for all workspace files

        Raises:
            AgentException: If unable to list files

        Example:
            >>> files = agent.get_workspace_files()
            >>> print(files)
            [Path('/workspace/main.py'), Path('/workspace/test.py')]
        """
        pass

    @abstractmethod
    def read_file(self, path: Path) -> str:
        """Read contents of file from workspace.

        Args:
            path: Path to file (relative to workspace root or absolute)

        Returns:
            File contents as string

        Raises:
            FileNotFoundError: If file doesn't exist
            AgentException: If unable to read file

        Example:
            >>> content = agent.read_file(Path('main.py'))
            >>> print(content)
            'def main():\\n    ...'
        """
        pass

    @abstractmethod
    def write_file(self, path: Path, content: str) -> None:
        """Write content to file in workspace.

        Creates parent directories if they don't exist.

        Args:
            path: Path to file (relative to workspace root or absolute)
            content: Content to write

        Raises:
            AgentException: If unable to write file

        Example:
            >>> agent.write_file(Path('config.yaml'), 'key: value\\n')
        """
        pass

    @abstractmethod
    def get_file_changes(
        self,
        since: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """Get files modified since timestamp.

        Tracks what files the agent has created/modified, enabling validation
        and rollback functionality.

        Args:
            since: Unix timestamp, or None for all changes since last check

        Returns:
            List of dictionaries with keys:
                - 'path': Path object for changed file
                - 'change_type': 'created', 'modified', or 'deleted'
                - 'timestamp': Unix timestamp of change
                - 'hash': File content hash (for change detection)
                - 'size': File size in bytes

        Example:
            >>> import time
            >>> start = time.time()
            >>> agent.send_prompt("Create main.py")
            >>> changes = agent.get_file_changes(since=start)
            >>> print(changes)
            [{'path': Path('main.py'), 'change_type': 'created', ...}]
        """
        pass

    @abstractmethod
    def is_healthy(self) -> bool:
        """Check if agent is responsive and ready.

        Should perform a quick health check (e.g., ping, simple command).
        Used by orchestrator to detect if agent has crashed or disconnected.

        Returns:
            True if agent is healthy and responsive, False otherwise

        Example:
            >>> if not agent.is_healthy():
            ...     print("Agent is down, attempting reconnection...")
            ...     agent.initialize(config)
        """
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Release resources and clean up.

        Called when agent is no longer needed. Should:
        - Close network connections (SSH, Docker API)
        - Kill agent processes
        - Clean up temporary files
        - Release locks

        This method should not raise exceptions - catch and log them internally.

        Example:
            >>> try:
            ...     agent.cleanup()
            ... finally:
            ...     # Resources are released even if error occurs
            ...     pass
        """
        pass

    def get_capabilities(self) -> Dict[str, Any]:
        """Get agent capabilities (optional).

        Returns information about what this agent can do. Override in
        subclasses to provide agent-specific capabilities.

        Returns:
            Dictionary with capability information:
                - 'supports_streaming': bool
                - 'supports_interactive': bool
                - 'max_file_size': int (bytes)
                - 'supported_languages': list

        Example:
            >>> caps = agent.get_capabilities()
            >>> if caps.get('supports_streaming'):
            ...     # Use streaming mode
            ...     pass
        """
        return {
            'supports_streaming': False,
            'supports_interactive': False,
            'max_file_size': 10 * 1024 * 1024,  # 10 MB default
            'supported_languages': ['python']
        }


class LLMPlugin(ABC):
    """Abstract base class for local LLM providers.

    This interface enables multiple LLM backends (Ollama, llama.cpp, vLLM)
    without changing core orchestration logic.

    The local LLM is used for:
    - Validating agent responses
    - Generating optimized prompts
    - Scoring confidence
    - Quality control

    Implementing a new LLM provider:
        1. Subclass LLMPlugin
        2. Implement all @abstractmethod methods
        3. Register using @register_llm decorator
        4. Configure in config.yaml

    Example:
        >>> from src.plugins.registry import register_llm
        >>> @register_llm('my-llm')
        ... class MyLLMProvider(LLMPlugin):
        ...     def initialize(self, config: dict) -> None:
        ...         self.api_url = config['api_url']
        ...
        ...     def generate(self, prompt: str, **kwargs) -> str:
        ...         # Call LLM API
        ...         return "Generated text"

    Thread-safety:
        Implementations should be thread-safe or document if they're not.
    """

    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize LLM provider with configuration.

        Args:
            config: Configuration dictionary with:
                - 'model': Model name to use
                - 'api_url': API endpoint URL
                - 'timeout': Default timeout (seconds)
                - 'temperature': Default temperature
                - Provider-specific settings

        Raises:
            LLMConnectionException: If unable to connect
            LLMConfigException: If configuration invalid
            LLMModelNotFoundException: If model not available

        Example:
            >>> llm = OllamaProvider()
            >>> llm.initialize({
            ...     'model': 'qwen2.5-coder:32b',
            ...     'api_url': 'http://localhost:11434',
            ...     'temperature': 0.7
            ... })
        """
        pass

    @abstractmethod
    def generate(
        self,
        prompt: str,
        **kwargs
    ) -> str:
        """Generate text completion.

        Args:
            prompt: Input prompt
            **kwargs: Generation parameters:
                - temperature: float (0.0-2.0)
                - max_tokens: int
                - top_p: float
                - stop: list of stop sequences
                - system: system prompt

        Returns:
            Generated text as string

        Raises:
            LLMException: If generation fails
            LLMTimeoutException: If generation times out
            LLMResponseException: If response invalid

        Example:
            >>> response = llm.generate(
            ...     "Explain this code:",
            ...     temperature=0.3,
            ...     max_tokens=500
            ... )
        """
        pass

    @abstractmethod
    def generate_stream(
        self,
        prompt: str,
        **kwargs
    ) -> Iterator[str]:
        """Generate with streaming output.

        Yields text chunks as they're generated, enabling real-time display
        and early stopping.

        Args:
            prompt: Input prompt
            **kwargs: Same as generate()

        Yields:
            Text chunks as they're generated

        Raises:
            LLMException: If generation fails

        Example:
            >>> for chunk in llm.generate_stream("Write a story"):
            ...     print(chunk, end='', flush=True)
        """
        pass

    @abstractmethod
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text.

        Used for context management and prompt optimization. Should be
        reasonably accurate (within 5-10%).

        Args:
            text: Text to count tokens for

        Returns:
            Approximate token count

        Example:
            >>> count = llm.estimate_tokens("Hello world")
            >>> print(count)
            2
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if LLM is accessible and ready.

        Quick health check - should complete in <1 second.

        Returns:
            True if LLM is available, False otherwise

        Example:
            >>> if llm.is_available():
            ...     response = llm.generate(prompt)
            ... else:
            ...     print("LLM service is down")
        """
        pass

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about loaded model (optional).

        Returns:
            Dictionary with model information:
                - 'model_name': str
                - 'context_length': int
                - 'quantization': str
                - 'size_gb': float

        Example:
            >>> info = llm.get_model_info()
            >>> print(f"Context length: {info['context_length']}")
        """
        return {
            'model_name': 'unknown',
            'context_length': 4096,
            'quantization': 'unknown',
            'size_gb': 0.0
        }
