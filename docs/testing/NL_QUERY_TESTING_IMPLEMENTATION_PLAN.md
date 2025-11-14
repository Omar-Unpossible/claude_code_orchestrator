# NL Query Testing Implementation Plan

**Version**: 1.0
**Date**: 2025-11-13
**Status**: Ready for Implementation
**Related Bugs**: FastPathMatcher API mismatch, StateManager missing methods, Query project filtering

---

## Executive Summary

This document outlines the implementation plan for comprehensive testing improvements to Obra's Natural Language (NL) query system. The improvements address three critical bugs discovered during production use and establish a robust testing framework to prevent similar issues in the future.

**Impact**:
- Prevents 3 classes of bugs from recurring
- Adds 100+ regression tests
- Increases test coverage by 2-3%
- Validates end-to-end NL command flow
- Establishes multi-project testing patterns

---

## Background

### Discovered Bugs

During production testing of Obra's NL command interface, three critical bugs were identified:

#### Bug 1: Fast Path Matcher API Mismatch
**Symptom**: `TypeError: OperationContext.__init__() got an unexpected keyword argument 'entity_type'`

**Root Cause**: FastPathMatcher was creating OperationContext with `entity_type` (singular) parameter, but OperationContext expects `entity_types` (plural, list) after ADR-016 refactor.

**Impact**: Broke all fast-path queries like "list all projects"

**Fix**: Changed `fast_path_matcher.py:172` to use `entity_types=[pattern_def.entity_type]`

#### Bug 2: Missing StateManager Methods
**Symptom**: `AttributeError: 'StateManager' object has no attribute 'list_epics'`

**Root Cause**: StateManager had `list_tasks()` but no convenience methods for `list_epics()` or `list_stories()`, despite having methods for creating epics/stories.

**Impact**: Bulk delete operations failed for epics; API inconsistency confused developers

**Fix**: Added `list_epics()` and `list_stories()` methods to StateManager at lines 1060-1118

#### Bug 3: Query Project Filtering
**Symptom**:
```
orchestrator> list the tasks for project #1
✓ Found 2 items(s)
  No results found
```

**Root Cause**: NL query methods (`_query_simple`, `_query_hierarchical`, `_query_backlog`, `_query_next_steps`) were not filtering by `project_id`, returning tasks from ALL projects but then displaying only the current project's tasks, causing count mismatches.

**Impact**: Confusing user experience; queries showed incorrect counts; multi-project setups returned wrong data

**Fix**: Added `project_id` parameter to all `state_manager.list_tasks()` calls in `nl_query_helper.py`

### Why These Bugs Occurred

1. **Integration Gap**: Unit tests existed for individual components but not for integration between FastPathMatcher → OperationContext → NLCommandProcessor
2. **API Incompleteness**: No systematic testing for StateManager API consistency across entity types
3. **Single-Project Testing**: All existing tests used single-project fixtures, missing multi-project filtering bugs

---

## Testing Strategy

### Objectives

1. **Prevent Regression**: Ensure fixed bugs don't reoccur
2. **Validate Integration**: Test component interactions, not just units
3. **Multi-Project Testing**: Validate filtering with multiple projects
4. **End-to-End Coverage**: Test complete user workflows
5. **API Consistency**: Validate all entity types have complete CRUD methods

### Test Categories

#### Category 1: Integration Tests
**Purpose**: Validate components work together correctly

**Files**:
- `tests/nl/test_fast_path_matcher_integration.py` (30+ tests)
- `tests/integration/test_nl_command_e2e.py` (10+ tests)

**Coverage**:
- FastPathMatcher creates valid OperationContext objects
- OperationContext can be passed through NL pipeline
- Complete user workflow from input to formatted output

#### Category 2: API Completeness Tests
**Purpose**: Ensure StateManager has consistent methods for all entity types

**Files**:
- `tests/test_state_manager_api_completeness.py` (25+ tests)

