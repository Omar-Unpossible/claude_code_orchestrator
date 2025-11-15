# Production Monitoring - Machine Implementation Guide

**Target:** Claude Code CLI
**Format:** Step-by-step implementation instructions
**Version:** 1.0
**Estimated Time:** 8-10 hours

---

## PHASE 1: Core Infrastructure

### STEP 1.1: Create monitoring module structure

**ACTION:** Create directory and init file

```bash
mkdir -p src/monitoring
touch src/monitoring/__init__.py
```

**FILE:** `src/monitoring/__init__.py`
```python
"""Production monitoring and logging."""

from src.monitoring.production_logger import ProductionLogger

__all__ = ['ProductionLogger']
```

**VERIFY:**
```bash
ls -la src/monitoring/
# Expected: __init__.py exists
```

---

### STEP 1.2: Implement ProductionLogger class

**FILE:** `src/monitoring/production_logger.py`

**COMPLETE IMPLEMENTATION:**

```python
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
                (r'\b[A-Za-z0-9_-]{20,}\b', '[TOKEN]'),  # Generic token
                (r'sk-[A-Za-z0-9]{32,}', '[API_KEY]'),  # OpenAI-style
                (r'ghp_[A-Za-z0-9]{36}', '[GH_TOKEN]'),  # GitHub token
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
```

**VERIFY:**
```bash
python3 -c "from src.monitoring.production_logger import ProductionLogger; print('OK')"
# Expected: OK
```

---

### STEP 1.3: Add configuration schema

**FILE:** `config/config.yaml`

**ACTION:** Add this section at the end of the file (after existing sections)

```yaml
# Production Monitoring (v1.8.0)
monitoring:
  production_logging:
    # Master enable/disable
    enabled: false  # Disabled by default for backward compatibility

    # Log file location
    path: "~/obra-runtime/logs/production.jsonl"

    # What to log
    events:
      user_input: true
      nl_results: true
      execution_results: true
      errors: true
      orchestrator_prompts: false    # Verbose, disabled by default
      implementer_responses: false   # Verbose, disabled by default

    # Privacy settings
    privacy:
      redact_pii: true               # Email, IP, phone, SSN
      redact_secrets: true           # API keys, tokens
      redact_patterns: []            # Custom regex patterns (future)

    # Log rotation
    rotation:
      max_file_size_mb: 100          # Rotate at 100MB
      max_files: 10                  # Keep 10 files (1GB total)

    # Performance (future)
    async_logging: false             # Sync by default
    buffer_size: 1024                # Flush every 1KB
```

**VERIFY:**
```bash
python3 -c "from src.core.config import Config; c = Config.load(); print('enabled:', c.config.get('monitoring', {}).get('production_logging', {}).get('enabled', 'NOT_FOUND'))"
# Expected: enabled: False
```

---

## PHASE 2: Interactive REPL Integration

### STEP 2.1: Add ProductionLogger to InteractiveMode

**FILE:** `src/interactive.py`

**ACTION 1:** Add import at top of file (around line 10-20)

```python
from src.monitoring.production_logger import ProductionLogger, generate_session_id
```

**ACTION 2:** Modify `__init__` method (around line 60-100)

**FIND:**
```python
    def __init__(self, orchestrator, config):
        """Initialize interactive mode.

        Args:
            orchestrator: Orchestrator instance
            config: Configuration object
        """
        self.orchestrator = orchestrator
        self.config = config
        self.current_project = None
```

**REPLACE WITH:**
```python
    def __init__(self, orchestrator, config):
        """Initialize interactive mode.

        Args:
            orchestrator: Orchestrator instance
            config: Configuration object
        """
        self.orchestrator = orchestrator
        self.config = config
        self.current_project = None

        # Production logging (v1.8.0)
        self.session_id = generate_session_id()
        monitoring_config = config.config.get('monitoring', {}).get('production_logging', {})

        if monitoring_config.get('enabled', False):
            try:
                self.prod_logger = ProductionLogger(monitoring_config)
                logger.info(f"Production logging enabled: session={self.session_id}")
            except Exception as e:
                logger.error(f"Failed to initialize ProductionLogger: {e}", exc_info=True)
                self.prod_logger = None
        else:
            self.prod_logger = None
```

