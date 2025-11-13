# End-to-End (E2E) Tests

**Purpose**: Validate complete user journeys and real-world scenarios
**Speed**: 20-45 minutes
**Run**: Before major releases, nightly CI (optional)

## Test Categories

### Complete Workflows (`test_complete_workflows.py`)
Validate full end-to-end workflows covering the complete Obra value proposition.

**Tests**:
- `test_e2e_nl_to_task_creation` - Natural language → Task creation (full pipeline)
- `test_e2e_epic_to_stories_workflow` - Epic → Stories → Tasks hierarchy
- `test_e2e_task_with_dependencies` - Task dependency chains (M9 feature)
- `test_e2e_project_milestone_workflow` - Project → Epics → Milestone
- `test_e2e_multi_iteration_quality_loop` - Quality improvement across iterations

### Real-World Scenarios (`test_real_world_scenarios.py`)
Simulate actual production usage patterns.

**Tests**:
- `test_scenario_new_feature_development` - Adding new feature to existing project
- `test_scenario_bug_fix_urgent_patch` - Urgent production bug fix
- `test_scenario_multi_developer_project` - Multiple developers collaborating

**Edge Cases**:
- `test_edge_case_empty_project_workflow` - Operations on empty project
- `test_edge_case_circular_dependency_prevention` - Circular dependency handling
- `test_edge_case_very_long_epic` - Large epic with many stories (stress test)

## Running Tests

```bash
# All E2E tests
pytest tests/e2e/ -v -m e2e

# Only complete workflows
pytest tests/e2e/test_complete_workflows.py -v -m e2e

# Only real-world scenarios
pytest tests/e2e/test_real_world_scenarios.py -v -m e2e

# Skip slow tests (run fast E2E only)
pytest tests/e2e/ -v -m "e2e and not slow"

# With coverage
pytest tests/e2e/ -v -m e2e --cov=src --cov-report=term
```

## Prerequisites

### For Complete Workflows
- Ollama running on `http://10.0.75.1:11434`
- Qwen model available
- In-memory database (no setup needed)

### For Real-World Scenarios
- Same as above
- Temporary workspace (auto-created)

## Expected Results

| Test Suite | Tests | Duration | Pass Rate |
|------------|-------|----------|-----------|
| Complete Workflows | 5 tests | 5-10 min | 100% |
| Real-World Scenarios | 6 tests | 10-15 min | 100% |
| **Total** | **11 tests** | **15-25 min** | **100%** |

## Test Output

Each test includes detailed progress logging:

```
=== SCENARIO: New Feature Development ===
✓ Step 1: Using existing project 'E-Commerce Platform'
✓ Step 2: Created epic 42 via NL command
✓ Step 3: Broke down epic into 3 stories
✓ Step 4: Created task chain: 15 → 16 → 17
✓ Step 5: Progress check - Epic: 1, Stories: 3, Tasks: 8
✓ SCENARIO COMPLETE: Feature development workflow validated
```

## Key Validations

**E2E Workflows**:
- ✅ Natural language processing (full 5-stage pipeline)
- ✅ Task creation and hierarchy (Epic/Story/Task)
- ✅ Dependency management (M9 feature)
- ✅ Milestone tracking
- ✅ Quality iteration loops

**Real-World Scenarios**:
- ✅ Feature development workflow
- ✅ Urgent bug fix (high-priority fast track)
- ✅ Multi-developer collaboration (no conflicts)
- ✅ Edge case handling (empty projects, circular deps, large epics)

## Troubleshooting

**Tests taking too long**:
- Check Ollama is running and responsive
- Verify network latency to Ollama host
- Consider running subset of tests

**Tests failing**:
- Verify all Tier 1-3 tests pass first
- Check StateManager can initialize
- Ensure NL command processor configured

**Memory issues**:
- E2E tests use in-memory database
- Large epic test creates 20 stories (expected)
- Tests clean up after themselves
