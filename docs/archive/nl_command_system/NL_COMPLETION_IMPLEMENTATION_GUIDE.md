# NL Completion Implementation Guide (Machine-Optimized)

**For**: Claude Code LLM Agent
**Starting Point**: Commit `5b514d6` (v1.6.1-pre-nl-redesign)
**Target Version**: v1.6.2
**Estimated Tokens**: ~50K per phase

---

## Critical Context

**Project**: Obra (Claude Code Orchestrator) - AI orchestration platform
**Architecture**: Hybrid local (Qwen) + remote (Claude Code) LLMs
**Current State**: NL command system 92% functional (233/253 tests passing)
**Goal**: Complete remaining 8% - implement confirmation workflow and StateManager extensions

**What Works**: CREATE, QUERY operations
**What Needs Work**: UPDATE/DELETE (missing confirmation), task mutations (missing StateManager APIs)

**Key Constraints**:
- Follow existing patterns in `src/core/state.py` for StateManager methods
- No breaking changes to existing APIs
- Test coverage ≥90% for new code
- Read `docs/development/TEST_GUIDELINES.md` before writing tests (WSL2 crash prevention)

---

## Phase 1: Confirmation Workflow (Priority 1)

### Problem
UPDATE/DELETE operations show confirmation prompt but don't handle "yes/no" responses:
```
User: delete project #3
System: [confirmation prompt]
User: yes
System: ERROR - can't understand "yes"
```

### Solution Architecture
```python
class NLCommandProcessor:
    pending_confirmation: Optional[PendingOperation]

    def process(message):
        if pending_confirmation and is_confirmation(message):
            return execute_pending(confirmed=True)
        # ... normal flow
```

### Implementation Files

**File 1: `src/nl/nl_command_processor.py`**

Add to class definition:
```python
from dataclasses import dataclass
import time

@dataclass
class PendingOperation:
    context: OperationContext
    project_id: int
    timestamp: float
    original_message: str
```

Add to `__init__()`:
```python
self.pending_confirmation: Optional[PendingOperation] = None
self.confirmation_timeout = config.get('nl_commands.confirmation_timeout', 60)
```

Add helper methods:
```python
def _is_confirmation_response(self, message: str) -> bool:
    """Check if message is yes/y/confirm/ok/proceed."""
    confirmation_keywords = {'yes', 'y', 'confirm', 'ok', 'proceed', 'go ahead'}
    return message.strip().lower() in confirmation_keywords

def _is_cancellation_response(self, message: str) -> bool:
    """Check if message is no/n/cancel/abort."""
    cancellation_keywords = {'no', 'n', 'cancel', 'abort', 'stop', 'nevermind'}
    return message.strip().lower() in cancellation_keywords

def _handle_confirmation_response(self, message: str, project_id: Optional[int] = None) -> NLResponse:
    """Execute pending operation after user confirms."""
    # Check timeout
    if time.time() - self.pending_confirmation.timestamp > self.confirmation_timeout:
        self.pending_confirmation = None
        return NLResponse(
            response=f"{Fore.YELLOW}Confirmation timeout. Please try again.{Style.RESET_ALL}",
            intent='ERROR',
            success=False
        )

    # Execute with confirmed=True
    execution_result = self.command_executor.execute(
        self.pending_confirmation.context,
        project_id=self.pending_confirmation.project_id,
        confirmed=True
    )

    # Clear pending state
    operation = self.pending_confirmation.context.operation.value
    self.pending_confirmation = None

    # Format response
    response = self.response_formatter.format(
        execution_result,
        intent='COMMAND',
        operation=operation
    )

    return NLResponse(
        response=response,
        intent='COMMAND',
        success=execution_result.success,
        updated_context=self._update_conversation_context(message, 'COMMAND', {})
    )

def _handle_cancellation(self) -> NLResponse:
    """Cancel pending operation."""
    operation = self.pending_confirmation.context.operation.value
    entity_type = self.pending_confirmation.context.entity_type.value
    self.pending_confirmation = None

    return NLResponse(
        response=f"{Fore.GREEN}✓ Cancelled {operation} {entity_type} operation{Style.RESET_ALL}",
        intent='COMMAND',
        success=True
    )
```

