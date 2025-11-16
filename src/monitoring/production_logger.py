"""Production logging for monitoring and analytics."""

import json
import logging
import uuid
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Dict, Optional
from logging.handlers import RotatingFileHandler
from threading import Lock

logger = logging.getLogger(__name__)


class ProductionLogger:
    """Structured JSON Lines logging for production monitoring.

    Logs I/O boundaries and critical metadata while excluding verbose
    in-progress messages. Thread-safe with automatic log rotation.

    Event Types:
        - user_input: User commands and natural language input
        - nl_result: NL parsing results with quality metrics
        - execution_result: Task execution outcomes
        - error: Errors with stage and context
        - orch_prompt: Orchestrator→Implementer prompts (optional)
        - impl_response: Implementer responses (optional)

    Example:
        >>> logger = ProductionLogger(config)
        >>> logger.log_user_input(session_id, "delete all projects")
        >>> logger.log_nl_result(session_id, parsed_intent, duration_ms=1234)
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize production logger from configuration.

        Args:
            config: Configuration dict with keys:
                - path: Log file path (str)
                - events: Dict of event types to enable (bool)
                - privacy: Privacy settings (dict)
                - rotation: Rotation settings (dict)

        Raises:
            ValueError: If config is invalid
            IOError: If log file cannot be created
        """
        self.config = config
        self._lock = Lock()

        # Parse configuration
        log_path = Path(config.get('path', '~/obra-runtime/logs/production.jsonl')).expanduser()
        self.log_path = log_path

        # Event filtering
        events_config = config.get('events', {})
        self.log_user_input_enabled = events_config.get('user_input', True)
        self.log_nl_results_enabled = events_config.get('nl_results', True)
        self.log_exec_results_enabled = events_config.get('execution_results', True)
        self.log_errors_enabled = events_config.get('errors', True)
        self.log_orch_prompts_enabled = events_config.get('orchestrator_prompts', False)
        self.log_impl_responses_enabled = events_config.get('implementer_responses', False)

        # Privacy settings
        privacy_config = config.get('privacy', {})
        self.redact_pii = privacy_config.get('redact_pii', True)
        self.redact_secrets = privacy_config.get('redact_secrets', True)

        # Rotation settings
        rotation_config = config.get('rotation', {})
        max_bytes = rotation_config.get('max_file_size_mb', 100) * 1024 * 1024
        backup_count = rotation_config.get('max_files', 10)

        # Create log directory
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # Setup rotating file handler
        self.logger = logging.getLogger('obra.production')
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False  # Don't propagate to root logger

        # Remove existing handlers
        self.logger.handlers.clear()

        # Add rotating file handler
        handler = RotatingFileHandler(
            str(log_path),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        handler.setFormatter(logging.Formatter('%(message)s'))  # JSON only, no prefix
        self.logger.addHandler(handler)

        logger.info(f"ProductionLogger initialized: path={log_path}, rotation={max_bytes}B/{backup_count} files")

    def _log_event(self, event_type: str, session_id: str, **kwargs) -> None:
        """Internal method to log structured event.

        Args:
            event_type: Type of event (user_input, nl_result, etc.)
            session_id: Session UUID
            **kwargs: Event-specific data
        """
        with self._lock:
            event = {
                "type": event_type,
                "ts": datetime.now(UTC).isoformat(),
                "session": session_id,
                **kwargs
            }

            # Redact if enabled
            if self.redact_pii or self.redact_secrets:
                event = self._redact_sensitive_data(event)

            # Log as single JSON line
            try:
                self.logger.info(json.dumps(event, default=str))
            except Exception as e:
                logger.error(f"Failed to log event: {e}", exc_info=True)

    def _redact_sensitive_data(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Redact PII and secrets from event.

        Args:
            event: Event dict to redact

        Returns:
            Redacted event dict
        """
        import re

        # Patterns to redact
        patterns = []

        if self.redact_pii:
            patterns.extend([
                (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]'),  # Email
                (r'\b(?:\d{1,3}\.){3}\d{1,3}\b', '[IP]'),  # IPv4
                (r'\b\d{3}-\d{2}-\d{4}\b', '[SSN]'),  # SSN
                (r'\b\d{3}-\d{3}-\d{4}\b', '[PHONE]'),  # Phone
            ])

        if self.redact_secrets:
            patterns.extend([
                # Specific API key patterns (order matters - more specific first)
                (r'sk-[A-Za-z0-9]{32,}', '[API_KEY]'),  # OpenAI-style
                (r'ghp_[A-Za-z0-9]{36}', '[GH_TOKEN]'),  # GitHub token
                # Generic token (but exclude UUIDs with 4 hyphens)
                # This pattern matches long alphanumeric strings but NOT UUID format
                (r'\b[A-Za-z0-9_]{40,}\b', '[TOKEN]'),  # Very long tokens without hyphens
            ])

        # Redact in string fields
        def redact_string(s: str) -> str:
            for pattern, replacement in patterns:
                s = re.sub(pattern, replacement, s)
            return s

        # Recursively redact
        def redact_dict(d: Dict) -> Dict:
            result = {}
            for key, value in d.items():
                if isinstance(value, str):
                    result[key] = redact_string(value)
                elif isinstance(value, dict):
                    result[key] = redact_dict(value)
                elif isinstance(value, list):
                    result[key] = [redact_string(v) if isinstance(v, str) else v for v in value]
                else:
                    result[key] = value
            return result

        return redact_dict(event)

    def log_user_input(self, session_id: str, input_text: str) -> None:
        """Log user input event.

        Args:
            session_id: Session UUID
            input_text: User's input text (command or NL)

        Example:
            >>> logger.log_user_input(session_id, "delete all projects")
        """
        if not self.log_user_input_enabled:
            return

        self._log_event("user_input", session_id, input=input_text)

    def log_nl_result(
        self,
        session_id: str,
        parsed_intent: Any,  # ParsedIntent type
        duration_ms: int
    ) -> None:
        """Log NL processing result with quality metrics.

        Args:
            session_id: Session UUID
            parsed_intent: ParsedIntent object from NL pipeline
            duration_ms: Processing duration in milliseconds

        Example:
            >>> logger.log_nl_result(session_id, parsed_intent, duration_ms=1234)
        """
        if not self.log_nl_results_enabled:
            return

        # Extract data from ParsedIntent
        intent_type = str(parsed_intent.intent_type) if hasattr(parsed_intent, 'intent_type') else 'UNKNOWN'
        confidence = float(parsed_intent.confidence) if hasattr(parsed_intent, 'confidence') else 0.0

        # Extract operation context if available
        operation = None
        entity = None
        identifier = None
        validation = "unknown"

        if hasattr(parsed_intent, 'operation_context') and parsed_intent.operation_context:
            ctx = parsed_intent.operation_context
            operation = str(ctx.operation) if hasattr(ctx, 'operation') else None
            entity = str(ctx.entity_type) if hasattr(ctx, 'entity_type') else None
            identifier = str(ctx.identifier) if hasattr(ctx, 'identifier') else None

        # Check validation status
        if hasattr(parsed_intent, 'metadata'):
            validation = "failed" if parsed_intent.metadata.get('validation_failed') else "passed"

        self._log_event(
            "nl_result",
            session_id,
            intent=intent_type,
            confidence=confidence,
            operation=operation,
            entity=entity,
            identifier=identifier,
            validation=validation,
            duration_ms=duration_ms
        )

    def log_execution_result(
        self,
        session_id: str,
        result: Dict[str, Any],
        duration_ms: int
    ) -> None:
        """Log execution result.

        Args:
            session_id: Session UUID
            result: Execution result dict from orchestrator
            duration_ms: Execution duration in milliseconds

        Example:
            >>> logger.log_execution_result(session_id, result, duration_ms=9800)
        """
        if not self.log_exec_results_enabled:
            return

        self._log_event(
            "execution_result",
            session_id,
            success=result.get('success', False),
            message=result.get('message', ''),
            entities_affected=result.get('bulk_results') or result.get('data'),
            total_duration_ms=duration_ms
        )

    def log_error(
        self,
        session_id: str,
        stage: str,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log error event with context.

        Args:
            session_id: Session UUID
            stage: Stage where error occurred (e.g., 'nl_processing', 'validation')
            error: Exception object
            context: Optional additional context

        Example:
            >>> logger.log_error(session_id, "validation", exc, {"task_id": 7})
        """
        if not self.log_errors_enabled:
            return

        error_data = {
            "stage": stage,
            "error_type": type(error).__name__,
            "error": str(error),
            "recoverable": not isinstance(error, (SystemExit, KeyboardInterrupt))
        }

        if context:
            error_data["context"] = context

        self._log_event("error", session_id, **error_data)

    def log_orch_prompt(
        self,
        session_id: str,
        task_id: int,
        target: str,
        prompt_length: int,
        context_tokens: int
    ) -> None:
        """Log orchestrator prompt to implementer (optional).

        Args:
            session_id: Session UUID
            task_id: Task ID
            target: Target implementer (e.g., 'claude-code')
            prompt_length: Length of prompt in characters
            context_tokens: Number of context tokens

        Example:
            >>> logger.log_orch_prompt(session_id, 7, "claude-code", 1500, 5000)
        """
        if not self.log_orch_prompts_enabled:
            return

        self._log_event(
            "orch_prompt",
            session_id,
            task_id=task_id,
            target=target,
            prompt_length=prompt_length,
            context_tokens=context_tokens
        )

    def log_impl_response(
        self,
        session_id: str,
        task_id: int,
        success: bool,
        duration_ms: int,
        output_length: int
    ) -> None:
        """Log implementer response (optional).

        Args:
            session_id: Session UUID
            task_id: Task ID
            success: Whether implementation succeeded
            duration_ms: Implementation duration in milliseconds
            output_length: Length of output in characters

        Example:
            >>> logger.log_impl_response(session_id, 7, True, 8500, 2300)
        """
        if not self.log_impl_responses_enabled:
            return

        self._log_event(
            "impl_response",
            session_id,
            task_id=task_id,
            success=success,
            duration_ms=duration_ms,
            output_length=output_length
        )

    def close(self) -> None:
        """Flush and close logger."""
        with self._lock:
            for handler in self.logger.handlers:
                handler.flush()
                handler.close()
            logger.info("ProductionLogger closed")


def generate_session_id() -> str:
    """Generate unique session ID.

    Returns:
        UUID4 string

    Example:
        >>> session_id = generate_session_id()
        >>> print(session_id)
        'a1b2c3d4-e5f6-...'
    """
    return str(uuid.uuid4())


# ============================================================================
# Global ProductionLogger Pattern (Issue #3 - v1.8.1)
# ============================================================================

_production_logger_instance: Optional[ProductionLogger] = None


def get_production_logger() -> Optional[ProductionLogger]:
    """Get the global production logger instance.

    Returns:
        ProductionLogger instance or None if not initialized

    Example:
        >>> logger = get_production_logger()
        >>> if logger:
        ...     logger.log_user_input(session_id, "delete project 5")
    """
    global _production_logger_instance
    return _production_logger_instance


def initialize_production_logger(config: Dict[str, Any]) -> Optional[ProductionLogger]:
    """Initialize the global production logger from configuration.

    This function should be called once at application startup (CLI or interactive mode).
    Subsequent calls will return the existing instance without re-initialization.

    Args:
        config: Configuration dict with monitoring.production_logging section

    Returns:
        ProductionLogger instance or None if disabled in config

    Example:
        >>> config = Config.load()
        >>> logger = initialize_production_logger(config.config)
        >>> logger.log_user_input(session_id, "create project Foo")
    """
    global _production_logger_instance

    # Check if already initialized
    if _production_logger_instance is not None:
        logger.debug("ProductionLogger already initialized, returning existing instance")
        return _production_logger_instance

    # Check if enabled in config
    enabled = config.get('monitoring', {}).get('production_logging', {}).get('enabled', True)

    if not enabled:
        logger.info("Production logging disabled in config")
        _production_logger_instance = None
        return None

    # Extract production logging config
    prod_logging_config = config.get('monitoring', {}).get('production_logging', {})

    try:
        _production_logger_instance = ProductionLogger(prod_logging_config)
        logger.info("ProductionLogger initialized globally")
        return _production_logger_instance

    except Exception as e:
        logger.error(f"Failed to initialize ProductionLogger: {e}", exc_info=True)
        _production_logger_instance = None
        return None
