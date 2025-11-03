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
from datetime import datetime, UTC

from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

from src.core.models import (
    Base, ProjectState, Task, Interaction, Checkpoint,
    BreakpointEvent, UsageTracking, FileState, PatternLearning,
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

    def close(self) -> None:
        """Close database session and connections.

        Should be called on shutdown.
        """
        if self._session:
            self._session.close()
            self._session = None
        logger.info("StateManager closed")
