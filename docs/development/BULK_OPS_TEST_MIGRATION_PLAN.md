# Bulk Operations Test Migration Plan

**Version:** 1.0
**Date:** 2025-11-13
**Status:** In Progress
**Estimated Effort:** 2-3 hours

---

## Overview

The bulk operations implementation (v1.7.5) introduced a **breaking API change** to `EntityTypeClassifier.classify()` to support multi-entity bulk operations. This requires updating 29+ existing tests.

### API Change Summary

**Old API (v1.7.4 and earlier):**
```python
def classify(self, user_input: str, operation: OperationType) -> EntityTypeResult:
    """Returns EntityTypeResult object."""
    pass

# Usage
result = classifier.classify("create epic for auth", OperationType.CREATE)
assert result.entity_type == EntityType.EPIC
assert result.confidence > 0.7
```

**New API (v1.7.5):**
```python
def classify(self, user_input: str, operation: OperationType) -> tuple:
    """Returns (entity_types: List[EntityType], confidence: float)."""
    pass

# Usage
entity_types, confidence = classifier.classify("create epic for auth", OperationType.CREATE)
assert entity_types[0] == EntityType.EPIC
assert confidence > 0.7
```

### Why This Change?

**Problem Solved:**
- Commands like `"delete all epics stories and tasks"` require detecting **multiple entity types**
- Old API could only return one `EntityType` at a time
- Bulk operations need to know all target entity types upfront

**Benefits:**
- ✅ Multi-entity bulk operations work correctly
- ✅ Better separation of concerns (classifier returns raw data, not domain object)
- ✅ More flexible for future enhancements

---

## Affected Tests

### Test Breakdown (from pytest output)

**File: `tests/nl/test_entity_type_classifier.py`**
- **Total Failing:** 27 tests
- **Categories:**
  - PROJECT classification: 5 tests
  - EPIC classification: 5 tests
  - STORY classification: 5 tests
  - TASK classification: 5 tests
  - MILESTONE classification: 5 tests
  - Edge cases: 2 tests

**File: `tests/nl/test_nl_performance.py`**
- **Total Failing:** 1 test
- **Issue:** `OperationContext` initialization using old `entity_type` parameter

**File: `tests/nl/test_performance_benchmarks.py`**
- **Total Failing:** 1 test
- **Issue:** Expects `EntityTypeResult` object

**Total Tests to Update:** 29 tests

---

## Migration Strategy

### Phase 1: Update Entity Type Classifier Tests (Priority: HIGH)

**File:** `tests/nl/test_entity_type_classifier.py`

**Pattern 1: Simple Classification Tests**

❌ **Before:**
```python
def test_epic_create_explicit(self, classifier):
    """Test explicit 'epic' mention."""
    result = classifier.classify(
        "create epic for user authentication",
        operation=OperationType.CREATE
    )

    assert result.entity_type == EntityType.EPIC
    assert result.confidence >= 0.7
```

✅ **After:**
```python
def test_epic_create_explicit(self, classifier):
    """Test explicit 'epic' mention."""
    entity_types, confidence = classifier.classify(
        "create epic for user authentication",
        operation=OperationType.CREATE
    )

    # Single entity type expected
    assert len(entity_types) == 1
    assert entity_types[0] == EntityType.EPIC
    assert confidence >= 0.7
```

**Pattern 2: Edge Case Tests**

❌ **Before:**
```python
def test_llm_failure(self, mock_llm_fail):
    """Test graceful handling of LLM failure."""
    classifier = EntityTypeClassifier(mock_llm_fail)

    with pytest.raises(EntityTypeClassificationException):
        result = classifier.classify("some text", OperationType.CREATE)
```

✅ **After:**
```python
def test_llm_failure(self, mock_llm_fail):
    """Test graceful handling of LLM failure."""
    classifier = EntityTypeClassifier(mock_llm_fail)

    with pytest.raises(EntityTypeClassificationException):
        entity_types, confidence = classifier.classify("some text", OperationType.CREATE)
```

**Pattern 3: Tests with Multiple Assertions**

❌ **Before:**
```python
def test_project_update_status_change(self, classifier):
    """Test project status update detection."""
    result = classifier.classify(
        "Mark the manual tetris test as INACTIVE",
        operation=OperationType.UPDATE
    )

    assert result.entity_type == EntityType.PROJECT
    assert result.confidence >= 0.85
    assert "project status" in result.reasoning.lower()
```

