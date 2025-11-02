"""Mock plugin implementations for testing.

This module provides test doubles for agents and LLMs, enabling testing
without real SSH connections or LLM inference.
"""

from tests.mocks.mock_agent import MockAgent
from tests.mocks.echo_agent import EchoAgent
from tests.mocks.error_agent import ErrorAgent
from tests.mocks.slow_agent import SlowAgent
from tests.mocks.mock_llm import MockLLM

__all__ = [
    'MockAgent',
    'EchoAgent',
    'ErrorAgent',
    'SlowAgent',
    'MockLLM',
]
