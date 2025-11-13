# Natural Language Command System Completion Plan

**Document Type**: Implementation Plan
**Status**: Ready for Implementation
**Estimated Effort**: 5-7 days
**Target Version**: v1.6.2
**Created**: 2025-11-12
**Starting Point**: Commit `5b514d6` (v1.6.1-pre-nl-redesign)

---

## Executive Summary

This plan completes the natural language command system by implementing missing features rather than redesigning the architecture. The current ADR-016 system is 92% functional (233/253 tests passing) with well-defined bugs and missing features.

**Current State:**
- ✅ CREATE operations: Fully working
- ✅ QUERY operations: Fully working
- ⚠️ UPDATE operations: Needs confirmation workflow
- ⚠️ DELETE operations: Needs confirmation workflow
- ⚠️ Task mutations: Need StateManager API support

**Target State:**
- ✅ All CRUD operations working
- ✅ Interactive confirmation workflow
- ✅ 100% test coverage for NL pipeline
- ✅ Production-ready error handling
- ✅ Complete documentation

---

## Phase 1: Interactive Confirmation Workflow

**Effort**: 2 days
**Priority**: Critical
**Dependencies**: None

### Problem Statement

Currently, UPDATE and DELETE operations require confirmation, but the system doesn't handle user responses:
```
User: delete project #3
System: ⚠ Confirmation required: This will delete project #3.
User: yes
System: ? I'm not sure what you'd like to do...  [ERROR]
```

The confirmation prompt is shown, but "yes/no" responses are treated as new commands that fail intent classification.

### Solution Design

Implement a **confirmation state machine** in `NLCommandProcessor`:

```python
class NLCommandProcessor:
    def __init__(self, ...):
        # Add confirmation state tracking
        self.pending_confirmation: Optional[PendingOperation] = None
        self.confirmation_timeout = 60  # seconds
        self.confirmation_timestamp: Optional[float] = None

    def process(self, message: str, ...) -> NLResponse:
        # Check if this is a confirmation response
        if self.pending_confirmation:
            if self._is_confirmation_response(message):
                return self._handle_confirmation_response(message, ...)
            elif self._is_cancellation_response(message):
                return self._handle_cancellation()
            # Else: treat as new command (implicit cancellation)

        # Normal command processing...
```

### Implementation Tasks

#### Task 1.1: Add Confirmation State Tracking
**File**: `src/nl/nl_command_processor.py`

Add state tracking fields:
```python
@dataclass
class PendingOperation:
    """Pending operation awaiting confirmation."""
    context: OperationContext
    project_id: int
    timestamp: float
    original_message: str
```

Add to `NLCommandProcessor.__init__()`:
```python
self.pending_confirmation: Optional[PendingOperation] = None
self.confirmation_timeout = config.get('nl_commands.confirmation_timeout', 60)
```

#### Task 1.2: Implement Confirmation Detection
**File**: `src/nl/nl_command_processor.py`

```python
def _is_confirmation_response(self, message: str) -> bool:
    """Check if message is a confirmation response.

    Accepts: yes, y, confirm, ok, proceed, go ahead
    """
    confirmation_keywords = {'yes', 'y', 'confirm', 'ok', 'proceed', 'go ahead'}
    normalized = message.strip().lower()
    return normalized in confirmation_keywords

def _is_cancellation_response(self, message: str) -> bool:
    """Check if message is a cancellation response.

    Accepts: no, n, cancel, abort, stop, nevermind
    """
    cancellation_keywords = {'no', 'n', 'cancel', 'abort', 'stop', 'nevermind'}
    normalized = message.strip().lower()
    return normalized in cancellation_keywords
```

#### Task 1.3: Handle Confirmation Responses
**File**: `src/nl/nl_command_processor.py`

