"""Integration tests for CLI commands.

These tests verify that CLI commands work end-to-end with real configuration
and database operations. They would have caught the bugs we discovered.
"""

import pytest
import os
import tempfile
from pathlib import Path
from click.testing import CliRunner

from src.cli import cli
from src.core.state import StateManager
from src.core.config import Config


@pytest.fixture
def cli_runner():
    """Create a Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def test_runtime_dir(tmp_path):
    """Create a temporary runtime directory for testing."""
    runtime_dir = tmp_path / "obra-runtime"
    runtime_dir.mkdir()
    (runtime_dir / "data").mkdir()
    (runtime_dir / "logs").mkdir()
    (runtime_dir / "workspace").mkdir()
    return runtime_dir


@pytest.fixture
def test_config(test_runtime_dir, tmp_path):
    """Create a test configuration file."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    config_file = config_dir / "config.yaml"
    config_content = f"""
database:
  url: sqlite:///{test_runtime_dir}/data/test.db

agent:
  type: claude-code-local
  workspace_path: {test_runtime_dir}/workspace

llm:
  type: ollama
  model: qwen2.5-coder:32b
  api_url: http://localhost:11434

logging:
  file: {test_runtime_dir}/logs/test.log
  level: DEBUG
"""
    config_file.write_text(config_content)
    return config_file


class TestCLIConfigLoading:
    """Test that CLI properly loads configuration."""

    def test_cli_loads_config_without_explicit_path(self, cli_runner, monkeypatch, test_config):
        """Test that CLI loads config even without --config flag.

        This test would have caught the Config() vs Config.load() bug.
        """
        # Change to directory with config
        monkeypatch.chdir(test_config.parent.parent)

        result = cli_runner.invoke(cli, ['config', 'show'])

        # Should not crash and should show config
        assert result.exit_code == 0
        assert 'database' in result.output.lower() or result.output.strip() != '{}'

    def test_cli_loads_config_with_explicit_path(self, cli_runner, test_config):
        """Test that CLI loads config with --config flag."""
        result = cli_runner.invoke(cli, ['--config', str(test_config), 'config', 'show'])

        assert result.exit_code == 0
        # Config should be loaded
        assert result.output.strip() != '{}'


class TestCLIStatusCommand:
    """Test the status command."""

    def test_status_command_works(self, cli_runner, test_config):
        """Test status command doesn't crash.

        This test would have caught the list_tasks() missing method bug.
        """
        result = cli_runner.invoke(cli, ['--config', str(test_config), 'status'])

        assert result.exit_code == 0
        assert "Orchestrator Status" in result.output or "Projects:" in result.output

    def test_status_shows_correct_counts(self, cli_runner, test_config):
        """Test that status shows correct task counts."""
        # First create a project and task
        cli_runner.invoke(cli, ['--config', str(test_config), 'project', 'create', 'Test Project'])
        cli_runner.invoke(cli, ['--config', str(test_config), 'task', 'create', 'Test Task', '--project', '1'])

        # Check status
        result = cli_runner.invoke(cli, ['--config', str(test_config), 'status'])

        assert result.exit_code == 0
        assert "Projects: 1" in result.output
        assert "Total: 1" in result.output


class TestCLITaskCommands:
    """Test task-related CLI commands."""

    def test_task_list_all_projects(self, cli_runner, test_config):
        """Test listing tasks across all projects.

        This tests the list_tasks() method we added.
        """
        result = cli_runner.invoke(cli, ['--config', str(test_config), 'task', 'list'])

        assert result.exit_code == 0
        # Should say no tasks or show empty list, not crash
        assert "No tasks found" in result.output or "Tasks:" in result.output

    def test_task_list_by_project(self, cli_runner, test_config):
        """Test listing tasks for specific project.

        This tests the get_project_tasks() method we added.
        """
        # Create project first
        cli_runner.invoke(cli, ['--config', str(test_config), 'project', 'create', 'Test'])

        # List tasks for project
        result = cli_runner.invoke(cli, ['--config', str(test_config), 'task', 'list', '--project', '1'])

        assert result.exit_code == 0
        assert "No tasks found" in result.output or "Tasks:" in result.output

    def test_task_create_and_list(self, cli_runner, test_config):
        """Test creating and listing tasks."""
        # Create project
        result = cli_runner.invoke(cli, ['--config', str(test_config), 'project', 'create', 'Test Project'])
        assert result.exit_code == 0

        # Create task
        result = cli_runner.invoke(cli, [
            '--config', str(test_config),
            'task', 'create', 'Test Task',
            '--project', '1',
            '--description', 'Test description'
        ])
        assert result.exit_code == 0
        assert "Created task #1" in result.output

        # List tasks
        result = cli_runner.invoke(cli, ['--config', str(test_config), 'task', 'list'])
        assert result.exit_code == 0
        assert "Test Task" in result.output


