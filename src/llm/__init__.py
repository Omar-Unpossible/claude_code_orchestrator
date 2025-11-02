"""LLM interface components for the orchestrator.

This package provides:
- Local LLM interface (Ollama/Qwen)
- Prompt generation with templates
- Response validation and quality checks
- Token counting and context management
"""

from src.llm.local_interface import LocalLLMInterface
from src.llm.response_validator import ResponseValidator

__all__ = ['LocalLLMInterface', 'ResponseValidator']