```python
def _handle_confirmation_response(
    self,
    message: str,
    project_id: Optional[int] = None
) -> NLResponse:
    """Execute pending operation after confirmation."""

    # Check timeout
    if time.time() - self.pending_confirmation.timestamp > self.confirmation_timeout:
        self.pending_confirmation = None
        return NLResponse(
            response=f"{Fore.YELLOW}Confirmation timeout. Please try again.{Style.RESET_ALL}",
            intent='ERROR',
            success=False
        )

    # Execute with confirmation
    execution_result = self.command_executor.execute(
        self.pending_confirmation.context,
        project_id=self.pending_confirmation.project_id,
        confirmed=True
    )

    # Clear pending state
    self.pending_confirmation = None

    # Format response
    response = self.response_formatter.format(
        execution_result,
        intent='COMMAND',
        operation=self.pending_confirmation.context.operation.value
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

#### Task 1.4: Store Pending Operation on Confirmation Required
**File**: `src/nl/nl_command_processor.py`

In `_handle_command()` method, modify confirmation handling:

```python
# After execution_result = self.command_executor.execute(...)
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

#### Task 1.5: Update Response Formatter
**File**: `src/nl/response_formatter.py`

Improve confirmation message with clearer instructions:

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

#### Task 1.6: Add Tests
**File**: `tests/nl/test_confirmation_workflow.py` (new file)

```python
class TestConfirmationWorkflow:
    def test_update_requires_confirmation(self):
        """Test that UPDATE operations require confirmation."""

    def test_delete_requires_confirmation(self):
        """Test that DELETE operations require confirmation."""

    def test_confirmation_yes_executes(self):
        """Test that 'yes' executes pending operation."""

    def test_confirmation_no_cancels(self):
        """Test that 'no' cancels pending operation."""

    def test_confirmation_timeout(self):
        """Test that confirmations timeout after N seconds."""

    def test_new_command_cancels_pending(self):
        """Test that new command implicitly cancels pending confirmation."""

    def test_multiple_confirmation_variations(self):
        """Test various confirmation words: yes, y, ok, confirm, etc."""
```

### Testing Checklist

- [ ] Confirmation prompt shows for UPDATE operations
- [ ] Confirmation prompt shows for DELETE operations
- [ ] "yes" executes the pending operation
- [ ] "no" cancels the pending operation
- [ ] Timeout after 60 seconds
- [ ] New command implicitly cancels pending confirmation
- [ ] All confirmation keyword variations work (yes, y, ok, confirm)
- [ ] All cancellation keyword variations work (no, n, cancel, abort)

### Documentation Updates

- [ ] Update `docs/guides/NL_COMMAND_GUIDE.md` with confirmation workflow
- [ ] Update `CHANGELOG.md` with new feature
- [ ] Add confirmation workflow diagram to architecture docs

---

## Phase 2: StateManager API Extensions

**Effort**: 2 days
**Priority**: High
**Dependencies**: None

### Problem Statement

Task-level UPDATE and DELETE operations fail because StateManager lacks these methods:
- `update_task(task_id, updates)` - Only `update_task_status()` exists
- `delete_task(task_id)` - No method exists

### Solution Design

Add missing StateManager methods following existing patterns:

```python
class StateManager:
    def update_task(
        self,
        task_id: int,
        updates: Dict[str, Any]
    ) -> Task:
        """Update task fields.

        Args:
            task_id: Task ID
            updates: Dictionary of fields to update
                - title: New title
                - description: New description
                - priority: New priority (1-10)
                - status: New status (TaskStatus enum)
                - dependencies: New dependencies list

        Returns:
            Updated Task object
        """

    def delete_task(
        self,
        task_id: int,
        soft: bool = True
    ) -> None:
        """Delete task (soft or hard delete).

        Args:
            task_id: Task ID to delete
            soft: If True, mark as deleted (default). If False, hard delete.
        """
```

### Implementation Tasks

#### Task 2.1: Add `update_task()` Method
**File**: `src/core/state.py`

```python
def update_task(
    self,
    task_id: int,
    updates: Dict[str, Any]
) -> Task:
    """Update task fields.

    Args:
        task_id: Task ID
        updates: Dictionary of fields to update

    Returns:
        Updated Task object

    Raises:
        DatabaseException: If update fails
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

                logger.info(f"Updated task {task_id}: {updates}")
                return task

        except SQLAlchemyError as e:
            raise DatabaseException(
                operation='update_task',
                details=str(e)
            ) from e
```

