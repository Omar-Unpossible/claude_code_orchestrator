"""Plugin system for the Claude Code orchestrator.

This package provides the plugin architecture that enables:
- Multiple agent implementations (Claude Code, Aider, etc.)
- Multiple LLM providers (Ollama, llama.cpp, etc.)
- Easy testing with mock plugins
- Configuration-driven agent selection

Main components:
- base.py: Abstract base classes (AgentPlugin, LLMPlugin)
- registry.py: Registration and discovery system
- exceptions.py: Exception hierarchy for plugins
"""

from src.plugins.base import AgentPlugin, LLMPlugin
from src.plugins.registry import (
    AgentRegistry,
    LLMRegistry,
    register_agent,
    register_llm,
)
from src.plugins.exceptions import (
    PluginException,
    AgentException,
    AgentConnectionException,
    AgentTimeoutException,
    AgentProcessException,
    AgentConfigException,
    LLMException,
    LLMConnectionException,
    LLMTimeoutException,
    LLMModelNotFoundException,
    LLMResponseException,
    PluginRegistryException,
    PluginNotFoundError,
    PluginValidationError,
)

__all__ = [
    # Base classes
    'AgentPlugin',
    'LLMPlugin',
    # Registry
    'AgentRegistry',
    'LLMRegistry',
    'register_agent',
    'register_llm',
    # Exceptions
    'PluginException',
    'AgentException',
    'AgentConnectionException',
    'AgentTimeoutException',
    'AgentProcessException',
    'AgentConfigException',
    'LLMException',
    'LLMConnectionException',
    'LLMTimeoutException',
    'LLMModelNotFoundException',
    'LLMResponseException',
    'PluginRegistryException',
    'PluginNotFoundError',
    'PluginValidationError',
]
