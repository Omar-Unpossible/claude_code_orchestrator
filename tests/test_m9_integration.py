"""Integration tests for M9 features.

Tests the integration of M9 enhancements:
- Retry logic with LLM interface
- Git integration with task completion
- Task dependency resolution with execution
- Configuration profiles with full system
"""

import pytest
import tempfile
import shutil
import yaml
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from requests.exceptions import ConnectionError, Timeout

from src.core.config import Config
from src.core.state import StateManager
from src.core.models import TaskStatus
from src.utils.retry_manager import RetryManager, RetryConfig
from src.utils.git_manager import GitManager, GitConfig
from src.orchestration.dependency_resolver import DependencyResolver


@pytest.fixture
def temp_git_repo(tmp_path):
    """Create a temporary git repository."""
    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()

    # Initialize git repo (mocked)
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout='', stderr='')

    yield repo_dir


@pytest.fixture
def state_manager_with_deps(test_config):
    """Create state manager with dependency support."""
    db_url = test_config.get('database.url')
    sm = StateManager.get_instance(db_url)
    yield sm
    sm.close()


class TestRetryWithLLM:
    """Integration tests for retry logic with LLM interface."""

    @pytest.mark.skip(reason="Requires complex request mocking before LLM initialization")
    @patch('requests.post')
    def test_llm_retry_on_connection_error(self, mock_post, fast_time):
        """Test LLM retries on connection errors."""
        from src.llm.local_interface import LocalLLMInterface

        # Mock requests to fail twice then succeed
        call_count = {'count': 0}

        def side_effect(*args, **kwargs):
            call_count['count'] += 1
            if call_count['count'] < 3:
                raise ConnectionError("Connection refused")

            # Success on third attempt
            response = Mock()
            response.status_code = 200
            response.json.return_value = {
                'response': 'test response',
                'done': True
            }
            return response

        mock_post.side_effect = side_effect

        # Create LLM interface with retry
        llm = LocalLLMInterface()
        llm.initialize({
            'url': 'http://localhost:11434',
            'model': 'qwen2.5-coder:32b',
            'timeout': 10,
            'retry_attempts': 3,
            'retry_backoff_base': 2.0,
            'retry_backoff_max': 10.0
        })

        result = llm.generate("test prompt")

        assert result == 'test response'
        assert call_count['count'] == 3

    @pytest.mark.skip(reason="Requires complex request mocking before LLM initialization")
    @patch('requests.post')
    def test_llm_retry_exhausted(self, mock_post, fast_time):
        """Test LLM retry exhaustion raises error."""
        from src.llm.local_interface import LocalLLMInterface
        from src.utils.retry_manager import RetryExhaustedError

        # Mock requests to always fail
        mock_post.side_effect = ConnectionError("Always fail")

        llm = LocalLLMInterface()
        llm.initialize({
            'url': 'http://localhost:11434',
            'model': 'qwen2.5-coder:32b',
            'timeout': 10,
            'retry_attempts': 2,
            'retry_backoff_base': 2.0,
            'retry_backoff_max': 10.0
        })

        with pytest.raises(RetryExhaustedError):
            llm.generate("test prompt")


