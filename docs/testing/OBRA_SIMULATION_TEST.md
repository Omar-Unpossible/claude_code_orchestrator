# Obra Interactive Simulation Test

## Test Overview

**Objective**: Validate Obra's end-to-end orchestration capabilities by building a real CLI tool with full development lifecycle (design → implementation → testing → debugging → refinement).

**Scenario**: Build a **JSON-to-Markdown Report Generator** CLI tool that converts structured JSON data into formatted Markdown reports with configurable templates.

**Why This Test**:
- **Real-world complexity**: Multi-file project, CLI parsing, file I/O, templates, error handling
- **Clear success criteria**: Objective validation (working CLI + passing tests)
- **Tests Obra features**: NL commands, task hierarchy, quality validation, production logging, debugging
- **Achievable scope**: Can complete in 1-2 hour session
- **Demonstrates value**: Shows hybrid orchestration (Obra + Claude Code) vs direct Claude usage

---

## Success Criteria

### Must Have (P0)
1. ✅ Working CLI tool `json2md` with argument parsing
2. ✅ Converts JSON to Markdown with at least 2 templates (simple, detailed)
3. ✅ Unit tests with ≥80% coverage
4. ✅ Error handling (invalid JSON, missing files, bad templates)
5. ✅ README with usage examples
6. ✅ All tests passing (`pytest`)

### Should Have (P1)
7. ✅ Custom template support (user-provided Jinja2 templates)
8. ✅ Output file writing (not just stdout)
9. ✅ Integration test with real JSON fixtures
10. ✅ Type hints and docstrings

### Nice to Have (P2)
11. ⭐ CLI colors and formatting
12. ⭐ JSON schema validation
13. ⭐ Multiple output formats (Markdown, HTML)

---

## Test Phases

### Phase 1: Setup and Planning (10 mins)
**Goal**: Initialize Obra project and create task hierarchy

**Actions**:
1. Start Obra interactive mode
2. Create project via NL command
3. Create epic for the tool development
4. Create stories for each feature area
5. Verify task hierarchy

**Expected Obra Behavior**:
- NL intent classification works correctly
- Project/epic/story entities created
- Production log captures setup events
- No errors in task creation

**Validation**:
```bash
# Check production log
tail -f ~/obra-runtime/logs/production.jsonl | jq 'select(.event_type=="user_input" or .event_type=="execution_result")'
```

---

### Phase 2: Core Implementation (30 mins)
**Goal**: Implement working CLI with basic functionality

**Stories to Execute**:
1. **Story 1**: CLI argument parsing (Click or argparse)
2. **Story 2**: JSON loading and validation
3. **Story 3**: Markdown generation (simple template)
4. **Story 4**: Error handling and user feedback

**Expected Obra Behavior**:
- Each story creates tasks automatically
- Claude Code generates implementation
- Quality validation detects missing edge cases
- Obra requests clarification or improvement if quality < 70%

**Validation**:
```bash
# Run the tool manually
python json2md.py --input test.json --template simple --output report.md
```

---

### Phase 3: Testing and Validation (20 mins)
**Goal**: Add comprehensive tests and fix any bugs

**Stories to Execute**:
5. **Story 5**: Unit tests for each module
6. **Story 6**: Integration test with fixtures
7. **Story 7**: Bug fixes based on test failures

**Expected Obra Behavior**:
- Test failures trigger retry/refinement
- Production log shows quality scores improving
- Obra uses validation pipeline to verify fixes

**Validation**:
```bash
# Run tests
pytest --cov=json2md --cov-report=term

# Check coverage
coverage report
```

---

### Phase 4: Debugging and Iteration (20 mins)
**Goal**: Use production logs to identify and fix issues

