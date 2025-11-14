# Integrated Natural Language Testing Strategy
**Date**: 2025-11-13
**Version**: 2.0 (INTEGRATED)
**Priority**: CRITICAL
**Philosophy**: ✅ REAL Testing First, 🔶 Mocks for Initial Validation Only

---

## Executive Summary

**Problem**: Current testing has 88% unit test coverage but **broken real workflows**:
- ❌ 10/12 integration tests failing (not updated for v1.7.5 API)
- ❌ 3/10 smoke tests failing (pipeline issues)
- ❌ 0 E2E tests running (all skipped)
- ❌ Basic workflows broken: list projects, create epics, delete assets

**Root Cause**: Mock-heavy testing strategy hides real integration issues

**New Philosophy**:
```
┌─────────────────────────────────────────────────┐
│  WORK IS NOT "DONE" UNTIL REAL TESTS PASS      │
│                                                  │
│  ✅ REAL LLM (Qwen 2.5 Coder on Ollama)        │
│  ✅ REAL StateManager (SQLite)                  │
│  ✅ REAL Orchestrator (full pipeline)           │
│  ✅ REAL workflows (actual user commands)       │
│                                                  │
│  🔶 Mocks ONLY for initial unit test validity   │
│  🔶 Mocks NOT for integration/E2E/acceptance     │
└─────────────────────────────────────────────────┘
```

**Solution**: 4-tier testing pyramid with automated variation testing

---

## Testing Philosophy: Real First

### Tier 1: Mock-Based Unit Tests (20% of effort)
**Purpose**: Fast validation of code logic
**When**: Initial development, TDD, quick iteration
**NOT Done Criteria**: Code may work in isolation but fail in integration

**Example**:
```python
def test_entity_classifier_with_mock():
    """Mock-based: Validates logic, NOT real behavior"""
    mock_llm.generate.return_value = '{"entity_types": ["TASK"]}'
    entity_types, conf = classifier.classify("create task")
    assert entity_types == [EntityType.TASK]  # ✅ Passes but may not work in reality
```

### Tier 2: Real Component Integration (30% of effort)
**Purpose**: Validate components work together with REAL dependencies
**When**: After unit tests pass, before E2E
**NOT Done Criteria**: Components work together but workflow may fail

**Example**:
```python
def test_nl_pipeline_real_components():
    """Real components, mock LLM only"""
    real_state_manager = StateManager('sqlite:///:memory:')
    real_nl_processor = NLCommandProcessor(llm=mock_llm_realistic, state=real_state_manager)

    response = real_nl_processor.process("list all tasks")
    # Uses REAL StateManager, REAL NLQueryHelper, mocked LLM
```

### Tier 3: Real LLM Workflow Tests (40% of effort) ⭐ PRIMARY
**Purpose**: Validate complete workflows with REAL LLM
**When**: Before considering work "done"
**IS Done Criteria**: User workflows work end-to-end with real LLM

**Example**:
```python
@pytest.mark.requires_ollama
@pytest.mark.real_llm
def test_create_epic_real_workflow():
    """REAL LLM + REAL components - This is what users experience"""
    real_llm = OllamaLLM('http://10.0.75.1:11434', 'qwen2.5-coder:32b')
    real_orchestrator = Orchestrator(config, llm=real_llm)

    # Actual user command
    result = real_orchestrator.execute_nl_command("create epic for user auth", project_id=1)

    # Validate in database
    epic = real_orchestrator.state_manager.get_task(result.created_ids[0])
    assert epic.task_type == TaskType.EPIC
    assert "auth" in epic.title.lower()
```

### Tier 4: Automated Variation Testing (10% of effort) 🚀 NEW
**Purpose**: Stress test NL pipeline with 100+ real variations
**When**: After workflows pass, before release
**IS Done Criteria**: Pipeline handles natural language variations gracefully

