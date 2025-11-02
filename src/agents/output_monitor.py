"""Real-time output monitoring for Claude Code agent with event detection.

This module provides comprehensive monitoring of agent output including:
- Completion detection with multiple heuristics
- Error detection and extraction
- Rate limit detection
- Circular buffer management
- Event notification via observer pattern
- Thread-safe operations

The OutputMonitor uses pattern matching and timing heuristics to determine
when agent responses are complete, detect errors, and identify rate limiting.
"""

import re
import time
import logging
import threading
from collections import deque
from typing import List, Optional, Callable, Any, Dict
from pathlib import Path

from src.core.exceptions import (
    MonitoringException,
    EventDetectionException
)

logger = logging.getLogger(__name__)


class OutputMonitor:
    """Real-time monitor for agent output with completion and event detection.

    Monitors streaming output from Claude Code agent to detect:
    - Response completion
    - Errors and exceptions
    - Rate limiting
    - Other significant events

    Features:
    - Circular buffer for output history
    - Pattern-based event detection
    - Observer pattern for event notification
    - Thread-safe operations
    - Optional output logging to file

    Attributes:
        buffer_size: Maximum lines to keep in buffer
        completion_timeout: Seconds of inactivity after marker to confirm completion
        output_file: Optional path to log output
        is_monitoring: Whether monitoring is currently active

    Example:
        >>> monitor = OutputMonitor()
        >>> monitor.register_observer(lambda event: print(event))
        >>> monitor.start_monitoring(output_stream)
        >>> while not monitor.is_complete():
        ...     time.sleep(0.1)
        >>> response = monitor.get_response()
        >>> monitor.stop_monitoring()
    """

    # Detection patterns (class constants for easy configuration)
    COMPLETION_MARKERS = [
        "Ready for",
        ">>>",
        "Command completed",
        "Finished",
        "Done",
        "✓",  # Success marker
    ]

    ERROR_MARKERS = [
        "Error:",
        "Exception:",
        "Traceback:",
        "FAILED",
        "AssertionError",
        "✗",  # Error marker
        "ERROR",
    ]

    RATE_LIMIT_MARKERS = [
        "rate limit",
        "too many requests",
        "try again",
        "quota exceeded",
        "retry after",
    ]

    # Buffer and timing configuration
    DEFAULT_BUFFER_SIZE = 10000
    DEFAULT_COMPLETION_TIMEOUT = 2.0  # Seconds of inactivity after marker

    def __init__(
        self,
        buffer_size: int = DEFAULT_BUFFER_SIZE,
        completion_timeout: float = DEFAULT_COMPLETION_TIMEOUT,
        output_file: Optional[Path] = None,
        completion_markers: Optional[List[str]] = None,
        error_markers: Optional[List[str]] = None,
        rate_limit_markers: Optional[List[str]] = None
    ):
        """Initialize output monitor.

        Args:
            buffer_size: Maximum lines in circular buffer (default: 10000)
            completion_timeout: Seconds of inactivity to confirm completion (default: 2.0)
            output_file: Optional file path to log all output
            completion_markers: Optional custom completion patterns
            error_markers: Optional custom error patterns
            rate_limit_markers: Optional custom rate limit patterns
        """
        self.buffer_size = buffer_size
        self.completion_timeout = completion_timeout
        self.output_file = output_file

        # Pattern lists (allow customization)
        self.completion_markers = completion_markers or self.COMPLETION_MARKERS
        self.error_markers = error_markers or self.ERROR_MARKERS
        self.rate_limit_markers = rate_limit_markers or self.RATE_LIMIT_MARKERS

        # Compile regex patterns for performance
        self._completion_regex = re.compile(
            '|'.join(re.escape(m) for m in self.completion_markers),
            re.IGNORECASE
        )
        self._error_regex = re.compile(
            '|'.join(re.escape(m) for m in self.error_markers),
            re.IGNORECASE
        )
        self._rate_limit_regex = re.compile(
            '|'.join(re.escape(m) for m in self.rate_limit_markers),
            re.IGNORECASE
        )

        # Buffer and state
        self._buffer: deque = deque(maxlen=buffer_size)
        self._lock = threading.RLock()
        self._observers: List[Callable[[Dict[str, Any]], None]] = []
        self._completion_event = threading.Event()
        self._monitoring_thread: Optional[threading.Thread] = None
        self._stop_monitoring_flag = threading.Event()

        # Tracking
        self._last_output_time: float = 0.0
        self._completion_marker_found: bool = False
        self._detected_error: Optional[str] = None
        self._detected_rate_limit: bool = False
        self.is_monitoring: bool = False

        # Output file handle
        self._output_file_handle: Optional[Any] = None

        logger.debug(
            f"OutputMonitor initialized: buffer_size={buffer_size}, "
            f"completion_timeout={completion_timeout}s"
        )

    def start_monitoring(self, output_stream: Any) -> None:
        """Begin monitoring an output stream.

        Starts a background thread that reads from the stream and processes
        output lines for event detection.

        Args:
            output_stream: Stream object with readline() method (like file or channel)

        Raises:
            MonitoringException: If monitoring already active or stream invalid
        """
        with self._lock:
            if self.is_monitoring:
                raise MonitoringException(
                    "Monitoring already active",
                    context={'is_monitoring': True},
                    recovery="Stop current monitoring before starting new session"
                )

            if not hasattr(output_stream, 'readline'):
                raise MonitoringException(
                    "Invalid output stream",
                    context={'stream_type': type(output_stream).__name__},
                    recovery="Stream must have readline() method"
                )

            # Reset state
            self._buffer.clear()
            self._completion_event.clear()
            self._stop_monitoring_flag.clear()
            self._completion_marker_found = False
            self._detected_error = None
            self._detected_rate_limit = False
            self._last_output_time = time.time()

            # Open output file if specified
            if self.output_file:
                try:
                    self._output_file_handle = open(self.output_file, 'a', encoding='utf-8')
                    logger.debug(f"Logging output to {self.output_file}")
                except Exception as e:
                    logger.warning(f"Could not open output file: {e}")
                    self._output_file_handle = None

            # Start monitoring thread
            self._monitoring_thread = threading.Thread(
                target=self._monitor_loop,
                args=(output_stream,),
                daemon=True,
                name="OutputMonitor"
            )
            self._monitoring_thread.start()
            self.is_monitoring = True

            logger.info("Output monitoring started")

    def stop_monitoring(self) -> None:
        """Stop monitoring and clean up resources.

        Gracefully stops the monitoring thread and closes output file if open.
        This method does not raise exceptions.
        """
        with self._lock:
            if not self.is_monitoring:
                logger.debug("Monitoring not active, nothing to stop")
                return

            logger.info("Stopping output monitoring")

            # Signal thread to stop
            self._stop_monitoring_flag.set()

            # Wait for thread to finish (with timeout)
            if self._monitoring_thread and self._monitoring_thread.is_alive():
                self._monitoring_thread.join(timeout=5.0)
                if self._monitoring_thread.is_alive():
                    logger.warning("Monitoring thread did not stop cleanly")

            # Close output file
            if self._output_file_handle:
                try:
                    self._output_file_handle.close()
                except Exception as e:
                    logger.warning(f"Error closing output file: {e}")
                finally:
                    self._output_file_handle = None

            self.is_monitoring = False
            logger.info("Output monitoring stopped")

    def is_complete(self) -> bool:
        """Check if output indicates completion.

        Uses multiple heuristics:
        1. Completion marker found in output
        2. No new output for completion_timeout seconds after marker
        3. Completion event has been set

        Returns:
            True if output appears complete, False otherwise
        """
        with self._lock:
            # Simple check: completion event set
            if self._completion_event.is_set():
                return True

            # Heuristic: marker found and timeout elapsed
            if self._completion_marker_found:
                idle_time = time.time() - self._last_output_time
                if idle_time >= self.completion_timeout:
                    # Set completion event
                    self._completion_event.set()
                    self._notify_observers({
                        'type': 'completion',
                        'timestamp': time.time(),
                        'idle_seconds': idle_time
                    })
                    return True

            return False

    def get_response(self) -> str:
        """Get the full response from buffer.

        Returns:
            Complete response as single string with newlines
        """
        with self._lock:
            response = '\n'.join(self._buffer)
            logger.debug(f"Retrieved response ({len(response)} chars)")
            return response

    def detect_error(self) -> Optional[str]:
        """Detect and extract error messages from output.

        Returns:
            Error message if detected, None otherwise
        """
        with self._lock:
            return self._detected_error

    def detect_rate_limit(self) -> bool:
        """Detect if rate limiting occurred.

        Returns:
            True if rate limit detected, False otherwise
        """
        with self._lock:
            return self._detected_rate_limit

    def get_buffer(self, lines: int = 100) -> List[str]:
        """Get recent buffer lines.

        Args:
            lines: Number of recent lines to retrieve (default: 100)

        Returns:
            List of recent output lines (newest last)
        """
        with self._lock:
            buffer_list = list(self._buffer)
            # Return last N lines
            return buffer_list[-lines:] if lines < len(buffer_list) else buffer_list

    def register_observer(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Register event observer callback.

        The callback will be invoked with event dictionaries containing:
        - type: Event type ('completion', 'error', 'rate_limit', 'output_line')
        - timestamp: Event timestamp
        - Additional fields depending on event type

        Args:
            callback: Callable that accepts event dictionary

        Example:
            >>> def my_handler(event):
            ...     print(f"Event: {event['type']}")
            >>> monitor.register_observer(my_handler)
        """
        with self._lock:
            self._observers.append(callback)
            logger.debug(f"Registered observer (total: {len(self._observers)})")

    def clear_buffer(self) -> None:
        """Clear the output buffer.

        Removes all buffered output. Use with caution during active monitoring.
        """
        with self._lock:
            self._buffer.clear()
            logger.debug("Buffer cleared")

    # Private methods

    def _monitor_loop(self, output_stream: Any) -> None:
        """Main monitoring loop (runs in background thread).

        Args:
            output_stream: Stream to read from
        """
        logger.debug("Monitoring loop started")

        try:
            while not self._stop_monitoring_flag.is_set():
                try:
                    # Read line from stream (with timeout handling)
                    line = self._read_line_with_timeout(output_stream, timeout=0.5)

                    if line is None:
                        # No data available, check for completion timeout
                        if self._check_completion_timeout():
                            break
                        continue

                    # Process the line
                    self._process_line(line)

                except Exception as e:
                    logger.error(f"Error in monitoring loop: {e}", exc_info=True)
                    self._notify_observers({
                        'type': 'monitor_error',
                        'timestamp': time.time(),
                        'error': str(e)
                    })
                    # Continue monitoring despite error
                    time.sleep(0.1)

        except Exception as e:
            logger.error(f"Fatal error in monitoring loop: {e}", exc_info=True)
        finally:
            logger.debug("Monitoring loop exiting")

    def _read_line_with_timeout(self, stream: Any, timeout: float) -> Optional[str]:
        """Read a line from stream with timeout.

        Args:
            stream: Stream to read from
            timeout: Timeout in seconds

        Returns:
            Line as string, or None if no data available
        """
        # This is a simple implementation - in production you might use
        # select.select() or stream-specific non-blocking mechanisms
        try:
            # For paramiko channel, use recv_ready()
            if hasattr(stream, 'recv_ready'):
                if stream.recv_ready():
                    chunk = stream.recv(4096).decode('utf-8', errors='ignore')
                    # Split into lines and process
                    lines = chunk.split('\n')
                    for line in lines[:-1]:  # All but last (may be incomplete)
                        if line:
                            return line
                    # Return last line if it's complete
                    if lines[-1]:
                        return lines[-1]
                return None

            # For file-like objects with readline
            elif hasattr(stream, 'readline'):
                # Note: readline() blocks, so this isn't ideal
                # In production, use non-blocking I/O
                line = stream.readline()
                if line:
                    return line.rstrip('\n')
                return None

            else:
                logger.warning(f"Unsupported stream type: {type(stream)}")
                return None

        except Exception as e:
            logger.debug(f"Error reading from stream: {e}")
            return None

    def _process_line(self, line: str) -> None:
        """Process a single output line.

        Adds to buffer, detects patterns, notifies observers.

        Args:
            line: Output line to process
        """
        with self._lock:
            # Add to buffer
            self._buffer.append(line)
            self._last_output_time = time.time()

            # Write to output file if configured
            if self._output_file_handle:
                try:
                    self._output_file_handle.write(line + '\n')
                    self._output_file_handle.flush()
                except Exception as e:
                    logger.warning(f"Error writing to output file: {e}")

            # Detect completion marker
            if self._completion_regex.search(line):
                if not self._completion_marker_found:
                    self._completion_marker_found = True
                    logger.info(f"Completion marker detected: {line[:100]}")
                    self._notify_observers({
                        'type': 'completion_marker',
                        'timestamp': time.time(),
                        'line': line
                    })

            # Detect error
            if self._error_regex.search(line):
                error_msg = self._extract_error(line)
                if not self._detected_error:
                    self._detected_error = error_msg
                    logger.warning(f"Error detected: {error_msg}")
                    self._notify_observers({
                        'type': 'error',
                        'timestamp': time.time(),
                        'error': error_msg,
                        'line': line
                    })

            # Detect rate limit
            if self._rate_limit_regex.search(line):
                if not self._detected_rate_limit:
                    self._detected_rate_limit = True
                    logger.warning(f"Rate limit detected: {line[:100]}")
                    self._notify_observers({
                        'type': 'rate_limit',
                        'timestamp': time.time(),
                        'line': line
                    })

            # Notify observers of new output
            self._notify_observers({
                'type': 'output_line',
                'timestamp': time.time(),
                'line': line
            })

    def _check_completion_timeout(self) -> bool:
        """Check if completion timeout has elapsed.

        Returns:
            True if completion confirmed by timeout, False otherwise
        """
        with self._lock:
            if self._completion_marker_found:
                idle_time = time.time() - self._last_output_time
                if idle_time >= self.completion_timeout:
                    if not self._completion_event.is_set():
                        logger.info(
                            f"Completion confirmed by timeout ({idle_time:.1f}s idle)"
                        )
                        self._completion_event.set()
                        self._notify_observers({
                            'type': 'completion',
                            'timestamp': time.time(),
                            'idle_seconds': idle_time
                        })
                    return True
            return False

    def _extract_error(self, line: str) -> str:
        """Extract error message from line.

        Args:
            line: Line containing error marker

        Returns:
            Extracted error message
        """
        # Try to extract meaningful error message
        # This is basic extraction - could be enhanced with more sophisticated parsing

        # Find error marker
        match = self._error_regex.search(line)
        if match:
            # Return from marker to end of line
            start_pos = match.start()
            error_msg = line[start_pos:].strip()
            return error_msg

        return line.strip()

    def _notify_observers(self, event: Dict[str, Any]) -> None:
        """Notify all registered observers of an event.

        Args:
            event: Event dictionary to send to observers
        """
        # Note: observers are called with lock held
        # Keep observer callbacks fast to avoid blocking
        for observer in self._observers:
            try:
                observer(event)
            except Exception as e:
                logger.error(
                    f"Error in observer callback: {e}",
                    exc_info=True
                )

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - clean up monitoring."""
        self.stop_monitoring()
        return False

    def get_stats(self) -> Dict[str, Any]:
        """Get monitoring statistics.

        Returns:
            Dictionary with monitoring stats
        """
        with self._lock:
            return {
                'is_monitoring': self.is_monitoring,
                'buffer_lines': len(self._buffer),
                'buffer_capacity': self.buffer_size,
                'completion_detected': self._completion_event.is_set(),
                'completion_marker_found': self._completion_marker_found,
                'error_detected': self._detected_error is not None,
                'rate_limit_detected': self._detected_rate_limit,
                'last_output_time': self._last_output_time,
                'idle_seconds': time.time() - self._last_output_time if self._last_output_time > 0 else 0,
                'observers_count': len(self._observers)
            }

    def wait_for_completion(self, timeout: Optional[float] = None) -> bool:
        """Wait for completion event with optional timeout.

        Args:
            timeout: Maximum seconds to wait, or None for indefinite

        Returns:
            True if completion detected, False if timeout exceeded
        """
        return self._completion_event.wait(timeout)
