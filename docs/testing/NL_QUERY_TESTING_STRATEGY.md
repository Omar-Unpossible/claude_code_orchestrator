# Natural Language Query Testing Strategy

**Version**: 1.0
**Date**: 2025-11-13
**Status**: Active
**Scope**: NL Command System Testing

---

## Overview

This document defines the comprehensive testing strategy for Obra's Natural Language (NL) query system, covering the entire pipeline from user input to formatted response.

### System Under Test

The NL query system consists of:

1. **FastPathMatcher** - Pattern-based query detection (bypasses LLM for common queries)
2. **NLCommandProcessor** - 5-stage NL processing pipeline
3. **NLQueryHelper** - Query execution and result formatting
4. **StateManager** - Data access layer with entity-specific methods
5. **Orchestrator** - Integration and validation layer

### Testing Philosophy

**Test the Integration, Not Just the Units**

While unit tests are valuable, the bugs fixed by this testing suite were all **integration bugs**:
- Components worked correctly in isolation
- Components failed when combined
- API mismatches weren't caught by unit tests alone

Therefore, this strategy emphasizes:
- ✅ **Integration tests** - Test component interactions
- ✅ **End-to-end tests** - Test complete user workflows
- ✅ **Multi-project fixtures** - Test with realistic data scenarios
- ✅ **API consistency tests** - Validate all entity types equally

---

## Test Pyramid

```
           /\
          /  \     E2E Tests (10%)
         /----\    - Complete user workflows
        /      \   - NL input → formatted output
       /--------\
      / Integration\ (30%)
     /--------------\ - Component interactions
    /   Unit Tests   \ (60%)
   /------------------\ - Individual functions
  /____________________\ - Mocked dependencies
```

### Layer Breakdown

**Unit Tests (60%)**:
- Individual function testing
- Mocked dependencies
- Fast execution (<1s per test)
- Examples: `test_fast_path_matcher.py`, `test_state.py`

**Integration Tests (30%)**:
- Component interaction testing
- Real database (in-memory)
- Moderate execution (1-3s per test)
- Examples: `test_fast_path_matcher_integration.py`, `test_state_manager_api_completeness.py`

**End-to-End Tests (10%)**:
- Complete workflow testing
- Full system stack
- Slower execution (3-5s per test)
- Examples: `test_nl_command_e2e.py`

---

## Test Categories

### Category 1: Fast Path Integration Tests

**Purpose**: Validate FastPathMatcher creates valid OperationContext objects

**File**: `tests/nl/test_fast_path_matcher_integration.py`

**Coverage**:
- Pattern matching for all entity types (project, epic, story, task, milestone)
- ID extraction from patterns (e.g., "get epic 5")
- OperationContext structure validation
- Backward compatibility (entity_type property)
- Case-insensitive matching
- Metrics tracking (hit/miss counts)

**Why This Matters**:
Bug #1 (Fixed): FastPathMatcher used `entity_type` instead of `entity_types`, causing TypeError when OperationContext was created. Unit tests for FastPathMatcher passed because they didn't validate the created OperationContext. Integration tests catch this.

**Key Test Pattern**:
```python
def test_pattern_creates_valid_context(matcher):
    context = matcher.match("list all projects")

    # Validate structure
    assert isinstance(context, OperationContext)
    assert isinstance(context.entity_types, list)  # Must be list!

    # Validate can be used downstream
    _ = context.operation
    _ = context.entity_type  # Backward compat property
```

### Category 2: StateManager API Completeness Tests

**Purpose**: Ensure all entity types have consistent CRUD methods

**File**: `tests/test_state_manager_api_completeness.py`

**Coverage**:
- All entity types have list methods (list_projects, list_epics, list_stories, list_tasks, list_milestones)
- Methods accept appropriate filters (project_id, epic_id, status)
- Methods return correct types (Task, Project, Milestone models)
- Filtering works correctly (by project, by epic, by status)
- Empty results handled gracefully
- Method signatures are consistent

**Why This Matters**:
Bug #2 (Fixed): StateManager had `create_epic()` and `get_epic_stories()` but no `list_epics()`. Bulk delete operations failed because they expected `list_epics()` to exist. This tests for API symmetry.

**Key Test Pattern**:
```python
def test_all_list_methods_available(state_manager, project_id):
    """Validate API symmetry across entity types."""
    # All these should work without AttributeError
    projects = state_manager.list_projects()
    epics = state_manager.list_epics(project_id)
    stories = state_manager.list_stories(project_id)
    tasks = state_manager.list_tasks(project_id)
    milestones = state_manager.list_milestones(project_id)
```

### Category 3: Query Project Filtering Tests

**Purpose**: Validate queries filter by project_id in multi-project scenarios

