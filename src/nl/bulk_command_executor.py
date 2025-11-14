"""Executor for bulk operations with transaction safety."""

import logging
from typing import List, Dict, Any, Optional
from src.core.state import StateManager
from src.nl.types import EntityType


class BulkOperationException(Exception):
    """Exception raised during bulk operations."""

    def __init__(self, message: str, partial_results: Optional[Dict] = None):
        super().__init__(message)
        self.partial_results = partial_results or {}


class BulkCommandExecutor:
    """Executes bulk operations with transaction safety and confirmation."""

    DEPENDENCY_ORDER = [
        EntityType.SUBTASK,
        EntityType.TASK,
        EntityType.STORY,
        EntityType.EPIC
    ]

    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager
        self.logger = logging.getLogger(__name__)

    def execute_bulk_delete(
        self,
        project_id: int,
        entity_types: List[EntityType],
        require_confirmation: bool = True
    ) -> Dict[str, Any]:
        """
        Execute bulk delete across multiple entity types.

        Args:
            project_id: Target project ID
            entity_types: List of entity types to delete
            require_confirmation: If True, prompt user before executing

        Returns:
            Result dict with counts: {epic: 5, story: 12, task: 23}

        Raises:
            BulkOperationException: If deletion fails (with partial results)
        """
        self.logger.info(
            f"Bulk delete requested: project={project_id}, types={entity_types}"
        )

        # Get counts before deletion
        counts = self._get_entity_counts(project_id, entity_types)
        self.logger.info(f"Deletion targets: {counts}")

        if require_confirmation:
            if not self._confirm_bulk_delete(counts):
                self.logger.info("Bulk delete cancelled by user")
                return {'cancelled': True, 'counts': counts}

        # Execute deletions in dependency order
        ordered_types = self._order_by_dependencies(entity_types)
        results = {}

        try:
            for entity_type in ordered_types:
                deleted_count = self._delete_all_of_type(project_id, entity_type)
                results[entity_type.value] = deleted_count
                self.logger.info(f"Deleted {deleted_count} {entity_type.value}(s)")

        except Exception as e:
            self.logger.error(f"Bulk delete failed: {e}", exc_info=True)
            raise BulkOperationException(
                f"Bulk delete failed at {entity_type.value}: {e}",
                partial_results=results
            )

        self.logger.info(f"Bulk delete complete: {results}")
        return results

    def _delete_all_of_type(self, project_id: int, entity_type: EntityType) -> int:
        """Delete all entities of given type in project."""
        if entity_type == EntityType.TASK:
            return self.state_manager.delete_all_tasks(project_id)
        elif entity_type == EntityType.STORY:
            return self.state_manager.delete_all_stories(project_id)
        elif entity_type == EntityType.EPIC:
            return self.state_manager.delete_all_epics(project_id)
        elif entity_type == EntityType.SUBTASK:
            return self.state_manager.delete_all_subtasks(project_id)
        else:
            raise ValueError(f"Bulk delete not supported for {entity_type.value}")

    def _order_by_dependencies(self, entity_types: List[EntityType]) -> List[EntityType]:
        """Order entity types by dependency (delete children first)."""
        return [et for et in self.DEPENDENCY_ORDER if et in entity_types]

    def _get_entity_counts(
        self, project_id: int, entity_types: List[EntityType]
    ) -> Dict[str, int]:
        """Get count of entities before deletion."""
        counts = {}

        for entity_type in entity_types:
            if entity_type == EntityType.TASK:
                tasks = self.state_manager.list_tasks(project_id)
                counts['tasks'] = len(tasks)
            elif entity_type == EntityType.STORY:
                stories = self.state_manager.list_tasks(
                    project_id, task_type='story'
                )
                counts['stories'] = len(stories) if stories else 0
            elif entity_type == EntityType.EPIC:
                epics = self.state_manager.list_epics(project_id)
                counts['epics'] = len(epics) if epics else 0
            elif entity_type == EntityType.SUBTASK:
                # Subtasks are tasks with parent_task_id
                all_tasks = self.state_manager.list_tasks(project_id)
                subtasks = [t for t in all_tasks if t.parent_task_id is not None]
                counts['subtasks'] = len(subtasks)

        return counts

    def _confirm_bulk_delete(self, counts: Dict[str, int]) -> bool:
        """Prompt user to confirm bulk delete."""
        if not counts or sum(counts.values()) == 0:
            print("No items to delete.")
            return False

        items_str = ", ".join([f"{count} {name}" for name, count in counts.items() if count > 0])
        print(f"\n⚠️  WARNING: This will delete {items_str}")
        print("This action cannot be undone.")

        response = input("Continue? (yes/no): ").strip().lower()
        return response in ['yes', 'y']