✅ **After:**
```python
def test_project_update_status_change(self, classifier):
    """Test project status update detection."""
    entity_types, confidence = classifier.classify(
        "Mark the manual tetris test as INACTIVE",
        operation=OperationType.UPDATE
    )

    assert len(entity_types) == 1
    assert entity_types[0] == EntityType.PROJECT
    assert confidence >= 0.85
    # Note: reasoning is no longer available in tuple return
```

### Phase 2: Update Performance Tests (Priority: MEDIUM)

**File:** `tests/nl/test_nl_performance.py`

❌ **Before:**
```python
def test_metrics_recording_entity_type_classifier(mock_llm, state_manager):
    """Test metrics recording for entity type classifier."""
    operation_context = OperationContext(
        operation=OperationType.CREATE,
        entity_type=EntityType.TASK,  # ❌ Wrong parameter
        identifier=None,
        parameters={},
        confidence=0.95,
        raw_input="create task"
    )
```

✅ **After:**
```python
def test_metrics_recording_entity_type_classifier(mock_llm, state_manager):
    """Test metrics recording for entity type classifier."""
    operation_context = OperationContext(
        operation=OperationType.CREATE,
        entity_types=[EntityType.TASK],  # ✅ Use entity_types (list)
        identifier=None,
        parameters={},
        confidence=0.95,
        raw_input="create task"
    )
```

**File:** `tests/nl/test_performance_benchmarks.py`

❌ **Before:**
```python
def test_entity_type_classifier_latency(self, classifier, benchmark):
    """Benchmark entity type classification latency."""
    result = benchmark(
        classifier.classify,
        "create epic for authentication",
        OperationType.CREATE
    )
    assert result.entity_type == EntityType.EPIC  # ❌ Returns tuple now
```

✅ **After:**
```python
def test_entity_type_classifier_latency(self, classifier, benchmark):
    """Benchmark entity type classification latency."""
    entity_types, confidence = benchmark(
        classifier.classify,
        "create epic for authentication",
        OperationType.CREATE
    )
    assert entity_types[0] == EntityType.EPIC  # ✅ Tuple unpacking
```

### Phase 3: Verify Backward Compatibility Layer (Priority: HIGH)

**File:** `src/nl/types.py`

The `OperationContext` class has a backward compatibility property:

```python
@dataclass
class OperationContext:
    entity_types: List[EntityType]  # New field

    @property
    def entity_type(self) -> EntityType:
        """Backward compatibility: return first entity type."""
        return self.entity_types[0] if self.entity_types else None
```

**Test this works:**
```python
def test_operation_context_backward_compatibility():
    """Test entity_type property for backward compatibility."""
    context = OperationContext(
        operation=OperationType.CREATE,
        entity_types=[EntityType.EPIC, EntityType.STORY],
        confidence=0.9,
        raw_input="test"
    )

    # New API
    assert context.entity_types == [EntityType.EPIC, EntityType.STORY]

    # Backward compatibility
    assert context.entity_type == EntityType.EPIC  # Returns first
```

---

## Migration Checklist

### 🎯 Phase 1: Entity Type Classifier Tests (27 tests)

**PROJECT classification (5 tests):**
- [ ] `test_project_update_status_change`
- [ ] `test_project_query_explicit`
- [ ] `test_project_create_explicit`
- [ ] `test_project_update_by_id`
- [ ] `test_project_delete`

**EPIC classification (5 tests):**
- [ ] `test_epic_create_explicit`
- [ ] `test_epic_update_status`
- [ ] `test_epic_delete_by_id`
- [ ] `test_epic_query_list`
- [ ] `test_epic_create_inferred_large_system`

**STORY classification (5 tests):**
- [ ] `test_story_create_explicit`
- [ ] `test_story_create_user_feature`
- [ ] `test_story_update_by_id`
- [ ] `test_story_query_for_epic`
- [ ] `test_story_delete`

**TASK classification (5 tests):**
- [ ] `test_task_query_explicit`
- [ ] `test_task_create_technical_work`
- [ ] `test_task_update_priority`
- [ ] `test_task_delete_by_id`
- [ ] `test_task_query_next_steps`

**MILESTONE classification (5 tests):**
- [ ] `test_milestone_create_explicit`
- [ ] `test_milestone_update_by_id`
- [ ] `test_milestone_delete`
- [ ] `test_milestone_query_roadmap`
- [ ] `test_milestone_create_beta_launch`

**Edge cases (2 tests):**
- [ ] `test_llm_failure`
- [ ] `test_invalid_json_response_with_fallback`

### 🎯 Phase 2: Performance Tests (2 tests)