**Coverage**:
- All entity types have list methods (list_projects, list_epics, list_stories, list_tasks, list_milestones)
- Methods accept appropriate filters (status, epic_id, project_id)
- Methods return correct types (Task, Milestone models)
- Empty results handled gracefully

#### Category 3: Query Filtering Tests
**Purpose**: Validate queries filter by project_id in multi-project scenarios

**Files**:
- `tests/nl/test_nl_query_project_filtering.py` (25+ tests)

**Coverage**:
- SIMPLE queries filter by project
- HIERARCHICAL queries filter by project
- BACKLOG queries filter by project
- NEXT_STEPS queries filter by project
- ROADMAP queries filter by project
- Count accuracy (reported count matches actual entities)

#### Category 4: Regression Tests
**Purpose**: Prevent re-introduction of fixed bugs

**Files**:
- Modifications to `tests/nl/test_fast_path_matcher.py` (2+ tests)
- Modifications to `tests/test_state.py` (3+ tests)
- Modifications to `tests/nl/test_nl_query_helper.py` (2+ tests)

**Coverage**:
- entity_types is list, not single value
- list_epics() and list_stories() exist and work
- Queries filter by project_id parameter

---

## Implementation Plan

### Phase 1: Core Test Infrastructure (Priority: HIGH)

**Timeline**: 2-3 hours

**Tasks**:
1. Create `test_fast_path_matcher_integration.py`
2. Create `test_state_manager_api_completeness.py`
3. Create `test_nl_query_project_filtering.py`
4. Create `test_nl_command_e2e.py`

**Success Criteria**:
- All 4 files created
- All tests pass independently
- No import or fixture errors

### Phase 2: Regression Test Updates (Priority: HIGH)

**Timeline**: 1 hour

**Tasks**:
1. Add OperationContext validation tests to `test_fast_path_matcher.py`
2. Add list_epics/list_stories tests to `test_state.py`
3. Add project filtering tests to `test_nl_query_helper.py`

**Success Criteria**:
- All existing tests still pass
- New tests validate bug fixes
- No breaking changes

### Phase 3: Integration and Validation (Priority: MEDIUM)

**Timeline**: 1 hour

**Tasks**:
1. Run full test suite
2. Validate coverage improvements
3. Manual testing of bug scenarios
4. Performance testing (test execution time)

**Success Criteria**:
- All 100+ new tests pass
- Coverage increased by 2-3%
- Manual bug scenarios work correctly
- Test suite runs in <5 minutes

### Phase 4: Documentation and CI/CD (Priority: LOW)

**Timeline**: 1 hour

**Tasks**:
1. Update `docs/testing/NL_QUERY_TESTING_STRATEGY.md`
2. Update `CHANGELOG.md`
3. Update `docs/testing/README.md`
4. Add to CI/CD pipeline (if applicable)

**Success Criteria**:
- Documentation reflects new tests
- Changelog updated
- CI/CD includes new tests

---

## Test Design Patterns

### Pattern 1: Multi-Project Fixtures

**Problem**: Single-project fixtures don't catch filtering bugs

**Solution**: Create fixtures with multiple projects and cross-project data

```python
@pytest.fixture
def multi_project_db(state_manager):
    """Creates 2 projects with different entities."""
    project1_id = state_manager.create_project("Project 1", "First")
    project2_id = state_manager.create_project("Project 2", "Second")
    # Add entities to both...
    return {'project1_id': project1_id, 'project2_id': project2_id}
```

**Benefits**:
- Validates filtering logic
- Tests project isolation
- Catches cross-project bugs

### Pattern 2: Count Accuracy Assertions

**Problem**: Count in message doesn't match displayed entities

**Solution**: Always assert `count == len(entities)`

```python
count_in_message = int(result['message'].split()[1])
entities = result['data']['entities']
assert count_in_message == len(entities), "Count must match entities"
```

**Benefits**:
- Catches count calculation bugs
- Validates user-facing messages
- Ensures consistency

### Pattern 3: Integration Path Testing

