# Agile Hierarchy Completion - Fresh Session Seed Prompt

**Purpose**: Start a new Claude Code session to complete Agile/Scrum hierarchy implementation
**Context**: Phase 1 (Core Implementation) is 100% complete, Phase 2 (Production Readiness) needs completion
**Estimated Time**: 16 hours (2 days)
**Completion Plan**: `docs/development/AGILE_HIERARCHY_COMPLETION_PLAN.md`

---

## Quick Start Command

Copy-paste this into a fresh Claude Code session:

```
Read "docs/development/AGILE_HIERARCHY_COMPLETION_PLAN.md" and implement Phase 2: Production Readiness. Follow the detailed implementation steps, creating comprehensive tests, enhanced CLI commands, and updated documentation. Start with Epic 1 (Code Quality & Consistency) and work through Epic 4 (Documentation Updates) sequentially.
```

---

## Context Summary

### What's Already Done ✅

**Phase 1: Core Implementation (24 hours, 100% complete)**

1. **Database Schema** (`src/core/models.py`)
   - TaskType enum: EPIC, STORY, TASK, SUBTASK
   - Task model: Added task_type, epic_id, story_id fields
   - Milestone model: Complete with relationships
   - Fixed: SQLAlchemy relationship ambiguity with foreign_keys parameter

2. **StateManager** (`src/core/state.py`)
   - `create_epic()` - Create large features (line ~739)
   - `create_story()` - Create user deliverables (line ~773)
   - `get_epic_stories()` - Query stories in epic (line ~820)
   - `get_story_tasks()` - Query tasks in story (line ~841)
   - `create_milestone()` - Create checkpoints (line ~862)
   - `check_milestone_completion()` - Validate requirements (line ~927)
   - `achieve_milestone()` - Mark as achieved (line ~946)

3. **Orchestrator** (`src/orchestrator.py`)
   - `execute_epic()` - Execute all stories in epic (line ~667)
   - Validates epic exists and is correct type
   - Gets stories, executes sequentially

4. **CLI Commands** (`src/cli.py`)
   - `obra epic create/execute` (lines ~383-450)
   - `obra story create` (lines ~457-489)
   - `obra milestone create/check/achieve` (lines ~496-585)

5. **Migration** (`migrations/versions/003_agile_hierarchy.sql`)
   - Complete migration with rollback instructions
   - Adds columns, indexes, milestone table

6. **Tests** (`tests/test_agile_hierarchy_basic.py`)
   - 9 smoke tests, 100% pass rate
   - Fixtures: state_manager, sample_project (in conftest.py)

7. **Documentation**
   - CHANGELOG.md updated with v1.3.0 changes

### What Needs Completion 🔲

**Phase 2: Production Readiness (16 hours, 0% complete)**

See `AGILE_HIERARCHY_COMPLETION_PLAN.md` for detailed breakdown:

1. **Epic 1: Code Quality & Consistency** (6 hours)
   - Rename helper methods in orchestrator (_milestone → _epic)
   - Update existing tests (remove old terminology)
   - Code quality checks (mypy, pylint)

2. **Epic 2: Enhanced CLI Commands** (4 hours)
   - Add list/show/update/delete commands
   - Complete CRUD operations for epic/story/milestone

3. **Epic 3: Comprehensive Testing** (4 hours)
   - 150+ tests for edge cases, validation, performance
   - Integration tests with real orchestration flows

4. **Epic 4: Documentation Updates** (2 hours)
   - Update CLAUDE.md, architecture docs, guides
   - Create AGILE_WORKFLOW_GUIDE.md
   - Create MIGRATION_GUIDE_V1.3.md

---

## Project Context

### Architecture Overview

**Obra** (Claude Code Orchestrator) is an AI orchestration platform combining:
- **Local LLM** (Qwen 2.5 Coder on Ollama) for validation/quality scoring
- **Remote Agent** (Claude Code CLI) for code generation

**Key Design Principles**:
1. StateManager is single source of truth (no direct DB access)
2. Plugin-based architecture (agents and LLMs pluggable)
3. Per-iteration sessions (fresh Claude session per task)
4. Validation order: ResponseValidator → QualityController → ConfidenceScorer

### Agile Hierarchy Structure

```
Product (Project)
  ↓
Epic (Large feature, 3-15 sessions)
  ↓
Story (User deliverable, 1 session)
  ↓
Task (Technical work - default)
  ↓
Subtask (via parent_task_id)

Milestone → Checkpoint (when epics complete)
```

### Critical Files