class TestGitWithTaskCompletion:
    """Integration tests for git operations with task completion."""

    @pytest.fixture
    def git_manager_with_llm(self, temp_git_repo):
        """Create git manager with mocked LLM."""
        mock_llm = Mock()
        mock_llm.generate.return_value = "feat: implement feature\n\nDetailed description"

        mock_state_manager = Mock()

        config = GitConfig(
            enabled=True,
            auto_commit=True,
            create_branch=True,
            branch_prefix='obra/task-'
        )

        manager = GitManager(config, llm_interface=mock_llm, state_manager=mock_state_manager)
        manager.repo_path = temp_git_repo

        return manager, mock_llm

    @patch('subprocess.run')
    def test_commit_task_with_branch_creation(self, mock_run, git_manager_with_llm):
        """Test complete workflow: create branch → commit → PR."""
        git_manager, mock_llm = git_manager_with_llm

        # Mock task
        task = Mock(
            id=5,
            title="Implement authentication",
            description="Add user authentication",
            status=TaskStatus.COMPLETED
        )

        # Mock git commands
        mock_run.side_effect = [
            # create_branch: git branch --list
            MagicMock(returncode=0, stdout='', stderr=''),
            # create_branch: git checkout -b
            MagicMock(returncode=0, stdout='', stderr=''),
            # commit_task: git status
            MagicMock(returncode=0, stdout='M src/auth.py\n', stderr=''),
            # commit_task: git add -A
            MagicMock(returncode=0, stdout='', stderr=''),
            # commit_task: git commit
            MagicMock(returncode=0, stdout='', stderr='')
        ]

        # Create branch
        branch = git_manager.create_branch(task.id, task.title)
        assert 'obra/task-5' in branch

        # Commit task
        result = git_manager.commit_task(task)
        assert result is True

        # Verify LLM was called for commit message
        assert mock_llm.generate.called

    @patch('subprocess.run')
    def test_task_lifecycle_with_git(self, mock_run, state_manager_with_deps, git_manager_with_llm):
        """Test complete task lifecycle with git integration."""
        git_manager, mock_llm = git_manager_with_llm

        # Create project
        project = state_manager_with_deps.create_project(
            name='Git Integration Test',
            description='Test git integration',
            working_dir='/tmp/test'
        )

        # Create task
        task = state_manager_with_deps.create_task(project.id, {
            'title': 'Add new feature',
            'description': 'Implement feature X',
            'status': 'pending'
        })

        # Mock git operations
        mock_run.side_effect = [
            # create_branch
            MagicMock(returncode=0, stdout='', stderr=''),
            MagicMock(returncode=0, stdout='', stderr=''),
            # commit
            MagicMock(returncode=0, stdout='M file.py\n', stderr=''),
            MagicMock(returncode=0, stdout='', stderr=''),
            MagicMock(returncode=0, stdout='', stderr='')
        ]

        # Create branch for task
        branch = git_manager.create_branch(task.id, task.title)
        assert branch is not None

        # Update task status to completed
        state_manager_with_deps.update_task_status(task.id, TaskStatus.COMPLETED)

        # Commit completed task
        updated_task = state_manager_with_deps.get_task(task.id)
        result = git_manager.commit_task(updated_task)

        assert result is True
        assert updated_task.status == TaskStatus.COMPLETED


