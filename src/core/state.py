"""StateManager - Single source of truth for all application state.

This module provides the StateManager singleton that manages all state operations.
ALL components must access state through StateManager - no direct database access.

Critical Design Principles:
1. Single source of truth - all state goes through StateManager
2. Thread-safe by default - all public methods are locked
3. Transaction support - context managers for atomic operations
4. Fail-safe - errors trigger rollback
5. Auditable - every change is logged
"""

import logging
from contextlib import contextmanager
from threading import RLock
from typing import Optional, List, Dict, Any
from datetime import datetime, UTC, timedelta

from sqlalchemy import create_engine, desc, func, case
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

from src.core.models import (
    Base, ProjectState, Task, Interaction, Checkpoint,
    BreakpointEvent, UsageTracking, FileState, PatternLearning,
    ParameterEffectiveness, PromptRuleViolation, ComplexityEstimate,
    ParallelAgentAttempt,
    TaskStatus, TaskAssignee, InteractionSource, BreakpointSeverity,
    ProjectStatus
)
from src.core.exceptions import (
    StateManagerException, DatabaseException, TransactionException,
    CheckpointException
)

logger = logging.getLogger(__name__)


class StateManager:
    """Thread-safe singleton for all state management operations.

    The StateManager is the ONLY way to access and modify application state.
    It provides:
    - CRUD operations for all entities
    - Transaction support
    - Checkpoint/restore capability
    - Event emission
    - Thread safety

    Example:
        >>> state_manager = StateManager(database_url='sqlite:///test.db')
        >>> project = state_manager.create_project(
        ...     name='test',
        ...     description='Test project',
        ...     working_dir='/tmp/test'
        ... )
        >>> task = state_manager.create_task(project.id, {
        ...     'title': 'Test task',
        ...     'description': 'Do something'
        ... })
    """

    _instance: Optional['StateManager'] = None
    _lock = RLock()

    def __init__(self, database_url: str, echo: bool = False):
        """Initialize StateManager.

        Note: Use StateManager.get_instance() instead of direct instantiation
        to ensure singleton behavior.

        Args:
            database_url: Database connection URL
            echo: Whether to log SQL queries
        """
        self._database_url = database_url
        self._echo = echo

        # Create engine with connection pooling
        # SQLite doesn't support pool_size/max_overflow
        engine_kwargs = {
            'echo': echo,
            'pool_pre_ping': True,  # Verify connections before using
        }
        if not database_url.startswith('sqlite'):
            engine_kwargs['pool_size'] = 10
            engine_kwargs['max_overflow'] = 20

        self._engine = create_engine(database_url, **engine_kwargs)

        # Create session factory
        self._SessionLocal = sessionmaker(
            bind=self._engine,
            autocommit=False,
            autoflush=False
        )

        # Thread-local session
        self._session: Optional[Session] = None

        # Transaction depth tracking (for nested transaction support)
        self._transaction_depth = 0

        # Create tables
        Base.metadata.create_all(self._engine)

        logger.info(f"StateManager initialized with database: {database_url}")

    @classmethod
    def get_instance(
        cls,
        database_url: Optional[str] = None,
        echo: bool = False
    ) -> 'StateManager':
        """Get or create StateManager singleton instance.

        Thread-safe factory method.

        Args:
            database_url: Database URL (required on first call)
            echo: Whether to log SQL queries

        Returns:
            StateManager instance

        Example:
            >>> sm = StateManager.get_instance('sqlite:///data/db.sqlite')
        """
        with cls._lock:
            if cls._instance is None:
                if database_url is None:
                    raise StateManagerException(
                        "database_url required for first initialization",
                        recovery="Provide database_url parameter"
                    )
                cls._instance = cls(database_url, echo)
            return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton instance (for testing only).

        Example:
            >>> StateManager.reset_instance()  # In test teardown
        """
        with cls._lock:
            if cls._instance and cls._instance._session:
                cls._instance._session.close()
            cls._instance = None

    def _get_session(self) -> Session:
        """Get or create session for current thread.

        Returns:
            SQLAlchemy session
        """
        if self._session is None:
            self._session = self._SessionLocal()
        return self._session

    @contextmanager
    def transaction(self):
        """Context manager for database transactions.

        Ensures atomic operations - all changes committed together or rolled back.
        Supports nested transactions - only commits at outermost level.

        Example:
            >>> with state_manager.transaction():
            ...     state_manager.create_task(project_id, task_data)
            ...     state_manager.record_interaction(project_id, task_id, interaction_data)
            ... # Both committed together, or both rolled back on error
        """
        session = self._get_session()
        self._transaction_depth += 1
        is_outermost = (self._transaction_depth == 1)

        try:
            yield session
            # Only commit at the outermost transaction level
            if is_outermost:
                session.commit()
                logger.debug("Transaction committed")
        except Exception as e:
            # Only rollback at the outermost transaction level
            if is_outermost:
                session.rollback()
                logger.error(f"Transaction rolled back: {e}")
            self._transaction_depth = 0  # Reset on error
            raise TransactionException(
                reason=str(e),
                operations=['transaction']
            ) from e
        finally:
            self._transaction_depth -= 1

    # Project Management

    def create_project(
        self,
        name: str,
        description: str,
        working_dir: str,
        config: Optional[Dict[str, Any]] = None
    ) -> ProjectState:
        """Create a new project.

        Args:
            name: Project name (must be unique)
            description: Project description
            working_dir: Working directory path
            config: Optional configuration dictionary

        Returns:
            Created ProjectState

        Raises:
            DatabaseException: If creation fails

        Example:
            >>> project = state_manager.create_project(
            ...     name='my-project',
            ...     description='My awesome project',
            ...     working_dir='/tmp/my-project'
            ... )
        """
        with self._lock:
            try:
                with self.transaction():
                    project = ProjectState(
                        project_name=name,
                        description=description,
                        working_directory=working_dir,
                        configuration=config or {},
                        status=ProjectStatus.ACTIVE
                    )
                    session = self._get_session()
                    session.add(project)
                    session.flush()  # Get ID
                    logger.info(f"Created project: {project.id} ({name})")
                    return project
            except SQLAlchemyError as e:
                raise DatabaseException(
                    operation='create_project',
                    details=str(e)
                ) from e

    def get_project(self, project_id: int) -> Optional[ProjectState]:
        """Get project by ID.

        Args:
            project_id: Project ID

        Returns:
            ProjectState or None if not found
        """
        with self._lock:
            session = self._get_session()
            return session.query(ProjectState).filter(
                ProjectState.id == project_id,
                ProjectState.is_deleted == False
            ).first()

    def list_projects(
        self,
        status: Optional[ProjectStatus] = None
    ) -> List[ProjectState]:
        """List all projects.

        Args:
            status: Optional status filter

        Returns:
            List of projects
        """
        with self._lock:
            session = self._get_session()
            query = session.query(ProjectState).filter(
                ProjectState.is_deleted == False
            )

            if status:
                query = query.filter(ProjectState.status == status)

            return query.order_by(desc(ProjectState.created_at)).all()

    def update_project(
        self,
        project_id: int,
        updates: Dict[str, Any]
    ) -> ProjectState:
        """Update project.

        Args:
            project_id: Project ID
            updates: Dictionary of fields to update

        Returns:
            Updated ProjectState

        Raises:
            DatabaseException: If update fails
        """
        with self._lock:
            try:
                with self.transaction():
                    project = self.get_project(project_id)
                    if not project:
                        raise DatabaseException(
                            operation='update_project',
                            details=f'Project {project_id} not found'
                        )

                    for key, value in updates.items():
                        if hasattr(project, key):
                            setattr(project, key, value)

                    logger.info(f"Updated project {project_id}: {updates}")
                    return project
            except SQLAlchemyError as e:
                raise DatabaseException(
                    operation='update_project',
                    details=str(e)
                ) from e

    def delete_project(self, project_id: int, soft: bool = True) -> None:
        """Delete project.

        Args:
            project_id: Project ID
            soft: If True, soft delete (set is_deleted=True)
        """
        with self._lock:
            try:
                with self.transaction():
                    project = self.get_project(project_id)
                    if not project:
                        return

                    if soft:
                        project.is_deleted = True
                        logger.info(f"Soft deleted project {project_id}")
                    else:
                        session = self._get_session()
                        session.delete(project)
                        logger.info(f"Hard deleted project {project_id}")
            except SQLAlchemyError as e:
                raise DatabaseException(
                    operation='delete_project',
                    details=str(e)
                ) from e

    # Task Management

    def create_task(
        self,
        project_id: int,
        task_data: Dict[str, Any]
    ) -> Task:
        """Create a new task.

        Args:
            project_id: Project ID
            task_data: Task data dictionary with keys:
                - title (required)
                - description (required)
                - priority (optional, default 5)
                - assigned_to (optional, default CLAUDE_CODE)
                - dependencies (optional, list of task IDs)
                - context (optional, dict)

        Returns:
            Created Task

        Raises:
            DatabaseException: If creation fails
        """
        with self._lock:
            try:
                with self.transaction():
                    task = Task(
                        project_id=project_id,
                        title=task_data['title'],
                        description=task_data['description'],
                        priority=task_data.get('priority', 5),
                        assigned_to=task_data.get('assigned_to', TaskAssignee.CLAUDE_CODE),
                        dependencies=task_data.get('dependencies', []),
                        context=task_data.get('context', {}),
                        status=TaskStatus.PENDING,
                        parent_task_id=task_data.get('parent_task_id')
                    )
                    session = self._get_session()
                    session.add(task)
                    session.flush()
                    logger.info(f"Created task: {task.id} ({task.title})")
                    return task
            except SQLAlchemyError as e:
                raise DatabaseException(
                    operation='create_task',
                    details=str(e)
                ) from e

    def get_task(self, task_id: int) -> Optional[Task]:
        """Get task by ID.

        Args:
            task_id: Task ID

        Returns:
            Task or None
        """
        with self._lock:
            session = self._get_session()
            return session.query(Task).filter(
                Task.id == task_id,
                Task.is_deleted == False
            ).first()

    def update_task_status(
        self,
        task_id: int,
        status: TaskStatus,
        metadata: Optional[Dict] = None
    ) -> Task:
        """Update task status.

        Args:
            task_id: Task ID
            status: New status
            metadata: Optional metadata to update

        Returns:
            Updated Task
        """
        with self._lock:
            try:
                with self.transaction():
                    task = self.get_task(task_id)
                    if not task:
                        raise DatabaseException(
                            operation='update_task_status',
                            details=f'Task {task_id} not found'
                        )

                    task.status = status

                    # Update timestamps based on status
                    if status == TaskStatus.RUNNING and not task.started_at:
                        task.started_at = datetime.now(UTC)
                    elif status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
                        task.completed_at = datetime.now(UTC)

                    # Update metadata
                    if metadata:
                        for key, value in metadata.items():
                            if hasattr(task, key):
                                setattr(task, key, value)

                    logger.info(f"Updated task {task_id} status: {status.value}")
                    return task
            except SQLAlchemyError as e:
                raise DatabaseException(
                    operation='update_task_status',
                    details=str(e)
                ) from e

    def get_tasks_by_status(
        self,
        project_id: int,
        status: TaskStatus
    ) -> List[Task]:
        """Get tasks by status.

        Args:
            project_id: Project ID
            status: Task status

        Returns:
            List of tasks
        """
        with self._lock:
            session = self._get_session()
            return session.query(Task).filter(
                Task.project_id == project_id,
                Task.status == status,
                Task.is_deleted == False
            ).order_by(desc(Task.priority), Task.created_at).all()

    def list_tasks(
        self,
        project_id: Optional[int] = None,
        status: Optional[TaskStatus] = None,
        limit: Optional[int] = None
    ) -> List[Task]:
        """Get all tasks with optional filtering.

        Args:
            project_id: Filter by project ID (None = all projects)
            status: Filter by status (None = all statuses)
            limit: Maximum number of tasks to return (None = no limit)

        Returns:
            List of tasks matching criteria, ordered by priority and created date

        Example:
            >>> # Get all tasks
            >>> all_tasks = state_manager.list_tasks()
            >>> # Get all pending tasks
            >>> pending = state_manager.list_tasks(status='pending')
            >>> # Get tasks for project 1
            >>> project_tasks = state_manager.list_tasks(project_id=1)
        """
        with self._lock:
            session = self._get_session()
            query = session.query(Task).filter(Task.is_deleted == False)

            # Apply filters
            if project_id is not None:
                query = query.filter(Task.project_id == project_id)
            if status is not None:
                query = query.filter(Task.status == status)

            # Order by priority (desc) and created date
            query = query.order_by(desc(Task.priority), Task.created_at)

            # Apply limit
            if limit is not None:
                query = query.limit(limit)

            return query.all()

    def get_project_tasks(
        self,
        project_id: int,
        status: Optional[TaskStatus] = None
    ) -> List[Task]:
        """Get all tasks for a specific project.

        Args:
            project_id: Project ID
            status: Optional status filter (None = all statuses)

        Returns:
            List of tasks in the project

        Example:
            >>> # Get all tasks in project 1
            >>> tasks = state_manager.get_project_tasks(1)
            >>> # Get only pending tasks in project 1
            >>> pending = state_manager.get_project_tasks(1, status='pending')
        """
        return self.list_tasks(project_id=project_id, status=status)

    # M9: Task Dependency Management

    def add_task_dependency(
        self,
        task_id: int,
        depends_on: int
    ) -> Task:
        """Add a dependency to a task (M9).

        Args:
            task_id: Task that will depend on another
            depends_on: Task ID that will be depended on

        Returns:
            Updated task

        Raises:
            StateManagerException: If operation fails

        Example:
            >>> # Task 5 depends on task 3
            >>> task = state_manager.add_task_dependency(5, 3)
        """
        with self._lock:
            try:
                with self.transaction():
                    task = self.get_task(task_id)
                    if not task:
                        raise StateManagerException(
                            operation='add_task_dependency',
                            details=f'Task {task_id} not found'
                        )

                    task.add_dependency(depends_on)
                    session = self._get_session()
                    session.flush()

                    logger.debug(f"Added dependency: task {task_id} depends on {depends_on}")
                    return task
            except SQLAlchemyError as e:
                raise DatabaseException(
                    operation='add_task_dependency',
                    details=str(e)
                ) from e

    def remove_task_dependency(
        self,
        task_id: int,
        depends_on: int
    ) -> Task:
        """Remove a dependency from a task (M9).

        Args:
            task_id: Task ID
            depends_on: Dependency task ID to remove

        Returns:
            Updated task

        Example:
            >>> task = state_manager.remove_task_dependency(5, 3)
        """
        with self._lock:
            try:
                with self.transaction():
                    task = self.get_task(task_id)
                    if not task:
                        raise StateManagerException(
                            operation='remove_task_dependency',
                            details=f'Task {task_id} not found'
                        )

                    task.remove_dependency(depends_on)
                    session = self._get_session()
                    session.flush()

                    logger.debug(f"Removed dependency: task {task_id} no longer depends on {depends_on}")
                    return task
            except SQLAlchemyError as e:
                raise DatabaseException(
                    operation='remove_task_dependency',
                    details=str(e)
                ) from e

    def get_task_dependencies(
        self,
        task_id: int
    ) -> List[Task]:
        """Get all tasks that a task depends on (M9).

        Args:
            task_id: Task ID

        Returns:
            List of Task objects this task depends on

        Example:
            >>> deps = state_manager.get_task_dependencies(5)
            >>> print(f"Task 5 depends on {len(deps)} tasks")
        """
        with self._lock:
            task = self.get_task(task_id)
            if not task:
                return []

            dep_ids = task.get_dependencies()
            if not dep_ids:
                return []

            # Fetch all dependency tasks
            session = self._get_session()
            return session.query(Task).filter(Task.id.in_(dep_ids)).all()

    def get_dependent_tasks(
        self,
        task_id: int
    ) -> List[Task]:
        """Get all tasks that depend on this task (M9).

        Args:
            task_id: Task ID

        Returns:
            List of tasks that depend on this task

        Example:
            >>> dependents = state_manager.get_dependent_tasks(3)
            >>> print(f"{len(dependents)} tasks depend on task 3")
        """
        with self._lock:
            task = self.get_task(task_id)
            if not task:
                return []

            # Find all tasks in same project that have this task in their dependencies
            session = self._get_session()
            all_tasks = session.query(Task).filter(
                Task.project_id == task.project_id,
                Task.is_deleted == False  # noqa: E712
            ).all()

            dependents = []
            for t in all_tasks:
                if task_id in t.get_dependencies():
                    dependents.append(t)

            return dependents

    def get_tasks_by_project(
        self,
        project_id: int
    ) -> List[Task]:
        """Get all tasks for a project (M9 - alias for dependency resolver).

        Args:
            project_id: Project ID

        Returns:
            List of all tasks in project

        Example:
            >>> tasks = state_manager.get_tasks_by_project(1)
        """
        return self.get_project_tasks(project_id)

    # Interaction Management

    def record_interaction(
        self,
        project_id: int,
        task_id: Optional[int],
        interaction_data: Dict[str, Any]
    ) -> Interaction:
        """Record an agent/LLM interaction.

        Args:
            project_id: Project ID
            task_id: Task ID (optional)
            interaction_data: Interaction data with keys:
                - source (required): InteractionSource
                - prompt (required): str
                - response (optional): str
                - confidence_score (optional): float
                - quality_score (optional): float
                - duration_seconds (optional): float

        Returns:
            Created Interaction
        """
        with self._lock:
            try:
                with self.transaction():
                    interaction = Interaction(
                        project_id=project_id,
                        task_id=task_id,
                        source=interaction_data['source'],
                        prompt=interaction_data['prompt'],
                        response=interaction_data.get('response'),
                        confidence_score=interaction_data.get('confidence_score'),
                        quality_score=interaction_data.get('quality_score'),
                        duration_seconds=interaction_data.get('duration_seconds'),
                        context=interaction_data.get('context', {})
                    )
                    session = self._get_session()
                    session.add(interaction)
                    session.flush()
                    logger.debug(f"Recorded interaction: {interaction.id}")
                    return interaction
            except SQLAlchemyError as e:
                raise DatabaseException(
                    operation='record_interaction',
                    details=str(e)
                ) from e

    def get_interactions(
        self,
        project_id: int,
        limit: int = 100
    ) -> List[Interaction]:
        """Get recent interactions for project.

        Args:
            project_id: Project ID
            limit: Maximum number to return

        Returns:
            List of interactions (most recent first)
        """
        with self._lock:
            session = self._get_session()
            return session.query(Interaction).filter(
                Interaction.project_id == project_id
            ).order_by(desc(Interaction.timestamp)).limit(limit).all()

    def get_task_interactions(self, task_id: int) -> List[Interaction]:
        """Get all interactions for a task.

        Args:
            task_id: Task ID

        Returns:
            List of interactions
        """
        with self._lock:
            session = self._get_session()
            return session.query(Interaction).filter(
                Interaction.task_id == task_id
            ).order_by(Interaction.timestamp).all()

    # Checkpoint Management

    def create_checkpoint(
        self,
        project_id: int,
        checkpoint_type: str,
        description: Optional[str] = None
    ) -> Checkpoint:
        """Create a state checkpoint for rollback capability.

        Args:
            project_id: Project ID
            checkpoint_type: Type of checkpoint
            description: Optional description

        Returns:
            Created Checkpoint

        Raises:
            CheckpointException: If creation fails
        """
        with self._lock:
            try:
                with self.transaction():
                    # Snapshot current state
                    project = self.get_project(project_id)
                    if not project:
                        raise CheckpointException(
                            operation='create',
                            checkpoint_id='<new>',
                            details=f'Project {project_id} not found'
                        )

                    # Create snapshot (simplified - full implementation would serialize all state)
                    state_snapshot = {
                        'project': project.to_dict(),
                        'timestamp': datetime.now(UTC).isoformat()
                    }

                    checkpoint = Checkpoint(
                        project_id=project_id,
                        checkpoint_type=checkpoint_type,
                        description=description,
                        state_snapshot=state_snapshot
                    )

                    session = self._get_session()
                    session.add(checkpoint)
                    session.flush()

                    logger.info(f"Created checkpoint: {checkpoint.id} ({checkpoint_type})")
                    return checkpoint
            except SQLAlchemyError as e:
                raise CheckpointException(
                    operation='create',
                    checkpoint_id='<new>',
                    details=str(e)
                ) from e

    def list_checkpoints(
        self,
        project_id: int,
        limit: int = 10
    ) -> List[Checkpoint]:
        """List checkpoints for project.

        Args:
            project_id: Project ID
            limit: Maximum number to return

        Returns:
            List of checkpoints (most recent first)
        """
        with self._lock:
            session = self._get_session()
            return session.query(Checkpoint).filter(
                Checkpoint.project_id == project_id
            ).order_by(desc(Checkpoint.created_at)).limit(limit).all()

    # Breakpoint Management

    def log_breakpoint_event(
        self,
        project_id: int,
        task_id: Optional[int],
        breakpoint_data: Dict[str, Any]
    ) -> BreakpointEvent:
        """Log a breakpoint event.

        Args:
            project_id: Project ID
            task_id: Task ID (optional)
            breakpoint_data: Breakpoint data with keys:
                - breakpoint_type (required): str
                - reason (required): str
                - severity (optional): BreakpointSeverity
                - context (optional): dict

        Returns:
            Created BreakpointEvent
        """
        with self._lock:
            try:
                with self.transaction():
                    event = BreakpointEvent(
                        project_id=project_id,
                        task_id=task_id,
                        breakpoint_type=breakpoint_data['breakpoint_type'],
                        reason=breakpoint_data['reason'],
                        severity=breakpoint_data.get('severity', BreakpointSeverity.MEDIUM),
                        context=breakpoint_data.get('context', {})
                    )
                    session = self._get_session()
                    session.add(event)
                    session.flush()
                    logger.warning(f"Breakpoint triggered: {event.id} - {event.reason}")
                    return event
            except SQLAlchemyError as e:
                raise DatabaseException(
                    operation='log_breakpoint_event',
                    details=str(e)
                ) from e

    def resolve_breakpoint(
        self,
        breakpoint_id: int,
        resolution: str,
        resolved_by: str
    ) -> BreakpointEvent:
        """Resolve a breakpoint.

        Args:
            breakpoint_id: Breakpoint event ID
            resolution: Resolution description
            resolved_by: Who resolved it

        Returns:
            Updated BreakpointEvent
        """
        with self._lock:
            try:
                with self.transaction():
                    session = self._get_session()
                    event = session.query(BreakpointEvent).get(breakpoint_id)
                    if not event:
                        raise DatabaseException(
                            operation='resolve_breakpoint',
                            details=f'Breakpoint {breakpoint_id} not found'
                        )

                    event.resolved = True
                    event.resolution = resolution
                    event.resolved_by = resolved_by
                    event.resolved_at = datetime.now(UTC)

                    logger.info(f"Resolved breakpoint {breakpoint_id}")
                    return event
            except SQLAlchemyError as e:
                raise DatabaseException(
                    operation='resolve_breakpoint',
                    details=str(e)
                ) from e

    # File State Management

    def record_file_change(
        self,
        project_id: int,
        task_id: Optional[int],
        file_path: str,
        file_hash: str,
        file_size: int,
        change_type: str
    ) -> FileState:
        """Record a file change.

        Args:
            project_id: Project ID
            task_id: Task ID (optional)
            file_path: File path
            file_hash: SHA-256 hash
            file_size: File size in bytes
            change_type: 'created', 'modified', or 'deleted'

        Returns:
            Created FileState
        """
        with self._lock:
            try:
                with self.transaction():
                    file_state = FileState(
                        project_id=project_id,
                        task_id=task_id,
                        file_path=file_path,
                        file_hash=file_hash,
                        file_size=file_size,
                        change_type=change_type
                    )
                    session = self._get_session()
                    session.add(file_state)
                    session.flush()
                    logger.debug(f"Recorded file change: {file_path} ({change_type})")
                    return file_state
            except SQLAlchemyError as e:
                raise DatabaseException(
                    operation='record_file_change',
                    details=str(e)
                ) from e

    def get_file_changes(
        self,
        project_id: int,
        since: Optional[datetime] = None
    ) -> List[FileState]:
        """Get file changes for project.

        Args:
            project_id: Project ID
            since: Optional timestamp to filter from

        Returns:
            List of file states
        """
        with self._lock:
            session = self._get_session()
            query = session.query(FileState).filter(
                FileState.project_id == project_id
            )

            if since:
                query = query.filter(FileState.created_at >= since)

            return query.order_by(desc(FileState.created_at)).all()

    # Parameter Effectiveness Tracking (TASK_2.1.3)

    def log_parameter_usage(
        self,
        template_name: str,
        parameter_name: str,
        was_included: bool,
        token_count: int,
        task_id: Optional[int] = None,
        prompt_token_count: Optional[int] = None
    ) -> None:
        """Log parameter usage for effectiveness tracking.

        Args:
            template_name: Template used (e.g., 'validation')
            parameter_name: Parameter name (e.g., 'file_changes')
            was_included: Whether parameter fit in token budget
            token_count: Tokens used by this parameter
            task_id: Associated task ID
            prompt_token_count: Total prompt tokens
        """
        with self._lock:
            try:
                session = self._get_session()
                record = ParameterEffectiveness(
                    template_name=template_name,
                    parameter_name=parameter_name,
                    was_included=was_included,
                    task_id=task_id,
                    parameter_token_count=token_count,
                    prompt_token_count=prompt_token_count,
                    validation_accurate=None  # Set later via update
                )
                session.add(record)
                session.commit()
                logger.debug(
                    f"Logged parameter usage: {template_name}.{parameter_name} "
                    f"(included={was_included}, tokens={token_count})"
                )
            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"Failed to log parameter usage: {e}")
                raise DatabaseException(
                    operation='log_parameter_usage',
                    details=str(e)
                ) from e

    def update_validation_accuracy(
        self,
        task_id: int,
        was_accurate: bool,
        window_minutes: int = 60
    ) -> int:
        """Update validation accuracy for recent parameter usage.

        When we learn whether a validation was accurate (from human review
        or test results), update all parameter usage records for that task
        within the time window.

        Args:
            task_id: Task ID
            was_accurate: Whether validation was accurate
            window_minutes: Time window to update (default 60 min)

        Returns:
            Number of records updated
        """
        with self._lock:
            try:
                session = self._get_session()
                cutoff = datetime.now(UTC) - timedelta(minutes=window_minutes)

                updated = session.query(ParameterEffectiveness).filter(
                    ParameterEffectiveness.task_id == task_id,
                    ParameterEffectiveness.timestamp >= cutoff,
                    ParameterEffectiveness.validation_accurate.is_(None)
                ).update(
                    {'validation_accurate': was_accurate},
                    synchronize_session=False
                )

                session.commit()
                logger.info(
                    f"Updated {updated} parameter usage records for task {task_id} "
                    f"(accurate={was_accurate})"
                )
                return updated
            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"Failed to update validation accuracy: {e}")
                raise DatabaseException(
                    operation='update_validation_accuracy',
                    details=str(e)
                ) from e

    def get_parameter_effectiveness(
        self,
        template_name: str,
        min_samples: int = 20
    ) -> Dict[str, Dict[str, Any]]:
        """Analyze which parameters correlate with accurate validation.

        Args:
            template_name: Template to analyze (e.g., 'validation')
            min_samples: Minimum samples required per parameter

        Returns:
            Dict mapping parameter names to effectiveness metrics:
            {
                'param_name': {
                    'accuracy_when_included': 0.85,
                    'accuracy_when_excluded': 0.70,
                    'sample_count': 50,
                    'impact_score': 0.15  # Difference in accuracy
                }
            }
        """
        with self._lock:
            try:
                session = self._get_session()

                # Get accuracy when parameter is included
                included = session.query(
                    ParameterEffectiveness.parameter_name,
                    func.avg(
                        case((ParameterEffectiveness.validation_accurate == True, 1.0), else_=0.0)
                    ).label('accuracy'),
                    func.count(ParameterEffectiveness.id).label('count')
                ).filter(
                    ParameterEffectiveness.template_name == template_name,
                    ParameterEffectiveness.was_included == True,
                    ParameterEffectiveness.validation_accurate.isnot(None)
                ).group_by(
                    ParameterEffectiveness.parameter_name
                ).having(
                    func.count(ParameterEffectiveness.id) >= min_samples
                ).all()

                # Get accuracy when parameter is excluded
                excluded = session.query(
                    ParameterEffectiveness.parameter_name,
                    func.avg(
                        case((ParameterEffectiveness.validation_accurate == True, 1.0), else_=0.0)
                    ).label('accuracy')
                ).filter(
                    ParameterEffectiveness.template_name == template_name,
                    ParameterEffectiveness.was_included == False,
                    ParameterEffectiveness.validation_accurate.isnot(None)
                ).group_by(
                    ParameterEffectiveness.parameter_name
                ).all()

                excluded_dict = {param: acc for param, acc in excluded}

                # Build result
                result = {}
                for param, accuracy_included, count in included:
                    accuracy_excluded = excluded_dict.get(param, 0.0)
                    result[param] = {
                        'accuracy_when_included': float(accuracy_included),
                        'accuracy_when_excluded': float(accuracy_excluded),
                        'sample_count': count,
                        'impact_score': float(accuracy_included - accuracy_excluded)
                    }

                return result
            except SQLAlchemyError as e:
                logger.error(f"Failed to get parameter effectiveness: {e}")
                raise DatabaseException(
                    operation='get_parameter_effectiveness',
                    details=str(e)
                ) from e

    # ========================================================================
    # Prompt Rule Violation Methods (LLM-First Framework)
    # ========================================================================

    def log_rule_violation(
        self,
        task_id: int,
        rule_data: Dict[str, Any]
    ) -> PromptRuleViolation:
        """Log a prompt rule violation.

        Args:
            task_id: Task ID where violation occurred
            rule_data: Rule violation data with keys:
                - rule_id (required): str - e.g., "CODE_001"
                - rule_name (required): str
                - rule_domain (required): str - e.g., "code_generation"
                - violation_details (required): dict - Context and specifics
                - severity (required): str - "critical", "high", "medium", "low"
                - resolution_notes (optional): str

        Returns:
            Created PromptRuleViolation

        Raises:
            DatabaseException: If database operation fails

        Example:
            >>> violation = state_manager.log_rule_violation(
            ...     task_id=123,
            ...     rule_data={
            ...         'rule_id': 'CODE_001',
            ...         'rule_name': 'NO_STUBS',
            ...         'rule_domain': 'code_generation',
            ...         'violation_details': {
            ...             'file': '/path/to/file.py',
            ...             'function': 'my_function',
            ...             'line': 42,
            ...             'issue': 'Function contains only pass statement'
            ...         },
            ...         'severity': 'critical'
            ...     }
            ... )
        """
        with self._lock:
            try:
                with self.transaction():
                    violation = PromptRuleViolation(
                        task_id=task_id,
                        rule_id=rule_data['rule_id'],
                        rule_name=rule_data['rule_name'],
                        rule_domain=rule_data['rule_domain'],
                        violation_details=rule_data['violation_details'],
                        severity=rule_data['severity'],
                        resolution_notes=rule_data.get('resolution_notes')
                    )
                    session = self._get_session()
                    session.add(violation)
                    session.flush()
                    logger.warning(
                        f"Rule violation logged: {violation.rule_id} "
                        f"({violation.severity}) in task {task_id}"
                    )
                    return violation
            except SQLAlchemyError as e:
                raise DatabaseException(
                    operation='log_rule_violation',
                    details=str(e)
                ) from e

    def get_rule_violations(
        self,
        task_id: Optional[int] = None,
        rule_id: Optional[str] = None,
        severity: Optional[str] = None,
        resolved: Optional[bool] = None
    ) -> List[PromptRuleViolation]:
        """Get rule violations with optional filters.

        Args:
            task_id: Filter by task ID (optional)
            rule_id: Filter by rule ID (optional)
            severity: Filter by severity (optional)
            resolved: Filter by resolution status (optional)

        Returns:
            List of PromptRuleViolation records

        Example:
            >>> # Get all unresolved critical violations
            >>> violations = state_manager.get_rule_violations(
            ...     severity='critical',
            ...     resolved=False
            ... )
        """
        with self._lock:
            try:
                session = self._get_session()
                query = session.query(PromptRuleViolation)

                if task_id is not None:
                    query = query.filter(PromptRuleViolation.task_id == task_id)
                if rule_id is not None:
                    query = query.filter(PromptRuleViolation.rule_id == rule_id)
                if severity is not None:
                    query = query.filter(PromptRuleViolation.severity == severity)
                if resolved is not None:
                    query = query.filter(PromptRuleViolation.resolved == resolved)

                return query.order_by(desc(PromptRuleViolation.created_at)).all()
            except SQLAlchemyError as e:
                logger.error(f"Failed to get rule violations: {e}")
                raise DatabaseException(
                    operation='get_rule_violations',
                    details=str(e)
                ) from e

    # ========================================================================
    # Complexity Estimate Methods (LLM-First Framework)
    # ========================================================================

    def log_complexity_estimate(
        self,
        task_id: int,
        estimate_data: Dict[str, Any]
    ) -> ComplexityEstimate:
        """Log a task complexity estimate.

        Args:
            task_id: Task ID
            estimate_data: Complexity estimate data with keys:
                - estimated_tokens (required): int
                - estimated_loc (required): int
                - estimated_files (required): int
                - estimated_duration_minutes (required): int
                - overall_complexity_score (required): int (0-100)
                - heuristic_score (required): int (0-100)
                - llm_adjusted_score (optional): int (0-100)
                - should_decompose (required): bool
                - decomposition_reason (optional): str
                - estimation_factors (optional): dict
                - confidence (optional): float (0.0-1.0, default 0.5)

        Returns:
            Created ComplexityEstimate

        Raises:
            DatabaseException: If database operation fails

        Example:
            >>> estimate = state_manager.log_complexity_estimate(
            ...     task_id=123,
            ...     estimate_data={
            ...         'estimated_tokens': 5000,
            ...         'estimated_loc': 250,
            ...         'estimated_files': 3,
            ...         'estimated_duration_minutes': 120,
            ...         'overall_complexity_score': 75,
            ...         'heuristic_score': 70,
            ...         'llm_adjusted_score': 75,
            ...         'should_decompose': True,
            ...         'decomposition_reason': 'Exceeds max_files threshold',
            ...         'confidence': 0.8
            ...     }
            ... )
        """
        with self._lock:
            try:
                with self.transaction():
                    estimate = ComplexityEstimate(
                        task_id=task_id,
                        estimated_tokens=estimate_data['estimated_tokens'],
                        estimated_loc=estimate_data['estimated_loc'],
                        estimated_files=estimate_data['estimated_files'],
                        estimated_duration_minutes=estimate_data['estimated_duration_minutes'],
                        overall_complexity_score=estimate_data['overall_complexity_score'],
                        heuristic_score=estimate_data['heuristic_score'],
                        llm_adjusted_score=estimate_data.get('llm_adjusted_score'),
                        should_decompose=estimate_data['should_decompose'],
                        decomposition_reason=estimate_data.get('decomposition_reason'),
                        estimation_factors=estimate_data.get('estimation_factors', {}),
                        confidence=estimate_data.get('confidence', 0.5)
                    )
                    session = self._get_session()
                    session.add(estimate)
                    session.flush()
                    logger.info(
                        f"Complexity estimate logged for task {task_id}: "
                        f"score={estimate.overall_complexity_score}, "
                        f"decompose={estimate.should_decompose}"
                    )
                    return estimate
            except SQLAlchemyError as e:
                raise DatabaseException(
                    operation='log_complexity_estimate',
                    details=str(e)
                ) from e

    def get_complexity_estimate(self, task_id: int) -> Optional[ComplexityEstimate]:
        """Get complexity estimate for a task.

        Args:
            task_id: Task ID

        Returns:
            ComplexityEstimate or None if not found

        Example:
            >>> estimate = state_manager.get_complexity_estimate(task_id=123)
            >>> if estimate and estimate.should_decompose:
            ...     print(f"Task should be decomposed: {estimate.decomposition_reason}")
        """
        with self._lock:
            try:
                session = self._get_session()
                return session.query(ComplexityEstimate).filter(
                    ComplexityEstimate.task_id == task_id
                ).first()
            except SQLAlchemyError as e:
                logger.error(f"Failed to get complexity estimate for task {task_id}: {e}")
                raise DatabaseException(
                    operation='get_complexity_estimate',
                    details=str(e)
                ) from e

    # ========================================================================
    # Parallel Agent Attempt Methods (LLM-First Framework)
    # ========================================================================

    def log_parallel_attempt(
        self,
        task_id: int,
        attempt_data: Dict[str, Any]
    ) -> ParallelAgentAttempt:
        """Log a parallel agent execution attempt.

        Args:
            task_id: Task ID
            attempt_data: Parallel attempt data with keys:
                - num_agents (required): int
                - agent_ids (required): list of str/int
                - subtask_ids (required): list of int
                - success (required): bool
                - failure_reason (optional): str
                - conflict_detected (optional): bool (default False)
                - conflict_details (optional): dict
                - total_duration_seconds (required): float
                - sequential_estimate_seconds (optional): float
                - speedup_factor (optional): float
                - max_concurrent_agents (required): int
                - total_token_usage (optional): int
                - failed_agent_count (optional): int (default 0)
                - parallelization_strategy (required): str
                - fallback_to_sequential (optional): bool (default False)
                - execution_metadata (optional): dict
                - started_at (required): datetime
                - completed_at (required): datetime

        Returns:
            Created ParallelAgentAttempt

        Raises:
            DatabaseException: If database operation fails

        Example:
            >>> from datetime import datetime, UTC
            >>> attempt = state_manager.log_parallel_attempt(
            ...     task_id=123,
            ...     attempt_data={
            ...         'num_agents': 3,
            ...         'agent_ids': ['agent_1', 'agent_2', 'agent_3'],
            ...         'subtask_ids': [124, 125, 126],
            ...         'success': True,
            ...         'total_duration_seconds': 120.5,
            ...         'sequential_estimate_seconds': 300.0,
            ...         'speedup_factor': 2.49,
            ...         'max_concurrent_agents': 3,
            ...         'parallelization_strategy': 'file_based',
            ...         'started_at': datetime.now(UTC),
            ...         'completed_at': datetime.now(UTC)
            ...     }
            ... )
        """
        with self._lock:
            try:
                with self.transaction():
                    attempt = ParallelAgentAttempt(
                        task_id=task_id,
                        num_agents=attempt_data['num_agents'],
                        agent_ids=attempt_data['agent_ids'],
                        subtask_ids=attempt_data['subtask_ids'],
                        success=attempt_data['success'],
                        failure_reason=attempt_data.get('failure_reason'),
                        conflict_detected=attempt_data.get('conflict_detected', False),
                        conflict_details=attempt_data.get('conflict_details'),
                        total_duration_seconds=attempt_data['total_duration_seconds'],
                        sequential_estimate_seconds=attempt_data.get('sequential_estimate_seconds'),
                        speedup_factor=attempt_data.get('speedup_factor'),
                        max_concurrent_agents=attempt_data['max_concurrent_agents'],
                        total_token_usage=attempt_data.get('total_token_usage'),
                        failed_agent_count=attempt_data.get('failed_agent_count', 0),
                        parallelization_strategy=attempt_data['parallelization_strategy'],
                        fallback_to_sequential=attempt_data.get('fallback_to_sequential', False),
                        execution_metadata=attempt_data.get('execution_metadata', {}),
                        started_at=attempt_data['started_at'],
                        completed_at=attempt_data['completed_at']
                    )
                    session = self._get_session()
                    session.add(attempt)
                    session.flush()
                    logger.info(
                        f"Parallel attempt logged for task {task_id}: "
                        f"agents={attempt.num_agents}, success={attempt.success}, "
                        f"speedup={attempt.speedup_factor}"
                    )
                    return attempt
            except SQLAlchemyError as e:
                raise DatabaseException(
                    operation='log_parallel_attempt',
                    details=str(e)
                ) from e

    def get_parallel_attempts(
        self,
        task_id: Optional[int] = None,
        success: Optional[bool] = None
    ) -> List[ParallelAgentAttempt]:
        """Get parallel agent attempts with optional filters.

        Args:
            task_id: Filter by task ID (optional)
            success: Filter by success status (optional)

        Returns:
            List of ParallelAgentAttempt records

        Example:
            >>> # Get all successful parallel attempts
            >>> attempts = state_manager.get_parallel_attempts(success=True)
            >>> avg_speedup = sum(a.speedup_factor for a in attempts) / len(attempts)
        """
        with self._lock:
            try:
                session = self._get_session()
                query = session.query(ParallelAgentAttempt)

                if task_id is not None:
                    query = query.filter(ParallelAgentAttempt.task_id == task_id)
                if success is not None:
                    query = query.filter(ParallelAgentAttempt.success == success)

                return query.order_by(desc(ParallelAgentAttempt.created_at)).all()
            except SQLAlchemyError as e:
                logger.error(f"Failed to get parallel attempts: {e}")
                raise DatabaseException(
                    operation='get_parallel_attempts',
                    details=str(e)
                ) from e

    def close(self) -> None:
        """Close database session and connections.

        Should be called on shutdown.
        """
        if self._session:
            self._session.close()
            self._session = None
        logger.info("StateManager closed")
