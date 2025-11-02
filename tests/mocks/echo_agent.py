"""Echo agent implementation for testing.

Returns the prompt as the response - useful for simple orchestration tests.
"""

from pathlib import Path
from typing import List, Optional, Dict, Any
from src.plugins.base import AgentPlugin


class EchoAgent(AgentPlugin):
    """Agent that echoes the prompt back as response.

    Useful for testing orchestration logic when you need predictable,
    simple responses.

    Example:
        >>> agent = EchoAgent()
        >>> agent.initialize({})
        >>> response = agent.send_prompt("Hello world")
        >>> assert response == "Echo: Hello world"
    """

    def __init__(self):
        """Initialize echo agent."""
        self.config = {}
        self.workspace_path = None

    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize with configuration."""
        self.config = config
        self.workspace_path = Path(config.get('workspace_path', '/tmp/echo_workspace'))

    def send_prompt(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Echo the prompt back."""
        return f"Echo: {prompt}"

    def get_workspace_files(self) -> List[Path]:
        """Return empty workspace."""
        return []

    def read_file(self, path: Path) -> str:
        """Reading files not supported."""
        raise FileNotFoundError(f"EchoAgent has no files: {path}")

    def write_file(self, path: Path, content: str) -> None:
        """Writing files not supported."""
        pass  # Silently ignore writes

    def get_file_changes(
        self,
        since: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """Return no changes."""
        return []

    def is_healthy(self) -> bool:
        """Always healthy."""
        return True

    def cleanup(self) -> None:
        """Nothing to clean up."""
        pass
