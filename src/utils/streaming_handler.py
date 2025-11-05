"""Streaming log handler for real-time colored output.

This module provides a custom logging handler that outputs logs in real-time
with color coding for different agent communications (Orchestrator, Implementer).

Supports dynamic agent labels based on actual models in use:
- [ORCH:ollama] or [ORCH:openai-codex] for orchestrator
- [IMPL:claude-code] for implementer
- Legacy labels ([QWEN], [OBRA→CLAUDE]) still supported for backward compatibility

Part of Interactive Streaming Interface (Phase 1-2).
"""

import logging
from typing import Dict
import colorama

# Initialize colorama for cross-platform colored output
colorama.init()


class StreamingHandler(logging.Handler):
    """Custom log handler for real-time colored output.

    Colors different types of messages (dynamic labels support):
    - [ORCH:*] (orchestrator): Yellow
    - [IMPL:*] (implementer): Green
    - ORCH→IMPL: Blue
    - IMPL→ORCH: Green
    - Legacy labels ([QWEN], [OBRA→CLAUDE], etc.): Still supported
    - Errors: Red
    - Decisions: Cyan
    - Metadata: Dim white

    CRITICAL: Uses flush=True on print() for unbuffered output (<100ms latency).
    """

    # Color mapping for different message types
    COLOR_MAP: Dict[str, str] = {
        # New dynamic labels (Phase 1)
        '[ORCH:': colorama.Fore.YELLOW,  # Matches [ORCH:ollama], [ORCH:codex]
        '[IMPL:': colorama.Fore.GREEN,   # Matches [IMPL:claude-code]
        'ORCH→IMPL': colorama.Fore.BLUE,
        '[ORCH→IMPL]': colorama.Fore.BLUE,
        'IMPL→ORCH': colorama.Fore.GREEN,
        '[IMPL→ORCH]': colorama.Fore.GREEN,

        # Legacy labels (backward compatibility - deprecated but supported)
        'OBRA→CLAUDE': colorama.Fore.BLUE,
        '[OBRA→CLAUDE]': colorama.Fore.BLUE,
        'CLAUDE→OBRA': colorama.Fore.GREEN,
        '[CLAUDE→OBRA]': colorama.Fore.GREEN,
        'QWEN': colorama.Fore.YELLOW,
        '[QWEN]': colorama.Fore.YELLOW,

        # Level-based colors
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
    def format_orch_to_impl(iteration: int, chars: int, impl_name: str = 'claude-code') -> str:
        """Format Orch→Impl prompt message.

        Args:
            iteration: Current iteration number
            chars: Number of characters in prompt
            impl_name: Implementer name (e.g., 'claude-code')

        Returns:
            Formatted message string

        Example:
            >>> StreamingHandler.format_orch_to_impl(3, 1234, 'claude-code')
            '[ORCH→IMPL:claude-code] Iteration 3 | Prompt: 1,234 chars'
        """
        return f"[ORCH→IMPL:{impl_name}] Iteration {iteration} | Prompt: {chars:,} chars"

    @staticmethod
    def format_obra_to_claude(iteration: int, chars: int) -> str:
        """DEPRECATED: Use format_orch_to_impl() instead.

        Kept for backward compatibility.
        """
        return StreamingHandler.format_orch_to_impl(iteration, chars)

    @staticmethod
    def format_impl_to_orch(turns: int, chars: int, impl_name: str = 'claude-code') -> str:
        """Format Impl→Orch response message.

        Args:
            turns: Number of turns used
            chars: Number of characters in response
            impl_name: Implementer name (e.g., 'claude-code')

        Returns:
            Formatted message string

        Example:
            >>> StreamingHandler.format_impl_to_orch(2, 5678, 'claude-code')
            '[IMPL→ORCH:claude-code] Response received | Turns: 2 | 5,678 chars'
        """
        return f"[IMPL→ORCH:{impl_name}] Response received | Turns: {turns} | {chars:,} chars"

    @staticmethod
    def format_claude_to_obra(turns: int, chars: int) -> str:
        """DEPRECATED: Use format_impl_to_orch() instead.

        Kept for backward compatibility.
        """
        return StreamingHandler.format_impl_to_orch(turns, chars)

    @staticmethod
    def format_orch_validation(quality: float, decision: str, llm_name: str = 'ollama') -> str:
        """Format orchestrator validation message.

        Args:
            quality: Quality score (0.0-1.0)
            decision: Decision string (PROCEED/RETRY/etc.)
            llm_name: LLM name (e.g., 'ollama', 'openai-codex')

        Returns:
            Formatted message string

        Example:
            >>> StreamingHandler.format_orch_validation(0.81, 'PROCEED', 'ollama')
            '[ORCH:ollama] Quality: 0.81 (PASS) | Decision: PROCEED'
        """
        status = "PASS" if quality >= 0.7 else "FAIL"
        return f"[ORCH:{llm_name}] Quality: {quality:.2f} ({status}) | Decision: {decision}"

    @staticmethod
    def format_qwen_validation(quality: float, decision: str) -> str:
        """DEPRECATED: Use format_orch_validation() instead.

        Kept for backward compatibility.
        """
        return StreamingHandler.format_orch_validation(quality, decision, 'ollama')

    @staticmethod
    def format_separator() -> str:
        """Format separator line between iterations.

        Returns:
            Separator string (80 chars)
        """
        return "─" * 80