Modify `process()` method - add at the very beginning:
```python
def process(self, message: str, context: Optional[Dict[str, Any]] = None,
            project_id: Optional[int] = None, confirmed: bool = False) -> NLResponse:
    """Process natural language message through pipeline."""

    if not message or not message.strip():
        return NLResponse(response="Please provide a message", intent="INVALID", success=False)

    # NEW: Check for confirmation response first
    if self.pending_confirmation:
        if self._is_confirmation_response(message):
            return self._handle_confirmation_response(message, project_id)
        elif self._is_cancellation_response(message):
            return self._handle_cancellation()
        # Else: treat as new command (implicit cancellation)
        self.pending_confirmation = None

    # ... existing code continues ...
```

Modify `_handle_command()` - update confirmation handling (around line 405):
```python
# Inside _handle_command(), after execution_result = self.command_executor.execute(...)
if execution_result.confirmation_required:
    # Store pending operation
    self.pending_confirmation = PendingOperation(
        context=operation_context,
        project_id=proj_id,
        timestamp=time.time(),
        original_message=message
    )

    # Return confirmation prompt
    response = self.response_formatter.format(
        execution_result,
        intent='COMMAND',
        operation=operation_context.operation.value
    )

    return NLResponse(
        response=response,
        intent='CONFIRMATION',
        success=False,
        updated_context=self._update_conversation_context(message, 'CONFIRMATION', {})
    )
```

**File 2: `src/nl/response_formatter.py`**

Update `_format_confirmation()` method:
```python
def _format_confirmation(self, result: ExecutionResult) -> str:
    """Format confirmation prompt."""
    entity_type = result.results.get('entity_type', 'item')
    operation = result.results.get('operation', 'modify')
    identifier = result.results.get('identifier')

    # Build identifier part
    identifier_part = ""
    if identifier is not None:
        if isinstance(identifier, int):
            identifier_part = f" #{identifier}"
        else:
            identifier_part = f" '{identifier}'"

    message = (
        f"{Fore.YELLOW}⚠ Confirmation required:{Style.RESET_ALL}\n"
        f"  This will {operation} {entity_type}{identifier_part}.\n"
        f"\n"
        f"  Type 'yes' to confirm, 'no' to cancel"
    )
    return message
```

**File 3: `tests/nl/test_confirmation_workflow.py` (NEW)**

