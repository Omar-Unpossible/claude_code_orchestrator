"""Structured logging configuration for Obra.

Provides structured JSON logging for observability and debugging.

Log Events:
- llm_request: LLM API calls (provider, model, latency, success)
- agent_execution: Agent task execution (type, task_id, duration, files)
- nl_command: Natural language commands (intent, operation, success)
- orchestrator_step: Orchestration pipeline steps (step, task_id, duration)

Usage:
    from src.core.logging_config import get_structured_logger

    logger = get_structured_logger(__name__)
    logger.log_llm_request(
        provider='ollama',
        model='qwen2.5-coder:32b',
        latency_ms=1234,
        success=True
    )
"""

import logging
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional
import threading


# Thread-local storage for correlation IDs
_correlation_context = threading.local()


class StructuredLogger:
    """Structured JSON logger for observability."""

    def __init__(self, name: str):
        """Initialize structured logger.

        Args:
            name: Logger name (typically __name__)
        """
        self.name = name
        self.logger = logging.getLogger(name)

        # Set default level
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def _log_structured(self, event: str, level: int, **fields):
        """Log structured event with fields.

        Args:
            event: Event type (e.g., 'llm_request')
            level: Log level (logging.INFO, logging.ERROR, etc.)
            **fields: Event-specific fields
        """
        # Build structured log entry
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'event': event,
            'logger': self.name
        }

        # Add correlation ID if available
        if hasattr(_correlation_context, 'correlation_id'):
            log_entry['correlation_id'] = _correlation_context.correlation_id

        # Add all fields
        log_entry.update(fields)

        # Log as JSON
        self.logger.log(level, json.dumps(log_entry))

    def log_llm_request(
        self,
        provider: str,
        model: str,
        latency_ms: float,
        success: bool,
        error: Optional[str] = None,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
        **extra
    ):
        """Log LLM request.

        Args:
            provider: LLM provider (ollama, openai-codex)
            model: Model name
            latency_ms: Request latency in milliseconds
            success: Whether request succeeded
            error: Error message if failed
            prompt_tokens: Number of prompt tokens (if available)
            completion_tokens: Number of completion tokens (if available)
            **extra: Additional fields
        """
        fields = {
            'provider': provider,
            'model': model,
            'latency_ms': latency_ms,
            'success': success
        }

        if error:
            fields['error'] = error

        if prompt_tokens:
            fields['prompt_tokens'] = prompt_tokens

        if completion_tokens:
            fields['completion_tokens'] = completion_tokens

        fields.update(extra)

        level = logging.INFO if success else logging.ERROR
        self._log_structured('llm_request', level, **fields)

    def log_agent_execution(
        self,
        agent_type: str,
        task_id: int,
        iteration: int,
        duration_s: float,
        success: bool,
        files_modified: Optional[list] = None,
        error: Optional[str] = None,
        **extra
    ):
        """Log agent execution.

        Args:
            agent_type: Agent type (claude-code-local, claude-code-ssh)
            task_id: Task ID being executed
            iteration: Iteration number
            duration_s: Execution duration in seconds
            success: Whether execution succeeded
            files_modified: List of files modified by agent
            error: Error message if failed
            **extra: Additional fields
        """
        fields = {
            'agent_type': agent_type,
            'task_id': task_id,
            'iteration': iteration,
            'duration_s': duration_s,
            'success': success
        }

        if files_modified:
            fields['files_modified'] = files_modified
            fields['file_count'] = len(files_modified)

        if error:
            fields['error'] = error

        fields.update(extra)

        level = logging.INFO if success else logging.ERROR
        self._log_structured('agent_execution', level, **fields)

    def log_nl_command(
        self,
        command: str,
        intent: str,
        operation: Optional[str] = None,
        entity_type: Optional[str] = None,
        success: bool = True,
        latency_ms: Optional[float] = None,
        confidence: Optional[float] = None,
        error: Optional[str] = None,
        **extra
    ):
        """Log natural language command.

        Args:
            command: Raw NL command text
            intent: Intent (COMMAND, QUESTION)
            operation: Operation type (CREATE, UPDATE, DELETE, QUERY)
            entity_type: Entity type (epic, story, task)
            success: Whether command succeeded
            latency_ms: Processing latency in milliseconds
            confidence: Confidence score (0-1)
            error: Error message if failed
            **extra: Additional fields
        """
        fields = {
            'command': command,
            'intent': intent,
            'success': success
        }

        if operation:
            fields['operation'] = operation

        if entity_type:
            fields['entity_type'] = entity_type

        if latency_ms:
            fields['latency_ms'] = latency_ms

        if confidence:
            fields['confidence'] = confidence

        if error:
            fields['error'] = error

        fields.update(extra)

        level = logging.INFO if success else logging.ERROR
        self._log_structured('nl_command', level, **fields)

    def log_orchestrator_step(
        self,
        step: str,
        task_id: int,
        duration_ms: float,
        success: bool,
        iteration: Optional[int] = None,
        quality_score: Optional[float] = None,
        confidence_score: Optional[float] = None,
        error: Optional[str] = None,
        **extra
    ):
        """Log orchestrator pipeline step.

        Args:
            step: Step name (context_build, prompt_gen, agent_exec, validate, etc.)
            task_id: Task ID being orchestrated
            duration_ms: Step duration in milliseconds
            success: Whether step succeeded
            iteration: Iteration number (if applicable)
            quality_score: Quality score (if applicable)
            confidence_score: Confidence score (if applicable)
            error: Error message if failed
            **extra: Additional fields
        """
        fields = {
            'step': step,
            'task_id': task_id,
            'duration_ms': duration_ms,
            'success': success
        }

        if iteration is not None:
            fields['iteration'] = iteration

        if quality_score is not None:
            fields['quality_score'] = quality_score

        if confidence_score is not None:
            fields['confidence_score'] = confidence_score

        if error:
            fields['error'] = error

        fields.update(extra)

        level = logging.INFO if success else logging.ERROR
        self._log_structured('orchestrator_step', level, **fields)

    def info(self, message: str, **fields):
        """Log INFO level message with optional fields."""
        self._log_structured('info', logging.INFO, message=message, **fields)

    def warning(self, message: str, **fields):
        """Log WARNING level message with optional fields."""
        self._log_structured('warning', logging.WARNING, message=message, **fields)

    def error(self, message: str, **fields):
        """Log ERROR level message with optional fields."""
        self._log_structured('error', logging.ERROR, message=message, **fields)

    def debug(self, message: str, **fields):
        """Log DEBUG level message with optional fields."""
        self._log_structured('debug', logging.DEBUG, message=message, **fields)


