"""Streaming log handler for real-time colored output.

This module provides a custom logging handler that outputs logs in real-time
with color coding for different agent communications (Obra, Claude, Qwen).

Part of Interactive Streaming Interface (Phase 1).
"""

import logging
from typing import Dict
import colorama

# Initialize colorama for cross-platform colored output
colorama.init()


class StreamingHandler(logging.Handler):
    """Custom log handler for real-time colored output.

    Colors different types of messages:
    - OBRA→CLAUDE: Blue
    - CLAUDE→OBRA: Green
    - QWEN: Yellow
    - Errors: Red
    - Decisions: Cyan
    - Metadata: Dim white

    CRITICAL: Uses flush=True on print() for unbuffered output (<100ms latency).
    """

    # Color mapping for different message types
    COLOR_MAP: Dict[str, str] = {
        'OBRA→CLAUDE': colorama.Fore.BLUE,
        '[OBRA→CLAUDE]': colorama.Fore.BLUE,
        'CLAUDE→OBRA': colorama.Fore.GREEN,
        '[CLAUDE→OBRA]': colorama.Fore.GREEN,
        'QWEN': colorama.Fore.YELLOW,
        '[QWEN]': colorama.Fore.YELLOW,
        'ERROR': colorama.Fore.RED,
        'CRITICAL': colorama.Fore.RED + colorama.Style.BRIGHT,
        'DECISION': colorama.Fore.CYAN,
        '[OBRA]': colorama.Fore.CYAN,
        'WARNING': colorama.Fore.YELLOW,
    }

    def __init__(self):
        """Initialize the streaming handler."""
        super().__init__()
        self.setFormatter(logging.Formatter('%(message)s'))

    def emit(self, record: logging.LogRecord) -> None:
        """Format and output log record with color coding.

        Args:
            record: LogRecord to emit

        Note:
            Uses flush=True for unbuffered output (critical for streaming latency).
        """
        try:
            msg = self.format(record)

            # Determine color based on message content
            color = colorama.Fore.WHITE  # Default color
            for keyword, keyword_color in self.COLOR_MAP.items():
                if keyword in msg:
                    color = keyword_color
                    break

            # Special handling for level-based coloring if no keyword match
            if color == colorama.Fore.WHITE:
                if record.levelno >= logging.ERROR:
                    color = colorama.Fore.RED
                elif record.levelno >= logging.WARNING:
                    color = colorama.Fore.YELLOW

            # Print with color and CRITICAL flush=True for immediate output
            print(f"{color}{msg}{colorama.Style.RESET_ALL}", flush=True)

        except Exception:
            self.handleError(record)

    @staticmethod
    def format_obra_to_claude(iteration: int, chars: int) -> str:
        """Format Obra→Claude prompt message.

        Args:
            iteration: Current iteration number
            chars: Number of characters in prompt

        Returns:
            Formatted message string
        """
        return f"[OBRA→CLAUDE] Iteration {iteration} | Prompt: {chars:,} chars"

    @staticmethod
    def format_claude_to_obra(turns: int, chars: int) -> str:
        """Format Claude→Obra response message.

        Args:
            turns: Number of turns used
            chars: Number of characters in response

        Returns:
            Formatted message string
        """
        return f"[CLAUDE→OBRA] Response received | Turns: {turns} | {chars:,} chars"

    @staticmethod
    def format_qwen_validation(quality: float, decision: str) -> str:
        """Format Qwen validation message.

        Args:
            quality: Quality score (0.0-1.0)
            decision: Decision string (PROCEED/RETRY/etc.)

        Returns:
            Formatted message string
        """
        status = "PASS" if quality >= 0.7 else "FAIL"
        return f"[QWEN] Quality: {quality:.2f} ({status}) | Decision: {decision}"

    @staticmethod
    def format_separator() -> str:
        """Format separator line between iterations.

        Returns:
            Separator string (80 chars)
        """
        return "─" * 80