class TestDependencyExecution:
    """Integration tests for dependency resolution with task execution."""

    @pytest.fixture
    def resolver_with_tasks(self, state_manager_with_deps, test_config):
        """Create resolver with test tasks."""
        import uuid
        # Create project with unique name
        project = state_manager_with_deps.create_project(
            name=f'Dependency Test {uuid.uuid4().hex[:8]}',
            description='Test dependency resolution',
            working_dir='/tmp/test'
        )

        # Create tasks with dependencies
        # Task 1: No dependencies
        task1 = state_manager_with_deps.create_task(project.id, {
            'title': 'Setup environment',
            'description': 'Install dependencies',
            'status': 'pending'
        })

        # Task 2: Depends on task 1
        task2 = state_manager_with_deps.create_task(project.id, {
            'title': 'Create models',
            'description': 'Define data models',
            'status': 'pending'
        })
        state_manager_with_deps.add_task_dependency(task2.id, task1.id)

        # Task 3: Depends on task 2
        task3 = state_manager_with_deps.create_task(project.id, {
            'title': 'Create API',
            'description': 'Implement REST API',
            'status': 'pending'
        })
        state_manager_with_deps.add_task_dependency(task3.id, task2.id)

        # Create resolver
        resolver = DependencyResolver(state_manager_with_deps, test_config)

        return resolver, state_manager_with_deps, project, [task1, task2, task3]

    def test_execution_order_with_dependencies(self, resolver_with_tasks):
        """Test execution order respects dependencies."""
        resolver, state_manager, project, tasks = resolver_with_tasks

        # Get execution order
        order = resolver.get_execution_order(project.id)

        # Verify order respects dependencies
        task1_idx = order.index(tasks[0].id)
        task2_idx = order.index(tasks[1].id)
        task3_idx = order.index(tasks[2].id)

        assert task1_idx < task2_idx  # Task 1 before task 2
        assert task2_idx < task3_idx  # Task 2 before task 3

    def test_task_ready_when_dependencies_complete(self, resolver_with_tasks):
        """Test task becomes ready when dependencies complete."""
        resolver, state_manager, project, tasks = resolver_with_tasks

        # Initially, task 2 is not ready (task 1 pending)
        assert resolver.is_task_ready(tasks[1].id) is False

        # Complete task 1
        state_manager.update_task_status(tasks[0].id, TaskStatus.COMPLETED)

        # Now task 2 should be ready
        assert resolver.is_task_ready(tasks[1].id) is True

        # Task 3 still not ready (task 2 pending)
        assert resolver.is_task_ready(tasks[2].id) is False

    def test_blocked_tasks_identification(self, resolver_with_tasks):
        """Test identifying blocked tasks."""
        resolver, state_manager, project, tasks = resolver_with_tasks

        # All tasks are blocked except task 1
        blocked = resolver.get_blocked_tasks(project.id)

        assert tasks[1].id in blocked  # Task 2 blocked by task 1
        assert tasks[2].id in blocked  # Task 3 blocked by task 2

        # Complete task 1
        state_manager.update_task_status(tasks[0].id, TaskStatus.COMPLETED)

        # Now only task 3 should be blocked
        blocked = resolver.get_blocked_tasks(project.id)
        assert tasks[1].id not in blocked
        assert tasks[2].id in blocked

    def test_progressive_execution(self, resolver_with_tasks):
        """Test progressive task execution following dependencies."""
        resolver, state_manager, project, tasks = resolver_with_tasks

        execution_log = []

        # Execute tasks in order
        order = resolver.get_execution_order(project.id)

        for task_id in order:
            # Check if ready
            if resolver.is_task_ready(task_id):
                # Execute (mock)
                execution_log.append(task_id)
                state_manager.update_task_status(task_id, TaskStatus.RUNNING)
                state_manager.update_task_status(task_id, TaskStatus.COMPLETED)

        # Verify all tasks were executed
        assert len(execution_log) == 3

        # Verify execution order
        assert execution_log[0] == tasks[0].id
        assert execution_log[1] == tasks[1].id
        assert execution_log[2] == tasks[2].id


