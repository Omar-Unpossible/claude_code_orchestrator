"""SubTask data class for task decomposition.

This module provides a data class representing a decomposed subtask when a complex
task is broken down into smaller, manageable pieces. Subtasks can have dependencies
on other subtasks and can be marked as parallelizable for concurrent execution.

Example Usage:
    >>> from datetime import datetime
    >>> subtask = SubTask(
    ...     subtask_id=1,
    ...     parent_task_id=100,
    ...     title="Implement data models",
    ...     description="Create User, Product, Order models with SQLAlchemy",
    ...     estimated_complexity=30.0,
    ...     estimated_duration_minutes=45,
    ...     dependencies=[],
    ...     parallelizable=True,
    ...     parallel_group=1,
    ...     status="pending",
    ...     assigned_agent_id=None,
    ...     created_at=datetime.now()
    ... )
    >>> # Serialize to dictionary
    >>> data = subtask.to_dict()
    >>> # Deserialize from dictionary
    >>> subtask2 = SubTask.from_dict(data)
    >>> # Check if ready to execute
    >>> if subtask.is_ready_to_execute():
    ...     subtask.mark_in_progress()
    ...     # ... execute subtask ...
    ...     subtask.mark_completed()
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class SubTask:
    """Represents a decomposed subtask from a complex parent task.

    A subtask is a smaller, manageable piece of work that is part of a larger
    complex task. Subtasks can have dependencies on other subtasks and can be
    executed in parallel or sequentially based on their configuration.

    Attributes:
        subtask_id: Unique identifier for this subtask.
        parent_task_id: ID of the original complex task this belongs to.
        title: Brief title describing the subtask.
        description: Detailed description of what needs to be done.
        estimated_complexity: Complexity score ranging from 0-100.
        estimated_duration_minutes: Estimated time to complete in minutes.
        dependencies: List of subtask IDs that must complete before this one.
        parallelizable: Whether this subtask can run in parallel with others.
        parallel_group: Group ID for parallel execution (None if sequential).
        status: Current status: "pending", "in_progress", "completed", "failed".
        assigned_agent_id: ID of the agent working on this (None if unassigned).
        created_at: Timestamp when the subtask was created.
    """

    subtask_id: int
    parent_task_id: int
    title: str
    description: str
    estimated_complexity: float
    estimated_duration_minutes: int
    dependencies: List[int] = field(default_factory=list)
    parallelizable: bool = False
    parallel_group: Optional[int] = None
    status: str = "pending"
    assigned_agent_id: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        """Validate field values after initialization.

        Raises:
            ValueError: If any field has an invalid value.
        """
        if self.estimated_complexity < 0 or self.estimated_complexity > 100:
            raise ValueError(
                f"estimated_complexity must be between 0 and 100, "
                f"got {self.estimated_complexity}"
            )

        if self.estimated_duration_minutes < 0:
            raise ValueError(
                f"estimated_duration_minutes must be non-negative, "
                f"got {self.estimated_duration_minutes}"
            )

        valid_statuses = {"pending", "in_progress", "completed", "failed"}
        if self.status not in valid_statuses:
            raise ValueError(
                f"status must be one of {valid_statuses}, got '{self.status}'"
            )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the SubTask to a JSON-serializable dictionary.

        Converts the SubTask instance to a dictionary with all fields,
        properly handling datetime serialization to ISO format string.

        Returns:
            Dictionary containing all SubTask fields with JSON-compatible types.
        """
        return {
            'subtask_id': self.subtask_id,
            'parent_task_id': self.parent_task_id,
            'title': self.title,
            'description': self.description,
            'estimated_complexity': self.estimated_complexity,
            'estimated_duration_minutes': self.estimated_duration_minutes,
            'dependencies': self.dependencies.copy(),
            'parallelizable': self.parallelizable,
            'parallel_group': self.parallel_group,
            'status': self.status,
            'assigned_agent_id': self.assigned_agent_id,
            'created_at': self.created_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SubTask':
        """Deserialize a SubTask from a dictionary.

        Creates a SubTask instance from a dictionary, properly handling
        datetime deserialization from ISO format string.

        Args:
            data: Dictionary containing SubTask fields.

        Returns:
            New SubTask instance with fields populated from the dictionary.

        Raises:
            ValueError: If required fields are missing or invalid.
            TypeError: If field types are incorrect.
        """
        # Create a copy to avoid modifying the input
        data_copy = data.copy()

        # Handle datetime deserialization
        if isinstance(data_copy.get('created_at'), str):
            data_copy['created_at'] = datetime.fromisoformat(data_copy['created_at'])

        # Ensure dependencies is a list
        if 'dependencies' not in data_copy:
            data_copy['dependencies'] = []

        return cls(**data_copy)

    def __repr__(self) -> str:
        """Return a detailed string representation for debugging.

        Returns:
            String showing key SubTask attributes.
        """
        return (
            f"SubTask(id={self.subtask_id}, parent={self.parent_task_id}, "
            f"title='{self.title}', status='{self.status}', "
            f"complexity={self.estimated_complexity}, "
            f"duration={self.estimated_duration_minutes}min, "
            f"dependencies={self.dependencies}, "
            f"parallelizable={self.parallelizable})"
        )

    def is_ready_to_execute(self) -> bool:
        """Check if the subtask is ready to be executed.

        A subtask is ready to execute if:
        - Its status is "pending"
        - It has no dependencies (dependency checking against other subtasks
          will be implemented in the TaskComplexityEstimator)

        Returns:
            True if the subtask can be executed now, False otherwise.
        """
        if self.status != "pending":
            return False

        # For now, just check if dependencies list is empty
        # Full dependency resolution will be handled by TaskComplexityEstimator
        return len(self.dependencies) == 0

    def mark_in_progress(self) -> None:
        """Mark the subtask as currently being executed.

        Transitions the status from "pending" to "in_progress".

        Raises:
            ValueError: If the current status is not "pending".
        """
        if self.status != "pending":
            raise ValueError(
                f"Cannot mark subtask as in_progress: "
                f"current status is '{self.status}', expected 'pending'"
            )
        self.status = "in_progress"

    def mark_completed(self) -> None:
        """Mark the subtask as successfully completed.

        Transitions the status from "in_progress" to "completed".

        Raises:
            ValueError: If the current status is not "in_progress".
        """
        if self.status != "in_progress":
            raise ValueError(
                f"Cannot mark subtask as completed: "
                f"current status is '{self.status}', expected 'in_progress'"
            )
        self.status = "completed"

    def mark_failed(self) -> None:
        """Mark the subtask as failed.

        Transitions the status from "in_progress" to "failed".

        Raises:
            ValueError: If the current status is not "in_progress".
        """
        if self.status != "in_progress":
            raise ValueError(
                f"Cannot mark subtask as failed: "
                f"current status is '{self.status}', expected 'in_progress'"
            )
        self.status = "failed"
