# ADR-017 Implementation Startup Prompt (v2 - Test-First)

**Purpose**: Short prompt to start Claude Code implementation with test-first approach

**Version**: 2.0 (Enhanced with comprehensive testing)

---

## Startup Prompt

```
I need you to implement ADR-017 (Unified Execution Architecture) for the Obra project using a TEST-FIRST approach.

CONTEXT:
The alignment review identified that Obra's Natural Language interface bypasses the core validation pipeline. We're refactoring to route ALL commands through the orchestrator with unified execution.

CRITICAL INSIGHT FROM TESTING ANALYSIS:
While unit tests are excellent (88% coverage), integration testing has critical gaps:
- LLM connectivity: 0% coverage (HIGH RISK)
- Agent communication: 5% coverage (CRITICAL RISK)
- Orchestrator E2E: 10% coverage (CRITICAL RISK)

STRATEGY: TEST-FIRST REFACTORING
Build comprehensive testing infrastructure FIRST (Story 0), then use those tests to validate each refactoring step. This ensures high confidence and early issue detection.

PLANS AVAILABLE:
- Enhanced plan (with testing): docs/development/ADR017_ENHANCED_WITH_TESTING.yaml
- Testing enhancement summary: docs/development/ADR017_TESTING_ENHANCEMENT_SUMMARY.md
- Epic breakdown: docs/development/ADR017_UNIFIED_EXECUTION_EPIC_BREAKDOWN.md

START WITH STORY 0 (FOUNDATION - MOST IMPORTANT):
Read the enhanced plan (YAML) and begin with Story 0: Testing Infrastructure Foundation.

This includes:
1. Tier 1: Health Checks (7 tests, <30s)
2. Tier 1: Smoke Tests (10 tests, <60s)
3. Tier 2: LLM Integration (15 tests, 5-8 min)
4. Tier 3: Agent Integration (12 tests, 10-15 min)
5. THE CRITICAL TEST (test_full_workflow_create_project_to_execution)
6. Structured logging foundation
7. Metrics collection foundation

VALIDATION BEFORE PROCEEDING:
Before moving to Story 1, ALL of these must pass:
- pytest tests/health tests/smoke -v (17 tests in <2 min)
- pytest tests/integration/test_llm_connectivity.py -v (15 tests in 5-8 min)
- THE CRITICAL TEST must pass (validates E2E workflow)

If THE CRITICAL TEST passes, we have confidence the system works end-to-end and can proceed with refactoring.

IMPORTANT GUIDELINES:
- Follow the enhanced plan (ADR017_ENHANCED_WITH_TESTING.yaml)
- Story 0 is PREREQUISITE - must complete before any refactoring
- Use tests to validate each refactor step (Stories 1-5)
- Run tests frequently: pytest tests/health tests/smoke -v
- THE CRITICAL TEST is the single most important test
- No story complete until tests pass and docs updated

AFTER STORY 0:
Wait for my approval before proceeding to Story 1. We'll review the testing infrastructure together and run THE CRITICAL TEST to establish baseline.

QUESTIONS:
Ask if you need clarification on testing strategy, test implementation, or validation approach.

Let's begin with Story 0. Please read the enhanced YAML plan and start building the testing infrastructure.
```

---

## Alternative: Ultra-Concise Startup (If Context Already Loaded)

```
Begin ADR-017 implementation with TEST-FIRST approach.

Enhanced Plan: docs/development/ADR017_ENHANCED_WITH_TESTING.yaml

Start with Story 0 (Testing Infrastructure - FOUNDATION):
- Build health checks, smoke tests, integration tests
- Implement THE CRITICAL TEST
- Validate: All tests pass before Story 1

This is PREREQUISITE for refactoring. Test-first = high confidence.

Ready to start Story 0?
```

---

## What to Expect

### Story 0 (Week 1 - Testing Foundation)

**Claude will**:
1. Read the enhanced implementation plan
2. Create test directories: `tests/health/`, `tests/smoke/`, `tests/integration/`
3. Implement 44 tests across 4 tiers
4. Implement structured logging and metrics
5. Create CLI health command
6. Run tests and report results

**You should**:
1. Review test implementation quality
2. Verify THE CRITICAL TEST passes (most important validation)
3. Confirm health + smoke tests run in <2 minutes
4. Approve progression to Story 1 only if all tests pass

### Stories 1-5 (Weeks 2-3 - Refactoring)

**Claude will**:
1. Implement each story incrementally
2. Run tests after each story to validate
3. Report test results (pass/fail)
4. Request approval before next story

**You should**:
1. Review each story's output
2. Verify tests still passing
3. Approve progression only if tests pass
4. Monitor THE CRITICAL TEST especially

### Story 5 Complete (Week 3 - THE BIG MOMENT)

**Validation**:
```bash
# All tests must pass
pytest tests/ -v

# THE CRITICAL TEST must pass with unified architecture
pytest tests/integration/test_orchestrator_e2e.py::test_full_workflow_create_project_to_execution -v
```

**If passing**: Unified architecture is functional, proceed to Story 6

### Stories 6-10 (Week 4-5 - Polish & Release)

**Claude will**:
1. Add 45 unified execution specific tests
2. Update documentation
3. Implement safety enhancements
4. Add observability features
5. Prepare for release

---

## The Critical Test Explained

### What It Is

`test_full_workflow_create_project_to_execution()` in `tests/integration/test_orchestrator_e2e.py`

### What It Does

