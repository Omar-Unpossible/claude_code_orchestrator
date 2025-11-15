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
    ParallelAgentAttempt, SessionRecord, ContextWindowUsage, Milestone,
    TaskStatus, TaskAssignee, InteractionSource, BreakpointSeverity,
    ProjectStatus, TaskType
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
        else:
            # For SQLite, disable same-thread check to allow FileWatcher (watchdog observer)
            # to record file changes from background threads. Safe because StateManager
            # has its own thread-safe locking (RLock).
            engine_kwargs['connect_args'] = {'check_same_thread': False}

        self._engine = create_engine(database_url, **engine_kwargs)

        # Create session factory
        self._SessionLocal = sessionmaker(
            bind=self._engine,
            autocommit=False,
            autoflush=False
        )

        # Thread-local session
        self._session: Optional[Session] = None

        # Config reference for documentation hooks (ADR-015)
        self._config: Optional[Any] = None

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

    def set_config(self, config: Any) -> None:
        """Set config reference for documentation hooks (ADR-015).

        Args:
            config: Config instance

        Example:
            >>> state_manager.set_config(config)
        """
        self._config = config
        logger.debug("Config reference set in StateManager")

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

    def delete_all_projects(self, soft: bool = True) -> int:
        """Delete all projects.

        Args:
            soft: If True, soft delete (set is_deleted=True)

        Returns:
            Number of projects deleted

        Example:
            >>> count = state_manager.delete_all_projects()
            >>> print(f"Deleted {count} projects")
        """
        with self._lock:
            try:
                with self.transaction():
                    session = self._get_session()

                    # Get all non-deleted projects
                    if soft:
                        projects = session.query(ProjectState).filter(
                            ProjectState.is_deleted == False  # noqa: E712
                        ).all()

                        # Soft delete each project
                        for project in projects:
                            project.is_deleted = True

                        count = len(projects)
                        logger.info(f"Soft deleted {count} projects")
                    else:
                        # Hard delete - count first
                        count = session.query(ProjectState).filter(
                            ProjectState.is_deleted == False  # noqa: E712
                        ).count()

                        # Delete all
                        session.query(ProjectState).filter(
                            ProjectState.is_deleted == False  # noqa: E712
                        ).delete()

                        logger.info(f"Hard deleted {count} projects")

                    return count

            except SQLAlchemyError as e:
                raise DatabaseException(
                    operation='delete_all_projects',
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
                - task_type (optional, default TASK) - ADR-013
                - epic_id (optional) - ADR-013
                - story_id (optional) - ADR-013

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
                        parent_task_id=task_data.get('parent_task_id'),
                        task_type=task_data.get('task_type', TaskType.TASK),
                        epic_id=task_data.get('epic_id'),
                        story_id=task_data.get('story_id'),
                        # ADR-015: Documentation maintenance fields
                        requires_adr=task_data.get('requires_adr', False),
                        has_architectural_changes=task_data.get('has_architectural_changes', False),
                        changes_summary=task_data.get('changes_summary', None)
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
            status: New status (TaskStatus enum or string)
            metadata: Optional metadata to update

        Returns:
            Updated Task
        """
        # Convert string to enum if needed (defensive programming)
        if isinstance(status, str):
            status = TaskStatus(status)

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
                        # Initialize task.task_metadata if None
                        if task.task_metadata is None:
                            task.task_metadata = {}
                        # Merge new metadata into task.task_metadata dict
                        metadata_updated = False
                        for key, value in metadata.items():
                            # Check if this is a direct Task column attribute
                            if hasattr(task, key) and key in ['retry_count', 'max_retries', 'result', 'context']:
                                setattr(task, key, value)
                            else:
                                # Store in task_metadata JSON field for non-column data
                                task.task_metadata[key] = value
                                metadata_updated = True

                        # Mark task_metadata as modified for SQLAlchemy to detect changes
                        if metadata_updated:
                            from sqlalchemy.orm import attributes
                            attributes.flag_modified(task, 'task_metadata')

                    logger.info(f"Updated task {task_id} status: {status.value}")
                    return task
            except SQLAlchemyError as e:
                raise DatabaseException(
                    operation='update_task_status',
                    details=str(e)
                ) from e

    def update_task(
        self,
        task_id: int,
        updates: Dict[str, Any]
    ) -> Task:
        """Update task fields.

        Args:
            task_id: Task ID
            updates: Dictionary of fields to update:
                - title: New title
                - description: New description
                - priority: New priority (1-10)
                - status: New status (TaskStatus enum)
                - dependencies: New dependencies list
                - assigned_to: New assignee
                - context: New context dict

        Returns:
            Updated Task object

        Raises:
            DatabaseException: If update fails

        Example:
            >>> state.update_task(5, {
            ...     'title': 'New Title',
            ...     'priority': 3,
            ...     'status': TaskStatus.RUNNING
            ... })
        """
        with self._lock:
            try:
                with self.transaction():
                    task = self.get_task(task_id)
                    if not task:
                        raise DatabaseException(
                            operation='update_task',
                            details=f'Task {task_id} not found'
                        )

                    # Update allowed fields
                    allowed_fields = {
                        'title', 'description', 'priority', 'status',
                        'dependencies', 'assigned_to', 'context',
                        'epic_id', 'story_id', 'parent_task_id'
                    }

                    for key, value in updates.items():
                        if key in allowed_fields and hasattr(task, key):
                            setattr(task, key, value)

                    logger.info(f"Updated task {task_id}: {list(updates.keys())}")
                    return task

            except SQLAlchemyError as e:
                raise DatabaseException(
                    operation='update_task',
                    details=str(e)
                ) from e

    def delete_task(
        self,
        task_id: int,
        soft: bool = True
    ) -> None:
        """Delete task (soft or hard delete).

        Args:
            task_id: Task ID to delete
            soft: If True, mark as deleted (default). If False, hard delete.

        Raises:
            DatabaseException: If deletion fails

        Example:
            >>> state.delete_task(5, soft=True)  # Soft delete
            >>> state.delete_task(5, soft=False)  # Hard delete
        """
        with self._lock:
            try:
                with self.transaction():
                    task = self.get_task(task_id)
                    if not task:
                        raise DatabaseException(
                            operation='delete_task',
                            details=f'Task {task_id} not found'
                        )

                    if soft:
                        # Soft delete: mark as deleted
                        task.is_deleted = True
                        logger.info(f"Soft deleted task {task_id}")
                    else:
                        # Hard delete: remove from database
                        session = self._get_session()
                        session.delete(task)
                        logger.info(f"Hard deleted task {task_id}")

            except SQLAlchemyError as e:
                raise DatabaseException(
                    operation='delete_task',
                    details=str(e)
                ) from e

    def delete_all_tasks(self, project_id: int) -> int:
        """
        Delete all tasks in project (excluding stories/epics/subtasks).

        Args:
            project_id: Project ID

        Returns:
            Count of tasks deleted

        Raises:
            DatabaseException: If deletion fails
        """
        with self._lock:
            try:
                with self.transaction():
                    session = self._get_session()
                    tasks = session.query(Task).filter(
                        Task.project_id == project_id,
                        Task.task_type == TaskType.TASK,
                        Task.is_deleted == False
                    ).all()

                    count = len(tasks)
                    for task in tasks:
                        session.delete(task)

                    logger.info(f"Deleted {count} tasks from project {project_id}")
                    return count

            except SQLAlchemyError as e:
                raise DatabaseException(
                    operation='delete_all_tasks',
                    details=str(e)
                ) from e

    def delete_all_stories(self, project_id: int) -> int:
        """
        Delete all stories in project (cascade to child tasks).

        Args:
            project_id: Project ID

        Returns:
            Count of stories deleted

        Raises:
            DatabaseException: If deletion fails
        """
        with self._lock:
            try:
                with self.transaction():
                    session = self._get_session()
                    stories = session.query(Task).filter(
                        Task.project_id == project_id,
                        Task.task_type == TaskType.STORY,
                        Task.is_deleted == False
                    ).all()

                    count = len(stories)

                    # Delete child tasks first
                    for story in stories:
                        child_tasks = session.query(Task).filter(
                            Task.story_id == story.id,
                            Task.is_deleted == False
                        ).all()
                        for task in child_tasks:
                            session.delete(task)

                    # Delete stories
                    for story in stories:
                        session.delete(story)

                    logger.info(f"Deleted {count} stories from project {project_id}")
                    return count

            except SQLAlchemyError as e:
                raise DatabaseException(
                    operation='delete_all_stories',
                    details=str(e)
                ) from e

    def delete_all_epics(self, project_id: int) -> int:
        """
        Delete all epics in project (cascade to stories and tasks).

        Args:
            project_id: Project ID

        Returns:
            Count of epics deleted

        Raises:
            DatabaseException: If deletion fails
        """
        with self._lock:
            try:
                with self.transaction():
                    session = self._get_session()
                    epics = session.query(Task).filter(
                        Task.project_id == project_id,
                        Task.task_type == TaskType.EPIC,
                        Task.is_deleted == False
                    ).all()

                    count = len(epics)

                    # Delete child stories and their tasks first
                    for epic in epics:
                        stories = session.query(Task).filter(
                            Task.epic_id == epic.id,
                            Task.is_deleted == False
                        ).all()

                        for story in stories:
                            # Delete tasks belonging to this story
                            child_tasks = session.query(Task).filter(
                                Task.story_id == story.id,
                                Task.is_deleted == False
                            ).all()
                            for task in child_tasks:
                                session.delete(task)

                            # Delete the story
                            session.delete(story)

                    # Delete epics
                    for epic in epics:
                        session.delete(epic)

                    logger.info(f"Deleted {count} epics from project {project_id}")
                    return count

            except SQLAlchemyError as e:
                raise DatabaseException(
                    operation='delete_all_epics',
                    details=str(e)
                ) from e

    def delete_all_subtasks(self, project_id: int) -> int:
        """
        Delete all subtasks in project.

        Args:
            project_id: Project ID

        Returns:
            Count of subtasks deleted

        Raises:
            DatabaseException: If deletion fails
        """
        with self._lock:
            try:
                with self.transaction():
                    session = self._get_session()
                    subtasks = session.query(Task).filter(
                        Task.project_id == project_id,
                        Task.parent_task_id.isnot(None),
                        Task.is_deleted == False
                    ).all()

                    count = len(subtasks)
                    for subtask in subtasks:
                        session.delete(subtask)

                    logger.info(f"Deleted {count} subtasks from project {project_id}")
                    return count

            except SQLAlchemyError as e:
                raise DatabaseException(
                    operation='delete_all_subtasks',
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
        task_type: Optional[TaskType] = None,
        limit: Optional[int] = None
    ) -> List[Task]:
        """Get all tasks with optional filtering.

        Args:
            project_id: Filter by project ID (None = all projects)
            status: Filter by status (None = all statuses)
            task_type: Filter by task type (None = all types)
            limit: Maximum number of tasks to return (None = no limit)

        Returns:
            List of tasks matching criteria, ordered by priority and created date

        Example:
            >>> # Get all tasks
            >>> all_tasks = state_manager.list_tasks()
            >>> # Get all pending tasks
            >>> pending = state_manager.list_tasks(status='pending')
            >>> # Get all epics
            >>> epics = state_manager.list_tasks(task_type=TaskType.EPIC)
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
            if task_type is not None:
                query = query.filter(Task.task_type == task_type)

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

    # ============================================================================
    # Agile/Scrum Hierarchy Methods (ADR-013)
    # ============================================================================

    def list_epics(
        self,
        project_id: int,
        status: Optional[TaskStatus] = None
    ) -> List[Task]:
        """List all epics for a project.

        Args:
            project_id: Project ID
            status: Optional status filter (None = all statuses)

        Returns:
            List of Epic tasks

        Example:
            >>> epics = state.list_epics(project_id=1)
            >>> open_epics = state.list_epics(project_id=1, status=TaskStatus.PENDING)
        """
        return self.list_tasks(
            project_id=project_id,
            task_type=TaskType.EPIC,
            status=status
        )

    def list_stories(
        self,
        project_id: int,
        epic_id: Optional[int] = None,
        status: Optional[TaskStatus] = None
    ) -> List[Task]:
        """List all stories for a project, optionally filtered by epic.

        Args:
            project_id: Project ID
            epic_id: Optional epic ID filter (None = all epics)
            status: Optional status filter (None = all statuses)

        Returns:
            List of Story tasks

        Example:
            >>> stories = state.list_stories(project_id=1)
            >>> epic_stories = state.list_stories(project_id=1, epic_id=5)
            >>> open_stories = state.list_stories(project_id=1, status=TaskStatus.PENDING)
        """
        with self._lock:
            session = self._get_session()
            query = session.query(Task).filter(
                Task.project_id == project_id,
                Task.task_type == TaskType.STORY,
                Task.is_deleted == False
            )

            if epic_id is not None:
                query = query.filter(Task.epic_id == epic_id)
            if status is not None:
                query = query.filter(Task.status == status)

            return query.all()

    def create_epic(
        self,
        project_id: int,
        title: str,
        description: str,
        **kwargs
    ) -> int:
        """Create an Epic task.

        Epic: Large feature spanning multiple stories (3-15 sessions).

        Args:
            project_id: Project ID
            title: Epic title
            description: Epic description
            **kwargs: Additional task fields (priority, context, etc.)

        Returns:
            Epic task ID

        Example:
            >>> epic_id = state.create_epic(1, "User Auth System", "OAuth + MFA")
        """
        with self._lock:
            task_data = {
                'title': title,
                'description': description,
                'task_type': TaskType.EPIC,
                **kwargs
            }
            task = self.create_task(project_id, task_data)
            logger.info(f"Created epic {task.id}: {title}")
            return task.id

    def create_story(
        self,
        project_id: int,
        epic_id: int,
        title: str,
        description: str,
        **kwargs
    ) -> int:
        """Create a Story task under an Epic.

        Story: User-facing deliverable (1 orchestration session).

        Args:
            project_id: Project ID
            epic_id: Parent epic ID
            title: Story title
            description: Story description
            **kwargs: Additional task fields

        Returns:
            Story task ID

        Raises:
            ValueError: If epic doesn't exist or is not type EPIC

        Example:
            >>> story_id = state.create_story(1, epic_id, "Email login", "As a user...")
        """
        with self._lock:
            # Validate epic
            epic = self.get_task(epic_id)
            if not epic:
                raise ValueError(f"Epic {epic_id} does not exist")
            if epic.task_type != TaskType.EPIC:
                raise ValueError(f"Task {epic_id} is not an Epic (type={epic.task_type.value})")

            task_data = {
                'title': title,
                'description': description,
                'task_type': TaskType.STORY,
                'epic_id': epic_id,
                **kwargs
            }
            task = self.create_task(project_id, task_data)
            logger.info(f"Created story {task.id} under epic {epic_id}: {title}")
            return task.id

    def get_epic_stories(self, epic_id: int) -> List[Task]:
        """Get all stories belonging to an epic.

        Args:
            epic_id: Epic task ID

        Returns:
            List of Story tasks

        Example:
            >>> stories = state.get_epic_stories(1)
        """
        with self._lock:
            session = self._get_session()
            tasks = session.query(Task).filter(
                Task.epic_id == epic_id,
                Task.task_type == TaskType.STORY,
                Task.is_deleted == False
            ).all()
            return tasks

    def complete_epic(self, epic_id: int) -> None:
        """Mark epic as complete and trigger documentation maintenance.

        ADR-015: Automatically creates documentation maintenance task if:
        - requires_adr or has_architectural_changes is True
        - documentation.enabled is True in config

        Args:
            epic_id: Epic task ID

        Raises:
            ValueError: If epic doesn't exist or is not type EPIC
            DatabaseException: If database operation fails

        Example:
            >>> state.complete_epic(5)
        """
        with self._lock:
            try:
                with self.transaction():
                    session = self._get_session()

                    # Get epic
                    epic = session.query(Task).filter(
                        Task.id == epic_id,
                        Task.is_deleted == False
                    ).first()

                    if not epic:
                        raise ValueError(f"Epic {epic_id} does not exist")
                    if epic.task_type != TaskType.EPIC:
                        raise ValueError(f"Task {epic_id} is not an Epic (type={epic.task_type.value})")

                    # Mark epic complete
                    epic.status = TaskStatus.COMPLETED
                    epic.completed_at = datetime.now(UTC)
                    logger.info(f"Epic {epic_id} completed: {epic.title}")

                    # Check if documentation maintenance is enabled
                    doc_enabled = self._config.get('documentation.enabled', False) if hasattr(self, '_config') else False

                    if doc_enabled and (epic.requires_adr or epic.has_architectural_changes):
                        # Import here to avoid circular dependency
                        from src.utils.documentation_manager import DocumentationManager

                        doc_mgr = DocumentationManager(self, self._config)

                        # Get epic stories for context
                        stories = self.get_epic_stories(epic_id)

                        # Determine maintenance scope
                        scope = 'comprehensive' if (epic.requires_adr or epic.has_architectural_changes) else 'lightweight'

                        # Create maintenance task
                        context = {
                            'epic_id': epic_id,
                            'epic_title': epic.title,
                            'epic_description': epic.description,
                            'changes': epic.changes_summary or 'No changes summary provided',
                            'stories': [{'id': s.id, 'title': s.title} for s in stories],
                            'project_id': epic.project_id
                        }

                        try:
                            maintenance_task_id = doc_mgr.create_maintenance_task(
                                trigger='epic_complete',
                                scope=scope,
                                context=context
                            )

                            if maintenance_task_id > 0:
                                logger.info(
                                    f"Created documentation maintenance task {maintenance_task_id} "
                                    f"for epic {epic_id}"
                                )
                        except Exception as e:
                            logger.error(f"Failed to create documentation maintenance task: {e}")
                            # Don't fail epic completion if doc task creation fails

            except SQLAlchemyError as e:
                raise DatabaseException(
                    operation='complete_epic',
                    details=str(e)
                ) from e

    def get_story_tasks(self, story_id: int) -> List[Task]:
        """Get all tasks implementing a story.

        Args:
            story_id: Story task ID

        Returns:
            List of Task objects

        Example:
            >>> tasks = state.get_story_tasks(1)
        """
        with self._lock:
            session = self._get_session()
            tasks = session.query(Task).filter(
                Task.story_id == story_id,
                Task.task_type == TaskType.TASK,
                Task.is_deleted == False
            ).all()
            return tasks

    def list_milestones(
        self,
        project_id: Optional[int] = None,
        achieved: Optional[bool] = None,
        limit: Optional[int] = None
    ) -> List[Milestone]:
        """Get all milestones with optional filtering.

        Args:
            project_id: Filter by project ID (None = all projects)
            achieved: Filter by achievement status (None = all)
            limit: Maximum number to return (None = no limit)

        Returns:
            List of milestones matching criteria, ordered by target_date

        Example:
            >>> milestones = state.list_milestones(project_id=1)
            >>> active = state.list_milestones(project_id=1, achieved=False)
        """
        with self._lock:
            session = self._get_session()
            query = session.query(Milestone).filter(
                Milestone.is_deleted == False
            )

            # Apply filters
            if project_id is not None:
                query = query.filter(Milestone.project_id == project_id)
            if achieved is not None:
                query = query.filter(Milestone.achieved == achieved)

            # Order by target_date (nulls last), then created_at
            query = query.order_by(
                Milestone.target_date.asc().nullslast(),
                Milestone.created_at
            )

            # Apply limit
            if limit is not None:
                query = query.limit(limit)

            return query.all()

    def create_milestone(
        self,
        project_id: int,
        name: str,
        description: Optional[str] = None,
        required_epic_ids: Optional[List[int]] = None,
        target_date: Optional[datetime] = None,
        version: Optional[str] = None
    ) -> int:
        """Create a milestone checkpoint.

        Args:
            project_id: Project ID
            name: Milestone name
            description: Optional description
            required_epic_ids: Epics that must complete
            target_date: Optional target date
            version: Optional version string (e.g., "v1.4.0") - ADR-015

        Returns:
            Milestone ID

        Example:
            >>> milestone_id = state.create_milestone(1, "Auth Complete", epics=[1, 2], version="v1.0.0")
        """
        with self._lock:
            try:
                with self.transaction():
                    milestone = Milestone(
                        project_id=project_id,
                        name=name,
                        description=description,
                        required_epic_ids=required_epic_ids or [],
                        target_date=target_date,
                        version=version,
                        achieved=False
                    )
                    session = self._get_session()
                    session.add(milestone)
                    session.flush()
                    milestone_id = milestone.id
                    logger.info(f"Created milestone {milestone_id}: {name}")
                    return milestone_id
            except SQLAlchemyError as e:
                raise DatabaseException(
                    operation='create_milestone',
                    details=str(e)
                ) from e

    def get_milestone(self, milestone_id: int) -> Optional[Milestone]:
        """Get milestone by ID.

        Args:
            milestone_id: Milestone ID

        Returns:
            Milestone or None

        Example:
            >>> milestone = state.get_milestone(1)
        """
        with self._lock:
            session = self._get_session()
            return session.query(Milestone).filter(
                Milestone.id == milestone_id,
                Milestone.is_deleted == False
            ).first()

    def check_milestone_completion(self, milestone_id: int) -> bool:
        """Check if milestone requirements are met.

        Args:
            milestone_id: Milestone ID

        Returns:
            True if all required epics are completed

        Example:
            >>> if state.check_milestone_completion(1):
            ...     state.achieve_milestone(1)
        """
        milestone = self.get_milestone(milestone_id)
        if not milestone:
            return False

        return milestone.check_completion(self)

    def achieve_milestone(self, milestone_id: int) -> None:
        """Mark milestone as achieved and trigger comprehensive documentation maintenance.

        ADR-015: Automatically creates comprehensive documentation maintenance task
        when milestone is achieved (if documentation.enabled is True).

        Args:
            milestone_id: Milestone ID

        Raises:
            DatabaseException: If database operation fails

        Example:
            >>> state.achieve_milestone(1)
        """
        with self._lock:
            try:
                with self.transaction():
                    session = self._get_session()
                    milestone = session.query(Milestone).filter(
                        Milestone.id == milestone_id
                    ).first()

                    if not milestone:
                        logger.warning(f"Milestone {milestone_id} not found")
                        return

                    milestone.achieved = True
                    milestone.achieved_at = datetime.now(UTC)
                    logger.info(f"Milestone {milestone_id} achieved: {milestone.name}")

                    # Check if documentation maintenance is enabled
                    doc_enabled = self._config.get('documentation.enabled', False) if hasattr(self, '_config') else False

                    if doc_enabled:
                        # Import here to avoid circular dependency
                        from src.utils.documentation_manager import DocumentationManager

                        doc_mgr = DocumentationManager(self, self._config)

                        # Get all epics in milestone
                        completed_epics = []
                        for epic_id in milestone.required_epic_ids:
                            epic = self.get_task(epic_id)
                            if epic:
                                completed_epics.append(epic.to_dict())

                        # Create comprehensive maintenance task
                        context = {
                            'milestone_id': milestone_id,
                            'milestone_name': milestone.name,
                            'milestone_description': milestone.description,
                            'version': milestone.version or 'Unknown',
                            'epics': completed_epics,
                            'project_id': milestone.project_id
                        }

                        try:
                            maintenance_task_id = doc_mgr.create_maintenance_task(
                                trigger='milestone_achieved',
                                scope='comprehensive',
                                context=context
                            )

                            if maintenance_task_id > 0:
                                logger.info(
                                    f"Created comprehensive documentation maintenance task {maintenance_task_id} "
                                    f"for milestone {milestone_id}"
                                )
                        except Exception as e:
                            logger.error(f"Failed to create documentation maintenance task: {e}")
                            # Don't fail milestone achievement if doc task creation fails

            except SQLAlchemyError as e:
                raise DatabaseException(
                    operation='achieve_milestone',
                    details=str(e)
                ) from e

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

    # ========================================================================
    # Session Management Methods (Iterative Orchestration)
    # ========================================================================

    def create_session_record(
        self,
        session_id: str,
        project_id: int,
        milestone_id: Optional[int] = None,
        task_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> SessionRecord:
        """Create a new session record.

        Creates a session record to track Claude Code session lifecycle.
        Sessions maintain context across multiple tasks within a milestone,
        or track individual iterations for standalone tasks.

        Args:
            session_id: Claude Code session UUID
            project_id: Associated project ID
            milestone_id: Optional milestone ID being executed
            task_id: Optional task ID for per-iteration tracking (BUG-PHASE4-006 fix)
            metadata: Optional metadata dict (reserved for future use)

        Returns:
            Created SessionRecord

        Raises:
            DatabaseException: If creation fails

        Example:
            >>> session = state_manager.create_session_record(
            ...     session_id='abc123',
            ...     project_id=1,
            ...     milestone_id=5,
            ...     task_id=10,
            ...     metadata={'iteration': 1}
            ... )
        """
        with self._lock:
            try:
                with self.transaction():
                    session_record = SessionRecord(
                        session_id=session_id,
                        project_id=project_id,
                        milestone_id=milestone_id,
                        task_id=task_id,
                        started_at=datetime.now(UTC),
                        status='active',
                        total_tokens=0,
                        total_turns=0,
                        total_cost_usd=0.0
                    )
                    session = self._get_session()
                    session.add(session_record)
                    session.flush()
                    logger.info(
                        f"Created session record: {session_id[:8]}... "
                        f"(project={project_id}, milestone={milestone_id}, task={task_id})"
                    )
                    return session_record
            except SQLAlchemyError as e:
                raise DatabaseException(
                    operation='create_session_record',
                    details=str(e)
                ) from e

    def complete_session_record(
        self,
        session_id: str,
        ended_at: datetime
    ) -> SessionRecord:
        """Mark a session as completed.

        Updates session status to 'completed' and sets end timestamp.

        Args:
            session_id: Claude Code session UUID
            ended_at: Session end timestamp

        Returns:
            Updated SessionRecord

        Raises:
            DatabaseException: If update fails or session not found

        Example:
            >>> from datetime import datetime, UTC
            >>> session = state_manager.complete_session_record(
            ...     session_id='abc123',
            ...     ended_at=datetime.now(UTC)
            ... )
        """
        with self._lock:
            try:
                with self.transaction():
                    session = self._get_session()
                    session_record = session.query(SessionRecord).filter(
                        SessionRecord.session_id == session_id
                    ).first()

                    if not session_record:
                        raise DatabaseException(
                            operation='complete_session_record',
                            details=f'Session {session_id} not found'
                        )

                    session_record.status = 'completed'
                    session_record.ended_at = ended_at

                    logger.info(f"Completed session: {session_id[:8]}...")
                    return session_record
            except SQLAlchemyError as e:
                raise DatabaseException(
                    operation='complete_session_record',
                    details=str(e)
                ) from e

    def save_session_summary(
        self,
        session_id: str,
        summary: str
    ) -> SessionRecord:
        """Save generated summary to session record.

        Stores the LLM-generated summary of session work for milestone transitions.

        Args:
            session_id: Claude Code session UUID
            summary: Generated summary text

        Returns:
            Updated SessionRecord

        Raises:
            DatabaseException: If update fails or session not found

        Example:
            >>> session = state_manager.save_session_summary(
            ...     session_id='abc123',
            ...     summary='Completed tasks 1-3, all tests passing'
            ... )
        """
        with self._lock:
            try:
                with self.transaction():
                    session = self._get_session()
                    session_record = session.query(SessionRecord).filter(
                        SessionRecord.session_id == session_id
                    ).first()

                    if not session_record:
                        raise DatabaseException(
                            operation='save_session_summary',
                            details=f'Session {session_id} not found'
                        )

                    session_record.summary = summary

                    logger.debug(
                        f"Saved summary for session {session_id[:8]}... "
                        f"({len(summary)} chars)"
                    )
                    return session_record
            except SQLAlchemyError as e:
                raise DatabaseException(
                    operation='save_session_summary',
                    details=str(e)
                ) from e

    def get_session_record(self, session_id: str) -> Optional[SessionRecord]:
        """Get session record by session ID.

        Args:
            session_id: Claude Code session UUID

        Returns:
            SessionRecord or None if not found

        Example:
            >>> session = state_manager.get_session_record('abc123')
            >>> if session:
            ...     print(f"Session status: {session.status}")
        """
        with self._lock:
            session = self._get_session()
            return session.query(SessionRecord).filter(
                SessionRecord.session_id == session_id
            ).first()

    def get_latest_session_for_milestone(
        self,
        milestone_id: int
    ) -> Optional[SessionRecord]:
        """Get the most recent session for a milestone.

        Useful for session continuity and context management.

        Args:
            milestone_id: Milestone ID

        Returns:
            SessionRecord or None if no session exists for milestone

        Example:
            >>> session = state_manager.get_latest_session_for_milestone(5)
            >>> if session and session.summary:
            ...     print(f"Previous work: {session.summary}")
        """
        with self._lock:
            session = self._get_session()
            return session.query(SessionRecord).filter(
                SessionRecord.milestone_id == milestone_id
            ).order_by(desc(SessionRecord.started_at)).first()

    def get_interactions_for_session(
        self,
        session_id: str
    ) -> List[Interaction]:
        """Get all interactions that occurred in a session.

        Retrieves interactions linked to this session via agent_session_id.

        Args:
            session_id: Claude Code session UUID

        Returns:
            List of Interaction records from this session

        Example:
            >>> interactions = state_manager.get_interactions_for_session('abc123')
            >>> total_tokens = sum(i.total_tokens for i in interactions)
        """
        with self._lock:
            session = self._get_session()
            return session.query(Interaction).filter(
                Interaction.agent_session_id == session_id
            ).order_by(Interaction.timestamp).all()

    def update_session_usage(
        self,
        session_id: str,
        tokens: int,
        turns: int,
        cost: float
    ) -> SessionRecord:
        """Update cumulative usage for a session.

        Updates cumulative token count, turn count, and cost.
        Used for context window management.

        Args:
            session_id: Claude Code session UUID
            tokens: Tokens to add to cumulative total
            turns: Turns to add to cumulative total
            cost: Cost (USD) to add to cumulative total

        Returns:
            Updated SessionRecord

        Raises:
            DatabaseException: If update fails or session not found

        Example:
            >>> session = state_manager.update_session_usage(
            ...     session_id='abc123',
            ...     tokens=1500,
            ...     turns=1,
            ...     cost=0.05
            ... )
        """
        with self._lock:
            try:
                with self.transaction():
                    session = self._get_session()
                    session_record = session.query(SessionRecord).filter(
                        SessionRecord.session_id == session_id
                    ).first()

                    if not session_record:
                        raise DatabaseException(
                            operation='update_session_usage',
                            details=f'Session {session_id} not found'
                        )

                    # Add to cumulative totals
                    session_record.total_tokens += tokens
                    session_record.total_turns += turns
                    session_record.total_cost_usd += cost

                    logger.debug(
                        f"Updated session usage {session_id[:8]}...: "
                        f"tokens={session_record.total_tokens}, "
                        f"turns={session_record.total_turns}, "
                        f"cost=${session_record.total_cost_usd:.2f}"
                    )
                    return session_record
            except SQLAlchemyError as e:
                raise DatabaseException(
                    operation='update_session_usage',
                    details=str(e)
                ) from e

    # ========================================================================
    # Token Tracking Methods (Context Window Management - Phase 3)
    # ========================================================================

    def add_session_tokens(
        self,
        session_id: str,
        task_id: int,
        tokens_dict: Dict[str, int]
    ) -> ContextWindowUsage:
        """Add tokens to cumulative session total.

        Creates a ContextWindowUsage record with cumulative token count.
        Calculates new cumulative total from previous records + current tokens.

        Args:
            session_id: Claude Code session UUID
            task_id: Task ID that generated these tokens
            tokens_dict: Token breakdown with keys:
                - total_tokens: Sum to add to cumulative
                - input_tokens: Input tokens for this interaction
                - cache_creation_tokens: Tokens cached in this interaction
                - cache_read_tokens: Tokens read from cache
                - output_tokens: Output tokens for this interaction

        Returns:
            Created ContextWindowUsage record with cumulative total

        Raises:
            DatabaseException: If creation fails

        Example:
            >>> usage = state_manager.add_session_tokens(
            ...     session_id='abc123',
            ...     task_id=5,
            ...     tokens_dict={
            ...         'total_tokens': 1500,
            ...         'input_tokens': 1000,
            ...         'cache_creation_tokens': 200,
            ...         'cache_read_tokens': 100,
            ...         'output_tokens': 500
            ...     }
            ... )
            >>> print(f"Cumulative tokens: {usage.cumulative_tokens}")
        """
        with self._lock:
            try:
                with self.transaction():
                    session = self._get_session()

                    # Get previous cumulative total
                    previous = session.query(ContextWindowUsage).filter(
                        ContextWindowUsage.session_id == session_id
                    ).order_by(desc(ContextWindowUsage.timestamp)).first()

                    previous_total = previous.cumulative_tokens if previous else 0

                    # Calculate new cumulative total
                    new_cumulative = previous_total + tokens_dict['total_tokens']

                    # Create new usage record
                    usage = ContextWindowUsage(
                        session_id=session_id,
                        task_id=task_id,
                        cumulative_tokens=new_cumulative,
                        input_tokens=tokens_dict.get('input_tokens', 0),
                        cache_creation_tokens=tokens_dict.get('cache_creation_tokens', 0),
                        cache_read_tokens=tokens_dict.get('cache_read_tokens', 0),
                        output_tokens=tokens_dict.get('output_tokens', 0)
                    )

                    session.add(usage)
                    session.flush()

                    logger.debug(
                        f"Added {tokens_dict['total_tokens']} tokens to session {session_id[:8]}...: "
                        f"cumulative={new_cumulative}"
                    )
                    return usage
            except SQLAlchemyError as e:
                raise DatabaseException(
                    operation='add_session_tokens',
                    details=str(e)
                ) from e

    def get_session_token_usage(self, session_id: str) -> int:
        """Get cumulative token count for session.

        Queries the latest ContextWindowUsage record to get current cumulative total.

        Args:
            session_id: Claude Code session UUID

        Returns:
            Cumulative token count (0 if no records exist)

        Example:
            >>> tokens = state_manager.get_session_token_usage('abc123')
            >>> print(f"Session has used {tokens:,} tokens")
        """
        with self._lock:
            try:
                session = self._get_session()
                latest = session.query(ContextWindowUsage).filter(
                    ContextWindowUsage.session_id == session_id
                ).order_by(desc(ContextWindowUsage.timestamp)).first()

                return latest.cumulative_tokens if latest else 0
            except SQLAlchemyError as e:
                logger.error(f"Failed to get session token usage: {e}")
                raise DatabaseException(
                    operation='get_session_token_usage',
                    details=str(e)
                ) from e

    def reset_session_tokens(self, session_id: str) -> None:
        """Reset token tracking for new session.

        Note: This is a no-op since fresh sessions automatically start at 0.
        We don't delete history - new session_id means fresh start.

        Args:
            session_id: Claude Code session UUID (unused, for API consistency)

        Example:
            >>> # When starting fresh session, no reset needed
            >>> state_manager.reset_session_tokens('new_session_123')
            >>> # First add_session_tokens() will start at cumulative=0
        """
        # No-op: Fresh sessions start at 0 automatically
        # History is preserved (not deleted) for analysis
        pass

    def get_task_session_metrics(self, task_id: int) -> Dict[str, Any]:
        """Aggregate session metrics across all iterations of a task.

        BUG-PHASE4-006 FIX: With per-iteration sessions, each task may have
        multiple session records (one per iteration). This method aggregates
        all session metrics at the task level for reporting and analysis.

        Args:
            task_id: Task ID to aggregate metrics for

        Returns:
            Dict with aggregated metrics:
            - total_tokens: Sum of all session tokens across iterations
            - total_turns: Sum of all turns across iterations
            - total_cost: Sum of all costs across iterations
            - num_iterations: Number of sessions (iterations) for this task
            - avg_tokens_per_iteration: Average tokens per iteration
            - sessions: List of individual session records with their metrics

        Raises:
            DatabaseException: If query fails

        Example:
            >>> metrics = state_manager.get_task_session_metrics(task_id=123)
            >>> print(f"Task used {metrics['total_tokens']:,} tokens across "
            ...       f"{metrics['num_iterations']} iterations")
            >>> print(f"Average: {metrics['avg_tokens_per_iteration']:.0f} tokens/iteration")
        """
        with self._lock:
            try:
                with self.transaction():
                    session = self._get_session()

                    # Query all sessions for this task
                    sessions = session.query(SessionRecord).filter(
                        SessionRecord.task_id == task_id
                    ).order_by(SessionRecord.started_at).all()

                    if not sessions:
                        # No sessions found - return zeros
                        return {
                            'total_tokens': 0,
                            'total_turns': 0,
                            'total_cost': 0.0,
                            'num_iterations': 0,
                            'avg_tokens_per_iteration': 0.0,
                            'sessions': []
                        }

                    # Aggregate metrics
                    total_tokens = sum(s.total_tokens or 0 for s in sessions)
                    total_turns = sum(s.total_turns or 0 for s in sessions)
                    total_cost = sum(s.total_cost_usd or 0.0 for s in sessions)
                    num_iterations = len(sessions)
                    avg_tokens = total_tokens / num_iterations if num_iterations > 0 else 0.0

                    return {
                        'total_tokens': total_tokens,
                        'total_turns': total_turns,
                        'total_cost': total_cost,
                        'num_iterations': num_iterations,
                        'avg_tokens_per_iteration': avg_tokens,
                        'sessions': [s.to_dict() for s in sessions]
                    }

            except SQLAlchemyError as e:
                logger.error(f"Failed to get task session metrics: {e}")
                raise DatabaseException(
                    operation='get_task_session_metrics',
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
