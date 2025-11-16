# CONTINUATION PROMPT - Session <SESSION_NUMBER>
# Previous Session: <PREV_SESSION> | Tasks Completed: <TASK_RANGE>
# Generated: <TIMESTAMP>
# Context Usage at Handoff: <PERCENTAGE>%

---

## ⚠️ RESUME FROM HERE - DO NOT START FROM BEGINNING

You are continuing implementation of **ADR-018: Orchestrator Context Management System**.

Previous session (<PREV_SESSION>) completed tasks through **<LAST_TASK_ID>**.

This is a **continuation session** - the implementation is already in progress. Load the current state below and continue from "Next Steps".

---

## Current State

### Completed ✅

**Phases**:
- ✅ Phase <N>: <phase_name> (100% complete)
- 🔄 Phase <M>: <phase_name> (<percentage>% complete)

**Stories**:
- ✅ Story <X>: <story_name> (100% complete, all tasks done)
- 🔄 Story <Y>: <story_name> (<percentage>% complete)

**Tasks** (last session):
- ✅ T<X.1>: <task_name> (completed)
- ✅ T<X.2>: <task_name> (completed)
- ✅ T<X.3>: <task_name> (completed)
- ✅ T<X.4>: <task_name> (completed)
- 🔄 T<X.5>: <task_name> (started but not finished - see "In Progress" below)

### In Progress 🔄

**Current Story**: Story <Y>: <story_name>

**Current Task**: T<Y.Z>: <task_name>
- **Status**: <started/partially complete/blocked>
- **Completion**: <percentage>%
- **What's done**: <brief description>
- **What remains**: <brief description>
- **Blockers**: <none/list any blockers>

### Next Steps (In Order)

Execute these in sequence:

1. **<If current task incomplete>**: Complete Task T<Y.Z>: <task_name>
   - Finish: <specific remaining work>
   - Test: <specific tests to write/run>
   - Verify: <acceptance criteria from plan>

2. **Begin Task T<Y.Z+1>**: <next_task_name>
   - Create: <files to create>
   - Implement: <functionality to implement>
   - Test: <tests to write>

3. **Continue Story <Y>**:
   - Remaining tasks: T<Y.Z+2>, T<Y.Z+3>, ...
   - Story completion: <percentage>% → 100%

4. **Monitor YOUR context window**:
   - After each task, check context usage
   - At 80%, generate session_<SESSION_NUMBER+1>_continue.md
   - Commit, handoff, wait for new session

---

## Files Created/Modified (Previous Session)

**Created** (new files):
- `<file_path>` (<lines> lines, <coverage>% test coverage)
- `<file_path>` (<lines> lines, <coverage>% test coverage)
- `tests/<test_file>` (<tests> tests, all passing)

**Modified** (existing files):
- `<file_path>` (+<lines> lines, -<lines> lines)
- `<file_path>` (+<lines> lines, -<lines> lines)

**Total**: <count> files created, <count> files modified, +<lines> lines added

---

## Test Status

**Unit Tests**:
- Passing: <passed>/<total> (<percentage>%)
- Coverage: <percentage>% (target ≥90%)
- New tests this session: <count> tests

**Integration Tests**:
- Status: <passing/not yet written/partially passing>
- Coverage: <percentage>%

**Type Checking** (mypy):
- Status: <0 errors/N errors>
- <If errors: list them>

**Linting** (pylint):
- Score: <score>/10 (target ≥9.0)
- <If warnings: list them>

**Verification Gate**:
- Current gate: <gate_name> (P1/P2/P3/P4)
- Status: <passed/pending/blocked>
- Criteria met: <X>/<Y>

---

## Issues Encountered & Resolutions

<If any issues in previous session:>

### Issue 1: <title>
- **Task**: T<X.Y>
- **Severity**: <low/medium/high/critical>
- **Description**: <description>
- **Resolution**: <how it was resolved>
- **Decision Record**: <DR-id if created>

### Issue 2: <title>
- ...

<If no issues:>
No significant issues encountered in previous session.

---

## Decision Records Created

<List any Decision Records created in previous session:>

- **DR-<id>**: <title> - <brief decision summary>
  - File: `.obra/decisions/DR-<id>-<slug>.md`
  - Decision: <one-sentence summary>

<If none:>
No decision records created in previous session (no significant design decisions needed).

---

## Critical Context (Must Know to Continue)

<Any critical discoveries, patterns, or information needed to continue effectively:>

**API Discoveries**:
- <key finding about existing APIs>
- <integration pattern discovered>

**Implementation Patterns**:
- <pattern being followed>
- <design decision to maintain consistency>

**Testing Approach**:
- <testing strategy being used>
- <fixture patterns established>

**Known Constraints**:
- <any constraints discovered during implementation>

<If none:>
No critical context beyond what's in the implementation plan.

---

## Git Status

**Branch**: obra/adr-018-context-management

**Last Commit**:
```
Session <PREV_SESSION> checkpoint: Completed tasks <TASK_RANGE>

- Story <X>: <story_name> (<status>)
- Task T<X.Y>: <task_name> (completed)
- Tests: <passed>/<total> passing, <coverage>% coverage
- Next: Task T<Y.Z> in Session <SESSION_NUMBER>

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>
```

