"""Git integration for automatic version control and commit management.

This module provides the GitManager class for automatic git operations including:
- Auto-commit after task completion
- Semantic commit message generation using LLM
- Branch management per task
- Optional PR creation via gh CLI
- Rollback support

Key Features:
- LLM-generated semantic commit messages
- Task-specific branching (obra/task-{id}-{slug})
- Configurable commit strategies (per-task, per-milestone, manual)
- Optional PR creation with automated summaries
- Git status checking and validation
- Rollback capabilities

Example:
    >>> git_manager = GitManager(config, llm_interface, state_manager)
    >>> git_manager.initialize('/path/to/project')
    >>>
    >>> # Auto-commit after task completion
    >>> git_manager.commit_task(task)
    >>>
    >>> # Create PR
    >>> pr_url = git_manager.create_pull_request(task)
"""

import logging
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, UTC
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class GitConfig:
    """Configuration for git operations.

    Attributes:
        enabled: Enable git integration
        auto_commit: Automatically commit after task completion
        commit_strategy: Strategy for committing (per_task, per_milestone, manual)
        create_branch: Create branch per task
        branch_prefix: Prefix for branch names
        auto_pr: Automatically create pull requests
        pr_base_branch: Base branch for PRs
        commit_message_template: Template style for commit messages
        include_metadata: Include Obra metadata in commits
    """
    enabled: bool = False
    auto_commit: bool = True
    commit_strategy: str = 'per_task'
    create_branch: bool = True
    branch_prefix: str = 'obra/task-'
    auto_pr: bool = False
    pr_base_branch: str = 'main'
    commit_message_template: str = 'semantic'
    include_metadata: bool = True


class GitException(Exception):
    """Base exception for git operations."""

    def __init__(self, message: str, command: Optional[str] = None, stderr: Optional[str] = None):
        """Initialize exception.

        Args:
            message: Error message
            command: Git command that failed
            stderr: Standard error output
        """
        super().__init__(message)
        self.command = command
        self.stderr = stderr