**VERIFY:**
```bash
grep -n "self.prod_logger" src/interactive.py
# Expected: Should find the initialization code
```

---

### STEP 2.2: Log user input in natural language handler

**FILE:** `src/interactive.py`

**ACTION:** Modify `_handle_natural_language` method (around line 710-760)

**FIND:**
```python
    def _handle_natural_language(self, message: str):
        """Handle natural language input from user.

        Args:
            message: Natural language message from user
        """
        try:
```

**INSERT AFTER THE `try:` LINE:**
```python
            # Log user input (production monitoring)
            if self.prod_logger:
                self.prod_logger.log_user_input(self.session_id, message)

            start_time = time.time()  # Track total duration
```

**ALSO ADD IMPORT at top of file:**
```python
import time
```

**VERIFY:**
```bash
grep -A 3 "def _handle_natural_language" src/interactive.py | grep "log_user_input"
# Expected: Should find the log_user_input call
```

---

### STEP 2.3: Log NL processing results

**FILE:** `src/interactive.py`

**ACTION:** Modify in `_handle_natural_language` method

**FIND:**
```python
                parsed_intent = self.nl_processor.process(message, context=context)
```

**REPLACE WITH:**
```python
                nl_start = time.time()
                parsed_intent = self.nl_processor.process(message, context=context)
                nl_duration_ms = int((time.time() - nl_start) * 1000)

                # Log NL processing result (production monitoring)
                if self.prod_logger:
                    self.prod_logger.log_nl_result(self.session_id, parsed_intent, nl_duration_ms)
```

**VERIFY:**
```bash
grep -A 2 "nl_processor.process" src/interactive.py | grep "log_nl_result"
# Expected: Should find the log_nl_result call
```

---

### STEP 2.4: Log execution results

**FILE:** `src/interactive.py`

**ACTION:** Modify after `execute_nl_command` call (around line 750-755)

**FIND:**
```python
                    try:
                        result = self.orchestrator.execute_nl_command(
                            parsed_intent,
                            project_id=self.current_project,
                            interactive=True
                        )

                        # Display result message
                        if result.get('success'):
```

**REPLACE WITH:**
```python
                    try:
                        exec_start = time.time()
                        result = self.orchestrator.execute_nl_command(
                            parsed_intent,
                            project_id=self.current_project,
                            interactive=True
                        )
                        exec_duration_ms = int((time.time() - exec_start) * 1000)

                        # Log execution result (production monitoring)
                        if self.prod_logger:
                            self.prod_logger.log_execution_result(
                                self.session_id, result, exec_duration_ms
                            )

                        # Display result message
                        if result.get('success'):
```

**VERIFY:**
```bash
grep -A 5 "execute_nl_command" src/interactive.py | grep "log_execution_result"
# Expected: Should find the log_execution_result call
```

---

### STEP 2.5: Log errors

**FILE:** `src/interactive.py`

**ACTION:** Modify exception handling in `_handle_natural_language`

**FIND:**
```python
        except Exception as e:
            logger.exception(f"Natural language processing failed: {e}")
            print(f"\n✗ Error: {str(e)}\n")
```

**REPLACE WITH:**
```python
        except Exception as e:
            # Log error (production monitoring)
            if self.prod_logger:
                self.prod_logger.log_error(
                    self.session_id,
                    stage="nl_processing",
                    error=e,
                    context={"message": message[:100]}  # First 100 chars
                )

            logger.exception(f"Natural language processing failed: {e}")
            print(f"\n✗ Error: {str(e)}\n")
```

**ALSO FIND** (execution error handling, around line 765-770):
```python
                    except Exception as e:
                        logger.exception(f"NL command execution failed: {e}")
                        print(f"\n✗ Execution failed: {str(e)}\n")
```