```python
"""Tests for interactive confirmation workflow."""

import pytest
from unittest.mock import Mock, MagicMock
from src.nl.nl_command_processor import NLCommandProcessor, PendingOperation
from src.nl.types import OperationContext, OperationType, EntityType
from src.core.state import StateManager
import time

class TestConfirmationWorkflow:
    """Test confirmation workflow for UPDATE/DELETE operations."""

    @pytest.fixture
    def processor(self, mock_llm, test_state_manager):
        """Create NL processor with mocked components."""
        from src.nl.nl_command_processor import NLCommandProcessor
        config = {
            'nl_commands': {
                'enabled': True,
                'require_confirmation_for': ['update', 'delete'],
                'confirmation_timeout': 5
            }
        }
        return NLCommandProcessor(
            llm_plugin=mock_llm,
            state_manager=test_state_manager,
            config=config
        )

    def test_update_requires_confirmation(self, processor, mock_llm):
        """Test that UPDATE operations require confirmation."""
        # Setup LLM to return proper classifications
        mock_llm.generate.side_effect = [
            '{"intent": "COMMAND", "confidence": 0.95}',
            '{"operation_type": "UPDATE", "confidence": 0.94}',
            '{"entity_type": "project", "confidence": 0.96}',
            '{"identifier": 1, "confidence": 0.98}',
            '{"parameters": {"status": "COMPLETED"}, "confidence": 0.90}'
        ]

        response = processor.process("update project 1 status to completed")

        assert response.intent == 'CONFIRMATION'
        assert not response.success
        assert 'yes' in response.response.lower()
        assert processor.pending_confirmation is not None

    def test_confirmation_yes_executes(self, processor, mock_llm):
        """Test that 'yes' executes pending operation."""
        # First create pending operation
        context = OperationContext(
            operation=OperationType.UPDATE,
            entity_type=EntityType.PROJECT,
            identifier=1,
            parameters={'status': 'COMPLETED'},
            confidence=0.9,
            raw_input='update project 1'
        )
        processor.pending_confirmation = PendingOperation(
            context=context,
            project_id=1,
            timestamp=time.time(),
            original_message='update project 1'
        )

        # Now confirm
        response = processor.process("yes")

        assert response.success
        assert processor.pending_confirmation is None

    def test_confirmation_no_cancels(self, processor):
        """Test that 'no' cancels pending operation."""
        context = OperationContext(
            operation=OperationType.DELETE,
            entity_type=EntityType.PROJECT,
            identifier=1,
            parameters={},
            confidence=0.9,
            raw_input='delete project 1'
        )
        processor.pending_confirmation = PendingOperation(
            context=context,
            project_id=1,
            timestamp=time.time(),
            original_message='delete project 1'
        )

        response = processor.process("no")

        assert response.success
        assert 'cancelled' in response.response.lower()
        assert processor.pending_confirmation is None

    def test_confirmation_timeout(self, processor):
        """Test that confirmations timeout."""
        context = OperationContext(
            operation=OperationType.DELETE,
            entity_type=EntityType.PROJECT,
            identifier=1,
            parameters={},
            confidence=0.9,
            raw_input='delete project 1'
        )
        processor.pending_confirmation = PendingOperation(
            context=context,
            project_id=1,
            timestamp=time.time() - 100,  # 100 seconds ago (timeout is 5s)
            original_message='delete project 1'
        )

        response = processor.process("yes")

        assert not response.success
        assert 'timeout' in response.response.lower()
        assert processor.pending_confirmation is None

    def test_new_command_cancels_pending(self, processor, mock_llm):
        """Test that new command implicitly cancels pending confirmation."""
        # Setup pending operation
        processor.pending_confirmation = PendingOperation(
            context=Mock(),
            project_id=1,
            timestamp=time.time(),
            original_message='delete project 1'
        )

        # Setup LLM for new command
        mock_llm.generate.side_effect = [
            '{"intent": "COMMAND", "confidence": 0.95}',
            '{"operation_type": "QUERY", "confidence": 0.94}',
            # ... other stages
        ]

        # Issue new command
        response = processor.process("list projects")

        # Pending confirmation should be cleared
        assert processor.pending_confirmation is None

    @pytest.mark.parametrize("confirmation_word", [
        "yes", "y", "Y", "YES", "confirm", "ok", "proceed"
    ])
    def test_confirmation_variations(self, processor, confirmation_word):
        """Test various confirmation keywords."""
        processor.pending_confirmation = PendingOperation(
            context=Mock(operation=Mock(value='delete'), entity_type=Mock(value='project')),
            project_id=1,
            timestamp=time.time(),
            original_message='delete project 1'
        )

        assert processor._is_confirmation_response(confirmation_word)

    @pytest.mark.parametrize("cancellation_word", [
        "no", "n", "N", "NO", "cancel", "abort", "stop"
    ])
    def test_cancellation_variations(self, processor, cancellation_word):
        """Test various cancellation keywords."""
        processor.pending_confirmation = PendingOperation(
            context=Mock(operation=Mock(value='delete'), entity_type=Mock(value='project')),
            project_id=1,
            timestamp=time.time(),
            original_message='delete project 1'
        )

        assert processor._is_cancellation_response(cancellation_word)
```

**Testing Checklist Phase 1**:
```bash
# Run Phase 1 tests
pytest tests/nl/test_confirmation_workflow.py -v

# Expected: All tests pass
# If any fail, fix before proceeding to Phase 2
```

---

## Phase 2: StateManager Extensions (Priority 2)

### Problem
Task UPDATE/DELETE operations fail because StateManager lacks these methods.

### Solution
Add `update_task()` and `delete_task()` methods to StateManager following existing patterns.

### Implementation Files

**File 1: `src/core/state.py`**

Add after `update_task_status()` method (around line 475):

```python
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
```

**File 2: `src/nl/command_executor.py`**

Replace `_update_entity()` method (around line 484):

