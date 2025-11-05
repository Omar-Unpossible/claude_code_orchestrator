"""Tests for StreamingHandler (Phase 1).

Compliance with TEST_GUIDELINES.md:
- No sleeps
- No threads
- Minimal memory (< 10KB)
- Focus on formatting and color coding
"""

import logging
import io
import sys
from unittest.mock import patch

import pytest
import colorama

from src.utils.streaming_handler import StreamingHandler


class TestStreamingHandler:
    """Test suite for StreamingHandler."""

    def test_handler_initialization(self):
        """Test that handler initializes correctly."""
        handler = StreamingHandler()
        assert handler is not None
        assert isinstance(handler, logging.Handler)

    def test_color_map_contains_keywords(self):
        """Test that color map contains expected keywords."""
        handler = StreamingHandler()
        assert 'OBRA→CLAUDE' in handler.COLOR_MAP
        assert '[OBRA→CLAUDE]' in handler.COLOR_MAP
        assert 'CLAUDE→OBRA' in handler.COLOR_MAP
        assert '[CLAUDE→OBRA]' in handler.COLOR_MAP
        assert 'QWEN' in handler.COLOR_MAP
        assert '[QWEN]' in handler.COLOR_MAP
        assert 'ERROR' in handler.COLOR_MAP
        assert '[OBRA]' in handler.COLOR_MAP

    def test_emit_obra_to_claude(self, capsys):
        """Test that OBRA→CLAUDE messages are colored blue."""
        handler = StreamingHandler()
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='',
            lineno=0,
            msg='[OBRA→CLAUDE] Test message',
            args=(),
            exc_info=None
        )

        handler.emit(record)
        captured = capsys.readouterr()

        # Check that output contains the message
        assert '[OBRA→CLAUDE]' in captured.out
        assert 'Test message' in captured.out
        # Check that blue color code is present
        assert colorama.Fore.BLUE in captured.out

    def test_emit_claude_to_obra(self, capsys):
        """Test that CLAUDE→OBRA messages are colored green."""
        handler = StreamingHandler()
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='',
            lineno=0,
            msg='[CLAUDE→OBRA] Response received',
            args=(),
            exc_info=None
        )

        handler.emit(record)
        captured = capsys.readouterr()

        # Check that output contains the message
        assert '[CLAUDE→OBRA]' in captured.out
        assert 'Response received' in captured.out
        # Check that green color code is present
        assert colorama.Fore.GREEN in captured.out

    def test_emit_qwen_validation(self, capsys):
        """Test that QWEN messages are colored yellow."""
        handler = StreamingHandler()
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='',
            lineno=0,
            msg='[QWEN] Quality: 0.76 (PASS)',
            args=(),
            exc_info=None
        )

        handler.emit(record)
        captured = capsys.readouterr()

        # Check that output contains the message
        assert '[QWEN]' in captured.out
        assert 'Quality' in captured.out
        # Check that yellow color code is present
        assert colorama.Fore.YELLOW in captured.out

    def test_emit_error_message(self, capsys):
        """Test that ERROR messages are colored red."""
        handler = StreamingHandler()
        record = logging.LogRecord(
            name='test',
            level=logging.ERROR,
            pathname='',
            lineno=0,
            msg='ERROR: Something went wrong',
            args=(),
            exc_info=None
        )

        handler.emit(record)
        captured = capsys.readouterr()

        # Check that output contains the message
        assert 'ERROR' in captured.out
        # Check that red color code is present
        assert colorama.Fore.RED in captured.out

    def test_emit_decision(self, capsys):
        """Test that OBRA decision messages are colored cyan."""
        handler = StreamingHandler()
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='',
            lineno=0,
            msg='[OBRA] Decision: PROCEED',
            args=(),
            exc_info=None
        )

        handler.emit(record)
        captured = capsys.readouterr()

        # Check that output contains the message
        assert '[OBRA]' in captured.out
        assert 'Decision' in captured.out
        # Check that cyan color code is present
        assert colorama.Fore.CYAN in captured.out

    def test_format_obra_to_claude(self):
        """Test formatting helper for OBRA→CLAUDE."""
        result = StreamingHandler.format_obra_to_claude(iteration=1, chars=1234)
        assert '[OBRA→CLAUDE]' in result
        assert 'Iteration 1' in result
        assert '1,234 chars' in result

    def test_format_claude_to_obra(self):
        """Test formatting helper for CLAUDE→OBRA."""
        result = StreamingHandler.format_claude_to_obra(turns=5, chars=5678)
        assert '[CLAUDE→OBRA]' in result
        assert 'Turns: 5' in result
        assert '5,678 chars' in result

    def test_format_qwen_validation(self):
        """Test formatting helper for QWEN validation."""
        result = StreamingHandler.format_qwen_validation(quality=0.76, decision='PROCEED')
        assert '[QWEN]' in result
        assert 'Quality: 0.76' in result
        assert 'PASS' in result
        assert 'Decision: PROCEED' in result

    def test_format_qwen_validation_fail(self):
        """Test formatting helper for QWEN validation (FAIL)."""
        result = StreamingHandler.format_qwen_validation(quality=0.65, decision='RETRY')
        assert '[QWEN]' in result
        assert 'Quality: 0.65' in result
        assert 'FAIL' in result  # < 0.7 threshold
        assert 'Decision: RETRY' in result

    def test_format_separator(self):
        """Test separator formatting."""
        result = StreamingHandler.format_separator()
        assert len(result) == 80
        assert all(c == '─' for c in result)

    def test_emit_handles_exception_gracefully(self, capsys):
        """Test that handler doesn't crash on emit error."""
        handler = StreamingHandler()
        # Create a malformed record
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='',
            lineno=0,
            msg=None,  # None message should be handled
            args=(),
            exc_info=None
        )

        # Should not raise exception
        try:
            handler.emit(record)
        except Exception as e:
            pytest.fail(f"Handler raised exception: {e}")

    def test_long_message_handling(self, capsys):
        """Test that long messages are handled correctly."""
        handler = StreamingHandler()
        long_message = 'A' * 10000  # 10KB message
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='',
            lineno=0,
            msg=f'[OBRA→CLAUDE] {long_message}',
            args=(),
            exc_info=None
        )

        handler.emit(record)
        captured = capsys.readouterr()

        # Check that message is output (may be truncated by terminal)
        assert '[OBRA→CLAUDE]' in captured.out

    def test_color_reset_after_message(self, capsys):
        """Test that color is reset after each message."""
        handler = StreamingHandler()
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='',
            lineno=0,
            msg='[OBRA→CLAUDE] Test',
            args=(),
            exc_info=None
        )

        handler.emit(record)
        captured = capsys.readouterr()

        # Check that color reset code is present
        assert colorama.Style.RESET_ALL in captured.out

    def test_flush_is_used(self):
        """Test that flush=True is used in print (for <100ms latency)."""
        # This is tested implicitly by the implementation
        # We can verify by checking the source code uses flush=True
        import inspect
        source = inspect.getsource(StreamingHandler.emit)
        assert 'flush=True' in source, "StreamingHandler.emit must use flush=True for streaming latency"
