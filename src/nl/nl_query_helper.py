"""Read-only Query Helper for Natural Language Commands (ADR-017).

After ADR-017 refactor, NLQueryHelper handles ONLY query operations.
Write operations (CREATE/UPDATE/DELETE) route through orchestrator via
IntentToTaskConverter (Story 2).

This module provides query context building for:
- SIMPLE queries: List entities (projects, epics, stories, tasks, milestones)
- HIERARCHICAL queries: Show task hierarchies (epics → stories → tasks)
- NEXT_STEPS queries: Show next pending tasks for a project
- BACKLOG queries: Show all pending tasks
- ROADMAP queries: Show milestones and associated epics

Classes:
    NLQueryHelper: Build query contexts for NL queries (read-only)

Example:
    >>> from src.nl.nl_query_helper import NLQueryHelper
    >>> from src.nl.types import OperationContext, OperationType, QueryType, EntityType
    >>> helper = NLQueryHelper(state_manager)
    >>> context = OperationContext(
    ...     operation=OperationType.QUERY,
    ...     entity_type=EntityType.TASK,
    ...     query_type=QueryType.SIMPLE
    ... )
    >>> # Execute query using helpers
    >>> result = helper.execute(context, project_id=1)
    >>> print(f"Found {result.results['count']} tasks")
"""

import logging
import warnings
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple

from core.state import StateManager
from core.models import TaskType, TaskStatus
from core.exceptions import OrchestratorException
from src.nl.types import OperationContext, OperationType, EntityType, QueryType

logger = logging.getLogger(__name__)


class QueryException(OrchestratorException):
    """Exception raised during query operations."""
    pass


@dataclass
class QueryResult:
    """Result of query operation.

    Attributes:
        success: True if query succeeded
        query_type: Type of query executed
        entity_type: Type of entities queried
        results: Query results data
        errors: List of error messages
    """
    success: bool
    query_type: str = ""
    entity_type: str = ""
    results: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


