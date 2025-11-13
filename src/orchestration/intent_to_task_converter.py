"""Intent to Task Converter for ADR-017 Unified Execution Architecture.

This module converts parsed NL intents (OperationContext) into Task objects
for orchestrator execution, enabling consistent validation and quality control
across all command sources (CLI and natural language).

Classes:
    IntentToTaskConverter: Converts OperationContext → Task objects

Example:
    >>> from src.orchestration.intent_to_task_converter import IntentToTaskConverter
    >>> converter = IntentToTaskConverter(state_manager)
    >>> task = converter.convert(
    ...     parsed_intent=operation_context,
    ...     project_id=1,
    ...     original_message="create epic for user authentication"
    ... )
    >>> print(task.title)
    'Create epic: User Authentication'
"""

import logging
from datetime import datetime, UTC
from typing import Dict, Any, Optional

from src.core.state import StateManager
from src.core.models import Task, TaskType
from src.nl.types import OperationContext, OperationType, EntityType
from src.core.exceptions import OrchestratorException

logger = logging.getLogger(__name__)


class IntentConversionException(OrchestratorException):
    """Exception raised when intent conversion fails."""
    pass


class IntentToTaskConverter:
    """Converts parsed NL intents to Task objects for orchestrator execution.

    This converter bridges the NL command pipeline with the orchestration engine,
    transforming OperationContext objects (from NL parsing) into Task objects
    that can be executed by the orchestrator with full validation and quality control.

    Args:
        state_manager: StateManager instance for task creation

    Example:
        >>> converter = IntentToTaskConverter(state_manager)
        >>> parsed = OperationContext(
        ...     operation=OperationType.CREATE,
        ...     entity_type=EntityType.EPIC,
        ...     parameters={'title': 'User Auth', 'description': 'OAuth + MFA'},
        ...     confidence=0.95,
        ...     raw_input='create epic for user authentication'
        ... )
        >>> task = converter.convert(parsed, project_id=1, original_message='...')
        >>> assert task.title == 'Create epic: User Auth'
    """

    def __init__(self, state_manager: StateManager):
        """Initialize the converter.

        Args:
            state_manager: StateManager instance for task creation
        """
        self.state_manager = state_manager
        logger.info("IntentToTaskConverter initialized")

    def convert(
        self,
        parsed_intent: OperationContext,
        project_id: int,
        original_message: str
    ) -> Task:
        """Convert parsed intent to executable task.

        Args:
            parsed_intent: OperationContext from NL parsing pipeline
            project_id: Project ID for task creation
            original_message: Original NL message (for context)

        Returns:
            Task object enriched with NL metadata

        Raises:
            IntentConversionException: If conversion fails or validation errors occur

        Example:
            >>> task = converter.convert(
            ...     parsed_intent=OperationContext(
            ...         operation=OperationType.CREATE,
            ...         entity_type=EntityType.STORY,
            ...         parameters={'title': 'User Login', 'epic_id': 5}
            ...     ),
            ...     project_id=1,
            ...     original_message='add story for user login to epic 5'
            ... )
        """
        # Validate input first (before accessing attributes)
        self._validate_input(parsed_intent, project_id)

        logger.debug(
            f"Converting intent: operation={parsed_intent.operation}, "
            f"entity={parsed_intent.entity_type}, confidence={parsed_intent.confidence}"
        )

        # Map operation to task data
        try:
            if parsed_intent.operation == OperationType.CREATE:
                task_data = self._map_create_operation(parsed_intent)
            elif parsed_intent.operation == OperationType.UPDATE:
                task_data = self._map_update_operation(parsed_intent)
            elif parsed_intent.operation == OperationType.DELETE:
                task_data = self._map_delete_operation(parsed_intent)
            elif parsed_intent.operation == OperationType.QUERY:
                # QUERY operations don't create tasks (handled separately)
                raise IntentConversionException(
                    "QUERY operations should not be converted to tasks",
                    context={
                        'operation': str(parsed_intent.operation),
                        'entity_type': str(parsed_intent.entity_type)
                    },
                    recovery="Handle QUERY operations in NL command processor"
                )
            else:
                raise IntentConversionException(
                    f"Unknown operation type: {parsed_intent.operation}",
                    context={'operation': str(parsed_intent.operation)},
                    recovery="Use CREATE, UPDATE, DELETE, or QUERY"
                )
        except Exception as e:
            if isinstance(e, IntentConversionException):
                raise
            raise IntentConversionException(
                f"Failed to map operation: {e}",
                context={
                    'operation': str(parsed_intent.operation),
                    'entity_type': str(parsed_intent.entity_type),
                    'error': str(e)
                },
                recovery="Check operation parameters and entity type"
            )

        # Create task via StateManager
        try:
            task = self.state_manager.create_task(project_id, task_data)
        except Exception as e:
            raise IntentConversionException(
                f"Failed to create task via StateManager: {e}",
                context={
                    'project_id': project_id,
                    'task_data': task_data,
                    'error': str(e)
                },
                recovery="Check StateManager is initialized and project exists"
            )

        # Enrich task with NL context metadata
        task = self._enrich_with_nl_context(
            task,
            parsed_intent,
            original_message
        )

        logger.info(
            f"Successfully converted intent to task: id={task.id}, "
            f"title='{task.title[:50]}...', operation={parsed_intent.operation}"
        )

        return task

    def _validate_input(
        self,
        parsed_intent: OperationContext,
        project_id: int
    ) -> None:
        """Validate input parameters.

        Args:
            parsed_intent: Parsed intent to validate
            project_id: Project ID to validate

        Raises:
            IntentConversionException: If validation fails
        """
        if not isinstance(parsed_intent, OperationContext):
            raise IntentConversionException(
                "parsed_intent must be an OperationContext instance",
                context={'type': type(parsed_intent).__name__},
                recovery="Pass OperationContext from NL parser"
            )

        if not isinstance(project_id, int) or project_id <= 0:
            raise IntentConversionException(
                "project_id must be a positive integer",
                context={'project_id': project_id},
                recovery="Provide valid project ID"
            )

        # Verify project exists
        project = self.state_manager.get_project(project_id)
        if project is None:
            raise IntentConversionException(
                f"Project {project_id} does not exist",
                context={'project_id': project_id},
                recovery="Create project first or use valid project ID"
            )

    def _map_create_operation(
        self,
        parsed_intent: OperationContext
    ) -> Dict[str, Any]:
        """Map CREATE operation to task data.

        Args:
            parsed_intent: Parsed intent with CREATE operation

        Returns:
            Task data dictionary for StateManager.create_task()

        Raises:
            IntentConversionException: If required parameters missing
        """
        params = parsed_intent.parameters

        # Extract title (required)
        title_value = params.get('title', '').strip()
        if not title_value:
            raise IntentConversionException(
                "CREATE operation requires 'title' parameter",
                context={
                    'entity_type': str(parsed_intent.entity_type),
                    'parameters': params
                },
                recovery="Provide title in parameters"
            )

        # Build task title with operation context
        entity_name = str(parsed_intent.entity_type).title()
        task_title = f"Create {entity_name.lower()}: {title_value}"

        # Build description with instructions
        description_parts = [
            f"Natural language request to create a new {entity_name.lower()}."
        ]

        # Add user-provided description if present
        if 'description' in params and params['description']:
            description_parts.append(f"\nDetails: {params['description']}")

        # Add parameter details
        param_details = []
        for key, value in params.items():
            if key not in ['title', 'description'] and value is not None:
                param_details.append(f"- {key}: {value}")

        if param_details:
            description_parts.append("\nParameters:")
            description_parts.extend(param_details)

        task_description = '\n'.join(description_parts)

        # Map entity type to task type
        task_type = self._map_entity_to_task_type(parsed_intent.entity_type)

        # Build task data
        task_data = {
            'title': task_title,
            'description': task_description,
            'task_type': task_type,
            'priority': params.get('priority', 5),
        }

        # Add hierarchical relationships
        if 'epic_id' in params and params['epic_id']:
            task_data['epic_id'] = params['epic_id']

        if 'story_id' in params and params['story_id']:
            task_data['story_id'] = params['story_id']

        if 'parent_task_id' in params and params['parent_task_id']:
            task_data['parent_task_id'] = params['parent_task_id']

        # Add dependencies
        if 'dependencies' in params and params['dependencies']:
            task_data['dependencies'] = params['dependencies']

        return task_data

    def _map_update_operation(
        self,
        parsed_intent: OperationContext
    ) -> Dict[str, Any]:
        """Map UPDATE operation to task data.

        Args:
            parsed_intent: Parsed intent with UPDATE operation

        Returns:
            Task data dictionary for StateManager.create_task()

        Raises:
            IntentConversionException: If required parameters missing
        """
        params = parsed_intent.parameters
        identifier = parsed_intent.identifier

        if identifier is None:
            raise IntentConversionException(
                "UPDATE operation requires an identifier",
                context={
                    'entity_type': str(parsed_intent.entity_type),
                    'parameters': params
                },
                recovery="Provide entity identifier (name or ID)"
            )

        # Determine what's being updated
        update_fields = [
            key for key in params.keys()
            if key not in ['identifier', 'entity_type']
        ]

        if not update_fields:
            raise IntentConversionException(
                "UPDATE operation requires at least one field to update",
                context={
                    'identifier': identifier,
                    'parameters': params
                },
                recovery="Specify what to update (status, priority, etc.)"
            )

        # Build task title
        entity_name = str(parsed_intent.entity_type).title()
        fields_str = ', '.join(update_fields)
        task_title = f"Update {entity_name.lower()} '{identifier}': {fields_str}"

        # Build description with update instructions
        description_parts = [
            f"Natural language request to update {entity_name.lower()} '{identifier}'.",
            "\nChanges requested:"
        ]

        for field in update_fields:
            value = params[field]
            description_parts.append(f"- Set {field} to: {value}")

        task_description = '\n'.join(description_parts)

        # Build task data (UPDATE operations create TASK type by default)
        task_data = {
            'title': task_title,
            'description': task_description,
            'task_type': TaskType.TASK,
            'priority': params.get('priority', 5),
            # Store update metadata in context
            'context': {
                'update_target': {
                    'entity_type': str(parsed_intent.entity_type),
                    'identifier': identifier,
                    'fields': {k: v for k, v in params.items() if k in update_fields}
                }
            }
        }

        return task_data

    def _map_delete_operation(
        self,
        parsed_intent: OperationContext
    ) -> Dict[str, Any]:
        """Map DELETE operation to task data.

        Args:
            parsed_intent: Parsed intent with DELETE operation

        Returns:
            Task data dictionary for StateManager.create_task()

        Raises:
            IntentConversionException: If required parameters missing
        """
        identifier = parsed_intent.identifier

        if identifier is None:
            raise IntentConversionException(
                "DELETE operation requires an identifier",
                context={
                    'entity_type': str(parsed_intent.entity_type),
                    'parameters': parsed_intent.parameters
                },
                recovery="Provide entity identifier (name or ID)"
            )

        # Build task title
        entity_name = str(parsed_intent.entity_type).title()
        task_title = f"Delete {entity_name.lower()} '{identifier}'"

        # Build description with safety context
        task_description = (
            f"Natural language request to delete {entity_name.lower()} '{identifier}'.\n\n"
            f"⚠️ WARNING: This will permanently remove the {entity_name.lower()} "
            f"and may affect dependent items.\n\n"
            f"Please review carefully before executing."
        )

        # Build task data (DELETE operations create TASK type by default)
        task_data = {
            'title': task_title,
            'description': task_description,
            'task_type': TaskType.TASK,
            'priority': parsed_intent.parameters.get('priority', 5),
            # Store delete metadata in context
            'context': {
                'delete_target': {
                    'entity_type': str(parsed_intent.entity_type),
                    'identifier': identifier,
                }
            }
        }

        return task_data

    def _map_entity_to_task_type(self, entity_type: EntityType) -> TaskType:
        """Map entity type to task type.

        Args:
            entity_type: Entity type from OperationContext

        Returns:
            Corresponding TaskType enum value

        Raises:
            IntentConversionException: If entity type cannot be mapped
        """
        mapping = {
            EntityType.EPIC: TaskType.EPIC,
            EntityType.STORY: TaskType.STORY,
            EntityType.TASK: TaskType.TASK,
            EntityType.SUBTASK: TaskType.SUBTASK,
            # PROJECT and MILESTONE don't map to TaskType (special handling)
            EntityType.PROJECT: TaskType.TASK,  # Creating project is a TASK
            EntityType.MILESTONE: TaskType.TASK,  # Creating milestone is a TASK
        }

        if entity_type not in mapping:
            raise IntentConversionException(
                f"Cannot map entity type to task type: {entity_type}",
                context={'entity_type': str(entity_type)},
                recovery="Use supported entity type (epic/story/task/subtask)"
            )

        return mapping[entity_type]

    def _enrich_with_nl_context(
        self,
        task: Task,
        parsed_intent: OperationContext,
        original_message: str
    ) -> Task:
        """Enrich task with NL context metadata.

        This metadata helps the orchestrator understand that this task originated
        from natural language, includes confidence scores, and preserves the
        original user message for context.

        Args:
            task: Task object to enrich
            parsed_intent: Original parsed intent
            original_message: Original NL message

        Returns:
            Task with enriched context
        """
        # Create NL context metadata
        nl_context = {
            'source': 'natural_language',
            'original_message': original_message,
            'intent_confidence': parsed_intent.confidence,
            'operation_type': str(parsed_intent.operation),
            'entity_type': str(parsed_intent.entity_type),
            'parsed_at': datetime.now(UTC).isoformat(),
        }

        # Store entity identifier if available
        if hasattr(parsed_intent, 'identifier') and parsed_intent.identifier:
            nl_context['entity_identifier'] = parsed_intent.identifier

        # Merge with existing context (if any)
        if task.context is None:
            task.context = {}

        task.context['nl_context'] = nl_context

        # Story 8 (ADR-017): Also store in task_metadata for easy access by confirmation check
        if task.task_metadata is None:
            task.task_metadata = {}

        task.task_metadata.update(nl_context)

        return task
