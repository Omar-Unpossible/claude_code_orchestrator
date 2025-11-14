"""Command Validation for Natural Language Commands.

This module validates extracted entities against Obra business rules before execution.
Checks include:
- Operation + entity type combinations are valid
- Required parameters are present for the operation
- Parameter values are valid (status, priority, etc.)
- Referenced entities exist (epic_id, story_id, parent_task_id, identifier for UPDATE/DELETE)
- No circular dependencies in task dependencies
- Required fields are present
- Field types match schema

Classes:
    ValidationResult: Dataclass holding validation results
    CommandValidator: Validates entities using StateManager

Example (new OperationContext API):
    >>> from core.state import StateManager
    >>> from src.nl.types import OperationContext, OperationType, EntityType
    >>> state = StateManager(db_url)
    >>> validator = CommandValidator(state)
    >>> context = OperationContext(
    ...     operation=OperationType.UPDATE,
    ...     entity_type=EntityType.PROJECT,
    ...     identifier="manual tetris test",
    ...     parameters={"status": "INACTIVE"}
    ... )
    >>> result = validator.validate(context)
    >>> if result.valid:
    ...     # Proceed to execution
    ...     pass
    >>> else:
    ...     print(result.errors)

Example (legacy ExtractedEntities API - deprecated):
    >>> from nl.entity_extractor import ExtractedEntities
    >>> result = validator.validate_legacy(extracted_entities)
"""

import logging
import warnings
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Union
from core.state import StateManager
from core.exceptions import OrchestratorException
from src.nl.types import OperationContext, OperationType, EntityType, QueryType

# Import for backward compatibility (to be deprecated in v1.7.0)
try:
    from nl.entity_extractor import ExtractedEntities
    LEGACY_SUPPORT = True
except ImportError:
    LEGACY_SUPPORT = False

logger = logging.getLogger(__name__)


class ValidationException(OrchestratorException):
    """Exception raised during validation."""
    pass


@dataclass
class ValidationResult:
    """Result of command validation.

    Attributes:
        valid: True if all validations passed
        errors: List of error messages (blockers)
        warnings: List of warning messages (non-blockers)
        validated_command: Validated command dict ready for execution
    """
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    validated_command: Dict[str, Any] = field(default_factory=dict)


