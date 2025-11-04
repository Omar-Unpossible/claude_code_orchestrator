"""ParallelAgentCoordinator - Manages parallel execution of subtasks with multiple agents.

This module provides coordination for multiple Claude Code agents executing subtasks
simultaneously. It handles agent spawning, monitoring, failure handling, and result merging.

Key Features:
- Spawn parallel agents (one per subtask in parallel group)
- Monitor agent progress with timeouts
- Handle failures with retry logic
- Merge results from successful agents
- Enforce RULE_SINGLE_AGENT_TESTING (no parallel testing)
- Track parallel attempts for learning

Thread-safe for concurrent access.
"""

# =============================================================================
# DEPRECATED: This module implemented Obra-level parallelization (spawning multiple agents).
#
# This approach has been deprecated in favor of Claude-driven parallelization, where:
# - Obra provides suggestions (via StructuredPromptBuilder)
# - Claude decides whether to parallelize (using Task tool)
# - Claude handles code merging (within its context window)
#
# This module is kept for reference but should not be used in production.
#
# See ADR-005 (docs/decisions/ADR-005-claude-driven-parallelization.md) for rationale.
# =============================================================================

import warnings
import logging

warnings.warn(
    "ParallelAgentCoordinator is deprecated. Use Claude-driven parallelization instead.",
    DeprecationWarning,
    stacklevel=2
)
import time
from datetime import datetime, UTC
from queue import Queue, Empty
from threading import Thread, RLock
from typing import List, Dict, Any, Optional, Callable

from src.core.exceptions import OrchestratorException
from src.core.state import StateManager
from src.orchestration.subtask import SubTask
from src.plugins.base import AgentPlugin
from src.plugins.exceptions import AgentException

logger = logging.getLogger(__name__)


