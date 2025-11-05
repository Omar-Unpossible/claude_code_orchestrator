# Tetris Test - Critical Bug Fix Plan

**Date**: 2025-11-04
**Test ID**: test_tetrisgame
**Status**: BLOCKED - Critical bugs discovered during first execution
**Severity**: P0 - Test cannot proceed without fixes

---

## Executive Summary

First execution of Tetris game test revealed **4 critical bugs** that prevented successful task execution:

1. **Prompt Generation Bug (P0)**: Task object not flattened to template variables → 78% prompt data loss
2. **Data Persistence Bug (P0)**: Interaction data not saved to database → No response tracking
3. **Output Validation Bug (P0)**: Decision engine approves empty responses → False positives
4. **Working Directory Bug (P1)**: Agent launches in wrong directory → Context confusion

**Impact**: Test appeared to "succeed" (quality: 0.72, status: completed) but **zero actual work performed**.

---

## Bug Details

### BUG-TETRIS-001: Prompt Generation Data Loss (P0)

**File**: `src/orchestrator.py`
**Line**: ~line 450-455 (prompt_context construction)

**Root Cause**:
```python
# CURRENT (BROKEN):
prompt_context = {
    'task': task_object,      # Task object with .title, .description, etc.
    'context': context_text
}

prompt = self.prompt_generator.generate_prompt('task_execution', prompt_context)
```

**Template Expects**:
```jinja2
{{ task_title }}         # ❌ UNDEFINED → renders as ""
{{ task_description }}   # ❌ UNDEFINED → renders as ""
{{ task_id }}            # ❌ UNDEFINED → renders as ""
{{ project_name }}       # ❌ UNDEFINED → renders as ""
{{ working_directory }}  # ❌ UNDEFINED → renders as ""
```

**Evidence**:
- Task description: **1,203 chars**
- Context built: **1,205 chars** (300 tokens)
- **Prompt sent to Claude**: **267 chars** (78% data loss!)
- Claude received: Mostly empty template with undefined variables

**Impact**:
- Claude Code received incomplete/empty prompt
- No requirements, no context, no actionable information
- Responded with confusion: "I'm in an empty workspace directory"
- Task falsely marked as "complete" (quality: 0.72)

**Fix Required**:
Flatten task object attributes into flat dictionary for template:
```python
# FIXED:
prompt_context = {
    'task_id': task.id,
    'task_title': task.title,
    'task_description': task.description,
    'project_name': project.project_name,
    'working_directory': project.working_directory,
    'task_priority': task.priority,
    'context': context_text
}
```

**Testing**:
- Verify prompt length after fix (should be ~1,200+ chars)
- Log full prompt to validate all variables populated
- Unit test: mock task object, verify template rendering

---

### BUG-TETRIS-002: Interaction Data Not Persisted (P0)

**File**: `src/orchestrator.py`
**Line**: Unknown (likely in iteration loop)

**Root Cause**:
- Agent response received (1,027 chars)
- Response validated and approved (quality: 0.72)
- **Data never saved to `interaction` table**
- Only metadata saved to `session_record` table

**Evidence**:
```sql
SELECT COUNT(*) FROM interaction WHERE task_id=1;
-- Result: 0 rows (should be 1+)

SELECT * FROM session_record WHERE task_id=1;
-- Result: 1 row with metadata only (no response text)
```

**Impact**:
- No response tracking or history
- Cannot debug what Claude actually said
- Context continuity broken for multi-iteration tasks
- Audit trail incomplete

**Fix Required**:
- Add `state_manager.record_interaction()` call after agent response
- Ensure all required fields populated (prompt, response, quality_score, etc.)
- Verify database transaction commits

**Testing**:
- After fix, verify interaction table has 1+ rows per task execution
- Validate response text is stored completely (not truncated)
- Check timestamps, session_id, and metadata

---

### BUG-TETRIS-003: Output Validation False Positives (P0)

**File**: `src/orchestration/decision_engine.py`
**Line**: Decision logic (~line 100-200)

**Root Cause**:
- Decision engine validates **text quality only**
- Does not detect:
  - No files created
  - No planning document generated
  - No actionable output produced
  - Response is just confusion/questions
- Approved response: "I can see we're in the `/home/.../workspace` directory, which is currently empty"
- Quality score: **0.72 (PASS)** - grammatically correct but useless

**Impact**:
- False completion signals
- Wastes iterations on non-productive responses
- No feedback to Claude to actually do work
- Test passes despite zero progress

