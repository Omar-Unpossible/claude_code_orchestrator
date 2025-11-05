"""Plugin registration and discovery system.

This module provides registries for agents and LLMs with decorator-based
auto-registration, enabling configuration-driven plugin selection.
"""

import inspect
import logging
from typing import Dict, List, Type, Any
from threading import RLock

from src.plugins.base import AgentPlugin, LLMPlugin
from src.plugins.exceptions import (
    PluginNotFoundError,
    PluginValidationError,
    PluginRegistryException
)

logger = logging.getLogger(__name__)


class AgentRegistry:
    """Registry for agent plugins with decorator-based registration.

    **Singleton Pattern**: This registry operates at the class level using
    class methods and class attributes. Do NOT instantiate this class - use
    AgentRegistry.register(), AgentRegistry.get(), etc. directly as class
    methods. The registry maintains global state shared across all access points.

    This registry enables runtime discovery and instantiation of agents
    based on configuration, without hardcoding agent types.

    Thread-safe for concurrent registration and retrieval.

    Example:
        >>> from src.plugins.registry import register_agent
        >>> @register_agent('my-agent')
        ... class MyAgent(AgentPlugin):
        ...     pass
        ...
        >>> # Later, load agent from config (use class method, NOT instance)
        >>> agent_class = AgentRegistry.get('my-agent')
        >>> agent = agent_class()
        >>> agent.initialize(config)
        >>>
        >>> # WRONG: Do not instantiate registry
        >>> # registry = AgentRegistry()  # Don't do this!
    """

    _agents: Dict[str, Type[AgentPlugin]] = {}
    _lock = RLock()  # Thread-safe registration

    @classmethod
    def register(
        cls,
        name: str,
        agent_class: Type[AgentPlugin],
        validate: bool = True
    ) -> None:
        """Register an agent plugin.

        Args:
            name: Unique name for the agent (e.g., 'claude-code-ssh')
            agent_class: Agent class (must inherit from AgentPlugin)
            validate: Whether to validate interface implementation (default: True)

        Raises:
            PluginValidationError: If agent doesn't implement required interface
            TypeError: If agent_class is not a class

        Example:
            >>> AgentRegistry.register('test-agent', MyAgentClass)
        """
        with cls._lock:
            # Validate input
            if not inspect.isclass(agent_class):
                raise TypeError(
                    f"agent_class must be a class, got {type(agent_class)}"
                )

            # Validate interface implementation
            if validate and not issubclass(agent_class, AgentPlugin):
                raise PluginValidationError(
                    plugin_name=name,
                    missing_methods=['Must inherit from AgentPlugin']
                )

            if validate:
                missing = cls._validate_interface(agent_class)
                if missing:
                    raise PluginValidationError(
                        plugin_name=name,
                        missing_methods=missing
                    )

            # Warn if overriding existing registration
            if name in cls._agents:
                logger.warning(
                    f"Overriding existing agent registration: {name} "
                    f"(was {cls._agents[name].__name__}, now {agent_class.__name__})"
                )

            cls._agents[name] = agent_class
            logger.debug(f"Registered agent: {name} -> {agent_class.__name__}")

    @classmethod
    def get(cls, name: str) -> Type[AgentPlugin]:
        """Get agent class by name.

        Args:
            name: Agent name

        Returns:
            Agent class

        Raises:
            PluginNotFoundError: If agent not registered

        Example:
            >>> agent_class = AgentRegistry.get('claude-code-ssh')
            >>> agent = agent_class()
        """
        with cls._lock:
            if name not in cls._agents:
                available = cls.list()
                raise PluginNotFoundError(
                    plugin_type='agent',
                    plugin_name=name,
                    available=available
                )
            return cls._agents[name]

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """Check if an agent is registered.

        Args:
            name: Agent name

        Returns:
            True if agent is registered, False otherwise

        Example:
            >>> if AgentRegistry.is_registered('claude-code-ssh'):
            ...     agent = AgentRegistry.get('claude-code-ssh')
        """
        with cls._lock:
            return name in cls._agents

    @classmethod
    def list(cls) -> List[str]:
        """List all registered agent names.

        Returns:
            List of registered agent names

        Example:
            >>> available = AgentRegistry.list()
            >>> print(available)
            ['claude-code-ssh', 'aider', 'mock']
        """
        with cls._lock:
            return list(cls._agents.keys())

    @classmethod
    def unregister(cls, name: str) -> None:
        """Remove agent from registry.

        Useful for testing or dynamic plugin unloading.

        Args:
            name: Agent name to remove

        Example:
            >>> AgentRegistry.unregister('test-agent')
        """
        with cls._lock:
            if name in cls._agents:
                del cls._agents[name]
                logger.debug(f"Unregistered agent: {name}")

    @classmethod
    def clear(cls) -> None:
        """Clear all registrations.

        WARNING: Use only in tests! This removes all registered agents.

        Example:
            >>> # In test teardown
            >>> AgentRegistry.clear()
        """
        with cls._lock:
            cls._agents.clear()
            logger.debug("Cleared all agent registrations")

    @classmethod
    def _validate_interface(cls, agent_class: Type[AgentPlugin]) -> List[str]:
        """Validate that agent implements all required methods.

        Args:
            agent_class: Agent class to validate

        Returns:
            List of missing method names (empty if valid)
        """
        required_methods = [
            'initialize',
            'send_prompt',
            'get_workspace_files',
            'read_file',
            'write_file',
            'get_file_changes',
            'is_healthy',
            'cleanup'
        ]

        missing = []
        for method_name in required_methods:
            if not hasattr(agent_class, method_name):
                missing.append(method_name)
            elif not callable(getattr(agent_class, method_name)):
                missing.append(f"{method_name} (not callable)")

        return missing