**Core Implementation**:
- `src/core/models.py` - Database models (TaskType, Milestone)
- `src/core/state.py` - StateManager with epic/story methods
- `src/orchestrator.py` - Orchestration logic, execute_epic()
- `src/cli.py` - CLI commands

**Tests**:
- `tests/test_agile_hierarchy_basic.py` - 9 smoke tests
- `tests/conftest.py` - Fixtures (state_manager, sample_project)

**Documentation**:
- `docs/development/AGILE_HIERARCHY_COMPLETION_PLAN.md` - THIS IS YOUR GUIDE
- `docs/decisions/ADR-013-adopt-agile-work-hierarchy.md` - Architecture decision
- `CHANGELOG.md` - Version history

---

## Implementation Instructions

### Step-by-Step Approach

**IMPORTANT**: Follow the completion plan sequentially. Each epic builds on the previous.

### Epic 1: Code Quality & Consistency (Start Here)

**Objective**: Rename helper methods for consistency

**Files to Modify**:
- `src/orchestrator.py` (lines ~125, ~539, ~579, ~624)

**Key Changes**:
```python
# Rename methods
_start_milestone_session → _start_epic_session
_end_milestone_session → _end_epic_session
_build_milestone_context → _build_epic_context

# Update variables (line ~125)
self._current_milestone_id → self._current_epic_id
self._current_milestone_context → self._current_epic_context
self._current_milestone_first_task → self._current_epic_first_task
```

**Validation**:
```bash
# Check no old references remain
grep -r "_.*milestone_" src/orchestrator.py

# Run tests
pytest tests/test_orchestrator.py -v
```

**Then**: Update existing tests that reference old terminology.

### Epic 2: Enhanced CLI Commands

**Objective**: Add list/show/update/delete for complete CRUD

**Files to Modify**:
- `src/cli.py` (after line ~450)

**Pattern to Follow**:
```python
@epic.command('list')
@click.option('--project', '-p', type=int)
@click.option('--status', '-s')
@click.pass_context
def epic_list(ctx, project, status):
    """List all epics."""
    # Query epics with filters
    # Display formatted table
    # Handle errors gracefully
```

See completion plan lines 189-280 for complete implementation.

### Epic 3: Comprehensive Testing

**Objective**: Achieve ≥85% test coverage

**Files to Create**:
- `tests/test_agile_hierarchy_comprehensive.py`

**Test Categories**:
1. Edge cases (invalid inputs, empty results)
2. Validation (epic type checking, story parent validation)
3. Complex scenarios (milestone with multiple epics)
4. Cascade operations (delete epic → soft delete stories)
5. Performance (50+ stories in epic)

See completion plan lines 317-554 for test templates.

### Epic 4: Documentation Updates

**Objective**: Update all documentation with Agile terminology

**Files to Update**:
- `CLAUDE.md` - Search/replace milestone → epic terminology
- `docs/architecture/ARCHITECTURE.md` - Update diagrams
- `docs/guides/GETTING_STARTED.md` - Update examples
- `docs/guides/CLI_REFERENCE.md` - Add new commands

**Files to Create**:
- `docs/guides/AGILE_WORKFLOW_GUIDE.md` - Complete workflow examples
- `docs/guides/MIGRATION_GUIDE_V1.3.md` - v1.2 → v1.3 migration

See completion plan lines 556-792 for complete guide templates.

---

## Success Criteria Checklist

### Code Quality
- [ ] All helper methods use "epic" terminology (not "milestone")
- [ ] No references to `_.*milestone_` in orchestrator.py
- [ ] No linting warnings (run `pylint src/orchestrator.py src/cli.py`)
- [ ] Type checking passes (run `mypy src/`)

### CLI Completeness
- [ ] `obra epic list/show/update/delete` work
- [ ] `obra story list/show/update/move` work
- [ ] `obra milestone list/show/update` work
- [ ] All commands have `--help` text
- [ ] Error messages are clear

### Test Coverage
- [ ] Overall coverage ≥85% (run `pytest --cov=src --cov-report=term`)
- [ ] 150+ tests total (including new comprehensive tests)
- [ ] All tests pass (`pytest tests/ -v`)
- [ ] Edge cases covered
- [ ] Performance tests pass

### Documentation
- [ ] CLAUDE.md updated (no "milestone" as task group)
- [ ] AGILE_WORKFLOW_GUIDE.md created
- [ ] MIGRATION_GUIDE_V1.3.md created
- [ ] CLI_REFERENCE.md has all commands
- [ ] All guides use correct terminology

