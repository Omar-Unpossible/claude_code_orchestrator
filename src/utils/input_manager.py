"""Input manager for non-blocking user input in interactive mode.

This module provides a thread-safe input manager that listens for user commands
in a separate thread, allowing the orchestrator to continue execution while
waiting for input.

v1.5.0: Updated for natural language default behavior. Slash commands only
        appear in autocomplete when user types '/'.

Part of Interactive Streaming Interface (Phase 2).
"""

import logging
import threading
from queue import Queue, Empty
from typing import Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter, Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.history import InMemoryHistory

logger = logging.getLogger(__name__)

# Slash command names for autocompletion (v1.5.0)
SLASH_COMMANDS = [
    '/help',
    '/status',
    '/pause',
    '/resume',
    '/stop',
    '/to-impl',
    '/to-claude',        # Alias
    '/to-implementer',   # Formal
    '/override-decision',
]


class SlashCommandCompleter(Completer):
    """Custom completer that only completes slash commands.

    Only provides completions when user input starts with '/'.
    This allows natural language input without autocomplete interference.
    """

    def get_completions(self, document: Document, complete_event):
        """Provide tab completions for slash commands only.

        Args:
            document: Current document state
            complete_event: Completion event

        Yields:
            Completion objects for matching slash commands
        """
        text = document.text_before_cursor

        # Only complete if text starts with '/'
        if text.startswith('/'):
            word = text[1:]  # Remove leading slash for matching
            for cmd in SLASH_COMMANDS:
                if cmd[1:].startswith(word.lower()):  # Case-insensitive match
                    yield Completion(
                        cmd,
                        start_position=-len(text),
                        display_meta="Command"
                    )


class InputManager:
    """Manage non-blocking user input in separate thread.

    Uses prompt_toolkit for rich input experience with command history
    and autocompletion. Commands are placed in a thread-safe queue for
    the orchestrator to consume.

    Thread-safe for concurrent access.

    Attributes:
        command_queue: Thread-safe queue for passing commands
        listening: Flag indicating if input thread is active
        thread: Background thread for input listening
        session: PromptSession for rich input

    Example:
        >>> manager = InputManager()
        >>> manager.start_listening()
        >>> # Wait for user input...
        >>> command = manager.get_command(timeout=0.1)
        >>> if command:
        ...     print(f"User typed: {command}")
        >>> manager.stop_listening()
    """

    def __init__(self):
        """Initialize input manager."""
        self.command_queue: Queue = Queue()
        self.listening = False
        self.thread: Optional[threading.Thread] = None
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # Create prompt session with history and autocomplete (v1.5.0)
        self.history = InMemoryHistory()
        self.completer = SlashCommandCompleter()
        self.session = PromptSession(
            history=self.history,
            completer=self.completer,
            complete_while_typing=False,  # Only complete on TAB
            bottom_toolbar="Type naturally to talk to orchestrator, or /help for commands"
        )

    def start_listening(self) -> None:
        """Start input listener thread.

        Creates and starts a daemon thread that continuously listens
        for user input and places it in the command queue.

        Raises:
            RuntimeError: If already listening
        """
        if self.listening:
            raise RuntimeError("InputManager already listening")

        self.listening = True
        self.thread = threading.Thread(
            target=self._input_loop,
            daemon=True,  # Thread exits when main program exits
            name="InputManager-Thread"
        )
        self.thread.start()
        self.logger.debug("Started input listener thread")

    def stop_listening(self) -> None:
        """Stop input listener thread.

        Sets the listening flag to False and waits for the thread to
        terminate (with timeout).
        """
        if not self.listening:
            return

        self.listening = False

        # Wait for thread to finish (with timeout)
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)

        if self.thread and self.thread.is_alive():
            self.logger.warning("Input thread did not terminate cleanly")
        else:
            self.logger.debug("Stopped input listener thread")

        self.thread = None

    def get_command(self, timeout: float = 0.1) -> Optional[str]:
        """Get command from queue (non-blocking with timeout).

        Args:
            timeout: Maximum time to wait for command (seconds)

        Returns:
            Command string if available, None if queue is empty

        Example:
            >>> command = manager.get_command(timeout=0.1)
            >>> if command:
            ...     print(f"Got command: {command}")
        """
        try:
            return self.command_queue.get(timeout=timeout)
        except Empty:
            return None

    def _input_loop(self) -> None:
        """Input listener loop (runs in background thread).

        Continuously prompts for user input and places it in the queue.
        Runs until listening flag is set to False.
        """
        self.logger.debug("Input loop started")

        while self.listening:
            try:
                # Prompt for input (this blocks until user presses Enter)
                # Using prompt_toolkit's PromptSession for rich features
                user_input = self.session.prompt('> ')

                if user_input.strip():
                    # Put command in queue for orchestrator to consume
                    self.command_queue.put(user_input.strip())
                    self.logger.debug(f"Queued command: {user_input[:50]}")

            except (EOFError, KeyboardInterrupt):
                # User pressed Ctrl+D or Ctrl+C
                self.logger.debug("Input interrupted by user")
                break
            except Exception as e:
                # Log but don't crash the thread
                self.logger.error(f"Error in input loop: {e}", exc_info=True)
                # Brief sleep to avoid tight loop on repeated errors
                import time
                time.sleep(0.1)

        self.logger.debug("Input loop terminated")

    def is_listening(self) -> bool:
        """Check if input manager is currently listening.

        Returns:
            True if listening, False otherwise
        """
        return self.listening and self.thread is not None and self.thread.is_alive()

    def get_input_with_timeout(self, prompt: str, timeout: int = 60) -> str:
        """Get user input with timeout for confirmation prompts.

        This is a synchronous method for getting direct input with a timeout,
        separate from the background command queue. Used for confirmation prompts
        where we need immediate user response.

        Args:
            prompt: Prompt text to display
            timeout: Timeout in seconds (default: 60)

        Returns:
            User input string

        Raises:
            TimeoutError: If user doesn't respond within timeout

        Example:
            >>> try:
            ...     response = manager.get_input_with_timeout("Confirm (y/n)? ", timeout=30)
            ...     if response == 'y':
            ...         print("Confirmed")
            ... except TimeoutError:
            ...     print("Timeout - aborting")
        """
        import threading
        import sys

        result = []
        error = []

        def input_thread():
            """Thread to get input."""
            try:
                user_input = input(prompt)
                result.append(user_input)
            except Exception as e:
                error.append(e)

        # Start input thread
        thread = threading.Thread(target=input_thread, daemon=True)
        thread.start()

        # Wait for thread with timeout
        thread.join(timeout=timeout)

        # Check if thread completed
        if thread.is_alive():
            # Timeout occurred
            self.logger.warning(f"Input timeout after {timeout}s")
            raise TimeoutError(f"Input timeout after {timeout} seconds")

        # Check for errors
        if error:
            raise error[0]

        # Return result
        if result:
            return result[0]
        else:
            # Thread finished but no result (shouldn't happen)
            raise RuntimeError("Input thread finished without result")