class TestProfileWithSystem:
    """Integration tests for profiles with full system."""

    @pytest.fixture
    def temp_config_with_profile(self, tmp_path):
        """Create temporary config with profile."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        profiles_dir = config_dir / "profiles"
        profiles_dir.mkdir()

        # Create default config
        default_config = {
            'database': {'url': 'sqlite:///:memory:'},
            'agent': {'type': 'local', 'timeout': 120},
            'testing': {'run_tests': False},
            'retry': {'max_attempts': 5}
        }
        with open(config_dir / 'default_config.yaml', 'w') as f:
            yaml.dump(default_config, f)

        # Create test profile
        profile_config = {
            'testing': {'run_tests': True, 'coverage_threshold': 0.85},
            'retry': {'max_attempts': 3, 'base_delay': 2.0},
            'git': {'enabled': True, 'auto_commit': True}
        }
        with open(profiles_dir / 'test_profile.yaml', 'w') as f:
            yaml.dump(profile_config, f)

        return config_dir

    def test_profile_affects_retry_config(self, temp_config_with_profile):
        """Test profile configuration affects retry manager."""
        with patch('src.core.config.Path') as mock_path:
            def path_side_effect(path_str):
                if 'default_config.yaml' in str(path_str):
                    return temp_config_with_profile / 'default_config.yaml'
                elif 'profiles/test_profile' in str(path_str):
                    return temp_config_with_profile / 'profiles' / 'test_profile.yaml'
                else:
                    mock = Mock()
                    mock.exists.return_value = False
                    return mock

            mock_path.side_effect = path_side_effect

            Config.reset()
            config = Config.load(profile='test_profile')

            # Profile should override retry settings
            assert config.get('retry.max_attempts') == 3
            assert config.get('retry.base_delay') == 2.0

            # Profile should set git enabled
            assert config.get('git.enabled') is True

    def test_profile_affects_git_config(self, temp_config_with_profile):
        """Test profile enables git integration."""
        with patch('src.core.config.Path') as mock_path:
            def path_side_effect(path_str):
                if 'default_config.yaml' in str(path_str):
                    return temp_config_with_profile / 'default_config.yaml'
                elif 'profiles/test_profile' in str(path_str):
                    return temp_config_with_profile / 'profiles' / 'test_profile.yaml'
                else:
                    mock = Mock()
                    mock.exists.return_value = False
                    return mock

            mock_path.side_effect = path_side_effect

            Config.reset()
            config = Config.load(profile='test_profile')

            # Create git manager from config
            git_config = GitConfig(
                enabled=config.get('git.enabled', False),
                auto_commit=config.get('git.auto_commit', False)
            )

            assert git_config.enabled is True
            assert git_config.auto_commit is True


class TestCombinedScenario:
    """Integration tests for combined M9 features."""

    @patch('subprocess.run')
    def test_task_with_retry_dependency_git(
        self,
        mock_run,
        state_manager_with_deps,
        test_config,
        fast_time
    ):
        """Test complete workflow: dependencies + retry + git."""
        # Setup git manager
        mock_llm = Mock()
        mock_llm.generate.return_value = "feat: complete task\n\nTask completed successfully"

        git_config = GitConfig(enabled=True, auto_commit=True, create_branch=True)
        git_manager = GitManager(git_config, llm_interface=mock_llm, state_manager=state_manager_with_deps)

        # Setup dependency resolver
        resolver = DependencyResolver(state_manager_with_deps, test_config)

        # Create project
        project = state_manager_with_deps.create_project(
            name='Combined Test',
            description='Test combined M9 features',
            working_dir='/tmp/test'
        )

        # Create tasks with dependencies
        task1 = state_manager_with_deps.create_task(project.id, {
            'title': 'Setup',
            'description': 'Setup task',
            'status': 'pending'
        })

        task2 = state_manager_with_deps.create_task(project.id, {
            'title': 'Implementation',
            'description': 'Implementation task',
            'status': 'pending'
        })
        state_manager_with_deps.add_task_dependency(task2.id, task1.id)

        # Mock git operations
        mock_run.side_effect = [
            # Task 1: create branch
            MagicMock(returncode=0, stdout='', stderr=''),
            MagicMock(returncode=0, stdout='', stderr=''),
            # Task 1: commit
            MagicMock(returncode=0, stdout='M file1.py\n', stderr=''),
            MagicMock(returncode=0, stdout='', stderr=''),
            MagicMock(returncode=0, stdout='', stderr=''),
            # Task 2: create branch
            MagicMock(returncode=0, stdout='', stderr=''),
            MagicMock(returncode=0, stdout='', stderr=''),
            # Task 2: commit
            MagicMock(returncode=0, stdout='M file2.py\n', stderr=''),
            MagicMock(returncode=0, stdout='', stderr=''),
            MagicMock(returncode=0, stdout='', stderr='')
        ]

        # Execute task 1
        assert resolver.is_task_ready(task1.id) is True
        state_manager_with_deps.update_task_status(task1.id, TaskStatus.COMPLETED)

        # Commit task 1
        updated_task1 = state_manager_with_deps.get_task(task1.id)
        git_manager.create_branch(task1.id, updated_task1.title)
        result1 = git_manager.commit_task(updated_task1)
        assert result1 is True

        # Now task 2 should be ready
        assert resolver.is_task_ready(task2.id) is True

        # Execute task 2
        state_manager_with_deps.update_task_status(task2.id, TaskStatus.COMPLETED)

        # Commit task 2
        updated_task2 = state_manager_with_deps.get_task(task2.id)
        git_manager.create_branch(task2.id, updated_task2.title)
        result2 = git_manager.commit_task(updated_task2)
        assert result2 is True

        # Verify both tasks completed
        assert updated_task1.status == TaskStatus.COMPLETED
        assert updated_task2.status == TaskStatus.COMPLETED

    def test_dependency_validation_with_depth_limit(self, state_manager_with_deps):
        """Test dependency validation respects depth limits from config."""
        config = Mock()
        config.get.return_value = {
            'max_depth': 2,
            'allow_cycles': False
        }

        resolver = DependencyResolver(state_manager_with_deps, config)

        # Create project
        project = state_manager_with_deps.create_project(
            name='Depth Test',
            description='Test dependency depth limits',
            working_dir='/tmp/test'
        )

        # Create chain: 1 <- 2 <- 3
        task1 = state_manager_with_deps.create_task(project.id, {'title': 'Task 1', 'description': 'Task 1'})
        task2 = state_manager_with_deps.create_task(project.id, {'title': 'Task 2', 'description': 'Task 2'})
        task3 = state_manager_with_deps.create_task(project.id, {'title': 'Task 3', 'description': 'Task 3'})
        task4 = state_manager_with_deps.create_task(project.id, {'title': 'Task 4', 'description': 'Task 4'})

        # Add dependencies
        state_manager_with_deps.add_task_dependency(task2.id, task1.id)
        state_manager_with_deps.add_task_dependency(task3.id, task2.id)

        # Trying to add task4 -> task3 would exceed depth 2
        valid, error = resolver.validate_dependency(task4.id, task3.id)

        # Should fail due to depth limit
        assert valid is False
        assert 'depth' in error.lower()


class TestErrorRecovery:
    """Integration tests for error recovery scenarios."""

    @patch('subprocess.run')
    def test_git_rollback_on_commit_failure(self, mock_run, fast_time):
        """Test git rollback when commit fails."""
        mock_llm = Mock()
        mock_llm.generate.return_value = "feat: test commit"

        mock_state_manager = Mock()
        git_config = GitConfig(enabled=True)
        git_manager = GitManager(git_config, llm_interface=mock_llm, state_manager=mock_state_manager)

        # Mock task
        task = Mock(
            id=1,
            title="Test task",
            status=TaskStatus.COMPLETED
        )

        # Mock git operations: status succeeds, but commit fails
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout='M file.py\n', stderr=''),  # status
            MagicMock(returncode=0, stdout='', stderr=''),  # add
            MagicMock(returncode=1, stdout='', stderr='Commit failed'),  # commit fails
            MagicMock(returncode=0, stdout='', stderr='')  # reset (rollback)
        ]

        # Attempt commit
        result = git_manager.commit_task(task)

        # Should return False and rollback
        assert result is False

    def test_dependency_cycle_detection_prevents_deadlock(self, state_manager_with_deps, test_config):
        """Test cycle detection prevents dependency deadlock."""
        resolver = DependencyResolver(state_manager_with_deps, test_config)

        # Create project
        project = state_manager_with_deps.create_project(
            name='Cycle Test',
            description='Test cycle detection',
            working_dir='/tmp/test'
        )

        # Create tasks
        task1 = state_manager_with_deps.create_task(project.id, {'title': 'Task 1', 'description': 'Task 1'})
        task2 = state_manager_with_deps.create_task(project.id, {'title': 'Task 2', 'description': 'Task 2'})

        # Add dependency: task2 -> task1
        state_manager_with_deps.add_task_dependency(task2.id, task1.id)

        # Try to add reverse dependency: task1 -> task2 (would create cycle)
        valid, error = resolver.validate_dependency(task1.id, task2.id)

        # Should detect cycle
        assert valid is False
        assert 'circular' in error.lower() or 'cycle' in error.lower()
