# Validation Checklist: End-to-End Testing

Use this checklist when manually validating Obra's real-world functionality. Print this out or keep it open during testing.

**Date**: _________________
**Tester**: _________________
**Version**: v1.1 (M8 Complete)
**Test Environment**: [ ] WSL2  [ ] Linux  [ ] macOS  [ ] Windows

---

## Pre-Test Setup

### Environment Prerequisites

- [ ] Python 3.12+ installed and activated in venv
- [ ] All dependencies installed (`pip install -r requirements.txt`)
- [ ] Database directory exists (`data/`)
- [ ] Logs directory exists (`logs/`)
- [ ] Test workspace directory accessible (`/tmp/obra_test_run/`)

### External Dependencies

- [ ] **Ollama**: Running on `localhost:11434` (or configured host)
- [ ] **Ollama Model**: `qwen2.5-coder:32b` pulled and ready
- [ ] **Claude Code CLI**: Installed and in PATH (`claude --version`)
- [ ] **API Key**: `ANTHROPIC_API_KEY` environment variable set
- [ ] **Network**: Connectivity to anthropic.com verified

### Configuration

- [ ] Test config created (`config/test_config.yaml`)
- [ ] Agent type configured (mock or claude_code_local)
- [ ] Database path configured correctly
- [ ] Workspace directory path set
- [ ] Logging level set appropriately (INFO or DEBUG)

**Notes**: _______________________________________________________________

---

## Component Testing

### Database & State Management

- [ ] Database file created on initialization
- [ ] Tables created (projects, tasks, iterations, etc.)
- [ ] StateManager can create projects
- [ ] StateManager can create tasks
- [ ] StateManager can update task status
- [ ] StateManager can retrieve tasks by ID
- [ ] StateManager can query all tasks for a project
- [ ] State persists between sessions (restart and check)

**Issues Found**: _______________________________________________________________

### Agent Communication (Local)

- [ ] ClaudeCodeLocalAgent can be instantiated
- [ ] Agent initializes (subprocess starts)
- [ ] Workspace directory created
- [ ] Agent reaches READY state
- [ ] `send_prompt()` accepts prompts
- [ ] `send_prompt()` returns responses
- [ ] Agent maintains state across multiple prompts
- [ ] `is_healthy()` returns True when running
- [ ] `get_status()` returns valid status info
- [ ] `cleanup()` stops subprocess gracefully

**Agent Health Metrics**:
- Startup time: _______ seconds
- Response latency: _______ seconds
- Memory usage: _______ MB
- Process PID: _______

**Issues Found**: _______________________________________________________________

### File Monitoring

- [ ] FileWatcher can be created for workspace
- [ ] FileWatcher detects new files
- [ ] FileWatcher detects file modifications
- [ ] FileWatcher detects file deletions
- [ ] Debouncing works (rapid changes grouped)
- [ ] Ignore patterns work (`.git`, `__pycache__` ignored)
- [ ] File change events stored in database
- [ ] File content snapshots captured

**Files Monitored**: _______________________________________________________________

**Issues Found**: _______________________________________________________________

### Validation Pipeline

#### ResponseValidator

- [ ] Validates response completeness
- [ ] Detects incomplete responses
- [ ] Checks for closed code blocks
- [ ] Validates minimum response length
- [ ] Returns validation result with details

#### QualityController

- [ ] Calculates quality score (0-100)
- [ ] Identifies syntax errors in code
- [ ] Detects missing error handling
- [ ] Checks for test coverage
- [ ] Validates documentation/comments
- [ ] Returns detailed quality metrics

#### ConfidenceScorer

- [ ] Calculates confidence score (0-100)
- [ ] Considers validation results
- [ ] Considers quality scores
- [ ] Considers agent health
- [ ] Considers retry count
- [ ] Returns score with breakdown

#### DecisionEngine

- [ ] Decides PROCEED when scores high
- [ ] Decides RETRY when validation fails
- [ ] Decides CLARIFY when quality low
- [ ] Decides ESCALATE when confidence low
- [ ] Returns decision with reasoning

**Sample Scores**:
- Validation: _______
- Quality: _______
- Confidence: _______
- Decision: _______

**Issues Found**: _______________________________________________________________

### Breakpoint System

- [ ] Breakpoint can be created
- [ ] Breakpoint stored in database
- [ ] Breakpoint triggers on low confidence
- [ ] Breakpoint triggers on low quality
- [ ] Breakpoint triggers on validation failure
- [ ] Breakpoint triggers on unexpected error
- [ ] User notified of breakpoint reason
- [ ] User input can be provided
- [ ] Execution resumes after breakpoint
- [ ] Breakpoint resolution logged

