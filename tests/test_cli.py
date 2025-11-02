"""Tests for CLI interface - Click-based commands."""

import pytest
from click.testing import CliRunner
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from src.cli import cli
from src.core.state import StateManager


@pytest.fixture
def runner():
    """Create Click test runner."""
    return CliRunner()


@pytest.fixture
def isolated_fs(runner):
    """Create isolated filesystem for testing."""
    with runner.isolated_filesystem():
        yield


@pytest.fixture
def state_manager():
    """Create test state manager."""
    sm = StateManager.get_instance('sqlite:///:memory:')
    yield sm
    sm.close()


class TestCLIBasics:
    """Test basic CLI functionality."""

    def test_cli_help(self, runner):
        """Test CLI help command."""
        result = runner.invoke(cli, ['--help'])

        assert result.exit_code == 0
        assert 'Claude Code Orchestrator' in result.output

    def test_cli_verbose_flag(self, runner):
        """Test verbose flag."""
        result = runner.invoke(cli, ['--verbose', '--help'])

        assert result.exit_code == 0


class TestInitCommand:
    """Test init command."""

    def test_init_creates_database(self, runner, isolated_fs):
        """Test init creates database."""
        result = runner.invoke(cli, ['init'])

        assert result.exit_code == 0
        assert 'initialized successfully' in result.output

    def test_init_creates_config(self, runner, isolated_fs):
        """Test init creates default config."""
        result = runner.invoke(cli, ['init'])

        assert result.exit_code == 0

        # Check config file was created
        config_file = Path('config/config.yaml')
        assert config_file.exists()

    def test_init_with_custom_db(self, runner, isolated_fs):
        """Test init with custom database URL."""
        result = runner.invoke(cli, ['init', '--db-url', 'sqlite:///custom.db'])

        assert result.exit_code == 0
        assert 'custom.db' in result.output


class TestProjectCommands:
    """Test project management commands."""

    def test_project_create(self, runner, isolated_fs):
        """Test creating a project."""
        # Initialize first
        runner.invoke(cli, ['init'])

        # Create project
        result = runner.invoke(cli, ['project', 'create', 'Test Project'])

        assert result.exit_code == 0
        assert 'Created project' in result.output
        assert 'Test Project' in result.output

    def test_project_create_with_description(self, runner, isolated_fs):
        """Test creating project with description."""
        runner.invoke(cli, ['init'])

        result = runner.invoke(cli, [
            'project', 'create', 'My Project',
            '--description', 'This is a test project'
        ])

        assert result.exit_code == 0
        assert 'Created project' in result.output

    def test_project_list_empty(self, runner, isolated_fs):
        """Test listing projects when none exist."""
        runner.invoke(cli, ['init'])

        result = runner.invoke(cli, ['project', 'list'])

        assert result.exit_code == 0
        assert 'No projects found' in result.output

    def test_project_list_with_projects(self, runner, isolated_fs):
        """Test listing projects."""
        runner.invoke(cli, ['init'])
        runner.invoke(cli, ['project', 'create', 'Project 1'])
        runner.invoke(cli, ['project', 'create', 'Project 2'])

        result = runner.invoke(cli, ['project', 'list'])

        assert result.exit_code == 0
        assert 'Project 1' in result.output
        assert 'Project 2' in result.output

    def test_project_show(self, runner, isolated_fs):
        """Test showing project details."""
        runner.invoke(cli, ['init'])
        runner.invoke(cli, ['project', 'create', 'Test Project'])

        result = runner.invoke(cli, ['project', 'show', '1'])

        assert result.exit_code == 0
        assert 'Test Project' in result.output

    def test_project_show_not_found(self, runner, isolated_fs):
        """Test showing non-existent project."""
        runner.invoke(cli, ['init'])

        result = runner.invoke(cli, ['project', 'show', '999'])

        assert result.exit_code == 1
        assert 'not found' in result.output


