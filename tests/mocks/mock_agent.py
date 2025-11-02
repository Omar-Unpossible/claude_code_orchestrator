"""Mock agent implementation for testing.

Provides a configurable test double that tracks all interactions.
"""

import time
from pathlib import Path
from typing import List, Optional, Dict, Any
from src.plugins.base import AgentPlugin


class MockAgent(AgentPlugin):
    """Configurable mock agent for testing.

    This test double returns predefined responses and tracks all interactions,
    enabling testing of orchestration logic without real agents.

    Example:
        >>> agent = MockAgent()
        >>> agent.initialize({})
        >>> agent.set_response("Task completed successfully")
        >>> response = agent.send_prompt("Do something")
        >>> assert response == "Task completed successfully"
        >>> assert agent.call_count == 1
    """

    def __init__(self):
        """Initialize mock agent."""
        self.config = {}
        self.responses = []  # Queue of responses to return
        self.default_response = "Mock response"
        self.prompts_received = []  # History of prompts
        self.call_count = 0
        self.workspace_files = []  # Simulated workspace files
        self.file_contents = {}  # Simulated file contents
        self.file_changes = []  # Simulated file changes
        self.healthy = True

    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize with configuration."""
        self.config = config
        self.workspace_path = Path(config.get('workspace_path', '/tmp/mock_workspace'))

    def send_prompt(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Send prompt and return configured response."""
        self.call_count += 1
        self.prompts_received.append({
            'prompt': prompt,
            'context': context,
            'timestamp': time.time()
        })

        # Return next queued response or default
        if self.responses:
            return self.responses.pop(0)
        return self.default_response

    def get_workspace_files(self) -> List[Path]:
        """Return configured workspace files."""
        return self.workspace_files.copy()

    def read_file(self, path: Path) -> str:
        """Read from simulated file system."""
        path_str = str(path)
        if path_str not in self.file_contents:
            raise FileNotFoundError(f"File not found: {path}")
        return self.file_contents[path_str]

    def write_file(self, path: Path, content: str) -> None:
        """Write to simulated file system."""
        path_str = str(path)
        change_type = 'modified' if path_str in self.file_contents else 'created'
        self.file_contents[path_str] = content

        # Add to workspace files if new
        if path not in self.workspace_files:
            self.workspace_files.append(path)

        # Record change
        self.file_changes.append({
            'path': path,
            'change_type': change_type,
            'timestamp': time.time(),
            'hash': hash(content),
            'size': len(content)
        })

    def get_file_changes(
        self,
        since: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """Return configured file changes."""
        if since is None:
            return self.file_changes.copy()

        return [
            change for change in self.file_changes
            if change['timestamp'] >= since
        ]

    def is_healthy(self) -> bool:
        """Return configured health status."""
        return self.healthy

    def cleanup(self) -> None:
        """Clean up resources."""
        # Nothing to clean up in mock
        pass

    # Helper methods for testing

    def set_response(self, response: str) -> None:
        """Set single response to return."""
        self.responses = [response]

    def set_responses(self, responses: List[str]) -> None:
        """Set multiple responses to return in order."""
        self.responses = responses.copy()

    def set_healthy(self, healthy: bool) -> None:
        """Configure health status."""
        self.healthy = healthy

    def add_file(self, path: Path, content: str) -> None:
        """Add file to simulated workspace."""
        path_str = str(path)
        self.file_contents[path_str] = content
        if path not in self.workspace_files:
            self.workspace_files.append(path)

    def reset(self) -> None:
        """Reset mock state for next test."""
        self.responses = []
        self.prompts_received = []
        self.call_count = 0
        self.workspace_files = []
        self.file_contents = {}
        self.file_changes = []
        self.healthy = True
