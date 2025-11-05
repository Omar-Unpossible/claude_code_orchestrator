# M9 Implementation Plan: Core Enhancements (v1.2)

**Status**: 🚧 In Progress
**Timeline**: November 2-23, 2025 (3 weeks)
**Target**: Production-ready enhancements for reliability, workflows, and usability

## Executive Summary

M9 adds four critical enhancements to make Obra production-ready:

1. **Retry Logic with Exponential Backoff** - Gracefully handle transient failures
2. **Task Dependency System** - Enable complex workflows with dependency graphs
3. **Git Auto-Integration** - Automatic commits with LLM-generated messages
4. **Configuration Profiles** - Pre-configured settings for different project types

## Current Status

**Pre-M9 Metrics**:
- Total Code: ~15,600 lines (8,900 production + 4,700 tests + 2,000 docs)
- Test Coverage: 88% overall (433+ tests)
- All M0-M8 milestones complete

**M9 Targets**:
- Additional Code: ~650 lines production + 270 tests = ~920 lines
- Post-M9 Total: ~16,520 lines
- Post-M9 Tests: 703 total tests
- Coverage Goal: Maintain ≥88% overall, ≥90% for M9 modules

## Phase Breakdown

### Phase 1: Documentation & Planning (Days 1-2) ✅ COMPLETE

**Status**: 100% complete - **November 4, 2025**

**Completed**:
- ✅ M9 implementation plan created (792 lines)
- ✅ CLAUDE.md updated with M9 status
- ✅ Profile directory created (`config/profiles/`)
- ✅ 6 profile YAML files created (~10,000 lines)
- ✅ ADR-008: Retry Logic (8,441 lines)
- ✅ ADR-009: Task Dependencies (23,998 lines)
- ✅ ADR-010: Git Integration (21,769 lines)
- ✅ ARCHITECTURE.md updated with M9 features
- ✅ Configuration Profiles Guide created (765 lines)
- ✅ GETTING_STARTED.md updated with profile usage
- ✅ Phase 1 completion summary created

**Metrics**:
- Total documentation: ~66,000+ lines
- Time investment: ~21 hours (2.5 days)
- Files created/updated: 14

**Deliverables**:
- [x] `docs/development/M9_IMPLEMENTATION_PLAN.md` (this file)
- [ ] `docs/decisions/ADR-008-retry-logic.md`
- [ ] `docs/decisions/ADR-009-task-dependencies.md`
- [ ] `docs/decisions/ADR-010-git-integration.md`
- [ ] Updated `docs/architecture/ARCHITECTURE.md`
- [ ] Updated `docs/guides/GETTING_STARTED.md` with profile usage

---

### Phase 2: Configuration Profiles (Days 2-3)

**Goal**: Enable profile-based configuration for different project types

**Implementation Steps**:

1. **Update Config Class** (~100 lines)
   - Add `load_profile()` method to Config class
   - Implement profile inheritance (profile extends default_config)
   - Add profile validation
   - Support CLI profile override

2. **Profile Files** (DONE - 6 files exist)
   - ✅ `python_project.yaml` - Python projects
   - ✅ `web_app.yaml` - Web applications
   - ✅ `ml_project.yaml` - Machine learning projects
   - ✅ `microservice.yaml` - Microservices
   - ✅ `minimal.yaml` - Minimal configuration
   - ✅ `production.yaml` - Production settings

3. **CLI Integration** (~50 lines)
   - Add `--profile` flag to CLI
   - Add `--set` flag for runtime overrides
   - Example: `obra --profile python_project --set agent.type=local task execute 1`

4. **Testing** (~80 tests)
   - Test profile loading
   - Test profile inheritance
   - Test CLI profile flag
   - Test invalid profile handling
   - Test runtime overrides

**Files to Create/Modify**:
- `src/core/config.py` - Add profile loading
- `src/cli.py` - Add `--profile` and `--set` flags
- `tests/test_config_profiles.py` - Profile tests

**Coverage Target**: ≥90%

---

