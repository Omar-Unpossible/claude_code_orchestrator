"""Exception hierarchy for the plugin system.

This module defines all exceptions that can be raised by plugins (agents and LLMs).
All exceptions include context preservation and recovery suggestions.
"""

from typing import Optional, Dict, Any


class PluginException(Exception):
    """Base exception for all plugin-related errors.

    All plugin exceptions preserve context and provide recovery suggestions.

    Attributes:
        message: Human-readable error message
        context_data: Dictionary with error context (host, port, etc.)
        recovery_suggestion: Actionable advice for recovery

    Example:
        >>> raise PluginException(
        ...     "Plugin failed to initialize",
        ...     context={'plugin_name': 'test-agent'},
        ...     recovery="Check configuration file"
        ... )
    """

    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        recovery: Optional[str] = None
    ):
        """Initialize plugin exception.

        Args:
            message: Error message
            context: Optional context dictionary
            recovery: Optional recovery suggestion
        """
        super().__init__(message)
        self.context_data = context or {}
        self.recovery_suggestion = recovery

    def __repr__(self) -> str:
        """Return detailed representation."""
        return (
            f"{self.__class__.__name__}("
            f"message={str(self)!r}, "
            f"context={self.context_data!r}, "
            f"recovery={self.recovery_suggestion!r})"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize exception to dictionary for logging/JSON.

        Returns:
            Dictionary with type, message, context, and recovery

        Example:
            >>> exc = PluginException("Error", context={'key': 'value'})
            >>> exc.to_dict()
            {'type': 'PluginException', 'message': 'Error', ...}
        """
        return {
            'type': self.__class__.__name__,
            'message': str(self),
            'context': self.context_data,
            'recovery': self.recovery_suggestion
        }


# Agent Plugin Exceptions

class AgentException(PluginException):
    """Base exception for agent plugin errors.

    Raised when an agent (Claude Code, Aider, etc.) encounters an error.
    """
    pass


class AgentConnectionException(AgentException):
    """Raised when unable to connect to agent.

    Common causes:
    - SSH connection failed (VM not accessible)
    - Docker container not running
    - Network issues
    - Firewall blocking connection

    Example:
        >>> raise AgentConnectionException(
        ...     agent_type='claude-code-ssh',
        ...     host='192.168.1.100',
        ...     details='Connection refused'
        ... )
    """

    def __init__(self, agent_type: str, host: str, details: str):
        """Initialize connection exception.

        Args:
            agent_type: Type of agent (e.g., 'claude-code-ssh')
            host: Host address that failed
            details: Detailed error message
        """
        context = {
            'agent_type': agent_type,
            'host': host,
            'details': details
        }
        recovery = (
            'Check network connectivity, verify agent process is running, '
            'and ensure firewall allows connection'
        )
        super().__init__(
            f'Cannot connect to {agent_type} at {host}: {details}',
            context,
            recovery
        )


class AgentTimeoutException(AgentException):
    """Raised when agent operation times out.

    Common causes:
    - Agent is processing but too slowly
    - Network latency too high
    - Agent process hung or deadlocked

    Example:
        >>> raise AgentTimeoutException(
        ...     operation='send_prompt',
        ...     timeout_seconds=30,
        ...     agent_type='claude-code'
        ... )
    """

    def __init__(self, operation: str, timeout_seconds: float, agent_type: str):
        """Initialize timeout exception.

        Args:
            operation: Operation that timed out
            timeout_seconds: Timeout duration
            agent_type: Type of agent
        """
        context = {
            'operation': operation,
            'timeout_seconds': timeout_seconds,
            'agent_type': agent_type
        }
        recovery = (
            'Increase timeout duration, check agent process health, '
            'or reduce task complexity'
        )
        super().__init__(
            f'Operation {operation} on {agent_type} timed out after {timeout_seconds}s',
            context,
            recovery
        )


class AgentProcessException(AgentException):
    """Raised when agent process crashes or exits unexpectedly.

    Common causes:
    - Agent process killed by OS (OOM, etc.)
    - Segmentation fault
    - Agent encountered internal error
    - Workspace permissions issue

    Example:
        >>> raise AgentProcessException(
        ...     agent_type='claude-code',
        ...     exit_code=137,
        ...     stderr='OOM killed'
        ... )
    """

    def __init__(
        self,
        agent_type: str,
        exit_code: Optional[int] = None,
        stderr: Optional[str] = None
    ):
        """Initialize process exception.

        Args:
            agent_type: Type of agent
            exit_code: Process exit code (if available)
            stderr: Process stderr output (if available)
        """
        context = {
            'agent_type': agent_type,
            'exit_code': exit_code,
            'stderr': stderr
        }
        recovery = (
            'Check agent logs, verify system resources (RAM, disk), '
            'and ensure workspace has correct permissions'
        )
        super().__init__(
            f'Agent process {agent_type} crashed (exit code: {exit_code})',
            context,
            recovery
        )


class AgentConfigException(AgentException):
    """Raised when agent configuration is invalid.

    Common causes:
    - Missing required configuration keys
    - Invalid values (wrong type, out of range)
    - Conflicting settings
    - Invalid file paths

    Example:
        >>> raise AgentConfigException(
        ...     agent_type='claude-code-ssh',
        ...     config_key='ssh_key_path',
        ...     details='File not found'
        ... )
    """

    def __init__(self, agent_type: str, config_key: str, details: str):
        """Initialize config exception.

        Args:
            agent_type: Type of agent
            config_key: Configuration key that's invalid
            details: Details about the problem
        """
        context = {
            'agent_type': agent_type,
            'config_key': config_key,
            'details': details
        }
        recovery = (
            f'Check {config_key} in configuration file, '
            'verify format and values are correct'
        )
        super().__init__(
            f'Invalid configuration for {agent_type}: {config_key} - {details}',
            context,
            recovery
        )


# LLM Plugin Exceptions

class LLMException(PluginException):
    """Base exception for LLM plugin errors.

    Raised when a local LLM provider (Ollama, llama.cpp, etc.) encounters an error.
    """
    pass


class LLMConnectionException(LLMException):
    """Raised when unable to connect to LLM service.

    Common causes:
    - Ollama/llama.cpp not running
    - Wrong host/port configuration
    - Network issues

    Example:
        >>> raise LLMConnectionException(
        ...     provider='ollama',
        ...     url='http://localhost:11434',
        ...     details='Connection refused'
        ... )
    """

    def __init__(self, provider: str, url: str, details: str):
        """Initialize LLM connection exception.

        Args:
            provider: LLM provider name
            url: URL that failed
            details: Error details
        """
        context = {
            'provider': provider,
            'url': url,
            'details': details
        }
        recovery = (
            f'Ensure {provider} is running, check URL {url}, '
            'and verify network connectivity'
        )
        super().__init__(
            f'Cannot connect to {provider} at {url}: {details}',
            context,
            recovery
        )


class LLMTimeoutException(LLMException):
    """Raised when LLM generation times out.

    Common causes:
    - Prompt too long/complex
    - Model too large for hardware
    - Context length exceeded

    Example:
        >>> raise LLMTimeoutException(
        ...     provider='ollama',
        ...     model='qwen2.5-coder:32b',
        ...     timeout_seconds=10
        ... )
    """

    def __init__(self, provider: str, model: str, timeout_seconds: float):
        """Initialize timeout exception.

        Args:
            provider: LLM provider
            model: Model name
            timeout_seconds: Timeout duration
        """
        context = {
            'provider': provider,
            'model': model,
            'timeout_seconds': timeout_seconds
        }
        recovery = (
            'Increase timeout, reduce prompt length, or use faster model'
        )
        super().__init__(
            f'{provider} generation with {model} timed out after {timeout_seconds}s',
            context,
            recovery
        )


class LLMModelNotFoundException(LLMException):
    """Raised when requested model is not available.

    Common causes:
    - Model not pulled/downloaded
    - Wrong model name
    - Model deleted

    Example:
        >>> raise LLMModelNotFoundException(
        ...     provider='ollama',
        ...     model='qwen2.5-coder:32b'
        ... )
    """

    def __init__(self, provider: str, model: str):
        """Initialize model not found exception.

        Args:
            provider: LLM provider
            model: Model name
        """
        context = {
            'provider': provider,
            'model': model
        }
        recovery = (
            f'Pull/download model with: ollama pull {model} '
            'or check model name spelling'
        )
        super().__init__(
            f'Model {model} not found in {provider}',
            context,
            recovery
        )


class LLMResponseException(LLMException):
    """Raised when LLM returns invalid or incomplete response.

    Common causes:
    - Generation stopped prematurely
    - Invalid JSON/format in response
    - Context length exceeded

    Example:
        >>> raise LLMResponseException(
        ...     provider='ollama',
        ...     details='Response truncated'
        ... )
    """

    def __init__(self, provider: str, details: str):
        """Initialize response exception.

        Args:
            provider: LLM provider
            details: Details about the problem
        """
        context = {
            'provider': provider,
            'details': details
        }
        recovery = (
            'Retry generation, reduce prompt length, or adjust generation parameters'
        )
        super().__init__(
            f'Invalid response from {provider}: {details}',
            context,
            recovery
        )


# Plugin Registry Exceptions

class PluginRegistryException(PluginException):
    """Base exception for plugin registry errors."""
    pass


class PluginNotFoundError(PluginRegistryException):
    """Raised when requested plugin is not registered.

    Common causes:
    - Plugin not imported/registered
    - Wrong plugin name
    - Plugin module not loaded

    Example:
        >>> raise PluginNotFoundError(
        ...     plugin_type='agent',
        ...     plugin_name='unknown-agent'
        ... )
    """

    def __init__(self, plugin_type: str, plugin_name: str, available: list):
        """Initialize plugin not found error.

        Args:
            plugin_type: Type of plugin ('agent' or 'llm')
            plugin_name: Requested plugin name
            available: List of available plugin names
        """
        context = {
            'plugin_type': plugin_type,
            'plugin_name': plugin_name,
            'available_plugins': available
        }
        recovery = (
            f'Use one of the available {plugin_type}s: {", ".join(available)} '
            f'or register {plugin_name} plugin'
        )
        super().__init__(
            f'{plugin_type.capitalize()} plugin "{plugin_name}" not found',
            context,
            recovery
        )


class PluginValidationError(PluginRegistryException):
    """Raised when plugin doesn't implement required interface.

    Common causes:
    - Missing required methods
    - Wrong method signatures
    - Doesn't inherit from base class

    Example:
        >>> raise PluginValidationError(
        ...     plugin_name='bad-agent',
        ...     missing_methods=['send_prompt', 'cleanup']
        ... )
    """

    def __init__(self, plugin_name: str, missing_methods: list):
        """Initialize validation error.

        Args:
            plugin_name: Plugin name
            missing_methods: List of missing method names
        """
        context = {
            'plugin_name': plugin_name,
            'missing_methods': missing_methods
        }
        recovery = (
            f'Implement missing methods: {", ".join(missing_methods)}'
        )
        super().__init__(
            f'Plugin {plugin_name} is missing required methods: {", ".join(missing_methods)}',
            context,
            recovery
        )