**REPLACE WITH:**
```python
                    except Exception as e:
                        # Log error (production monitoring)
                        if self.prod_logger:
                            self.prod_logger.log_error(
                                self.session_id,
                                stage="execution",
                                error=e,
                                context={"project_id": self.current_project}
                            )

                        logger.exception(f"NL command execution failed: {e}")
                        print(f"\n✗ Execution failed: {str(e)}\n")
```

**VERIFY:**
```bash
grep -c "log_error" src/interactive.py
# Expected: Should find 2 occurrences
```

---

### STEP 2.6: Add cleanup on shutdown

**FILE:** `src/interactive.py`

**ACTION:** Modify `run` method cleanup (around line 200-220)

**FIND:**
```python
        finally:
            logger.info("Interactive mode ended")
```

**REPLACE WITH:**
```python
        finally:
            # Close production logger
            if self.prod_logger:
                try:
                    self.prod_logger.close()
                except Exception as e:
                    logger.error(f"Failed to close ProductionLogger: {e}")

            logger.info("Interactive mode ended")
```

**VERIFY:**
```bash
grep -A 3 "finally:" src/interactive.py | grep "close()"
# Expected: Should find prod_logger.close()
```

---

## PHASE 3: Testing

### STEP 3.1: Create unit tests

**FILE:** `tests/monitoring/test_production_logger.py`

**ACTION:** Create directory and test file

```bash
mkdir -p tests/monitoring
touch tests/monitoring/__init__.py
```

**COMPLETE TEST FILE:**

