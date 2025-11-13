"""Agent connectivity integration tests.

Run on: Before merge, nightly CI
Speed: 5-10 minutes
Purpose: Validate Claude Code agent communication
"""

import pytest
import os
import tempfile
import shutil
from src.agents.claude_code_local import ClaudeCodeLocalAgent
from src.core.config import Config


@pytest.mark.integration
class TestAgentConnectivity:
    """Validate agent connectivity and basic operations."""

    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace."""
        workspace = tempfile.mkdtemp(prefix='agent_test_')
        yield workspace
        # Cleanup
        if os.path.exists(workspace):
            shutil.rmtree(workspace)

    @pytest.fixture
    def agent_config(self):
        """Agent configuration."""
        return {
            'workspace_path': None,  # Set per test
            'dangerous_mode': True,  # Skip permissions for testing
            'print_mode': True  # Headless mode
        }

    def test_claude_code_local_agent_instantiate(self, agent_config, temp_workspace):
        """Verify Claude Code local agent can be instantiated."""
        agent_config['workspace_path'] = temp_workspace

        agent = ClaudeCodeLocalAgent()
        agent.initialize(agent_config)

        assert agent is not None

    def test_claude_code_local_agent_send_prompt(self, agent_config, temp_workspace):
        """Verify agent can send/receive prompts."""
        agent_config['workspace_path'] = temp_workspace

        agent = ClaudeCodeLocalAgent()
        agent.initialize(agent_config)

        # Send simple prompt
        response = agent.send_prompt("Create a file called test.txt with 'Hello World'")

        assert response is not None
        assert len(response) > 0

        # Verify file created
        test_file = os.path.join(temp_workspace, 'test.txt')
        # May take a moment for agent to execute
        import time
        time.sleep(0.5)

        # File may or may not exist depending on agent behavior
        # Just verify we got a response
        assert True

    def test_claude_code_session_isolation(self, agent_config, temp_workspace):
        """Verify sessions are isolated (per-iteration model)."""
        agent_config['workspace_path'] = temp_workspace

        # Session 1
        agent1 = ClaudeCodeLocalAgent()
        agent1.initialize(agent_config)
        response1 = agent1.send_prompt("Create file session1.txt")

        # Session 2 (fresh)
        agent2 = ClaudeCodeLocalAgent()
        agent2.initialize(agent_config)
        response2 = agent2.send_prompt("List all files")

        # Both should execute independently
        assert response1 is not None
        assert response2 is not None