### Phase 3: Retry Logic with Exponential Backoff (Day 3)

**Goal**: Handle transient failures gracefully with intelligent retry

**Implementation Steps**:

1. **Create RetryManager** (~150 lines)
   ```python
   class RetryManager:
       def __init__(self, config: dict):
           self.max_retries = config.get('max_retries', 3)
           self.base_delay = config.get('base_delay', 1.0)
           self.max_delay = config.get('max_delay', 60.0)
           self.backoff_factor = config.get('backoff_factor', 2.0)
           self.jitter = config.get('jitter', True)

       def execute_with_retry(self, func, *args, **kwargs):
           """Execute function with exponential backoff retry"""

       def is_retryable(self, error: Exception) -> bool:
           """Determine if error is retryable"""
   ```

2. **Error Classification** (~50 lines)
   - Retryable: Rate limits, timeouts, network errors
   - Non-retryable: Authentication, validation, syntax errors
   - Create error type registry

3. **Integration Points** (~100 lines)
   - Wrap agent calls (ClaudeCodeLocalAgent, ClaudeCodeSSHAgent)
   - Wrap LLM calls (OllamaInterface)
   - Add retry metrics to state

4. **Configuration** (~50 lines)
   ```yaml
   retry:
     enabled: true
     max_retries: 3
     base_delay: 1.0
     max_delay: 60.0
     backoff_factor: 2.0
     jitter: true
     retryable_errors:
       - RateLimitError
       - TimeoutError
       - NetworkError
   ```

5. **Testing** (~90 tests)
   - Test exponential backoff calculation
   - Test jitter addition
   - Test retryable vs non-retryable errors
   - Test max retries enforcement
   - Test successful retry after failure
   - Integration tests with mock agent

**Files to Create/Modify**:
- `src/utils/retry_manager.py` - New RetryManager class
- `src/core/exceptions.py` - Add retryable error types
- `src/agents/claude_code_local.py` - Add retry wrapper
- `src/llm/ollama_interface.py` - Add retry wrapper
- `config/default_config.yaml` - Add retry config
- `tests/test_retry_manager.py` - Retry tests

**Coverage Target**: ≥90%

---

### Phase 4: Git Auto-Integration (Days 4-5)

**Goal**: Automatic git operations with LLM-generated semantic commit messages

**Implementation Steps**:

1. **Create GitManager** (~200 lines)
   ```python
   class GitManager:
       def __init__(self, working_dir: str, config: dict):
           self.repo = git.Repo(working_dir)
           self.config = config
           self.llm = None  # For commit message generation

       def auto_commit(self, task: Task, changes: List[str]) -> str:
           """Auto-commit with LLM-generated message"""

       def create_task_branch(self, task: Task) -> str:
           """Create branch: obra/task-{id}-{slug}"""

       def create_pr(self, task: Task, branch: str) -> str:
           """Create PR via gh CLI (optional)"""

       def rollback_to_commit(self, commit_hash: str):
           """Rollback to specific commit"""
   ```

2. **LLM Commit Message Generation** (~100 lines)
   - Analyze changed files
   - Generate semantic commit message
   - Format: `type(scope): description\n\nBody\n\nFooter`
   - Types: feat, fix, refactor, docs, test, chore

3. **Integration with Orchestrator** (~100 lines)
   - Auto-commit after successful task completion
   - Optional branch-per-task mode
   - Optional PR creation mode
   - Add git metadata to state

4. **Configuration** (~50 lines)
   ```yaml
   git:
     enabled: true
     auto_commit: true
     commit_strategy: per_task  # per_task, per_milestone, manual
     branch_per_task: false
     branch_prefix: "obra/task-"
     create_pr: false
     pr_template: ".github/PULL_REQUEST_TEMPLATE.md"
   ```

5. **Testing** (~100 tests)
   - Test commit message generation
   - Test auto-commit
   - Test branch creation
   - Test PR creation (mock gh CLI)
   - Test rollback
   - Integration tests with git repo