- [ ] `test_metrics_recording_entity_type_classifier` (test_nl_performance.py)
- [ ] `test_entity_type_classifier_latency` (test_performance_benchmarks.py)

### 🎯 Phase 3: Integration Validation

- [ ] Run full test suite: `pytest tests/nl/ -v`
- [ ] Verify no regressions: `pytest tests/ -k "not slow" -v`
- [ ] Run bulk operation tests: `pytest tests/test_state_manager_bulk.py tests/nl/test_bulk_command_executor.py -v`
- [ ] Manual smoke test in interactive mode

---

## Automation Script

Create a helper script to automate the most common pattern:

**File:** `scripts/testing/migrate_entity_type_tests.py`

```python
#!/usr/bin/env python3
"""Automated migration of entity_type_classifier tests."""

import re
import sys
from pathlib import Path


def migrate_test_function(test_code: str) -> str:
    """Migrate a single test function to new API.

    Changes:
    1. result = classifier.classify(...)
       → entity_types, confidence = classifier.classify(...)
    2. result.entity_type → entity_types[0]
    3. result.confidence → confidence
    4. Add len(entity_types) == 1 assertion
    """
    # Pattern 1: Change result = to tuple unpacking
    test_code = re.sub(
        r'result = classifier\.classify\(',
        r'entity_types, confidence = classifier.classify(',
        test_code
    )

    # Pattern 2: Change result.entity_type to entity_types[0]
    test_code = re.sub(
        r'result\.entity_type',
        r'entity_types[0]',
        test_code
    )

    # Pattern 3: Change result.confidence to confidence
    test_code = re.sub(
        r'result\.confidence',
        r'confidence',
        test_code
    )

    # Pattern 4: Add assertion for single entity
    # Find first assertion after classify call
    if 'entity_types, confidence = classifier.classify' in test_code:
        # Add len check before first entity_types assertion
        test_code = re.sub(
            r'(entity_types, confidence = classifier\.classify\([^)]+\))\s+assert',
            r'\1\n    \n    # Single entity type expected\n    assert len(entity_types) == 1\n    assert',
            test_code,
            count=1
        )

    return test_code


def main():
    """Migrate test file."""
    if len(sys.argv) < 2:
        print("Usage: python migrate_entity_type_tests.py <test_file.py>")
        sys.exit(1)

    test_file = Path(sys.argv[1])
    if not test_file.exists():
        print(f"Error: {test_file} not found")
        sys.exit(1)

    # Read original
    original = test_file.read_text()

    # Migrate
    migrated = migrate_test_function(original)

    # Write backup
    backup = test_file.with_suffix('.py.bak')
    backup.write_text(original)
    print(f"✓ Backup created: {backup}")

    # Write migrated
    test_file.write_text(migrated)
    print(f"✓ Migrated: {test_file}")
    print(f"\nReview changes with: diff {backup} {test_file}")


if __name__ == '__main__':
    main()
```

**Usage:**
```bash
# Migrate single test file
python scripts/testing/migrate_entity_type_tests.py tests/nl/test_entity_type_classifier.py

# Review changes
diff tests/nl/test_entity_type_classifier.py.bak tests/nl/test_entity_type_classifier.py

# Run tests to verify
pytest tests/nl/test_entity_type_classifier.py -v
```

---

## Risk Mitigation

### Rollback Strategy

If migration causes issues, we have two rollback options:

**Option 1: Revert API Change (Simple)**

```python
# In src/nl/entity_type_classifier.py

def classify(self, user_input: str, operation: OperationType) -> EntityTypeResult:
    """Revert to old API temporarily."""
    entity_types, confidence = self._classify_internal(user_input, operation)

    # Return old format
    return EntityTypeResult(
        entity_type=entity_types[0],  # Take first
        confidence=confidence,
        raw_response="",
        reasoning=""
    )

def _classify_internal(self, user_input: str, operation: OperationType) -> tuple:
    """New implementation (keep for bulk ops)."""
    # ... existing new implementation ...
```

**Option 2: Feature Flag**

```yaml
# config/config.yaml
features:
  bulk_operations: false  # Disable if issues arise
```

### Validation Gates

Before marking migration complete, verify:

1. ✅ All 29 tests passing
2. ✅ No new test failures introduced
3. ✅ Bulk operations work in interactive mode
4. ✅ Performance benchmarks still pass
5. ✅ Documentation updated

---

## Testing Commands

### Run Specific Test Suites

