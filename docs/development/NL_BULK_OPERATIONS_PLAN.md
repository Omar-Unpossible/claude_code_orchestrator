# Natural Language Bulk Operations Enhancement Plan

**Status**: Planning
**Created**: 2025-11-13
**Target Version**: v1.7.5
**Estimated Effort**: 13-18 hours (2-3 days)

## Problem Statement

The NL command processor cannot handle bulk/batch operations across multiple entity types. User request:

```
"delete all epics stories and tasks for this project"
```

**Current behavior**: Fails with `ValueError: delete operation requires an identifier`

**Root causes**:
1. Entity type classifier cannot handle multiple entity types in one command
2. Identifier extractor doesn't recognize "all" as a valid bulk identifier
3. OperationContext validation requires identifier for all delete operations
4. No bulk operation support in the entire NL pipeline

## Detailed Error Analysis

### NL Processing Pipeline Output

```
2025-11-13 15:55:03,974 - nl.intent_classifier - INFO - Classified as COMMAND with confidence 0.89
2025-11-13 15:55:06,819 - src.nl.operation_classifier - INFO - Classified operation: delete (confidence=0.63)
2025-11-13 15:55:10,638 - src.nl.entity_type_classifier - INFO - Classified entity type: project (confidence=0.80, operation=delete)
2025-11-13 15:55:13,620 - src.nl.entity_identifier_extractor - INFO - Extracted identifier: None (type=NoneType, confidence=0.00)
2025-11-13 15:55:18,640 - src.nl.parameter_extractor - INFO - Extracted parameters: {'DELETE': True, 'PROJECT': 'current'} (confidence=0.41)
```

### Analysis

| Stage | Expected | Actual | Status |
|-------|----------|--------|--------|
| Intent | COMMAND | COMMAND (0.89) | ✅ Correct |
| Operation | delete | delete (0.63) | ✅ Correct |
| Entity Type | [epic, story, task] | project (0.80) | ❌ Wrong |
| Identifier | "__ALL__" | None (0.00) | ❌ Missing |
| Parameters | {bulk: True, scope: current} | {DELETE: True, PROJECT: current} (0.41) | ⚠️ Partial |

### Exception Trace

```python
File "src/nl/types.py", line 151, in __post_init__
    raise ValueError(f"{self.operation.value} operation requires an identifier")
ValueError: delete operation requires an identifier
```

**Validation logic flaw**: Assumes all delete operations require an identifier, doesn't account for bulk operations.

## Solution Architecture

### Phase 1: Add Bulk Operation Support (Core Fix)

#### 1.1 Update OperationContext Validation
**File**: `src/nl/types.py:151`

**Current validation**:
```python
if self.operation in [Operation.DELETE, Operation.UPDATE, Operation.SHOW] and not self.identifier:
    raise ValueError(f"{self.operation.value} operation requires an identifier")
```

**New validation**:
```python
# Allow bulk operations without identifier
is_bulk = self.parameters and (
    self.parameters.get('bulk') is True or
    self.parameters.get('all') is True or
    self.identifier == "__ALL__"
)

if self.operation in [Operation.DELETE, Operation.UPDATE, Operation.SHOW]:
    if not self.identifier and not is_bulk:
        raise ValueError(
            f"{self.operation.value} operation requires an identifier or bulk flag. "
            f"Use 'all' to operate on all items."
        )
```

#### 1.2 Enhance EntityIdentifierExtractor
**File**: `src/nl/entity_identifier_extractor.py`

**Add bulk keyword detection**:
```python
BULK_KEYWORDS = ['all', 'every', 'each', 'entire']

def _detect_bulk_operation(self, user_input: str) -> bool:
    """Detect if user wants bulk operation."""
    tokens = user_input.lower().split()
    return any(keyword in tokens for keyword in self.BULK_KEYWORDS)

def extract(self, user_input: str, entity_type: EntityType, operation: Operation) -> tuple:
    # Check for bulk operation first
    if self._detect_bulk_operation(user_input):
        return ("__ALL__", 0.95)  # High confidence for explicit "all"

    # Existing identifier extraction logic...
```

#### 1.3 Add Multi-Entity Support
**File**: `src/nl/entity_type_classifier.py`