class ParallelAgentCoordinator:
    """
    DEPRECATED: Coordinates multiple agents executing subtasks in parallel.

    This class has been deprecated in favor of Claude-driven parallelization.
    See ADR-005 for details.

    Responsibilities:
    - Spawn parallel agents (one per subtask in parallel group)
    - Monitor agent progress and status
    - Handle agent failures with retry logic
    - Merge results from successful agents
    - Enforce sequential testing rule (no parallel testing)
    - Track parallel attempts for learning

    Thread-safe for concurrent access.

    Example Usage:
        >>> coordinator = ParallelAgentCoordinator(
        ...     state_manager=state_manager,
        ...     agent_factory=lambda: AgentRegistry.get('claude_code_local')(),
        ...     config={'max_parallel_agents': 5}
        ... )
        >>> results = coordinator.execute_parallel(
        ...     subtasks=subtasks,
        ...     parent_task=task,
        ...     context={'project_id': 1}
        ... )
    """

    def __init__(
        self,
        state_manager: StateManager,
        agent_factory: Optional[Callable[[], AgentPlugin]] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize coordinator.

        DEPRECATED: Use Claude-driven parallelization instead.

        Args:
            state_manager: StateManager for logging and state tracking
            agent_factory: Factory function to create agent instances
            config: Configuration dict with:
                - max_parallel_agents: int (default 5)
                - agent_timeout_seconds: int (default 600)
                - retry_failed_agents: bool (default True)
                - max_retries: int (default 2)
                - parallelization_strategy: str (default 'parallel_groups')

        Raises:
            ValueError: If state_manager is None
        """
        warnings.warn(
            "ParallelAgentCoordinator is deprecated and should not be used",
            DeprecationWarning,
            stacklevel=2
        )
        if state_manager is None:
            raise ValueError("state_manager cannot be None")

        self._state_manager = state_manager
        self._agent_factory = agent_factory
        self._config = config or {}
        self._lock = RLock()

        # Configuration with defaults
        self._max_parallel_agents = self._config.get('max_parallel_agents', 5)
        self._agent_timeout_seconds = self._config.get('agent_timeout_seconds', 600)
        self._retry_failed_agents = self._config.get('retry_failed_agents', True)
        self._max_retries = self._config.get('max_retries', 2)
        self._parallelization_strategy = self._config.get(
            'parallelization_strategy',
            'parallel_groups'
        )

        logger.info(
            f"ParallelAgentCoordinator initialized: "
            f"max_agents={self._max_parallel_agents}, "
            f"timeout={self._agent_timeout_seconds}s, "
            f"retry={self._retry_failed_agents} (max={self._max_retries})"
        )

    def execute_parallel(
        self,
        subtasks: List[SubTask],
        parent_task: Any,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute subtasks in parallel groups.

        Process:
        1. Group subtasks by parallel_group
        2. For each group (sequential):
           a. Spawn agents for all tasks in group (parallel)
           b. Monitor agent progress
           c. Collect results
           d. Handle failures
        3. Merge all results
        4. Return consolidated results

        Args:
            subtasks: List of SubTask instances
            parent_task: Original parent task
            context: Execution context

        Returns:
            List of subtask results (one per subtask)

        Raises:
            OrchestratorException: If critical failure occurs

        Example:
            >>> results = coordinator.execute_parallel(
            ...     subtasks=[subtask1, subtask2, subtask3],
            ...     parent_task=task,
            ...     context={'project_id': 1}
            ... )
            >>> for result in results:
            ...     print(f"Subtask {result['subtask_id']}: {result['status']}")
        """
        if not subtasks:
            logger.warning("execute_parallel called with empty subtasks list")
            return []

        logger.info(f"Starting parallel execution of {len(subtasks)} subtasks")

        # Group subtasks by parallel_group
        groups = self._group_subtasks_by_parallel_group(subtasks)

        all_results = []

        # Execute each group sequentially
        for group_id, group_subtasks in groups.items():
            logger.info(
                f"Executing parallel group {group_id} with {len(group_subtasks)} subtasks"
            )

            # Enforce testing rule
            self._enforce_testing_rule(group_subtasks)

            # Execute group in parallel
            group_results = self._spawn_agents_for_group(
                subtasks=group_subtasks,
                parent_task=parent_task,
                context=context
            )

            all_results.extend(group_results)

        # Merge and sort results
        merged_results = self._merge_agent_results(all_results, subtasks)

        logger.info(
            f"Parallel execution complete: {len(merged_results)} results, "
            f"{sum(1 for r in merged_results if r['status'] == 'completed')} successful"
        )

        return merged_results

    def _group_subtasks_by_parallel_group(
        self,
        subtasks: List[SubTask]
    ) -> Dict[Optional[int], List[SubTask]]:
        """
        Group subtasks by parallel_group field.

        Args:
            subtasks: List of subtasks to group

        Returns:
            Dictionary mapping parallel_group ID to list of subtasks

        Note:
            Subtasks with parallel_group=None are placed in individual groups
        """
        groups: Dict[Optional[int], List[SubTask]] = {}

        for subtask in subtasks:
            group_id = subtask.parallel_group

            # If no parallel group, create individual group
            if group_id is None:
                # Use negative subtask_id as unique group identifier
                group_id = -subtask.subtask_id

            if group_id not in groups:
                groups[group_id] = []

            groups[group_id].append(subtask)

        # Sort groups by key for deterministic execution order
        return dict(sorted(groups.items()))

    def _spawn_agents_for_group(
        self,
        subtasks: List[SubTask],
        parent_task: Any,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Spawn and manage agents for a parallel group.

        Args:
            subtasks: List of subtasks in this parallel group
            parent_task: Parent task
            context: Execution context

        Returns:
            List of results (one per subtask)

        Process:
        1. Create agent for each subtask
        2. Start agents in threads
        3. Monitor progress with timeouts
        4. Collect results as agents complete
        5. Handle timeouts and failures
        """
        if not subtasks:
            return []

        # Track start time
        started_at = datetime.now(UTC)

        # Limit to max_parallel_agents
        num_agents = min(len(subtasks), self._max_parallel_agents)

        if num_agents < len(subtasks):
            logger.warning(
                f"Limiting parallel agents from {len(subtasks)} to {num_agents} "
                f"(max_parallel_agents={self._max_parallel_agents})"
            )
            # TODO: Handle excess subtasks (batch or queue them)

        # Create result queue (thread-safe)
        result_queue: Queue = Queue()

        # Create threads for each subtask
        threads: List[Thread] = []
        agent_subtasks = subtasks[:num_agents]  # Only take what we can handle

        for subtask in agent_subtasks:
            thread = Thread(
                target=self._execute_agent_for_subtask,
                args=(subtask, parent_task, result_queue, context),
                name=f"Agent-Subtask-{subtask.subtask_id}",
                daemon=True
            )
            threads.append(thread)

        # Start all threads
        logger.info(f"Starting {len(threads)} agent threads")
        for thread in threads:
            thread.start()

        # Monitor progress and collect results
        results = self._monitor_agent_progress(
            threads=threads,
            result_queue=result_queue,
            subtasks=agent_subtasks,
            timeout_seconds=self._agent_timeout_seconds
        )

        # Track completion time
        completed_at = datetime.now(UTC)

        # Log parallel attempt
        self._log_parallel_attempt(
            parent_task_id=parent_task.id,
            subtask_ids=[st.subtask_id for st in agent_subtasks],
            results=results,
            started_at=started_at,
            completed_at=completed_at
        )

        return results

    def _execute_agent_for_subtask(
        self,
        subtask: SubTask,
        parent_task: Any,
        result_queue: Queue,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Execute a single subtask with an agent (runs in thread).

        Args:
            subtask: Subtask to execute
            parent_task: Parent task
            result_queue: Queue to put result in
            context: Execution context

        Puts result dict in queue:
        {
            'subtask_id': int,
            'status': 'completed' | 'failed' | 'timeout',
            'result': Any,
            'error': Optional[str],
            'duration_seconds': float
        }
        """
        start_time = time.time()
        result = {
            'subtask_id': subtask.subtask_id,
            'status': 'failed',
            'result': None,
            'error': None,
            'duration_seconds': 0.0
        }

        try:
            logger.info(f"Agent starting execution of subtask {subtask.subtask_id}")

            # Create agent instance
            if self._agent_factory is None:
                raise OrchestratorException(
                    "agent_factory not configured",
                    context={'subtask_id': subtask.subtask_id},
                    recovery="Configure agent_factory in ParallelAgentCoordinator"
                )

            agent = self._agent_factory()

            # Initialize agent (if needed)
            if hasattr(agent, 'initialize') and callable(agent.initialize):
                agent_config = context.get('agent_config', {}) if context else {}
                agent.initialize(agent_config)

            # Mark subtask as in progress
            subtask.mark_in_progress()

            # Build prompt from subtask
            prompt = self._build_prompt_from_subtask(subtask, parent_task, context)

            # Execute with agent
            response = agent.send_prompt(prompt, context=context)

            # Mark subtask as completed
            subtask.mark_completed()

            # Success
            result['status'] = 'completed'
            result['result'] = response

            logger.info(
                f"Agent completed subtask {subtask.subtask_id} successfully "
                f"in {time.time() - start_time:.2f}s"
            )

            # Cleanup agent
            if hasattr(agent, 'cleanup') and callable(agent.cleanup):
                try:
                    agent.cleanup()
                except Exception as cleanup_err:
                    logger.warning(
                        f"Agent cleanup failed for subtask {subtask.subtask_id}: {cleanup_err}"
                    )

        except AgentException as agent_err:
            logger.error(
                f"Agent failed for subtask {subtask.subtask_id}: {agent_err}"
            )
            result['status'] = 'failed'
            result['error'] = str(agent_err)

            # Mark subtask as failed
            try:
                if subtask.status == 'in_progress':
                    subtask.mark_failed()
            except ValueError:
                pass  # Already in different state

        except Exception as exc:
            logger.exception(
                f"Unexpected error in agent for subtask {subtask.subtask_id}: {exc}"
            )
            result['status'] = 'failed'
            result['error'] = f"Unexpected error: {str(exc)}"

            # Mark subtask as failed
            try:
                if subtask.status == 'in_progress':
                    subtask.mark_failed()
            except ValueError:
                pass

        finally:
            # Record duration
            result['duration_seconds'] = time.time() - start_time

            # Put result in queue
            result_queue.put(result)

    def _build_prompt_from_subtask(
        self,
        subtask: SubTask,
        parent_task: Any,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Build prompt from subtask details.

        Args:
            subtask: Subtask to build prompt from
            parent_task: Parent task for context
            context: Additional context

        Returns:
            Formatted prompt string
        """
        prompt = f"""# Task: {subtask.title}

## Description
{subtask.description}

## Context
- Parent Task: {parent_task.title if hasattr(parent_task, 'title') else 'N/A'}
- Estimated Complexity: {subtask.estimated_complexity}/100
- Estimated Duration: {subtask.estimated_duration_minutes} minutes

## Requirements
- Complete the task as described
- Ensure code quality and correctness
- Follow best practices
"""

        # Add dependencies if any
        if subtask.dependencies:
            prompt += f"\n## Dependencies\nThis task depends on subtasks: {subtask.dependencies}\n"

        return prompt

    def _monitor_agent_progress(
        self,
        threads: List[Thread],
        result_queue: Queue,
        subtasks: List[SubTask],
        timeout_seconds: int
    ) -> List[Dict[str, Any]]:
        """
        Monitor running agent threads and collect results.

        Args:
            threads: List of agent threads
            result_queue: Queue where agents put results
            subtasks: List of subtasks being executed
            timeout_seconds: Max time to wait per agent

        Returns:
            List of results (successful + failed + timed out)

        Behavior:
        - Waits for all threads to complete or timeout
        - Collects results from queue as agents finish
        - Marks timed-out agents as failed
        - Returns all results (including failures)
        """
        results = []
        start_time = time.time()

        # Calculate per-thread timeout (use global timeout for all threads)
        deadline = start_time + timeout_seconds

        logger.info(
            f"Monitoring {len(threads)} agent threads "
            f"(timeout={timeout_seconds}s, deadline={deadline - start_time:.1f}s)"
        )

        # Track which subtasks have returned results
        completed_subtask_ids = set()

        # Wait for all threads with timeout
        for thread in threads:
            remaining = deadline - time.time()

            if remaining <= 0:
                logger.warning(
                    f"Global timeout reached, {len(threads) - len(completed_subtask_ids)} "
                    "threads still running"
                )
                break

            # Wait for thread with remaining time
            thread.join(timeout=remaining)

            # Collect results from queue (non-blocking)
            while not result_queue.empty():
                try:
                    result = result_queue.get_nowait()
                    results.append(result)
                    completed_subtask_ids.add(result['subtask_id'])
                except Empty:
                    break

        # Collect any remaining results
        while not result_queue.empty():
            try:
                result = result_queue.get_nowait()
                results.append(result)
                completed_subtask_ids.add(result['subtask_id'])
            except Empty:
                break

        # Handle timed-out threads
        for subtask in subtasks:
            if subtask.subtask_id not in completed_subtask_ids:
                logger.error(f"Subtask {subtask.subtask_id} timed out")
                results.append({
                    'subtask_id': subtask.subtask_id,
                    'status': 'timeout',
                    'result': None,
                    'error': f'Agent timed out after {timeout_seconds}s',
                    'duration_seconds': timeout_seconds
                })

                # Mark subtask as failed
                try:
                    if subtask.status == 'in_progress':
                        subtask.mark_failed()
                except ValueError:
                    pass

        elapsed = time.time() - start_time
        logger.info(
            f"Agent monitoring complete: {len(results)} results in {elapsed:.2f}s, "
            f"{sum(1 for r in results if r['status'] == 'completed')} successful, "
            f"{sum(1 for r in results if r['status'] == 'failed')} failed, "
            f"{sum(1 for r in results if r['status'] == 'timeout')} timed out"
        )

        return results

    def _handle_agent_failure(
        self,
        subtask: SubTask,
        error: str,
        retry_count: int,
        parent_task: Any,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Handle agent failure with retry logic.

        Args:
            subtask: Failed subtask
            error: Error message
            retry_count: Current retry count
            parent_task: Parent task
            context: Execution context

        Returns:
            Result if retry successful, None if retry failed

        Behavior:
        - Logs failure to StateManager
        - Retries if retry_count < max_retries
        - Returns None if all retries exhausted
        """
        logger.warning(
            f"Agent failed for subtask {subtask.subtask_id}: {error} "
            f"(retry {retry_count}/{self._max_retries})"
        )

        # Check if retries enabled and available
        if not self._retry_failed_agents or retry_count >= self._max_retries:
            logger.error(
                f"Subtask {subtask.subtask_id} failed permanently after "
                f"{retry_count} retries: {error}"
            )
            return None

        # Retry
        logger.info(f"Retrying subtask {subtask.subtask_id} (attempt {retry_count + 1})")

        # Reset subtask status
        subtask.status = 'pending'

        # Execute in single-threaded mode for retry (simpler)
        result_queue: Queue = Queue()

        self._execute_agent_for_subtask(
            subtask=subtask,
            parent_task=parent_task,
            result_queue=result_queue,
            context=context
        )

        # Get result
        try:
            result = result_queue.get(timeout=1.0)

            if result['status'] == 'completed':
                logger.info(f"Retry successful for subtask {subtask.subtask_id}")
                return result
            else:
                # Recursive retry
                return self._handle_agent_failure(
                    subtask=subtask,
                    error=result.get('error', 'Unknown error'),
                    retry_count=retry_count + 1,
                    parent_task=parent_task,
                    context=context
                )

        except Empty:
            logger.error(f"Retry timed out for subtask {subtask.subtask_id}")
            return None

    def _merge_agent_results(
        self,
        results: List[Dict[str, Any]],
        subtasks: List[SubTask]
    ) -> List[Dict[str, Any]]:
        """
        Merge results from parallel agents.

        Args:
            results: List of results from agents
            subtasks: List of subtasks

        Returns:
            Merged and sorted results (by subtask_id)

        Behavior:
        - Sorts results by subtask_id
        - Validates all subtasks have results
        - Adds missing results for failed subtasks
        """
        # Create map of subtask_id to result
        result_map = {r['subtask_id']: r for r in results}

        # Ensure all subtasks have results
        merged_results = []

        for subtask in subtasks:
            if subtask.subtask_id in result_map:
                merged_results.append(result_map[subtask.subtask_id])
            else:
                # Missing result - create failure entry
                logger.warning(
                    f"No result found for subtask {subtask.subtask_id}, "
                    "creating failure entry"
                )
                merged_results.append({
                    'subtask_id': subtask.subtask_id,
                    'status': 'failed',
                    'result': None,
                    'error': 'No result received from agent',
                    'duration_seconds': 0.0
                })

        # Sort by subtask_id for consistency
        merged_results.sort(key=lambda r: r['subtask_id'])

        return merged_results

    def _enforce_testing_rule(
        self,
        subtasks: List[SubTask]
    ) -> None:
        """
        Enforce RULE_SINGLE_AGENT_TESTING.

        No parallel testing allowed. If any subtask contains "test" in title/description,
        raise exception if multiple subtasks in parallel group.

        Args:
            subtasks: List of subtasks to validate

        Raises:
            OrchestratorException: If testing rule violated
        """
        # Check if any subtask is a testing task
        testing_tasks = [
            st for st in subtasks
            if 'test' in st.title.lower() or 'test' in st.description.lower()
        ]

        if len(testing_tasks) > 1:
            raise OrchestratorException(
                "RULE_SINGLE_AGENT_TESTING violated: "
                f"Cannot run {len(testing_tasks)} testing tasks in parallel. "
                "Testing tasks must be sequential.",
                context={
                    'testing_task_ids': [st.subtask_id for st in testing_tasks],
                    'testing_task_titles': [st.title for st in testing_tasks]
                },
                recovery=(
                    "Decompose testing tasks into sequential subtasks or "
                    "assign them to different parallel groups"
                )
            )

        if testing_tasks and len(subtasks) > 1:
            raise OrchestratorException(
                "RULE_SINGLE_AGENT_TESTING violated: "
                "Cannot run testing task in parallel with other tasks. "
                "Testing tasks must be isolated.",
                context={
                    'testing_task_id': testing_tasks[0].subtask_id,
                    'testing_task_title': testing_tasks[0].title,
                    'other_task_count': len(subtasks) - 1
                },
                recovery=(
                    "Move testing task to separate parallel group or "
                    "execute testing tasks sequentially"
                )
            )

    def _log_parallel_attempt(
        self,
        parent_task_id: int,
        subtask_ids: List[int],
        results: List[Dict[str, Any]],
        started_at: datetime,
        completed_at: datetime
    ) -> None:
        """
        Log parallel execution attempt to StateManager.

        Args:
            parent_task_id: Parent task ID
            subtask_ids: List of subtasks executed in parallel
            results: List of results from agents
            started_at: Start timestamp
            completed_at: Completion timestamp
        """
        with self._lock:
            # Calculate metrics
            success = all(r['status'] == 'completed' for r in results)
            failed_count = sum(1 for r in results if r['status'] in ('failed', 'timeout'))
            total_duration = (completed_at - started_at).total_seconds()

            # Calculate speedup estimate (rough)
            sequential_estimate = sum(r['duration_seconds'] for r in results)
            speedup_factor = (
                sequential_estimate / total_duration
                if total_duration > 0 else 0.0
            )

            # Build failure reason if failed
            failure_reason = None
            if not success:
                failed_results = [r for r in results if r['status'] != 'completed']
                failure_reason = '; '.join(
                    f"Subtask {r['subtask_id']}: {r.get('error', 'Unknown error')}"
                    for r in failed_results
                )

            # Create attempt data
            attempt_data = {
                'num_agents': len(subtask_ids),
                'agent_ids': [f"agent_{i}" for i in range(len(subtask_ids))],
                'subtask_ids': subtask_ids,
                'success': success,
                'failure_reason': failure_reason,
                'conflict_detected': False,  # TODO: Implement conflict detection
                'total_duration_seconds': total_duration,
                'sequential_estimate_seconds': sequential_estimate,
                'speedup_factor': speedup_factor,
                'max_concurrent_agents': len(subtask_ids),
                'failed_agent_count': failed_count,
                'parallelization_strategy': self._parallelization_strategy,
                'fallback_to_sequential': False,
                'execution_metadata': {
                    'timeout_seconds': self._agent_timeout_seconds,
                    'retry_enabled': self._retry_failed_agents,
                    'max_retries': self._max_retries
                },
                'started_at': started_at,
                'completed_at': completed_at
            }

            try:
                self._state_manager.log_parallel_attempt(
                    task_id=parent_task_id,
                    attempt_data=attempt_data
                )
                logger.info(
                    f"Logged parallel attempt: task_id={parent_task_id}, "
                    f"agents={len(subtask_ids)}, success={success}, "
                    f"duration={total_duration:.2f}s, speedup={speedup_factor:.2f}x"
                )
            except Exception as log_err:
                logger.error(
                    f"Failed to log parallel attempt: {log_err}",
                    exc_info=True
                )
