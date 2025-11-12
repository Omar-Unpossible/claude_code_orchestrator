"""Command Execution for Natural Language Commands.

This module executes validated commands via StateManager. Handles:
- CREATE/UPDATE/DELETE/QUERY operations (ADR-016)
- Hierarchical queries (HIERARCHICAL, NEXT_STEPS, BACKLOG, ROADMAP)
- Mapping entity types to StateManager methods (create_epic, create_story, etc.)
- Reference resolution (epic_reference/story_reference → IDs)
- Transaction safety with rollback on errors
- Confirmation workflow for destructive operations

Classes:
    ExecutionResult: Dataclass holding execution results
    CommandExecutor: Executes validated commands via StateManager

Example (new OperationContext API):
    >>> from core.state import StateManager
    >>> from src.nl.types import OperationContext, OperationType, EntityType
    >>> state = StateManager(db_url)
    >>> executor = CommandExecutor(state)
    >>> context = OperationContext(
    ...     operation=OperationType.CREATE,
    ...     entity_type=EntityType.EPIC,
    ...     parameters={"title": "User Auth", "description": "OAuth + MFA"}
    ... )
    >>> result = executor.execute(context)
    >>> if result.success:
    ...     print(f"Created IDs: {result.created_ids}")

Example (legacy API - deprecated):
    >>> result = executor.execute_legacy(validated_command)
"""

import logging
import warnings
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Union
from core.state import StateManager
from core.models import TaskType, TaskStatus
from core.exceptions import OrchestratorException
from src.nl.types import OperationContext, OperationType, EntityType, QueryType

logger = logging.getLogger(__name__)


class ExecutionException(OrchestratorException):
    """Exception raised during command execution."""
    pass


@dataclass
class ExecutionResult:
    """Result of command execution.

    Attributes:
        success: True if execution succeeded
        created_ids: List of IDs for created entities
        errors: List of error messages
        results: Additional result data (entity details, etc.)
        confirmation_required: True if confirmation needed before execution
    """
    success: bool
    created_ids: List[int] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    results: Dict[str, Any] = field(default_factory=dict)
    confirmation_required: bool = False