class GitManager:
    """Manages git operations for automatic version control.

    This class provides automatic git integration including commits, branching,
    and optional PR creation. It uses an LLM to generate semantic commit messages.

    Thread-safe for concurrent use.

    Example:
        >>> from src.llm.local_interface import LocalLLMInterface
        >>> from src.core.state import StateManager
        >>>
        >>> llm = LocalLLMInterface()
        >>> llm.initialize({'endpoint': 'http://localhost:11434'})
        >>> state_manager = StateManager.get_instance('sqlite:///test.db')
        >>>
        >>> config = GitConfig(enabled=True, auto_commit=True)
        >>> git_manager = GitManager(config, llm, state_manager)
        >>> git_manager.initialize('/path/to/project')
        >>>
        >>> # Commit after task completion
        >>> task = state_manager.get_task(1)
        >>> git_manager.commit_task(task)
    """

    def __init__(
        self,
        config: GitConfig,
        llm_interface: Any,
        state_manager: Any
    ):
        """Initialize git manager.

        Args:
            config: Git configuration
            llm_interface: LLM interface for commit message generation
            state_manager: State manager for task information
        """
        self.config = config
        self.llm = llm_interface
        self.state_manager = state_manager
        self.project_dir: Optional[Path] = None
        self._initialized = False

    def initialize(self, project_dir: str) -> None:
        """Initialize git manager with project directory.

        Args:
            project_dir: Path to project directory

        Raises:
            GitException: If directory is not a git repository
        """
        self.project_dir = Path(project_dir).resolve()

        # Check if git repository
        if not (self.project_dir / '.git').exists():
            logger.warning(f"Directory {self.project_dir} is not a git repository")
            if self.config.enabled:
                # Initialize git repo
                self._run_git_command(['init'], check=True)
                logger.info(f"Initialized git repository at {self.project_dir}")

        self._initialized = True
        logger.info(f"GitManager initialized for {self.project_dir}")

    def is_git_repository(self) -> bool:
        """Check if current directory is a git repository.

        Returns:
            True if git repository, False otherwise
        """
        if not self.project_dir:
            return False
        return (self.project_dir / '.git').exists()

    def get_current_branch(self) -> str:
        """Get current git branch name.

        Returns:
            Current branch name

        Raises:
            GitException: If unable to get branch name
        """
        result = self._run_git_command(['branch', '--show-current'], check=True)
        return result.stdout.strip()

    def get_status(self) -> Dict[str, Any]:
        """Get git status information.

        Returns:
            Dictionary with status info:
                - is_clean: bool (True if no changes)
                - staged_files: List[str]
                - unstaged_files: List[str]
                - untracked_files: List[str]

        Example:
            >>> status = git_manager.get_status()
            >>> if not status['is_clean']:
            ...     print(f"Uncommitted changes: {status['unstaged_files']}")
        """
        # Get status porcelain format
        result = self._run_git_command(['status', '--porcelain'], check=True)

        staged_files = []
        unstaged_files = []
        untracked_files = []

        for line in result.stdout.splitlines():
            if not line:
                continue

            status_code = line[:2]
            filename = line[3:]

            # Staged files (first character is not space)
            if status_code[0] not in (' ', '?'):
                staged_files.append(filename)

            # Unstaged files (second character is not space)
            if status_code[1] not in (' ', '?') and status_code[0] != '?':
                unstaged_files.append(filename)

            # Untracked files
            if status_code[0] == '?':
                untracked_files.append(filename)

        is_clean = len(staged_files) == 0 and len(unstaged_files) == 0 and len(untracked_files) == 0

        return {
            'is_clean': is_clean,
            'staged_files': staged_files,
            'unstaged_files': unstaged_files,
            'untracked_files': untracked_files
        }

    def create_branch(self, task_id: int, task_title: str) -> str:
        """Create a new branch for a task.

        Args:
            task_id: Task ID
            task_title: Task title

        Returns:
            Branch name created

        Raises:
            GitException: If branch creation fails

        Example:
            >>> branch = git_manager.create_branch(1, "Implement feature X")
            >>> print(branch)
            'obra/task-1-implement-feature-x'
        """
        # Create slug from task title
        slug = self._slugify(task_title)
        branch_name = f"{self.config.branch_prefix}{task_id}-{slug}"

        # Check if branch already exists
        result = self._run_git_command(['branch', '--list', branch_name])
        if result.stdout.strip():
            logger.info(f"Branch {branch_name} already exists")
            return branch_name

        # Create and checkout branch
        self._run_git_command(['checkout', '-b', branch_name], check=True)
        logger.info(f"Created and checked out branch: {branch_name}")

        return branch_name

    def commit_task(
        self,
        task: Any,
        files: Optional[List[str]] = None
    ) -> bool:
        """Commit changes for a task.

        Args:
            task: Task object
            files: Specific files to commit (None = all changes)

        Returns:
            True if commit successful, False otherwise

        Raises:
            GitException: If commit fails

        Example:
            >>> task = state_manager.get_task(1)
            >>> git_manager.commit_task(task)
        """
        if not self.config.enabled or not self.config.auto_commit:
            logger.debug("Auto-commit disabled, skipping")
            return False

        # Check if there are changes to commit
        status = self.get_status()
        if status['is_clean']:
            logger.info("No changes to commit")
            return False

        # Stage files
        if files:
            for file in files:
                self._run_git_command(['add', file], check=True)
        else:
            # Stage all changes
            self._run_git_command(['add', '-A'], check=True)

        # Generate commit message
        commit_message = self.generate_commit_message(task, status)

        # Commit
        self._run_git_command(['commit', '-m', commit_message], check=True)
        logger.info(f"Committed changes for task {task.id}")

        return True

    def generate_commit_message(
        self,
        task: Any,
        status: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate semantic commit message using LLM.

        Args:
            task: Task object
            status: Git status dict (optional, will fetch if not provided)

        Returns:
            Formatted commit message

        Example:
            >>> task = state_manager.get_task(1)
            >>> message = git_manager.generate_commit_message(task)
            >>> print(message)
            '''feat(module): Implement feature X

            Added functionality to...

            Obra Task ID: #1
            '''
        """
        if status is None:
            status = self.get_status()

        # Get changed files
        changed_files = status['staged_files'] + status['unstaged_files']

        # Build prompt for LLM
        prompt = f"""Generate a semantic commit message for the following task and changes.

Task Title: {task.title}
Task Description: {task.description}

Changed Files:
{chr(10).join(f'  - {f}' for f in changed_files[:10])}  # Limit to 10 files

Requirements:
1. Use semantic commit format: <type>(<scope>): <subject>
2. Types: feat, fix, docs, style, refactor, test, chore
3. Keep subject line under 72 characters
4. Include brief body explaining WHAT and WHY (not HOW)
5. Be concise but informative

Output ONLY the commit message, no explanation."""

        try:
            # Generate message using LLM
            llm_message = self.llm.generate(prompt, temperature=0.3, max_tokens=300)

            # Clean up message
            llm_message = llm_message.strip()

            # Add metadata if configured
            if self.config.include_metadata:
                # Get task metadata
                confidence = getattr(task, 'confidence_score', None)
                quality = getattr(task, 'quality_score', None)

                metadata_lines = [f"\nObra Task ID: #{task.id}"]
                if confidence is not None:
                    metadata_lines.append(f"Confidence: {confidence:.2f}")
                if quality is not None:
                    metadata_lines.append(f"Quality Score: {quality:.2f}")

                metadata_lines.append("\n🤖 Generated with Obra (Claude Code Orchestrator)")

                llm_message += '\n'.join(metadata_lines)

            return llm_message

        except Exception as e:
            logger.warning(f"Failed to generate commit message with LLM: {e}")
            # Fallback to simple message
            return self._generate_fallback_commit_message(task)

    def _generate_fallback_commit_message(self, task: Any) -> str:
        """Generate simple fallback commit message.

        Args:
            task: Task object

        Returns:
            Simple commit message
        """
        message = f"feat: {task.title}\n\n{task.description}"

        if self.config.include_metadata:
            message += f"\n\nObra Task ID: #{task.id}"
            message += "\n🤖 Generated with Obra"

        return message

    def create_pull_request(
        self,
        task: Any,
        base_branch: Optional[str] = None
    ) -> Optional[str]:
        """Create pull request via gh CLI.

        Args:
            task: Task object
            base_branch: Base branch for PR (defaults to config pr_base_branch)

        Returns:
            PR URL if successful, None otherwise

        Raises:
            GitException: If PR creation fails

        Example:
            >>> task = state_manager.get_task(1)
            >>> pr_url = git_manager.create_pull_request(task)
            >>> print(f"Created PR: {pr_url}")
        """
        if not self.config.auto_pr:
            logger.debug("Auto PR creation disabled")
            return None

        # Check if gh CLI is available
        if not self._is_gh_cli_available():
            logger.warning("gh CLI not available, cannot create PR")
            return None

        base_branch = base_branch or self.config.pr_base_branch

        # Generate PR title and body
        pr_title = f"[Obra] {task.title}"
        pr_body = self._generate_pr_body(task)

        try:
            # Create PR using gh CLI
            result = self._run_command(
                ['gh', 'pr', 'create', '--title', pr_title, '--body', pr_body, '--base', base_branch],
                check=True
            )

            pr_url = result.stdout.strip()
            logger.info(f"Created pull request: {pr_url}")
            return pr_url

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to create PR: {e}")
            return None

    def _generate_pr_body(self, task: Any) -> str:
        """Generate PR body description.

        Args:
            task: Task object

        Returns:
            PR body text
        """
        body = f"""## Summary

{task.description}

## Changes

This PR addresses Obra task #{task.id}: {task.title}

## Test Plan

- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

---

🤖 Automatically generated by Obra (Claude Code Orchestrator)
"""
        return body

    def rollback_task(self, task: Any) -> bool:
        """Rollback changes for a task.

        Args:
            task: Task object

        Returns:
            True if rollback successful

        Example:
            >>> git_manager.rollback_task(task)
        """
        # Get task branch name
        slug = self._slugify(task.title)
        branch_name = f"{self.config.branch_prefix}{task.id}-{slug}"

        try:
            # Checkout base branch
            self._run_git_command(['checkout', self.config.pr_base_branch], check=True)

            # Delete task branch
            self._run_git_command(['branch', '-D', branch_name], check=True)

            logger.info(f"Rolled back task {task.id}, deleted branch {branch_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to rollback task: {e}")
            return False

    def _run_git_command(
        self,
        args: List[str],
        check: bool = False
    ) -> subprocess.CompletedProcess:
        """Run git command.

        Args:
            args: Git command arguments (without 'git')
            check: Raise exception on non-zero exit

        Returns:
            CompletedProcess result

        Raises:
            GitException: If check=True and command fails
        """
        return self._run_command(['git'] + args, check=check)

    def _run_command(
        self,
        args: List[str],
        check: bool = False
    ) -> subprocess.CompletedProcess:
        """Run shell command.

        Args:
            args: Command and arguments
            check: Raise exception on non-zero exit

        Returns:
            CompletedProcess result

        Raises:
            GitException: If check=True and command fails
        """
        try:
            result = subprocess.run(
                args,
                cwd=str(self.project_dir) if self.project_dir else None,
                capture_output=True,
                text=True,
                check=check
            )
            return result

        except subprocess.CalledProcessError as e:
            raise GitException(
                f"Command failed: {' '.join(args)}",
                command=' '.join(args),
                stderr=e.stderr
            ) from e

    def _is_gh_cli_available(self) -> bool:
        """Check if gh CLI is installed and authenticated.

        Returns:
            True if gh CLI is available
        """
        try:
            result = subprocess.run(
                ['gh', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def _slugify(self, text: str, max_length: int = 50) -> str:
        """Convert text to URL-friendly slug.

        Args:
            text: Text to slugify
            max_length: Maximum slug length

        Returns:
            Slugified text

        Example:
            >>> git_manager._slugify("Implement Feature X!")
            'implement-feature-x'
        """
        # Convert to lowercase
        slug = text.lower()

        # Replace spaces and special chars with hyphens
        slug = re.sub(r'[^a-z0-9]+', '-', slug)

        # Remove leading/trailing hyphens
        slug = slug.strip('-')

        # Limit length
        slug = slug[:max_length]

        # Remove trailing hyphen if truncated
        slug = slug.rstrip('-')

        return slug


def create_git_manager_from_config(
    config_dict: Dict[str, Any],
    llm_interface: Any,
    state_manager: Any
) -> GitManager:
    """Factory function to create GitManager from configuration dictionary.

    Args:
        config_dict: Configuration dictionary with git settings
        llm_interface: LLM interface for commit message generation
        state_manager: State manager for task information

    Returns:
        Configured GitManager instance

    Example:
        >>> config = {
        ...     'enabled': True,
        ...     'auto_commit': True,
        ...     'commit_strategy': 'per_task'
        ... }
        >>> git_manager = create_git_manager_from_config(config, llm, state)
    """
    git_config = GitConfig(
        enabled=config_dict.get('enabled', False),
        auto_commit=config_dict.get('auto_commit', True),
        commit_strategy=config_dict.get('commit_strategy', 'per_task'),
        create_branch=config_dict.get('create_branch', True),
        branch_prefix=config_dict.get('branch_prefix', 'obra/task-'),
        auto_pr=config_dict.get('auto_pr', False),
        pr_base_branch=config_dict.get('pr_base_branch', 'main'),
        commit_message_template=config_dict.get('commit_message_template', 'semantic'),
        include_metadata=config_dict.get('include_metadata', True)
    )

    return GitManager(git_config, llm_interface, state_manager)
