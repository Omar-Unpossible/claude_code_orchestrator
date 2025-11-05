"""Tests for TaskScheduler - dependency resolution, prioritization, and state management."""

import pytest
import time
from datetime import datetime, UTC, timedelta
from unittest.mock import Mock, patch

from src.core.exceptions import TaskDependencyException, TaskStateException
from src.core.models import Task, TaskStatus
from src.core.state import StateManager
from src.orchestration.task_scheduler import TaskScheduler


@pytest.fixture
def state_manager(tmp_path):
    """Create StateManager with temporary database."""
    # Reset singleton
    StateManager.reset_instance()

    # Create temporary database
    db_path = tmp_path / "test.db"
    sm = StateManager.get_instance(f"sqlite:///{db_path}")

    yield sm

    # Cleanup
    sm.close()
    try:
        db_path.unlink()
    except:
        pass


@pytest.fixture
def scheduler(state_manager):
    """Create TaskScheduler instance."""
    return TaskScheduler(state_manager)


@pytest.fixture
def project(state_manager, tmp_path):
    """Create test project."""
    return state_manager.create_project(
        name="test_project",
        description="Test project for scheduler",
        working_dir=str(tmp_path)
    )


def create_task_for_scheduler(state_manager, project_id, title, description, priority=5,
                               status=None, dependencies=None, metadata=None):
    """Helper to create task directly in DB for scheduler tests.

    This bypasses StateManager.create_task() to allow setting custom status for testing.
    """
    task = Task(
        project_id=project_id,
        title=title,
        description=description,
        status=status,
        priority=priority,
        dependencies=dependencies or [],
        task_metadata=metadata or {}
    )
    # Use transaction context for thread-safe session handling
    with state_manager.transaction():
        session = state_manager._get_session()
        session.add(task)
        session.flush()  # Flush within transaction
        session.refresh(task)
    return task


class TestTaskScheduling:
    """Test basic task scheduling functionality."""

    def test_schedule_task_no_dependencies(self, scheduler, project):
        """Test scheduling task with no dependencies goes directly to ready."""
        task = create_task_for_scheduler(
            scheduler.state_manager,
            project.id,
            "Test Task",
            "No dependencies",
            priority=5,
            status=None
        )

        scheduler.schedule_task(task)

        assert task.status == TaskScheduler.STATE_READY
        ready_tasks = scheduler.get_ready_tasks(project.id)
        assert len(ready_tasks) == 1
        assert ready_tasks[0].id == task.id

    def test_schedule_task_with_pending_dependencies(self, scheduler, project):
        """Test scheduling task with unsatisfied dependencies stays pending."""
        # Create dependency task
        dep_task = create_task_for_scheduler(
            scheduler.state_manager,
            project.id,
            "Dependency",
            "Must complete first",
            status=TaskScheduler.STATE_PENDING,
            priority=5
        )

        # Create dependent task
        task = create_task_for_scheduler(
            scheduler.state_manager,
            project.id,
            "Dependent Task",
            "Depends on dep_task",
            status=None,
            priority=5,
            dependencies=[dep_task.id]
        )

        scheduler.schedule_task(task)

        assert task.status == TaskScheduler.STATE_PENDING
        ready_tasks = scheduler.get_ready_tasks(project.id)
        assert len(ready_tasks) == 0

    def test_schedule_task_with_completed_dependencies(self, scheduler, project):
        """Test scheduling task with completed dependencies goes to ready."""
        # Create completed dependency
        dep_task = create_task_for_scheduler(
            scheduler.state_manager,
            project.id,
            "Dependency",
            "Already done",
            status=TaskScheduler.STATE_COMPLETED,
            priority=5
        )

        # Create dependent task
        task = create_task_for_scheduler(
            scheduler.state_manager,
            project.id,
            "Dependent Task",
            "Depends on dep_task",
            status=None,
            priority=5,
            dependencies=[dep_task.id]
        )

        scheduler.schedule_task(task)

        assert task.status == TaskScheduler.STATE_READY