**Files to Create/Modify**:
- `src/utils/git_manager.py` - New GitManager class
- `src/orchestrator.py` - Integrate git operations
- `src/core/models.py` - Add git metadata to Task model
- `config/default_config.yaml` - Add git config
- `tests/test_git_manager.py` - Git tests
- `tests/test_integration_git.py` - Integration tests

**Coverage Target**: ≥90%

**Dependencies**: GitPython (add to requirements.txt)

---

### Phase 5: Task Dependency System (Days 6-10)

**Goal**: Enable complex workflows with task dependencies and proper execution order

**Implementation Steps**:

1. **Database Migration** (~50 lines)
   - Add `depends_on` JSON field to Task table
   - Create migration: `alembic/versions/xxx_add_task_dependencies.py`
   - Example: `depends_on = [1, 3, 5]` (task IDs)

2. **Update Task Model** (~50 lines)
   ```python
   class Task:
       # ... existing fields ...
       depends_on: List[int] = []  # List of task IDs
       dependents: List[int] = []  # Tasks that depend on this
       is_blocked: bool = False  # Blocked by incomplete dependencies
   ```

3. **Create DependencyResolver** (~200 lines)
   ```python
   class DependencyResolver:
       def __init__(self, state_manager: StateManager):
           self.state = state_manager

       def build_dependency_graph(self, tasks: List[Task]) -> nx.DiGraph:
           """Build directed graph of task dependencies"""

       def topological_sort(self, tasks: List[Task]) -> List[Task]:
           """Return tasks in optimal execution order"""

       def detect_cycles(self, tasks: List[Task]) -> List[List[int]]:
           """Detect circular dependencies"""

       def get_ready_tasks(self, tasks: List[Task]) -> List[Task]:
           """Get tasks with all dependencies complete"""

       def handle_cascading_failure(self, failed_task: Task):
           """Mark dependent tasks as blocked"""
   ```

4. **Update StateManager** (~100 lines)
   - Add `add_task_dependency(task_id, depends_on_id)`
   - Add `get_task_dependencies(task_id)`
   - Add `get_dependent_tasks(task_id)`
   - Add `get_ready_tasks(project_id)`

5. **Integration with Orchestrator** (~100 lines)
   - Check dependencies before task execution
   - Block tasks with incomplete dependencies
   - Handle cascading failures
   - Generate dependency visualization

6. **CLI Integration** (~50 lines)
   - Add `--depends-on` flag to `task create`
   - Add `task dependencies` command
   - Example: `obra task create "Task B" --depends-on 1,3`

7. **Configuration** (~50 lines)
   ```yaml
   task_dependencies:
     enabled: true
     max_depth: 10  # Maximum dependency chain depth
     allow_cycles: false  # Strict mode
     cascade_failures: true  # Block dependents on failure
   ```

8. **Testing** (~100 tests)
   - Test dependency graph building
   - Test topological sort
   - Test cycle detection
   - Test ready task selection
   - Test cascading failures
   - Integration tests with multi-task workflows

**Files to Create/Modify**:
- `alembic/versions/xxx_add_task_dependencies.py` - Database migration
- `src/core/models.py` - Update Task model
- `src/orchestration/dependency_resolver.py` - New DependencyResolver class
- `src/core/state.py` - Add dependency methods
- `src/orchestrator.py` - Integrate dependency checking
- `src/cli.py` - Add dependency CLI commands
- `config/default_config.yaml` - Add dependency config
- `tests/test_dependency_resolver.py` - Dependency tests
- `tests/test_integration_dependencies.py` - Integration tests

**Coverage Target**: ≥90%

**Dependencies**: networkx (add to requirements.txt)

---

### Phase 6: Integration Testing (Days 11-13)

**Goal**: Comprehensive testing of all M9 features together

**Test Scenarios**:

1. **Retry Integration** (~40 tests)
   - Agent retry with exponential backoff
   - LLM retry with jitter
   - Non-retryable error handling
   - Max retries enforcement
   - Retry metrics in state