1. Creates project via StateManager
2. Creates task via NL command ("create task to add hello world Python script")
3. **Executes task through orchestrator with REAL Claude Code agent**
4. Validates file was created (`hello.py` exists)
5. Validates code quality (basic sanity check)
6. Validates metrics tracked

### What It Validates

- ✅ LLM connectivity functional
- ✅ NL command parsing accurate
- ✅ Task creation successful
- ✅ Orchestrator execution works
- ✅ Agent communication reliable
- ✅ File operations successful
- ✅ Quality validation applied
- ✅ **END-TO-END WORKFLOW COMPLETE**

### Why It's Critical

**If this test passes**: Core value proposition validated (LLM + Orchestrator + Agent = Autonomous Development)

**If this test fails**: Core product broken, DO NOT MERGE, DO NOT RELEASE

**Runtime**: 1-2 minutes with real LLM + real agent

---

## Progress Tracking

### Create Epic and Stories in Obra

```bash
# Create epic
obra epic create "Unified Execution Architecture (ADR-017)" --project 1 \
  --description "Route all commands through orchestrator with test-first approach" \
  --requires-adr true --has-architectural-changes true

# Create stories (get epic_id from above)
obra story create "Testing Infrastructure Foundation" --epic <epic_id> --project 1
obra story create "Architecture Documentation" --epic <epic_id> --project 1
obra story create "Create IntentToTaskConverter" --epic <epic_id> --project 1
obra story create "Refactor CommandExecutor" --epic <epic_id> --project 1
obra story create "Update NLCommandProcessor" --epic <epic_id> --project 1
obra story create "Unified Orchestrator Routing" --epic <epic_id> --project 1
obra story create "Integration Testing" --epic <epic_id> --project 1
obra story create "Documentation Updates" --epic <epic_id> --project 1
obra story create "Destructive Operation Breakpoints" --epic <epic_id> --project 1
obra story create "Confirmation UI Polish" --epic <epic_id> --project 1
obra story create "Observability Enhancements" --epic <epic_id> --project 1
```

### Track Progress

```bash
# Show epic progress
obra epic show <epic_id>

# Complete story when done
obra story complete <story_id>

# Check system health (after Story 0)
obra health
```

---

## Test Execution Quick Reference

### During Development (Continuous)

```bash
# Fast feedback loop
pytest tests/health tests/smoke -v
# 17 tests in <2 minutes
```

### Before Commit

```bash
# Same as development
pytest tests/health tests/smoke -v
# Must pass to commit
```

### Before Merge

```bash
# Health + smoke + LLM integration
pytest tests/health tests/smoke -v
pytest tests/integration/test_llm_*.py -v -m integration
# 32 tests in <10 minutes
```

### After Story 5 (Unified Architecture Live)

```bash
# THE BIG VALIDATION
pytest tests/integration/test_orchestrator_e2e.py::test_full_workflow_create_project_to_execution -v
# MUST PASS - validates unified architecture works
```

### Before Release

```bash
# Full test suite
pytest tests/ -v --timeout=3600
# 870+ tests in ~30 minutes
# 100% pass rate required
```

---

## Key Success Criteria

### Story 0 Complete
- [ ] 17 health + smoke tests passing (<2 min)
- [ ] 15 LLM integration tests passing (<10 min)
- [ ] 12 agent integration tests passing (<15 min)
- [ ] **THE CRITICAL TEST passing (most important)**
- [ ] Structured logging functional
- [ ] Metrics collection functional
- [ ] `obra health` command working

### Story 5 Complete (Unified Architecture)
- [ ] All 770+ existing tests passing
- [ ] All Story 0 tests still passing
- [ ] **THE CRITICAL TEST passing with unified architecture**
- [ ] Latency benchmarks met (<3s P95)

### v1.7.0 Release
- [ ] All 870+ tests passing (100% pass rate)
- [ ] THE CRITICAL TEST passing
- [ ] All tier 1-3 integration tests passing
- [ ] Documentation updated
- [ ] Performance validated

---

## Troubleshooting

### If Tests Fail During Story 0

**Problem**: Health checks failing (LLM connectivity)
**Solution**: Verify Ollama running, correct endpoint configured

**Problem**: THE CRITICAL TEST failing
**Solution**: Check LLM connectivity, agent availability, workspace setup

**Problem**: Performance tests failing (latency too high)
**Solution**: Expected with real LLM/agent, adjust thresholds if needed

### If Tests Fail During Refactoring (Stories 1-5)

**Problem**: Smoke tests failing after component change
**Solution**: Component change broke existing functionality, revert and fix

**Problem**: THE CRITICAL TEST failing after Story 5
**Solution**: CRITICAL - Unified architecture broken, must fix before proceeding

**Problem**: Performance degradation
**Solution**: Expected ~500ms increase for validation, acceptable

---

## Important Reminders

### Do Not Skip Story 0
- Testing infrastructure is PREREQUISITE, not optional
- Provides validation for each refactor step
- Catches integration issues early
- Builds confidence for refactoring

### THE CRITICAL TEST Is Non-Negotiable
- Most important single test in entire system
- Validates core value proposition
- Must pass before any release
- If it fails, core product is broken

### Use Tests for Validation
- Run tests after each story
- Don't proceed if tests fail
- Tests provide confidence
- Fast feedback saves time

### 1 Week Investment = 100+ Hours Saved
- Testing infrastructure adds 1 week
- Saves 100+ hours/year in manual testing
- Prevents 20-30 incidents/year
- Immediate ROI from first validated refactor

---

**Last Updated**: 2025-11-12
**Version**: 2.0 (Test-First Approach)
**Ready**: Yes - All plans and documentation complete