### Integration
- [ ] Existing tests pass (no regressions)
- [ ] Migration script tested
- [ ] Real orchestration flows work end-to-end

---

## Common Pitfalls to Avoid

### 1. Don't Skip Test Updates
❌ Renaming methods without updating tests breaks CI
✅ Update tests immediately after code changes

### 2. Don't Forget Documentation
❌ Code complete but docs outdated confuses users
✅ Update docs in parallel with code

### 3. Don't Ignore Edge Cases
❌ Only testing happy path misses bugs
✅ Test invalid inputs, empty results, boundary conditions

### 4. Don't Change Existing Behavior
❌ Backward compatibility broken
✅ Existing tasks (TaskType.TASK) still work

### 5. Don't Overcomplicate CLI
❌ Too many options confuses users
✅ Follow existing CLI patterns, keep it simple

---

## Testing Strategy

### Run Tests Incrementally

After each epic:
```bash
# Quick smoke test
pytest tests/test_agile_hierarchy_basic.py -v

# Full test suite
pytest tests/ --cov=src --cov-report=term

# Specific module
pytest tests/test_orchestrator.py -v
```

### Test Guidelines

**CRITICAL**: Read `docs/development/TEST_GUIDELINES.md` before writing tests!

Key rules:
- Max sleep per test: 0.5s (use fast_time fixture)
- Max threads per test: 5
- Max memory allocation: 20KB per test
- Mark heavy tests: `@pytest.mark.slow`

### Performance Testing

```python
def test_large_epic_performance(state_manager, sample_project, fast_time):
    """Test epic with 50 stories."""
    import time

    epic_id = state_manager.create_epic(...)

    start = time.time()
    for i in range(50):
        state_manager.create_story(...)
    creation_time = time.time() - start

    assert creation_time < 5.0  # Should be fast
```

---

## Code Style & Standards

### Type Hints (Required)
```python
def create_epic(
    self,
    project_id: int,
    title: str,
    description: str,
    **kwargs
) -> int:
    """Create epic task."""
    pass
```

### Docstrings (Google Style)
```python
def create_epic(self, project_id: int, title: str, description: str) -> int:
    """Create an Epic task.

    Args:
        project_id: Project ID
        title: Epic title
        description: Epic description

    Returns:
        Epic task ID

    Example:
        >>> epic_id = state.create_epic(1, "Auth System", "OAuth + MFA")
    """
```

### Error Handling
```python
# Validate inputs
if not epic:
    raise ValueError(f"Epic {epic_id} does not exist")

# Use custom exceptions
from src.core.exceptions import DatabaseException
raise DatabaseException(operation='create_epic', details=str(e))
```

### CLI Patterns
```python
@cli.command()
@click.argument('id', type=int)
@click.option('--verbose', '-v', is_flag=True)
@click.pass_context
def show(ctx, id: int, verbose: bool):
    """Show detailed information."""
    try:
        config = ctx.obj['config']
        # ... implementation ...
        click.echo(f"✓ Success")
    except Exception as e:
        click.echo(f"✗ Failed: {e}", err=True)
        sys.exit(1)
```

---

## Verification Commands

### After Each Epic

```bash
# Epic 1: Code Quality
grep -r "_.*milestone_" src/orchestrator.py  # Should be empty
pytest tests/test_orchestrator.py -v  # Should pass

# Epic 2: Enhanced CLI
obra epic list --help  # Should show help
obra epic list --project 1  # Should work

# Epic 3: Comprehensive Testing
pytest tests/ --cov=src --cov-report=term  # Should show ≥85%

# Epic 4: Documentation
grep -r "execute_milestone" docs/ | grep -v "OLD\|deprecated"  # Minimal results
```

---

## Timeline Recommendations

### Day 1 (8 hours)
- **Morning** (4h): Epic 1 - Code Quality (rename methods, update tests)
- **Afternoon** (4h): Epic 2 - Enhanced CLI (list/show commands)

### Day 2 (8 hours)
- **Morning** (4h): Epic 3 - Comprehensive Testing (edge cases, integration)
- **Afternoon** (4h): Epic 4 - Documentation (guides, updates)

### Optional Day 3 (if needed)
- **Buffer**: Performance optimization, additional testing, code review

---

## Quick Reference Links

### Essential Reading (Read First)
1. **Completion Plan**: `docs/development/AGILE_HIERARCHY_COMPLETION_PLAN.md` ⭐
2. **ADR-013**: `docs/decisions/ADR-013-adopt-agile-work-hierarchy.md`
3. **Test Guidelines**: `docs/development/TEST_GUIDELINES.md` ⚠️