class TestPriorityOrdering:
    """Test priority-based task selection."""

    def test_get_next_task_highest_priority(self, scheduler, project):
        """Test that highest priority task is selected first."""
        # Create tasks with different priorities
        tasks = []
        for i, priority in enumerate([3, 8, 5, 1]):
            task = create_task_for_scheduler(
                scheduler.state_manager,
                project.id,
                f"Task {i}",
                f"Priority {priority}",
                status=None,
                priority=priority
            )
            tasks.append(task)

        # Schedule all tasks
        for task in tasks:
            scheduler.schedule_task(task)

        # Should get priority 8 task first
        next_task = scheduler.get_next_task(project.id)
        assert next_task.priority == 8
        assert next_task.status == TaskScheduler.STATE_RUNNING

    def test_get_next_task_empty_queue(self, scheduler, project):
        """Test getting next task when queue is empty."""
        next_task = scheduler.get_next_task(project.id)
        assert next_task is None


class TestDependencyResolution:
    """Test dependency resolution and topological sorting."""

    def test_resolve_dependencies_simple_chain(self, scheduler, project):
        """Test resolving simple dependency chain."""
        # Create chain: task1 → task2 → task3
        task1 = create_task_for_scheduler(
            scheduler.state_manager,
            project.id,
            "Task 1",
            "First",
            status=TaskScheduler.STATE_COMPLETED,
            priority=5
        )

        task2 = create_task_for_scheduler(
            scheduler.state_manager,
            project.id,
            "Task 2",
            "Second",
            status=TaskScheduler.STATE_COMPLETED,
            priority=5,
            dependencies=[task1.id]
        )

        task3 = create_task_for_scheduler(
            scheduler.state_manager,
            project.id,
            "Task 3",
            "Third",
            status=None,
            priority=5,
            dependencies=[task1.id, task2.id]
        )

        dependencies = scheduler.resolve_dependencies(task3)
        assert len(dependencies) == 2
        dep_ids = [d.id for d in dependencies]
        assert task1.id in dep_ids
        assert task2.id in dep_ids

    def test_resolve_dependencies_missing(self, scheduler, project):
        """Test resolving dependencies when one is missing."""
        task = create_task_for_scheduler(
            scheduler.state_manager,
            project.id,
            "Task",
            "Has missing dependency",
            status=None,
            priority=5,
            dependencies=[999999]
        )

        with pytest.raises(TaskDependencyException) as exc_info:
            scheduler.resolve_dependencies(task)

        assert "not found" in str(exc_info.value).lower()


class TestStateTransitions:
    """Test task state machine transitions."""

    def test_valid_transition_ready_to_running(self, scheduler, project):
        """Test valid transition from ready to running."""
        task = create_task_for_scheduler(
            scheduler.state_manager,
            project.id,
            "Task",
            "Test",
            status=TaskScheduler.STATE_READY,
            priority=5
        )

        scheduler._transition_state(task, TaskScheduler.STATE_RUNNING)
        assert task.status == TaskScheduler.STATE_RUNNING

    def test_invalid_transition_completed_to_running(self, scheduler, project):
        """Test invalid transition from completed to running."""
        task = create_task_for_scheduler(
            scheduler.state_manager,
            project.id,
            "Task",
            "Test",
            status=TaskScheduler.STATE_COMPLETED,
            priority=5
        )

        with pytest.raises(TaskStateException) as exc_info:
            scheduler._transition_state(task, TaskScheduler.STATE_RUNNING)

        assert "invalid" in str(exc_info.value).lower()

    def test_all_valid_transitions(self, scheduler, project):
        """Test all valid state transitions."""
        task = create_task_for_scheduler(
            scheduler.state_manager,
            project.id,
            "Task",
            "Test",
            status=None,
            priority=5
        )

        # pending → ready → running → completed
        scheduler._transition_state(task, TaskScheduler.STATE_PENDING)
        assert task.status == TaskScheduler.STATE_PENDING

        scheduler._transition_state(task, TaskScheduler.STATE_READY)
        assert task.status == TaskScheduler.STATE_READY

        scheduler._transition_state(task, TaskScheduler.STATE_RUNNING)
        assert task.status == TaskScheduler.STATE_RUNNING

        scheduler._transition_state(task, TaskScheduler.STATE_COMPLETED)
        assert task.status == TaskScheduler.STATE_COMPLETED


