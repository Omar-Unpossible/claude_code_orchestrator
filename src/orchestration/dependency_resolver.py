"""Task dependency resolution with topological sorting and cycle detection.

This module provides the DependencyResolver class for managing task dependencies
including:
- Topological sorting for execution order
- Cycle detection (circular dependencies)
- Dependency validation
- Execution readiness checking
- Visual dependency graph generation

Key Features:
- Kahn's algorithm for topological sort
- DFS-based cycle detection
- Configurable maximum dependency depth
- Thread-safe operations
- ASCII dependency graph visualization

Example:
    >>> from src.core.state import StateManager
    >>> from src.core.config import Config
    >>>
    >>> config = Config.load()
    >>> state_manager = StateManager.get_instance('sqlite:///test.db')
    >>> resolver = DependencyResolver(state_manager, config)
    >>>
    >>> # Check if task is ready to execute
    >>> is_ready = resolver.is_task_ready(task_id=5)
    >>>
    >>> # Get execution order for all tasks
    >>> order = resolver.get_execution_order(project_id=1)
    >>> print(f"Execute tasks in order: {order}")
"""

import logging
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Dict, List, Set, Optional, Tuple, Any
from threading import RLock

from src.core.models import Task, TaskStatus

logger = logging.getLogger(__name__)


@dataclass
class DependencyConfig:
    """Configuration for dependency resolution.

    Attributes:
        max_depth: Maximum dependency chain depth
        allow_cycles: Whether to allow circular dependencies
        fail_on_dependency_error: Fail task if dependency fails
    """
    max_depth: int = 10
    allow_cycles: bool = False
    fail_on_dependency_error: bool = True


class DependencyException(Exception):
    """Base exception for dependency resolution errors."""

    def __init__(self, message: str, task_id: Optional[int] = None, context: Optional[Dict] = None):
        """Initialize exception.

        Args:
            message: Error message
            task_id: Task ID related to error
            context: Additional context
        """
        super().__init__(message)
        self.task_id = task_id
        self.context = context or {}


class CircularDependencyError(DependencyException):
    """Raised when circular dependency is detected."""

    def __init__(self, cycle: List[int]):
        """Initialize exception.

        Args:
            cycle: List of task IDs forming the cycle
        """
        cycle_str = ' → '.join(str(tid) for tid in cycle)
        super().__init__(
            f"Circular dependency detected: {cycle_str}",
            context={'cycle': cycle}
        )
        self.cycle = cycle


class MaxDepthExceededError(DependencyException):
    """Raised when dependency depth exceeds maximum."""

    def __init__(self, task_id: int, depth: int, max_depth: int):
        """Initialize exception.

        Args:
            task_id: Task ID that exceeded depth
            depth: Actual depth reached
            max_depth: Maximum allowed depth
        """
        super().__init__(
            f"Task {task_id} dependency depth {depth} exceeds maximum {max_depth}",
            task_id=task_id,
            context={'depth': depth, 'max_depth': max_depth}
        )