**Example**:
```python
@pytest.mark.stress_test
def test_create_epic_100_variations():
    """100x variations of 'create epic' with REAL LLM"""
    variations = [
        "create epic for user auth",
        "add an epic for authentication",
        "I need to create a new epic called user auth",
        "can you create an epic for the auth system",
        # ... 96 more variations
    ]

    for variation in variations:
        result = orchestrator.execute_nl_command(variation, project_id=1)
        assert result.success, f"Failed: {variation}"
```

---

## Integrated Test Pyramid

```
            /\
           /  \     Tier 4: Automated Variation Testing (10%)
          / 🚀 \    - 100x variations per workflow
         /------\   - REAL LLM stress testing
        /        \  - Auto-document failures
       /----------\
      /   Tier 3   \ Tier 3: Real LLM Workflows (40%) ⭐
     /    ⭐ REAL   \ - Complete user journeys
    /      LLM      \ - REAL LLM + components
   /--------------  \ - IS "done" criteria
  /                  \
 /    Tier 2          \ Tier 2: Component Integration (30%)
/    Component Integ.  \ - Real components, mock LLM
/----------------------\ - NOT done, but necessary

        Tier 1          Tier 1: Mock Unit Tests (20%)
     Mock-Based Unit    - Fast iteration
   /------------------\ - NOT done, but useful
```

**Key Shift**: Inverted from current 80/20 mock/real to 30/70 mock/real

---

## Phase Structure

### Phase 0: Fix Broken Tests (IMMEDIATE - 4 hours)

**Goal**: Get existing tests passing to establish baseline

**Tasks**:
1. Fix 10 integration tests (`entity_type` → `entity_types`)
2. Fix 3 smoke tests (pipeline issues)
3. Verify 815 unit tests still pass

**Success**: 100% of existing tests pass (no real LLM yet)

---

### Phase 1: Real Component Integration (DAY 1 - 8 hours)

**Goal**: Establish real component testing infrastructure

#### Task 1.1: Create Real Component Fixtures
```python
# tests/conftest.py additions

@pytest.fixture
def real_state_manager():
    """REAL StateManager with in-memory SQLite"""
    state = StateManager('sqlite:///:memory:')
    yield state
    state.close()

@pytest.fixture
def real_nl_processor(real_state_manager, mock_llm_realistic):
    """REAL NLCommandProcessor with mock LLM (realistic responses)"""
    return NLCommandProcessor(
        llm_plugin=mock_llm_realistic,
        state_manager=real_state_manager,
        config={'nl_commands': {'enabled': True}}
    )

@pytest.fixture
def mock_llm_realistic():
    """Mock LLM with REALISTIC responses (matches real Qwen output format)"""
    llm = MagicMock()
    # Responses match actual Qwen 2.5 Coder output format
    llm.generate.side_effect = get_realistic_responses
    return llm
```

#### Task 1.2: Create 15 Workflow Integration Tests

**File**: `tests/integration/test_nl_workflows_real_components.py`

```python
"""Real component workflow tests (mock LLM only)"""

class TestProjectWorkflows:
    def test_list_projects_workflow(real_nl_processor, real_state_manager):
        # Create 3 projects
        for i in range(3):
            real_state_manager.create_project(f"Project {i}", "desc", f"/tmp/p{i}")

        # Execute NL command through real processor
        response = real_nl_processor.process("list all projects")

        # Validate complete response structure
        assert response.success
        assert len(response.results.entities) == 3

class TestEpicStoryTaskCreation:
    def test_create_epic_workflow(real_nl_processor, real_state_manager):
        project_id = real_state_manager.create_project("Test", "test", "/tmp/test")

        response = real_nl_processor.process("create epic for user auth")

        # Validate in actual database
        epic_id = response.created_ids[0]
        epic = real_state_manager.get_task(epic_id)
        assert epic.task_type == TaskType.EPIC

    # ... 13 more workflow tests
```

**Success**: 15 workflows pass with real components (mock LLM)

---

### Phase 2: Real LLM Infrastructure (DAY 2-3 - 12 hours) ⭐ CRITICAL

