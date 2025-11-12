"""Command Validation for Natural Language Commands.

This module validates extracted entities against Obra business rules before execution.
Checks include:
- Referenced entities exist (epic_id, story_id, parent_task_id)
- No circular dependencies in task dependencies
- Required fields are present
- Field types match schema

Classes:
    ValidationResult: Dataclass holding validation results
    CommandValidator: Validates entities using StateManager

Example:
    >>> from core.state import StateManager
    >>> state = StateManager(db_url)
    >>> validator = CommandValidator(state)
    >>> result = validator.validate(extracted_entities)
    >>> if result.valid:
    ...     # Proceed to execution
    ...     pass
    >>> else:
    ...     print(result.errors)
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from core.state import StateManager
from core.exceptions import OrchestratorException
from nl.entity_extractor import ExtractedEntities

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

    Args:
        state_manager: StateManager instance for entity lookups

    Example:
        >>> validator = CommandValidator(state_manager)
        >>> result = validator.validate(extracted_entities)
        >>> if not result.valid:
        ...     for error in result.errors:
        ...         print(f"Validation error: {error}")
    """

    def __init__(self, state_manager: StateManager):
        """Initialize command validator.

        Args:
            state_manager: StateManager for entity existence checks
        """
        self.state_manager = state_manager
        logger.info("CommandValidator initialized")

    def validate(self, entities: ExtractedEntities) -> ValidationResult:
        """Validate extracted entities against business rules.

        Args:
            entities: ExtractedEntities from EntityExtractor

        Returns:
            ValidationResult with validation status, errors, and validated command

        Example:
            >>> result = validator.validate(entities)
            >>> if result.valid:
            ...     executor.execute(result.validated_command)
        """
        errors = []
        warnings = []

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
            warnings=warnings,
            validated_command=validated_command
        )

        if result.valid:
            logger.info(f"Validation passed for {len(entities.entities)} {entities.entity_type}(s)")
        else:
            logger.warning(f"Validation failed with {len(errors)} error(s)")

        return result

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