class TestTaskCompletion:
    """Test task completion logic."""

    def test_mark_complete_updates_status(self, scheduler, project):
        """Test marking task complete updates status."""
        task = create_task_for_scheduler(
            scheduler.state_manager,
            project.id,
            "Task",
            "Test",
            status=TaskScheduler.STATE_RUNNING,
            priority=5
        )

        scheduler.mark_complete(task.id, {'output': 'success'})

        updated_task = scheduler.state_manager.get_task(task.id)
        assert updated_task.status == TaskScheduler.STATE_COMPLETED

    def test_mark_complete_promotes_pending_tasks(self, scheduler, project):
        """Test completing task promotes pending dependents to ready."""
        # Create dependency task
        dep_task = create_task_for_scheduler(
            scheduler.state_manager,
            project.id,
            "Dependency",
            "Must complete first",
            status=TaskScheduler.STATE_RUNNING,
            priority=5
        )

        # Create dependent task
        dependent_task = create_task_for_scheduler(
            scheduler.state_manager,
            project.id,
            "Dependent",
            "Waits on dep_task",
            status=TaskScheduler.STATE_PENDING,
            priority=5,
            dependencies=[dep_task.id]
        )

        # Complete dependency
        scheduler.mark_complete(dep_task.id, {'output': 'done'})

        # Dependent should now be ready
        updated_dependent = scheduler.state_manager.get_task(dependent_task.id)
        assert updated_dependent.status == TaskScheduler.STATE_READY


class TestTaskFailure:
    """Test task failure and retry logic."""

    def test_mark_failed_with_retry(self, scheduler, project):
        """Test task failure triggers retry."""
        task = create_task_for_scheduler(
            scheduler.state_manager,
            project.id,
            "Task",
            "Will fail",
            status=TaskScheduler.STATE_RUNNING,
            priority=5
        )

        scheduler.mark_failed(task.id, "Connection timeout")

        updated_task = scheduler.state_manager.get_task(task.id)
        assert updated_task.status == TaskScheduler.STATE_RETRYING
        assert updated_task.retry_count == 1

    def test_mark_failed_no_retry_on_validation_error(self, scheduler, project):
        """Test validation errors don't trigger retry."""
        task = create_task_for_scheduler(
            scheduler.state_manager,
            project.id,
            "Task",
            "Will fail",
            status=TaskScheduler.STATE_RUNNING,
            priority=5
        )

        scheduler.mark_failed(task.id, "Validation failed: invalid input")

        updated_task = scheduler.state_manager.get_task(task.id)
        assert updated_task.status == TaskScheduler.STATE_FAILED

    def test_mark_failed_max_retries_exceeded(self, scheduler, project):
        """Test task fails permanently after max retries."""
        task = create_task_for_scheduler(
            scheduler.state_manager,
            project.id,
            "Task",
            "Will fail",
            status=TaskScheduler.STATE_RUNNING,
            priority=5
        )
        # Set retry_count to 3 (max retries)
        task.retry_count = 3
        task.max_retries = 3
        session = scheduler.state_manager._get_session()
        session.commit()

        scheduler.mark_failed(task.id, "Connection timeout")

        updated_task = scheduler.state_manager.get_task(task.id)
        assert updated_task.status == TaskScheduler.STATE_FAILED

    def test_exponential_backoff_calculation(self, scheduler):
        """Test exponential backoff delay calculation."""
        assert scheduler._calculate_backoff(0) == 60    # 60 * 2^0
        assert scheduler._calculate_backoff(1) == 120   # 60 * 2^1
        assert scheduler._calculate_backoff(2) == 240   # 60 * 2^2
        assert scheduler._calculate_backoff(3) == 480   # 60 * 2^3