**Problem**: Components work in isolation but fail when integrated

**Solution**: Test complete paths through the system

```python
# User input → NL Processor → Orchestrator → Query Helper → Response
parsed_intent = nl_processor.process("list tasks")
result = orchestrator.execute_nl_command(parsed_intent, project_id=1)
assert result['success']
assert 'data' in result
```

**Benefits**:
- Validates real user workflows
- Catches API mismatches
- Tests error propagation

### Pattern 4: API Symmetry Testing

**Problem**: Some entity types have methods others don't

**Solution**: Test all entity types have complete CRUD operations

```python
def test_all_list_methods_available(state_manager):
    """Validate all entity types have list methods."""
    projects = state_manager.list_projects()
    epics = state_manager.list_epics(project_id)
    stories = state_manager.list_stories(project_id)
    tasks = state_manager.list_tasks(project_id)
    milestones = state_manager.list_milestones(project_id)
    # All should work without AttributeError
```

**Benefits**:
- Ensures API consistency
- Prevents missing method errors
- Documents expected API

---

## Coverage Goals

### Module Coverage Targets

| Module | Current | Target | Delta |
|--------|---------|--------|-------|
| `src/nl/fast_path_matcher.py` | 85% | 95% | +10% |
| `src/nl/nl_query_helper.py` | 75% | 90% | +15% |
| `src/core/state.py` (Agile methods) | 88% | 95% | +7% |
| `src/nl/nl_command_processor.py` | 80% | 90% | +10% |
| **Overall NL module** | 82% | 90% | +8% |

### Lines Added by Test File

| Test File | New Tests | Lines | Coverage Gain |
|-----------|-----------|-------|---------------|
| `test_fast_path_matcher_integration.py` | 30+ | 500+ | +10% fast_path_matcher.py |
| `test_state_manager_api_completeness.py` | 25+ | 450+ | +7% state.py |
| `test_nl_query_project_filtering.py` | 25+ | 600+ | +15% nl_query_helper.py |
| `test_nl_command_e2e.py` | 10+ | 400+ | +5% orchestrator.py |
| **Total** | **90+** | **1950+** | **+8% NL module** |

---

## Risk Assessment

### Risks and Mitigations

#### Risk 1: Test Execution Time
**Probability**: Medium
**Impact**: Low
**Mitigation**:
- Use in-memory SQLite for tests
- Follow TEST_GUIDELINES.md (max 0.5s sleep, 5 threads)
- Run tests in parallel with `pytest -n auto`

#### Risk 2: Fixture Complexity
**Probability**: Low
**Impact**: Medium
**Mitigation**:
- Reuse shared fixtures from `conftest.py`
- Document fixture dependencies
- Keep fixtures focused and single-purpose

#### Risk 3: Flaky Tests
**Probability**: Low
**Impact**: High
**Mitigation**:
- Use deterministic test data
- Avoid time-based assertions
- Clean up database state between tests

#### Risk 4: Breaking Changes
**Probability**: Very Low
**Impact**: High
**Mitigation**:
- Only add tests, don't modify production code
- Run full test suite before committing
- Use semantic versioning for any API changes

---

## Success Metrics

### Quantitative Metrics

- **Test Count**: Add 100+ new tests
- **Coverage Increase**: +2-3% overall, +8% NL module
- **Bug Prevention**: 0 regressions of fixed bugs
- **Execution Time**: Test suite completes in <5 minutes
- **Pass Rate**: 100% of new tests pass on first run

### Qualitative Metrics

- **Code Quality**: Tests follow pytest best practices
- **Documentation**: Clear docstrings explain what each test validates
- **Maintainability**: Tests are easy to understand and modify
- **Reusability**: Fixtures can be reused for future tests

---

## Dependencies

### Prerequisites

- Python 3.9+
- pytest 7.0+
- All Obra dependencies installed (`requirements.txt`)
- Access to test database
- LLM provider available (for NL processing tests)

### External Dependencies

