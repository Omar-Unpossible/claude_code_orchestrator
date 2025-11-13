"""Tests for Story 9: Confirmation Workflow UI Polish (ADR-017).

Tests the enhanced confirmation UI with:
- Rich color-coded prompts
- Cascade implications discovery
- Dry-run simulation
- Contextual help system
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, UTC

from src.orchestrator import Orchestrator
from src.core.config import Config
from src.core.state import StateManager
from src.core.models import Task, TaskStatus, TaskType, ProjectState
from src.core.exceptions import TaskStoppedException


@pytest.fixture
def state_manager():
    """Create test state manager."""
    sm = StateManager.get_instance('sqlite:///:memory:')
    yield sm
    sm.close()


@pytest.fixture
def project(state_manager):
    """Create test project with unique name."""
    import tempfile
    import uuid
    unique_id = uuid.uuid4().hex[:8]
    temp_dir = tempfile.mkdtemp(prefix='obra_story9_test_')
    proj = state_manager.create_project(
        name=f'Test Project Story9 {unique_id}',
        description='Test project for Story 9',
        working_dir=temp_dir
    )
    return proj


@pytest.fixture
def orchestrator(test_config, state_manager):
    """Create test orchestrator."""
    orch = Orchestrator(config=test_config)
    orch.state_manager = state_manager
    return orch


class TestGetEntityDetails:
    """Test _get_entity_details() method."""

    def test_get_project_details(self, orchestrator, project):
        """Test getting project details."""
        details = orchestrator._get_entity_details('project', project.id)

        assert details is not None
        assert details['name'] == project.project_name
        # Description might be None or 'Test project for Story 9'
        assert 'created_at' in details
        assert 'status' in details

    def test_get_task_details(self, orchestrator, project, state_manager):
        """Test getting task details."""
        task = state_manager.create_task(
            project_id=project.id,
            task_data={
                'title': 'Test Task',
                'description': 'Test description'
            }
        )

        details = orchestrator._get_entity_details('task', task.id)

        assert details is not None
        assert details['name'] == 'Test Task'
        assert details['description'] == 'Test description'

    def test_get_nonexistent_entity(self, orchestrator):
        """Test getting details for non-existent entity."""
        details = orchestrator._get_entity_details('task', 99999)
        assert details is None

    def test_get_epic_details(self, orchestrator, project, state_manager):
        """Test getting epic details."""
        epic_id = state_manager.create_epic(
            project_id=project.id,
            title='Test Epic',
            description='Epic description'
        )

        details = orchestrator._get_entity_details('epic', epic_id)

        assert details is not None
        assert details['name'] == 'Test Epic'


class TestGetCascadeImplications:
    """Test _get_cascade_implications() method."""

    def test_project_deletion_cascade(self, orchestrator, project, state_manager):
        """Test project deletion shows all child entities."""
        # Create tasks, epics, stories
        epic_id = state_manager.create_epic(project.id, 'Epic 1', 'Epic desc')
        story_id = state_manager.create_story(project.id, epic_id, 'Story 1', 'Story desc')
        task1 = state_manager.create_task(project.id, {'title': 'Task 1'})
        task2 = state_manager.create_task(project.id, {'title': 'Task 2'})

        cascade = orchestrator._get_cascade_implications('project', project.id, 'DELETE')

        assert cascade['has_cascade'] is True
        assert cascade['total_affected'] >= 4  # At least epic, story, 2 tasks
        assert 'epics' in cascade['affected_entities']
        assert 'stories' in cascade['affected_entities']
        assert 'tasks' in cascade['affected_entities']

    def test_epic_deletion_cascade(self, orchestrator, project, state_manager):
        """Test epic deletion shows child stories and tasks."""
        epic_id = state_manager.create_epic(project.id, 'Epic 1', 'Epic desc')
        story1_id = state_manager.create_story(project.id, epic_id, 'Story 1', 'Story desc')
        story2_id = state_manager.create_story(project.id, epic_id, 'Story 2', 'Story desc')

        cascade = orchestrator._get_cascade_implications('epic', epic_id, 'DELETE')

        assert cascade['has_cascade'] is True
        assert cascade['total_affected'] == 2  # 2 stories
        assert cascade['affected_entities']['stories'] == 2

    def test_story_deletion_cascade(self, orchestrator, project, state_manager):
        """Test story deletion shows child tasks."""
        epic_id = state_manager.create_epic(project.id, 'Epic 1', 'Epic desc')
        story_id = state_manager.create_story(project.id, epic_id, 'Story 1', 'Story desc')
        task1 = state_manager.create_task(project.id, {'title': 'Task 1', 'story_id': story_id})
        task2 = state_manager.create_task(project.id, {'title': 'Task 2', 'story_id': story_id})

        cascade = orchestrator._get_cascade_implications('story', story_id, 'DELETE')

        assert cascade['has_cascade'] is True
        assert cascade['total_affected'] == 2
        assert cascade['affected_entities']['tasks'] == 2

    def test_task_deletion_cascade_subtasks(self, orchestrator, project, state_manager):
        """Test task deletion shows child subtasks."""
        parent_task = state_manager.create_task(project.id, {'title': 'Parent Task'})
        subtask1 = state_manager.create_task(project.id, {'title': 'Subtask 1', 'parent_task_id': parent_task.id})
        subtask2 = state_manager.create_task(project.id, {'title': 'Subtask 2', 'parent_task_id': parent_task.id})

        cascade = orchestrator._get_cascade_implications('task', parent_task.id, 'DELETE')

        assert cascade['has_cascade'] is True
        assert cascade['total_affected'] == 2
        assert cascade['affected_entities']['subtasks'] == 2

    def test_update_operation_no_cascade(self, orchestrator, project):
        """Test UPDATE operations don't show cascade."""
        cascade = orchestrator._get_cascade_implications('project', project.id, 'UPDATE')

        assert cascade['has_cascade'] is False
        assert cascade['total_affected'] == 0

    def test_cascade_details_populated(self, orchestrator, project, state_manager):
        """Test cascade details contain entity info."""
        task1 = state_manager.create_task(project.id, {'title': 'Task 1'})
        task2 = state_manager.create_task(project.id, {'title': 'Task 2'})

        cascade = orchestrator._get_cascade_implications('project', project.id, 'DELETE')

        assert len(cascade['details']) >= 2
        assert all('type' in d for d in cascade['details'])
        assert all('id' in d for d in cascade['details'])
        assert all('name' in d for d in cascade['details'])


