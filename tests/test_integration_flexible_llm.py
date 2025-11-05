"""Integration tests for flexible LLM orchestration.

Tests end-to-end orchestrator functionality with both Ollama and OpenAI Codex
LLM types to ensure the registry-based LLM system works correctly.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import subprocess

from src.orchestrator import Orchestrator
from src.core.exceptions import OrchestratorException
from src.core.state import StateManager
from src.llm.local_interface import LocalLLMInterface
from src.llm.openai_codex_interface import OpenAICodexLLMPlugin


@pytest.fixture
def state_manager(test_config):
    """Create state manager for integration tests."""
    db_url = test_config.get('database.url')
    sm = StateManager.get_instance(db_url)
    yield sm
    sm.close()


class TestFlexibleLLMOrchestration:
    """Test orchestrator with different LLM types."""

    def test_orchestrator_with_ollama_llm(self, test_config, monkeypatch):
        """Test orchestrator uses Ollama LLM when configured."""
        # Mock requests.get for Ollama health check
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'models': [
                {'name': 'qwen2.5-coder:32b', 'size': 1000000}
            ]
        }

        def mock_get(*args, **kwargs):
            return mock_response

        monkeypatch.setattr('requests.get', mock_get)

        # Configure for Ollama
        test_config._config['llm']['type'] = 'ollama'
        test_config._config['llm']['model'] = 'qwen2.5-coder:32b'
        test_config._config['llm']['base_url'] = 'http://localhost:11434'

        orchestrator = Orchestrator(config=test_config)
        orchestrator.initialize()

        # Verify Ollama LLM is used
        assert isinstance(orchestrator.llm_interface, LocalLLMInterface)
        assert orchestrator.llm_interface.model == 'qwen2.5-coder:32b'
        assert orchestrator.llm_interface.endpoint == 'http://localhost:11434'

        # Verify LLM is set in dependent components
        assert orchestrator.context_manager.llm_interface is orchestrator.llm_interface
        assert orchestrator.confidence_scorer.llm_interface is orchestrator.llm_interface

        # Cleanup
        orchestrator.shutdown()

    def test_orchestrator_with_codex_llm(self, test_config, monkeypatch):
        """Test orchestrator uses OpenAI Codex LLM when configured."""
        # Mock which command to find codex CLI
        def mock_which(cmd):
            if cmd == 'codex':
                return '/usr/local/bin/codex'
            return None

        monkeypatch.setattr('shutil.which', mock_which)

        # Configure for OpenAI Codex
        test_config._config['llm']['type'] = 'openai-codex'
        test_config._config['llm']['model'] = 'codex-mini-latest'
        test_config._config['llm']['codex_command'] = 'codex'

        orchestrator = Orchestrator(config=test_config)
        orchestrator.initialize()

        # Verify OpenAI Codex LLM is used
        assert isinstance(orchestrator.llm_interface, OpenAICodexLLMPlugin)
        assert orchestrator.llm_interface.model == 'codex-mini-latest'
        assert orchestrator.llm_interface.codex_command == 'codex'

        # Verify LLM is set in dependent components
        assert orchestrator.context_manager.llm_interface is orchestrator.llm_interface
        assert orchestrator.confidence_scorer.llm_interface is orchestrator.llm_interface

        # Cleanup
        orchestrator.shutdown()

    def test_orchestrator_invalid_llm_type(self, test_config):
        """Test orchestrator raises error for invalid LLM type."""
        # Configure with invalid LLM type
        test_config._config['llm']['type'] = 'invalid-llm'

        orchestrator = Orchestrator(config=test_config)

        # Should raise OrchestratorException during initialization
        with pytest.raises(OrchestratorException, match="Invalid LLM type"):
            orchestrator.initialize()

        # Orchestrator should be in ERROR state
        from src.orchestrator import OrchestratorState
        assert orchestrator._state == OrchestratorState.ERROR

    def test_quality_controller_with_codex(self, test_config, state_manager, monkeypatch):
        """Test QualityController works with OpenAI Codex LLM."""
        # Mock which command
        def mock_which(cmd):
            if cmd == 'codex':
                return '/usr/local/bin/codex'
            return None

        monkeypatch.setattr('shutil.which', mock_which)

        # Mock subprocess.run for codex CLI calls
        def mock_run(*args, **kwargs):
            result = MagicMock()
            result.returncode = 0
            result.stdout = "The code looks correct and follows best practices."
            return result

        monkeypatch.setattr('subprocess.run', mock_run)

        # Configure for OpenAI Codex
        test_config._config['llm']['type'] = 'openai-codex'
        test_config._config['llm']['model'] = 'codex-mini-latest'

        orchestrator = Orchestrator(config=test_config)
        orchestrator.initialize()

        # Verify OpenAI Codex is being used
        assert isinstance(orchestrator.llm_interface, OpenAICodexLLMPlugin)

        # Create test project and task
        project = state_manager.create_project(
            'Test Project',
            'Test quality controller',
            '/tmp/test'
        )
        task = state_manager.create_task(project.id, {
            'title': 'Implement function',
            'description': 'Create a function that adds two numbers',
            'priority': 5,
            'status': 'pending'
        })

        # Test quality controller validation
        agent_response = """
def add(a, b):
    \"\"\"Add two numbers.\"\"\"
    return a + b