None - all tests use mocked or in-memory databases.

---

## Rollout Plan

### Step 1: Create Test Files (Week 1)
- Implement all 4 new test files
- Verify tests pass independently
- Review with team

### Step 2: Update Existing Tests (Week 1)
- Add regression tests to existing files
- Ensure no breaking changes
- Run full test suite

### Step 3: Integration Testing (Week 2)
- Run all tests together
- Validate coverage improvements
- Performance testing

### Step 4: Documentation (Week 2)
- Update testing docs
- Update CHANGELOG
- Update README

### Step 5: CI/CD Integration (Week 3)
- Add to GitHub Actions / CI pipeline
- Configure coverage reporting
- Set up notifications

---

## Maintenance Plan

### Ongoing Maintenance

**Weekly**:
- Run full test suite
- Check for flaky tests
- Review coverage reports

**Monthly**:
- Review and update test fixtures
- Add tests for new features
- Refactor tests as needed

**Quarterly**:
- Review testing strategy
- Update coverage targets
- Performance optimization

### Test Ownership

| Test Category | Owner | Backup |
|---------------|-------|--------|
| FastPathMatcher | NL Module Team | Integration Team |
| StateManager | Core Team | API Team |
| Query Filtering | NL Module Team | Core Team |
| E2E Tests | Integration Team | QA Team |

---

## References

### Related Documents

- `docs/testing/TEST_GUIDELINES.md` - WSL2 crash prevention rules
- `docs/testing/CLAUDE_IMPLEMENTATION_NL_QUERY_TESTS.md` - Machine-optimized implementation guide
- `docs/decisions/ADR-016-decompose-nl-entity-extraction.md` - NL architecture
- `docs/decisions/ADR-017-unified-execution-architecture.md` - NL execution flow

### Bug Reports

- Bug #1: Fast Path Matcher API Mismatch (Fixed 2025-11-13)
- Bug #2: Missing StateManager Methods (Fixed 2025-11-13)
- Bug #3: Query Project Filtering (Fixed 2025-11-13)

### Code References

- `src/nl/fast_path_matcher.py:172` - entity_types fix
- `src/core/state.py:1060-1118` - list_epics/list_stories
- `src/nl/nl_query_helper.py:278,319,386,434` - project_id filtering

---

## Appendix A: Test File Structure

```
tests/
├── nl/
│   ├── test_fast_path_matcher.py              (EXISTING - modify)
│   ├── test_fast_path_matcher_integration.py  (NEW)
│   ├── test_nl_query_helper.py                (EXISTING - modify)
│   └── test_nl_query_project_filtering.py     (NEW)
├── integration/
│   └── test_nl_command_e2e.py                 (NEW)
├── test_state.py                              (EXISTING - modify)
└── test_state_manager_api_completeness.py     (NEW)
```

---

## Appendix B: Example Test Output

```bash
$ pytest tests/nl/test_fast_path_matcher_integration.py -v

tests/nl/test_fast_path_matcher_integration.py::TestFastPathMatcherIntegration::test_project_query_creates_valid_context PASSED
tests/nl/test_fast_path_matcher_integration.py::TestFastPathMatcherIntegration::test_task_query_creates_valid_context PASSED
tests/nl/test_fast_path_matcher_integration.py::TestFastPathMatcherIntegration::test_epic_with_id_creates_valid_context PASSED
...
============================== 30 passed in 2.45s ===============================

$ pytest --cov=src --cov-report=term-missing

---------- coverage: platform linux, python 3.9.18 -----------
Name                                Stmts   Miss  Cover   Missing
-----------------------------------------------------------------
src/nl/fast_path_matcher.py          145      7    95%   89-91, 145-147
src/nl/nl_query_helper.py            312     15    95%   234-238, 401-405
src/core/state.py                    1876     98    95%   (multiple)
-----------------------------------------------------------------
TOTAL                                8234    412    95%
```

---

**END OF IMPLEMENTATION PLAN**