class TestCLIProjectCommands:
    """Test project-related CLI commands."""

    def test_project_create(self, cli_runner, test_config):
        """Test creating a project."""
        result = cli_runner.invoke(cli, [
            '--config', str(test_config),
            'project', 'create', 'My Project',
            '--description', 'Test project'
        ])

        assert result.exit_code == 0
        assert "Created project #1" in result.output

    def test_project_list(self, cli_runner, test_config):
        """Test listing projects."""
        # Create a project first
        cli_runner.invoke(cli, ['--config', str(test_config), 'project', 'create', 'Test'])

        # List projects
        result = cli_runner.invoke(cli, ['--config', str(test_config), 'project', 'list'])

        assert result.exit_code == 0
        assert "Test" in result.output

    def test_project_show(self, cli_runner, test_config):
        """Test showing project details."""
        # Create a project
        cli_runner.invoke(cli, ['--config', str(test_config), 'project', 'create', 'Test'])

        # Show project
        result = cli_runner.invoke(cli, ['--config', str(test_config), 'project', 'show', '1'])

        assert result.exit_code == 0
        assert "Project #1" in result.output


class TestStateManagerMethods:
    """Direct tests for StateManager methods we added."""

    def test_list_tasks_all(self, test_runtime_dir):
        """Test list_tasks() with no filters."""
        db_url = f"sqlite:///{test_runtime_dir}/data/test.db"
        StateManager.reset_instance()
        state = StateManager.get_instance(db_url)

        # Should not crash
        tasks = state.list_tasks()
        assert isinstance(tasks, list)
        assert len(tasks) == 0  # No tasks yet

    def test_list_tasks_by_project(self, test_runtime_dir):
        """Test list_tasks() with project filter."""
        db_url = f"sqlite:///{test_runtime_dir}/data/test.db"
        StateManager.reset_instance()
        state = StateManager.get_instance(db_url)

        # Create project
        project = state.create_project(
            name='Test',
            description='Test project',
            working_dir=str(test_runtime_dir / 'workspace')
        )

        # Create task
        task = state.create_task(project.id, {
            'title': 'Test task',
            'description': 'Test',
            'priority': 5,
            'status': 'pending'
        })

        # List tasks for this project
        tasks = state.list_tasks(project_id=project.id)
        assert len(tasks) == 1
        assert tasks[0].id == task.id

    def test_list_tasks_by_status(self, test_runtime_dir):
        """Test list_tasks() with status filter."""
        db_url = f"sqlite:///{test_runtime_dir}/data/test.db"
        StateManager.reset_instance()
        state = StateManager.get_instance(db_url)

        # Create project and task
        project = state.create_project(
            name='Test',
            description='Test project',
            working_dir=str(test_runtime_dir / 'workspace')
        )
        task = state.create_task(project.id, {
            'title': 'Test task',
            'description': 'Test',
            'priority': 5,
            'status': 'pending'
        })

        # List pending tasks
        pending = state.list_tasks(status='pending')
        assert len(pending) == 1

        # List completed tasks (should be empty)
        completed = state.list_tasks(status='completed')
        assert len(completed) == 0

    def test_get_project_tasks(self, test_runtime_dir):
        """Test get_project_tasks() method."""
        db_url = f"sqlite:///{test_runtime_dir}/data/test.db"
        StateManager.reset_instance()
        state = StateManager.get_instance(db_url)

        # Create project
        project = state.create_project(
            name='Test',
            description='Test project',
            working_dir=str(test_runtime_dir / 'workspace')
        )

        # Create task
        state.create_task(project.id, {
            'title': 'Test task',
            'description': 'Test',
            'priority': 5,
            'status': 'pending'
        })

        # Get project tasks
        tasks = state.get_project_tasks(project.id)
        assert len(tasks) == 1
        assert tasks[0].title == 'Test task'


# Cleanup after each test to ensure StateManager singleton is reset
@pytest.fixture(autouse=True)
def cleanup_state_manager():
    """Reset StateManager singleton after each test."""
    yield
    StateManager.reset_instance()