**Fix Required**:
Add output validation heuristics:

```python
# Check for "no work done" indicators
no_work_indicators = [
    len(response) < 500,  # Too short for real work
    'empty' in response.lower() and 'directory' in response.lower(),
    'confused' in response.lower(),
    'not sure' in response.lower(),
    file_watcher.files_changed_count == 0,  # No files modified
    'no files' in response.lower()
]

if any(no_work_indicators) and iteration == 1:
    decision = 'RETRY'  # or 'CLARIFY'
    reason = 'No actionable work detected in response'
```

**Testing**:
- Test with empty/confused responses → should RETRY, not PROCEED
- Test with actual work (files created) → should PROCEED
- Test edge cases (minimal but valid responses)

---

### BUG-TETRIS-004: Wrong Working Directory (P1)

**File**: `src/agents/claude_code_local.py`
**Line**: Agent initialization (~line 50-100)

**Root Cause**:
- Claude Code launched in `workspace/` directory (empty)
- Prompt specified `/projects/test_tetrisgame/` for work
- No directory creation or navigation
- Claude confused about where to work

**Evidence**:
```
workspace/: empty (no files)
/projects/test_tetrisgame/: does not exist
Claude response: "I'm in the workspace directory, which is currently empty"
```

**Impact**:
- Agent doesn't know where to create files
- No clear working context
- Requires Claude to infer/create directories (error-prone)

**Fix Options**:

**Option 1: Auto-create target directory**
```python
# In orchestrator before sending prompt
target_dir = task.description.extract_directory()  # Parse from description
if target_dir and not os.path.exists(target_dir):
    os.makedirs(target_dir)
    os.chdir(target_dir)
```

**Option 2: Add explicit directory instruction to prompt**
```python
prompt_context['instructions'] = f"""
IMPORTANT: Create and work in directory: {target_dir}
First command should be: mkdir -p {target_dir} && cd {target_dir}
"""
```

**Option 3: Use workspace by default**
```python
# Simplest - tell Claude to work in workspace/
prompt_context['working_directory'] = './workspace'
prompt_context['instructions'] = """
Work in the ./workspace directory.
All project files should be created there.
"""
```

**Recommendation**: Option 3 (simplest, least assumptions)

**Testing**:
- Verify Claude creates files in expected directory
- Check working_directory matches reality
- Validate no "empty directory" confusion responses

---

## Fix Implementation Plan

### Phase 1: Critical Path Fixes (Blocking Test)

**Priority**: P0
**Time Estimate**: 1-2 hours
**Dependencies**: None

**Tasks**:

1. **Fix BUG-TETRIS-001 (Prompt Generation)**
   - [ ] Locate prompt_context construction in orchestrator.py
   - [ ] Flatten task object into flat dictionary
   - [ ] Add all required template variables (task_id, task_title, task_description, project_name, working_directory)
   - [ ] Log full prompt for validation
   - [ ] Test with mock task → verify all variables populated

2. **Fix BUG-TETRIS-002 (Data Persistence)**
   - [ ] Locate response handling in orchestrator iteration loop
   - [ ] Add `state_manager.record_interaction()` call
   - [ ] Pass all required fields (prompt, response, quality_score, validation_passed, confidence_score, etc.)
   - [ ] Verify transaction commits
   - [ ] Test: query interaction table after execution → should have data

3. **Fix BUG-TETRIS-003 (Output Validation)**
   - [ ] Add output validation module or enhance decision_engine.py
   - [ ] Implement "no work done" detection heuristics
   - [ ] Check file watcher for changes
   - [ ] Detect confusion/question responses
   - [ ] Return RETRY/CLARIFY instead of PROCEED for empty work
   - [ ] Test with various response types

4. **Fix BUG-TETRIS-004 (Working Directory)**
   - [ ] Set working_directory in prompt_context to './workspace'
   - [ ] Add explicit instruction to work in workspace
   - [ ] Update test plan to use workspace instead of /projects/
   - [ ] Test: verify files created in workspace/

### Phase 2: Validation & Testing

**Priority**: P0
**Time Estimate**: 30-60 minutes
**Dependencies**: Phase 1 complete

**Tasks**:

1. **Unit Tests**
   - [ ] Test prompt generation with mock task object
   - [ ] Test interaction persistence with mock response
   - [ ] Test output validation with various response types
   - [ ] Test working directory setup

2. **Integration Test**
   - [ ] Re-run Tetris planning task (task_id=2, fresh task)
   - [ ] Verify prompt is complete (1,200+ chars)
   - [ ] Verify interaction saved to database
   - [ ] Verify Claude receives full requirements
   - [ ] Verify files created in workspace/