#### Task 2.2: Add `delete_task()` Method
**File**: `src/core/state.py`

```python
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

#### Task 2.3: Update CommandExecutor to Use New Methods
**File**: `src/nl/command_executor.py`

Replace manual field updates with `StateManager.update_task()`:

```python
def _update_entity(self, context: OperationContext, entity_id: int, project_id: int):
    """Update entity via StateManager."""
    params = context.parameters

    if context.entity_type == EntityType.PROJECT:
        # ... existing project update logic ...

    else:  # EPIC, STORY, TASK, SUBTASK
        # Build updates dict
        updates = {}

        if 'status' in params:
            status_map = {...}
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

Replace exception-throwing delete with actual deletion:

```python
def _delete_entity(self, context: OperationContext, entity_id: int, project_id: int):
    """Delete entity via StateManager."""
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

#### Task 2.4: Add Tests
**File**: `tests/test_state_manager_task_operations.py` (new file)

```python
class TestTaskUpdate:
    def test_update_task_title(self):
        """Test updating task title."""

    def test_update_task_priority(self):
        """Test updating task priority."""

    def test_update_task_status(self):
        """Test updating task status."""

    def test_update_task_multiple_fields(self):
        """Test updating multiple task fields."""

    def test_update_nonexistent_task(self):
        """Test that updating nonexistent task raises exception."""

    def test_update_task_invalid_field(self):
        """Test that invalid fields are ignored."""

class TestTaskDelete:
    def test_soft_delete_task(self):
        """Test soft deleting a task."""

    def test_hard_delete_task(self):
        """Test hard deleting a task."""

    def test_delete_nonexistent_task(self):
        """Test that deleting nonexistent task raises exception."""

    def test_soft_deleted_task_not_in_queries(self):
        """Test that soft deleted tasks don't appear in list_tasks()."""
```

Update existing NL tests to expect success instead of errors:

**File**: `tests/nl/test_integration_full_pipeline.py`

```python
# Remove "confirmed=True" workarounds - they should now be required
def test_update_task_by_id(self):
    # ... existing test setup ...

    # Should require confirmation
    result = executor.execute(context)
    assert result.confirmation_required

    # Confirm and execute
    result = executor.execute(context, confirmed=True)
    assert result.success

    # Verify task was updated
    task = state.get_task(4)
    assert task.priority == 3  # HIGH
```

### Testing Checklist

- [ ] `update_task()` updates title successfully
- [ ] `update_task()` updates priority successfully
- [ ] `update_task()` updates status successfully
- [ ] `update_task()` updates multiple fields
- [ ] `update_task()` raises exception for nonexistent task
- [ ] `delete_task(soft=True)` marks task as deleted
- [ ] `delete_task(soft=False)` removes task from database
- [ ] Soft deleted tasks don't appear in `list_tasks()`
- [ ] NL UPDATE commands work end-to-end
- [ ] NL DELETE commands work end-to-end

### Documentation Updates

- [ ] Add `update_task()` to StateManager API docs
- [ ] Add `delete_task()` to StateManager API docs
- [ ] Update NL command examples to show UPDATE/DELETE
- [ ] Update CHANGELOG.md

---

## Phase 3: Error Recovery & Polish

**Effort**: 1-2 days
**Priority**: Medium
**Dependencies**: Phase 1 and 2

### Problem Statement

Current error messages are unclear and don't provide actionable recovery suggestions. Users need better guidance when commands fail.

### Solution Design

Implement comprehensive error handling with:
1. **Descriptive error messages** - Explain what went wrong
2. **Recovery suggestions** - Tell user how to fix it
3. **Retry logic** - Automatic retry for transient failures
4. **Validation improvements** - Better pre-execution checks

### Implementation Tasks

#### Task 3.1: Improve Error Messages
**File**: `src/nl/response_formatter.py`

Enhance `_suggest_recovery()` with more specific guidance:

```python
def _suggest_recovery(self, error_msg: str, results: Dict[str, Any]) -> str:
    """Suggest recovery action for error."""
    error_lower = error_msg.lower()

    # Entity not found
    if 'not found' in error_lower:
        entity_type = results.get('entity_type', 'item')
        return f"List {entity_type}s with 'list {entity_type}s' to see available options"

    # Missing required field
    if 'requires' in error_lower:
        if 'epic_id' in error_lower:
            return "Specify epic with 'in epic <id>' or 'for epic <name>'"
        elif 'story_id' in error_lower:
            return "Specify story with 'in story <id>' or 'for story <name>'"
        elif 'parent_task_id' in error_lower:
            return "Specify parent task with 'under task <id>'"
        return "Check required fields and try again"

    # Circular dependency
    if 'circular' in error_lower:
        return "Remove the circular dependency: task A depends on B, B depends on A"

    # Confirmation required
    if 'confirmation' in error_lower:
        return "This should not happen - confirmation should be prompted"

    # Database/connection errors
    if 'database' in error_lower or 'connection' in error_lower:
        return "Database connection issue. Check logs and try again."

    # Permission/access errors
    if 'permission' in error_lower or 'access' in error_lower:
        return "Check file permissions and working directory access"

    # Invalid parameter values
    if 'invalid' in error_lower:
        if 'priority' in error_lower:
            return "Priority must be 1-10 or HIGH/MEDIUM/LOW"
        if 'status' in error_lower:
            return "Status must be PENDING/RUNNING/COMPLETED/BLOCKED"
        return "Check parameter values and try again"

    # Generic recovery
    return "Try rephrasing your command or use 'help' for examples"