class DependencyResolver:
    """Resolves task dependencies with topological sorting and cycle detection.

    This class manages task dependency graphs, ensuring tasks are executed in
    the correct order and detecting circular dependencies.

    Thread-safe for concurrent use.

    Example:
        >>> resolver = DependencyResolver(state_manager, config)
        >>>
        >>> # Validate dependencies before adding
        >>> resolver.validate_dependency(task_id=5, depends_on=3)
        >>>
        >>> # Get execution order
        >>> order = resolver.get_execution_order(project_id=1)
        >>> for task_id in order:
        ...     execute_task(task_id)
    """

    def __init__(self, state_manager: Any, config: Any):
        """Initialize dependency resolver.

        Args:
            state_manager: StateManager instance for task access
            config: Configuration object
        """
        self.state_manager = state_manager
        self._lock = RLock()

        # Load dependency configuration
        dep_config = config.get('dependencies', {})
        self.config = DependencyConfig(
            max_depth=dep_config.get('max_depth', 10),
            allow_cycles=dep_config.get('allow_cycles', False),
            fail_on_dependency_error=dep_config.get('fail_on_dependency_error', True)
        )

        logger.info(
            f"DependencyResolver initialized: max_depth={self.config.max_depth}, "
            f"allow_cycles={self.config.allow_cycles}"
        )

    def validate_dependency(
        self,
        task_id: int,
        depends_on: int
    ) -> Tuple[bool, Optional[str]]:
        """Validate a dependency before adding it.

        Args:
            task_id: Task that will depend on another
            depends_on: Task that will be depended on

        Returns:
            Tuple of (is_valid, error_message)

        Example:
            >>> valid, error = resolver.validate_dependency(5, 3)
            >>> if not valid:
            ...     print(f"Invalid dependency: {error}")
        """
        with self._lock:
            # Check if tasks exist
            try:
                task = self.state_manager.get_task(task_id)
                dependency_task = self.state_manager.get_task(depends_on)
            except Exception as e:
                return False, f"Task not found: {e}"

            # Check same project
            if task.project_id != dependency_task.project_id:
                return False, f"Tasks must be in same project"

            # Check not depending on self
            if task_id == depends_on:
                return False, f"Task cannot depend on itself"

            # Temporarily add dependency for validation
            temp_deps = task.get_dependencies() + [depends_on]

            # Check if this would create a cycle
            if not self.config.allow_cycles:
                if self._would_create_cycle(task_id, temp_deps):
                    return False, f"Adding dependency would create a circular dependency"

            # Check depth limit
            depth = self._calculate_dependency_depth(task_id, temp_deps)
            if depth > self.config.max_depth:
                return False, f"Dependency depth {depth} exceeds maximum {self.config.max_depth}"

            return True, None

    def is_task_ready(self, task_id: int) -> bool:
        """Check if task is ready to execute (all dependencies completed).

        Args:
            task_id: Task ID to check

        Returns:
            True if task can execute, False if blocked by dependencies

        Example:
            >>> if resolver.is_task_ready(5):
            ...     execute_task(5)
            ... else:
            ...     print("Task is blocked by dependencies")
        """
        with self._lock:
            task = self.state_manager.get_task(task_id)

            # No dependencies = ready
            if not task.has_dependencies():
                return True

            # Check all dependencies
            for dep_id in task.get_dependencies():
                try:
                    dep_task = self.state_manager.get_task(dep_id)

                    # Dependency must be completed
                    if dep_task.status != TaskStatus.COMPLETED:
                        logger.debug(
                            f"Task {task_id} blocked by dependency {dep_id} "
                            f"(status: {dep_task.status.value})"
                        )
                        return False

                    # Check if dependency failed
                    if self.config.fail_on_dependency_error and dep_task.status == TaskStatus.FAILED:
                        logger.warning(
                            f"Task {task_id} blocked by failed dependency {dep_id}"
                        )
                        return False

                except Exception as e:
                    logger.error(f"Error checking dependency {dep_id}: {e}")
                    return False

            return True

    def get_blocked_tasks(self, project_id: int) -> List[int]:
        """Get list of tasks blocked by dependencies.

        Args:
            project_id: Project ID

        Returns:
            List of task IDs that are blocked

        Example:
            >>> blocked = resolver.get_blocked_tasks(project_id=1)
            >>> print(f"{len(blocked)} tasks are blocked")
        """
        with self._lock:
            tasks = self.state_manager.get_tasks_by_project(project_id)
            blocked = []

            for task in tasks:
                if task.status in [TaskStatus.PENDING, TaskStatus.READY]:
                    if task.has_dependencies() and not self.is_task_ready(task.id):
                        blocked.append(task.id)

            return blocked

    def get_execution_order(
        self,
        project_id: int,
        include_completed: bool = False
    ) -> List[int]:
        """Get topological sort order for task execution.

        Uses Kahn's algorithm for topological sorting.

        Args:
            project_id: Project ID
            include_completed: Include completed tasks in result

        Returns:
            List of task IDs in execution order

        Raises:
            CircularDependencyError: If circular dependency detected

        Example:
            >>> order = resolver.get_execution_order(project_id=1)
            >>> print(f"Execute in order: {order}")
        """
        with self._lock:
            tasks = self.state_manager.get_tasks_by_project(project_id)

            # Filter tasks if needed
            if not include_completed:
                tasks = [t for t in tasks if t.status != TaskStatus.COMPLETED]

            # Build adjacency list and in-degree count
            graph = defaultdict(list)  # task_id -> [dependent_task_ids]
            in_degree = defaultdict(int)  # task_id -> count of dependencies
            all_task_ids = set()

            for task in tasks:
                task_id = task.id
                all_task_ids.add(task_id)

                # Initialize in-degree
                if task_id not in in_degree:
                    in_degree[task_id] = 0

                # Add edges
                for dep_id in task.get_dependencies():
                    graph[dep_id].append(task_id)
                    in_degree[task_id] += 1
                    all_task_ids.add(dep_id)

            # Kahn's algorithm for topological sort
            queue = deque([tid for tid in all_task_ids if in_degree[tid] == 0])
            result = []

            while queue:
                task_id = queue.popleft()
                result.append(task_id)

                # Reduce in-degree for dependent tasks
                for dependent_id in graph[task_id]:
                    in_degree[dependent_id] -= 1
                    if in_degree[dependent_id] == 0:
                        queue.append(dependent_id)

            # Check if all tasks were processed (no cycles)
            if len(result) != len(all_task_ids):
                # Find cycle
                cycle = self._find_cycle(graph, all_task_ids, result)
                raise CircularDependencyError(cycle)

            return result

    def _would_create_cycle(
        self,
        task_id: int,
        dependencies: List[int]
    ) -> bool:
        """Check if adding dependencies would create a cycle.

        Args:
            task_id: Task ID
            dependencies: List of dependency task IDs

        Returns:
            True if cycle would be created
        """
        # Build temporary graph
        visited = set()
        rec_stack = set()

        def has_cycle_dfs(node: int) -> bool:
            """DFS to detect cycle."""
            visited.add(node)
            rec_stack.add(node)

            # Get neighbors
            if node == task_id:
                neighbors = dependencies
            else:
                try:
                    neighbor_task = self.state_manager.get_task(node)
                    neighbors = neighbor_task.get_dependencies()
                except Exception:
                    neighbors = []

            for neighbor in neighbors:
                if neighbor not in visited:
                    if has_cycle_dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        return has_cycle_dfs(task_id)

    def _calculate_dependency_depth(
        self,
        task_id: int,
        dependencies: Optional[List[int]] = None
    ) -> int:
        """Calculate maximum dependency chain depth.

        Args:
            task_id: Task ID
            dependencies: Override dependencies (for validation)

        Returns:
            Maximum depth of dependency chain
        """
        visited = set()

        def dfs_depth(node: int, depth: int) -> int:
            """DFS to calculate max depth."""
            if node in visited:
                return depth

            visited.add(node)

            # Get dependencies
            if node == task_id and dependencies is not None:
                deps = dependencies
            else:
                try:
                    dep_task = self.state_manager.get_task(node)
                    deps = dep_task.get_dependencies()
                except Exception:
                    deps = []

            if not deps:
                return depth

            max_child_depth = depth
            for dep_id in deps:
                child_depth = dfs_depth(dep_id, depth + 1)
                max_child_depth = max(max_child_depth, child_depth)

            return max_child_depth

        return dfs_depth(task_id, 0)

    def _find_cycle(
        self,
        graph: Dict[int, List[int]],
        all_tasks: Set[int],
        processed: List[int]
    ) -> List[int]:
        """Find a cycle in the dependency graph.

        Args:
            graph: Adjacency list
            all_tasks: All task IDs
            processed: Tasks that were processed (not in cycle)

        Returns:
            List of task IDs forming a cycle
        """
        unprocessed = all_tasks - set(processed)

        # DFS from unprocessed nodes to find cycle
        visited = set()
        rec_stack = []

        def dfs(node: int) -> Optional[List[int]]:
            """DFS to find cycle."""
            visited.add(node)
            rec_stack.append(node)

            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    cycle = dfs(neighbor)
                    if cycle:
                        return cycle
                elif neighbor in rec_stack:
                    # Found cycle
                    cycle_start = rec_stack.index(neighbor)
                    return rec_stack[cycle_start:] + [neighbor]

            rec_stack.pop()
            return None

        for node in unprocessed:
            if node not in visited:
                cycle = dfs(node)
                if cycle:
                    return cycle

        # Shouldn't reach here, but return any unprocessed as fallback
        return list(unprocessed)[:3]

    def visualize_dependencies(
        self,
        project_id: int,
        task_id: Optional[int] = None
    ) -> str:
        """Generate ASCII visualization of dependency graph.

        Args:
            project_id: Project ID
            task_id: Optional specific task to visualize

        Returns:
            ASCII art dependency graph

        Example:
            >>> graph = resolver.visualize_dependencies(project_id=1)
            >>> print(graph)
            Task 1: Setup database
            Task 2: Create models
            ├── depends on: Task 1
            Task 3: Create API
            ├── depends on: Task 2
            └── depends on: Task 1
        """
        with self._lock:
            if task_id:
                tasks = [self.state_manager.get_task(task_id)]
            else:
                tasks = self.state_manager.get_tasks_by_project(project_id)

            lines = []
            for task in tasks:
                lines.append(f"Task {task.id}: {task.title}")

                if task.has_dependencies():
                    deps = task.get_dependencies()
                    for i, dep_id in enumerate(deps):
                        try:
                            dep_task = self.state_manager.get_task(dep_id)
                            prefix = '└──' if i == len(deps) - 1 else '├──'
                            status_marker = '✓' if dep_task.status == TaskStatus.COMPLETED else '○'
                            lines.append(
                                f"  {prefix} {status_marker} depends on: "
                                f"Task {dep_id} ({dep_task.title[:30]}...)"
                            )
                        except Exception as e:
                            lines.append(f"  ├── ✗ depends on: Task {dep_id} (not found)")

                lines.append("")  # Empty line between tasks

            return '\n'.join(lines)


def create_dependency_resolver(state_manager: Any, config: Any) -> DependencyResolver:
    """Factory function to create DependencyResolver.

    Args:
        state_manager: StateManager instance
        config: Configuration object

    Returns:
        Configured DependencyResolver instance

    Example:
        >>> resolver = create_dependency_resolver(state_manager, config)
    """
    return DependencyResolver(state_manager, config)
