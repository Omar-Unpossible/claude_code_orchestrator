"""Command Execution for Natural Language Commands.

This module executes validated commands via StateManager. Handles:
- Mapping entity types to StateManager methods (create_epic, create_story, etc.)
- Reference resolution (epic_reference/story_reference → IDs)
- Transaction safety with rollback on errors
- Confirmation workflow for destructive operations

Classes:
    ExecutionResult: Dataclass holding execution results
    CommandExecutor: Executes validated commands via StateManager

Example:
    >>> from core.state import StateManager
    >>> state = StateManager(db_url)
    >>> executor = CommandExecutor(state)
    >>> result = executor.execute(validated_command)
    >>> if result.success:
    ...     print(f"Created IDs: {result.created_ids}")
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from core.state import StateManager
from core.models import TaskType
from core.exceptions import OrchestratorException

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

    Args:
        state_manager: StateManager instance for command execution
        require_confirmation_for: List of actions requiring confirmation
            (default: ['delete', 'update'])
        default_project_id: Default project ID if not specified (default: 1)

    Example:
        >>> executor = CommandExecutor(state_manager)
        >>> result = executor.execute({
        ...     'entity_type': 'epic',
        ...     'entities': [{'title': 'User Auth', 'description': 'OAuth + MFA'}]
        ... })
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
            require_confirmation_for: Actions requiring confirmation
            default_project_id: Default project ID
        """
        self.state_manager = state_manager
        self.require_confirmation_for = require_confirmation_for or ['delete', 'update']
        self.default_project_id = default_project_id
        logger.info("CommandExecutor initialized")

    def execute(
        self,
        validated_command: Dict[str, Any],
        project_id: Optional[int] = None,
        confirmed: bool = False
    ) -> ExecutionResult:
        """Execute validated command.

        Args:
            validated_command: Validated command from CommandValidator
            project_id: Project ID (uses default if not specified)
            confirmed: True if user has confirmed destructive operation

        Returns:
            ExecutionResult with success status, created IDs, and errors

        Example:
            >>> result = executor.execute({
            ...     'entity_type': 'story',
            ...     'entities': [{'title': 'Login', 'epic_id': 5}]
            ... })
        """
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
