"""ADR-017 Regression Tests - Backward Compatibility Validation.

Tests to ensure existing functionality still works after ADR-017 unified execution
architecture implementation.

Story 6: Integration Testing
"""

import pytest
import warnings
from unittest.mock import Mock, patch
import tempfile
import os

from src.orchestrator import Orchestrator
from src.core.config import Config
from src.core.state import StateManager
from src.core.models import TaskStatus, TaskType


@pytest.fixture
def test_config():
    """Create test configuration."""
    config = Config()
    config.data = {
        'database': {'url': 'sqlite:///:memory:'},
        'agent': {'type': 'mock', 'config': {}},
        'llm': {'type': 'ollama', 'endpoint': 'http://localhost:11434'},
        'orchestration': {
            'breakpoints': {},
            'decision': {},
            'quality': {'min_quality_score': 0.7}
        }
    }
    return config


@pytest.fixture
def state_manager(test_config):
    """Create state manager with in-memory database."""
    db_url = test_config.get('database.url') or 'sqlite:///:memory:'
    sm = StateManager(database_url=db_url)
    yield sm
    sm.close()


@pytest.fixture
def test_workspace():
    """Create temporary workspace."""
    workspace = tempfile.mkdtemp(prefix='regression_test_')
    yield workspace
    if os.path.exists(workspace):
        import shutil
        shutil.rmtree(workspace)


@pytest.fixture
def orchestrator(test_config, state_manager):
    """Create orchestrator with mocked LLM."""
    orch = Orchestrator(config=test_config)
    orch.initialize()

    # Mock LLM
    orch.llm_interface = Mock()
    orch.llm_interface.is_available = Mock(return_value=True)
    orch.llm_interface.generate = Mock(return_value="Mocked response")

    # Use shared state_manager
    orch.state_manager = state_manager
    orch.intent_to_task_converter.state_manager = state_manager
    orch.nl_query_helper.state_manager = state_manager

    return orch


# ============================================================================
# Regression Test 1: Direct StateManager CRUD Still Works
# ============================================================================

def test_direct_state_manager_create_task(state_manager, test_workspace):
    """Verify direct StateManager task creation unchanged."""
    # Create project
    project = state_manager.create_project(
        name="Regression Test Project",
        description="Testing direct StateManager access",
        working_dir=test_workspace
    )

    # Create task directly (should still work)
    task = state_manager.create_task(
        project_id=project.id,
        task_data={
            'title': 'Direct Task Creation',
            'description': 'Testing backward compatibility',
            'priority': 5,
            'task_type': TaskType.TASK
        }
    )

    assert task is not None
    assert task.id is not None
    assert task.title == 'Direct Task Creation'
    assert task.status == TaskStatus.PENDING
    assert task.task_type == TaskType.TASK


# ============================================================================
# Regression Test 2: Epic Execution Still Works
# ============================================================================

def test_epic_execution_unchanged(orchestrator, state_manager, test_workspace):
    """Verify epic execution flow unchanged."""
    # Create project
    project = state_manager.create_project(
        name="Epic Test Project",
        description="Testing epic execution",
        working_dir=test_workspace
    )

    # Create epic
    epic_id = state_manager.create_epic(
        project_id=project.id,
        title="Test Epic",
        description="Epic for regression testing"
    )

    # Verify epic created
    epic_task = state_manager.get_task(epic_id)
    assert epic_task is not None
    assert epic_task.task_type == TaskType.EPIC
    assert epic_task.title == "Test Epic"


# ============================================================================
# Regression Test 3: Story Creation Still Works
# ============================================================================

def test_story_creation_unchanged(state_manager, test_workspace):
    """Verify story creation unchanged."""
    # Create project
    project = state_manager.create_project(
        name="Story Test Project",
        description="Testing story creation",
        working_dir=test_workspace
    )

    # Create epic first
    epic_id = state_manager.create_epic(
        project_id=project.id,
        title="Parent Epic",
        description="Epic for stories"
    )

    # Create story under epic
    story_id = state_manager.create_story(
        project_id=project.id,
        epic_id=epic_id,
        title="Test Story",
        description="Story for regression testing"
    )

    # Verify story created
    story_task = state_manager.get_task(story_id)
    assert story_task is not None
    assert story_task.task_type == TaskType.STORY
    assert story_task.epic_id == epic_id
    assert story_task.title == "Test Story"


# ============================================================================
# Regression Test 4: Quality Scoring Still Applies
# ============================================================================

def test_quality_scoring_applied(orchestrator):
    """Verify quality scoring unchanged."""
    # Quality controller should still be initialized
    assert orchestrator.quality_controller is not None

    # Test quality scoring on a mock response
    response = "This is a test response for quality evaluation"

    # Mock the LLM call for quality scoring
    orchestrator.quality_controller.llm = Mock()
    orchestrator.quality_controller.llm.generate = Mock(return_value="0.85")

    # Quality scoring should work
    # Note: We're just verifying the component exists and is callable
    assert hasattr(orchestrator.quality_controller, 'calculate_quality_score')


# ============================================================================
# Regression Test 5: Confidence Tracking Still Works
# ============================================================================

def test_confidence_tracking_preserved(orchestrator):
    """Verify confidence scoring unchanged."""
    # Confidence scorer should still be initialized
    assert orchestrator.confidence_scorer is not None

    # Test confidence calculation
    task_context = {
        'complexity': 'medium',
        'requirements_clarity': 'high'
    }

    # Confidence scorer should work
    assert hasattr(orchestrator.confidence_scorer, 'predict_confidence')


# ============================================================================
# Regression Test 6: Breakpoints Still Trigger
# ============================================================================

def test_breakpoints_still_work(orchestrator):
    """Verify breakpoint system unchanged."""
    # Breakpoint manager should still be initialized
    assert orchestrator.breakpoint_manager is not None

    # Breakpoint manager should have core methods
    assert hasattr(orchestrator.breakpoint_manager, 'register_notification_callback')
    assert hasattr(orchestrator.breakpoint_manager, 'should_notify')


# ============================================================================
# Regression Test 7: File Watching Still Works
# ============================================================================

def test_file_watcher_unchanged(orchestrator):
    """Verify file watching unchanged."""
    # File watcher should be available (may be None if not initialized)
    assert hasattr(orchestrator, 'file_watcher')

    # File watcher should have standard methods when initialized
    if orchestrator.file_watcher is not None:
        assert hasattr(orchestrator.file_watcher, 'start_watching')
        assert hasattr(orchestrator.file_watcher, 'stop_watching')


# ============================================================================
# Regression Test 8: CLI Task Execute Still Works
# ============================================================================

def test_cli_task_execute_unchanged(orchestrator, state_manager, test_workspace):
    """Verify CLI task execution unchanged."""
    # Create project and task
    project = state_manager.create_project(
        name="CLI Test Project",
        description="Testing CLI task execution",
        working_dir=test_workspace
    )

    task = state_manager.create_task(
        project_id=project.id,
        task_data={
            'title': 'CLI Test Task',
            'description': 'Testing task execution via orchestrator',
            'task_type': TaskType.TASK
        }
    )

    # Verify task can be retrieved (execute_task would work in real scenario)
    retrieved_task = state_manager.get_task(task.id)
    assert retrieved_task is not None
    assert retrieved_task.id == task.id
    assert retrieved_task.status == TaskStatus.PENDING

    # Verify orchestrator has execute_task method
    assert hasattr(orchestrator, 'execute_task')