### Implementation Reference
- **Phase 1 Summary**: See "What's Already Done" section above
- **Core Models**: `src/core/models.py` lines 69-373 (TaskType, Milestone)
- **StateManager**: `src/core/state.py` lines 735-971 (epic/story methods)
- **Orchestrator**: `src/orchestrator.py` lines 667-789 (execute_epic)
- **CLI**: `src/cli.py` lines 379-585 (epic/story/milestone commands)

### Testing Reference
- **Smoke Tests**: `tests/test_agile_hierarchy_basic.py` (9 tests, all passing)
- **Fixtures**: `tests/conftest.py` lines 235-273 (state_manager, sample_project)
- **Test Guidelines**: `docs/development/TEST_GUIDELINES.md` (CRITICAL!)

---

## Environment Setup

```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies (if needed)
pip install -r requirements.txt

# Verify database
ls -la orchestrator.db  # Should exist

# Run initial tests
pytest tests/test_agile_hierarchy_basic.py -v  # Should pass (9/9)

# Check CLI commands
python -m src.cli --help | grep -E "epic|story|milestone"  # Should show commands
```

---

## Communication Guidelines

### Progress Updates

After completing each epic:
```
✅ Epic 1 Complete: Code Quality & Consistency
- Renamed 3 helper methods in orchestrator
- Updated 15 test files
- All tests passing (125/125)
- No linting warnings

Starting Epic 2: Enhanced CLI Commands...
```

### Blockers

If stuck:
```
🚫 Blocked on Epic 2: CLI list command
- Issue: Query returning wrong results
- Need: Clarification on filter behavior
- Tried: ...
- Error: ...
```

### Questions

Ask for clarification if:
- Requirements ambiguous
- Test expectations unclear
- Design decision needed
- Breaking change required

---

## Final Checklist

Before marking complete:

### Code
- [ ] All epics implemented
- [ ] All helper methods renamed
- [ ] CLI commands complete (list/show/update/delete)
- [ ] No linting warnings
- [ ] Type checking passes

### Tests
- [ ] 150+ total tests
- [ ] All tests pass
- [ ] Coverage ≥85%
- [ ] Edge cases covered
- [ ] Integration tests work

### Documentation
- [ ] CLAUDE.md updated
- [ ] All guides updated
- [ ] AGILE_WORKFLOW_GUIDE.md created
- [ ] MIGRATION_GUIDE_V1.3.md created
- [ ] CLI_REFERENCE.md complete

### Verification
- [ ] Migration script tested
- [ ] Real orchestration flows work
- [ ] Backward compatibility verified
- [ ] No regressions in existing tests

---

## Git Workflow

### Branch Strategy

```bash
# Create feature branch
git checkout -b feature/agile-hierarchy-phase2

# Commit after each epic
git add .
git commit -m "feat: Complete Epic 1 - Code Quality & Consistency

- Renamed helper methods in orchestrator
- Updated existing tests with new terminology
- All quality checks pass (mypy, pylint)

Refs: ADR-013"

# Push and create PR when all epics complete
git push origin feature/agile-hierarchy-phase2
```

### Commit Messages

Follow conventional commits:
```
feat: Add epic list/show CLI commands
fix: Correct milestone completion check logic
test: Add comprehensive edge case tests
docs: Create Agile workflow guide
refactor: Rename milestone helper methods
```

---

## Success Metrics

**Definition of Done**:
- All 4 epics implemented and tested
- 150+ tests, ≥85% coverage, 100% pass rate
- All documentation updated
- No regressions in existing functionality
- Code review approved
- Ready for merge to main

**Expected Outcome**:
- Production-ready Agile hierarchy
- Industry-standard terminology throughout
- Comprehensive CLI for epic/story/milestone management
- Complete test coverage
- User-friendly documentation

---

**Version**: 1.0
**Last Updated**: November 5, 2025
**Estimated Time**: 16 hours (2 days)
**Complexity**: Medium
**Dependencies**: Phase 1 complete (100%)

---

## Start Command

Ready to begin? Copy-paste this:

```
Read "docs/development/AGILE_HIERARCHY_COMPLETION_PLAN.md" and begin Phase 2 implementation. Start with Epic 1: Code Quality & Consistency (rename helper methods in orchestrator). Work sequentially through all 4 epics. Use the todo list tool to track progress. Report completion of each epic before moving to the next.
```

Good luck! 🚀