class TestRetryLogic:
    """Test task retry logic."""

    def test_retry_task_transitions_to_ready(self, scheduler, project):
        """Test retrying task transitions to ready state."""
        task = create_task_for_scheduler(
            scheduler.state_manager,
            project.id,
            "Task",
            "Retrying",
            status=TaskScheduler.STATE_RETRYING,
            priority=5,
            metadata={'retry_count': 1, 'retry_at': datetime.now(UTC).isoformat()}
        )

        scheduler.retry_task(task.id)

        updated_task = scheduler.state_manager.get_task(task.id)
        assert updated_task.status == TaskScheduler.STATE_READY

    def test_retry_task_applies_priority_penalty(self, scheduler, project):
        """Test retry reduces task priority."""
        initial_priority = 8
        task = create_task_for_scheduler(
            scheduler.state_manager,
            project.id,
            "Task",
            "Retrying",
            status=TaskScheduler.STATE_RETRYING,
            priority=initial_priority,
            metadata={'retry_count': 1, 'retry_at': datetime.now(UTC).isoformat()}
        )

        scheduler.retry_task(task.id)

        # Priority should be reduced by RETRY_PENALTY
        assert task.priority == initial_priority + TaskScheduler.RETRY_PENALTY


class TestDeadlockDetection:
    """Test circular dependency detection."""

    def test_detect_deadlock_simple_cycle(self, scheduler, project):
        """Test detecting simple circular dependency."""
        # Create task1 → task2 → task1 cycle
        task1 = create_task_for_scheduler(
            scheduler.state_manager,
            project.id,
            "Task 1",
            "Depends on task2",
            status=TaskScheduler.STATE_PENDING,
            priority=5
        )

        task2 = create_task_for_scheduler(
            scheduler.state_manager,
            project.id,
            "Task 2",
            "Depends on task1",
            status=TaskScheduler.STATE_PENDING,
            priority=5,
            dependencies=[task1.id]
        )

        # Update task1 to depend on task2 (creating cycle)
        task1.dependencies = [task2.id]
        session = scheduler.state_manager._get_session()
        session.commit()
        session.expire_all()  # Clear cache to ensure fresh data is loaded

        deadlock = scheduler.detect_deadlock(project.id)
        assert deadlock is not None
        assert len(deadlock) >= 2

    def test_detect_deadlock_no_cycle(self, scheduler, project):
        """Test no deadlock detected in valid DAG."""
        # Create task1 → task2 → task3 (no cycle)
        task1 = create_task_for_scheduler(
            scheduler.state_manager,
            project.id,
            "Task 1",
            "First",
            status=TaskScheduler.STATE_COMPLETED,
            priority=5
        )

        task2 = create_task_for_scheduler(
            scheduler.state_manager,
            project.id,
            "Task 2",
            "Second",
            status=TaskScheduler.STATE_READY,
            priority=5,
            dependencies=[task1.id]
        )

        deadlock = scheduler.detect_deadlock(project.id)
        assert deadlock is None


class TestTaskCancellation:
    """Test task cancellation."""

    def test_cancel_task_updates_status(self, scheduler, project):
        """Test cancelling task updates status."""
        task = create_task_for_scheduler(
            scheduler.state_manager,
            project.id,
            "Task",
            "Will be cancelled",
            status=TaskScheduler.STATE_RUNNING,
            priority=5
        )

        scheduler.cancel_task(task.id, "User requested cancellation")

        updated_task = scheduler.state_manager.get_task(task.id)
        assert updated_task.status == TaskScheduler.STATE_CANCELLED
        assert updated_task.task_metadata['reason'] == "User requested cancellation"


