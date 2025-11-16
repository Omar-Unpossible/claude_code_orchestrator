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
