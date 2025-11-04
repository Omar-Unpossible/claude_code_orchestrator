"""Agent plugin implementations.

This module contains concrete implementations of agent plugins:
- ClaudeCodeLocalAgent: Claude Code via local subprocess
- ClaudeCodeSSHAgent: Claude Code via SSH connection to VM
- MockAgent: Mock agent for testing
- (Future) ClaudeCodeDockerAgent: Claude Code in Docker container
- (Future) AiderAgent: Aider integration

All agents implement the AgentPlugin interface defined in src.plugins.base.
"""

from src.agents.claude_code_local import ClaudeCodeLocalAgent
from src.agents.claude_code_ssh import ClaudeCodeSSHAgent
from src.agents.mock_agent import MockAgent

__all__ = ['ClaudeCodeLocalAgent', 'ClaudeCodeSSHAgent', 'MockAgent']
