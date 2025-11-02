"""Task scheduling with dependency resolution and priority management.

This module implements the TaskScheduler, which manages task queue execution with:
- Dependency resolution using topological sort
- Priority-based task selection using heap queue
- State machine with valid transitions
- Exponential backoff retry logic
- Deadlock detection for circular dependencies
- Deadline-based priority boosting

The scheduler coordinates with StateManager for all state persistence.
"""

import heapq
import logging
import time
from collections import defaultdict, deque
from datetime import datetime, UTC, timedelta
from threading import RLock
from typing import Dict, List, Optional, Set, Tuple

from src.core.exceptions import (
    OrchestratorException,
    TaskDependencyException,
    TaskStateException
)
from src.core.models import Task
from src.core.state import StateManager


logger = logging.getLogger(__name__)


class TaskScheduler:
    """Task scheduler with dependency resolution and priority management.

    Manages task queue, execution order, dependencies, retries, and deadlock detection.
    All task state changes are persisted via StateManager.

    Task States:
        - pending: Created but dependencies not satisfied
        - ready: All dependencies satisfied, ready to execute
        - running: Currently being executed
        - blocked: Waiting on external event or human input
        - completed: Successfully finished
        - failed: Execution failed
        - cancelled: Manually cancelled
        - retrying: Failed but retrying with backoff

    Valid State Transitions:
        - pending → ready: All dependencies completed
        - ready → running: Picked for execution
        - running → completed: Execution successful
        - running → failed: Execution error
        - running → blocked: Waiting for breakpoint resolution
        - failed → retrying: Automatic retry triggered
        - retrying → running: Retry attempt started
        - running → cancelled: Cancellation requested
        - blocked → ready: Blocking condition resolved

    Example:
        >>> scheduler = TaskScheduler(state_manager)
        >>> scheduler.schedule_task(task1)
        >>> scheduler.schedule_task(task2)  # depends on task1
        >>>
        >>> # Get next ready task
        >>> task = scheduler.get_next_task(project_id)
        >>> # ... execute task ...
        >>> scheduler.mark_complete(task.id, result)
    """

    # Task state constants
    STATE_PENDING = 'pending'
    STATE_READY = 'ready'
    STATE_RUNNING = 'running'
    STATE_BLOCKED = 'blocked'
    STATE_COMPLETED = 'completed'
    STATE_FAILED = 'failed'
    STATE_CANCELLED = 'cancelled'
    STATE_RETRYING = 'retrying'

    # Valid state transitions
    VALID_TRANSITIONS = {
        STATE_PENDING: {STATE_READY},
        STATE_READY: {STATE_RUNNING},
        STATE_RUNNING: {STATE_COMPLETED, STATE_FAILED, STATE_BLOCKED, STATE_CANCELLED},
        STATE_FAILED: {STATE_RETRYING, STATE_CANCELLED},
        STATE_RETRYING: {STATE_RUNNING},
        STATE_BLOCKED: {STATE_READY, STATE_CANCELLED},
        STATE_COMPLETED: set(),  # Terminal state
        STATE_CANCELLED: set()   # Terminal state
    }

    # Retry configuration
    MAX_RETRIES = 3
    BASE_DELAY_SECONDS = 60
    EXPONENTIAL_BASE = 2

    # Priority configuration
    DEFAULT_PRIORITY = 5
    DEADLINE_BOOST = 2
    BLOCKING_BOOST = 1
    RETRY_PENALTY = -1

    def __init__(self, state_manager: StateManager):
        """Initialize task scheduler.

        Args:
            state_manager: StateManager instance for state persistence
        """
        self.state_manager = state_manager
        self._lock = RLock()

        # Priority queue: (priority, task_id) tuples
        # Note: heapq is min-heap, so we negate priority for max-heap behavior
        self._ready_queues: Dict[int, List[Tuple[int, int]]] = defaultdict(list)

        logger.info("TaskScheduler initialized")

    def schedule_task(self, task: Task) -> None:
        """Schedule a task for execution.

        The task is added to the system and its state is set based on dependencies.
        If all dependencies are satisfied, it goes to 'ready' state, otherwise 'pending'.

        Args:
            task: Task to schedule

        Raises:
            TaskDependencyException: If dependency resolution fails
        """
        with self._lock:
            logger.debug(f"Scheduling task {task.id}: {task.title}")

            # Check if dependencies are satisfied
            dependencies = self._parse_dependencies(task)
            dependencies_satisfied = self._check_dependencies_satisfied(task.project_id, dependencies)

            # Set initial state
            if dependencies_satisfied:
                self._transition_state(task, self.STATE_READY)
                self._add_to_ready_queue(task)
                logger.info(f"Task {task.id} scheduled as READY")
            else:
                self._transition_state(task, self.STATE_PENDING)
                logger.info(f"Task {task.id} scheduled as PENDING (waiting on dependencies)")

    def get_next_task(self, project_id: int) -> Optional[Task]:
        """Get the next highest-priority ready task.

        Args:
            project_id: Project ID to get task from

        Returns:
            Next task to execute, or None if no tasks ready
        """
        with self._lock:
            # Check for deadlocks before getting next task
            deadlock = self.detect_deadlock(project_id)
            if deadlock:
                task_ids = [t.id for t in deadlock]
                logger.error(f"Deadlock detected in project {project_id}: tasks {task_ids}")
                raise TaskDependencyException(
                    f"Circular dependency detected: {task_ids}",
                    context={'project_id': project_id, 'tasks': task_ids},
                    recovery="Manually resolve dependency cycle"
                )

            # Get ready queue for project
            ready_queue = self._ready_queues.get(project_id, [])
            if not ready_queue:
                return None

            # Apply priority boosting before selection
            self._apply_priority_boosts(project_id)

            # Pop highest priority task
            _, task_id = heapq.heappop(ready_queue)

            # Get task from database
            task = self.state_manager.get_task(task_id)
            if not task:
                logger.warning(f"Task {task_id} not found in database")
                return None

            # Transition to running
            self._transition_state(task, self.STATE_RUNNING)

            logger.info(f"Selected task {task_id} for execution (priority: {task.priority})")
            return task

    def resolve_dependencies(self, task: Task) -> List[Task]:
        """Resolve task dependencies in execution order.

        Uses topological sort (Kahn's algorithm) to determine execution order.

        Args:
            task: Task to resolve dependencies for

        Returns:
            List of tasks in execution order (dependencies first)

        Raises:
            TaskDependencyException: If circular dependency detected or dependency not found
        """
        with self._lock:
            dependency_ids = self._parse_dependencies(task)
            if not dependency_ids:
                return []

            # Build dependency graph
            graph = self._build_dependency_graph(task.project_id)

            # Topological sort using Kahn's algorithm
            in_degree = defaultdict(int)
            for node in graph:
                for neighbor in graph[node]:
                    in_degree[neighbor] += 1

            # Queue of nodes with no incoming edges
            queue = deque([node for node in graph if in_degree[node] == 0])
            result = []

            while queue:
                node = queue.popleft()
                result.append(node)

                for neighbor in graph[node]:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        queue.append(neighbor)

            # Check for cycle
            if len(result) != len(graph):
                raise TaskDependencyException(
                    "Circular dependency detected",
                    context={'task_id': task.id, 'dependencies': dependency_ids},
                    recovery="Remove circular dependency"
                )

            # Filter to only requested dependencies
            dependency_tasks = []
            for task_id in dependency_ids:
                dep_task = self.state_manager.get_task(task_id)
                if not dep_task:
                    raise TaskDependencyException(
                        f"Dependency task {task_id} not found",
                        context={'task_id': task.id, 'missing_dependency': task_id},
                        recovery="Create missing dependency task or update dependencies"
                    )
                dependency_tasks.append(dep_task)

            return dependency_tasks

    def mark_complete(self, task_id: int, result: dict) -> None:
        """Mark task as completed successfully.

        Args:
            task_id: Task ID to mark complete
            result: Result dictionary with task output
        """
        with self._lock:
            task = self.state_manager.get_task(task_id)
            if not task:
                raise TaskStateException(
                    f"Task {task_id} not found",
                    context={'task_id': task_id},
                    recovery="Verify task exists"
                )

            self._transition_state(task, self.STATE_COMPLETED)

            # Update task metadata
            self.state_manager.update_task_status(
                task_id=task_id,
                status=self.STATE_COMPLETED,
                metadata={'result': result, 'completed_at': datetime.now(UTC).isoformat()}
            )

            # Check if any pending tasks can now be ready
            self._promote_pending_tasks(task.project_id)

            logger.info(f"Task {task_id} marked as COMPLETED")

    def mark_failed(self, task_id: int, error: str) -> None:
        """Mark task as failed.

        Determines if task should be retried based on error type and retry count.

        Args:
            task_id: Task ID to mark failed
            error: Error message/reason
        """
        with self._lock:
            task = self.state_manager.get_task(task_id)
            if not task:
                raise TaskStateException(
                    f"Task {task_id} not found",
                    context={'task_id': task_id},
                    recovery="Verify task exists"
                )

            # Check retry eligibility
            retry_count = task.metadata.get('retry_count', 0) if task.metadata else 0
            should_retry = self._should_retry(error, retry_count)

            if should_retry:
                # Transition to retrying
                self._transition_state(task, self.STATE_RETRYING)

                # Calculate backoff delay
                delay = self._calculate_backoff(retry_count)

                # Update metadata
                self.state_manager.update_task_status(
                    task_id=task_id,
                    status=self.STATE_RETRYING,
                    metadata={
                        'error': error,
                        'retry_count': retry_count + 1,
                        'retry_at': (datetime.now(UTC) + timedelta(seconds=delay)).isoformat(),
                        'failed_at': datetime.now(UTC).isoformat()
                    }
                )

                logger.warning(f"Task {task_id} FAILED, will retry in {delay}s (attempt {retry_count + 1}/{self.MAX_RETRIES})")
            else:
                # Terminal failure
                self._transition_state(task, self.STATE_FAILED)

                self.state_manager.update_task_status(
                    task_id=task_id,
                    status=self.STATE_FAILED,
                    metadata={
                        'error': error,
                        'retry_count': retry_count,
                        'failed_at': datetime.now(UTC).isoformat()
                    }
                )

                logger.error(f"Task {task_id} FAILED permanently: {error}")

    def retry_task(self, task_id: int) -> None:
        """Retry a failed task.

        Args:
            task_id: Task ID to retry

        Raises:
            TaskStateException: If task is not in retrying state
        """
        with self._lock:
            task = self.state_manager.get_task(task_id)
            if not task:
                raise TaskStateException(
                    f"Task {task_id} not found",
                    context={'task_id': task_id},
                    recovery="Verify task exists"
                )

            if task.status != self.STATE_RETRYING:
                raise TaskStateException(
                    f"Cannot retry task {task_id} in state {task.status}",
                    context={'task_id': task_id, 'current_state': task.status},
                    recovery="Task must be in 'retrying' state"
                )

            # Check if retry delay has elapsed
            retry_at_str = task.metadata.get('retry_at') if task.metadata else None
            if retry_at_str:
                retry_at = datetime.fromisoformat(retry_at_str)
                if datetime.now(UTC) < retry_at:
                    logger.debug(f"Task {task_id} retry scheduled for {retry_at}, too early")
                    return

            # Transition to ready for retry
            self._transition_state(task, self.STATE_READY)

            # Apply retry penalty to priority
            adjusted_priority = task.priority + self.RETRY_PENALTY
            task.priority = max(1, adjusted_priority)  # Ensure priority >= 1

            self._add_to_ready_queue(task)

            logger.info(f"Task {task_id} retrying (priority adjusted to {task.priority})")

    def cancel_task(self, task_id: int, reason: str) -> None:
        """Cancel a task.

        Args:
            task_id: Task ID to cancel
            reason: Cancellation reason
        """
        with self._lock:
            task = self.state_manager.get_task(task_id)
            if not task:
                raise TaskStateException(
                    f"Task {task_id} not found",
                    context={'task_id': task_id},
                    recovery="Verify task exists"
                )

            self._transition_state(task, self.STATE_CANCELLED)

            self.state_manager.update_task_status(
                task_id=task_id,
                status=self.STATE_CANCELLED,
                metadata={
                    'reason': reason,
                    'cancelled_at': datetime.now(UTC).isoformat()
                }
            )

            logger.info(f"Task {task_id} cancelled: {reason}")

    def get_ready_tasks(self, project_id: int) -> List[Task]:
        """Get all ready tasks for a project.

        Args:
            project_id: Project ID

        Returns:
            List of ready tasks
        """
        with self._lock:
            ready_queue = self._ready_queues.get(project_id, [])
            task_ids = [task_id for _, task_id in ready_queue]

            tasks = []
            for task_id in task_ids:
                task = self.state_manager.get_task(task_id)
                if task and task.status == self.STATE_READY:
                    tasks.append(task)

            return tasks

    def get_blocked_tasks(self, project_id: int) -> List[Task]:
        """Get all blocked tasks for a project.

        Args:
            project_id: Project ID

        Returns:
            List of blocked tasks
        """
        # Query tasks from state manager
        all_tasks = self.state_manager.get_tasks_by_project(project_id)
        return [t for t in all_tasks if t.status == self.STATE_BLOCKED]

    def detect_deadlock(self, project_id: int) -> Optional[List[Task]]:
        """Detect circular dependencies (deadlock).

        Uses DFS cycle detection on the dependency graph.

        Args:
            project_id: Project ID to check

        Returns:
            List of tasks in deadlock cycle, or None if no deadlock
        """
        with self._lock:
            graph = self._build_dependency_graph(project_id)

            # DFS cycle detection
            visited = set()
            rec_stack = set()
            parent = {}

            def dfs(node: int) -> Optional[List[int]]:
                visited.add(node)
                rec_stack.add(node)

                for neighbor in graph.get(node, []):
                    if neighbor not in visited:
                        parent[neighbor] = node
                        cycle = dfs(neighbor)
                        if cycle:
                            return cycle
                    elif neighbor in rec_stack:
                        # Cycle detected, reconstruct cycle
                        cycle = [neighbor]
                        current = node
                        while current != neighbor:
                            cycle.append(current)
                            current = parent.get(current)
                            if current is None:
                                break
                        return cycle

                rec_stack.remove(node)
                return None

            # Check all nodes
            for node in graph:
                if node not in visited:
                    cycle_ids = dfs(node)
                    if cycle_ids:
                        # Convert IDs to Task objects
                        tasks = []
                        for task_id in cycle_ids:
                            task = self.state_manager.get_task(task_id)
                            if task:
                                tasks.append(task)
                        return tasks if tasks else None

            return None

    def get_task_status(self, task_id: int) -> str:
        """Get task status.

        Args:
            task_id: Task ID

        Returns:
            Task status string

        Raises:
            TaskStateException: If task not found
        """
        task = self.state_manager.get_task(task_id)
        if not task:
            raise TaskStateException(
                f"Task {task_id} not found",
                context={'task_id': task_id},
                recovery="Verify task exists"
            )
        return task.status

    # Private helper methods

    def _transition_state(self, task: Task, new_state: str) -> None:
        """Transition task to new state.

        Args:
            task: Task to transition
            new_state: Target state

        Raises:
            TaskStateException: If transition is invalid
        """
        current_state = task.status

        # Allow initial state setting
        if current_state is None:
            task.status = new_state
            return

        # Check valid transition
        valid_next_states = self.VALID_TRANSITIONS.get(current_state, set())
        if new_state not in valid_next_states:
            raise TaskStateException(
                f"Invalid state transition: {current_state} → {new_state}",
                context={'task_id': task.id, 'current_state': current_state, 'target_state': new_state},
                recovery=f"Valid transitions from {current_state}: {valid_next_states}"
            )

        task.status = new_state
        logger.debug(f"Task {task.id} transitioned: {current_state} → {new_state}")

    def _parse_dependencies(self, task: Task) -> List[int]:
        """Parse task dependencies from metadata.

        Args:
            task: Task to parse dependencies for

        Returns:
            List of dependency task IDs
        """
        if not task.metadata:
            return []

        dependencies_str = task.metadata.get('dependencies', '')
        if not dependencies_str:
            return []

        # Parse comma-separated IDs
        try:
            return [int(dep_id.strip()) for dep_id in dependencies_str.split(',') if dep_id.strip()]
        except ValueError as e:
            logger.warning(f"Invalid dependency format for task {task.id}: {dependencies_str}")
            return []

    def _check_dependencies_satisfied(self, project_id: int, dependency_ids: List[int]) -> bool:
        """Check if all dependencies are completed.

        Args:
            project_id: Project ID
            dependency_ids: List of dependency task IDs

        Returns:
            True if all dependencies completed, False otherwise
        """
        if not dependency_ids:
            return True

        for dep_id in dependency_ids:
            dep_task = self.state_manager.get_task(dep_id)
            if not dep_task or dep_task.status != self.STATE_COMPLETED:
                return False

        return True

    def _add_to_ready_queue(self, task: Task) -> None:
        """Add task to ready queue.

        Args:
            task: Task to add
        """
        # Negative priority for max-heap behavior
        priority_key = -task.priority
        heapq.heappush(self._ready_queues[task.project_id], (priority_key, task.id))

    def _apply_priority_boosts(self, project_id: int) -> None:
        """Apply priority boosts based on deadlines and dependencies.

        Args:
            project_id: Project ID
        """
        tasks = self.get_ready_tasks(project_id)

        for task in tasks:
            boost = 0

            # Deadline approaching boost
            if task.deadline:
                time_until_deadline = task.deadline - datetime.now(UTC)
                if time_until_deadline.total_seconds() < 3600:  # Within 1 hour
                    boost += self.DEADLINE_BOOST

            # Blocking others boost
            all_tasks = self.state_manager.get_tasks_by_project(project_id)
            for other_task in all_tasks:
                deps = self._parse_dependencies(other_task)
                if task.id in deps:
                    boost += self.BLOCKING_BOOST
                    break  # Only boost once

            if boost > 0:
                task.priority += boost
                logger.debug(f"Task {task.id} priority boosted by {boost} to {task.priority}")

    def _promote_pending_tasks(self, project_id: int) -> None:
        """Check pending tasks and promote to ready if dependencies satisfied.

        Args:
            project_id: Project ID
        """
        all_tasks = self.state_manager.get_tasks_by_project(project_id)
        pending_tasks = [t for t in all_tasks if t.status == self.STATE_PENDING]

        for task in pending_tasks:
            dependencies = self._parse_dependencies(task)
            if self._check_dependencies_satisfied(project_id, dependencies):
                self._transition_state(task, self.STATE_READY)
                self._add_to_ready_queue(task)
                logger.info(f"Task {task.id} promoted from PENDING to READY")

    def _build_dependency_graph(self, project_id: int) -> Dict[int, List[int]]:
        """Build dependency graph for project.

        Args:
            project_id: Project ID

        Returns:
            Adjacency list representation of dependency graph
        """
        graph = defaultdict(list)
        all_tasks = self.state_manager.get_tasks_by_project(project_id)

        for task in all_tasks:
            graph[task.id] = []  # Ensure all tasks in graph
            dependencies = self._parse_dependencies(task)
            for dep_id in dependencies:
                graph[dep_id].append(task.id)  # dep_id → task.id edge

        return dict(graph)

    def _should_retry(self, error: str, retry_count: int) -> bool:
        """Determine if task should be retried.

        Args:
            error: Error message
            retry_count: Current retry count

        Returns:
            True if should retry, False otherwise
        """
        if retry_count >= self.MAX_RETRIES:
            return False

        # Check for non-retryable errors
        non_retryable_keywords = [
            'validation',
            'authentication',
            'not found',
            'invalid',
            'permission denied'
        ]

        error_lower = error.lower()
        for keyword in non_retryable_keywords:
            if keyword in error_lower:
                return False

        # Retryable by default (transient errors)
        return True

    def _calculate_backoff(self, retry_count: int) -> int:
        """Calculate exponential backoff delay.

        Args:
            retry_count: Current retry count

        Returns:
            Delay in seconds
        """
        return self.BASE_DELAY_SECONDS * (self.EXPONENTIAL_BASE ** retry_count)
