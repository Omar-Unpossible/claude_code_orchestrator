# PHASE 4: VALIDATION - Handoff Document

**Date**: 2025-11-04
**From**: Phase 3 Completion
**To**: Phase 4 Validation
**Status**: Ready to begin

---

## Quick Start for Next Session

### Context Files to Read First
1. **FIX_PLAN.md** - Updated with Phase 3 completion (lines 1-35)
2. **Phase 3 Summary**: `/tmp/PHASE3_COMPLETE_FINAL_SUMMARY.md`
3. **Phase 4 Section**: FIX_PLAN.md lines 572-898 (validation tasks)

### Phase 3 Completion Summary
✅ **Complexity Estimator**: 54/54 tests (100%)  
✅ **Task Scheduler**: 28/28 tests (100%)  
✅ **Integration Tests**: 2/2 API fixes (100%)  
✅ **Total**: 84 tests fixed/maintained, zero regressions

---

## Phase 4 Overview

**Goal**: Validate production readiness through stress testing, real-world usage, and regression testing

**Duration**: 2-4 hours  
**Dependencies**: Phase 3 complete ✅

### Tasks Breakdown

#### Task 4.1: Stress Test (30 min)
- **Type**: Synthetic workflow test
- **Action**: Execute 10 simple tasks in sequence
- **Purpose**: Validate mechanics under load
- **Success**: All tasks complete, no errors, <30s per task

#### Task 4.2: Real-World Test (60 min)
- **Type**: Practical usage test
- **Action**: Implement calculator module (add/subtract/multiply/divide)
- **Purpose**: Validate practical task execution
- **Success**: File created, all functions work, docstrings present

#### Task 4.3: Regression Test (30 min)
- **Type**: CSV tool validation
- **Action**: Re-run M8 CSV test
- **Purpose**: Ensure no regressions vs baseline
- **Success**: Behavior matches M8, no performance degradation

#### Task 4.4: Validation Summary (10 min)
- **Action**: Generate comprehensive validation report
- **Deliverable**: Production readiness assessment

---

## Environment Requirements

### Critical for Phase 4

1. **Ollama Service** (REQUIRED for Task 4.1, 4.2, 4.3)
   - Must be running at `http://localhost:11434` (or configured host)
   - Model: Qwen 2.5 Coder 32B (or equivalent)
   - Status check: `curl http://localhost:11434/api/tags`

2. **Database**
   - SQLite: `data/stress_test.db` (will be created)
   - Ensure write permissions to `data/` directory

3. **Workspace Directories**
   - `/tmp/obra_stress_test` (Task 4.1)
   - `/tmp/calculator_test` (Task 4.2)
   - `/tmp/csv_test` (Task 4.3)

### Optional but Recommended

- **GPU Access**: For Qwen 2.5 Coder performance (RTX 5090 recommended)
- **Docker**: For consistent environment
- **Git**: For tracking changes during validation

---

## Starting Commands

### Quick Environment Check
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Check database directory permissions
ls -ld data/
mkdir -p data/ 2>/dev/null

# Check workspace directories
mkdir -p /tmp/obra_stress_test /tmp/calculator_test /tmp/csv_test

# Verify Python environment
source venv/bin/activate
python -c "from src.orchestrator import Orchestrator; print('✓ Import successful')"
```

### Task 4.1 Start (Stress Test)
```bash
cd /home/omarwsl/projects/claude_code_orchestrator

# Review stress test script from FIX_PLAN.md lines 607-649
# Execute stress test
python << 'SCRIPT'
from src.core.config import Config
from src.core.state import StateManager
from src.orchestrator import Orchestrator
import time

config = Config.load("config/config.yaml")
state = StateManager.get_instance("sqlite:///data/stress_test.db")

# Create project
project = state.create_project(
    "Stress Test",
    "Validates orchestration under load",
    "/tmp/obra_stress_test"
)

# Create 10 tasks
tasks = []
for i in range(1, 11):
    task = state.create_task(
        project_id=project.id,
        task_data={
            'title': f"Stress Task {i}",
            'description': f"echo 'Task {i} complete'"
        }
    )
    tasks.append(task)