**File**: `tests/nl/test_nl_query_project_filtering.py`

**Coverage**:
- SIMPLE queries filter by project (all entity types)
- HIERARCHICAL queries filter by project
- BACKLOG queries filter by project (pending tasks only)
- NEXT_STEPS queries filter by project (prioritized)
- ROADMAP queries filter by project (milestones)
- Count accuracy (reported count == actual entities)
- Empty project handling

**Why This Matters**:
Bug #3 (Fixed): Query methods returned tasks from ALL projects instead of filtering by project_id. This caused:
- "Found 5 items / No results found" contradictions
- Incorrect counts in multi-project setups
- Security concern (could see other projects' tasks)

Single-project test fixtures didn't catch this bug.

**Key Test Pattern**:
```python
def test_query_filters_by_project(query_helper, multi_project_db):
    """Validate project isolation."""
    # Query project 1
    result1 = query_helper.execute(context, project_id=project1_id)
    result2 = query_helper.execute(context, project_id=project2_id)

    # Counts should differ
    assert result1.results['count'] != result2.results['count']

    # Entities should only be from that project
    entities1 = result1.results['entities']
    assert all('P1' in e['title'] for e in entities1)
```

### Category 4: End-to-End NL Command Tests

**Purpose**: Test complete user workflow from input to output

**File**: `tests/integration/test_nl_command_e2e.py`

**Coverage**:
- User input → NLCommandProcessor → Orchestrator → Response
- Message formatting accuracy
- Count/entity matching validation
- Project isolation in full workflow
- Fast path integration with orchestrator
- Hierarchical query formatting
- Error handling and empty results

**Why This Matters**:
Unit and integration tests validated individual components, but didn't test the **complete path** a user request takes. E2E tests catch:
- Message formatting bugs
- Context passing issues
- Response structure changes

**Key Test Pattern**:
```python
def test_count_matches_display(orchestrator, project_id):
    """Validate user-facing message matches reality."""
    parsed_intent = nl_processor.process("list tasks")
    result = orchestrator.execute_nl_command(parsed_intent, project_id)

    # Extract count from message
    count_in_message = int(result['message'].split()[1])
    entities = result['data']['entities']

    # CRITICAL: Must match exactly
    assert count_in_message == len(entities)
```

---

## Test Data Strategy

### Multi-Project Fixtures

**Problem**: Single-project fixtures don't catch filtering bugs

**Solution**: Create fixtures with 2+ projects and cross-project data

```python
@pytest.fixture
def multi_project_db(state_manager):
    """Two projects with different entities."""
    # Project 1: 3 tasks, 1 epic, 1 story
    project1_id = create_project_with_tasks(state_manager, "Project 1", 3)

    # Project 2: 2 tasks, 1 epic, 1 story
    project2_id = create_project_with_tasks(state_manager, "Project 2", 2)

    return {'project1_id': project1_id, 'project2_id': project2_id}
```

**Benefits**:
- Tests project filtering logic
- Catches cross-project data leaks
- Validates query isolation
- Realistic production scenarios

### Entity Completeness Fixtures

**Problem**: Tests only create tasks, missing epics/stories/milestones

**Solution**: Create fixtures with ALL entity types

```python
@pytest.fixture
def project_with_entities(state_manager):
    """Project with complete entity hierarchy."""
    project_id = state_manager.create_project("Test", "Test")
    epic_id = state_manager.create_epic(project_id, "Epic", "Epic")
    story_id = state_manager.create_story(project_id, epic_id, "Story", "Story")
    task_id = state_manager.create_task(project_id, {'title': 'Task'})
    milestone_id = state_manager.create_milestone(project_id, "MS", "MS", [epic_id])

    return {'project_id': project_id, 'epic_id': epic_id, ...}
```

**Benefits**:
- Tests all entity types equally
- Validates API consistency
- Catches entity-specific bugs

---

## Assertion Patterns

### Pattern 1: Count Accuracy

**Always validate reported count matches actual entities**

```python
# BAD: Only check success
assert result.success

# GOOD: Validate count accuracy
assert result.results['count'] == len(result.results['entities'])
```

**Rationale**: Prevents "Found X items / No results found" bugs

### Pattern 2: Project Isolation

**Always validate entities are from correct project**

```python
# BAD: Only check count
assert len(entities) == expected_count

# GOOD: Validate entities are from correct project
assert all(e['project_id'] == project_id for e in entities)
```

**Rationale**: Prevents cross-project data leaks

### Pattern 3: API Symmetry

**Validate all entity types have equivalent methods**

```python
# BAD: Test one entity type
assert hasattr(state_manager, 'list_tasks')

# GOOD: Test all entity types
for entity_type in ['projects', 'epics', 'stories', 'tasks', 'milestones']:
    assert hasattr(state_manager, f'list_{entity_type}')
```

**Rationale**: Ensures API consistency

### Pattern 4: Integration Path Validation

**Test complete paths through system**

```python
# BAD: Test components separately
context = OperationContext(...)
result = query_helper.execute(context)

# GOOD: Test full integration
user_input = "list all tasks"
parsed_intent = nl_processor.process(user_input)
result = orchestrator.execute_nl_command(parsed_intent, project_id)
# Validate entire response structure
```

**Rationale**: Catches integration bugs

---

## Coverage Targets

### Module-Level Targets

| Module | Target | Priority |
|--------|--------|----------|
| `fast_path_matcher.py` | 95% | HIGH |
| `nl_query_helper.py` | 90% | HIGH |
| `nl_command_processor.py` | 90% | HIGH |
| `state.py` (Agile methods) | 95% | HIGH |
| `orchestrator.py` (NL methods) | 85% | MEDIUM |

### Feature-Level Targets

| Feature | Target | Tests |
|---------|--------|-------|
| Fast path matching | 95% | 30+ |
| Query execution | 90% | 25+ |
| Project filtering | 95% | 25+ |
| API completeness | 100% | 25+ |
| E2E workflows | 85% | 10+ |

---

## Test Execution Strategy

### Local Development

```bash
# Run all NL tests
pytest tests/nl/ -v

# Run integration tests only
pytest tests/integration/test_nl_command_e2e.py -v

# Run with coverage
pytest tests/nl/ --cov=src/nl --cov-report=term-missing

# Run fast tests only (< 1s each)
pytest -m "not slow"
```

### CI/CD Pipeline

```yaml
# Recommended GitHub Actions workflow
- name: Run NL Query Tests
  run: |
    pytest tests/nl/test_fast_path_matcher_integration.py -v
    pytest tests/test_state_manager_api_completeness.py -v
    pytest tests/nl/test_nl_query_project_filtering.py -v
    pytest tests/integration/test_nl_command_e2e.py -v

- name: Coverage Report
  run: |
    pytest --cov=src/nl --cov-report=xml
    codecov -f coverage.xml
```

### Performance Targets

- **Individual test**: < 1s (unit), < 3s (integration), < 5s (E2E)
- **Full NL suite**: < 5 minutes
- **Full test suite**: < 10 minutes

### Test Resource Limits (WSL2 Safety)

Per `docs/testing/TEST_GUIDELINES.md`:
- ⚠️ Max sleep per test: 0.5s (use `fast_time` fixture for longer)
- ⚠️ Max threads per test: 5 (with mandatory timeout)
- ⚠️ Max memory allocation: 20KB per test
- ⚠️ Mark heavy tests: `@pytest.mark.slow`

---

## Maintenance and Evolution

### Adding New Tests

When adding new NL features, add tests in this order:

1. **Unit tests** for new functions/methods
2. **Integration tests** for component interactions
3. **E2E tests** for user workflows
4. **Regression tests** to prevent bug reoccurrence

### Updating Existing Tests

When modifying NL code:

1. **Run affected tests** before making changes
2. **Update tests** to match new behavior
3. **Add regression tests** for bugs discovered
4. **Validate coverage** hasn't decreased

### Test Refactoring

Refactor tests when:
- ❌ Tests are flaky (fail intermittently)
- ❌ Tests are slow (exceed performance targets)
- ❌ Tests are unclear (hard to understand what's being tested)
- ❌ Tests are duplicative (multiple tests for same thing)

---

## Common Testing Pitfalls

### Pitfall 1: Testing in Isolation

**Problem**: Unit tests pass but integration fails

**Solution**: Always add integration tests for component boundaries

**Example**:
```python
# Unit test (INSUFFICIENT)
def test_fast_path_matcher():
    matcher = FastPathMatcher()
    result = matcher.match("list projects")
    assert result is not None

# Integration test (BETTER)
def test_fast_path_creates_valid_context():
    matcher = FastPathMatcher()
    context = matcher.match("list projects")
    # Validate context can be used downstream
    nl_processor.validate_context(context)  # Would catch API mismatch
```

### Pitfall 2: Single-Project Testing

**Problem**: Tests work with one project, fail with multiple

**Solution**: Use multi-project fixtures

**Example**:
```python
# Single-project test (INSUFFICIENT)
def test_query_tasks(state_manager):
    project_id = create_project(state_manager)
    tasks = query_helper.execute(..., project_id=project_id)
    assert len(tasks) > 0

# Multi-project test (BETTER)
def test_query_filters_by_project(multi_project_db):
    # Would catch if query returns ALL projects' tasks
    tasks1 = query_helper.execute(..., project_id=project1_id)
    tasks2 = query_helper.execute(..., project_id=project2_id)
    assert tasks1 != tasks2
```

### Pitfall 3: Ignoring Count Accuracy

**Problem**: Message says "Found 5 items" but displays 0

**Solution**: Always assert count == len(entities)

**Example**:
```python
# Weak assertion (INSUFFICIENT)
def test_query_succeeds():
    result = execute_query(...)
    assert result.success

# Strong assertion (BETTER)
def test_query_count_accurate():
    result = execute_query(...)
    assert result.success
    assert result.results['count'] == len(result.results['entities'])
```

### Pitfall 4: Missing API Symmetry

**Problem**: Some entity types have methods, others don't

**Solution**: Test all entity types have equivalent methods

**Example**:
```python
# Incomplete test (INSUFFICIENT)
def test_list_tasks_exists():
    assert hasattr(state_manager, 'list_tasks')

# Complete test (BETTER)
def test_all_list_methods_exist():
    entity_types = ['projects', 'epics', 'stories', 'tasks', 'milestones']
    for entity_type in entity_types:
        method_name = f'list_{entity_type}'
        assert hasattr(state_manager, method_name), \
            f"Missing {method_name}() method"
```

---

## Test Quality Metrics

### Quantitative Metrics

- **Test Count**: 100+ new tests added
- **Coverage**: 90%+ for NL modules
- **Pass Rate**: 100% (no flaky tests)
- **Execution Time**: <5 minutes for NL suite
- **Bug Detection**: 100% of fixed bugs have regression tests

### Qualitative Metrics

- **Clarity**: Tests have clear docstrings explaining what they validate
- **Maintainability**: Tests are easy to update when code changes
- **Isolation**: Tests don't depend on external services
- **Determinism**: Tests produce same result every time
- **Relevance**: Tests validate real user workflows

---

## Future Enhancements

### Phase 2 Testing (Future)

Once Phase 1 (current) is complete, consider:

1. **Performance Testing**
   - Query execution time benchmarks
   - Large dataset stress tests
   - Concurrent query handling

2. **Security Testing**
   - SQL injection prevention
   - Cross-project data isolation
   - Input validation

3. **Usability Testing**
   - Message clarity validation
   - Error message quality
   - Help text accuracy

4. **Compatibility Testing**
   - Different LLM providers
   - Database backend variations
   - Python version compatibility

---

## References

### Related Documents

- `CLAUDE_IMPLEMENTATION_NL_QUERY_TESTS.md` - Implementation guide for Claude Code
- `NL_QUERY_TESTING_IMPLEMENTATION_PLAN.md` - Human-readable plan with timelines
- `TEST_GUIDELINES.md` - WSL2 crash prevention rules
- `ADR-016-decompose-nl-entity-extraction.md` - NL architecture
- `ADR-017-unified-execution-architecture.md` - NL execution flow

### External References

- [pytest documentation](https://docs.pytest.org/)
- [pytest fixtures guide](https://docs.pytest.org/en/stable/fixture.html)
- [Test Pyramid concept](https://martinfowler.com/articles/practical-test-pyramid.html)

---

## Appendix: Quick Reference

### Test File Locations

```
tests/
├── nl/
│   ├── test_fast_path_matcher.py              (Unit + Integration)
│   ├── test_fast_path_matcher_integration.py  (Integration)
│   ├── test_nl_query_helper.py                (Unit + Integration)
│   └── test_nl_query_project_filtering.py     (Integration)
├── integration/
│   └── test_nl_command_e2e.py                 (E2E)
├── test_state.py                              (Unit)
└── test_state_manager_api_completeness.py     (Integration)
```

### Running Tests by Category

```bash
# Unit tests only
pytest tests/nl/test_fast_path_matcher.py -v

# Integration tests
pytest tests/nl/test_fast_path_matcher_integration.py \
       tests/test_state_manager_api_completeness.py \
       tests/nl/test_nl_query_project_filtering.py -v

# E2E tests
pytest tests/integration/test_nl_command_e2e.py -v

# All NL tests
pytest tests/nl/ tests/integration/test_nl_command_e2e.py -v
```

### Key Assertions to Remember

```python
# Count accuracy
assert result['count'] == len(result['entities'])

# Project isolation
assert all(e['project_id'] == project_id for e in entities)

# API symmetry
assert hasattr(state_manager, f'list_{entity_type}')

# Integration path
parsed_intent = nl_processor.process(user_input)
result = orchestrator.execute_nl_command(parsed_intent, project_id)
assert result['success'] and 'data' in result
```

---

**END OF TESTING STRATEGY**
