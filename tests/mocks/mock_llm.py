"""Mock LLM implementation for testing.

Provides configurable test double for LLM providers.
"""

from typing import Dict, Any, Iterator
from src.plugins.base import LLMPlugin
from src.plugins.registry import register_llm


@register_llm('mock')
class MockLLM(LLMPlugin):
    """Configurable mock LLM for testing.

    Returns predefined responses and tracks all interactions.

    Example:
        >>> llm = MockLLM()
        >>> llm.initialize({'model': 'test'})
        >>> llm.set_response("This is a test response")
        >>> response = llm.generate("Hello")
        >>> assert response == "This is a test response"
    """

    def __init__(self):
        """Initialize mock LLM."""
        self.config = {}
        self.responses = []  # Queue of responses
        self.default_response = "Mock LLM response"
        self.prompts_received = []  # History
        self.call_count = 0
        self.available = True
        self.tokens_per_word = 1.3  # Rough estimate for token counting

    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize with configuration."""
        self.config = config
        self.model = config.get('model', 'mock-model')

    def generate(self, prompt: str, **kwargs) -> str:
        """Generate response."""
        self.call_count += 1
        self.prompts_received.append({
            'prompt': prompt,
            'kwargs': kwargs
        })

        # Return next queued response or default
        if self.responses:
            return self.responses.pop(0)
        return self.default_response

    def generate_stream(self, prompt: str, **kwargs) -> Iterator[str]:
        """Generate streaming response."""
        response = self.generate(prompt, **kwargs)
        # Yield response word by word
        words = response.split()
        for word in words:
            yield word + ' '

    def estimate_tokens(self, text: str) -> int:
        """Estimate tokens (rough word count)."""
        word_count = len(text.split())
        return int(word_count * self.tokens_per_word)

    def is_available(self) -> bool:
        """Return configured availability."""
        return self.available

    def get_model_info(self) -> Dict[str, Any]:
        """Return mock model info."""
        return {
            'model_name': self.model,
            'context_length': 4096,
            'quantization': 'Q4_K_M',
            'size_gb': 20.0
        }

    # Helper methods for testing

    def set_response(self, response: str) -> None:
        """Set single response."""
        self.responses = [response]

    def set_responses(self, responses: list) -> None:
        """Set multiple responses."""
        self.responses = responses.copy()

    def set_available(self, available: bool) -> None:
        """Configure availability."""
        self.available = available

    def reset(self) -> None:
        """Reset mock state."""
        self.responses = []
        self.prompts_received = []
        self.call_count = 0
        self.available = True