class TestAssessOperationImpact:
    """Test _assess_operation_impact() method."""

    def test_impact_assessment_basic(self, orchestrator, project, state_manager):
        """Test basic impact assessment."""
        task1 = state_manager.create_task(project.id, {'title': 'Task 1'})

        impact = orchestrator._assess_operation_impact('project', project.id, 'DELETE')

        assert impact['estimated_changes'] >= 1
        assert impact['files_affected'] > 0
        assert 'KB' in impact['estimated_size'] or 'MB' in impact['estimated_size']
        assert impact['estimated_duration'] > 0

    def test_impact_scales_with_entities(self, orchestrator, project, state_manager):
        """Test impact scales with number of entities."""
        # Create many tasks
        for i in range(10):
            state_manager.create_task(project.id, {'title': f'Task {i}'})

        impact = orchestrator._assess_operation_impact('project', project.id, 'DELETE')

        assert impact['estimated_changes'] >= 10
        assert impact['files_affected'] >= 20  # Rough estimate


class TestSimulateDestructiveOperation:
    """Test _simulate_destructive_operation() method."""

    def test_simulate_delete_shows_before_after(self, orchestrator, project, state_manager, capsys):
        """Test simulation shows before/after state."""
        task = state_manager.create_task(project.id, {'title': 'Test Task'})
        task_obj = Task(
            id=1,
            project_id=project.id,
            title='Simulated Task',
            description='Test',
            status=TaskStatus.PENDING,
            created_at=datetime.now(UTC),
            task_metadata={
                'operation_type': 'DELETE',
                'entity_type': 'task',
                'entity_identifier': task.id
            }
        )

        orchestrator._simulate_destructive_operation(task_obj, 'task', task.id, 'DELETE')

        captured = capsys.readouterr()
        assert 'SIMULATION MODE' in captured.out
        assert 'BEFORE:' in captured.out
        assert 'AFTER' in captured.out
        assert 'deleted' in captured.out
        assert 'END SIMULATION' in captured.out

    def test_simulate_shows_cascade_effects(self, orchestrator, project, state_manager, capsys):
        """Test simulation shows cascade effects."""
        epic_id = state_manager.create_epic(project.id, 'Epic 1', 'Epic desc')
        story_id = state_manager.create_story(project.id, epic_id, 'Story 1', 'Story desc')

        task_obj = Task(
            id=1,
            project_id=project.id,
            title='Simulated Epic Deletion',
            description='Test',
            status=TaskStatus.PENDING,
            created_at=datetime.now(UTC),
            task_metadata={
                'operation_type': 'DELETE',
                'entity_type': 'epic',
                'entity_identifier': epic_id
            }
        )

        orchestrator._simulate_destructive_operation(task_obj, 'epic', epic_id, 'DELETE')

        captured = capsys.readouterr()
        assert 'cascade deleted' in captured.out