**Goal**: Establish REAL LLM testing capability

#### Task 2.1: Real LLM Fixture & Skip Logic

```python
# tests/conftest.py

@pytest.fixture
def real_ollama_llm():
    """REAL Qwen 2.5 Coder LLM on Ollama

    Skips test if Ollama unavailable (graceful degradation for CI).
    """
    try:
        llm = LocalLLMInterface(
            endpoint='http://10.0.75.1:11434',
            model='qwen2.5-coder:32b',
            temperature=0.1  # Deterministic for testing
        )
        # Health check
        llm.generate("test", max_tokens=5)
        return llm
    except Exception as e:
        pytest.skip(f"Ollama unavailable: {e}")

@pytest.fixture
def real_orchestrator(real_ollama_llm, test_config):
    """REAL Orchestrator with REAL LLM"""
    orchestrator = Orchestrator(config=test_config)
    orchestrator.llm_provider = real_ollama_llm
    return orchestrator
```

#### Task 2.2: Create 20 Real LLM Workflow Tests

**File**: `tests/integration/test_nl_workflows_real_llm.py`

```python
"""Complete workflows with REAL Qwen 2.5 Coder LLM

These are the TRUE acceptance tests. Work is NOT done until these pass.
"""

@pytest.mark.requires_ollama
@pytest.mark.real_llm
@pytest.mark.acceptance
class TestRealLLMProjectWorkflows:

    def test_list_projects_real_llm(real_orchestrator):
        """ACCEPTANCE: User can list projects"""
        # Create real test data
        project_id = real_orchestrator.state_manager.create_project(
            "Tetris Game", "Test project", "/tmp/tetris"
        )

        # Execute with REAL LLM
        result = real_orchestrator.execute_nl_command(
            "show me all projects",
            project_id=project_id
        )

        # Validate user-facing output
        assert result['success'], f"Failed: {result.get('error')}"
        assert 'Tetris Game' in result['message']

    def test_create_epic_real_llm(real_orchestrator):
        """ACCEPTANCE: User can create epic"""
        project_id = real_orchestrator.state_manager.create_project(
            "Test", "Test", "/tmp/test"
        )

        # Natural user input
        result = real_orchestrator.execute_nl_command(
            "create epic for user authentication system",
            project_id=project_id
        )

        # Validate creation
        assert result['success']
        epic_id = result['data']['created_ids'][0]
        epic = real_orchestrator.state_manager.get_task(epic_id)
        assert epic.task_type == TaskType.EPIC
        assert "auth" in epic.title.lower()

    # ... 18 more acceptance tests covering all 20 user stories
```

**Success**: 20 core workflows pass with REAL LLM

---

### Phase 3: Automated Variation Testing Infrastructure (DAY 4-5 - 16 hours) 🚀

**Goal**: Build system for automated 100x variation testing

#### Task 3.1: Variation Generator

**File**: `tests/utils/variation_generator.py`

```python
"""Generate natural language variations for stress testing"""

from typing import List
import random

class NLVariationGenerator:
    """Generate variations of NL commands for stress testing."""

    # Variation templates for each operation
    VARIATION_TEMPLATES = {
        'create_epic': [
            "create epic for {topic}",
            "add an epic for {topic}",
            "I need to create a new epic called {topic}",
            "can you create an epic for the {topic}",
            "please add epic: {topic}",
            "new epic for {topic}",
            "create a new epic about {topic}",
            "I want to create an epic related to {topic}",
            # ... 92 more variations
        ],
        'list_projects': [
            "list all projects",
            "show me all projects",
            "what projects do I have",
            "display all projects",
            "show projects",
            "list projects",
            "can you show me all my projects",
            "I want to see all projects",
            # ... 92 more variations
        ],
        # ... templates for all operations
    }

    def generate_variations(
        self,
        operation: str,
        count: int = 100,
        **kwargs
    ) -> List[str]:
        """Generate N variations of an operation.

        Args:
            operation: Operation type (e.g., 'create_epic')
            count: Number of variations to generate
            **kwargs: Template parameters (e.g., topic="user auth")

        Returns:
            List of variation strings
        """
        templates = self.VARIATION_TEMPLATES.get(operation, [])

        if len(templates) < count:
            # Permute templates with parameter variations
            return self._permute_variations(templates, kwargs, count)

        return [
            template.format(**kwargs)
            for template in random.sample(templates, count)
        ]

    def _permute_variations(
        self,
        templates: List[str],
        params: dict,
        count: int
    ) -> List[str]:
        """Create permutations by varying parameters."""
        # Implementation for parameter permutation
        pass
```

