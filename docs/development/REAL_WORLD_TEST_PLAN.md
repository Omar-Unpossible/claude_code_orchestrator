# Real-World Test Plan: End-to-End Orchestration

**Version**: 1.0
**Date**: 2025-11-02
**Status**: Ready for Execution
**Target**: Obra v1.1 with Local Agent (M8)

## Overview

This test plan validates the complete Obra orchestration system with a real project. It tests the full workflow from task creation through agent execution, monitoring, validation, quality control, and breakpoint handling.

## Test Objectives

1. **System Integration**: Verify all components work together (database, agent, LLM, orchestrator)
2. **Agent Communication**: Validate local agent subprocess management and I/O
3. **Monitoring**: Confirm file watching and output monitoring work correctly
4. **Validation Pipeline**: Test ResponseValidator → QualityController → ConfidenceScorer → DecisionEngine
5. **Breakpoint System**: Verify breakpoints trigger correctly and handle human input
6. **State Management**: Ensure StateManager correctly persists and retrieves state
7. **End-to-End Flow**: Complete task execution from creation to completion

## Test Environment

### Prerequisites
- ✅ Obra installed and configured (M0-M8 complete)
- ✅ Python 3.12+ virtual environment activated
- ✅ SQLite database initialized
- ✅ Ollama running with Qwen 2.5 Coder model
- ✅ Claude Code CLI installed and in PATH
- ⚠️ ANTHROPIC_API_KEY environment variable set

### Configuration
Use `config/example_local_agent.yaml` as base, adjusted for testing:
- Agent type: `claude_code_local` (not mock!)
- Workspace: `./test_workspace`
- Breakpoints: enabled
- Quality threshold: 70
- Confidence threshold: 50

## Test Project: Simple Python Calculator

We'll use a simple calculator project to test the system:

**Project Goal**: Create a Python calculator with:
- Basic operations (add, subtract, multiply, divide)
- Error handling (division by zero)
- Unit tests
- CLI interface

**Why This Project**:
- Small enough to complete quickly
- Complex enough to test validation
- Has testable requirements (unit tests)
- Requires multiple files (structure)
- Can trigger quality checks

## Test Scenarios

### Scenario 1: Happy Path - Complete Task
**Duration**: 10-15 minutes
**Difficulty**: Easy
**Expected Outcome**: Task completes without breakpoints

**Steps**:
1. Initialize Obra database
2. Create project: "Calculator Project"
3. Create task: "Create a Python calculator with add, subtract, multiply, divide functions"
4. Execute task with orchestrator
5. Monitor execution progress
6. Validate final output

**Success Criteria**:
- ✅ Task completes with status: COMPLETED
- ✅ Files created in workspace: `calculator.py`, `test_calculator.py`
- ✅ Code passes validation (syntax check)
- ✅ Quality score ≥ 70
- ✅ Confidence score ≥ 50
- ✅ No breakpoints triggered
- ✅ State saved correctly in database

### Scenario 2: Quality Control - Low Quality Response
**Duration**: 15-20 minutes
**Difficulty**: Medium
**Expected Outcome**: Breakpoint triggered due to low quality

**Steps**:
1. Create task with ambiguous requirements: "Make the calculator better somehow"
2. Execute task
3. Expect low quality score due to vague implementation
4. Breakpoint should trigger
5. Provide clarification: "Add input validation and error messages"
6. Resume and complete

**Success Criteria**:
- ✅ Initial response has quality score < 70
- ✅ Breakpoint triggered: QUALITY_TOO_LOW
- ✅ Clarification stored in database
- ✅ Resumed execution incorporates feedback
- ✅ Final quality score ≥ 70

### Scenario 3: Confidence Scoring - Uncertain Response
**Duration**: 15-20 minutes
**Difficulty**: Medium
**Expected Outcome**: Breakpoint triggered due to low confidence

**Steps**:
1. Create task: "Refactor the calculator to use classes and inheritance"
2. Execute task
3. Expect low confidence due to major refactoring
4. Breakpoint should trigger
5. Review changes and approve
6. Complete task

**Success Criteria**:
- ✅ Confidence score < 50 after refactoring
- ✅ Breakpoint triggered: LOW_CONFIDENCE
- ✅ Human review logged
- ✅ Approval allows task to complete
- ✅ Refactored code works correctly

### Scenario 4: File Monitoring - Track Changes
**Duration**: 10-15 minutes
**Difficulty**: Easy
**Expected Outcome**: File changes tracked correctly

**Steps**:
1. Create task: "Add logarithm and exponent functions"
2. Enable file watching
3. Execute task
4. Monitor file change events
5. Verify changes tracked in database