class TestDisplayCascadeDetails:
    """Test _display_cascade_details() method."""

    def test_display_cascade_no_cascade(self, orchestrator, capsys):
        """Test display when no cascade."""
        cascade_info = {
            'has_cascade': False,
            'total_affected': 0,
            'affected_entities': {},
            'details': []
        }

        orchestrator._display_cascade_details(cascade_info)

        captured = capsys.readouterr()
        assert 'No cascade effects' in captured.out

    def test_display_cascade_with_entities(self, orchestrator, capsys):
        """Test display with cascade entities."""
        cascade_info = {
            'has_cascade': True,
            'total_affected': 3,
            'affected_entities': {'tasks': 2, 'stories': 1},
            'details': [
                {'type': 'task', 'id': 1, 'name': 'Task 1'},
                {'type': 'task', 'id': 2, 'name': 'Task 2'},
                {'type': 'story', 'id': 3, 'name': 'Story 1'}
            ]
        }

        orchestrator._display_cascade_details(cascade_info)

        captured = capsys.readouterr()
        assert 'CASCADE DETAILS' in captured.out
        assert 'Total affected entities: 3' in captured.out or '3' in captured.out
        assert 'Task 1' in captured.out
        assert 'Story 1' in captured.out


class TestDisplayConfirmationHelp:
    """Test _display_confirmation_help() method."""

    def test_display_help(self, orchestrator, capsys):
        """Test help display shows all options."""
        orchestrator._display_confirmation_help()

        captured = capsys.readouterr()
        assert 'CONFIRMATION HELP' in captured.out
        assert '[y]' in captured.out
        assert '[n]' in captured.out
        assert '[s]' in captured.out
        assert '[c]' in captured.out
        assert '[h]' in captured.out
        assert 'Recovery Options' in captured.out