**Breakpoints Triggered**: _______________________________________________________________

**Issues Found**: _______________________________________________________________

---

## End-to-End Scenarios

### Scenario 1: Happy Path ✓

**Task**: "Create a Python calculator with add, subtract, multiply, divide functions"

- [ ] Project created successfully
- [ ] Task created successfully
- [ ] Task status: PENDING → IN_PROGRESS
- [ ] Agent receives task prompt
- [ ] Agent generates calculator.py
- [ ] Agent generates test_calculator.py
- [ ] Files created in workspace
- [ ] Response validation passes
- [ ] Quality score ≥ 70: _______
- [ ] Confidence score ≥ 50: _______
- [ ] No breakpoints triggered
- [ ] Tests run and pass (pytest)
- [ ] Task status: IN_PROGRESS → COMPLETED
- [ ] State persisted to database

**Duration**: _______ minutes
**Status**: [ ] PASSED  [ ] FAILED

**Output Files**:
- calculator.py: [ ] Exists  [ ] Correct
- test_calculator.py: [ ] Exists  [ ] Correct

**Code Quality**:
- [ ] Functions defined correctly
- [ ] Error handling present (divide by zero)
- [ ] Tests cover all functions
- [ ] Tests pass (5/5)

**Issues Found**: _______________________________________________________________

### Scenario 2: Quality Control

**Task**: "Make the calculator better somehow" (ambiguous)

- [ ] Task created with ambiguous description
- [ ] Agent generates response
- [ ] Quality score < 70: _______
- [ ] Breakpoint triggered: QUALITY_TOO_LOW
- [ ] User notified with clear reason
- [ ] Clarification provided: "Add input validation"
- [ ] Agent generates improved response
- [ ] Quality score improved ≥ 70: _______
- [ ] Task completes successfully

**Duration**: _______ minutes
**Status**: [ ] PASSED  [ ] FAILED

**Issues Found**: _______________________________________________________________

### Scenario 3: Confidence Testing

**Task**: "Refactor calculator to use classes and inheritance"

- [ ] Task created (complex refactoring)
- [ ] Agent generates refactored code
- [ ] Confidence score < 50: _______
- [ ] Breakpoint triggered: LOW_CONFIDENCE
- [ ] User reviews changes
- [ ] User approves or requests changes
- [ ] Task completes or retries

**Duration**: _______ minutes
**Status**: [ ] PASSED  [ ] FAILED

**Issues Found**: _______________________________________________________________

### Scenario 4: File Monitoring

**Task**: "Add logarithm and exponent functions"

- [ ] Initial files exist (from Scenario 1)
- [ ] FileWatcher enabled and monitoring
- [ ] Task executes
- [ ] calculator.py modified
- [ ] File modification detected
- [ ] FileChangeEvent created in database
- [ ] Change metadata captured (lines added)
- [ ] File content snapshot saved
- [ ] Rollback possible (previous version available)

**File Changes Detected**: _______________________________________________________________

**Duration**: _______ minutes
**Status**: [ ] PASSED  [ ] FAILED

**Issues Found**: _______________________________________________________________

### Scenario 5: Agent Recovery

**Task**: "Add comprehensive docstrings"

- [ ] Task starts execution
- [ ] Agent process started
- [ ] Simulate failure (kill process manually): `kill -9 <PID>`
- [ ] Health check detects failure
- [ ] Breakpoint triggered: UNEXPECTED_ERROR
- [ ] Error logged with context
- [ ] Agent cleanup executed
- [ ] Agent can be reinitialized
- [ ] Task can resume (or marked for retry)

**Duration**: _______ minutes
**Status**: [ ] PASSED  [ ] FAILED

**Recovery Time**: _______ seconds

**Issues Found**: _______________________________________________________________

### Scenario 6: Multi-Iteration

**Task**: "Create calculator with GUI, persistence, and history" (complex)

- [ ] Task created (multi-part requirement)
- [ ] Iteration 1: Core GUI framework
- [ ] Iteration 2: Calculation logic
- [ ] Iteration 3: Add persistence (JSON)
- [ ] Iteration 4: Add history feature
- [ ] Context maintained across iterations
- [ ] Each iteration builds on previous
- [ ] Quality improves over iterations
- [ ] Final deliverable meets all requirements
- [ ] All iterations logged in database

**Iterations**: _______
**Duration**: _______ minutes
**Status**: [ ] PASSED  [ ] FAILED

**Quality Progression**:
- Iteration 1: _______
- Iteration 2: _______
- Iteration 3: _______
- Iteration 4: _______

**Issues Found**: _______________________________________________________________

---

## Performance Metrics

