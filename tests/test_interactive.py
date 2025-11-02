"""Tests for InteractiveMode - REPL for orchestrator control."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from io import StringIO

from src.interactive import InteractiveMode
from src.core.config import Config
from src.core.state import StateManager


# Use test_config from conftest.py


@pytest.fixture
def state_manager():
    """Create test state manager."""
    sm = StateManager.get_instance('sqlite:///:memory:')
    yield sm
    sm.close()


@pytest.fixture
def interactive(test_config):
    """Create interactive mode instance."""
    return InteractiveMode(test_config)


class TestInteractiveModeInitialization:
    """Test InteractiveMode initialization."""

    def test_initialization(self, test_config):
        """Test interactive mode initializes."""
        mode = InteractiveMode(test_config)

        assert mode.config is test_config
        assert mode.orchestrator is None
        assert mode.state_manager is None
        assert mode.current_project is None
        assert mode.running is False
        assert isinstance(mode.commands, dict)

    def test_command_mapping(self, interactive):
        """Test commands are mapped correctly."""
        assert 'help' in interactive.commands
        assert 'exit' in interactive.commands
        assert 'project' in interactive.commands
        assert 'task' in interactive.commands
        assert 'execute' in interactive.commands
        assert 'status' in interactive.commands


class TestCommandExecution:
    """Test command execution."""

    def test_execute_help_command(self, interactive, capsys):
        """Test help command."""
        interactive.cmd_help([])

        captured = capsys.readouterr()
        assert 'Available Commands' in captured.out

    def test_execute_exit_command(self, interactive):
        """Test exit command."""
        interactive.running = True
        interactive.cmd_exit([])

        assert interactive.running is False

    def test_execute_history_command_empty(self, interactive, capsys):
        """Test history command with no history."""
        interactive.cmd_history([])

        captured = capsys.readouterr()
        assert 'No command history' in captured.out

    def test_execute_history_command_with_history(self, interactive, capsys):
        """Test history command with commands."""
        interactive.history = ['help', 'project list', 'exit']
        interactive.cmd_history([])

        captured = capsys.readouterr()
        assert 'help' in captured.out
        assert 'project list' in captured.out


class TestProjectCommands:
    """Test project management commands."""

    @patch.object(StateManager, 'create_project')
    def test_project_create(self, mock_create, interactive, capsys, state_manager):
        """Test creating a project."""
        interactive.state_manager = state_manager

        # Mock the create_project to return a mock project
        mock_project = Mock()
        mock_project.id = 1
        mock_create.return_value = mock_project

        interactive._project_create(['TestProject', 'description'])

        captured = capsys.readouterr()
        assert 'Created project' in captured.out
        assert interactive.current_project == 1

    @patch.object(StateManager, 'list_projects')
    def test_project_list_empty(self, mock_list, interactive, capsys, state_manager):
        """Test listing projects when none exist."""
        interactive.state_manager = state_manager
        mock_list.return_value = []

        interactive._project_list()

        captured = capsys.readouterr()
        assert 'No projects found' in captured.out

    @patch.object(StateManager, 'list_projects')
    def test_project_list_with_projects(self, mock_list, interactive, capsys, state_manager):
        """Test listing projects."""
        interactive.state_manager = state_manager

        # Create mock projects
        project1 = Mock()
        project1.id = 1
        project1.name = 'Project 1'
        project1.description = 'Test'
        project1.status = 'active'

        project2 = Mock()
        project2.id = 2
        project2.name = 'Project 2'
        project2.description = 'Test'
        project2.status = 'active'

        mock_list.return_value = [project1, project2]

        interactive._project_list()

        captured = capsys.readouterr()
        assert 'Project 1' in captured.out
        assert 'Project 2' in captured.out

    @patch.object(StateManager, 'get_project')
    @patch.object(StateManager, 'get_project_tasks')
    def test_project_show(self, mock_tasks, mock_get, interactive, capsys, state_manager):
        """Test showing project details."""
        interactive.state_manager = state_manager

        # Mock project
        project = Mock()
        project.id = 1
        project.name = 'Test Project'
        project.description = 'Test'
        project.working_dir = '/tmp'
        project.status = 'active'
        project.created_at = '2025-01-01'
        project.updated_at = '2025-01-01'

        mock_get.return_value = project
        mock_tasks.return_value = []

        interactive._project_show(['1'])

        captured = capsys.readouterr()
        assert 'Test Project' in captured.out

    @patch.object(StateManager, 'get_project')
    def test_project_show_not_found(self, mock_get, interactive, capsys, state_manager):
        """Test showing non-existent project."""
        interactive.state_manager = state_manager
        mock_get.return_value = None

        interactive._project_show(['999'])

        captured = capsys.readouterr()
        assert 'not found' in captured.out


class TestTaskCommands:
    """Test task management commands."""

    @patch.object(StateManager, 'create_task')
    def test_task_create(self, mock_create, interactive, capsys, state_manager):
        """Test creating a task."""
        interactive.state_manager = state_manager
        interactive.current_project = 1

        # Mock task
        mock_task = Mock()
        mock_task.id = 1
        mock_create.return_value = mock_task

        interactive._task_create(['Test Task'])

        captured = capsys.readouterr()
        assert 'Created task' in captured.out

    def test_task_create_no_project(self, interactive, capsys, state_manager):
        """Test creating task without current project."""
        interactive.state_manager = state_manager
        interactive.current_project = None

        interactive._task_create(['Test Task'])

        captured = capsys.readouterr()
        assert 'No project selected' in captured.out

    @patch.object(StateManager, 'list_tasks')
    def test_task_list_empty(self, mock_list, interactive, capsys, state_manager):
        """Test listing tasks when none exist."""
        interactive.state_manager = state_manager
        mock_list.return_value = []

        interactive._task_list()

        captured = capsys.readouterr()
        assert 'No tasks found' in captured.out

    @patch.object(StateManager, 'get_project_tasks')
    def test_task_list_with_project(self, mock_tasks, interactive, capsys, state_manager):
        """Test listing tasks for current project."""
        interactive.state_manager = state_manager
        interactive.current_project = 1

        # Mock tasks
        task = Mock()
        task.id = 1
        task.title = 'Test Task'
        task.status = 'pending'
        task.project_id = 1
        task.priority = 5

        mock_tasks.return_value = [task]

        interactive._task_list()

        captured = capsys.readouterr()
        assert 'Test Task' in captured.out

    @patch.object(StateManager, 'get_task')
    def test_task_show(self, mock_get, interactive, capsys, state_manager):
        """Test showing task details."""
        interactive.state_manager = state_manager

        # Mock task
        task = Mock()
        task.id = 1
        task.title = 'Test Task'
        task.description = 'Test'
        task.project_id = 1
        task.status = 'pending'
        task.priority = 5
        task.created_at = '2025-01-01'
        task.updated_at = '2025-01-01'

        mock_get.return_value = task

        interactive._task_show(['1'])

        captured = capsys.readouterr()
        assert 'Test Task' in captured.out


class TestExecutionCommands:
    """Test execution commands."""

    def test_execute_task(self, interactive, capsys, state_manager, fast_time):
        """Test executing a task."""
        # Initialize interactive mode
        interactive.state_manager = state_manager

        # Create mock orchestrator
        mock_orch = Mock()
        mock_orch.execute_task.return_value = {
            'status': 'completed',
            'iterations': 2,
            'quality_score': 0.85,
            'confidence': 0.9
        }
        interactive.orchestrator = mock_orch

        # Create a task
        project = state_manager.create_project({'name': 'Test', 'working_dir': '/tmp'})
        task = state_manager.create_task(project.id, {'title': 'Test', 'status': 'pending'})

        interactive.cmd_execute([str(task.id)])

        captured = capsys.readouterr()
        assert 'completed successfully' in captured.out

    def test_execute_task_escalated(self, interactive, capsys, state_manager, fast_time):
        """Test executing task that gets escalated."""
        interactive.state_manager = state_manager

        mock_orch = Mock()
        mock_orch.execute_task.return_value = {
            'status': 'escalated',
            'reason': 'Low confidence',
            'iterations': 3
        }
        interactive.orchestrator = mock_orch

        project = state_manager.create_project({'name': 'Test', 'working_dir': '/tmp'})
        task = state_manager.create_task(project.id, {'title': 'Test', 'status': 'pending'})

        interactive.cmd_execute([str(task.id)])

        captured = capsys.readouterr()
        assert 'escalated' in captured.out

    def test_execute_invalid_task_id(self, interactive, capsys, state_manager):
        """Test executing with invalid task ID."""
        interactive.state_manager = state_manager
        interactive.orchestrator = Mock()

        interactive.cmd_execute(['invalid'])

        captured = capsys.readouterr()
        assert 'Invalid task ID' in captured.out

    def test_status_command(self, interactive, capsys, state_manager, fast_time):
        """Test status command."""
        interactive.state_manager = state_manager

        # Mock orchestrator status
        mock_orch = Mock()
        mock_orch.get_status.return_value = {
            'state': 'initialized',
            'current_task': None,
            'current_project': None,
            'iteration_count': 0,
            'uptime_seconds': 60.0,
            'components': {
                'state_manager': True,
                'agent': True,
                'llm': True
            }
        }
        interactive.orchestrator = mock_orch

        interactive.cmd_status([])

        captured = capsys.readouterr()
        assert 'Orchestrator Status' in captured.out


class TestUseCommand:
    """Test use command for setting current project."""

    @patch.object(StateManager, 'get_project')
    def test_use_valid_project(self, mock_get, interactive, capsys, state_manager):
        """Test setting current project."""
        interactive.state_manager = state_manager

        # Mock project
        project = Mock()
        project.id = 1
        project.name = 'Test Project'

        mock_get.return_value = project

        interactive.cmd_use(['1'])

        assert interactive.current_project == 1
        captured = capsys.readouterr()
        assert 'Using project' in captured.out

    @patch.object(StateManager, 'get_project')
    def test_use_invalid_project(self, mock_get, interactive, capsys, state_manager):
        """Test setting invalid project."""
        interactive.state_manager = state_manager
        mock_get.return_value = None

        interactive.cmd_use(['999'])

        assert interactive.current_project is None
        captured = capsys.readouterr()
        assert 'not found' in captured.out

    def test_use_invalid_id(self, interactive, capsys, state_manager):
        """Test use with invalid ID format."""
        interactive.state_manager = state_manager

        interactive.cmd_use(['invalid'])

        captured = capsys.readouterr()
        assert 'Invalid project ID' in captured.out


class TestCommandParsing:
    """Test command parsing."""

    def test_parse_simple_command(self, interactive, capsys):
        """Test parsing simple command."""
        interactive.running = True

        # Mock input to return 'help' then EOFError
        with patch('builtins.input', side_effect=['help', EOFError()]):
            interactive.run()

        # Should have executed help
        assert 'help' in interactive.history

    def test_parse_command_with_args(self, interactive):
        """Test parsing command with arguments."""
        interactive.running = True
        interactive.state_manager = Mock()
        interactive.orchestrator = Mock()

        # Should handle quotes in arguments
        with patch('builtins.input', side_effect=['project create "My Project"', EOFError()]):
            interactive.run()

        # Should have parsed correctly
        assert len(interactive.history) == 1


class TestErrorHandling:
    """Test error handling in interactive mode."""

    def test_keyboard_interrupt(self, interactive, capsys):
        """Test handling Ctrl+C gracefully."""
        interactive.running = True

        with patch('builtins.input', side_effect=[KeyboardInterrupt(), 'exit']):
            # Mock orchestrator
            interactive.orchestrator = Mock()
            interactive.state_manager = Mock()

            try:
                interactive.run()
            except:
                pass

        # Should continue running after Ctrl+C
        captured = capsys.readouterr()
        assert "Use 'exit'" in captured.out or 'Goodbye' in captured.out

    def test_command_error(self, interactive, capsys):
        """Test handling command errors."""
        interactive.state_manager = Mock()
        interactive.state_manager.list_projects.side_effect = Exception("Database error")

        interactive._project_list()

        captured = capsys.readouterr()
        assert 'Failed to list projects' in captured.out


class TestInteractiveLoop:
    """Test interactive loop functionality."""

    def test_empty_input(self, interactive):
        """Test handling empty input."""
        interactive.running = True
        interactive.state_manager = Mock()
        interactive.orchestrator = Mock()

        # Empty strings should be ignored
        with patch('builtins.input', side_effect=['', '', 'exit']):
            interactive.run()

        # History should not include empty strings
        assert '' not in interactive.history

    def test_unknown_command(self, interactive, capsys):
        """Test handling unknown command."""
        interactive.running = True
        interactive.state_manager = Mock()
        interactive.orchestrator = Mock()

        with patch('builtins.input', side_effect=['unknowncommand', 'exit']):
            interactive.run()

        captured = capsys.readouterr()
        assert 'Unknown command' in captured.out