class CommandValidator:
    """Validates extracted entities against Obra business rules.

    Uses StateManager to check if referenced entities exist and validate
    business constraints like circular dependencies, required fields, etc.

    Supports two APIs:
    - New: validate(OperationContext) - ADR-016 pipeline
    - Legacy: validate_legacy(ExtractedEntities) - deprecated, will be removed in v1.7.0

    Args:
        state_manager: StateManager instance for entity lookups

    Example:
        >>> validator = CommandValidator(state_manager)
        >>> context = OperationContext(operation=OperationType.UPDATE, ...)
        >>> result = validator.validate(context)
        >>> if not result.valid:
        ...     for error in result.errors:
        ...         print(f"Validation error: {error}")
    """

    # Valid status values for different entity types
    VALID_STATUS_VALUES = {
        EntityType.PROJECT: ["ACTIVE", "INACTIVE", "COMPLETED", "PAUSED"],
        EntityType.EPIC: ["ACTIVE", "INACTIVE", "COMPLETED", "PAUSED", "BLOCKED"],
        EntityType.STORY: ["ACTIVE", "INACTIVE", "COMPLETED", "PAUSED", "BLOCKED"],
        EntityType.TASK: ["ACTIVE", "INACTIVE", "COMPLETED", "PAUSED", "BLOCKED"],
        EntityType.SUBTASK: ["ACTIVE", "INACTIVE", "COMPLETED", "PAUSED", "BLOCKED"],
    }

    # Valid priority values
    VALID_PRIORITY_VALUES = ["HIGH", "MEDIUM", "LOW"]

    def __init__(self, state_manager: StateManager):
        """Initialize command validator.

        Args:
            state_manager: StateManager for entity existence checks
        """
        self.state_manager = state_manager
        logger.info("CommandValidator initialized")

    def validate(self, context: OperationContext) -> ValidationResult:
        """Validate operation context against business rules (ADR-016 API).

        Args:
            context: OperationContext from NL pipeline with operation, entity_type, identifier, parameters

        Returns:
            ValidationResult with validation status, errors, and validated command

        Raises:
            ValidationException: If validation fails critically

        Example:
            >>> context = OperationContext(
            ...     operation=OperationType.UPDATE,
            ...     entity_type=EntityType.PROJECT,
            ...     identifier="manual tetris test",
            ...     parameters={"status": "INACTIVE"}
            ... )
            >>> result = validator.validate(context)
            >>> if result.valid:
            ...     executor.execute(result.validated_command)
        """
        errors = []
        warnings = []

        # Validate operation + entity type combination
        combo_errors = self._validate_operation_entity_combination(context)
        errors.extend(combo_errors)

        # Validate operation-specific requirements
        op_errors = self._validate_operation_requirements(context)
        errors.extend(op_errors)

        # Validate parameters for operation type
        param_errors = self._validate_operation_parameters(context)
        errors.extend(param_errors)

        # Validate entity exists for UPDATE/DELETE operations
        if context.operation in [OperationType.UPDATE, OperationType.DELETE]:
            existence_errors = self._validate_entity_exists(context)
            errors.extend(existence_errors)

        # Validate dependencies (if present)
        if 'dependencies' in context.parameters:
            dep_errors = self._validate_dependencies_from_context(context)
            errors.extend(dep_errors)

        # Build validated command if no errors
        if not errors:
            validated_command = {
                'operation': context.operation.value,
                'entity_type': context.entity_type.value,
                'identifier': context.identifier,
                'parameters': context.parameters,
                'confidence': context.confidence
            }
        else:
            validated_command = {}

        result = ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            validated_command=validated_command
        )

        if result.valid:
            logger.info(f"Validation passed for {context.operation.value} {context.entity_type.value}")
        else:
            logger.warning(f"Validation failed with {len(errors)} error(s): {errors}")

        return result

    def validate_legacy(self, entities: 'ExtractedEntities') -> ValidationResult:
        """Validate extracted entities against business rules (DEPRECATED - use validate()).

        This method provides backward compatibility with the old EntityExtractor API.
        Will be removed in v1.7.0.

        Args:
            entities: ExtractedEntities from EntityExtractor

        Returns:
            ValidationResult with validation status, errors, and validated command

        Example:
            >>> result = validator.validate_legacy(entities)
            >>> if result.valid:
            ...     executor.execute(result.validated_command)
        """
        if not LEGACY_SUPPORT:
            raise ValidationException(
                "Legacy validation not available - ExtractedEntities import failed. "
                "Please use validate(OperationContext) instead."
            )

        warnings.warn(
            "validate_legacy() is deprecated and will be removed in v1.7.0. "
            "Use validate(OperationContext) instead.",
            DeprecationWarning,
            stacklevel=2
        )

        errors = []
        warnings_list = []

        # Validate each entity
        for entity in entities.entities:
            # Check required fields
            field_errors = self._validate_required_fields(entity, entities.entity_type)
            errors.extend(field_errors)

            # Check epic/story references exist
            ref_errors = self._validate_references(entity, entities.entity_type)
            errors.extend(ref_errors)

            # Check for circular dependencies (tasks only)
            if entities.entity_type == 'task' and 'dependencies' in entity:
                dep_errors = self._validate_dependencies(entity)
                errors.extend(dep_errors)

        # Build validated command if no errors
        if not errors:
            validated_command = {
                'entity_type': entities.entity_type,
                'entities': entities.entities,
                'confidence': entities.confidence
            }
        else:
            validated_command = {}

        result = ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings_list,
            validated_command=validated_command
        )

        if result.valid:
            logger.info(f"Validation passed for {len(entities.entities)} {entities.entity_type}(s)")
        else:
            logger.warning(f"Validation failed with {len(errors)} error(s)")

        return result

    # ==================== New Validation Methods (ADR-016) ====================

    def _validate_operation_entity_combination(self, context: OperationContext) -> List[str]:
        """Validate that operation + entity type combination is valid.

        Args:
            context: OperationContext with operation and entity_type

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        # All operations are valid for all entity types in current design
        # Future: Could add restrictions like "MILESTONE can't be UPDATE'd directly"
        # For now, this is a placeholder for future business rules

        # Validate entity type is not MILESTONE for CREATE (milestones created via special method)
        if context.operation == OperationType.CREATE and context.entity_type == EntityType.MILESTONE:
            # Actually, milestones CAN be created via NL commands, so this is fine
            pass

        return errors

    def _validate_operation_requirements(self, context: OperationContext) -> List[str]:
        """Validate operation-specific requirements (e.g., UPDATE requires identifier).

        Args:
            context: OperationContext with operation, entity_type, identifier

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        # UPDATE and DELETE operations require an identifier
        if context.operation in [OperationType.UPDATE, OperationType.DELETE]:
            if context.identifier is None:
                errors.append(
                    f"{context.operation.value.upper()} operation requires an identifier "
                    f"(entity name or ID)"
                )

        # QUERY operations with identifier = None are "show all" queries (valid)
        # CREATE operations should not have an identifier in context.identifier
        # (identifier is the name being created, passed in parameters)

        return errors

    def _validate_operation_parameters(self, context: OperationContext) -> List[str]:
        """Validate parameters for operation type (status values, priority, etc.).

        Phase 4: Handles None values for optional parameters gracefully.

        Args:
            context: OperationContext with operation, entity_type, parameters

        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        params = context.parameters

        # Validate status parameter (optional field)
        if 'status' in params:
            status_value = params['status']
            if status_value is None:
                pass  # OK - optional field not provided
            else:
                status = status_value.upper() if isinstance(status_value, str) else status_value
                valid_statuses = self.VALID_STATUS_VALUES.get(context.entity_type, [])

                if valid_statuses and status not in valid_statuses:
                    errors.append(
                        f"Invalid status '{params['status']}' for {context.entity_type.value}. "
                        f"Valid values: {', '.join(valid_statuses)}"
                    )

        # Validate priority parameter (optional field)
        if 'priority' in params:
            priority_value = params['priority']
            if priority_value is None:
                pass  # OK - optional field not provided
            else:
                priority = priority_value.upper() if isinstance(priority_value, str) else priority_value

                if priority not in self.VALID_PRIORITY_VALUES:
                    errors.append(
                        f"Invalid priority '{params['priority']}'. "
                        f"Valid values: {', '.join(self.VALID_PRIORITY_VALUES)}"
                    )

        # Validate dependencies parameter (must be list of integers)
        if 'dependencies' in params:
            deps = params['dependencies']

            if not isinstance(deps, list):
                errors.append(f"Dependencies must be a list, got {type(deps).__name__}")
            else:
                for dep in deps:
                    if not isinstance(dep, int):
                        errors.append(f"Dependency IDs must be integers, got {type(dep).__name__}: {dep}")
                        break

        # Validate epic_id, story_id, parent_task_id (must be integers if present)
        for id_field in ['epic_id', 'story_id', 'parent_task_id', 'project_id']:
            if id_field in params and params[id_field] is not None:
                if not isinstance(params[id_field], int):
                    errors.append(f"{id_field} must be an integer, got {type(params[id_field]).__name__}")

        return errors

    def _validate_entity_exists(self, context: OperationContext) -> List[str]:
        """Validate entity exists for UPDATE/DELETE operations.

        Args:
            context: OperationContext with entity_type and identifier

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        if context.identifier is None:
            # Already caught by _validate_operation_requirements
            return errors

        try:
            # Determine lookup method based on entity type
            entity = None

            if context.entity_type == EntityType.PROJECT:
                # Try to find project by ID or name
                if isinstance(context.identifier, int):
                    entity = self.state_manager.get_project(context.identifier)
                else:
                    # Search by name
                    projects = self.state_manager.list_projects()
                    for proj in projects:
                        if proj.project_name.lower() == context.identifier.lower():
                            entity = proj
                            break

            elif context.entity_type == EntityType.MILESTONE:
                # Try to find milestone by ID
                if isinstance(context.identifier, int):
                    entity = self.state_manager.get_milestone(context.identifier)
                else:
                    # Milestones don't have a name search method
                    errors.append(f"Milestone lookup by name '{context.identifier}' not supported. Use milestone ID.")
                    return errors

            else:  # EPIC, STORY, TASK, SUBTASK
                # All are stored in tasks table, lookup by ID or title
                if isinstance(context.identifier, int):
                    entity = self.state_manager.get_task(context.identifier)
                else:
                    # Search by title (this is slow, but acceptable for validation)
                    # Note: In production, CommandExecutor should do fuzzy matching
                    errors.append(
                        f"{context.entity_type.value.capitalize()} lookup by name '{context.identifier}' "
                        f"is not implemented in validator. CommandExecutor will resolve."
                    )
                    # Don't block validation - let executor handle name resolution
                    return []

            if entity is None and isinstance(context.identifier, int):
                errors.append(
                    f"{context.entity_type.value.capitalize()} with ID {context.identifier} not found"
                )

        except Exception as e:
            logger.error(f"Error checking entity existence: {e}", exc_info=True)
            errors.append(f"Error validating entity existence: {str(e)}")

        return errors

    def _validate_dependencies_from_context(self, context: OperationContext) -> List[str]:
        """Validate task dependencies from OperationContext.

        Args:
            context: OperationContext with dependencies in parameters

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        dependencies = context.parameters.get('dependencies', [])
        if not dependencies:
            return errors

        # For UPDATE operations, check for circular dependencies
        if context.operation == OperationType.UPDATE and isinstance(context.identifier, int):
            task_id = context.identifier

            # Check for direct self-dependency
            if task_id in dependencies:
                errors.append(f"Task {task_id} cannot depend on itself")
                return errors

            # Check for circular dependencies via StateManager
            try:
                all_deps = self._get_all_dependencies(dependencies)

                # If task_id appears in transitive dependencies, it's circular
                if task_id in all_deps:
                    errors.append(
                        f"Circular dependency detected: task {task_id} depends on itself transitively"
                    )
            except Exception as e:
                logger.warning(f"Could not check circular dependencies: {e}")
                # Don't block on this - executor will handle it

        return errors

    # ==================== Legacy Validation Methods ====================

    def _validate_required_fields(self, entity: Dict[str, Any], entity_type: str) -> List[str]:
        """Validate required fields are present.

        Args:
            entity: Entity dictionary
            entity_type: Type of entity (epic, story, task, etc.)

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        # If entity has 'id', it's an UPDATE operation - only validate presence of id
        # For updates, any additional fields present will be updated, but not all are required
        if 'id' in entity:
            # Update operation - only 'id' is required
            return errors

        # CREATE operation - validate all required fields
        required_fields = {
            'epic': ['title'],
            'story': ['title'],
            'task': ['title'],
            'subtask': ['title', 'parent_task_id'],
            'milestone': ['name', 'required_epic_ids']
        }

        entity_required = required_fields.get(entity_type, [])

        for field in entity_required:
            # Handle milestone 'name' vs 'title'
            check_field = 'title' if field == 'name' and 'title' in entity else field

            if check_field not in entity or not entity[check_field]:
                errors.append(f"{entity_type} missing required field '{field}'")

        return errors

    def _validate_references(self, entity: Dict[str, Any], entity_type: str) -> List[str]:
        """Validate referenced entities exist.

        Args:
            entity: Entity dictionary
            entity_type: Type of entity

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        # Validate epic_id exists
        if 'epic_id' in entity and entity['epic_id']:
            try:
                epic = self.state_manager.get_task(entity['epic_id'])
                if not epic:
                    errors.append(f"Epic {entity['epic_id']} not found")
                elif epic.task_type.value != 'epic':
                    errors.append(f"Task {entity['epic_id']} is not an epic (type={epic.task_type.value})")
            except Exception as e:
                errors.append(f"Error checking epic {entity['epic_id']}: {e}")

        # Validate story_id exists
        if 'story_id' in entity and entity['story_id']:
            try:
                story = self.state_manager.get_task(entity['story_id'])
                if not story:
                    errors.append(f"Story {entity['story_id']} not found")
                elif story.task_type.value != 'story':
                    errors.append(f"Task {entity['story_id']} is not a story (type={story.task_type.value})")
            except Exception as e:
                errors.append(f"Error checking story {entity['story_id']}: {e}")

        # Validate parent_task_id exists (for subtasks)
        if 'parent_task_id' in entity and entity['parent_task_id']:
            try:
                parent = self.state_manager.get_task(entity['parent_task_id'])
                if not parent:
                    errors.append(f"Parent task {entity['parent_task_id']} not found")
            except Exception as e:
                errors.append(f"Error checking parent task {entity['parent_task_id']}: {e}")

        # Note: epic_reference and story_reference are resolved during execution
        # (they're names, not IDs, so we can't validate here without doing a search)

        return errors

    def _validate_dependencies(self, entity: Dict[str, Any]) -> List[str]:
        """Validate task dependencies for circular references.

        Args:
            entity: Task entity dictionary

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        dependencies = entity.get('dependencies', [])
        if not dependencies:
            return errors

        # Check if task has an ID (updating existing task)
        task_id = entity.get('id')
        if not task_id:
            # New task, can't have circular dependency with itself
            return errors

        # Check for direct self-dependency
        if task_id in dependencies:
            errors.append(f"Task {task_id} cannot depend on itself")
            return errors

        # Check for circular dependencies via StateManager
        try:
            # Get all dependencies recursively
            all_deps = self._get_all_dependencies(dependencies)

            # If task_id appears in transitive dependencies, it's circular
            if task_id in all_deps:
                errors.append(
                    f"Circular dependency detected: task {task_id} depends on itself transitively"
                )
        except Exception as e:
            logger.warning(f"Could not check circular dependencies: {e}")
            # Don't block on this - executor will handle it

        return errors

    def _get_all_dependencies(self, dep_ids: List[int], visited: Optional[set] = None) -> set:
        """Recursively get all dependencies.

        Args:
            dep_ids: List of direct dependency IDs
            visited: Set of already visited task IDs (to detect cycles)

        Returns:
            Set of all dependency IDs (direct and transitive)
        """
        if visited is None:
            visited = set()

        all_deps = set(dep_ids)

        for dep_id in dep_ids:
            if dep_id in visited:
                # Cycle detected
                continue

            visited.add(dep_id)

            try:
                task = self.state_manager.get_task(dep_id)
                if task and task.dependencies:
                    # Recursively get dependencies
                    transitive_deps = self._get_all_dependencies(
                        task.dependencies,
                        visited
                    )
                    all_deps.update(transitive_deps)
            except Exception as e:
                logger.warning(f"Could not fetch task {dep_id}: {e}")

        return all_deps