2. **Git Integration** (~40 tests)
   - Auto-commit after task completion
   - LLM-generated commit messages
   - Branch-per-task workflow
   - PR creation workflow
   - Rollback workflow

3. **Dependency Integration** (~40 tests)
   - Multi-task workflow with dependencies
   - Parallel task execution (independent tasks)
   - Cascading failure handling
   - Cycle detection and rejection
   - Dependency visualization

4. **Profile Integration** (~30 tests)
   - Load profile from CLI
   - Profile inheritance
   - Runtime overrides
   - Profile validation
   - Profile-specific settings

5. **Combined Workflows** (~30 tests)
   - Profile + Retry + Git workflow
   - Profile + Dependencies workflow
   - All features together (E2E)
   - Performance benchmarks
   - Regression testing

**Files to Create**:
- `tests/integration/test_retry_integration.py`
- `tests/integration/test_git_integration.py`
- `tests/integration/test_dependency_integration.py`
- `tests/integration/test_profile_integration.py`
- `tests/integration/test_m9_e2e.py`

**Coverage Target**: ≥90% for integration tests

---

### Phase 7: Documentation (Days 14-15)

**Goal**: Complete user and developer documentation for M9

**Deliverables**:

1. **M9 Completion Summary** (~500 lines)
   - `docs/development/milestones/M9_COMPLETION_SUMMARY.md`
   - Implementation details
   - Test results
   - Coverage metrics
   - Known issues
   - Future improvements

2. **User Guides** (~300 lines)
   - `docs/guides/RETRY_LOGIC_GUIDE.md` - Using retry configuration
   - `docs/guides/TASK_DEPENDENCIES_GUIDE.md` - Creating dependent tasks
   - `docs/guides/GIT_INTEGRATION_GUIDE.md` - Git auto-commit workflows
   - `docs/guides/CONFIGURATION_PROFILES_GUIDE.md` - Profile usage

3. **Architecture Updates** (~200 lines)
   - Update `docs/architecture/ARCHITECTURE.md`
   - Add M9 features to system design
   - Update data flow diagrams
   - Update component diagrams

4. **README Updates** (~50 lines)
   - Update feature list with M9 features
   - Add M9 status badge
   - Add quick examples

5. **QUICK_START.md Updates** (~100 lines)
   - Add profile usage examples
   - Add dependency workflow example
   - Add git integration example

6. **CLAUDE.md Updates** (~50 lines)
   - Mark M9 as complete
   - Update status metrics
   - Add M9 pitfalls section

**Total Documentation**: ~1,200 lines

---

## Implementation Details

### 1. Retry Logic with Exponential Backoff

**Design Principles**:
- **Retryable vs Non-Retryable**: Clear error classification
- **Exponential Backoff**: 1s → 2s → 4s → 8s → 16s (configurable)
- **Jitter**: Add randomness to prevent thundering herd
- **Max Delay Cap**: Prevent excessive wait times
- **Transparency**: Log all retry attempts

**Algorithm**:
```python
delay = min(base_delay * (backoff_factor ** attempt), max_delay)
if jitter:
    delay *= (0.5 + random.random())  # 50-150% of calculated delay
```

**Error Classification**:
```python
RETRYABLE_ERRORS = {
    'RateLimitError': True,
    'TimeoutError': True,
    'NetworkError': True,
    'ConnectionError': True,
}

NON_RETRYABLE_ERRORS = {
    'AuthenticationError': False,
    'ValidationError': False,
    'SyntaxError': False,
    'PermissionError': False,
}
```

---

### 2. Task Dependency System

**Design Principles**:
- **Directed Acyclic Graph (DAG)**: No cycles allowed
- **Topological Sort**: Optimal execution order
- **Lazy Evaluation**: Check dependencies at execution time
- **Cascading Failures**: Block dependents on failure
- **Visualization**: Generate dependency graphs