```python
def _update_entity(self, context: OperationContext, entity_id: int, project_id: int):
    """Update entity via StateManager.

    Args:
        context: OperationContext with entity_type and parameters
        entity_id: Entity ID to update
        project_id: Project ID
    """
    params = context.parameters

    if context.entity_type == EntityType.PROJECT:
        # Build updates dict for StateManager
        updates = {}

        if 'status' in params:
            # Map status string to ProjectStatus enum
            from core.models import ProjectStatus
            status_map = {
                'ACTIVE': ProjectStatus.ACTIVE,
                'INACTIVE': ProjectStatus.PAUSED,
                'PAUSED': ProjectStatus.PAUSED,
                'COMPLETED': ProjectStatus.COMPLETED,
                'ARCHIVED': ProjectStatus.ARCHIVED
            }
            status_str = params['status'].upper()
            if status_str in status_map:
                updates['status'] = status_map[status_str]

        if 'description' in params:
            updates['description'] = params['description']

        if 'name' in params or 'title' in params:
            updates['project_name'] = params.get('name') or params.get('title')

        # Use StateManager's update_project method
        self.state_manager.update_project(entity_id, updates)

    else:  # EPIC, STORY, TASK, SUBTASK
        # Build updates dict
        updates = {}

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
                updates['status'] = status_map[status_str]

        if 'title' in params:
            updates['title'] = params['title']

        if 'description' in params:
            updates['description'] = params['description']

        if 'priority' in params:
            updates['priority'] = self._normalize_priority(params['priority'])

        if 'dependencies' in params:
            updates['dependencies'] = params['dependencies']

        # Use StateManager's update_task method
        self.state_manager.update_task(entity_id, updates)
```

Replace `_delete_entity()` method (around line 556):

```python
def _delete_entity(self, context: OperationContext, entity_id: int, project_id: int):
    """Delete entity via StateManager.

    Args:
        context: OperationContext with entity_type
        entity_id: Entity ID to delete
        project_id: Project ID
    """
    if context.entity_type == EntityType.PROJECT:
        # Use StateManager's delete_project method
        self.state_manager.delete_project(entity_id, soft=True)

    elif context.entity_type == EntityType.MILESTONE:
        # Milestone deletion not yet supported
        raise ExecutionException(
            "Milestone deletion not yet supported via NL commands",
            recovery="Use CLI command: obra milestone delete <id>"
        )

    else:  # EPIC, STORY, TASK, SUBTASK
        # Use StateManager's delete_task method
        self.state_manager.delete_task(entity_id, soft=True)
```

**File 3: `tests/test_state_manager_task_operations.py` (NEW)**

```python
"""Tests for StateManager task update and delete operations."""

import pytest
from src.core.state import StateManager
from core.models import TaskStatus, TaskType

class TestTaskUpdate:
    """Test StateManager.update_task() method."""

    @pytest.fixture
    def state_with_task(self, test_state_manager):
        """Create state manager with a test task."""
        # Create project
        project = test_state_manager.create_project(
            name="Test Project",
            description="Test",
            working_dir="/tmp/test"
        )

        # Create task
        task = test_state_manager.create_task(
            project_id=project.id,
            task_data={
                'title': 'Original Title',
                'description': 'Original Description',
                'priority': 5,
                'task_type': TaskType.TASK
            }
        )

        return test_state_manager, task.id

    def test_update_task_title(self, state_with_task):
        """Test updating task title."""
        state, task_id = state_with_task

        updated = state.update_task(task_id, {'title': 'New Title'})

        assert updated.title == 'New Title'
        assert updated.description == 'Original Description'  # Unchanged

    def test_update_task_priority(self, state_with_task):
        """Test updating task priority."""
        state, task_id = state_with_task

        updated = state.update_task(task_id, {'priority': 1})

        assert updated.priority == 1

    def test_update_task_status(self, state_with_task):
        """Test updating task status."""
        state, task_id = state_with_task

        updated = state.update_task(task_id, {'status': TaskStatus.RUNNING})

        assert updated.status == TaskStatus.RUNNING

    def test_update_multiple_fields(self, state_with_task):
        """Test updating multiple task fields."""
        state, task_id = state_with_task

        updates = {
            'title': 'Updated Title',
            'priority': 3,
            'status': TaskStatus.COMPLETED
        }
        updated = state.update_task(task_id, updates)

        assert updated.title == 'Updated Title'
        assert updated.priority == 3
        assert updated.status == TaskStatus.COMPLETED

    def test_update_nonexistent_task(self, test_state_manager):
        """Test that updating nonexistent task raises exception."""
        from src.core.exceptions import DatabaseException

        with pytest.raises(DatabaseException) as exc_info:
            test_state_manager.update_task(999, {'title': 'New'})

        assert 'not found' in str(exc_info.value).lower()

    def test_update_ignores_invalid_fields(self, state_with_task):
        """Test that invalid fields are ignored."""
        state, task_id = state_with_task

        # Should not raise exception
        updated = state.update_task(task_id, {
            'title': 'Valid',
            'invalid_field': 'Should be ignored'
        })

        assert updated.title == 'Valid'
        assert not hasattr(updated, 'invalid_field')

class TestTaskDelete:
    """Test StateManager.delete_task() method."""

    @pytest.fixture
    def state_with_task(self, test_state_manager):
        """Create state manager with a test task."""
        project = test_state_manager.create_project(
            name="Test Project",
            description="Test",
            working_dir="/tmp/test"
        )
        task = test_state_manager.create_task(
            project_id=project.id,
            task_data={'title': 'Test Task', 'task_type': TaskType.TASK}
        )
        return test_state_manager, task.id

    def test_soft_delete_task(self, state_with_task):
        """Test soft deleting a task."""
        state, task_id = state_with_task

        state.delete_task(task_id, soft=True)

        # Task still exists but marked as deleted
        task = state.get_task(task_id)
        assert task is not None
        assert task.is_deleted is True

    def test_hard_delete_task(self, state_with_task):
        """Test hard deleting a task."""
        state, task_id = state_with_task

        state.delete_task(task_id, soft=False)

        # Task should not exist
        task = state.get_task(task_id)
        assert task is None

    def test_delete_nonexistent_task(self, test_state_manager):
        """Test that deleting nonexistent task raises exception."""
        from src.core.exceptions import DatabaseException

        with pytest.raises(DatabaseException) as exc_info:
            test_state_manager.delete_task(999)

        assert 'not found' in str(exc_info.value).lower()

    def test_soft_deleted_not_in_list(self, state_with_task):
        """Test that soft deleted tasks don't appear in list_tasks()."""
        state, task_id = state_with_task

        # Before delete
        tasks_before = state.list_tasks()
        assert any(t.id == task_id for t in tasks_before)

        # Soft delete
        state.delete_task(task_id, soft=True)

        # After delete - should not appear
        # Note: list_tasks() needs filter for is_deleted=False
        # This test may need adjustment based on list_tasks() implementation
```