**Update to detect multiple entity types**:
```python
def classify(self, user_input: str, operation: Operation) -> tuple:
    """
    Returns: (entity_types: List[EntityType], confidence: float)
    """
    # Detect multiple entity types in input
    entity_keywords = {
        'epic': EntityType.EPIC,
        'story': EntityType.STORY,
        'task': EntityType.TASK,
        'subtask': EntityType.SUBTASK,
        'milestone': EntityType.MILESTONE,
        'project': EntityType.PROJECT
    }

    detected_types = []
    for keyword, entity_type in entity_keywords.items():
        if keyword in user_input.lower():
            detected_types.append(entity_type)

    if len(detected_types) > 1:
        return (detected_types, 0.85)  # High confidence for explicit mentions
    elif len(detected_types) == 1:
        return ([detected_types[0]], 0.90)
    else:
        # Fallback to LLM classification for single entity
        return self._llm_classify(user_input, operation)
```

**Update OperationContext dataclass**:
```python
@dataclass
class OperationContext:
    operation: Operation
    entity_types: List[EntityType]  # Changed from entity_type (singular)
    identifier: Optional[Union[int, str]]
    parameters: Optional[Dict[str, Any]] = None
    confidence: float = 0.0
```

### Phase 2: Update Command Execution Layer

#### 2.1 Enhance IntentToTaskConverter
**File**: `src/nl/intent_to_task_converter.py`

**Handle bulk operations**:
```python
def _convert_delete_operation(self, context: OperationContext, project_id: int) -> Task:
    if context.identifier == "__ALL__":
        # Bulk delete operation
        entity_list = ", ".join([et.value for et in context.entity_types])
        description = f"Delete all {entity_list} in project {project_id}"

        task_context = {
            'bulk_operation': True,
            'entity_types': [et.value for et in context.entity_types],
            'scope': 'current_project',
            'requires_confirmation': True
        }
    else:
        # Single delete operation (existing logic)
        description = f"Delete {context.entity_types[0].value} {context.identifier}"
        task_context = {'entity_id': context.identifier}

    return self.state_manager.create_task(
        project_id=project_id,
        title=description,
        description=description,
        context=task_context
    )
```

#### 2.2 Add BulkCommandExecutor
**New file**: `src/nl/bulk_command_executor.py`

```python
from typing import List, Dict, Any
from src.state.state_manager import StateManager
from src.nl.types import EntityType

class BulkCommandExecutor:
    """Executes bulk operations with transaction safety."""

    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager

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
        """
        # Get counts before deletion (for confirmation/reporting)
        counts = self._get_entity_counts(project_id, entity_types)

        if require_confirmation:
            if not self._confirm_bulk_delete(counts):
                return {'cancelled': True}

        # Execute deletions in dependency order (tasks → stories → epics)
        ordered_types = self._order_by_dependencies(entity_types)
        results = {}

        try:
            for entity_type in ordered_types:
                deleted = self._delete_all_of_type(project_id, entity_type)
                results[entity_type.value] = deleted
        except Exception as e:
            # Rollback handled by StateManager transaction
            raise BulkOperationException(
                f"Bulk delete failed at {entity_type.value}: {e}",
                partial_results=results
            )

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
        dependency_order = [
            EntityType.SUBTASK,
            EntityType.TASK,
            EntityType.STORY,
            EntityType.EPIC
        ]
        return [et for et in dependency_order if et in entity_types]

    def _get_entity_counts(self, project_id: int, entity_types: List[EntityType]) -> Dict[str, int]:
        """Get count of entities before deletion."""
        counts = {}
        for entity_type in entity_types:
            if entity_type == EntityType.TASK:
                counts['tasks'] = len(self.state_manager.list_tasks(project_id))
            elif entity_type == EntityType.STORY:
                counts['stories'] = len(self.state_manager.list_stories(project_id))
            elif entity_type == EntityType.EPIC:
                counts['epics'] = len(self.state_manager.list_epics(project_id))
        return counts

    def _confirm_bulk_delete(self, counts: Dict[str, int]) -> bool:
        """Prompt user to confirm bulk delete."""
        items = ", ".join([f"{count} {name}" for name, count in counts.items()])
        response = input(f"\n⚠️  Delete {items}? This cannot be undone. (yes/no): ")
        return response.lower() in ['yes', 'y']
```

#### 2.3 Update StateManager
**File**: `src/state/state_manager.py`

