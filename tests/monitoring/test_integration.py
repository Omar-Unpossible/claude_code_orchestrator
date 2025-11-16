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
