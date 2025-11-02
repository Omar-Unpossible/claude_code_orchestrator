"""Slow agent implementation for testing.

Adds configurable delays - useful for testing timeouts.
"""

import time
from pathlib import Path
from typing import List, Optional, Dict, Any
from src.plugins.base import AgentPlugin


class SlowAgent(AgentPlugin):
    """Agent that adds delays to test timeout handling.

    Example:
        >>> agent = SlowAgent(delay_seconds=5)
        >>> agent.initialize({})
        >>> # This will take 5 seconds
        >>> response = agent.send_prompt("test")
    """

    def __init__(self, delay_seconds: float = 1.0):
        """Initialize slow agent.

        Args:
            delay_seconds: Delay to add to each operation
        """
        self.delay_seconds = delay_seconds
        self.config = {}

    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize with configuration."""
        self.config = config
        # Allow overriding delay via config
        self.delay_seconds = config.get('delay_seconds', self.delay_seconds)

    def send_prompt(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Send prompt with delay."""
        time.sleep(self.delay_seconds)
        return f"Response after {self.delay_seconds}s: {prompt}"

    def get_workspace_files(self) -> List[Path]:
        """Return empty workspace after delay."""
        time.sleep(self.delay_seconds)
        return []

    def read_file(self, path: Path) -> str:
        """Read file with delay."""
        time.sleep(self.delay_seconds)
        raise FileNotFoundError(f"SlowAgent has no files: {path}")

    def write_file(self, path: Path, content: str) -> None:
        """Write file with delay."""
        time.sleep(self.delay_seconds)

    def get_file_changes(
        self,
        since: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """Return changes after delay."""
        time.sleep(self.delay_seconds)
        return []

    def is_healthy(self) -> bool:
        """Health check with delay."""
        time.sleep(self.delay_seconds)
        return True

    def cleanup(self) -> None:
        """Cleanup with delay."""
        time.sleep(self.delay_seconds)