class TestTaskCommands:
    """Test task management commands."""

    def test_task_create(self, runner, isolated_fs):
        """Test creating a task."""
        runner.invoke(cli, ['init'])
        runner.invoke(cli, ['project', 'create', 'Test Project'])

        result = runner.invoke(cli, [
            'task', 'create', 'Implement feature',
            '--project', '1',
            '--description', 'Test task',
            '--priority', '8'
        ])

        assert result.exit_code == 0
        assert 'Created task' in result.output
        assert 'Implement feature' in result.output

    def test_task_create_without_project(self, runner, isolated_fs):
        """Test creating task without project fails."""
        runner.invoke(cli, ['init'])

        result = runner.invoke(cli, ['task', 'create', 'Test Task'])

        assert result.exit_code != 0

    def test_task_list_empty(self, runner, isolated_fs):
        """Test listing tasks when none exist."""
        runner.invoke(cli, ['init'])

        result = runner.invoke(cli, ['task', 'list'])

        assert result.exit_code == 0
        assert 'No tasks found' in result.output

    def test_task_list_with_tasks(self, runner, isolated_fs):
        """Test listing tasks."""
        runner.invoke(cli, ['init'])
        runner.invoke(cli, ['project', 'create', 'Project'])
        runner.invoke(cli, ['task', 'create', 'Task 1', '--project', '1'])
        runner.invoke(cli, ['task', 'create', 'Task 2', '--project', '1'])

        result = runner.invoke(cli, ['task', 'list'])

        assert result.exit_code == 0
        assert 'Task 1' in result.output
        assert 'Task 2' in result.output

    def test_task_list_filter_by_project(self, runner, isolated_fs):
        """Test filtering tasks by project."""
        runner.invoke(cli, ['init'])
        runner.invoke(cli, ['project', 'create', 'Project 1'])
        runner.invoke(cli, ['project', 'create', 'Project 2'])
        runner.invoke(cli, ['task', 'create', 'Task P1', '--project', '1'])
        runner.invoke(cli, ['task', 'create', 'Task P2', '--project', '2'])

        result = runner.invoke(cli, ['task', 'list', '--project', '1'])

        assert result.exit_code == 0
        assert 'Task P1' in result.output
        assert 'Task P2' not in result.output

    def test_task_list_filter_by_status(self, runner, isolated_fs):
        """Test filtering tasks by status."""
        runner.invoke(cli, ['init'])
        runner.invoke(cli, ['project', 'create', 'Project'])
        runner.invoke(cli, ['task', 'create', 'Task', '--project', '1'])

        result = runner.invoke(cli, ['task', 'list', '--status', 'pending'])

        assert result.exit_code == 0


class TestExecuteCommand:
    """Test task execution command."""

    @patch('src.cli.Orchestrator')
    def test_execute_task(self, mock_orchestrator_class, runner, isolated_fs):
        """Test executing a task."""
        # Setup mocks
        mock_orch = Mock()
        mock_orch.execute_task.return_value = {
            'status': 'completed',
            'iterations': 3,
            'quality_score': 0.85,
            'confidence': 0.9
        }
        mock_orchestrator_class.return_value = mock_orch

        runner.invoke(cli, ['init'])
        runner.invoke(cli, ['project', 'create', 'Project'])
        runner.invoke(cli, ['task', 'create', 'Task', '--project', '1'])

        result = runner.invoke(cli, ['task', 'execute', '1'])

        assert result.exit_code == 0
        assert 'completed successfully' in result.output

    @patch('src.cli.Orchestrator')
    def test_execute_task_escalated(self, mock_orchestrator_class, runner, isolated_fs):
        """Test executing task that gets escalated."""
        mock_orch = Mock()
        mock_orch.execute_task.return_value = {
            'status': 'escalated',
            'reason': 'Confidence too low',
            'iterations': 2
        }
        mock_orchestrator_class.return_value = mock_orch

        runner.invoke(cli, ['init'])
        runner.invoke(cli, ['project', 'create', 'Project'])
        runner.invoke(cli, ['task', 'create', 'Task', '--project', '1'])

        result = runner.invoke(cli, ['task', 'execute', '1'])

        assert result.exit_code == 0
        assert 'escalated' in result.output

    @patch('src.cli.Orchestrator')
    def test_execute_with_max_iterations(self, mock_orchestrator_class, runner, isolated_fs):
        """Test execute with custom max iterations."""
        mock_orch = Mock()
        mock_orch.execute_task.return_value = {
            'status': 'completed',
            'iterations': 1
        }
        mock_orchestrator_class.return_value = mock_orch

        runner.invoke(cli, ['init'])
        runner.invoke(cli, ['project', 'create', 'Project'])
        runner.invoke(cli, ['task', 'create', 'Task', '--project', '1'])

        result = runner.invoke(cli, ['task', 'execute', '1', '--max-iterations', '5'])

        assert result.exit_code == 0