### Agent Performance

- **Startup Time**: _______ seconds (target: < 30s)
- **Avg Response Time**: _______ seconds (target: < 120s)
- **Memory Usage**: _______ MB (target: < 500MB)
- **CPU Usage**: _______ % (peak)

### System Performance

- **Database Size**: _______ MB (after all tests)
- **Log Size**: _______ MB
- **Workspace Size**: _______ MB
- **Total Test Duration**: _______ minutes

### Resource Utilization

- [ ] Memory usage acceptable (< 1GB total)
- [ ] CPU usage reasonable (< 80% sustained)
- [ ] Disk I/O not excessive
- [ ] Network latency acceptable

---

## Code Quality Assessment

### Generated Code (from Scenario 1)

**Correctness**:
- [ ] Code runs without errors
- [ ] All functions work as expected
- [ ] Edge cases handled (e.g., divide by zero)

**Style**:
- [ ] PEP 8 compliant
- [ ] Meaningful variable names
- [ ] Consistent formatting

**Documentation**:
- [ ] Docstrings present
- [ ] Comments for complex logic
- [ ] Module-level documentation

**Testing**:
- [ ] Unit tests included
- [ ] Tests comprehensive (all functions)
- [ ] Tests pass (5/5)
- [ ] Test coverage > 80%

**Pylint Score**: _______ / 10 (run: `pylint calculator.py`)
**Mypy Check**: [ ] Passed  [ ] Failed (run: `mypy calculator.py`)

---

## Integration Validation

### Full Workflow

- [ ] Task creation → database entry
- [ ] Database entry → context building
- [ ] Context → prompt generation
- [ ] Prompt → agent execution
- [ ] Agent output → response capture
- [ ] Response → validation pipeline
- [ ] Validation → quality scoring
- [ ] Quality → confidence calculation
- [ ] Confidence → decision making
- [ ] Decision → state update
- [ ] State → database persistence

**Data Flow**: [ ] Smooth  [ ] Issues Found

**Issues**: _______________________________________________________________

### Error Handling

- [ ] Graceful handling of agent failures
- [ ] Proper logging of errors
- [ ] Error context captured
- [ ] Recovery mechanisms work
- [ ] User notifications clear

### State Consistency

- [ ] State consistent across components
- [ ] No race conditions observed
- [ ] Transaction rollback works (test with error injection)
- [ ] Concurrent access handled (if tested)

---

## Final Assessment

### Overall System Health

- **Stability**: [ ] Excellent  [ ] Good  [ ] Fair  [ ] Poor
- **Performance**: [ ] Excellent  [ ] Good  [ ] Fair  [ ] Poor
- **Usability**: [ ] Excellent  [ ] Good  [ ] Fair  [ ] Poor
- **Documentation**: [ ] Excellent  [ ] Good  [ ] Fair  [ ] Poor

### Blockers

Critical issues that prevent production use:

1. _______________________________________________________________
2. _______________________________________________________________
3. _______________________________________________________________

### Non-Blockers

Minor issues that should be addressed:

1. _______________________________________________________________
2. _______________________________________________________________
3. _______________________________________________________________

### Recommendations

- [ ] **READY FOR PRODUCTION** - All tests passed, no blockers
- [ ] **READY WITH CAVEATS** - Minor issues, acceptable for beta
- [ ] **NOT READY** - Critical issues must be fixed first

**Additional Notes**: _______________________________________________________________
_______________________________________________________________
_______________________________________________________________

---

## Sign-Off

**Tester Name**: _______________________________

**Signature**: _______________________________

**Date**: _______________________________

**Overall Result**: [ ] PASSED  [ ] FAILED

---

## Appendix: Command Reference

### Quick Test Commands

```bash
# Run automated test
python tests/test_runthrough.py --scenario 1

# Check database
sqlite3 data/orchestrator_test.db "SELECT * FROM tasks;"

# Run manual test
python -m src.cli task execute 1 --config config/test_config.yaml

# Check logs
tail -f logs/orchestrator.log

# Clean up
python tests/test_runthrough.py --clean
```

### Debugging Commands

```bash
# Python REPL testing
python
>>> from src.core.state import StateManager
>>> from src.core.config import Config
>>> config = Config.load('config/test_config.yaml')
>>> state = StateManager(config)
>>> tasks = state.get_all_tasks(project_id=1)
>>> print(tasks)

# Check agent health
ps aux | grep claude

# Monitor workspace
watch -n 1 'ls -ltr /tmp/obra_test_run/workspace/'

# Check Ollama
curl http://localhost:11434/api/tags
```

---

**Validation Checklist v1.0** - Last Updated: 2025-11-02