class NLQueryHelper:
    """Build and execute query contexts for natural language queries (READ-ONLY).

    After ADR-017, this class ONLY handles queries. Write operations
    (CREATE/UPDATE/DELETE) are handled by IntentToTaskConverter + Orchestrator.

    Supported query types:
    - SIMPLE: List entities (projects, epics, stories, tasks, milestones)
    - HIERARCHICAL/WORKPLAN: Show task hierarchies (epics → stories → tasks)
    - NEXT_STEPS: Show next pending tasks for a project
    - BACKLOG: Show all pending tasks
    - ROADMAP: Show milestones and associated epics

    Args:
        state_manager: StateManager instance for query execution
        default_project_id: Default project ID if not specified (default: 1)

    Example:
        >>> helper = NLQueryHelper(state_manager)
        >>> context = OperationContext(
        ...     operation=OperationType.QUERY,
        ...     entity_type=EntityType.EPIC,
        ...     query_type=QueryType.HIERARCHICAL
        ... )
        >>> result = helper.execute(context, project_id=1)
        >>> print(f"Found {result.results['epic_count']} epics")
    """

    def __init__(
        self,
        state_manager: StateManager,
        default_project_id: int = 1
    ):
        """Initialize NL query helper.

        Args:
            state_manager: StateManager for query execution
            default_project_id: Default project ID
        """
        self.state_manager = state_manager
        self.default_project_id = default_project_id
        logger.info("NLQueryHelper initialized (query-only mode)")

    def execute(
        self,
        context: OperationContext,
        project_id: Optional[int] = None
    ) -> QueryResult:
        """Execute query operation from OperationContext.

        NOTE: This method will be deprecated in v1.8.0 in favor of
        build_query_context(). Currently kept for backward compatibility.

        Args:
            context: OperationContext with QUERY operation
            project_id: Project ID (uses default if not specified)

        Returns:
            QueryResult with query data

        Raises:
            QueryException: If context.operation is not QUERY

        Example:
            >>> context = OperationContext(
            ...     operation=OperationType.QUERY,
            ...     entity_type=EntityType.TASK,
            ...     query_type=QueryType.SIMPLE
            ... )
            >>> result = helper.execute(context, project_id=1)
        """
        # Validate operation type
        if context.operation != OperationType.QUERY:
            raise QueryException(
                f"NLQueryHelper only handles QUERY operations. "
                f"Got: {context.operation}. "
                f"Use IntentToTaskConverter + Orchestrator for write operations "
                f"(CREATE/UPDATE/DELETE).",
                context={
                    'operation': str(context.operation),
                    'entity_type': str(context.entity_type)
                },
                recovery="Route write operations through IntentToTaskConverter"
            )

        # Use provided project_id or default
        proj_id = project_id or self.default_project_id

        # Execute query based on query_type
        try:
            query_type = context.query_type or QueryType.SIMPLE

            # Map WORKPLAN to HIERARCHICAL (user-facing synonym)
            if query_type == QueryType.WORKPLAN:
                query_type = QueryType.HIERARCHICAL

            # Route to query handler
            if query_type == QueryType.SIMPLE:
                return self._query_simple(context, proj_id)
            elif query_type == QueryType.HIERARCHICAL:
                return self._query_hierarchical(context, proj_id)
            elif query_type == QueryType.NEXT_STEPS:
                return self._query_next_steps(context, proj_id)
            elif query_type == QueryType.BACKLOG:
                return self._query_backlog(context, proj_id)
            elif query_type == QueryType.ROADMAP:
                return self._query_roadmap(context, proj_id)
            else:
                return QueryResult(
                    success=False,
                    errors=[f"Unknown query type: {query_type}"]
                )

        except Exception as e:
            logger.error(f"Failed to execute query {context.entity_type.value}: {e}")
            return QueryResult(
                success=False,
                errors=[f"Failed to execute query: {str(e)}"]
            )

    # ==================== Query Handlers ====================

    def _query_simple(
        self,
        context: OperationContext,
        project_id: int
    ) -> QueryResult:
        """Execute SIMPLE query (list entities).

        Args:
            context: OperationContext with entity_type
            project_id: Project ID

        Returns:
            QueryResult with entity list
        """
        if context.entity_type == EntityType.PROJECT:
            projects = self.state_manager.list_projects()

            # Filter by identifier if provided
            if context.identifier is not None:
                if isinstance(context.identifier, int):
                    # Filter by ID
                    projects = [p for p in projects if p.id == context.identifier]
                elif isinstance(context.identifier, str):
                    # Filter by name (case-insensitive partial match)
                    projects = [p for p in projects
                               if context.identifier.lower() in p.project_name.lower()]

            return QueryResult(
                success=True,
                query_type='simple',
                entity_type='project',
                results={
                    'query_type': 'simple',
                    'entity_type': 'project',
                    'entities': [
                        {
                            'id': p.id,
                            'name': p.project_name,
                            'description': p.description,
                            'status': p.status.value
                        }
                        for p in projects
                    ],
                    'count': len(projects)
                }
            )

        elif context.entity_type == EntityType.MILESTONE:
            milestones = self.state_manager.list_milestones(project_id)

            # Filter by identifier if provided
            if context.identifier is not None:
                if isinstance(context.identifier, int):
                    # Filter by ID
                    milestones = [m for m in milestones if m.id == context.identifier]
                elif isinstance(context.identifier, str):
                    # Filter by name (case-insensitive partial match)
                    milestones = [m for m in milestones
                                 if context.identifier.lower() in m.name.lower()]

            return QueryResult(
                success=True,
                query_type='simple',
                entity_type='milestone',
                results={
                    'query_type': 'simple',
                    'entity_type': 'milestone',
                    'entities': [
                        {
                            'id': m.id,
                            'name': m.name,
                            'description': m.description,
                            'status': 'COMPLETED' if m.achieved else 'ACTIVE'
                        }
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

            tasks = self.state_manager.list_tasks(
                project_id=project_id,
                task_type=task_type,
                limit=50
            )
            return QueryResult(
                success=True,
                query_type='simple',
                entity_type=context.entity_type.value,
                results={
                    'query_type': 'simple',
                    'entity_type': context.entity_type.value,
                    'entities': [
                        {
                            'id': t.id,
                            'title': t.title,
                            'description': t.description,
                            'status': t.status.value,
                            'priority': t.priority
                        }
                        for t in tasks
                    ],
                    'count': len(tasks)
                }
            )

    def _query_hierarchical(
        self,
        context: OperationContext,
        project_id: int
    ) -> QueryResult:
        """Execute HIERARCHICAL query (show task hierarchies: epics → stories → tasks).

        Args:
            context: OperationContext
            project_id: Project ID

        Returns:
            QueryResult with hierarchical task structure
        """
        # Get all epics for project
        epics = self.state_manager.list_tasks(
            project_id=project_id,
            task_type=TaskType.EPIC,
            limit=50
        )

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
                        {
                            'task_id': t.id,
                            'task_title': t.title,
                            'task_status': t.status.value
                        }
                        for t in tasks
                    ]
                }

                epic_data['stories'].append(story_data)

            hierarchy.append(epic_data)

        return QueryResult(
            success=True,
            query_type='hierarchical',
            entity_type='task',
            results={
                'query_type': 'hierarchical',
                'project_id': project_id,
                'hierarchy': hierarchy,
                'epic_count': len(hierarchy)
            }
        )

    def _query_next_steps(
        self,
        context: OperationContext,
        project_id: int
    ) -> QueryResult:
        """Execute NEXT_STEPS query (show next pending tasks).

        Args:
            context: OperationContext
            project_id: Project ID

        Returns:
            QueryResult with next pending tasks
        """
        # Get all pending/active tasks for project
        all_tasks = self.state_manager.list_tasks(
            project_id=project_id,
            limit=100
        )
        pending_tasks = [
            t for t in all_tasks
            if t.status in [TaskStatus.READY, TaskStatus.PENDING, TaskStatus.RUNNING]
        ]

        # Sort by priority (lower number = higher priority)
        pending_tasks.sort(key=lambda t: t.priority)

        return QueryResult(
            success=True,
            query_type='next_steps',
            entity_type='task',
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

    def _query_backlog(
        self,
        context: OperationContext,
        project_id: int
    ) -> QueryResult:
        """Execute BACKLOG query (show all pending tasks).

        Args:
            context: OperationContext
            project_id: Project ID

        Returns:
            QueryResult with all pending tasks
        """
        # Get all pending tasks for this project
        all_tasks = self.state_manager.list_tasks(
            project_id=project_id,
            limit=200
        )
        pending_tasks = [
            t for t in all_tasks
            if t.status in [TaskStatus.READY, TaskStatus.PENDING, TaskStatus.RUNNING]
        ]

        return QueryResult(
            success=True,
            query_type='backlog',
            entity_type='task',
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

    def _query_roadmap(
        self,
        context: OperationContext,
        project_id: int
    ) -> QueryResult:
        """Execute ROADMAP query (show milestones and associated epics).

        Args:
            context: OperationContext
            project_id: Project ID

        Returns:
            QueryResult with roadmap data
        """
        # Get all milestones for project
        milestones = self.state_manager.list_milestones(project_id)

        roadmap = []
        for milestone in milestones:
            milestone_data = {
                'milestone_id': milestone.id,
                'milestone_name': milestone.name,
                'milestone_status': 'COMPLETED' if milestone.achieved else 'ACTIVE',
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

        return QueryResult(
            success=True,
            query_type='roadmap',
            entity_type='milestone',
            results={
                'query_type': 'roadmap',
                'project_id': project_id,
                'milestones': roadmap,
                'milestone_count': len(roadmap)
            }
        )