**Testing Checklist Phase 2**:
```bash
# Run Phase 2 tests
pytest tests/test_state_manager_task_operations.py -v
pytest tests/nl/test_command_executor.py::TestExecuteUpdate -v
pytest tests/nl/test_command_executor.py::TestExecuteDelete -v
pytest tests/nl/test_integration_full_pipeline.py::TestFullPipelineUPDATE -v
pytest tests/nl/test_integration_full_pipeline.py::TestFullPipelineDELETE -v

# Expected: All previously failing UPDATE/DELETE tests now pass
```

---

## Phase 3: Error Recovery & Polish (Priority 3)

**This phase is lower priority - can be done after Phases 1 & 2 are complete and validated.**

Key improvements:
1. Better error messages with recovery suggestions
2. Retry logic for transient failures
3. Help system
4. Enhanced validation warnings

Implementation details in `docs/development/NL_COMPLETION_PLAN.md` (human-readable version).

---

## Success Criteria

**Phase 1 Complete When**:
- ✅ All confirmation workflow tests pass
- ✅ UPDATE operations require confirmation and handle "yes/no"
- ✅ DELETE operations require confirmation and handle "yes/no"
- ✅ Timeout handling works
- ✅ Cancellation works

**Phase 2 Complete When**:
- ✅ All StateManager task operation tests pass
- ✅ UPDATE task via NL command works
- ✅ DELETE task via NL command works
- ✅ Integration tests pass

**Overall Success**:
- ✅ 100% NL test suite passing (or 95%+ with documented skips)
- ✅ Zero breaking changes
- ✅ Documentation updated

---

## Quick Reference

**Test Everything**:
```bash
pytest tests/nl/ -v
```

**Test Specific Phase**:
```bash
# Phase 1
pytest tests/nl/test_confirmation_workflow.py -v

# Phase 2
pytest tests/test_state_manager_task_operations.py -v
pytest tests/nl/test_command_executor.py::TestExecuteUpdate -v
pytest tests/nl/test_command_executor.py::TestExecuteDelete -v
```

**Run Full Integration Tests**:
```bash
pytest tests/nl/test_integration_full_pipeline.py -v
```

---

## Common Pitfalls

1. **Don't forget to import** `time` module in `nl_command_processor.py`
2. **Use `with self._lock:` and `with self.transaction():`** in StateManager methods
3. **Follow TEST_GUIDELINES.md** - max 0.5s sleep, 5 threads per test
4. **Test both soft and hard delete** in Phase 2
5. **Update `list_tasks()` to filter `is_deleted=False`** if needed
6. **Remember to clear `pending_confirmation`** after timeout or execution