**Success Criteria**:
- ✅ FileChangeEvents created for modified files
- ✅ Timestamps accurate
- ✅ File content snapshots captured
- ✅ Change metadata (lines added/removed) recorded
- ✅ Rollback capability available

### Scenario 5: Agent Health - Recovery from Failure
**Duration**: 15-20 minutes
**Difficulty**: Hard
**Expected Outcome**: System recovers from agent failure

**Steps**:
1. Create task: "Add comprehensive docstrings"
2. Execute task
3. Simulate agent failure (kill Claude Code process)
4. Expect health check to fail
5. Verify breakpoint triggered
6. Restart agent and resume

**Success Criteria**:
- ✅ Agent health check detects failure
- ✅ Breakpoint triggered: UNEXPECTED_ERROR
- ✅ Error logged with context
- ✅ Agent cleanup executed
- ✅ Agent reinitialized successfully
- ✅ Task can resume from last checkpoint

### Scenario 6: Multi-Iteration Task
**Duration**: 20-30 minutes
**Difficulty**: Hard
**Expected Outcome**: Complex task completed over multiple iterations

**Steps**:
1. Create complex task: "Create calculator with GUI, persistence, and history"
2. Execute task
3. Expect multiple iterations:
   - Iteration 1: Core GUI framework
   - Iteration 2: Calculation logic integration
   - Iteration 3: Add persistence (JSON)
   - Iteration 4: Add history feature
4. Monitor confidence/quality across iterations
5. Handle any breakpoints

**Success Criteria**:
- ✅ Multiple iterations (≥ 3) executed
- ✅ Each iteration builds on previous
- ✅ Context maintained across iterations
- ✅ Quality improves over iterations
- ✅ Final deliverable meets requirements
- ✅ All iterations logged in database

## Execution Guide

### Phase 1: Environment Setup (5 minutes)

```bash
# 1. Navigate to project directory
cd /home/omarwsl/projects/claude_code_orchestrator

# 2. Activate virtual environment
source venv/bin/activate

# 3. Verify Ollama is running
curl -s http://localhost:11434/api/tags | grep qwen2.5-coder

# 4. Verify Claude Code CLI
claude --version

# 5. Set environment variables
export ANTHROPIC_API_KEY=your_key_here
export OBRA_RUNTIME_DIR=/tmp/obra_test_run

# 6. Clean previous test data (optional)
rm -rf /tmp/obra_test_run/*
rm -f data/orchestrator.db

# 7. Create test configuration
cp config/example_local_agent.yaml config/test_config.yaml

# 8. Edit config (if needed)
# Set workspace_dir: /tmp/obra_test_run/workspace
# Set agent.type: claude_code_local
```

### Phase 2: System Initialization (2 minutes)

```bash
# 1. Initialize Obra database
python -m src.cli init --config config/test_config.yaml

# 2. Verify database created
ls -lh data/orchestrator.db

# 3. Create test project
python -m src.cli project create "Calculator Test Project" \
    --description "Test project for end-to-end validation" \
    --config config/test_config.yaml

# Expected output: Project created with ID: 1

# 4. Verify project in database
python -m src.cli project list --config config/test_config.yaml
```

### Phase 3: Scenario Execution (variable time)

#### Scenario 1: Happy Path

```bash
# 1. Create task
python -m src.cli task create \
    "Create a Python calculator with add, subtract, multiply, divide functions. Include unit tests." \
    --project 1 \
    --config config/test_config.yaml

# Expected output: Task created with ID: 1

# 2. Execute task
python -m src.cli task execute 1 \
    --config config/test_config.yaml

# Expected: Task runs for 5-10 minutes, shows progress
# Watch for:
# - Agent initialization
# - Task execution start
# - File changes detected
# - Validation passed
# - Quality score
# - Confidence score
# - Task completion

# 3. Check task status
python -m src.cli task show 1 --config config/test_config.yaml

# 4. Verify output files
ls -la /tmp/obra_test_run/workspace/
cat /tmp/obra_test_run/workspace/calculator.py
cat /tmp/obra_test_run/workspace/test_calculator.py

# 5. Run tests (verify code works)
cd /tmp/obra_test_run/workspace
python -m pytest test_calculator.py -v
```

#### Scenario 2-6: Follow similar pattern

Each scenario follows the same pattern:
1. Create task with specific requirements
2. Execute task
3. Monitor output and state
4. Interact at breakpoints (if any)
5. Verify completion and outcomes
6. Check database state

### Phase 4: Validation and Reporting (10 minutes)