#### Task 3.2: Automated Test Runner

**File**: `tests/stress/automated_variation_tester.py`

```python
"""Automated variation testing with self-documentation of failures"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

class AutomatedVariationTester:
    """Run 100x variations and auto-document results."""

    def __init__(self, orchestrator, output_dir: Path):
        self.orchestrator = orchestrator
        self.output_dir = output_dir
        self.variation_generator = NLVariationGenerator()

    def run_variation_test(
        self,
        operation: str,
        count: int = 100,
        **params
    ) -> Dict[str, Any]:
        """Run N variations of an operation.

        Returns:
            {
                'operation': str,
                'total': int,
                'passed': int,
                'failed': int,
                'failures': List[dict],
                'execution_time_ms': float
            }
        """
        variations = self.variation_generator.generate_variations(
            operation, count, **params
        )

        results = {
            'operation': operation,
            'total': count,
            'passed': 0,
            'failed': 0,
            'failures': [],
            'start_time': datetime.now().isoformat()
        }

        for i, variation in enumerate(variations, 1):
            try:
                result = self.orchestrator.execute_nl_command(
                    variation,
                    project_id=params.get('project_id')
                )

                if result['success']:
                    results['passed'] += 1
                else:
                    results['failed'] += 1
                    results['failures'].append({
                        'variation': variation,
                        'error': result.get('error', 'Unknown'),
                        'iteration': i
                    })

            except Exception as e:
                results['failed'] += 1
                results['failures'].append({
                    'variation': variation,
                    'exception': str(e),
                    'iteration': i
                })

        # Save results
        self._save_results(operation, results)

        # Auto-generate issue report if failures
        if results['failed'] > 0:
            self._generate_issue_report(operation, results)

        return results

    def _save_results(self, operation: str, results: dict):
        """Save test results to JSON"""
        output_file = self.output_dir / f"{operation}_results.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)

    def _generate_issue_report(self, operation: str, results: dict):
        """Auto-generate issue report for failures"""
        report = self.output_dir / f"{operation}_ISSUES.md"

        with open(report, 'w') as f:
            f.write(f"# Variation Testing Issues: {operation}\n\n")
            f.write(f"**Date**: {datetime.now().isoformat()}\n")
            f.write(f"**Pass Rate**: {results['passed']}/{results['total']} ({results['passed']/results['total']*100:.1f}%)\n\n")

            f.write("## Failed Variations\n\n")
            for failure in results['failures']:
                f.write(f"### Iteration {failure['iteration']}\n")
                f.write(f"**Input**: `{failure['variation']}`\n")
                f.write(f"**Error**: {failure.get('error', failure.get('exception'))}\n\n")

            f.write("## Recommended Fixes\n\n")
            # AI-generated fix suggestions
            f.write(self._suggest_fixes(results['failures']))

    def _suggest_fixes(self, failures: List[dict]) -> str:
        """Use LLM to suggest fixes for common failure patterns"""
        # Group failures by error type
        error_groups = self._group_failures_by_error(failures)

        suggestions = []
        for error_type, examples in error_groups.items():
            suggestions.append(f"### {error_type}\n")
            suggestions.append(f"**Affected variations**: {len(examples)}\n")
            suggestions.append(f"**Examples**: {examples[:3]}\n")
            suggestions.append(f"**Suggested Fix**: [AI-generated suggestion]\n\n")

        return "\n".join(suggestions)
```