```

Add example-based error suggestions:

```python
def format_error_with_examples(
    self,
    error_msg: str,
    entity_type: str,
    operation: str
) -> str:
    """Format error with command examples."""
    base_error = self._format_error(...)

    examples = self._get_examples(entity_type, operation)
    if examples:
        base_error += f"\n\n{Fore.CYAN}Examples:{Style.RESET_ALL}"
        for example in examples:
            base_error += f"\n  • {example}"

    return base_error

def _get_examples(self, entity_type: str, operation: str) -> List[str]:
    """Get example commands for entity type and operation."""
    examples_map = {
        ('project', 'create'): [
            "create project 'My New Project'",
            "create project for mobile app",
        ],
        ('project', 'update'): [
            "update project 5 status to completed",
            "mark project 'Mobile App' as inactive",
        ],
        ('epic', 'create'): [
            "create epic for user authentication",
            "add epic 'Payment System' to project 1",
        ],
        # ... more examples
    }
    return examples_map.get((entity_type, operation), [])
```

#### Task 3.2: Add Retry Logic for Transient Failures
**File**: `src/nl/nl_command_processor.py`

Add retry wrapper for execution:

```python
def _execute_with_retry(
    self,
    operation_context: OperationContext,
    project_id: int,
    confirmed: bool = False,
    max_retries: int = 3
) -> ExecutionResult:
    """Execute command with automatic retry for transient failures."""

    retryable_errors = [
        'timeout',
        'connection',
        'temporary',
        'lock',
    ]

    for attempt in range(max_retries):
        try:
            result = self.command_executor.execute(
                operation_context,
                project_id=project_id,
                confirmed=confirmed
            )

            # Success or non-retryable failure
            if result.success or not self._is_retryable(result, retryable_errors):
                return result

            # Wait before retry (exponential backoff)
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # 1s, 2s, 4s
                time.sleep(wait_time)
                logger.info(f"Retrying command (attempt {attempt + 2}/{max_retries})")

        except Exception as e:
            if attempt == max_retries - 1:
                raise
            logger.warning(f"Attempt {attempt + 1} failed: {e}")

    return result

def _is_retryable(self, result: ExecutionResult, retryable_keywords: List[str]) -> bool:
    """Check if error is retryable based on error message."""
    if not result.errors:
        return False

    error_msg = result.errors[0].lower()
    return any(keyword in error_msg for keyword in retryable_keywords)
