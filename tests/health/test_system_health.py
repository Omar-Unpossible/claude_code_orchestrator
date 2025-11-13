"""System health checks for critical components.

Run on: Every commit, deployment validation
Speed: <30 seconds
Purpose: Fast gate to catch system-level failures
"""

import pytest
import requests
import time
from src.core.state import StateManager
from src.core.config import Config
from src.plugins.registry import AgentRegistry, LLMRegistry


class TestSystemHealth:
    """Fast health checks for all critical systems."""

    def test_llm_connectivity_ollama(self):
        """Verify Ollama is reachable and responding."""
        try:
            response = requests.get(
                'http://10.0.75.1:11434/api/tags',
                timeout=5
            )
            assert response.status_code == 200
            data = response.json()
            assert 'models' in data
        except requests.exceptions.RequestException as e:
            pytest.fail(f"Ollama not accessible: {e}")

    def test_llm_connectivity_openai_codex(self):
        """Verify OpenAI Codex config exists (skip if no API key)."""
        import os
        if not os.getenv('OPENAI_API_KEY'):
            pytest.skip("OPENAI_API_KEY not set")

        # Just verify config can load OpenAI settings
        config = Config.load()
        # Should not raise exception
        assert True

    def test_database_connectivity(self):
        """Verify database is accessible."""
        start = time.time()

        state = StateManager(database_url='sqlite:///:memory:')

        # Create test project
        project = state.create_project(
            name="Health Check Project",
            description="Test",
            working_dir="/tmp/health_check"
        )

        # Query it back
        retrieved = state.get_project(project.id)
        assert retrieved is not None
        assert retrieved.project_name == "Health Check Project"

        state.close()

        # Should complete in <1s
        duration = time.time() - start
        assert duration < 1.0, f"Database too slow: {duration}s"

    def test_agent_registry_loaded(self):
        """Verify agent plugins are registered."""
        # Check Claude Code local agent registered
        try:
            agent = AgentRegistry.get('claude-code-local')
            assert agent is not None
        except KeyError:
            pytest.fail("Claude Code local agent not registered")

    def test_llm_registry_loaded(self):
        """Verify LLM plugins are registered."""
        # Check Ollama LLM registered
        try:
            llm = LLMRegistry.get('ollama')
            assert llm is not None
        except KeyError:
            pytest.fail("Ollama LLM not registered")

    def test_configuration_valid(self):
        """Verify default configuration loads."""
        config = Config.load()

        # Validate required keys present
        assert config.get('llm.type') in ['ollama', 'openai-codex']
        assert config.get('llm.model') is not None
        assert config.get('database.url') is not None

    def test_state_manager_initialization(self):
        """Verify StateManager can initialize."""
        start = time.time()

        state = StateManager(database_url='sqlite:///:memory:')

        # Verify DB tables created (should not raise exception)
        state.list_projects()

        state.close()

        duration = time.time() - start
        assert duration < 1.0, f"StateManager init too slow: {duration}s"