#### Task 3.3: Stress Test Suite

**File**: `tests/stress/test_automated_variations.py`

```python
"""100x variation stress tests for all workflows"""

import pytest
from pathlib import Path

@pytest.fixture
def variation_tester(real_orchestrator, tmp_path):
    """Automated variation tester"""
    return AutomatedVariationTester(real_orchestrator, tmp_path)

@pytest.mark.stress_test
@pytest.mark.requires_ollama
@pytest.mark.slow
class TestAutomatedVariations:
    """100x variations with REAL LLM - Final acceptance"""

    def test_create_epic_100_variations(variation_tester, real_state_manager):
        """Stress test: Create epic with 100 natural variations"""
        project_id = real_state_manager.create_project("Test", "Test", "/tmp/test")

        results = variation_tester.run_variation_test(
            operation='create_epic',
            count=100,
            project_id=project_id,
            topic='user authentication'
        )

        # Acceptance criteria: 95% success rate
        pass_rate = results['passed'] / results['total']
        assert pass_rate >= 0.95, f"Pass rate {pass_rate:.1%} below 95% threshold"

        # Document failures for improvement
        if results['failed'] > 0:
            pytest.fail(
                f"{results['failed']} variations failed. "
                f"See {variation_tester.output_dir}/create_epic_ISSUES.md"
            )

    def test_list_projects_100_variations(variation_tester, real_state_manager):
        """Stress test: List projects with 100 natural variations"""
        # Create test projects
        for i in range(3):
            real_state_manager.create_project(f"Project {i}", "desc", f"/tmp/p{i}")

        results = variation_tester.run_variation_test(
            operation='list_projects',
            count=100,
            project_id=1
        )

        pass_rate = results['passed'] / results['total']
        assert pass_rate >= 0.95

    # ... 18 more 100x variation tests (one per workflow)
```

**Success**: 95%+ pass rate on 100x variations per workflow

---

### Phase 4: Automated Fix Loop (DAY 6-7 - 16 hours) 🤖

**Goal**: Claude autonomously fixes failures from variation testing

#### Task 4.1: Issue Parser

**File**: `tests/automation/issue_parser.py`

```python
"""Parse variation test failures into actionable issues"""

class VariationIssueParser:
    """Parse failure reports and create fix tasks"""

    def parse_failure_report(self, report_path: Path) -> List[Dict]:
        """Parse ISSUES.md into structured fix tasks"""
        with open(report_path) as f:
            content = f.read()

        # Extract failures
        failures = self._extract_failures(content)

        # Group by error pattern
        grouped = self._group_by_pattern(failures)

        # Create fix tasks
        fix_tasks = []
        for pattern, examples in grouped.items():
            fix_tasks.append({
                'pattern': pattern,
                'affected_count': len(examples),
                'examples': examples[:5],
                'priority': self._calculate_priority(len(examples)),
                'suggested_file': self._infer_fix_location(pattern),
                'suggested_fix': self._suggest_fix_approach(pattern, examples)
            })

        return fix_tasks
```

#### Task 4.2: Automated Fix Executor

**File**: `tests/automation/automated_fixer.py`