**Data Structure**:
```python
# Task 1 (no dependencies)
# Task 2 (depends on Task 1)
# Task 3 (depends on Task 1)
# Task 4 (depends on Task 2, 3)

Dependency Graph:
1 → 2 → 4
  → 3 ↗

Execution Order: [1, 2, 3, 4] or [1, 3, 2, 4]
```

**Database Schema**:
```sql
ALTER TABLE tasks ADD COLUMN depends_on JSON DEFAULT '[]';

-- Example: Task 4 depends on Task 2 and Task 3
UPDATE tasks SET depends_on = '[2, 3]' WHERE id = 4;
```

---

### 3. Git Auto-Integration

**Design Principles**:
- **Semantic Commits**: Follow conventional commit format
- **LLM-Generated Messages**: Context-aware descriptions
- **Optional Branching**: Branch-per-task or single branch
- **Optional PR Creation**: Integrate with gh CLI
- **Rollback Support**: Complement checkpoint system

**Commit Message Format**:
```
type(scope): short description

Longer description explaining what changed and why.

Task-ID: 123
Generated-By: Obra v1.2
```

**Workflow**:
```python
1. Task completes successfully
2. Orchestrator calls GitManager.auto_commit()
3. GitManager generates commit message via LLM
4. GitManager stages changes and commits
5. (Optional) GitManager creates branch
6. (Optional) GitManager creates PR via gh CLI
7. Commit hash saved to Task metadata
```

---

### 4. Configuration Profiles

**Design Principles**:
- **Inheritance**: Profiles extend default_config.yaml
- **Override**: Profile values override defaults
- **Runtime Override**: CLI flags override profile
- **Validation**: Validate profile structure
- **Extensibility**: Easy to add custom profiles

**Profile Inheritance**:
```yaml
# config/default_config.yaml (base)
agent:
  type: local
  response_timeout: 7200

# config/profiles/python_project.yaml (extends)
agent:
  response_timeout: 3600  # Override

# Result: python_project gets all defaults + overrides
```

**CLI Usage**:
```bash
# Use profile
obra --profile python_project task execute 1

# Override specific value
obra --profile python_project --set agent.type=ssh task execute 1

# Multiple overrides
obra --profile production --set retry.max_retries=5 --set git.enabled=false task execute 1
```

---

## Testing Strategy

### Unit Tests (~180 tests)
- RetryManager: 90 tests
- DependencyResolver: 100 tests
- GitManager: 100 tests
- Config profiles: 80 tests

### Integration Tests (~180 tests)
- Retry integration: 40 tests
- Git integration: 40 tests
- Dependency integration: 40 tests
- Profile integration: 30 tests
- Combined workflows: 30 tests

### Total: ~270 new tests

### Coverage Targets
- Overall: ≥88% (maintain)
- M9 modules: ≥90%
- Critical paths: ≥95%

---

## Dependencies

**New Python Packages**:
```txt
GitPython==3.1.40  # Git operations
networkx==3.2.1    # Dependency graph
```

**System Dependencies**:
```bash
git                # Version control
gh                 # GitHub CLI (optional, for PR creation)
```

---

## Configuration

**New Config Sections**:

```yaml
# Retry Logic
retry:
  enabled: true
  max_retries: 3
  base_delay: 1.0
  max_delay: 60.0
  backoff_factor: 2.0
  jitter: true
  retryable_errors:
    - RateLimitError
    - TimeoutError
    - NetworkError

# Git Integration
git:
  enabled: true
  auto_commit: true
  commit_strategy: per_task  # per_task, per_milestone, manual
  branch_per_task: false
  branch_prefix: "obra/task-"
  create_pr: false
  pr_template: ".github/PULL_REQUEST_TEMPLATE.md"

# Task Dependencies
task_dependencies:
  enabled: true
  max_depth: 10
  allow_cycles: false
  cascade_failures: true

# Configuration Profiles
profiles:
  default_profile: null  # No profile by default
  profile_dir: "config/profiles"
```

---

## Risks and Mitigations

### Risk 1: Git operations slow down execution
**Mitigation**:
- Make git operations async
- Add config flag to disable
- Batch commits (commit at milestone end)