```python
"""Unit tests for ProductionLogger."""

import json
import pytest
import tempfile
import uuid
from pathlib import Path
from datetime import datetime

from src.monitoring.production_logger import ProductionLogger, generate_session_id


@pytest.fixture
def temp_log_dir(tmp_path):
    """Temporary log directory."""
    return tmp_path / "logs"


@pytest.fixture
def test_config(temp_log_dir):
    """Test configuration."""
    return {
        'path': str(temp_log_dir / "production.jsonl"),
        'events': {
            'user_input': True,
            'nl_results': True,
            'execution_results': True,
            'errors': True,
        },
        'privacy': {
            'redact_pii': True,
            'redact_secrets': True,
        },
        'rotation': {
            'max_file_size_mb': 1,  # Small for testing
            'max_files': 2,
        }
    }


@pytest.fixture
def logger(test_config):
    """ProductionLogger instance."""
    logger = ProductionLogger(test_config)
    yield logger
    logger.close()


def test_initialization(test_config, temp_log_dir):
    """Test logger initialization."""
    logger = ProductionLogger(test_config)
    assert logger is not None
    assert logger.log_path.parent == temp_log_dir
    logger.close()


def test_generate_session_id():
    """Test session ID generation."""
    session_id = generate_session_id()
    assert isinstance(session_id, str)
    assert len(session_id) == 36  # UUID4 format

    # Verify it's a valid UUID
    parsed = uuid.UUID(session_id)
    assert str(parsed) == session_id


def test_log_user_input(logger, test_config):
    """Test logging user input."""
    session_id = generate_session_id()
    logger.log_user_input(session_id, "delete all projects")
    logger.close()

    # Read log file
    log_path = Path(test_config['path'])
    assert log_path.exists()

    with open(log_path) as f:
        lines = f.readlines()

    assert len(lines) == 1
    event = json.loads(lines[0])

    assert event['type'] == 'user_input'
    assert event['session'] == session_id
    assert event['input'] == 'delete all projects'
    assert 'ts' in event


def test_log_nl_result(logger, test_config):
    """Test logging NL processing result."""
    session_id = generate_session_id()

    # Mock ParsedIntent
    class MockIntent:
        intent_type = "COMMAND"
        confidence = 0.95
        operation_context = type('obj', (), {
            'operation': 'DELETE',
            'entity_type': 'project',
            'identifier': '__ALL__'
        })()
        metadata = {}

    logger.log_nl_result(session_id, MockIntent(), duration_ms=1234)
    logger.close()

    # Read log file
    with open(test_config['path']) as f:
        event = json.loads(f.readline())

    assert event['type'] == 'nl_result'
    assert event['session'] == session_id
    assert event['intent'] == 'COMMAND'
    assert event['confidence'] == 0.95
    assert event['operation'] == 'DELETE'
    assert event['entity'] == 'project'
    assert event['identifier'] == '__ALL__'
    assert event['validation'] == 'passed'
    assert event['duration_ms'] == 1234


def test_log_execution_result(logger, test_config):
    """Test logging execution result."""
    session_id = generate_session_id()

    result = {
        'success': True,
        'message': 'Deleted 15 projects',
        'bulk_results': {'projects': 15}
    }

    logger.log_execution_result(session_id, result, duration_ms=9800)
    logger.close()

    # Read log file
    with open(test_config['path']) as f:
        event = json.loads(f.readline())

    assert event['type'] == 'execution_result'
    assert event['session'] == session_id
    assert event['success'] is True
    assert event['message'] == 'Deleted 15 projects'
    assert event['entities_affected'] == {'projects': 15}
    assert event['total_duration_ms'] == 9800


def test_log_error(logger, test_config):
    """Test logging error."""
    session_id = generate_session_id()

    try:
        raise ValueError("Project ID must be positive")
    except ValueError as e:
        logger.log_error(session_id, "validation", e, context={"task_id": 7})

    logger.close()

    # Read log file
    with open(test_config['path']) as f:
        event = json.loads(f.readline())

    assert event['type'] == 'error'
    assert event['session'] == session_id
    assert event['stage'] == 'validation'
    assert event['error_type'] == 'ValueError'
    assert event['error'] == 'Project ID must be positive'
    assert event['recoverable'] is True
    assert event['context']['task_id'] == 7


def test_pii_redaction(test_config):
    """Test PII redaction."""
    test_config['privacy']['redact_pii'] = True
    logger = ProductionLogger(test_config)
    session_id = generate_session_id()

    # Input with email and IP
    logger.log_user_input(session_id, "Contact me at john@example.com from 192.168.1.1")
    logger.close()

    # Read log file
    with open(test_config['path']) as f:
        event = json.loads(f.readline())

    assert '[EMAIL]' in event['input']
    assert '[IP]' in event['input']
    assert 'john@example.com' not in event['input']
    assert '192.168.1.1' not in event['input']


def test_secret_redaction(test_config):
    """Test secret redaction."""
    test_config['privacy']['redact_secrets'] = True
    logger = ProductionLogger(test_config)
    session_id = generate_session_id()

    # Input with API key
    logger.log_user_input(session_id, "Use key sk-abcdef1234567890abcdef1234567890")
    logger.close()

    # Read log file
    with open(test_config['path']) as f:
        event = json.loads(f.readline())

    assert '[API_KEY]' in event['input']
    assert 'sk-abcdef' not in event['input']


def test_multiple_events(logger, test_config):
    """Test logging multiple events in sequence."""
    session_id = generate_session_id()

    logger.log_user_input(session_id, "delete all projects")

    class MockIntent:
        intent_type = "COMMAND"
        confidence = 0.91
        operation_context = type('obj', (), {'operation': 'DELETE', 'entity_type': 'project', 'identifier': '__ALL__'})()
        metadata = {}

    logger.log_nl_result(session_id, MockIntent(), duration_ms=1234)
    logger.log_execution_result(session_id, {'success': True, 'message': 'Done'}, duration_ms=5000)
    logger.close()

    # Read log file
    with open(test_config['path']) as f:
        events = [json.loads(line) for line in f]

    assert len(events) == 3
    assert events[0]['type'] == 'user_input'
    assert events[1]['type'] == 'nl_result'
    assert events[2]['type'] == 'execution_result'

    # All should have same session ID
    assert all(e['session'] == session_id for e in events)


def test_log_rotation(test_config, temp_log_dir):
    """Test log file rotation."""
    # Set small max size for testing
    test_config['rotation']['max_file_size_mb'] = 0.001  # ~1KB

    logger = ProductionLogger(test_config)
    session_id = generate_session_id()

    # Write many events to trigger rotation
    for i in range(100):
        logger.log_user_input(session_id, f"Command {i}" * 20)  # Make it large

    logger.close()

    # Check for rotated files
    log_files = list(temp_log_dir.glob("production.jsonl*"))
    assert len(log_files) >= 2  # Original + at least 1 rotated


def test_disabled_events(test_config):
    """Test that disabled events are not logged."""
    test_config['events']['user_input'] = False
    test_config['events']['nl_results'] = False

    logger = ProductionLogger(test_config)
    session_id = generate_session_id()

    logger.log_user_input(session_id, "test")

    class MockIntent:
        intent_type = "COMMAND"
        confidence = 0.95
        operation_context = None
        metadata = {}

    logger.log_nl_result(session_id, MockIntent(), duration_ms=100)
    logger.log_execution_result(session_id, {'success': True}, duration_ms=100)
    logger.close()

    # Read log file
    with open(test_config['path']) as f:
        events = [json.loads(line) for line in f]

    # Only execution_result should be logged
    assert len(events) == 1
    assert events[0]['type'] == 'execution_result'


def test_thread_safety(logger, test_config):
    """Test concurrent logging from multiple threads."""
    import threading
    session_id = generate_session_id()

    def log_events(thread_id):
        for i in range(10):
            logger.log_user_input(session_id, f"Thread {thread_id} message {i}")

    threads = [threading.Thread(target=log_events, args=(i,)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5.0)

    logger.close()

    # Read log file
    with open(test_config['path']) as f:
        events = [json.loads(line) for line in f]

    # Should have 50 events (5 threads * 10 messages)
    assert len(events) == 50
```