class TestTaskQueries:
    """Test task query methods."""

    def test_get_ready_tasks(self, scheduler, project):
        """Test getting all ready tasks."""
        # Create mix of tasks in different states
        for i, status in enumerate([
            TaskScheduler.STATE_READY,
            TaskScheduler.STATE_PENDING,
            TaskScheduler.STATE_READY,
            TaskScheduler.STATE_COMPLETED
        ]):
            task = create_task_for_scheduler(
                scheduler.state_manager,
                project.id,
                f"Task {i}",
                f"Status {status}",
                status=status,
                priority=5
            )
            if status == TaskScheduler.STATE_READY:
                scheduler._add_to_ready_queue(task)

        ready_tasks = scheduler.get_ready_tasks(project.id)
        assert len(ready_tasks) == 2
        assert all(t.status == TaskScheduler.STATE_READY for t in ready_tasks)

    def test_get_blocked_tasks(self, scheduler, project):
        """Test getting all blocked tasks."""
        # Create mix of tasks
        for i, status in enumerate([
            TaskScheduler.STATE_BLOCKED,
            TaskScheduler.STATE_READY,
            TaskScheduler.STATE_BLOCKED
        ]):
            task = create_task_for_scheduler(
                scheduler.state_manager,
                project.id,
                f"Task {i}",
                f"Status {status}",
                status=status,
                priority=5
            )

        blocked_tasks = scheduler.get_blocked_tasks(project.id)
        assert len(blocked_tasks) == 2
        assert all(t.status == TaskScheduler.STATE_BLOCKED for t in blocked_tasks)

    def test_get_task_status(self, scheduler, project):
        """Test getting task status."""
        task = create_task_for_scheduler(
            scheduler.state_manager,
            project.id,
            "Task",
            "Test",
            status=TaskScheduler.STATE_RUNNING,
            priority=5
        )

        status = scheduler.get_task_status(task.id)
        assert status == TaskScheduler.STATE_RUNNING


class TestThreadSafety:
    """Test thread-safe operations."""

    def test_concurrent_task_scheduling(self, scheduler, project):
        """Test scheduling tasks concurrently."""
        import threading

        # Create all tasks first (serially to avoid session conflicts)
        tasks = []
        for i in range(9):
            task = create_task_for_scheduler(
                scheduler.state_manager,
                project.id,
                f"Task {i}",
                "Concurrent",
                status=None,
                priority=5
            )
            tasks.append(task)

        # Now schedule them concurrently (3 threads, 3 tasks each)
        def schedule_tasks(task_batch):
            for task in task_batch:
                scheduler.schedule_task(task)

        # Divide tasks into 3 batches
        batch_size = 3
        threads = [
            threading.Thread(target=schedule_tasks, args=(tasks[i*batch_size:(i+1)*batch_size],))
            for i in range(3)
        ]

        for t in threads:
            t.start()

        for t in threads:
            t.join(timeout=5.0)

        # Should have 9 ready tasks
        ready_tasks = scheduler.get_ready_tasks(project.id)
        assert len(ready_tasks) == 9


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_schedule_task_with_invalid_dependency_format(self, scheduler, project):
        """Test scheduling task with malformed dependency string."""
        task = create_task_for_scheduler(
            scheduler.state_manager,
            project.id,
            "Task",
            "Bad deps",
            status=None,
            priority=5,
            metadata={'dependencies': 'not,valid,numbers'}
        )

        # Should handle gracefully
        scheduler.schedule_task(task)
        assert task.status == TaskScheduler.STATE_READY  # No valid deps

    def test_mark_complete_nonexistent_task(self, scheduler):
        """Test marking nonexistent task as complete."""
        with pytest.raises(TaskStateException):
            scheduler.mark_complete(999999, {})

    def test_get_task_status_nonexistent(self, scheduler):
        """Test getting status of nonexistent task."""
        with pytest.raises(TaskStateException):
            scheduler.get_task_status(999999)