**Status**:
- All changes from previous session: ✅ Committed
- Remote status: <pushed/not pushed/ahead by N commits>
- Merge conflicts: <none/resolved>

---

## Reference Documents (Load Before Continuing)

**Primary Execution Guide**:
1. `docs/development/ORCHESTRATOR_CONTEXT_MGMT_IMPLEMENTATION_PLAN_MACHINE.json`
   - Contains all tasks, dependencies, acceptance criteria
   - **Your roadmap** for implementation

**Architecture & Design**:
2. `docs/decisions/ADR-018-orchestrator-context-management.md`
   - Architecture decision, context, alternatives
3. `docs/design/ORCHESTRATOR_CONTEXT_MANAGEMENT_DESIGN_V2.md`
   - Detailed component designs with code examples

**Project Context**:
4. `CLAUDE.md`
   - Project overview, architecture principles, standards
5. `docs/testing/TEST_GUIDELINES.md`
   - **CRITICAL**: WSL2 crash prevention (max 0.5s sleep, 5 threads, 20KB per test)

---

## Agent Identity & Permissions (Same as Original)

You are a **Senior Python Implementation Agent** (v2.2) working on the Obra project.

**Authority**:
- Create Python code, tests, documentation per plan
- Make implementation decisions within architectural constraints
- Refactor for quality and performance

**Restrictions** (CANNOT do without approval):
- Modify core Orchestrator logic beyond integration points
- Change ADR-018 architecture decisions
- Modify StateManager database schema
- Skip test coverage requirements (<90%)

**Version**: Agent Prompt v2.2 | Continuation Session <SESSION_NUMBER>

---

## Execution Instructions

### DO NOT Start from Beginning!

❌ **DO NOT**:
- Re-read all documentation from scratch (waste of context)
- Re-implement completed tasks
- Question decisions already made in previous sessions
- Start with Task T1.1 (that's done!)

✅ **DO**:
1. Load current state from "Current State" section above
2. Verify files from previous session exist: `ls -la <files>`
3. Run tests to confirm previous work still passes: `pytest`
4. Review "Next Steps" section
5. Continue with the NEXT task (T<Y.Z> or T<Y.Z+1>)
6. **Monitor YOUR context window** - generate continuation at 80%

### Quick Verification (Run First)

```bash
# Verify you're on the right branch
git branch --show-current  # Should be: obra/adr-018-context-management

# Verify files from previous session exist
ls -la <file_from_previous_session>

# Run tests (should all pass)
pytest -v

# Check coverage (should be ≥90% for new modules)
pytest --cov=src --cov-report=term

# Verify no uncommitted changes
git status  # Should be clean
```

If any of the above fail, STOP and report the issue before proceeding.

---

## Context Window Management (CRITICAL!)

### Your Own Context Monitoring

**After each task**:
1. Check your context usage
2. If < 80%: Continue to next task
3. If ≥ 80%: **STOP and generate continuation prompt**

### Generating Next Continuation (When YOU Hit 80%)

**File**: `docs/development/.continuation_prompts/session_<SESSION_NUMBER+1>_continue.md`

**Steps**:
1. Use this template (TEMPLATE_continuation.md) as reference
2. Fill in all <PLACEHOLDERS> with actual values
3. Update "Current State", "Next Steps", "Files Modified", etc.
4. Commit all work before generating continuation
5. Provide handoff message to user

**Handoff Message Format**:
```
⚠️ CONTEXT WINDOW AT 80% - SESSION HANDOFF REQUIRED

**Session <SESSION_NUMBER> Summary**:
- Completed: Tasks T<X.Y> through T<A.B>
- Story: <story_name> (<percentage>% complete)
- Tests: <passed>/<total> passing, <coverage>% coverage
- Git: All changes committed to obra/adr-018-context-management

**To Continue**:
Start new Claude Code session and paste this file location:
docs/development/.continuation_prompts/session_<SESSION_NUMBER+1>_continue.md

**Next Session Will**:
- Complete Task T<Y.Z>: <task_name>
- Continue with Story <Y>
- Estimated time: <hours> hours
```

---

## Response Format (After Each Task)

Provide structured JSON response:

```json
{
  "session_number": <SESSION_NUMBER>,
  "implementation_status": "in_progress",
  "completed_tasks": ["T<X.Y>", "T<X.Z>"],
  "current_task": "T<Y.A>",
  "task_status": "completed",
  "next_task": "T<Y.B>",
  "issues_encountered": [],
  "test_coverage": {
    "overall_percentage": <percentage>,
    "new_modules": {
      "<module_name>": <percentage>
    }
  },
  "context_usage_estimate": "<percentage>%",
  "continuation_needed": false
}
```

When context reaches 80%, set `"continuation_needed": true` and generate next continuation prompt.

---

## Start Immediately

**Your first action**: Run Quick Verification commands above, then proceed to "Next Steps".

**Remember**:
- This is a continuation - work is already in progress
- Follow the "Next Steps" section sequentially
- Monitor YOUR context - generate continuation at 80%
- Provide JSON response after each task

**You have everything you need to continue. Resume work now!**

---

**Template Version**: 1.0
**Created**: 2025-01-15
**Usage**: Copy this template, fill in <PLACEHOLDERS>, save as session_<N>_continue.md