```bash
# Entity type classifier tests only
pytest tests/nl/test_entity_type_classifier.py -v

# Performance tests
pytest tests/nl/test_nl_performance.py tests/nl/test_performance_benchmarks.py -v

# Bulk operation tests (should already pass)
pytest tests/test_state_manager_bulk.py tests/nl/test_bulk_command_executor.py -v

# Full NL suite
pytest tests/nl/ -v

# Integration suite
pytest tests/integration/ -v
```

### Verify No Regressions

```bash
# Run full suite (exclude slow tests)
pytest tests/ -k "not slow" -v --tb=short

# Check coverage
pytest --cov=src.nl --cov-report=term-missing tests/nl/

# Run in parallel for speed
pytest -n auto tests/nl/
```

---

## Timeline Estimate

| Phase | Tasks | Estimated Time | Status |
|-------|-------|---------------|--------|
| **Phase 1** | Update 27 entity_type_classifier tests | 1.5 hours | ⏳ Pending |
| **Phase 2** | Update 2 performance tests | 15 minutes | ⏳ Pending |
| **Phase 3** | Validation & smoke testing | 30 minutes | ⏳ Pending |
| **Documentation** | Update test guidelines | 15 minutes | ⏳ Pending |
| **Total** | | **2-3 hours** | |

---

## Success Criteria

Migration is complete when:

1. ✅ All 29 tests pass without modification to implementation
2. ✅ No regressions in unrelated tests
3. ✅ Bulk operations work correctly in interactive mode
4. ✅ Documentation reflects new API
5. ✅ Performance benchmarks meet targets
6. ✅ Test coverage maintained at ≥88%

---

## Additional Test Cases to Add

While migrating, add these test cases for bulk operations:

**File:** `tests/nl/test_entity_type_classifier.py`

```python
class TestEntityTypeClassifierBulkOperations:
    """Test multi-entity type classification for bulk operations."""

    def test_bulk_delete_multiple_entities(self, classifier):
        """Test 'delete all epics stories and tasks' returns all three."""
        entity_types, confidence = classifier.classify(
            "delete all epics stories and tasks",
            operation=OperationType.DELETE
        )

        # Should detect all three entity types
        assert len(entity_types) == 3
        assert EntityType.EPIC in entity_types
        assert EntityType.STORY in entity_types
        assert EntityType.TASK in entity_types
        assert confidence >= 0.85

    def test_bulk_delete_single_with_all_keyword(self, classifier):
        """Test 'delete all tasks' returns single entity type."""
        entity_types, confidence = classifier.classify(
            "delete all tasks",
            operation=OperationType.DELETE
        )

        assert len(entity_types) == 1
        assert entity_types[0] == EntityType.TASK
        assert confidence >= 0.90  # High confidence for explicit keyword

    def test_bulk_delete_without_all_keyword(self, classifier):
        """Test 'delete tasks' without 'all' returns single entity."""
        entity_types, confidence = classifier.classify(
            "delete tasks",
            operation=OperationType.DELETE
        )

        assert len(entity_types) == 1
        assert entity_types[0] == EntityType.TASK
```

---

## Documentation Updates

After migration complete, update:

1. **Test Guidelines** (`docs/testing/TEST_GUIDELINES.md`):
   - Add section on EntityTypeClassifier API changes
   - Document tuple unpacking pattern
   - Provide migration examples

2. **Architecture Docs** (`docs/architecture/ARCHITECTURE.md`):
   - Update NL command pipeline diagram
   - Document multi-entity classification flow

3. **Changelog** (`CHANGELOG.md`):
   ```markdown
   ### [1.7.5] - 2025-11-13

   #### Added
   - Bulk delete operations with multi-entity support
   - Natural language commands like "delete all epics stories and tasks"

   #### Changed
   - **BREAKING**: `EntityTypeClassifier.classify()` now returns `(List[EntityType], float)` tuple instead of `EntityTypeResult`
   - `OperationContext.entity_types` is now a list (backward compatible `entity_type` property provided)
   ```

---

## Notes

**Rationale for Breaking Change:**
- Multi-entity bulk operations are a critical feature request
- Old API couldn't support this use case
- Clean break now vs. complex dual-API maintenance later
- Only internal tests affected (no external API consumers)

**Alternative Considered:**
- Adding `classify_multi()` method alongside `classify()`
- **Rejected because:** Would lead to code duplication and confusion

**Backward Compatibility:**
- `OperationContext.entity_type` property provides read access to first entity type
- Existing code using `context.entity_type` will continue working
- Only direct `classifier.classify()` callers need updates (all in tests)

---

**Last Updated:** 2025-11-13
**Next Review:** After Phase 1 completion
**Owner:** Development Team