```

#### Task 3.3: Enhanced Validation
**File**: `src/nl/command_validator.py`

Add pre-validation for common issues:

```python
def validate(self, context: OperationContext) -> ValidationResult:
    """Enhanced validation with detailed feedback."""

    errors = []
    warnings = []

    # Existing validation...

    # Additional checks

    # Check for common mistakes
    if context.operation == OperationType.CREATE:
        if context.entity_type == EntityType.STORY and not context.parameters.get('epic_id'):
            warnings.append(
                "Stories typically belong to an epic. "
                "Use 'in epic <id>' to specify one."
            )

    # Check for potentially destructive operations
    if context.operation == OperationType.DELETE:
        entity_name = self._get_entity_name(context)
        if entity_name:
            warnings.append(
                f"This will permanently delete {context.entity_type.value} '{entity_name}'"
            )

    # Check for ambiguous identifiers
    if isinstance(context.identifier, str) and len(context.identifier) < 3:
        warnings.append(
            "Short identifier may be ambiguous. "
            "Consider using ID number for clarity."
        )

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        validated_command=self._build_validated_command(context)
    )
```

#### Task 3.4: Add Help System
**File**: `src/nl/nl_command_processor.py`

Add help command handling:

```python
def process(self, message: str, ...) -> NLResponse:
    """Process natural language message."""

    # Check for help request
    if message.lower().strip() in ['help', '?', 'help me']:
        return self._show_help()

    # Check for entity-specific help
    if message.lower().startswith('help '):
        entity_type = message.lower().split()[1]
        return self._show_entity_help(entity_type)

    # ... normal processing ...

def _show_help(self) -> NLResponse:
    """Show general help message."""
    help_text = f"""
{Fore.CYAN}Obra Natural Language Commands{Style.RESET_ALL}

{Fore.YELLOW}Creating:{Style.RESET_ALL}
  • create project 'name'
  • create epic for [description]
  • create story in epic <id>
  • create task with priority HIGH

{Fore.YELLOW}Querying:{Style.RESET_ALL}
  • list projects
  • show all epics
  • list tasks for story 5
  • show project status

{Fore.YELLOW}Updating:{Style.RESET_ALL}
  • update project 5 status to completed
  • change task 3 priority to LOW
  • mark epic 2 as blocked

{Fore.YELLOW}Deleting:{Style.RESET_ALL}
  • delete project 3
  • remove task 7

Type 'help <entity>' for more: help project, help epic, help task
"""
    return NLResponse(
        response=help_text,
        intent='HELP',
        success=True
    )
```

#### Task 3.5: Add Tests
**File**: `tests/nl/test_error_recovery.py` (new file)

```python
class TestErrorRecovery:
    def test_retry_transient_failure(self):
        """Test automatic retry for transient failures."""

    def test_no_retry_permanent_failure(self):
        """Test that permanent failures are not retried."""

    def test_exponential_backoff(self):
        """Test that retry uses exponential backoff."""

    def test_max_retries_respected(self):
        """Test that max retries limit is respected."""

class TestErrorMessages:
    def test_entity_not_found_error(self):
        """Test error message for entity not found."""

    def test_missing_required_field_error(self):
        """Test error message for missing required field."""

    def test_circular_dependency_error(self):
        """Test error message for circular dependency."""

class TestHelpSystem:
    def test_general_help(self):
        """Test general help command."""

    def test_entity_specific_help(self):
        """Test entity-specific help (help project, help epic, etc.)."""
```

### Testing Checklist

- [ ] Error messages include recovery suggestions
- [ ] Examples shown for common command types
- [ ] Retry logic works for transient failures
- [ ] No retry for permanent failures
- [ ] Help command shows general usage
- [ ] Entity-specific help works
- [ ] Warnings shown for potentially destructive operations
- [ ] Validation catches common mistakes

### Documentation Updates

- [ ] Update `docs/guides/NL_COMMAND_GUIDE.md` with help system
- [ ] Add troubleshooting section to documentation
- [ ] Document error codes and recovery suggestions
- [ ] Update CHANGELOG.md

---

## Integration Testing

After all phases complete, run comprehensive integration tests:

### End-to-End Scenarios

**Scenario 1: Full Project Lifecycle**
```python
def test_full_project_lifecycle():
    """Test complete project lifecycle via NL commands."""
    processor = NLCommandProcessor(...)

    # Create project
    response = processor.process("create project 'Test Project'")
    assert response.success
    project_id = response.created_ids[0]

    # Create epic
    response = processor.process("create epic for authentication")
    assert response.success
    epic_id = response.created_ids[0]

    # Create story
    response = processor.process(f"create story in epic {epic_id}")
    assert response.success

    # Update project
    response = processor.process(f"update project {project_id} status to completed")
    # Should require confirmation
    assert response.intent == 'CONFIRMATION'

    # Confirm
    response = processor.process("yes")
    assert response.success

    # Verify update
    project = state.get_project(project_id)
    assert project.status == ProjectStatus.COMPLETED