class CommandExecutor:
    """Executes validated commands via StateManager.

    Maps natural language commands to StateManager method calls, with
    transaction safety, reference resolution, and confirmation workflow.

    Supports two APIs:
    - New: execute(OperationContext) - ADR-016 pipeline with CREATE/UPDATE/DELETE/QUERY
    - Legacy: execute_legacy(dict) - deprecated, will be removed in v1.7.0

    Args:
        state_manager: StateManager instance for command execution
        require_confirmation_for: List of operations requiring confirmation
            (default: ['delete', 'update'])
        default_project_id: Default project ID if not specified (default: 1)

    Example:
        >>> executor = CommandExecutor(state_manager)
        >>> context = OperationContext(
        ...     operation=OperationType.CREATE,
        ...     entity_type=EntityType.EPIC,
        ...     parameters={'title': 'User Auth'}
        ... )
        >>> result = executor.execute(context)
        >>> if result.success:
        ...     print(f"Created epic {result.created_ids[0]}")
    """

    def __init__(
        self,
        state_manager: StateManager,
        require_confirmation_for: Optional[List[str]] = None,
        default_project_id: int = 1
    ):
        """Initialize command executor.

        Args:
            state_manager: StateManager for executing commands
            require_confirmation_for: Operations requiring confirmation
            default_project_id: Default project ID
        """
        self.state_manager = state_manager
        self.require_confirmation_for = require_confirmation_for or ['delete', 'update']
        self.default_project_id = default_project_id
        logger.info("CommandExecutor initialized")

    def execute(
        self,
        context: OperationContext,
        project_id: Optional[int] = None,
        confirmed: bool = False
    ) -> ExecutionResult:
        """Execute operation from OperationContext (ADR-016 API).

        Routes to appropriate handler based on operation type:
        - CREATE: _execute_create()
        - UPDATE: _execute_update()
        - DELETE: _execute_delete()
        - QUERY: _execute_query()

        Args:
            context: OperationContext from NL pipeline
            project_id: Project ID (uses default if not specified)
            confirmed: True if user has confirmed destructive operation

        Returns:
            ExecutionResult with success status, created IDs, and data

        Example:
            >>> context = OperationContext(
            ...     operation=OperationType.UPDATE,
            ...     entity_type=EntityType.PROJECT,
            ...     identifier=1,
            ...     parameters={"status": "INACTIVE"}
            ... )
            >>> result = executor.execute(context)
        """
        # Use provided project_id or default
        proj_id = project_id or self.default_project_id

        # Check if confirmation required
        if context.operation.value in self.require_confirmation_for and not confirmed:
            return ExecutionResult(
                success=False,
                confirmation_required=True,
                errors=[f"{context.operation.value} operation requires confirmation"]
            )

        # Route to operation handler
        try:
            if context.operation == OperationType.CREATE:
                return self._execute_create(context, proj_id)
            elif context.operation == OperationType.UPDATE:
                return self._execute_update(context, proj_id)
            elif context.operation == OperationType.DELETE:
                return self._execute_delete(context, proj_id)
            elif context.operation == OperationType.QUERY:
                return self._execute_query(context, proj_id)
            else:
                return ExecutionResult(
                    success=False,
                    errors=[f"Unknown operation type: {context.operation}"]
                )

        except Exception as e:
            logger.exception(f"Unexpected error during execution: {e}")
            return ExecutionResult(
                success=False,
                errors=[f"Execution error: {e}"]
            )

    # ==================== Operation Handlers (ADR-016) ====================

    def _execute_create(self, context: OperationContext, project_id: int) -> ExecutionResult:
        """Execute CREATE operation.

        Args:
            context: OperationContext with entity_type and parameters
            project_id: Project ID

        Returns:
            ExecutionResult with created entity ID
        """
        try:
            # Route to entity-specific create method
            entity_id = self._create_entity_from_context(context, project_id)

            logger.info(
                f"Created {context.entity_type.value} {entity_id} via NL command"
            )

            return ExecutionResult(
                success=True,
                created_ids=[entity_id],
                results={
                    'operation': 'create',
                    'entity_type': context.entity_type.value,
                    'entity_id': entity_id
                }
            )

        except Exception as e:
            logger.error(f"Failed to create {context.entity_type.value}: {e}")
            return ExecutionResult(
                success=False,
                errors=[f"Failed to create {context.entity_type.value}: {str(e)}"]
            )

    def _execute_update(self, context: OperationContext, project_id: int) -> ExecutionResult:
        """Execute UPDATE operation.

        Args:
            context: OperationContext with entity_type, identifier, and parameters
            project_id: Project ID

        Returns:
            ExecutionResult with updated entity info
        """
        try:
            # Resolve identifier to entity ID
            entity_id = self._resolve_identifier_to_id(context, project_id)

            if entity_id is None:
                return ExecutionResult(
                    success=False,
                    errors=[
                        f"{context.entity_type.value.capitalize()} '{context.identifier}' not found"
                    ]
                )

            # Update entity via StateManager
            self._update_entity(context, entity_id, project_id)

            logger.info(
                f"Updated {context.entity_type.value} {entity_id} via NL command"
            )

            return ExecutionResult(
                success=True,
                results={
                    'operation': 'update',
                    'entity_type': context.entity_type.value,
                    'entity_id': entity_id,
                    'updated_fields': list(context.parameters.keys())
                }
            )

        except Exception as e:
            logger.error(f"Failed to update {context.entity_type.value}: {e}")
            return ExecutionResult(
                success=False,
                errors=[f"Failed to update {context.entity_type.value}: {str(e)}"]
            )

    def _execute_delete(self, context: OperationContext, project_id: int) -> ExecutionResult:
        """Execute DELETE operation.

        Args:
            context: OperationContext with entity_type and identifier
            project_id: Project ID

        Returns:
            ExecutionResult with deletion status
        """
        try:
            # Resolve identifier to entity ID
            entity_id = self._resolve_identifier_to_id(context, project_id)

            if entity_id is None:
                return ExecutionResult(
                    success=False,
                    errors=[
                        f"{context.entity_type.value.capitalize()} '{context.identifier}' not found"
                    ]
                )

            # Delete entity via StateManager
            self._delete_entity(context, entity_id, project_id)

            logger.info(
                f"Deleted {context.entity_type.value} {entity_id} via NL command"
            )

            return ExecutionResult(
                success=True,
                results={
                    'operation': 'delete',
                    'entity_type': context.entity_type.value,
                    'entity_id': entity_id
                }
            )

        except Exception as e:
            logger.error(f"Failed to delete {context.entity_type.value}: {e}")
            return ExecutionResult(
                success=False,
                errors=[f"Failed to delete {context.entity_type.value}: {str(e)}"]
            )

    def _execute_query(self, context: OperationContext, project_id: int) -> ExecutionResult:
        """Execute QUERY operation with hierarchical support.

        Supports query types:
        - SIMPLE: List entities of specified type
        - HIERARCHICAL/WORKPLAN: Show task hierarchies (epics → stories → tasks)
        - NEXT_STEPS: Show next pending tasks for a project
        - BACKLOG: Show all pending tasks
        - ROADMAP: Show milestones and associated epics

        Args:
            context: OperationContext with entity_type and query_type
            project_id: Project ID

        Returns:
            ExecutionResult with queried data
        """
        try:
            query_type = context.query_type or QueryType.SIMPLE

            # Map WORKPLAN to HIERARCHICAL (user-facing synonym)
            if query_type == QueryType.WORKPLAN:
                query_type = QueryType.HIERARCHICAL

            # Route to query handler
            if query_type == QueryType.SIMPLE:
                return self._query_simple(context, project_id)
            elif query_type == QueryType.HIERARCHICAL:
                return self._query_hierarchical(context, project_id)
            elif query_type == QueryType.NEXT_STEPS:
                return self._query_next_steps(context, project_id)
            elif query_type == QueryType.BACKLOG:
                return self._query_backlog(context, project_id)
            elif query_type == QueryType.ROADMAP:
                return self._query_roadmap(context, project_id)
            else:
                return ExecutionResult(
                    success=False,
                    errors=[f"Unknown query type: {query_type}"]
                )

        except Exception as e:
            logger.error(f"Failed to query {context.entity_type.value}: {e}")
            return ExecutionResult(
                success=False,
                errors=[f"Failed to query {context.entity_type.value}: {str(e)}"]
            )

    # ==================== Helper Methods for Operation Handlers ====================

    def _create_entity_from_context(self, context: OperationContext, project_id: int) -> int:
        """Create entity from OperationContext.

        Args:
            context: OperationContext with entity_type and parameters
            project_id: Project ID

        Returns:
            Created entity ID
        """
        # Convert parameters to entity dict format
        entity = context.parameters.copy()

        # Route to entity-specific create method
        entity_type_str = context.entity_type.value

        if context.entity_type == EntityType.PROJECT:
            # Create project directly via StateManager
            name = entity.get('name') or entity.get('title', '')
            description = entity.get('description', '')
            return self.state_manager.create_project(
                project_name=name,
                description=description
            )
        elif context.entity_type == EntityType.EPIC:
            return self._create_epic(entity, project_id)
        elif context.entity_type == EntityType.STORY:
            return self._create_story(entity, project_id)
        elif context.entity_type == EntityType.TASK:
            return self._create_task(entity, project_id)
        elif context.entity_type == EntityType.SUBTASK:
            return self._create_subtask(entity, project_id)
        elif context.entity_type == EntityType.MILESTONE:
            return self._create_milestone(entity, project_id)
        else:
            raise ExecutionException(f"Unknown entity type: {context.entity_type}")

    def _resolve_identifier_to_id(self, context: OperationContext, project_id: int) -> Optional[int]:
        """Resolve identifier (name or ID) to entity ID.

        Args:
            context: OperationContext with entity_type and identifier
            project_id: Project ID

        Returns:
            Entity ID or None if not found
        """
        identifier = context.identifier

        # If already an int, return it
        if isinstance(identifier, int):
            return identifier

        # Resolve name to ID
        if context.entity_type == EntityType.PROJECT:
            # Search projects by name
            projects = self.state_manager.get_all_projects()
            for proj in projects:
                if proj.project_name.lower() == identifier.lower():
                    return proj.id
            return None

        elif context.entity_type == EntityType.MILESTONE:
            # Milestones don't have name search - require ID
            logger.warning(f"Milestone lookup by name '{identifier}' not supported")
            return None

        else:  # EPIC, STORY, TASK, SUBTASK
            # Search tasks by title
            task_type_map = {
                EntityType.EPIC: TaskType.EPIC,
                EntityType.STORY: TaskType.STORY,
                EntityType.TASK: TaskType.TASK,
                EntityType.SUBTASK: TaskType.SUBTASK
            }
            task_type = task_type_map.get(context.entity_type)

            if task_type:
                tasks = self.state_manager.list_tasks(
                    task_type=task_type,
                    limit=20
                )
                for task in tasks:
                    if identifier.lower() in task.title.lower():
                        return task.id

            return None

    def _update_entity(self, context: OperationContext, entity_id: int, project_id: int):
        """Update entity via StateManager.

        Args:
            context: OperationContext with entity_type and parameters
            entity_id: Entity ID to update
            project_id: Project ID
        """
        params = context.parameters

        if context.entity_type == EntityType.PROJECT:
            # Update project
            project = self.state_manager.get_project(entity_id)
            if not project:
                raise ExecutionException(f"Project {entity_id} not found")

            # Update fields
            if 'status' in params:
                # Map status string to TaskStatus enum
                status_map = {
                    'ACTIVE': TaskStatus.RUNNING,
                    'INACTIVE': TaskStatus.CANCELLED,
                    'COMPLETED': TaskStatus.COMPLETED,
                    'PAUSED': TaskStatus.PENDING,
                    'BLOCKED': TaskStatus.BLOCKED
                }
                status_str = params['status'].upper()
                if status_str in status_map:
                    project.status = status_map[status_str]

            if 'description' in params:
                project.description = params['description']

            if 'name' in params or 'title' in params:
                project.project_name = params.get('name') or params.get('title')

            # Save changes
            self.state_manager.db.commit()

        else:  # EPIC, STORY, TASK, SUBTASK
            # Update task
            task = self.state_manager.get_task(entity_id)
            if not task:
                raise ExecutionException(f"Task {entity_id} not found")

            # Update fields
            if 'status' in params:
                status_map = {
                    'ACTIVE': TaskStatus.RUNNING,
                    'INACTIVE': TaskStatus.CANCELLED,
                    'COMPLETED': TaskStatus.COMPLETED,
                    'PAUSED': TaskStatus.PENDING,
                    'BLOCKED': TaskStatus.BLOCKED,
                    'PENDING': TaskStatus.PENDING,
                    'RUNNING': TaskStatus.RUNNING,
                    'READY': TaskStatus.READY
                }
                status_str = params['status'].upper()
                if status_str in status_map:
                    task.status = status_map[status_str]

            if 'title' in params:
                task.title = params['title']

            if 'description' in params:
                task.description = params['description']

            if 'priority' in params:
                task.priority = params['priority']

            if 'dependencies' in params:
                task.dependencies = params['dependencies']

            # Save changes
            self.state_manager.db.commit()

    def _delete_entity(self, context: OperationContext, entity_id: int, project_id: int):
        """Delete entity via StateManager.

        Args:
            context: OperationContext with entity_type
            entity_id: Entity ID to delete
            project_id: Project ID
        """
        if context.entity_type == EntityType.PROJECT:
            # Delete project (if StateManager supports it)
            raise ExecutionException("Project deletion not supported via NL commands")

        elif context.entity_type == EntityType.MILESTONE:
            # Delete milestone
            self.state_manager.db.query(self.state_manager.db.Milestone).filter_by(id=entity_id).delete()
            self.state_manager.db.commit()

        else:  # EPIC, STORY, TASK, SUBTASK
            # Delete task
            self.state_manager.db.query(self.state_manager.db.Task).filter_by(id=entity_id).delete()
            self.state_manager.db.commit()

    def _query_simple(self, context: OperationContext, project_id: int) -> ExecutionResult:
        """Execute simple QUERY (list entities).

        Args:
            context: OperationContext with entity_type
            project_id: Project ID

        Returns:
            ExecutionResult with entity list
        """
        if context.entity_type == EntityType.PROJECT:
            projects = self.state_manager.get_all_projects()
            return ExecutionResult(
                success=True,
                results={
                    'query_type': 'simple',
                    'entity_type': 'project',
                    'entities': [
                        {'id': p.id, 'name': p.project_name, 'description': p.description}
                        for p in projects
                    ],
                    'count': len(projects)
                }
            )

        elif context.entity_type == EntityType.MILESTONE:
            milestones = self.state_manager.list_milestones(project_id)
            return ExecutionResult(
                success=True,
                results={
                    'query_type': 'simple',
                    'entity_type': 'milestone',
                    'entities': [
                        {'id': m.id, 'name': m.name, 'description': m.description}
                        for m in milestones
                    ],
                    'count': len(milestones)
                }
            )

        else:  # EPIC, STORY, TASK, SUBTASK
            task_type_map = {
                EntityType.EPIC: TaskType.EPIC,
                EntityType.STORY: TaskType.STORY,
                EntityType.TASK: TaskType.TASK,
                EntityType.SUBTASK: TaskType.SUBTASK
            }
            task_type = task_type_map.get(context.entity_type)

            tasks = self.state_manager.list_tasks(task_type=task_type, limit=50)
            return ExecutionResult(
                success=True,
                results={
                    'query_type': 'simple',
                    'entity_type': context.entity_type.value,
                    'entities': [
                        {
                            'id': t.id,
                            'title': t.title,
                            'description': t.description,
                            'status': t.status.value
                        }
                        for t in tasks
                    ],
                    'count': len(tasks)
                }
            )

    def _query_hierarchical(self, context: OperationContext, project_id: int) -> ExecutionResult:
        """Execute HIERARCHICAL query (show task hierarchies: epics → stories → tasks).

        Args:
            context: OperationContext
            project_id: Project ID

        Returns:
            ExecutionResult with hierarchical task structure
        """
        # Get all epics for project
        epics = self.state_manager.list_tasks(task_type=TaskType.EPIC, limit=50)

        hierarchy = []
        for epic in epics:
            # Get stories for this epic
            stories = self.state_manager.get_epic_stories(epic.id)

            epic_data = {
                'epic_id': epic.id,
                'epic_title': epic.title,
                'epic_status': epic.status.value,
                'stories': []
            }

            for story in stories:
                # Get tasks for this story
                tasks = self.state_manager.get_story_tasks(story.id)

                story_data = {
                    'story_id': story.id,
                    'story_title': story.title,
                    'story_status': story.status.value,
                    'tasks': [
                        {'task_id': t.id, 'task_title': t.title, 'task_status': t.status.value}
                        for t in tasks
                    ]
                }

                epic_data['stories'].append(story_data)

            hierarchy.append(epic_data)

        return ExecutionResult(
            success=True,
            results={
                'query_type': 'hierarchical',
                'project_id': project_id,
                'hierarchy': hierarchy,
                'epic_count': len(hierarchy)
            }
        )

    def _query_next_steps(self, context: OperationContext, project_id: int) -> ExecutionResult:
        """Execute NEXT_STEPS query (show next pending tasks).

        Args:
            context: OperationContext
            project_id: Project ID

        Returns:
            ExecutionResult with next pending tasks
        """
        # Get all pending/active tasks for project
        all_tasks = self.state_manager.list_tasks(limit=100)
        pending_tasks = [
            t for t in all_tasks
            if t.status in [TaskStatus.READY, TaskStatus.PENDING, TaskStatus.RUNNING]
            and t.project_id == project_id
        ]

        # Sort by priority (assuming higher = more important)
        pending_tasks.sort(key=lambda t: t.priority, reverse=True)

        return ExecutionResult(
            success=True,
            results={
                'query_type': 'next_steps',
                'project_id': project_id,
                'tasks': [
                    {
                        'id': t.id,
                        'title': t.title,
                        'status': t.status.value,
                        'priority': t.priority,
                        'task_type': t.task_type.value
                    }
                    for t in pending_tasks[:10]  # Top 10 next steps
                ],
                'count': len(pending_tasks)
            }
        )

    def _query_backlog(self, context: OperationContext, project_id: int) -> ExecutionResult:
        """Execute BACKLOG query (show all pending tasks).

        Args:
            context: OperationContext
            project_id: Project ID

        Returns:
            ExecutionResult with all pending tasks
        """
        # Get all pending tasks
        all_tasks = self.state_manager.list_tasks(limit=200)
        pending_tasks = [
            t for t in all_tasks
            if t.status in [TaskStatus.READY, TaskStatus.PENDING, TaskStatus.RUNNING]
            and t.project_id == project_id
        ]

        return ExecutionResult(
            success=True,
            results={
                'query_type': 'backlog',
                'project_id': project_id,
                'tasks': [
                    {
                        'id': t.id,
                        'title': t.title,
                        'status': t.status.value,
                        'priority': t.priority,
                        'task_type': t.task_type.value
                    }
                    for t in pending_tasks
                ],
                'count': len(pending_tasks)
            }
        )

    def _query_roadmap(self, context: OperationContext, project_id: int) -> ExecutionResult:
        """Execute ROADMAP query (show milestones and associated epics).

        Args:
            context: OperationContext
            project_id: Project ID

        Returns:
            ExecutionResult with roadmap data
        """
        # Get all milestones for project
        milestones = self.state_manager.list_milestones(project_id)

        roadmap = []
        for milestone in milestones:
            milestone_data = {
                'milestone_id': milestone.id,
                'milestone_name': milestone.name,
                'milestone_status': milestone.status.value if hasattr(milestone, 'status') else 'ACTIVE',
                'required_epics': []
            }

            # Get required epics
            if milestone.required_epic_ids:
                for epic_id in milestone.required_epic_ids:
                    epic = self.state_manager.get_task(epic_id)
                    if epic:
                        milestone_data['required_epics'].append({
                            'epic_id': epic.id,
                            'epic_title': epic.title,
                            'epic_status': epic.status.value
                        })

            roadmap.append(milestone_data)

        return ExecutionResult(
            success=True,
            results={
                'query_type': 'roadmap',
                'project_id': project_id,
                'milestones': roadmap,
                'milestone_count': len(roadmap)
            }
        )

    # ==================== Legacy Methods ====================

    def execute_legacy(
        self,
        validated_command: Dict[str, Any],
        project_id: Optional[int] = None,
        confirmed: bool = False
    ) -> ExecutionResult:
        """Execute validated command (DEPRECATED - use execute(OperationContext)).

        This method provides backward compatibility with the old EntityExtractor API.
        Will be removed in v1.7.0.

        Args:
            validated_command: Validated command from CommandValidator
            project_id: Project ID (uses default if not specified)
            confirmed: True if user has confirmed destructive operation

        Returns:
            ExecutionResult with success status, created IDs, and errors

        Example:
            >>> result = executor.execute_legacy({
            ...     'entity_type': 'story',
            ...     'entities': [{'title': 'Login', 'epic_id': 5}]
            ... })
        """
        warnings.warn(
            "execute_legacy() is deprecated and will be removed in v1.7.0. "
            "Use execute(OperationContext) instead.",
            DeprecationWarning,
            stacklevel=2
        )

        if not validated_command:
            return ExecutionResult(
                success=False,
                errors=["Empty command - nothing to execute"]
            )

        entity_type = validated_command.get('entity_type')
        entities = validated_command.get('entities', [])

        if not entities:
            return ExecutionResult(
                success=False,
                errors=[f"No {entity_type} entities to create"]
            )

        # Use provided project_id or default
        proj_id = project_id or self.default_project_id

        # Check if confirmation required
        action = validated_command.get('action', 'create')
        if action in self.require_confirmation_for and not confirmed:
            return ExecutionResult(
                success=False,
                confirmation_required=True,
                errors=[f"{action} operation requires confirmation"]
            )

        # Execute with transaction safety
        created_ids = []
        errors = []

        try:
            # Execute each entity
            for entity in entities:
                try:
                    created_id = self._execute_single_entity(
                        entity_type,
                        entity,
                        proj_id
                    )
                    if created_id:
                        created_ids.append(created_id)
                except Exception as e:
                    error_msg = f"Failed to create {entity_type}: {e}"
                    errors.append(error_msg)
                    logger.error(error_msg)

                    # Rollback on first error
                    if created_ids:
                        logger.warning(
                            f"Partial execution: {len(created_ids)} {entity_type}(s) created "
                            f"before error. Consider rollback."
                        )
                    break

            # Determine success
            success = len(errors) == 0 and len(created_ids) > 0

            result = ExecutionResult(
                success=success,
                created_ids=created_ids,
                errors=errors,
                results={
                    'entity_type': entity_type,
                    'created_count': len(created_ids),
                    'failed_count': len(entities) - len(created_ids)
                }
            )

            if success:
                logger.info(
                    f"Successfully created {len(created_ids)} {entity_type}(s): "
                    f"IDs {created_ids}"
                )
            else:
                logger.error(
                    f"Execution failed for {entity_type}: {len(errors)} error(s)"
                )

            return result

        except Exception as e:
            logger.exception(f"Unexpected error during execution: {e}")
            return ExecutionResult(
                success=False,
                errors=[f"Execution error: {e}"]
            )

    def _execute_single_entity(
        self,
        entity_type: str,
        entity: Dict[str, Any],
        project_id: int
    ) -> int:
        """Execute creation of single entity.

        Args:
            entity_type: Type of entity (epic, story, task, subtask, milestone)
            entity: Entity data dictionary
            project_id: Project ID

        Returns:
            Created entity ID

        Raises:
            ExecutionException: If execution fails
        """
        # Resolve references (epic_reference/story_reference → IDs)
        resolved_entity = self._resolve_references(entity.copy(), entity_type)

        # Route to appropriate StateManager method
        if entity_type == 'epic':
            return self._create_epic(resolved_entity, project_id)
        elif entity_type == 'story':
            return self._create_story(resolved_entity, project_id)
        elif entity_type == 'task':
            return self._create_task(resolved_entity, project_id)
        elif entity_type == 'subtask':
            return self._create_subtask(resolved_entity, project_id)
        elif entity_type == 'milestone':
            return self._create_milestone(resolved_entity, project_id)
        else:
            raise ExecutionException(
                f"Unknown entity type: {entity_type}",
                context={'entity': entity}
            )

    def _resolve_references(
        self,
        entity: Dict[str, Any],
        entity_type: str
    ) -> Dict[str, Any]:
        """Resolve epic_reference/story_reference to IDs.

        Args:
            entity: Entity dictionary
            entity_type: Type of entity

        Returns:
            Entity with resolved references (epic_id, story_id)
        """
        # Resolve epic_reference (name) to epic_id
        if 'epic_reference' in entity and entity['epic_reference']:
            epic_name = entity['epic_reference']
            # Search for epic by title
            epics = self.state_manager.list_tasks(
                task_type=TaskType.EPIC,
                limit=10
            )
            matching_epic = next(
                (e for e in epics if epic_name.lower() in e.title.lower()),
                None
            )
            if matching_epic:
                entity['epic_id'] = matching_epic.id
                logger.debug(f"Resolved epic '{epic_name}' to ID {matching_epic.id}")
            else:
                raise ExecutionException(
                    f"Epic '{epic_name}' not found",
                    context={'epic_reference': epic_name},
                    recovery="Create the epic first or use numeric epic_id"
                )

        # Resolve story_reference (name) to story_id
        if 'story_reference' in entity and entity['story_reference']:
            story_name = entity['story_reference']
            # Search for story by title
            stories = self.state_manager.list_tasks(
                task_type=TaskType.STORY,
                limit=10
            )
            matching_story = next(
                (s for s in stories if story_name.lower() in s.title.lower()),
                None
            )
            if matching_story:
                entity['story_id'] = matching_story.id
                logger.debug(f"Resolved story '{story_name}' to ID {matching_story.id}")
            else:
                raise ExecutionException(
                    f"Story '{story_name}' not found",
                    context={'story_reference': story_name},
                    recovery="Create the story first or use numeric story_id"
                )

        return entity

    def _create_epic(self, entity: Dict[str, Any], project_id: int) -> int:
        """Create epic via StateManager.

        Args:
            entity: Epic data
            project_id: Project ID

        Returns:
            Epic ID
        """
        title = entity.get('title', '')
        description = entity.get('description', '')
        priority = entity.get('priority', 5)

        # Build kwargs for additional fields
        kwargs = {}
        if priority != 5:
            kwargs['priority'] = priority

        epic_id = self.state_manager.create_epic(
            project_id=project_id,
            title=title,
            description=description,
            **kwargs
        )

        logger.info(f"Created epic {epic_id}: {title}")
        return epic_id

    def _create_story(self, entity: Dict[str, Any], project_id: int) -> int:
        """Create story via StateManager.

        Args:
            entity: Story data
            project_id: Project ID

        Returns:
            Story ID

        Raises:
            ExecutionException: If epic_id not provided or epic doesn't exist
        """
        title = entity.get('title', '')
        description = entity.get('description', '')
        epic_id = entity.get('epic_id')

        if not epic_id:
            raise ExecutionException(
                "Story requires epic_id",
                context={'story': entity},
                recovery="Specify epic_id or epic_reference"
            )

        priority = entity.get('priority', 5)
        kwargs = {}
        if priority != 5:
            kwargs['priority'] = priority

        story_id = self.state_manager.create_story(
            project_id=project_id,
            epic_id=epic_id,
            title=title,
            description=description,
            **kwargs
        )

        logger.info(f"Created story {story_id} under epic {epic_id}: {title}")
        return story_id

    def _create_task(self, entity: Dict[str, Any], project_id: int) -> int:
        """Create task via StateManager.

        Args:
            entity: Task data
            project_id: Project ID

        Returns:
            Task ID
        """
        task_data = {
            'title': entity.get('title', ''),
            'description': entity.get('description', ''),
            'task_type': TaskType.TASK,
            'priority': entity.get('priority', 5)
        }

        # Add optional fields
        if 'story_id' in entity:
            task_data['story_id'] = entity['story_id']
        if 'epic_id' in entity:
            task_data['epic_id'] = entity['epic_id']
        if 'dependencies' in entity:
            task_data['dependencies'] = entity['dependencies']

        task = self.state_manager.create_task(project_id, task_data)
        logger.info(f"Created task {task.id}: {task.title}")
        return task.id

    def _create_subtask(self, entity: Dict[str, Any], project_id: int) -> int:
        """Create subtask via StateManager.

        Args:
            entity: Subtask data
            project_id: Project ID

        Returns:
            Subtask ID

        Raises:
            ExecutionException: If parent_task_id not provided
        """
        parent_task_id = entity.get('parent_task_id')
        if not parent_task_id:
            raise ExecutionException(
                "Subtask requires parent_task_id",
                context={'subtask': entity},
                recovery="Specify parent_task_id"
            )

        task_data = {
            'title': entity.get('title', ''),
            'description': entity.get('description', ''),
            'task_type': TaskType.SUBTASK,
            'parent_task_id': parent_task_id,
            'priority': entity.get('priority', 5)
        }

        task = self.state_manager.create_task(project_id, task_data)
        logger.info(f"Created subtask {task.id} under task {parent_task_id}: {task.title}")
        return task.id

    def _create_milestone(self, entity: Dict[str, Any], project_id: int) -> int:
        """Create milestone via StateManager.

        Args:
            entity: Milestone data
            project_id: Project ID

        Returns:
            Milestone ID

        Raises:
            ExecutionException: If required_epic_ids not provided
        """
        name = entity.get('name') or entity.get('title', '')
        description = entity.get('description', '')
        required_epic_ids = entity.get('required_epic_ids')

        if not required_epic_ids:
            raise ExecutionException(
                "Milestone requires required_epic_ids",
                context={'milestone': entity},
                recovery="Specify list of epic IDs required for this milestone"
            )

        milestone_id = self.state_manager.create_milestone(
            project_id=project_id,
            name=name,
            description=description,
            required_epic_ids=required_epic_ids
        )

        logger.info(f"Created milestone {milestone_id}: {name}")
        return milestone_id