```python
"""Claude-driven automated fix execution"""

class AutomatedFixer:
    """Execute fixes autonomously with Claude"""

    def __init__(self, claude_code_path: str):
        self.claude_code = claude_code_path

    def execute_fix_loop(
        self,
        issue_report: Path,
        max_iterations: int = 5
    ) -> Dict:
        """Autonomous fix loop:

        1. Parse issues
        2. Generate fix with Claude
        3. Apply fix
        4. Re-run tests
        5. Repeat until pass or max iterations
        """
        iteration = 0

        while iteration < max_iterations:
            # Parse current failures
            parser = VariationIssueParser()
            fix_tasks = parser.parse_failure_report(issue_report)

            if not fix_tasks:
                return {'success': True, 'iterations': iteration}

            # Pick highest priority task
            task = fix_tasks[0]

            # Generate fix with Claude
            fix_prompt = self._create_fix_prompt(task)
            fix_result = self._execute_claude_fix(fix_prompt)

            # Apply fix
            self._apply_fix(fix_result)

            # Re-run variation tests
            retest_result = self._rerun_tests(task['pattern'])

            if retest_result['passed'] == retest_result['total']:
                # Fix worked, move to next issue
                continue

            iteration += 1

        return {'success': False, 'iterations': iteration, 'remaining_issues': len(fix_tasks)}

    def _create_fix_prompt(self, task: dict) -> str:
        """Create Claude Code prompt for fix"""
        return f"""
Fix NL variation test failure:

**Pattern**: {task['pattern']}
**Affected**: {task['affected_count']} variations
**Examples**:
{chr(10).join(f"- {ex}" for ex in task['examples'])}

**Suspected File**: {task['suggested_file']}
**Suggested Approach**: {task['suggested_fix']}

Please:
1. Analyze the failure pattern
2. Identify root cause in the code
3. Implement fix
4. Verify fix doesn't break existing tests
5. Document what was changed

After fix, the variation tests will re-run automatically.
"""

    def _execute_claude_fix(self, prompt: str) -> dict:
        """Execute fix with Claude Code"""
        # Call Claude Code CLI with prompt
        result = subprocess.run(
            [self.claude_code, 'code', '--prompt', prompt],
            capture_output=True,
            text=True
        )
        return {'stdout': result.stdout, 'returncode': result.returncode}
```

#### Task 4.3: Continuous Fix Loop

**File**: `scripts/automated_fix_loop.py`

```python
"""Continuous automated testing and fixing"""

def run_automated_fix_loop():
    """Main loop: Test → Document → Fix → Re-test"""

    orchestrator = setup_real_orchestrator()
    variation_tester = AutomatedVariationTester(orchestrator, Path('test_results'))
    automated_fixer = AutomatedFixer('/path/to/claude-code')

    # Operations to test
    operations = [
        'create_epic', 'create_story', 'create_task',
        'list_projects', 'list_epics', 'list_stories', 'list_tasks',
        'update_task', 'delete_task',
        # ... all 20 operations
    ]

    for operation in operations:
        print(f"\n{'='*60}")
        print(f"Testing: {operation}")
        print(f"{'='*60}\n")

        # Run 100x variations
        results = variation_tester.run_variation_test(operation, count=100)

        # Check pass rate
        pass_rate = results['passed'] / results['total']
        print(f"Pass rate: {pass_rate:.1%}")

        if pass_rate < 0.95:
            print(f"⚠️  Below 95% threshold. Starting automated fixes...")

            # Automated fix loop
            issue_report = Path(f'test_results/{operation}_ISSUES.md')
            fix_result = automated_fixer.execute_fix_loop(issue_report, max_iterations=5)

            if fix_result['success']:
                print(f"✅ Fixed all issues in {fix_result['iterations']} iterations")
            else:
                print(f"❌ Could not fix all issues. {fix_result['remaining_issues']} remain.")
                print(f"Manual intervention required.")
        else:
            print(f"✅ Passed with {pass_rate:.1%}")

if __name__ == '__main__':
    run_automated_fix_loop()
```

**Success**: Autonomous fix loop reduces manual debugging by 80%

---

## Implementation Timeline

```
┌─────────────────────────────────────────────────────────────┐
│ Week 1: Foundation                                          │
├─────────────────────────────────────────────────────────────┤
│ Day 1-2: Phase 0 + Phase 1 (Fix broken + Component tests)  │
│ Day 3-4: Phase 2 (Real LLM infrastructure)                 │
│ Day 5:   Phase 2 (20 real LLM workflow tests)              │
├─────────────────────────────────────────────────────────────┤
│ Week 2: Automation                                          │
├─────────────────────────────────────────────────────────────┤
│ Day 6-7: Phase 3 (Variation testing infrastructure)        │
│ Day 8-9: Phase 3 (100x variation test suite)               │
│ Day 10:  Phase 4 (Automated fix loop)                      │
└─────────────────────────────────────────────────────────────┘
```