class CorrelationContext:
    """Context manager for correlation ID tracking.

    Usage:
        with CorrelationContext() as ctx:
            # All logs in this block include correlation_id
            logger.log_llm_request(...)
    """

    def __init__(self, correlation_id: Optional[str] = None):
        """Initialize correlation context.

        Args:
            correlation_id: Correlation ID (generated if not provided)
        """
        import uuid
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.previous_id = None

    def __enter__(self):
        """Enter context - set correlation ID."""
        # Save previous ID (for nested contexts)
        self.previous_id = getattr(_correlation_context, 'correlation_id', None)

        # Set new correlation ID
        _correlation_context.correlation_id = self.correlation_id

        return self

    def __exit__(self, *args):
        """Exit context - restore previous ID."""
        if self.previous_id:
            _correlation_context.correlation_id = self.previous_id
        else:
            # Clear correlation ID
            if hasattr(_correlation_context, 'correlation_id'):
                delattr(_correlation_context, 'correlation_id')


# Global logger cache
_logger_cache: Dict[str, StructuredLogger] = {}


def get_structured_logger(name: str) -> StructuredLogger:
    """Get or create structured logger.

    Args:
        name: Logger name (typically __name__)

    Returns:
        StructuredLogger instance
    """
    if name not in _logger_cache:
        _logger_cache[name] = StructuredLogger(name)

    return _logger_cache[name]


def configure_logging(level: str = 'INFO', format_json: bool = True, log_file: Optional[str] = None):
    """Configure global logging settings.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        format_json: Whether to use JSON formatting (default: True)
        log_file: Optional file path for logging (default: logs/obra.log)
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove existing handlers
    root_logger.handlers = []

    # Console handler
    console_handler = logging.StreamHandler()

    if format_json:
        # JSON formatter (structured logging)
        formatter = logging.Formatter('%(message)s')
    else:
        # Human-readable formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler (for log querying)
    if log_file is None:
        import os
        log_file = 'logs/obra.log'
        os.makedirs('logs', exist_ok=True)

    if log_file:
        import os
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter('%(message)s'))  # Always JSON for file
        root_logger.addHandler(file_handler)


def query_logs(
    event: Optional[str] = None,
    level: Optional[str] = None,
    correlation_id: Optional[str] = None,
    since: Optional[str] = None,
    limit: int = 100,
    log_file: str = 'logs/obra.log'
) -> List[Dict[str, Any]]:
    """Query structured logs with filters.

    Args:
        event: Filter by event type (e.g., 'llm_request', 'nl_command')
        level: Filter by log level (DEBUG, INFO, WARNING, ERROR)
        correlation_id: Filter by correlation ID
        since: Filter by time (e.g., '5m', '1h', '1d', ISO timestamp)
        limit: Maximum number of entries to return
        log_file: Path to log file (default: logs/obra.log)

    Returns:
        List of matching log entries (most recent first)
    """
    import os

    if not os.path.exists(log_file):
        return []

    # Parse since time
    cutoff_time = None
    if since:
        cutoff_time = _parse_since_time(since)

    # Read log file and filter
    matching_entries = []

    try:
        with open(log_file, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())

                    # Apply filters
                    if event and entry.get('event') != event:
                        continue

                    if level and entry.get('level', 'INFO') != level:
                        continue

                    if correlation_id and entry.get('correlation_id') != correlation_id:
                        continue

                    if cutoff_time:
                        entry_time = datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
                        if entry_time < cutoff_time:
                            continue

                    matching_entries.append(entry)

                except (json.JSONDecodeError, KeyError):
                    # Skip malformed entries
                    continue

        # Return most recent first
        matching_entries.reverse()

        return matching_entries[:limit]

    except Exception as e:
        # Return empty list on error
        return []


def _parse_since_time(since: str) -> datetime:
    """Parse 'since' time string into datetime.

    Args:
        since: Time string (e.g., '5m', '1h', '2d', ISO timestamp)

    Returns:
        Datetime object
    """
    from datetime import timedelta

    # Try parsing as ISO timestamp first
    try:
        return datetime.fromisoformat(since.replace('Z', '+00:00'))
    except ValueError:
        pass

    # Parse relative time (e.g., '5m', '1h', '2d')
    import re
    match = re.match(r'^(\d+)([mhd])$', since.lower())
    if match:
        value = int(match.group(1))
        unit = match.group(2)

        if unit == 'm':
            delta = timedelta(minutes=value)
        elif unit == 'h':
            delta = timedelta(hours=value)
        elif unit == 'd':
            delta = timedelta(days=value)
        else:
            delta = timedelta(hours=1)  # Default to 1 hour

        return datetime.utcnow() - delta

    # Default to 1 hour ago
    return datetime.utcnow() - timedelta(hours=1)