3. **Regression Verification**
   - [ ] Run CSV test to ensure no regressions
   - [ ] Check other test suites still pass
   - [ ] Validate decision logic still works for valid responses

### Phase 3: Documentation & Cleanup

**Priority**: P1
**Time Estimate**: 30 minutes
**Dependencies**: Phase 1-2 complete

**Tasks**:

1. **Update Documentation**
   - [ ] Document bug fixes in this file
   - [ ] Update TETRIS_GAME_TEST_PLAN.md with working_directory change
   - [ ] Create BUG_FIX_SUMMARY.md with lessons learned
   - [ ] Update CLAUDE.md with new pitfalls

2. **Code Cleanup**
   - [ ] Add inline comments explaining fixes
   - [ ] Remove debug logging if excessive
   - [ ] Update type hints if needed

---

## Success Criteria

**Phase 1 Complete When**:
- ✅ Prompt contains full task description (1,200+ chars)
- ✅ Interaction data saved to database (verified via SQL query)
- ✅ Empty responses trigger RETRY, not PROCEED
- ✅ Claude Code launches in correct directory (workspace/)

**Phase 2 Complete When**:
- ✅ All unit tests pass
- ✅ Tetris planning task executes successfully (milestone plan generated)
- ✅ No regressions in CSV test or other test suites

**Phase 3 Complete When**:
- ✅ All documentation updated
- ✅ Code reviewed and cleaned
- ✅ Ready to resume Tetris test

---

## Test Execution After Fixes

**Pre-Flight Checklist**:
1. ✅ All Phase 1 bugs fixed
2. ✅ All Phase 2 tests pass
3. ✅ Database has interaction data from test runs
4. ✅ Prompt length logged and verified (>1,000 chars)

**Execution Steps**:

1. **Create New Task** (don't reuse task_id=1)
   ```bash
   ./venv/bin/python -m src.cli task create \
     --project 1 \
     --description "[FULL TETRIS PROMPT HERE]" \
     "Tetris Game - Milestone Planning v2"
   ```

2. **Execute with Logging**
   ```bash
   ./venv/bin/python -m src.cli task execute <TASK_ID> 2>&1 | tee /tmp/tetris_v2_execution.log
   ```

3. **Validate Results**
   ```bash
   # Check interaction data
   sqlite3 /home/omarwsl/obra-runtime/data/orchestrator.db \
     "SELECT prompt, response FROM interaction WHERE task_id=<TASK_ID>;"

   # Check files created
   ls -la workspace/

   # Check prompt length in logs
   grep "AGENT SEND" /tmp/tetris_v2_execution.log
   ```

**Expected Outcome**:
- Prompt length: 1,200+ chars (full requirements sent)
- Interaction saved: 1+ rows in database
- Files created: Planning document or milestone breakdown in workspace/
- Quality score: 0.80+ (real work, not confusion)
- Status: completed or in_progress (with real progress)

---

## Lessons Learned

**For Future Development**:

1. **Template Variable Validation**: Add unit tests that validate template variables match expected data structure
2. **Data Persistence Tests**: Add assertions after each state change to verify DB writes
3. **Output Validation**: Never trust quality score alone - check for tangible outputs (files, docs, etc.)
4. **Working Directory Clarity**: Always explicitly set and communicate working directory
5. **Prompt Logging**: Log full prompts at DEBUG level for debugging
6. **False Positive Detection**: Add heuristics to detect "no work done" scenarios

**For CLAUDE.md**:
- ❌ **Don't pass object to template expecting flat variables**
- ❌ **Don't skip interaction persistence after validation**
- ❌ **Don't approve responses based on grammar alone**
- ❌ **Don't assume Claude knows where to work without explicit instruction**

---

## References

- **Test Plan**: `docs/development/TETRIS_GAME_TEST_PLAN.md`
- **Quick Start**: `docs/development/TETRIS_TEST_QUICK_START.md`
- **Execution Log**: `/tmp/tetris_test_execution.log`
- **Template**: `config/prompt_templates.yaml` (task_execution template)
- **Orchestrator**: `src/orchestrator.py` (prompt_context construction)
- **Decision Engine**: `src/orchestration/decision_engine.py`
- **Agent**: `src/agents/claude_code_local.py`

---

**Status**: Ready for Implementation
**Next Action**: Execute Phase 1 fixes
**Last Updated**: 2025-11-04