class LLMRegistry:
    """Registry for LLM plugins with decorator-based registration.

    **Singleton Pattern**: This registry operates at the class level using
    class methods and class attributes. Do NOT instantiate this class - use
    LLMRegistry.register(), LLMRegistry.get(), etc. directly as class methods.
    The registry maintains global state shared across all access points.

    Similar to AgentRegistry but for LLM providers (Ollama, llama.cpp, etc.).

    Thread-safe for concurrent registration and retrieval.

    Example:
        >>> from src.plugins.registry import register_llm
        >>> @register_llm('my-llm')
        ... class MyLLM(LLMPlugin):
        ...     pass
        ...
        >>> # Later (use class method, NOT instance)
        >>> llm_class = LLMRegistry.get('my-llm')
        >>> llm = llm_class()
        >>>
        >>> # WRONG: Do not instantiate registry
        >>> # registry = LLMRegistry()  # Don't do this!
    """

    _llms: Dict[str, Type[LLMPlugin]] = {}
    _lock = RLock()

    @classmethod
    def register(
        cls,
        name: str,
        llm_class: Type[LLMPlugin],
        validate: bool = True
    ) -> None:
        """Register an LLM plugin.

        Args:
            name: Unique name for LLM (e.g., 'ollama')
            llm_class: LLM class (must inherit from LLMPlugin)
            validate: Whether to validate interface implementation

        Raises:
            PluginValidationError: If LLM doesn't implement required interface
            TypeError: If llm_class is not a class
        """
        with cls._lock:
            if not inspect.isclass(llm_class):
                raise TypeError(
                    f"llm_class must be a class, got {type(llm_class)}"
                )

            if validate and not issubclass(llm_class, LLMPlugin):
                raise PluginValidationError(
                    plugin_name=name,
                    missing_methods=['Must inherit from LLMPlugin']
                )

            if validate:
                missing = cls._validate_interface(llm_class)
                if missing:
                    raise PluginValidationError(
                        plugin_name=name,
                        missing_methods=missing
                    )

            if name in cls._llms:
                logger.warning(
                    f"Overriding existing LLM registration: {name} "
                    f"(was {cls._llms[name].__name__}, now {llm_class.__name__})"
                )

            cls._llms[name] = llm_class
            logger.debug(f"Registered LLM: {name} -> {llm_class.__name__}")

    @classmethod
    def get(cls, name: str) -> Type[LLMPlugin]:
        """Get LLM class by name.

        Args:
            name: LLM name

        Returns:
            LLM class

        Raises:
            PluginNotFoundError: If LLM not registered
        """
        with cls._lock:
            if name not in cls._llms:
                available = cls.list()
                raise PluginNotFoundError(
                    plugin_type='llm',
                    plugin_name=name,
                    available=available
                )
            return cls._llms[name]

    @classmethod
    def list(cls) -> List[str]:
        """List all registered LLM names.

        Returns:
            List of registered LLM names
        """
        with cls._lock:
            return list(cls._llms.keys())

    @classmethod
    def unregister(cls, name: str) -> None:
        """Remove LLM from registry."""
        with cls._lock:
            if name in cls._llms:
                del cls._llms[name]
                logger.debug(f"Unregistered LLM: {name}")

    @classmethod
    def clear(cls) -> None:
        """Clear all LLM registrations (use only in tests!)."""
        with cls._lock:
            cls._llms.clear()
            logger.debug("Cleared all LLM registrations")

    @classmethod
    def _validate_interface(cls, llm_class: Type[LLMPlugin]) -> List[str]:
        """Validate that LLM implements all required methods."""
        required_methods = [
            'initialize',
            'generate',
            'generate_stream',
            'estimate_tokens',
            'is_available'
        ]

        missing = []
        for method_name in required_methods:
            if not hasattr(llm_class, method_name):
                missing.append(method_name)
            elif not callable(getattr(llm_class, method_name)):
                missing.append(f"{method_name} (not callable)")

        return missing


# Decorator functions for convenient registration

def register_agent(name: str, validate: bool = True):
    """Decorator for auto-registering agent plugins.

    Args:
        name: Unique name for the agent
        validate: Whether to validate interface implementation

    Returns:
        Decorator function

    Example:
        >>> @register_agent('claude-code-ssh')
        ... class ClaudeCodeSSHAgent(AgentPlugin):
        ...     def initialize(self, config):
        ...         pass
        ...     # ... implement other methods
    """
    def decorator(agent_class: Type[AgentPlugin]) -> Type[AgentPlugin]:
        AgentRegistry.register(name, agent_class, validate=validate)
        return agent_class
    return decorator


def register_llm(name: str, validate: bool = True):
    """Decorator for auto-registering LLM plugins.

    Args:
        name: Unique name for the LLM
        validate: Whether to validate interface implementation

    Returns:
        Decorator function

    Example:
        >>> @register_llm('ollama')
        ... class OllamaProvider(LLMPlugin):
        ...     def initialize(self, config):
        ...         pass
        ...     # ... implement other methods
    """
    def decorator(llm_class: Type[LLMPlugin]) -> Type[LLMPlugin]:
        LLMRegistry.register(name, llm_class, validate=validate)
        return llm_class
    return decorator