### Risk 2: Dependency resolution complexity
**Mitigation**:
- Limit max dependency depth (default: 10)
- Clear error messages for cycles
- Visualization tools for debugging

### Risk 3: LLM-generated commit messages quality
**Mitigation**:
- Fallback to template-based messages
- Add commit message validation
- Allow manual override

### Risk 4: Profile configuration conflicts
**Mitigation**:
- Clear inheritance rules
- Validation on load
- Error messages show conflict source

---

## Success Criteria

### Functional Requirements
- ✅ All M9 features implemented
- ✅ All tests passing
- ✅ Coverage ≥88% overall, ≥90% for M9 modules
- ✅ No regressions in existing features

### Non-Functional Requirements
- ✅ Retry logic reduces transient failure impact
- ✅ Task dependencies enable complex workflows
- ✅ Git integration provides audit trail
- ✅ Profiles simplify project setup

### Documentation Requirements
- ✅ Complete user guides
- ✅ Complete developer documentation
- ✅ Architecture decision records
- ✅ Code examples and tutorials

---

## Timeline Summary

| Phase | Duration | Status | Deliverables |
|-------|----------|--------|--------------|
| 1. Documentation & Planning | Days 1-2 | 🔄 In Progress | M9 plan, ADRs, doc updates |
| 2. Configuration Profiles | Days 2-3 | 📋 Pending | Profile loading, CLI, tests |
| 3. Retry Logic | Day 3 | 📋 Pending | RetryManager, integration, tests |
| 4. Git Integration | Days 4-5 | 📋 Pending | GitManager, auto-commit, tests |
| 5. Task Dependencies | Days 6-10 | 📋 Pending | DependencyResolver, migration, tests |
| 6. Integration Testing | Days 11-13 | 📋 Pending | E2E tests, benchmarks |
| 7. Documentation | Days 14-15 | 📋 Pending | Guides, summaries, updates |

**Total**: 15 days (3 weeks)

---

## Post-M9 Roadmap

### v1.3 - Priority Enhancements
- Budget & Cost Controls (P0)
- Metrics & Reporting System (P0)
- Checkpoint System (P0)
- Prompt Template Library (P0)
- Escalation Levels (P0)

### v1.4+ - Future Enhancements
- Web UI dashboard
- Multi-project orchestration
- Pattern learning
- Monitoring integration

### v2.0 - Advanced Features
- Distributed architecture
- Multi-agent collaboration
- Advanced ML patterns

---

## Appendix

### A. Code Statistics

**Pre-M9**:
- Production code: 8,900 lines
- Test code: 4,700 lines
- Documentation: 2,000 lines
- Total: 15,600 lines

**M9 Additions**:
- Production code: ~650 lines
  - RetryManager: 150 lines
  - DependencyResolver: 200 lines
  - GitManager: 200 lines
  - Config profiles: 100 lines
- Test code: ~270 tests (~800 lines)
- Documentation: ~1,200 lines
- Total new: ~2,650 lines

**Post-M9 Total**: ~18,250 lines

### B. Test Distribution

| Module | Unit Tests | Integration Tests | Total |
|--------|-----------|------------------|-------|
| RetryManager | 70 | 20 | 90 |
| DependencyResolver | 80 | 20 | 100 |
| GitManager | 80 | 20 | 100 |
| Config Profiles | 60 | 20 | 80 |
| Combined Workflows | - | 30 | 30 |
| **Total** | **290** | **110** | **400** |

### C. Coverage Breakdown

| Module | Target | Expected |
|--------|--------|----------|
| RetryManager | ≥90% | 92% |
| DependencyResolver | ≥90% | 94% |
| GitManager | ≥90% | 91% |
| Config Profiles | ≥90% | 93% |
| Integration | ≥85% | 87% |
| **Overall** | **≥88%** | **89%** |

---

**Last Updated**: 2025-11-04
**Author**: Claude Code (Orchestrated by Obra)
**Version**: 1.0.0