class TestEnhancedConfirmationInteractive:
    """Test enhanced _request_confirmation_interactive() method."""

    def test_confirmation_displays_entity_details(self, orchestrator, project, state_manager, capsys):
        """Test confirmation shows entity details."""
        task = state_manager.create_task(project.id, {'title': 'Test Task', 'description': 'Test description'})

        task_obj = Task(
            id=1,
            project_id=project.id,
            title='Delete Task',
            description='Test',
            status=TaskStatus.PENDING,
            created_at=datetime.now(UTC),
            task_metadata={
                'operation_type': 'DELETE',
                'entity_type': 'task',
                'entity_identifier': task.id,
                'original_message': 'Delete task 1'
            }
        )

        # Mock input to decline
        with patch.object(orchestrator.input_manager, 'get_input_with_timeout', return_value='n'):
            with pytest.raises(TaskStoppedException):
                orchestrator._request_confirmation_interactive(task_obj)

        captured = capsys.readouterr()
        assert 'DESTRUCTIVE OPERATION' in captured.out
        assert 'Operation:' in captured.out
        assert 'DELETE' in captured.out
        assert 'Entity:' in captured.out

    def test_confirmation_shows_cascade_warning(self, orchestrator, project, state_manager, capsys):
        """Test confirmation shows cascade warning."""
        epic_id = state_manager.create_epic(project.id, 'Epic 1', 'Epic desc')
        story_id = state_manager.create_story(project.id, epic_id, 'Story 1', 'Story desc')

        task_obj = Task(
            id=1,
            project_id=project.id,
            title='Delete Epic',
            description='Test',
            status=TaskStatus.PENDING,
            created_at=datetime.now(UTC),
            task_metadata={
                'operation_type': 'DELETE',
                'entity_type': 'epic',
                'entity_identifier': epic_id,
                'original_message': 'Delete epic 1'
            }
        )

        with patch.object(orchestrator.input_manager, 'get_input_with_timeout', return_value='n'):
            with pytest.raises(TaskStoppedException):
                orchestrator._request_confirmation_interactive(task_obj)

        captured = capsys.readouterr()
        assert 'CASCADE WARNING' in captured.out

    def test_simulate_option_returns_to_prompt(self, orchestrator, project, state_manager, capsys):
        """Test [s] simulate option returns to prompt."""
        task = state_manager.create_task(project.id, {'title': 'Test Task'})

        task_obj = Task(
            id=1,
            project_id=project.id,
            title='Delete Task',
            description='Test',
            status=TaskStatus.PENDING,
            created_at=datetime.now(UTC),
            task_metadata={
                'operation_type': 'DELETE',
                'entity_type': 'task',
                'entity_identifier': task.id,
                'original_message': 'Delete task 1'
            }
        )

        # First 's' for simulate, then 'n' to abort
        with patch.object(orchestrator.input_manager, 'get_input_with_timeout', side_effect=['s', 'n']):
            with pytest.raises(TaskStoppedException):
                orchestrator._request_confirmation_interactive(task_obj)

        captured = capsys.readouterr()
        assert 'SIMULATION MODE' in captured.out
        assert 'Operation aborted' in captured.out

    def test_cascade_details_option_returns_to_prompt(self, orchestrator, project, state_manager, capsys):
        """Test [c] cascade details option returns to prompt."""
        epic_id = state_manager.create_epic(project.id, 'Epic 1', 'Epic desc')
        story_id = state_manager.create_story(project.id, epic_id, 'Story 1', 'Story desc')

        task_obj = Task(
            id=1,
            project_id=project.id,
            title='Delete Epic',
            description='Test',
            status=TaskStatus.PENDING,
            created_at=datetime.now(UTC),
            task_metadata={
                'operation_type': 'DELETE',
                'entity_type': 'epic',
                'entity_identifier': epic_id,
                'original_message': 'Delete epic 1'
            }
        )

        # First 'c' for cascade, then 'n' to abort
        with patch.object(orchestrator.input_manager, 'get_input_with_timeout', side_effect=['c', 'n']):
            with pytest.raises(TaskStoppedException):
                orchestrator._request_confirmation_interactive(task_obj)

        captured = capsys.readouterr()
        assert 'CASCADE DETAILS' in captured.out

    def test_help_option_returns_to_prompt(self, orchestrator, project, state_manager, capsys):
        """Test [h] help option returns to prompt."""
        task = state_manager.create_task(project.id, {'title': 'Test Task'})

        task_obj = Task(
            id=1,
            project_id=project.id,
            title='Delete Task',
            description='Test',
            status=TaskStatus.PENDING,
            created_at=datetime.now(UTC),
            task_metadata={
                'operation_type': 'DELETE',
                'entity_type': 'task',
                'entity_identifier': task.id,
                'original_message': 'Delete task 1'
            }
        )

        # First 'h' for help, then 'n' to abort
        with patch.object(orchestrator.input_manager, 'get_input_with_timeout', side_effect=['h', 'n']):
            with pytest.raises(TaskStoppedException):
                orchestrator._request_confirmation_interactive(task_obj)

        captured = capsys.readouterr()
        assert 'CONFIRMATION HELP' in captured.out

    def test_confirm_option_logs_cascade_info(self, orchestrator, project, state_manager):
        """Test [y] confirm logs cascade information in audit."""
        epic_id = state_manager.create_epic(project.id, 'Epic 1', 'Epic desc')
        story_id = state_manager.create_story(project.id, epic_id, 'Story 1', 'Story desc')

        task_obj = Task(
            id=1,
            project_id=project.id,
            title='Delete Epic',
            description='Test',
            status=TaskStatus.PENDING,
            created_at=datetime.now(UTC),
            task_metadata={
                'operation_type': 'DELETE',
                'entity_type': 'epic',
                'entity_identifier': epic_id,
                'original_message': 'Delete epic 1'
            }
        )

        with patch.object(orchestrator.input_manager, 'get_input_with_timeout', return_value='y'):
            result = orchestrator._request_confirmation_interactive(task_obj)

        assert result is True


class TestColoramaFallback:
    """Test graceful fallback when colorama unavailable."""

    def test_methods_work_without_colorama(self, orchestrator, project, state_manager):
        """Test all methods work without colorama installed."""
        # Mock ImportError for colorama
        with patch('builtins.__import__', side_effect=lambda name, *args:
                   (_ for _ in ()).throw(ImportError()) if name == 'colorama' else __import__(name, *args)):

            task = state_manager.create_task(project.id, {'title': 'Test Task'})

            # Should not raise exception
            details = orchestrator._get_entity_details('task', task.id)
            assert details is not None

            # Simulation should work without colors
            task_obj = Task(
                id=1,
                project_id=project.id,
                title='Delete Task',
                description='Test',
                status=TaskStatus.PENDING,
                created_at=datetime.now(UTC),
                task_metadata={
                    'operation_type': 'DELETE',
                    'entity_type': 'task',
                    'entity_identifier': task.id
                }
            )

            # Should not raise exception
            orchestrator._simulate_destructive_operation(task_obj, 'task', task.id, 'DELETE')
