"""Agent plugin implementations.

This module contains concrete implementations of agent plugins:
- ClaudeCodeSSHAgent: Claude Code via SSH connection to VM
- (Future) ClaudeCodeDockerAgent: Claude Code in Docker container
- (Future) AiderAgent: Aider integration

All agents implement the AgentPlugin interface defined in src.plugins.base.
"""

from src.agents.claude_code_ssh import ClaudeCodeSSHAgent

__all__ = ['ClaudeCodeSSHAgent']