**VERIFY:**
```bash
pytest tests/monitoring/test_production_logger.py -v
# Expected: All tests pass
```

---

### STEP 3.2: Create integration tests

**FILE:** `tests/monitoring/test_integration.py`

**COMPLETE TEST FILE:**

```python
"""Integration tests for production logging."""

import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from src.monitoring.production_logger import ProductionLogger, generate_session_id


@pytest.fixture
def temp_log_path(tmp_path):
    """Temporary log file path."""
    return tmp_path / "production.jsonl"


@pytest.fixture
def monitoring_config(temp_log_path):
    """Monitoring configuration."""
    return {
        'enabled': True,
        'path': str(temp_log_path),
        'events': {
            'user_input': True,
            'nl_results': True,
            'execution_results': True,
            'errors': True,
        },
        'privacy': {
            'redact_pii': True,
            'redact_secrets': True,
        },
        'rotation': {
            'max_file_size_mb': 100,
            'max_files': 10,
        }
    }


def test_full_nl_workflow_logged(monitoring_config, temp_log_path):
    """Test that a full NL workflow is logged correctly."""
    logger = ProductionLogger(monitoring_config)
    session_id = generate_session_id()

    # 1. User input
    logger.log_user_input(session_id, "delete all projects")

    # 2. NL processing
    class MockIntent:
        intent_type = "COMMAND"
        confidence = 0.91
        operation_context = type('obj', (), {
            'operation': 'DELETE',
            'entity_type': 'project',
            'identifier': '__ALL__'
        })()
        metadata = {}

    logger.log_nl_result(session_id, MockIntent(), duration_ms=1234)

    # 3. Execution
    result = {
        'success': True,
        'message': 'Deleted 15 projects',
        'bulk_results': {'projects': 15}
    }
    logger.log_execution_result(session_id, result, duration_ms=9800)

    logger.close()

    # Verify all events logged
    with open(temp_log_path) as f:
        events = [json.loads(line) for line in f]

    assert len(events) == 3

    # Verify event sequence
    assert events[0]['type'] == 'user_input'
    assert events[1]['type'] == 'nl_result'
    assert events[2]['type'] == 'execution_result'

    # Verify session continuity
    assert all(e['session'] == session_id for e in events)

    # Verify timestamps in order
    timestamps = [e['ts'] for e in events]
    assert timestamps == sorted(timestamps)


def test_error_workflow_logged(monitoring_config, temp_log_path):
    """Test that errors are logged correctly."""
    logger = ProductionLogger(monitoring_config)
    session_id = generate_session_id()

    # 1. User input
    logger.log_user_input(session_id, "invalid command")

    # 2. Error during processing
    try:
        raise ValueError("Invalid operation")
    except ValueError as e:
        logger.log_error(session_id, "nl_processing", e)

    logger.close()

    # Verify events
    with open(temp_log_path) as f:
        events = [json.loads(line) for line in f]

    assert len(events) == 2
    assert events[0]['type'] == 'user_input'
    assert events[1]['type'] == 'error'
    assert events[1]['stage'] == 'nl_processing'
    assert events[1]['error_type'] == 'ValueError'


def test_multi_turn_session(monitoring_config, temp_log_path):
    """Test multi-turn conversation tracking."""
    logger = ProductionLogger(monitoring_config)
    session_id = generate_session_id()

    # Turn 1
    logger.log_user_input(session_id, "list all projects")
    logger.log_execution_result(session_id, {'success': True}, duration_ms=100)

    # Turn 2
    logger.log_user_input(session_id, "delete project 5")
    logger.log_execution_result(session_id, {'success': True}, duration_ms=200)

    # Turn 3
    logger.log_user_input(session_id, "show status")
    logger.log_execution_result(session_id, {'success': True}, duration_ms=50)

    logger.close()

    # Verify session continuity
    with open(temp_log_path) as f:
        events = [json.loads(line) for line in f]

    assert len(events) == 6  # 3 inputs + 3 results
    assert all(e['session'] == session_id for e in events)
```