```bash
# 1. Generate execution report
python tests/test_runthrough.py --report

# 2. Check all tasks
python -m src.cli task list --project 1 --config config/test_config.yaml

# 3. Export database for inspection
sqlite3 data/orchestrator.db .dump > test_run_dump.sql

# 4. Collect logs
tar -czf test_run_logs.tar.gz logs/ /tmp/obra_test_run/

# 5. Generate coverage report (optional)
pytest tests/test_integration_e2e.py --cov=src --cov-report=html
```

## Validation Checklist

### System Components

- [ ] **Database**: SQLite initialized, tables created
- [ ] **StateManager**: Queries work, transactions commit
- [ ] **Configuration**: Config loads correctly, values accessible
- [ ] **Logging**: Logs written to file, correct log level

### Agent (ClaudeCodeLocalAgent)

- [ ] **Initialization**: Agent starts subprocess successfully
- [ ] **Communication**: send_prompt() returns responses
- [ ] **Health**: is_healthy() returns True when running
- [ ] **Cleanup**: Agent cleanup completes gracefully
- [ ] **Status**: get_status() returns correct info

### Orchestration Flow

- [ ] **Task Creation**: Tasks created in database
- [ ] **Context Building**: ContextManager builds context correctly
- [ ] **Prompt Generation**: Prompts include context and task info
- [ ] **Agent Execution**: Agent receives prompts and responds
- [ ] **Response Capture**: Responses logged and stored

### Validation Pipeline

- [ ] **ResponseValidator**: Checks completeness and format
- [ ] **QualityController**: Scores response quality (0-100)
- [ ] **ConfidenceScorer**: Calculates confidence (0-100)
- [ ] **DecisionEngine**: Decides next action correctly

### Breakpoint System

- [ ] **Trigger Detection**: Breakpoints trigger on conditions
- [ ] **User Notification**: Breakpoint reason clearly stated
- [ ] **Input Capture**: User input collected and stored
- [ ] **Resume**: Execution resumes after breakpoint
- [ ] **State Persistence**: Breakpoint state saved

### File Monitoring

- [ ] **FileWatcher**: Detects file changes in workspace
- [ ] **Change Events**: Events logged to database
- [ ] **Metadata**: File metadata captured correctly
- [ ] **Debouncing**: Rapid changes debounced properly

### Output Quality

- [ ] **Code Correctness**: Generated code runs without errors
- [ ] **Test Coverage**: Tests included and pass
- [ ] **Code Quality**: Follows Python best practices
- [ ] **Documentation**: Docstrings and comments present
- [ ] **Error Handling**: Edge cases handled

### Performance

- [ ] **Startup Time**: Agent starts in < 30 seconds
- [ ] **Response Latency**: Prompt-to-response < 2 minutes
- [ ] **Memory Usage**: < 500MB total
- [ ] **Database Size**: Reasonable growth (< 10MB for test)

## Success Criteria

### Minimum Viable Test (MVT)

To consider the test **PASSED**, the following must be true:

1. ✅ **At least Scenario 1 completes successfully**
2. ✅ **Task creates working code** (calculator.py runs)
3. ✅ **Tests pass** (test_calculator.py passes)
4. ✅ **No system crashes** or unhandled exceptions
5. ✅ **State persisted correctly** (database has records)

### Full Test Success

For a **COMPLETE PASS**, all scenarios should:

1. ✅ Execute without system errors
2. ✅ Produce expected outcomes
3. ✅ Trigger breakpoints as designed
4. ✅ Handle errors gracefully
5. ✅ Maintain state consistency
6. ✅ Generate usable code

## Known Issues and Workarounds

### Issue 1: Claude Code CLI Not Found
**Symptom**: Agent fails to start, "command not found"
**Fix**:
```bash
which claude  # Check if in PATH
npm install -g @anthropics/claude-code  # Install if missing
```

### Issue 2: Ollama Connection Refused
**Symptom**: LLM validation fails, connection error
**Fix**:
```bash
systemctl start ollama  # Start Ollama service
# Or: ollama serve & # Start manually
curl http://localhost:11434/api/tags  # Verify running
```

### Issue 3: Rate Limiting
**Symptom**: Agent returns rate limit error
**Fix**: Wait for rate limit to reset (usually 1 minute), breakpoint system should handle automatically

### Issue 4: Workspace Permission Errors
**Symptom**: Agent can't write files
**Fix**:
```bash
mkdir -p /tmp/obra_test_run/workspace
chmod 755 /tmp/obra_test_run/workspace
```

### Issue 5: Database Locked
**Symptom**: "Database is locked" error
**Fix**: Close other connections, or use WAL mode:
```bash
sqlite3 data/orchestrator.db "PRAGMA journal_mode=WAL;"
```