# Execute with orchestrator
orchestrator = Orchestrator(config=config, state_manager=state)
orchestrator.initialize()

start = time.time()
for task in tasks:
    result = orchestrator.execute_task(task.id)
    print(f"Task {task.id}: {result}")
duration = time.time() - start

print(f"\n=== STRESS TEST COMPLETE ===")
print(f"Tasks: 10")
print(f"Duration: {duration:.1f}s")
print(f"Avg per task: {duration/10:.1f}s")
SCRIPT
```

---

## Known Issues & Workarounds

### Issue 1: Test Interference
**Problem**: Some tests fail in comprehensive suite but pass in isolation  
**Impact**: Affects ~140 tests in full suite run  
**Workaround**: Run module tests in isolation for accurate assessment  
**Phase 4 Impact**: None - validation uses orchestrator directly, not test suite

### Issue 2: Integration Tests Require Ollama
**Problem**: 12/14 integration tests fail without Ollama running  
**Impact**: Can't verify integration tests without service  
**Phase 4 Impact**: CRITICAL - Phase 4 requires Ollama for all tasks  
**Action Required**: Ensure Ollama is running before starting Phase 4

### Issue 3: SQLAlchemy Session Conflicts
**Problem**: Concurrent test operations can cause session conflicts  
**Solution Applied**: Use transaction() contexts and serial resource creation  
**Phase 4 Impact**: None - patterns already established in Phase 3

---

## Success Criteria

### Phase 4 Will Be Complete When:

1. ✅ **Task 4.1 Complete**: 10/10 stress test tasks execute successfully
2. ✅ **Task 4.2 Complete**: Calculator implemented and validated
3. ✅ **Task 4.3 Complete**: CSV test matches M8 baseline
4. ✅ **Task 4.4 Complete**: Validation report generated
5. ✅ **Production Ready**: All critical functionality verified

### Metrics to Track

| Metric | Target | How to Measure |
|--------|--------|----------------|
| **Stress Test Success Rate** | 100% (10/10) | Count completed tasks |
| **Average Task Time** | <30s | Total time / 10 |
| **Calculator Functions** | 4/4 working | Unit test all functions |
| **CSV Regression** | No change | Compare output vs M8 |
| **Error Count** | 0 | Check logs for exceptions |

---

## Files & Locations

### Phase 3 Artifacts (Reference)
- `/tmp/PHASE3_COMPLETE_FINAL_SUMMARY.md` - Complete Phase 3 summary
- `/tmp/PHASE3_TASK_SCHEDULER_COMPLETE.md` - Task scheduler details
- `/tmp/PHASE3_INTEGRATION_SUMMARY.md` - Integration fixes
- `/tmp/PHASE3_FIX_CYCLE_SUMMARY.txt` - Fix cycle walkthrough

### Phase 4 Outputs (To Be Created)
- `/tmp/PHASE4_STRESS_TEST_RESULTS.txt` - Stress test output
- `/tmp/PHASE4_CALCULATOR_TEST.txt` - Calculator validation
- `/tmp/PHASE4_CSV_REGRESSION_TEST.txt` - CSV comparison
- `/tmp/PHASE4_VALIDATION_REPORT.md` - Final validation report

### Configuration Files
- `config/config.yaml` - Main Obra configuration
- `config/complexity_thresholds.yaml` - Complexity estimation settings
- `FIX_PLAN.md` - This document (updated with Phase 3 complete)

### Code Locations (If Debugging Needed)
- `src/orchestrator.py` - Main orchestration loop
- `src/core/state.py` - StateManager (database operations)
- `src/llm/local_interface.py` - LLM interface (Ollama)
- `src/agents/claude_code_local.py` - Local agent implementation

---

## Troubleshooting Guide

### Problem: Ollama Connection Refused
```bash
# Check if Ollama is running
ps aux | grep ollama

# Start Ollama if needed
ollama serve &

