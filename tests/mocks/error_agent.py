"""Error agent implementation for testing.

Always raises exceptions - useful for testing error handling.
"""

from pathlib import Path
from typing import List, Optional, Dict, Any
from src.plugins.base import AgentPlugin
from src.plugins.exceptions import AgentException, AgentTimeoutException


class ErrorAgent(AgentPlugin):
    """Agent that always fails with exceptions.

    Useful for testing error handling and recovery logic.

    Example:
        >>> agent = ErrorAgent()
        >>> agent.initialize({})
        >>> try:
        ...     agent.send_prompt("test")
        ... except AgentException:
        ...     print("Caught expected exception")
    """

    def __init__(self, exception_type: type = AgentException):
        """Initialize error agent.

        Args:
            exception_type: Type of exception to raise (default: AgentException)
        """
        self.exception_type = exception_type
        self.config = {}

    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize with configuration."""
        self.config = config
        # Allow overriding exception type via config
        exc_name = config.get('exception_type')
        if exc_name == 'timeout':
            self.exception_type = AgentTimeoutException

    def send_prompt(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Always raises exception."""
        if self.exception_type == AgentTimeoutException:
            raise AgentTimeoutException(
                operation='send_prompt',
                timeout_seconds=30,
                agent_type='error-agent'
            )
        raise AgentException(
            "ErrorAgent always fails",
            context={'prompt': prompt},
            recovery="Don't use ErrorAgent in production"
        )

    def get_workspace_files(self) -> List[Path]:
        """Raises exception."""
        raise self.exception_type("ErrorAgent always fails")

    def read_file(self, path: Path) -> str:
        """Raises exception."""
        raise self.exception_type("ErrorAgent always fails")

    def write_file(self, path: Path, content: str) -> None:
        """Raises exception."""
        raise self.exception_type("ErrorAgent always fails")

    def get_file_changes(
        self,
        since: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """Raises exception."""
        raise self.exception_type("ErrorAgent always fails")

    def is_healthy(self) -> bool:
        """Always unhealthy."""
        return False

    def cleanup(self) -> None:
        """Can't even clean up properly."""
        raise self.exception_type("ErrorAgent always fails")