class TestRunCommand:
    """Test continuous run command."""

    @patch('src.cli.Orchestrator')
    def test_run_command(self, mock_orchestrator_class, runner, isolated_fs):
        """Test running orchestrator."""
        mock_orch = Mock()
        mock_orch.run.side_effect = KeyboardInterrupt()
        mock_orchestrator_class.return_value = mock_orch

        runner.invoke(cli, ['init'])

        result = runner.invoke(cli, ['run'])

        # Should handle keyboard interrupt gracefully
        assert result.exit_code == 0


class TestStatusCommand:
    """Test status command."""

    def test_status_command(self, runner, isolated_fs):
        """Test getting orchestrator status."""
        runner.invoke(cli, ['init'])
        runner.invoke(cli, ['project', 'create', 'Project'])
        runner.invoke(cli, ['task', 'create', 'Task', '--project', '1'])

        result = runner.invoke(cli, ['status'])

        assert result.exit_code == 0
        assert 'Orchestrator Status' in result.output
        assert 'Projects:' in result.output
        assert 'Tasks:' in result.output


class TestInteractiveCommand:
    """Test interactive mode command."""

    def test_interactive_not_implemented_gracefully(self, runner, isolated_fs):
        """Test interactive command handles missing implementation."""
        runner.invoke(cli, ['init'])

        # Will fail because InteractiveMode not found
        result = runner.invoke(cli, ['interactive'])

        # Should exit with error
        assert result.exit_code == 1


class TestConfigCommands:
    """Test configuration commands."""

    def test_config_show(self, runner, isolated_fs):
        """Test showing configuration."""
        runner.invoke(cli, ['init'])

        result = runner.invoke(cli, ['config', 'show'])

        assert result.exit_code == 0
        assert 'Configuration' in result.output

    def test_config_validate_valid(self, runner, isolated_fs):
        """Test validating valid configuration."""
        runner.invoke(cli, ['init'])

        result = runner.invoke(cli, ['config', 'validate'])

        assert result.exit_code == 0
        assert 'valid' in result.output

    def test_config_validate_missing_settings(self, runner, isolated_fs):
        """Test validating config with missing settings."""
        # Create config dir but with incomplete config
        Path('config').mkdir(exist_ok=True)
        Path('config/config.yaml').write_text('# Empty config')

        result = runner.invoke(cli, ['-c', 'config/config.yaml', 'config', 'validate'])

        # Should fail validation
        assert result.exit_code == 1


class TestErrorHandling:
    """Test CLI error handling."""

    def test_invalid_command(self, runner):
        """Test invalid command."""
        result = runner.invoke(cli, ['invalid-command'])

        assert result.exit_code != 0

    def test_missing_required_argument(self, runner, isolated_fs):
        """Test missing required argument."""
        runner.invoke(cli, ['init'])

        result = runner.invoke(cli, ['project', 'create'])

        # Click should show usage
        assert result.exit_code != 0


class TestVerboseMode:
    """Test verbose logging."""

    def test_verbose_logging(self, runner, isolated_fs):
        """Test verbose flag enables detailed logging."""
        result = runner.invoke(cli, ['--verbose', 'init'])

        # Should complete successfully with verbose output
        assert result.exit_code == 0