```

**Scenario 2: Error Recovery**
```python
def test_error_recovery_scenario():
    """Test error recovery with helpful messages."""
    processor = NLCommandProcessor(...)

    # Try to create story without epic
    response = processor.process("create story for login feature")
    assert not response.success
    assert "epic" in response.response.lower()
    assert "specify epic" in response.response.lower()
```

**Scenario 3: Confirmation Workflow**
```python
def test_confirmation_workflow():
    """Test full confirmation workflow."""
    processor = NLCommandProcessor(...)

    # Create project
    response = processor.process("create project 'Temp'")
    project_id = response.created_ids[0]

    # Attempt delete - requires confirmation
    response = processor.process(f"delete project {project_id}")
    assert response.intent == 'CONFIRMATION'
    assert "delete" in response.response.lower()
    assert "yes" in response.response.lower()

    # Confirm
    response = processor.process("yes")
    assert response.success

    # Verify deletion
    project = state.get_project(project_id)
    assert project is None or project.is_deleted
```

### Performance Testing

**Latency Targets:**
- Simple commands (list, show): < 100ms
- Create operations: < 300ms
- Update/Delete with confirmation: < 500ms (excluding LLM classification time)

**Throughput Targets:**
- 10+ commands per second (without LLM bottleneck)

### Compatibility Testing

- [ ] All existing CLI commands still work
- [ ] Interactive mode works with new confirmation flow
- [ ] Orchestrator integration unaffected
- [ ] Database migrations not required

---

## Rollout Plan

### Version Tagging
- Current: `v1.6.1-pre-nl-redesign`
- Target: `v1.6.2-nl-complete`

### Deployment Steps

1. **Create feature branch**: `feature/nl-completion`
2. **Implement Phase 1** (confirmation workflow)
3. **Test and validate Phase 1**
4. **Implement Phase 2** (StateManager extensions)
5. **Test and validate Phase 2**
6. **Implement Phase 3** (error recovery)
7. **Run full integration test suite**
8. **Update documentation**
9. **Merge to main with tag `v1.6.2-nl-complete`**
10. **Deploy to production**

### Success Criteria

- ✅ 100% NL test suite passing
- ✅ All CRUD operations working via NL
- ✅ Confirmation workflow functioning
- ✅ Error messages clear and helpful
- ✅ Documentation complete
- ✅ Performance targets met
- ✅ Zero breaking changes to existing code

---

## Risk Mitigation

### Risk 1: Confirmation Timeout Issues
**Mitigation**: Make timeout configurable, default to 60 seconds
**Fallback**: Allow users to re-issue command instead of confirmation

### Risk 2: StateManager API Complexity
**Mitigation**: Follow existing patterns closely, comprehensive testing
**Fallback**: Keep existing `update_task_status()` as primary method

### Risk 3: Breaking Changes
**Mitigation**: Comprehensive compatibility testing
**Fallback**: Feature flag to disable confirmation workflow

### Risk 4: Performance Regression
**Mitigation**: Benchmark before/after, optimize hot paths
**Fallback**: Cache responses, optimize database queries

---

## Post-Completion

After successful deployment:

1. **Monitor production usage** for 2 weeks
2. **Gather user feedback** on confirmation UX
3. **Iterate on error messages** based on real errors
4. **Consider enhancements**:
   - Bulk operations ("delete all completed tasks")
   - Command aliases ("rm" = "delete")
   - Smart suggestions based on context
   - Multi-turn conversations

---

## References

- ADR-016: Natural Language Command Pipeline
- StateManager API Documentation
- Test Guidelines (WSL2 resource limits)
- NL Command Guide (user documentation)