## Test Artifacts

After test execution, the following artifacts will be available:

### Logs
- `logs/orchestrator.log` - Main application log
- `/tmp/obra_test_run/agent_*.log` - Agent-specific logs

### Database
- `data/orchestrator.db` - Complete state and history
- `test_run_dump.sql` - Database export for inspection

### Workspace
- `/tmp/obra_test_run/workspace/` - Generated code and files
- All modifications tracked with timestamps

### Reports
- `test_run_report.json` - Automated test results
- `test_run_coverage.html` - Code coverage report
- `test_run_logs.tar.gz` - Complete log archive

## Debugging

### Enable Verbose Logging

Edit `config/test_config.yaml`:
```yaml
logging:
  level: DEBUG  # Change from INFO

debug:
  enabled: true
  verbose_logging: true
```

### Monitor in Real-Time

```bash
# Terminal 1: Watch orchestrator log
tail -f logs/orchestrator.log

# Terminal 2: Watch agent process
watch -n 1 'ps aux | grep claude'

# Terminal 3: Watch file changes
watch -n 1 'ls -ltr /tmp/obra_test_run/workspace/'

# Terminal 4: Monitor database
watch -n 5 'sqlite3 data/orchestrator.db "SELECT id, status FROM tasks;"'
```

### Interactive Debugging

```python
# Start Python REPL
python

# Import Obra components
from src.core.config import Config
from src.core.state import StateManager
from src.agents.claude_code_local import ClaudeCodeLocalAgent

# Load config
config = Config.load('config/test_config.yaml')

# Test agent directly
agent = ClaudeCodeLocalAgent()
agent.initialize(config.get('agent.local'))
response = agent.send_prompt("Echo: Hello World")
print(response)
agent.cleanup()

# Inspect database
state = StateManager(config)
tasks = state.get_all_tasks(project_id=1)
for task in tasks:
    print(f"{task.id}: {task.status} - {task.description}")
```

## Next Steps After Testing

### If Tests Pass ✅

1. **Document Results**: Create test report with screenshots
2. **Production Deployment**: Deploy to production environment
3. **User Acceptance Testing**: Have users test with real projects
4. **Performance Tuning**: Optimize based on test metrics
5. **Feature Enhancements**: Implement v1.2 features

### If Tests Fail ❌

1. **Collect Artifacts**: Save logs, database, workspace
2. **Create Issue**: Document failure in GitHub issues
3. **Root Cause Analysis**: Debug using logs and state
4. **Fix and Retest**: Apply fixes and re-run tests
5. **Update Test Plan**: Adjust plan based on learnings

## Test Execution Timeline

| Phase | Duration | Cumulative |
|-------|----------|------------|
| Environment Setup | 5 min | 5 min |
| System Initialization | 2 min | 7 min |
| Scenario 1 (Happy Path) | 10-15 min | 17-22 min |
| Scenario 2 (Quality Control) | 15-20 min | 32-42 min |
| Scenario 3 (Confidence) | 15-20 min | 47-62 min |
| Scenario 4 (File Monitoring) | 10-15 min | 57-77 min |
| Scenario 5 (Recovery) | 15-20 min | 72-97 min |
| Scenario 6 (Multi-Iteration) | 20-30 min | 92-127 min |
| Validation & Reporting | 10 min | 102-137 min |
| **Total** | **~1.5-2.5 hours** | **Complete test suite** |

**Minimum Test**: Scenario 1 only = ~20 minutes

## Appendix: Test Data

### Sample Task Descriptions

**Simple Tasks** (for happy path testing):
- "Create a Python script that calculates fibonacci numbers"
- "Write a function to validate email addresses"
- "Implement a simple todo list in Python"

**Medium Complexity** (for quality/confidence testing):
- "Refactor this code to use design patterns"
- "Add comprehensive error handling and logging"
- "Optimize this code for performance"

**Complex Tasks** (for multi-iteration testing):
- "Create a REST API with FastAPI including auth and database"
- "Build a CLI tool with subcommands, config, and logging"
- "Implement a data pipeline with validation and transformations"

### Expected Quality Scores

| Task Type | Expected Quality | Expected Confidence |
|-----------|------------------|---------------------|
| Simple Implementation | 80-95 | 70-90 |
| Refactoring | 70-85 | 50-70 |
| Complex Feature | 60-80 | 40-60 |
| Ambiguous Task | 40-60 | 20-40 |

---

**Last Updated**: 2025-11-02
**Author**: Obra Development Team
**Status**: Ready for Execution
**Version**: 1.0