**Add bulk delete methods**:
```python
def delete_all_tasks(self, project_id: int) -> int:
    """Delete all tasks in project. Returns count deleted."""
    with self.transaction():
        tasks = self.session.query(Task).filter_by(project_id=project_id).all()
        count = len(tasks)
        for task in tasks:
            self.session.delete(task)
        return count

def delete_all_stories(self, project_id: int) -> int:
    """Delete all stories in project (cascade to tasks). Returns count deleted."""
    with self.transaction():
        stories = self.session.query(Task).filter_by(
            project_id=project_id,
            task_type=TaskType.STORY
        ).all()
        count = len(stories)

        # Delete child tasks first
        for story in stories:
            child_tasks = self.session.query(Task).filter_by(story_id=story.id).all()
            for task in child_tasks:
                self.session.delete(task)

        # Delete stories
        for story in stories:
            self.session.delete(story)

        return count

def delete_all_epics(self, project_id: int) -> int:
    """Delete all epics in project (cascade to stories/tasks). Returns count deleted."""
    with self.transaction():
        epics = self.session.query(Task).filter_by(
            project_id=project_id,
            task_type=TaskType.EPIC
        ).all()
        count = len(epics)

        # Delete child stories and their tasks first
        for epic in epics:
            stories = self.session.query(Task).filter_by(epic_id=epic.id).all()
            for story in stories:
                child_tasks = self.session.query(Task).filter_by(story_id=story.id).all()
                for task in child_tasks:
                    self.session.delete(task)
                self.session.delete(story)

        # Delete epics
        for epic in epics:
            self.session.delete(epic)

        return count

def delete_all_subtasks(self, project_id: int) -> int:
    """Delete all subtasks in project. Returns count deleted."""
    with self.transaction():
        subtasks = self.session.query(Task).filter_by(
            project_id=project_id,
            task_type=TaskType.SUBTASK
        ).all()
        count = len(subtasks)
        for subtask in subtasks:
            self.session.delete(subtask)
        return count
```

### Phase 3: Improve Parameter Extraction

#### 3.1 Enhance ParameterExtractor
**File**: `src/nl/parameter_extractor.py`

**Add bulk and scope detection**:
```python
def extract(self, user_input: str, operation: Operation, entity_type: EntityType) -> tuple:
    parameters = {}

    # Detect bulk operation
    if any(keyword in user_input.lower() for keyword in ['all', 'every', 'each', 'entire']):
        parameters['bulk'] = True
        parameters['all'] = True

    # Detect scope
    if 'this project' in user_input.lower() or 'current project' in user_input.lower():
        parameters['scope'] = 'current_project'
    elif 'all projects' in user_input.lower():
        parameters['scope'] = 'all_projects'

    # Existing parameter extraction logic...

    confidence = self._calculate_confidence(parameters, user_input)
    return (parameters, confidence)
```

### Phase 4: Safety & UX Improvements

#### 4.1 Confirmation Prompts
Implemented in `BulkCommandExecutor._confirm_bulk_delete()` (see Phase 2.2)

#### 4.2 Soft Delete (Future Enhancement)
**Optional**: Add soft-delete capability with 24-hour recovery window
- Add `deleted_at` timestamp to Task model
- Add `restore_deleted_items()` method
- Add cron job to purge soft-deleted items after 24 hours

#### 4.3 Improved Error Messages
Update validation messages throughout NL pipeline:
- `OperationContext`: Better error message (see Phase 1.1)
- `EntityIdentifierExtractor`: Suggest "all" keyword when identifier missing
- `BulkCommandExecutor`: Clear error messages with partial results on failure

### Phase 5: Testing

#### 5.1 Unit Tests (15 new tests)

**File**: `tests/nl/test_bulk_operations.py`