**VERIFY:**
```bash
pytest tests/monitoring/test_integration.py -v
# Expected: All tests pass
```

---

## PHASE 4: Documentation

### STEP 4.1: Create user guide

**FILE:** `docs/guides/PRODUCTION_MONITORING_GUIDE.md`

**ACTION:** Create guide (see full content in implementation plan)

**VERIFY:**
```bash
ls -la docs/guides/PRODUCTION_MONITORING_GUIDE.md
# Expected: File exists
```

---

### STEP 4.2: Update CLAUDE.md

**FILE:** `CLAUDE.md`

**ACTION:** Add section after "Session Management Architecture" (around line 350)

**INSERT:**

```markdown
### 16. Production Monitoring (v1.8.0)
**Structured logging for production observability:**

- **JSON Lines Format**: Machine-parsable, grep-friendly logs
- **I/O Boundaries**: User input → NL processing → execution → result
- **Quality Metrics**: Confidence scores, validation status, performance
- **Session Tracking**: Multi-turn conversation continuity
- **Privacy**: PII/secret redaction

**Key Events:**
- `user_input`: All user commands and NL text
- `nl_result`: NL parsing quality (confidence, validation, duration)
- `execution_result`: Task execution outcome (success, entities affected)
- `error`: Failures with stage and context

**Configuration:** `config/config.yaml` → `monitoring.production_logging`

**Enable/Disable:** `enabled: true/false` (disabled by default)

**Log Location:** `~/obra-runtime/logs/production.jsonl`

**Analysis:** `scripts/monitoring/analyze_logs.py`

**See**: `docs/guides/PRODUCTION_MONITORING_GUIDE.md` for complete guide
```

**VERIFY:**
```bash
grep -n "Production Monitoring" CLAUDE.md
# Expected: Should find the new section
```

---

## PHASE 5: Verification & Testing

### STEP 5.1: Run all tests

```bash
# Unit tests
pytest tests/monitoring/test_production_logger.py -v

# Integration tests
pytest tests/monitoring/test_integration.py -v

# All tests
pytest tests/ -v
```

**EXPECTED:** All tests pass

---

### STEP 5.2: Manual end-to-end test

**ACTION:** Test interactive REPL with logging enabled