**Total Effort**: 10 days (80 hours)

---

## Success Metrics

### Phase Completion Criteria

| Phase | Mock Tests | Real Component Tests | Real LLM Tests | Variation Tests | Done? |
|-------|------------|----------------------|----------------|-----------------|-------|
| Phase 0 | 100% pass | - | - | - | ✅ NOT DONE |
| Phase 1 | 100% pass | 100% pass (15 tests) | - | - | ✅ NOT DONE |
| Phase 2 | 100% pass | 100% pass | **100% pass (20 tests)** | - | **⭐ DONE** |
| Phase 3 | 100% pass | 100% pass | 100% pass | **95%+ pass (20x100 tests)** | **⭐ DONE** |
| Phase 4 | 100% pass | 100% pass | 100% pass | 98%+ pass + auto-fix | **🚀 DONE** |

### Acceptance Criteria (Work is "DONE")

```
✅ Phase 2 Complete:
  - 20 core workflows pass with REAL Qwen 2.5 Coder LLM
  - No mock LLM in acceptance tests
  - Tests run against real Ollama endpoint
  - User workflows validated end-to-end

✅ Phase 3 Complete:
  - 2000 total variations tested (20 workflows × 100 variations)
  - 95%+ pass rate on all workflows
  - Automated issue documentation
  - Failure patterns identified

✅ Phase 4 Complete:
  - 98%+ pass rate on variations
  - Automated fix loop reduces manual work by 80%
  - Claude can autonomously improve NL pipeline
```

---

## Configuration

### Test Execution Modes

```yaml
# pytest.ini additions

[pytest]
markers =
    real_llm: Tests using real Ollama/Qwen LLM (slow, requires Ollama)
    stress_test: 100x variation stress tests (very slow)
    acceptance: Acceptance tests (must pass for "done")
    mock_only: Tests using only mocks (fast, for TDD)

# Run only fast mock tests (TDD)
# pytest -m "mock_only"

# Run real component integration (pre-commit)
# pytest tests/integration/test_nl_workflows_real_components.py

# Run REAL LLM acceptance tests (pre-release)
# pytest -m "real_llm and acceptance"

# Run stress tests (nightly)
# pytest -m "stress_test"
```

### Environment Setup

```bash
# Required environment variables
export OLLAMA_ENDPOINT=http://10.0.75.1:11434
export OLLAMA_MODEL=qwen2.5-coder:32b
export CLAUDE_CODE_PATH=/path/to/claude-code

# Test database
export TEST_DATABASE_URL=sqlite:///:memory:

# Variation testing
export VARIATION_OUTPUT_DIR=./test_results
export AUTO_FIX_MAX_ITERATIONS=5
```

---

## Test Execution Strategy

### Development Cycle (TDD)

```bash
# Step 1: Write unit test with mocks (fast iteration)
pytest tests/nl/test_new_feature.py -m mock_only -vv

# Step 2: Write component integration test (real components, mock LLM)
pytest tests/integration/test_nl_workflows_real_components.py::test_new_feature -vv

# Step 3: Write REAL LLM acceptance test
pytest tests/integration/test_nl_workflows_real_llm.py::test_new_feature_real_llm -m "real_llm and acceptance" -vv

# Step 4: Run variation stress test
pytest tests/stress/test_automated_variations.py::test_new_feature_100_variations -m stress_test
```

### Pre-Commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

echo "Running pre-commit tests..."

# Fast: Mock-based unit tests
pytest tests/nl/ -m "mock_only" --maxfail=1

# Medium: Real component integration
pytest tests/integration/test_nl_workflows_real_components.py --maxfail=1

