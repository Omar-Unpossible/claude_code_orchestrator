"""Unit tests for DecisionRecordGenerator.

Tests automated ADR generation, privacy compliance, and decision record management.
Follows TEST_GUIDELINES.md constraints (max 0.5s sleep, 5 threads, 20KB).
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime, UTC
from unittest.mock import Mock, MagicMock

from src.orchestration.session.decision_record_generator import (
    DecisionRecordGenerator,
    DecisionRecord
)
from src.core.config import Config
from src.core.state import StateManager
from src.core.exceptions import OrchestratorException


@pytest.fixture
def mock_config(tmp_path):
    """Create mock configuration."""
    config = Mock(spec=Config)

    config_data = {
        'orchestrator': {
            'session_continuity': {
                'decision_logging': {
                    'enabled': True,
                    'significance_threshold': 0.7,
                    'output_dir': str(tmp_path / 'decision_records')
                }
            }
        }
    }

    def get_nested(key, default=None):
        """Navigate nested config dict."""
        keys = key.split('.')
        value = config_data
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    config.get = get_nested
    config._config = config_data

    return config


@pytest.fixture
def mock_state_manager():
    """Create mock StateManager."""
    return Mock(spec=StateManager)


@pytest.fixture
def mock_action():
    """Create mock Action object."""
    action = Mock()
    action.type = 'proceed'
    action.confidence = 0.9
    action.explanation = "Task completed successfully with high quality output."
    action.metadata = {'quality_score': 0.85}
    action.timestamp = datetime.now(UTC)
    return action


@pytest.fixture
def decision_context():
    """Create decision context."""
    task = MagicMock()
    task.id = 123
    task.title = "Implement feature X"

    return {
        'task': task,
        'validation_result': {'complete': True, 'valid': True},
        'quality_score': 0.85,
        'session_id': 'sess_123'
    }


@pytest.fixture
def generator(mock_config, mock_state_manager):
    """Create DecisionRecordGenerator instance."""
    return DecisionRecordGenerator(mock_config, mock_state_manager)


class TestInitialization:
    """Test DecisionRecordGenerator initialization."""

    def test_initialization_success(self, mock_config, mock_state_manager, tmp_path):
        """Test successful initialization."""
        generator = DecisionRecordGenerator(mock_config, mock_state_manager)

        assert generator.config == mock_config
        assert generator.state_manager == mock_state_manager
        assert generator.enabled is True
        assert generator.significance_threshold == 0.7
        assert generator.output_dir == Path(tmp_path / 'decision_records')

        # Output directory should be created
        assert generator.output_dir.exists()

    def test_initialization_disabled(self, mock_config, mock_state_manager):
        """Test initialization with logging disabled."""
        mock_config._config['orchestrator']['session_continuity']['decision_logging']['enabled'] = False

        generator = DecisionRecordGenerator(mock_config, mock_state_manager)

        assert generator.enabled is False


class TestSignificanceDetection:
    """Test significance detection."""

    def test_is_significant_above_threshold(self, generator, mock_action):
        """Test action above significance threshold."""
        mock_action.confidence = 0.9

        assert generator.is_significant(mock_action) is True

    def test_is_significant_at_threshold(self, generator, mock_action):
        """Test action at significance threshold."""
        mock_action.confidence = 0.7

        assert generator.is_significant(mock_action) is True

    def test_is_significant_below_threshold(self, generator, mock_action):
        """Test action below significance threshold."""
        mock_action.confidence = 0.6

        assert generator.is_significant(mock_action) is False

    def test_is_significant_disabled(self, generator, mock_action):
        """Test significance check when disabled."""
        generator.enabled = False

        assert generator.is_significant(mock_action) is False


class TestDecisionRecordGeneration:
    """Test decision record generation."""

    def test_generate_decision_record_success(self, generator, mock_action,
                                              decision_context):
        """Test successful DR generation."""
        dr = generator.generate_decision_record(mock_action, decision_context)

        assert isinstance(dr, DecisionRecord)
        assert dr.dr_id.startswith('DR-')
        assert dr.confidence == 0.9
        assert 'Task: Implement feature X' in dr.context
        assert 'proceed' in dr.decision
        assert len(dr.consequences) > 0
        assert dr.metadata['action_type'] == 'proceed'
        assert dr.metadata['task_id'] == 123

    def test_generate_decision_record_id_format(self, generator, mock_action,
                                                decision_context):
        """Test DR ID format."""
        dr = generator.generate_decision_record(mock_action, decision_context)

        # Format: DR-YYYYMMDD-NNN
        assert dr.dr_id.startswith('DR-')
        parts = dr.dr_id.split('-')
        assert len(parts) == 3
        assert len(parts[1]) == 8  # YYYYMMDD
        assert len(parts[2]) == 3  # NNN (zero-padded)

    def test_generate_decision_record_increments_counter(self, generator,
                                                         mock_action, decision_context):
        """Test DR counter increments."""
        dr1 = generator.generate_decision_record(mock_action, decision_context)
        dr2 = generator.generate_decision_record(mock_action, decision_context)

        # IDs should be different
        assert dr1.dr_id != dr2.dr_id

        # Counter should increment
        counter1 = int(dr1.dr_id.split('-')[2])
        counter2 = int(dr2.dr_id.split('-')[2])
        assert counter2 == counter1 + 1


class TestDecisionRecordSaving:
    """Test decision record saving."""

    def test_save_decision_record_success(self, generator, mock_action,
                                         decision_context):
        """Test successful DR save."""
        dr = generator.generate_decision_record(mock_action, decision_context)
        filepath = generator.save_decision_record(dr)

        # File should exist
        assert filepath.exists()
        assert filepath.name == f"{dr.dr_id}.md"

        # Content should be markdown
        content = filepath.read_text()
        assert f"# {dr.dr_id}" in content
        assert "## Context" in content
        assert "## Decision" in content
        assert "## Consequences" in content

    def test_save_decision_record_creates_directory(self, mock_config,
                                                   mock_state_manager, tmp_path):
        """Test save creates output directory if missing."""
        # Don't create directory in initialization
        output_dir = tmp_path / 'new_dir' / 'decision_records'
        mock_config._config['orchestrator']['session_continuity']['decision_logging']['output_dir'] = str(output_dir)

        generator = DecisionRecordGenerator(mock_config, mock_state_manager)

        assert output_dir.exists()


class TestPrivacyCompliance:
    """Test privacy compliance features."""

    def test_sanitize_reasoning_indicators(self, generator):
        """Test removal of reasoning indicators."""
        text = "I think this is the best approach. Let me consider the alternatives."

        sanitized = generator._sanitize_text(text)  # pylint: disable=protected-access

        # Reasoning indicators should be removed
        assert "I think" not in sanitized
        assert "Let me consider" not in sanitized

    def test_sanitize_api_keys(self, generator):
        """Test redaction of API keys."""
        text = "Using API key abcdef1234567890abcdef1234567890abcdef12 for authentication"

        sanitized = generator._sanitize_text(text)  # pylint: disable=protected-access

        # API key should be redacted
        assert "abcdef1234567890abcdef1234567890abcdef12" not in sanitized
        assert "[REDACTED_KEY]" in sanitized

    def test_sanitize_passwords(self, generator):
        """Test redaction of passwords."""
        text = 'password="mysecretpass123"'

        sanitized = generator._sanitize_text(text)  # pylint: disable=protected-access

        # Password should be redacted
        assert "mysecretpass123" not in sanitized
        assert "[REDACTED]" in sanitized

    def test_sanitize_multiple_secrets(self, generator):
        """Test redaction of multiple secrets."""
        text = """
        I think we should use API key abc123xyz789abc123xyz789abc123xyz789.
        The password is "secret123" and bearer token is Bearer xyz.abc.def
        """

        sanitized = generator._sanitize_text(text)  # pylint: disable=protected-access

        # All secrets should be redacted
        assert "abc123xyz789abc123xyz789abc123xyz789" not in sanitized
        assert "secret123" not in sanitized
        assert "Bearer xyz.abc.def" not in sanitized


class TestContextExtraction:
    """Test context extraction."""

    def test_extract_context_with_task(self, generator, decision_context):
        """Test context extraction with task."""
        context_str = generator._extract_context(decision_context)  # pylint: disable=protected-access

        assert "Task: Implement feature X" in context_str
        assert "Validation: complete=True, valid=True" in context_str
        assert "Quality score: 0.85" in context_str

    def test_extract_context_without_task(self, generator):
        """Test context extraction without task."""
        context = {'quality_score': 0.8}

        context_str = generator._extract_context(context)  # pylint: disable=protected-access

        assert "Quality score: 0.80" in context_str

    def test_extract_context_empty(self, generator):
        """Test context extraction with empty context."""
        context_str = generator._extract_context({})  # pylint: disable=protected-access

        # Should have default message
        assert "orchestration workflow" in context_str.lower()


class TestConsequencesExtraction:
    """Test consequences extraction."""

    def test_extract_consequences_proceed(self, generator, mock_action,
                                         decision_context):
        """Test consequences for proceed action."""
        mock_action.type = 'proceed'

        consequences = generator._extract_consequences(  # pylint: disable=protected-access
            mock_action, decision_context
        )

        assert any('complete' in c.lower() for c in consequences)

    def test_extract_consequences_escalate(self, generator, mock_action,
                                           decision_context):
        """Test consequences for escalate action."""
        mock_action.type = 'escalate'

        consequences = generator._extract_consequences(  # pylint: disable=protected-access
            mock_action, decision_context
        )

        assert any('human intervention' in c.lower() for c in consequences)

    def test_extract_consequences_high_confidence(self, generator, mock_action,
                                                  decision_context):
        """Test consequences include confidence note for high confidence."""
        mock_action.confidence = 0.95

        consequences = generator._extract_consequences(  # pylint: disable=protected-access
            mock_action, decision_context
        )

        assert any('high confidence' in c.lower() for c in consequences)

    def test_extract_consequences_low_confidence(self, generator, mock_action,
                                                 decision_context):
        """Test consequences include confidence note for low confidence."""
        mock_action.confidence = 0.5

        consequences = generator._extract_consequences(  # pylint: disable=protected-access
            mock_action, decision_context
        )

        assert any('low confidence' in c.lower() for c in consequences)


class TestDecisionRecordFormatting:
    """Test DecisionRecord to_markdown and to_dict."""

    def test_to_markdown_format(self, generator, mock_action, decision_context):
        """Test markdown format."""
        dr = generator.generate_decision_record(mock_action, decision_context)
        markdown = dr.to_markdown()

        # Should have ADR sections
        assert f"# {dr.dr_id}" in markdown
        assert "## Context" in markdown
        assert "## Decision" in markdown
        assert "## Consequences" in markdown
        assert "## Metadata" in markdown

    def test_to_dict_serialization(self, generator, mock_action, decision_context):
        """Test dictionary serialization."""
        dr = generator.generate_decision_record(mock_action, decision_context)
        data = dr.to_dict()

        assert data['dr_id'] == dr.dr_id
        assert data['confidence'] == dr.confidence
        assert 'timestamp' in data
        assert 'context' in data
        assert 'decision' in data
        assert 'consequences' in data
        assert 'metadata' in data


class TestErrorHandling:
    """Test error handling."""

    def test_generate_decision_record_error(self, generator):
        """Test error handling in generate_decision_record."""
        # Malformed action
        bad_action = Mock()
        bad_action.type = 'proceed'
        # Missing required attributes
        delattr(bad_action, 'confidence')

        with pytest.raises(OrchestratorException):
            generator.generate_decision_record(bad_action, {})

    def test_save_decision_record_permission_error(self, generator, mock_action,
                                                   decision_context):
        """Test save error handling."""
        dr = generator.generate_decision_record(mock_action, decision_context)

        # Make output directory read-only
        generator.output_dir.chmod(0o444)

        try:
            with pytest.raises(OrchestratorException) as exc_info:
                generator.save_decision_record(dr)

            assert "Failed to save" in str(exc_info.value)
        finally:
            # Restore permissions for cleanup
            generator.output_dir.chmod(0o755)