```python
def test_bulk_identifier_extraction():
    """Test 'all' keyword detection."""
    extractor = EntityIdentifierExtractor(llm_interface)

    identifier, conf = extractor.extract("delete all tasks", EntityType.TASK, Operation.DELETE)
    assert identifier == "__ALL__"
    assert conf > 0.9

def test_multi_entity_type_classification():
    """Test multiple entity type detection."""
    classifier = EntityTypeClassifier(llm_interface)

    types, conf = classifier.classify("delete epics stories and tasks", Operation.DELETE)
    assert len(types) == 3
    assert EntityType.EPIC in types
    assert EntityType.STORY in types
    assert EntityType.TASK in types

def test_operation_context_bulk_validation():
    """Test OperationContext accepts bulk operations."""
    context = OperationContext(
        operation=Operation.DELETE,
        entity_types=[EntityType.TASK],
        identifier="__ALL__",
        parameters={'bulk': True},
        confidence=0.9
    )
    # Should not raise ValueError

def test_bulk_executor_dependency_ordering():
    """Test entities deleted in correct order."""
    executor = BulkCommandExecutor(state_manager)

    entity_types = [EntityType.EPIC, EntityType.TASK, EntityType.STORY]
    ordered = executor._order_by_dependencies(entity_types)

    assert ordered == [EntityType.TASK, EntityType.STORY, EntityType.EPIC]
```

#### 5.2 Integration Tests (5 new tests)

**File**: `tests/integration/test_bulk_delete_e2e.py`

```python
def test_bulk_delete_all_tasks():
    """End-to-end: delete all tasks in project."""
    # Setup: create 5 tasks
    for i in range(5):
        state.create_task(project_id=1, title=f"Task {i}")

    # Execute: "delete all tasks"
    processor = NLCommandProcessor(llm_interface, state)
    result = processor.process("delete all tasks", project_id=1)

    # Verify: all tasks deleted
    remaining = state.list_tasks(project_id=1)
    assert len(remaining) == 0

def test_bulk_delete_cascade():
    """Test epic deletion cascades to stories and tasks."""
    # Setup: create epic → story → task
    epic = state.create_epic(1, "Epic 1", "Desc")
    story = state.create_story(1, epic, "Story 1", "Desc")
    task = state.create_task(1, "Task 1", story_id=story)

    # Execute: delete all epics
    executor = BulkCommandExecutor(state)
    result = executor.execute_bulk_delete(1, [EntityType.EPIC], require_confirmation=False)

    # Verify: epic, story, and task all deleted
    assert state.get_task(epic) is None
    assert state.get_task(story) is None
    assert state.get_task(task) is None
```

#### 5.3 Real-World Validation
- Test with actual Obra database
- Verify cascade delete doesn't break dependencies
- Verify confirmation prompts work in interactive mode

## Implementation Order

1. **Phase 1.2** (EntityIdentifierExtractor) - 1 hour
2. **Phase 1.1** (OperationContext validation) - 1 hour
3. **Phase 2.2** (BulkCommandExecutor) - 3 hours
4. **Phase 1.3** (Multi-entity support) - 2 hours
5. **Phase 2.3** (StateManager bulk methods) - 2 hours
6. **Phase 2.1** (IntentToTaskConverter) - 1 hour
7. **Phase 3.1** (ParameterExtractor) - 1 hour
8. **Phase 4** (Safety/UX) - 2 hours
9. **Phase 5** (Testing) - 4 hours

**Total**: 17 hours

## Open Questions

1. **Cascade delete behavior**: Should deleting an epic automatically delete its stories and tasks?
   - **Recommendation**: Yes, with confirmation prompt showing cascade impact

2. **Soft delete vs hard delete**: Should bulk deletes be recoverable?
   - **Recommendation**: Phase 2 - Hard delete with confirmation. Phase 3 (future) - Add soft delete

3. **Confirmation prompt**: CLI interactive prompt or require `--force` flag?
   - **Recommendation**: Interactive prompt (better UX)

4. **Scope**: Should "all" mean "all in current project" or "all in database"?
   - **Recommendation**: Current project by default, require `--all-projects` flag for global

## Success Criteria

- ✅ User can execute: "delete all epics stories and tasks" without error
- ✅ Multi-entity type detection: 3+ entity types in one command
- ✅ Bulk identifier detection: "all" keyword recognized with >0.9 confidence
- ✅ Transaction safety: Partial failures rollback cleanly
- ✅ Confirmation prompt: User confirms before destructive operation
- ✅ Test coverage: ≥90% for new components
- ✅ Integration tests: 5+ end-to-end scenarios passing
- ✅ Real-world validation: Works with actual Obra database

## Related Documents

- ADR-014: Natural Language Command Interface
- ADR-017: Unified Execution Architecture
- docs/guides/NL_COMMAND_GUIDE.md
- src/nl/types.py (OperationContext, ParsedIntent)
- src/nl/nl_command_processor.py (4-stage pipeline)

## Version History

- **2025-11-13**: Initial plan created