# Skip real LLM tests (too slow for pre-commit)
# Those run in CI/CD

if [ $? -eq 0 ]; then
    echo "✅ All pre-commit tests passed"
    exit 0
else
    echo "❌ Tests failed. Fix before committing."
    exit 1
fi
```

### CI/CD Pipeline (GitHub Actions)

```yaml
name: NL Testing Pipeline

on: [push, pull_request]

jobs:
  mock-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: pytest -m "mock_only" --cov=src/nl

  component-integration:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: pytest tests/integration/test_nl_workflows_real_components.py

  real-llm-acceptance:
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request'
    steps:
      - uses: actions/checkout@v3
      - name: Setup Ollama
        run: |
          docker run -d -p 11434:11434 ollama/ollama
          docker exec ollama ollama pull qwen2.5-coder:32b
      - run: pytest -m "real_llm and acceptance" --maxfail=5

  stress-testing:
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v3
      - name: Setup Ollama
        run: |
          docker run -d -p 11434:11434 ollama/ollama
          docker exec ollama ollama pull qwen2.5-coder:32b
      - run: pytest -m "stress_test" --tb=short
      - name: Upload variation reports
        if: failure()
        uses: actions/upload-artifact@v3
        with:
          name: variation-test-results
          path: test_results/
```

---

## Migration from Current State

### Current State (Before)
- 815 unit tests (88% coverage) - mostly mocks
- 10/12 integration tests failing
- 3/10 smoke tests failing
- 0 real LLM tests running
- 0 variation tests

### Target State (After Phase 4)
- 815+ unit tests (keep existing, fix broken)
- 15 real component integration tests
- 20 real LLM acceptance tests (⭐ "done" criteria)
- 2000 variation stress tests (20 × 100)
- Automated fix loop infrastructure

### Migration Path

**Week 1**:
- Fix broken tests → Baseline established
- Add real component tests → Integration validated
- Add real LLM tests → Acceptance criteria defined

**Week 2**:
- Add variation infrastructure → Stress testing enabled
- Run 100x variations → Identify edge cases
- Build automated fix loop → Self-improving system

---

## Benefits of This Approach

### Compared to Mock-Heavy Testing

| Aspect | Mock-Heavy (Old) | Real-First (New) | Benefit |
|--------|------------------|------------------|---------|
| **Bug Detection** | Unit bugs only | Integration bugs | Catch real issues |
| **Confidence** | False positives | True validation | Ship with confidence |
| **Coverage** | 88% lines | 95%+ workflows | User-centric metrics |
| **Maintenance** | High (mock drift) | Low (real behavior) | Less brittle tests |
| **Speed** | Fast (mocks) | Slower (real LLM) | But catches real bugs |

### Automated Variation Testing Benefits

1. **Discover Edge Cases**: 100x variations uncover edge cases manual testing misses
2. **NL Pipeline Robustness**: Validates system handles natural language flexibility
3. **Regression Prevention**: Variations become regression suite
4. **Self-Improving**: Automated fix loop continuously improves pipeline
5. **User Experience**: Tests match how real users phrase commands

---

## Conclusion

**Key Philosophy Shift**:

```
OLD: Unit tests pass → Integration tests pass → Ship (but real workflows broken)
NEW: Mock tests pass → Component tests pass → REAL LLM tests pass →
     100x variations pass → THEN ship
```

**Definition of "Done"**:
- ✅ Phase 2: 20 core workflows pass with REAL LLM
- ✅ Phase 3: 95%+ pass rate on 100x variations per workflow
- ✅ Phase 4: Automated fix loop maintains 98%+ pass rate

**Expected Outcome**:
- User workflows work in production (not just in tests)
- NL pipeline robust to natural language variations
- Bugs caught before users see them
- System self-improves via automated fix loop

---

**Status**: ✅ Plan Complete - Ready for Implementation
**Next Step**: Begin Phase 0 (Fix Broken Tests)
**Estimated Timeline**: 10 days (80 hours) to full automation