# Verify connectivity
curl http://localhost:11434/api/tags
```

### Problem: Import Errors
```bash
# Verify virtual environment
source venv/bin/activate

# Reinstall dependencies if needed
pip install -r requirements.txt
```

### Problem: Database Locked
```bash
# Check for stale database locks
rm -f data/*.db-journal

# Or use new database
export TEST_DB="sqlite:///data/validation_test.db"
```

### Problem: Permission Denied on /tmp
```bash
# Use alternative workspace
mkdir -p ~/obra_workspaces/stress_test
# Update paths in stress test script
```

---

## Quick Decision Tree

```
START Phase 4
│
├─ Is Ollama running?
│  ├─ NO → Start Ollama first (CRITICAL)
│  └─ YES → Continue
│
├─ Run Task 4.1 (Stress Test)
│  ├─ All 10 tasks complete?
│  │  ├─ YES → Proceed to Task 4.2
│  │  └─ NO → Debug, check logs, retry
│  │
│  └─ Average time <30s?
│     ├─ YES → Mark success
│     └─ NO → Note performance issue, continue
│
├─ Run Task 4.2 (Calculator)
│  ├─ File created?
│  │  ├─ YES → Test functions
│  │  └─ NO → Debug orchestrator
│  │
│  └─ All functions work?
│     ├─ YES → Mark success
│     └─ NO → Debug implementation
│
├─ Run Task 4.3 (CSV Regression)
│  ├─ Executes without error?
│  │  ├─ YES → Compare output
│  │  └─ NO → Debug, check CSV file
│  │
│  └─ Output matches M8 baseline?
│     ├─ YES → Mark success
│     └─ NO → Investigate regression
│
└─ Generate Task 4.4 (Validation Report)
   └─ All tasks passed?
      ├─ YES → Production Ready ✅
      └─ NO → Review failures, decide next steps
```

---

## Estimated Timeline

| Task | Duration | Dependencies |
|------|----------|--------------|
| Environment setup | 10 min | Ollama running |
| Task 4.1 (Stress) | 30 min | Environment ready |
| Task 4.2 (Calculator) | 60 min | Task 4.1 complete |
| Task 4.3 (CSV) | 30 min | Task 4.2 complete |
| Task 4.4 (Report) | 10 min | All tasks complete |
| **Total** | **2-3 hours** | Clean environment |

---

## Context for LLM (Next Session)

When resuming in a new session, provide this context:

> "We just completed Phase 3 of the Obra test suite cleanup. We fixed the Complexity Estimator (54/54 tests, 100%) and Task Scheduler (28/28 tests, 100%) modules, plus 2 integration test API issues. 
>
> Now we need to begin Phase 4 (Validation), which validates production readiness through:
> 1. Stress test (10 tasks under load)
> 2. Real-world test (calculator implementation)  
> 3. Regression test (CSV tool)
> 4. Validation report
>
> Please read FIX_PLAN.md (updated with Phase 3 completion) and /tmp/PHASE4_HANDOFF.md for full context, then start with Task 4.1 (Stress Test). **Critical**: Ensure Ollama is running at http://localhost:11434 before beginning."

---

## Final Checklist Before Starting Phase 4

- [ ] Read FIX_PLAN.md (Phase 3 completion section)
- [ ] Read `/tmp/PHASE3_COMPLETE_FINAL_SUMMARY.md`
- [ ] Verify Ollama is running (`curl http://localhost:11434/api/tags`)
- [ ] Check database permissions (`ls -ld data/`)
- [ ] Create workspace directories (`mkdir -p /tmp/obra_*`)
- [ ] Activate Python environment (`source venv/bin/activate`)
- [ ] Review Task 4.1 script in FIX_PLAN.md (lines 607-649)
- [ ] Ready to execute stress test

**When all checked**: Begin Task 4.1 (Stress Test)

---

**Handoff Document Generated**: 2025-11-04  
**Phase 3 Status**: ✅ COMPLETE  
**Phase 4 Status**: ⏳ READY TO BEGIN  
**Estimated Completion**: 2-3 hours from start