```bash
# 1. Enable production logging
# Edit config/config.yaml: set monitoring.production_logging.enabled = true

# 2. Start interactive mode
python -m src.cli interactive

# 3. Run test commands
orchestrator> delete all projects
# (Cancel when prompted)

orchestrator> exit

# 4. Verify logs created
ls -lh ~/obra-runtime/logs/production.jsonl

# 5. View logs
cat ~/obra-runtime/logs/production.jsonl | jq .

# 6. Should see 3 events:
# - user_input: "delete all projects"
# - nl_result: COMMAND, DELETE, project, confidence ~0.91
# - execution_result: cancelled=true (if you cancelled)
```

**VERIFY:** Log file exists with JSON events

---

### STEP 5.3: Verify privacy redaction

```bash
# 1. Test with PII
python -m src.cli interactive

orchestrator> send email to john@example.com from 192.168.1.1
orchestrator> exit

# 2. Check log
cat ~/obra-runtime/logs/production.jsonl | jq '.input'

# 3. Should see:
# "send email to [EMAIL] from [IP]"
```

**VERIFY:** Email and IP are redacted

---

## FINAL CHECKLIST

- [ ] `src/monitoring/` directory created
- [ ] `src/monitoring/__init__.py` exists
- [ ] `src/monitoring/production_logger.py` complete (400+ lines)
- [ ] `config/config.yaml` has `monitoring` section
- [ ] `src/interactive.py` modified (6 integration points)
- [ ] `tests/monitoring/test_production_logger.py` complete (15+ tests)
- [ ] `tests/monitoring/test_integration.py` complete (3+ tests)
- [ ] All tests pass (`pytest tests/monitoring/ -v`)
- [ ] Manual E2E test successful
- [ ] Privacy redaction verified
- [ ] `CLAUDE.md` updated with new section
- [ ] `docs/guides/PRODUCTION_MONITORING_GUIDE.md` created

---

## COMMIT MESSAGE

```
feat: Add production monitoring with structured logging (v1.8.0)

Implements JSON Lines logging for production observability, capturing
I/O boundaries and quality metrics while excluding verbose in-progress
messages.

**Features:**
- ProductionLogger class with rotating file handler
- 6 event types: user_input, nl_result, execution_result, error, etc.
- Session tracking for multi-turn conversations
- PII/secret redaction for privacy
- Configurable event filtering
- Thread-safe concurrent logging

**Integration:**
- 6 integration points in interactive.py
- Logs user input, NL processing, execution, errors
- <5% performance overhead
- Disabled by default for backward compatibility

**Testing:**
- 15+ unit tests (ProductionLogger)
- 3+ integration tests (E2E workflows)
- Manual testing verified
- Privacy redaction tested

**Configuration:**
monitoring.production_logging.enabled = false (default)

**Impact:**
- Enables real-time production monitoring
- Tracks NL command quality (confidence, validation)
- Identifies performance bottlenecks
- Supports data-driven prompt engineering

**Files Added:**
- src/monitoring/production_logger.py (450 lines)
- tests/monitoring/test_production_logger.py (250 lines)
- tests/monitoring/test_integration.py (120 lines)
- docs/guides/PRODUCTION_MONITORING_GUIDE.md

**Files Modified:**
- src/interactive.py (~60 lines added)
- config/config.yaml (monitoring section)
- CLAUDE.md (documentation)

See: docs/development/PRODUCTION_MONITORING_IMPLEMENTATION_PLAN.md
```

---

## TROUBLESHOOTING

### Issue: Import errors

```bash
# Solution: Ensure PYTHONPATH includes src/
export PYTHONPATH=/home/omarwsl/projects/claude_code_orchestrator:$PYTHONPATH
```

### Issue: Log file not created

```bash
# Solution: Check permissions and path
mkdir -p ~/obra-runtime/logs
chmod 755 ~/obra-runtime/logs
```

### Issue: Tests fail with "module not found"

```bash
# Solution: Install in editable mode
pip install -e .
```

---

**END OF MACHINE GUIDE**
**Estimated Implementation Time:** 8-10 hours
**Target Completion:** Within 1-2 days