# Test
assert add(2, 3) == 5
"""

        result = orchestrator.quality_controller.validate_output(
            output=agent_response,
            task=task,
            context={'language': 'python'}
        )

        # Verify quality validation works
        assert result is not None
        assert hasattr(result, 'overall_score')
        assert 0.0 <= result.overall_score <= 1.0

        # Verify LLM metrics were tracked (LLM may or may not be called depending on validation logic)
        assert hasattr(orchestrator.llm_interface, 'metrics')

        # Cleanup
        orchestrator.shutdown()

    def test_confidence_scorer_with_codex(self, test_config, state_manager, monkeypatch):
        """Test ConfidenceScorer uses OpenAI Codex LLM correctly."""
        # Mock which command
        def mock_which(cmd):
            if cmd == 'codex':
                return '/usr/local/bin/codex'
            return None

        monkeypatch.setattr('shutil.which', mock_which)

        # Mock subprocess.run for codex CLI calls
        def mock_run(*args, **kwargs):
            result = MagicMock()
            result.returncode = 0
            result.stdout = "High confidence: 0.9"
            return result

        monkeypatch.setattr('subprocess.run', mock_run)

        # Configure for OpenAI Codex
        test_config._config['llm']['type'] = 'openai-codex'
        test_config._config['llm']['model'] = 'codex-mini-latest'

        orchestrator = Orchestrator(config=test_config)
        orchestrator.initialize()

        # Verify OpenAI Codex is being used
        assert isinstance(orchestrator.llm_interface, OpenAICodexLLMPlugin)

        # Create test project and task (with unique name)
        project = state_manager.create_project(
            'Test Project Confidence Scorer',
            'Test confidence scorer',
            '/tmp/test_confidence'
        )
        task = state_manager.create_task(project.id, {
            'title': 'Implement function',
            'description': 'Create a function that adds two numbers',
            'priority': 5,
            'status': 'pending'
        })

        # Test confidence scorer with a response
        response = """
def add(a, b):
    \"\"\"Add two numbers.\"\"\"
    return a + b

# Test
assert add(2, 3) == 5
"""

        # Calculate confidence using ConfidenceScorer (correct method name)
        confidence = orchestrator.confidence_scorer.score_response(
            response=response,
            task=task,
            context={}
        )

        # Verify confidence score is valid
        assert 0.0 <= confidence <= 1.0

        # Verify LLM was potentially used (depending on confidence scorer implementation)
        assert hasattr(orchestrator.llm_interface, 'metrics')

        # Cleanup
        orchestrator.shutdown()

    def test_switch_between_llms(self, test_config, monkeypatch):
        """Test switching LLM type requires new orchestrator instance."""
        # Mock requests.get for Ollama health check
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'models': [
                {'name': 'qwen2.5-coder:32b', 'size': 1000000}
            ]
        }

        def mock_get(*args, **kwargs):
            return mock_response

        monkeypatch.setattr('requests.get', mock_get)

        # Mock which command for codex
        def mock_which(cmd):
            if cmd == 'codex':
                return '/usr/local/bin/codex'
            return None

        monkeypatch.setattr('shutil.which', mock_which)

        # Start with Ollama
        test_config._config['llm']['type'] = 'ollama'
        test_config._config['llm']['model'] = 'qwen2.5-coder:32b'
        test_config._config['llm']['base_url'] = 'http://localhost:11434'

        orch1 = Orchestrator(config=test_config)
        orch1.initialize()
        assert isinstance(orch1.llm_interface, LocalLLMInterface)

        # Verify model and config
        assert orch1.llm_interface.model == 'qwen2.5-coder:32b'

        # Switch to OpenAI Codex (new instance required)
        test_config._config['llm']['type'] = 'openai-codex'
        test_config._config['llm']['model'] = 'codex-mini-latest'
        test_config._config['llm']['codex_command'] = 'codex'

        orch2 = Orchestrator(config=test_config)
        orch2.initialize()
        assert isinstance(orch2.llm_interface, OpenAICodexLLMPlugin)

        # Verify model and config
        assert orch2.llm_interface.model == 'codex-mini-latest'

        # Verify they are different instances
        assert orch1.llm_interface is not orch2.llm_interface
        assert type(orch1.llm_interface) != type(orch2.llm_interface)

        # Cleanup
        orch1.shutdown()
        orch2.shutdown()


class TestLLMRegistryIntegration:
    """Test LLM registry integration with orchestrator."""

    def test_mock_llm_registration(self, test_config):
        """Test that mock LLM is properly registered for tests."""
        # Default test_config uses mock LLM
        test_config._config['llm']['type'] = 'mock'

        orchestrator = Orchestrator(config=test_config)
        orchestrator.initialize()

        # Verify mock LLM is used
        from tests.mocks.mock_llm import MockLLM
        assert isinstance(orchestrator.llm_interface, MockLLM)

        # Cleanup
        orchestrator.shutdown()

    def test_llm_registry_list_available(self):
        """Test that LLM registry lists all available LLM types."""
        from src.plugins.registry import LLMRegistry

        available = LLMRegistry.list()

        # Verify core LLMs are registered
        assert 'ollama' in available
        assert 'openai-codex' in available
        assert 'mock' in available

        # Should be at least 3 LLM types
        assert len(available) >= 3