**Deliberate Challenges** (test Obra's debugging):
- Introduce a failing test by requesting edge case
- Request feature that requires refactoring
- Simulate quality score drop (complex requirement)

**Expected Obra Behavior**:
- Production log shows low confidence/quality events
- Obra triggers breakpoint or clarification request
- Interactive checkpoints allow intervention
- Iterative improvement raises quality score

**Validation**:
```bash
# Analyze production log for debugging events
cat ~/obra-runtime/logs/production.jsonl | jq 'select(.event_type=="error" or .stage=="validation")'

# Check quality progression
cat ~/obra-runtime/logs/production.jsonl | jq 'select(.event_type=="nl_result") | {task: .task_id, confidence: .confidence, duration: .duration_ms}'
```

---

### Phase 5: Documentation and Completion (10 mins)
**Goal**: Finalize project with documentation

**Stories to Execute**:
8. **Story 8**: README with examples and installation
9. **Story 9**: Code cleanup and final validation

**Expected Obra Behavior**:
- Documentation maintenance system suggests updates
- Epic completion triggers maintenance task
- Git integration creates commit (if enabled)

**Validation**:
```bash
# Verify README exists and is complete
cat README.md

# Check git status
git status

# Verify final test run
pytest -v
```

---

## Simulation Instructions for Claude Code

### Prerequisites
```bash
# Ensure Obra is set up
cd /home/omarwsl/projects/claude_code_orchestrator

# Start Obra interactive mode
./scripts/startup/obra.sh

# Or alternative startup
python -m src.cli interactive
```

### Step-by-Step Execution

#### 1. Initialize Project (Phase 1)
```
# In Obra interactive terminal (natural language - no slash needed):

Create a new project called "JSON to Markdown Converter"

Create an epic for building a JSON-to-Markdown CLI tool with full testing

Create a story for CLI argument parsing in epic 1

Create a story for JSON loading and validation in epic 1

Create a story for Markdown generation in epic 1

Create a story for error handling in epic 1

Show me all stories for epic 1
```

#### 2. Execute Core Implementation (Phase 2)
```
# Execute each story sequentially:

Execute story 1

# Wait for completion, review output

Execute story 2

# Continue for all stories...

Show me the status of epic 1
```

#### 3. Add Testing (Phase 3)
```
Create a story for unit tests in epic 1

Create a story for integration tests in epic 1

Execute story 5

# After tests are created, run them:
/to-impl run pytest --cov

# If tests fail, create bug fix story:
Create a story for fixing test failures in epic 1
Execute story 7
```

#### 4. Debug Using Production Logs (Phase 4)
```
# Exit Obra temporarily to analyze logs:
/stop

# Check production log
tail -n 100 ~/obra-runtime/logs/production.jsonl | jq 'select(.event_type=="error" or .confidence < 0.7)'

# Resume Obra
./scripts/startup/obra.sh

# Based on log findings, request improvements:
Create a task to improve error handling based on production log findings

Execute task [ID]
```

#### 5. Finalize Documentation (Phase 5)
```
Create a story for README documentation in epic 1

Execute story 8

Show me the completion status of epic 1

# If all stories complete:
What's the final status of the JSON to Markdown project?
```

---

## Production Log Checkpoints

### Key Events to Monitor

**1. Intent Classification Success**:
```json
{
  "event_type": "nl_result",
  "intent": "COMMAND",
  "entity_type": "EPIC",
  "confidence": 0.95,
  "validation_status": "valid"
}
```

**2. Task Execution Quality**:
```json
{
  "event_type": "execution_result",
  "task_id": 123,
  "outcome": "success",
  "entities_affected": ["task:123"],
  "quality_score": 0.85
}
```

**3. Error Detection**:
```json
{
  "event_type": "error",
  "stage": "validation",
  "error_type": "QualityBelowThreshold",
  "task_id": 124
}
```

**4. Confidence Progression**:
```bash
# Track confidence over time
cat ~/obra-runtime/logs/production.jsonl | jq -r 'select(.event_type=="nl_result") | [.timestamp, .confidence, .task_id] | @tsv'
```

---

## Expected Outcomes

### Success Indicators
- ✅ All 9 stories completed successfully
- ✅ CLI tool works with test inputs
- ✅ Tests pass with ≥80% coverage
- ✅ Production log shows quality scores ≥0.7
- ✅ No unhandled errors in production log
- ✅ Epic marked complete
- ✅ Documentation exists and is accurate

### Failure Indicators
- ❌ Stories stuck in retry loop (quality never improves)
- ❌ NL commands misclassified (wrong entity type)
- ❌ Production log shows repeated errors
- ❌ Tests fail after multiple iterations
- ❌ Obra crashes or hangs
- ❌ Claude Code fails to generate working code

---

## Debugging Guide

### If NL Commands Fail
```bash
# Check LLM connection
python -m src.cli llm status

# Check intent classification
cat ~/obra-runtime/logs/production.jsonl | jq 'select(.event_type=="nl_result" and .validation_status=="invalid")'
```

### If Quality Scores Low
```bash
# Check validation failures
cat ~/obra-runtime/logs/production.jsonl | jq 'select(.stage=="validation" and .quality_score < 0.7)'

# Request explicit improvement:
/to-impl Please improve the code quality based on validation feedback
```

### If Obra Hangs
```bash
# Check for deadlocks
cat ~/obra-runtime/logs/production.jsonl | jq 'select(.event_type=="error" and .error_type=="Timeout")'

# Use interactive checkpoint:
/pause
/status
/resume
```

---

## Test Deliverables

### At End of Simulation

**1. Working Code**:
- `json2md/` directory with Python CLI tool
- `tests/` directory with pytest tests
- `README.md` with usage instructions

**2. Validation Report**:
```bash
# Generate validation report
echo "=== Test Results ===" > simulation_report.txt
pytest -v >> simulation_report.txt
echo "\n=== Coverage ===" >> simulation_report.txt
pytest --cov=json2md --cov-report=term >> simulation_report.txt
echo "\n=== Production Log Summary ===" >> simulation_report.txt
cat ~/obra-runtime/logs/production.jsonl | jq -s 'group_by(.event_type) | map({event: .[0].event_type, count: length})' >> simulation_report.txt
```

**3. Production Log Analysis**:
- Count of each event type
- Average confidence scores
- Quality score progression
- Error rate and types
- Total duration

**4. Lessons Learned**:
- What worked well?
- What failed or struggled?
- Obra bugs discovered?
- UX improvements needed?
- Performance bottlenecks?

---

## Extending the Test

### Additional Challenges (Optional)

**1. Multi-Epic Workflow**:
- Create Epic 2: "Add HTML Output Format"
- Create Epic 3: "Add JSON Schema Validation"
- Test epic dependency management

**2. Deliberate Failures**:
- Request impossible requirement (test Obra's pushback)
- Introduce syntax errors (test quality validation)
- Break tests (test debugging workflow)

**3. Advanced Features**:
- Enable git auto-commit
- Create milestone for v1.0 release
- Test maintenance task creation

---

## Post-Test Analysis

### Questions to Answer

1. **Functionality**: Did the simulation achieve all P0 success criteria?
2. **Quality**: What was the average quality score? Confidence?
3. **Efficiency**: How many iterations per story? Total time?
4. **Robustness**: How many errors? Were they handled gracefully?
5. **UX**: Was the NL interface intuitive? Any confusion?
6. **Logging**: Did production logs provide actionable debugging info?
7. **Value**: Would this be faster/better with Obra vs direct Claude usage?

### Metrics to Extract

```bash
# Total tasks created
cat ~/obra-runtime/logs/production.jsonl | jq -s '[.[] | select(.event_type=="execution_result")] | length'

# Success rate
cat ~/obra-runtime/logs/production.jsonl | jq -s '[.[] | select(.event_type=="execution_result")] | group_by(.outcome) | map({outcome: .[0].outcome, count: length})'

# Average quality
cat ~/obra-runtime/logs/production.jsonl | jq -s '[.[] | select(.quality_score != null) | .quality_score] | add / length'

# Average confidence
cat ~/obra-runtime/logs/production.jsonl | jq -s '[.[] | select(.confidence != null) | .confidence] | add / length'
```

---

## Timeline Estimate

- **Phase 1** (Setup): 10 minutes
- **Phase 2** (Implementation): 30 minutes
- **Phase 3** (Testing): 20 minutes
- **Phase 4** (Debugging): 20 minutes
- **Phase 5** (Documentation): 10 minutes
- **Total**: ~90 minutes

**Note**: Actual time may vary based on:
- Claude Code response latency
- Quality validation iterations
- Debugging complexity
- Your intervention frequency

---

## Success Definition

This simulation is **successful** if:

1. ✅ All P0 criteria met (working CLI + tests)
2. ✅ Epic completed without crashes
3. ✅ Production logs show quality ≥0.7
4. ✅ Deliverables match specifications
5. ✅ Claude Code can follow instructions autonomously

This simulation is **exceptional** if:

6. ⭐ All P1 criteria met (custom templates, integration tests)
7. ⭐ Quality scores ≥0.85 on first iteration
8. ⭐ Zero errors in production log
9. ⭐ Demonstrates clear value over direct Claude usage
10. ⭐ Discovers and fixes Obra bugs during test

---

**Last Updated**: 2025-11-15
**Test Type**: End-to-End Simulation
**Estimated Duration**: 90 minutes
**Difficulty**: Medium (realistic complexity)
**Obra Version**: v1.8.0+
