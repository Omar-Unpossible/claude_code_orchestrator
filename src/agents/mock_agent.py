"""Mock agent for testing purposes."""

from typing import Dict, Any, Optional
from src.plugins.base import AgentPlugin
from src.plugins.registry import register_agent


@register_agent('mock')
class MockAgent(AgentPlugin):
    """Mock agent that returns predefined responses for testing.

    This agent is used in tests to avoid dependencies on external services.
    """

    def __init__(self):
        """Initialize mock agent."""
        super().__init__()
        self._response = "Mock response"
        self._initialized = False

    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize mock agent.

        Args:
            config: Configuration dictionary (ignored for mock)
        """
        self._initialized = True
        self._response = config.get('response', 'Mock response')

    def send_prompt(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Send prompt to mock agent.

        Args:
            prompt: The prompt to send
            context: Optional context dictionary

        Returns:
            Predefined mock response
        """
        return self._response

    def get_response(self, timeout: Optional[int] = None) -> str:
        """Get response from mock agent.

        Args:
            timeout: Optional timeout (ignored)

        Returns:
            Predefined mock response
        """
        return self._response

    def cleanup(self) -> None:
        """Cleanup mock agent resources."""
        self._initialized = False

    def is_healthy(self) -> bool:
        """Check if mock agent is healthy.

        Returns:
            Always True for mock agent
        """
        return self._initialized

    def read_file(self, file_path: str) -> str:
        """Read file content (mock).

        Args:
            file_path: Path to file

        Returns:
            Mock file content
        """
        return f"Mock content of {file_path}"

    def write_file(self, file_path: str, content: str) -> bool:
        """Write file content (mock).

        Args:
            file_path: Path to file
            content: Content to write

        Returns:
            Always True for mock agent
        """
        return True

    def get_workspace_files(self) -> list[str]:
        """Get list of workspace files (mock).

        Returns:
            Empty list for mock agent
        """
        return []

    def get_file_changes(self) -> Dict[str, Any]:
        """Get file changes (mock).

        Returns:
            Empty dict for mock agent
        """
        return {}
