# ADR-017 Complete Implementation Plan - Summary

**Created**: 2025-11-12
**Status**: Ready for Implementation
**Approach**: Test-First Architectural Refactoring

---

## Executive Summary

I've created a **comprehensive, test-first implementation plan** for ADR-017 (Unified Execution Architecture) that integrates insights from the Testing Gap Analysis. The plan now includes **11 stories** (originally 9) over **4-5 weeks** with testing infrastructure built FIRST to validate the refactor at each step.

### Key Enhancement

**Original Plan**: Refactor → Test
**Enhanced Plan**: Test Infrastructure → Refactor (validated at each step) → Release

**Why**: Testing Gap Analysis revealed critical integration gaps (LLM connectivity 0%, agent communication 5%, orchestrator E2E 10%). Building tests first provides confidence and early issue detection.

---

## What's Been Delivered

### 📋 Core Planning Documents

1. **ADR017_UNIFIED_EXECUTION_EPIC_BREAKDOWN.md** (31 KB)
   - Human-readable epic breakdown
   - 9 detailed story descriptions
   - Business value, risks, release plan
   - **Status**: Original plan (9 stories)

2. **ADR017_UNIFIED_EXECUTION_IMPLEMENTATION_PLAN.yaml** (56 KB)
   - Machine-optimized for Claude Code
   - Detailed implementation steps
   - Test coverage requirements
   - **Status**: Original plan (9 stories)

3. **ADR017_ENHANCED_WITH_TESTING.yaml** (66 KB) ⭐ **USE THIS**
   - **Enhanced with comprehensive testing**
   - 11 stories (added Story 0 + Story 10)
   - Test-first approach with validation at each step
   - THE CRITICAL TEST as quality gate
   - **Status**: ENHANCED - Primary implementation plan

4. **ADR-017-unified-execution-architecture.md** (13 KB)
   - Architecture Decision Record
   - Problem, decision, consequences
   - Alternatives considered
   - **Status**: Complete ADR stub

### 📊 Testing Enhancement Documents

5. **ADR017_TESTING_ENHANCEMENT_SUMMARY.md** (15 KB) ⭐ **READ THIS**
   - Explains test-first approach
   - THE CRITICAL TEST explained
   - Story 0 details
   - Before/after comparison
   - **Status**: Complete enhancement explanation

6. **ADR017_STARTUP_PROMPT.md** (4 KB)
   - Original startup prompt
   - **Status**: Original (9 stories)

7. **ADR017_STARTUP_PROMPT_V2.md** (8 KB) ⭐ **USE THIS**
   - **Enhanced with test-first approach**
   - Instructions for Story 0 first
   - Validation criteria before proceeding
   - **Status**: ENHANCED - Primary startup prompt

### 📖 Reference Documents (Input)

8. **Testing Gap Analysis Summary** (docs/testing/)
   - Identified critical integration gaps
   - Proposed 4-tier testing strategy
   - **Status**: Input for enhancement

9. **Integration Testing Enhancement Plan** (docs/testing/)
   - Detailed testing strategy
   - Tier breakdowns with examples
   - **Status**: Input for enhancement

---

## The Enhanced Plan at a Glance

### Timeline: 4-5 Weeks (Originally 2-3 Weeks)

| Week | Stories | Focus | Deliverables |
|------|---------|-------|--------------|
| **1** | Story 0 | **Testing Foundation** | 44 tests, THE CRITICAL TEST, observability |
| **2** | 1-3 | Architecture + Core | ADR-017, IntentToTaskConverter, NLQueryHelper |
| **3** | 4-5 | Unified Routing | NL routing, orchestrator integration |
| **4** | 6-7 | Testing + Docs | 45 new tests, documentation updates |
| **5** | 8-10 | Safety + Observability | Confirmations, monitoring, CLI commands |

### Investment: +1 Week (+24 Hours)

**Why**: Testing infrastructure is prerequisite, not optional

**ROI**:
- Saves 100+ hours/year in manual testing
- Prevents 20-30 incidents/year
- 95%+ of issues caught automatically
- Immediate payback from first validated refactor

---

## Story 0: Testing Infrastructure (NEW - CRITICAL)

### Why Story 0 Is FIRST

**Problem**: Original plan had testing in Story 6 (after refactor)
**Issue**: Can't validate refactor without tests
**Solution**: Build tests FIRST, use them to validate each refactor step

### What Story 0 Delivers

#### Tier 1: Health Checks (7 tests, <30s)
- LLM connectivity (Ollama + OpenAI Codex)
- Database connectivity
- Agent/LLM registries
- Configuration validation
- StateManager initialization

**Purpose**: Fast validation all systems operational
**Run**: Every commit (fast quality gate)

#### Tier 1: Smoke Tests (10 tests, <60s)
- Project/epic/story/task creation
- NL command parsing
- LLM status/reconnect
- StateManager CRUD
- Orchestrator initialization

**Purpose**: Core workflows validated
**Run**: Every commit

#### Tier 2: LLM Integration (15 tests, 5-8 min)
- Ollama connection success/failure
- OpenAI Codex connection
- LLM switching (Ollama ↔ Codex)
- Timeout and retry
- Performance baselines

**Purpose**: LLM connectivity validated
**Run**: Before merge, nightly

#### Tier 3: Agent Integration (12 tests, 10-15 min)
- Claude Code agent connectivity
- Session management (per-iteration)
- **THE CRITICAL TEST** ⭐
- Quality feedback loops
- Multi-task epics
- Task dependencies
- Git integration E2E

**Purpose**: Core orchestration validated
**Run**: Before merge (with label), nightly

#### Observability Foundation
- Structured logging (JSON events)
- Metrics collection (LLM, agent, NL)
- Health check endpoint (`obra health`)

**Purpose**: Better debugging and monitoring
**Integration**: All critical paths

### THE CRITICAL TEST ⭐

**Name**: `test_full_workflow_create_project_to_execution()`
**Location**: `tests/integration/test_orchestrator_e2e.py`

**What It Does**:
1. Creates project via StateManager
2. Creates task via NL command
3. **Executes task through orchestrator with REAL Claude Code agent**
4. Validates file created
5. Validates code quality
6. Validates metrics tracked

**What It Validates**:
- LLM connectivity works
- NL parsing accurate
- Task creation successful
- Orchestrator execution works
- Agent communication reliable
- File operations work
- Quality validation applied
- **END-TO-END WORKFLOW COMPLETE**

**Importance**: **CRITICAL** - If this fails, core product is broken

**Success Criteria**: Test passes in <2 minutes with real LLM + real agent

**Failure Impact**: DO NOT MERGE, DO NOT RELEASE until fixed

---

## How Tests Validate Refactoring

### Validation at Each Step

```
Story 0: Build Tests
    ↓
THE CRITICAL TEST passes (baseline established)
    ↓
Story 1: Architecture Docs
    ├─ Validation: Run smoke tests (no code changes, should pass)
    ↓
Story 2: IntentToTaskConverter
    ├─ Validation: Run smoke tests (should still pass)
    ├─ Validation: THE CRITICAL TEST (not using new component yet)
    ↓
Story 3: NLQueryHelper Refactor
    ├─ Validation: NL smoke tests (renamed component works)
    ├─ Validation: LLM integration tests (NL pipeline functional)
    ↓
Story 4: NLCommandProcessor Update
    ├─ Validation: ALL smoke tests (CRITICAL - this changes NL behavior)
    ├─ Validation: ALL LLM integration tests
    ├─ Validation: ALL agent tests
    ↓
Story 5: Unified Orchestrator Routing ⭐ THE BIG MOMENT
    ├─ Validation: ALL health + smoke tests
    ├─ Validation: ALL integration tests
    ├─ Validation: THE CRITICAL TEST MUST PASS ← Unified architecture validated
    ↓
Story 6: Integration Testing (Enhanced)
    ├─ Add 45 new unified execution tests
    ├─ Validation: All 870+ tests passing
    ↓
Story 7-10: Polish, Safety, Observability
    └─ Validation: Continuous testing throughout
```

### Key Validation Points

**After Story 0**: All 44 tests passing, THE CRITICAL TEST passes (baseline)
**After Story 5**: THE CRITICAL TEST passes with unified architecture (SUCCESS)
**Before v1.7.0**: All 870+ tests passing, performance validated (RELEASE)

---

## Story 10: Observability Enhancements (NEW)

### What It Adds

**Duration**: 8 hours
**Priority**: P2
**Release**: v1.7.1

### Deliverables

#### Enhanced Structured Logging
- **Correlation IDs**: Track requests end-to-end across all components
- **Log Filtering**: Query by event, level, correlation ID, time
- **Context Managers**: Automatic correlation ID propagation

#### Metrics v2
- **Alerting Thresholds**: LLM success rate, latency, agent success
- **Trend Detection**: Sliding window analysis, anomaly detection
- **CLI Commands**: `obra health`, `obra metrics`, `obra logs`

### Example Usage

```bash
# Check system health
$ obra health
Status: HEALTHY ✅
LLM: Ollama (qwen2.5-coder:32b)
  - Available: Yes
  - Success Rate: 98.2%
  - Latency P95: 1234ms

# View metrics
$ obra metrics --window=1h
LLM Requests: 156
Success Rate: 97.4% (↑ 2%)
Latency P95: 1523ms (↓ 200ms)

# Query logs
$ obra logs --event=nl_command --since='5 minutes ago'
[nl_command] correlation_id=abc123
  command: "create epic for auth"
  success: true
```

---

## Test Coverage Comparison

### Before Enhancement

| Area | Coverage | Tests | Risk |
|------|----------|-------|------|
| LLM Connectivity | 0% | 0 | HIGH ⚠️ |
| Agent Communication | 5% | ~3 | CRITICAL 🔴 |
| Orchestrator E2E | 10% | ~5 | CRITICAL 🔴 |
| Health Checks | 0% | 0 | HIGH ⚠️ |
| Total Tests | 88% code | 770 | MEDIUM |

**Problem**: Excellent unit tests, insufficient integration tests

### After Enhancement

| Area | Coverage | Tests | Risk |
|------|----------|-------|------|
| LLM Connectivity | 100% | 15 | LOW ✅ |
| Agent Communication | 80% | 12 | LOW ✅ |
| Orchestrator E2E | 90% | 57 | LOW ✅ |
| Health Checks | 100% | 17 | NONE ✅ |
| Total Tests | 90% code | 870+ | LOW ✅ |

**Result**: Comprehensive integration coverage, high confidence

---

## Test Execution Strategy

### Development (Continuous)
```bash
pytest tests/health tests/smoke -v
# 17 tests in <2 minutes
```
**Run**: Continuously during development
**Purpose**: Fast feedback

### Pre-Commit
```bash
pytest tests/health tests/smoke -v
# 17 tests in <2 minutes
```
**Run**: Before every commit
**Gate**: Must pass to commit

### Pre-Merge
```bash
pytest tests/health tests/smoke -v
pytest tests/integration/test_llm_*.py -v -m integration
# 32 tests in <10 minutes
```
**Run**: Before merge to main
**Gate**: Must pass to merge

### Nightly
```bash
pytest tests/ -v --timeout=3600
# 870+ tests in ~30 minutes
```
**Run**: Every night
**Gate**: Alert if failures

### Before Release
```bash
pytest tests/ -v --timeout=3600
pytest tests/integration/test_orchestrator_e2e.py::test_full_workflow_create_project_to_execution -v
# Full suite + THE CRITICAL TEST
```
**Run**: Before every release
**Gate**: 100% pass rate required

---

## Getting Started

### Recommended Approach: Start Fresh

Use the **enhanced startup prompt** (v2) to begin with test-first approach:

**File**: `docs/development/ADR017_STARTUP_PROMPT_V2.md`

**Quick Start**:
```
Copy the startup prompt from ADR017_STARTUP_PROMPT_V2.md into a fresh Claude Code context window.

The prompt instructs Claude to:
1. Read ADR017_ENHANCED_WITH_TESTING.yaml
2. Start with Story 0 (Testing Infrastructure)
3. Validate all tests pass before proceeding to Story 1
4. Use tests to validate each refactor step
```

### Alternative: Obra Epic Execution

```bash
# 1. Create epic
obra epic create "Unified Execution Architecture (ADR-017)" --project 1 \
  --description "Route all commands through orchestrator with test-first approach" \
  --requires-adr true --has-architectural-changes true

# 2. Create 11 stories (use epic_id from above)
obra story create "Testing Infrastructure Foundation" --epic <epic_id> --project 1
obra story create "Architecture Documentation" --epic <epic_id> --project 1
obra story create "Create IntentToTaskConverter" --epic <epic_id> --project 1
# ... (repeat for all 11 stories)

# 3. Execute epic
obra epic execute <epic_id>
```

---

## Success Criteria

### Story 0 Complete (Week 1)
- [ ] 17 health + smoke tests passing (<2 min)
- [ ] 15 LLM integration tests passing (<10 min)
- [ ] 12 agent integration tests passing (<15 min)
- [ ] **THE CRITICAL TEST passing** ⭐
- [ ] Structured logging functional
- [ ] Metrics collection functional
- [ ] `obra health` command working

### Story 5 Complete (Week 3 - Unified Architecture Live)
- [ ] All 770+ existing tests passing
- [ ] All Story 0 tests still passing
- [ ] **THE CRITICAL TEST passing with unified architecture** ⭐
- [ ] Latency benchmarks met (<3s P95)
- [ ] No regressions

### v1.7.0 Release (Week 4)
- [ ] All 870+ tests passing (100% pass rate)
- [ ] THE CRITICAL TEST passing
- [ ] All tier 1-3 integration tests passing
- [ ] Documentation updated (8 files)
- [ ] Performance validated
- [ ] Ready for production

### v1.7.1 Release (Week 5)
- [ ] Confirmation workflow functional
- [ ] Observability enhancements live
- [ ] CLI commands working
- [ ] Production-ready monitoring

---

## Cost/Benefit Analysis

### Investment
- **Time**: +1 week for testing infrastructure
- **Effort**: 84-104 hours (was 60-80 hours)
- **Increase**: +40% implementation time

### Return
- **Confidence**: 95%+ of workflow issues caught automatically
- **Speed**: Manual testing reduced from 30min → 5min per feature
- **Prevention**: ~20-30 incidents/year prevented
- **Debugging**: 10x faster with structured logs
- **Monitoring**: Real-time health checks and metrics

### ROI
- **Time Saved**: ~100 hours/year in manual testing
- **Incidents Prevented**: ~20-30/year
- **Developer Velocity**: +30% (faster feedback, less debugging)
- **Payback Period**: Immediate (first refactor step validated)

**Net Benefit**: 100 hours saved - 24 hours invested = **76 hours year 1**, plus ongoing benefits

---

## Key Documents Reference

### Primary Implementation Documents (Use These)

1. **ADR017_ENHANCED_WITH_TESTING.yaml** ⭐
   - Machine-optimized plan for Claude Code
   - Includes all 11 stories with testing integration
   - **USE THIS for implementation**

2. **ADR017_TESTING_ENHANCEMENT_SUMMARY.md** ⭐
   - Human-readable explanation
   - Test-first approach explained
   - Before/after comparison
   - **READ THIS first to understand approach**

3. **ADR017_STARTUP_PROMPT_V2.md** ⭐
   - Enhanced startup prompt
   - Instructions for Story 0 first
   - Validation criteria
   - **USE THIS to start Claude Code**

### Reference Documents

4. **ADR017_UNIFIED_EXECUTION_EPIC_BREAKDOWN.md**
   - Original 9-story plan
   - Business value, risks, release plan
   - Good for context, but use enhanced plan

5. **ADR017_UNIFIED_EXECUTION_IMPLEMENTATION_PLAN.yaml**
   - Original machine-optimized plan
   - Good for reference, but use enhanced version

6. **ADR-017-unified-execution-architecture.md**
   - Architecture Decision Record
   - Problem, decision, consequences
   - Complete ADR documentation

### Testing Documents (Input)

7. **docs/testing/TESTING_GAP_ANALYSIS_SUMMARY.md**
   - Identified integration gaps
   - Proposed 4-tier strategy

8. **docs/testing/INTEGRATION_TESTING_ENHANCEMENT_PLAN.md**
   - Detailed testing strategy
   - Examples and implementation details

---

## Important Reminders

### Do Not Skip Story 0
- Testing infrastructure is PREREQUISITE, not optional
- Provides validation for each refactor step
- Catches integration issues early during refactor, not after
- Builds confidence for proceeding

### THE CRITICAL TEST Is Non-Negotiable
- Most important single test in entire system
- Validates core value proposition
- Must pass before any release
- If it fails, core product is broken
- Run after Story 0, after Story 5, before v1.7.0

### Test-First = High Confidence
- Build tests first, refactor second
- Use tests to validate each step
- Don't proceed if tests fail
- Fast feedback saves time and prevents costly rework

### 1 Week Investment = High ROI
- Testing infrastructure adds 1 week
- Saves 100+ hours/year in manual testing
- Prevents 20-30 incidents/year
- Immediate ROI from first validated refactor
- Every refactor step validated = confidence

---

## Questions?

### Why add Story 0?
**Answer**: Testing infrastructure is prerequisite for test-first refactoring. It provides validation at each step, catches issues early, and builds confidence.

### Can we skip testing and do it later?
**Answer**: No. Testing after refactoring is too late. Benefits of test-first:
- Early detection during refactor
- Regression prevention
- Confidence before proceeding
- Validation at each step

### Why 1 additional week?
**Answer**: Testing infrastructure is not optional overhead—it's foundation. ROI is immediate from first validated refactor step, plus ongoing benefits (100+ hours/year saved).

### What if THE CRITICAL TEST fails?
**Answer**: Core product is broken. DO NOT proceed, DO NOT merge, DO NOT release. Fix issue, verify test passes, then continue.

---

## Ready to Begin?

### Next Steps

1. **Review**: Read `ADR017_TESTING_ENHANCEMENT_SUMMARY.md` to understand approach
2. **Plan**: Review `ADR017_ENHANCED_WITH_TESTING.yaml` for detailed implementation
3. **Start**: Copy startup prompt from `ADR017_STARTUP_PROMPT_V2.md` into fresh Claude Code context
4. **Validate**: After Story 0, verify all 44 tests pass and THE CRITICAL TEST passes
5. **Proceed**: Only proceed to Story 1 if all validation passes
6. **Iterate**: Use tests to validate each subsequent story
7. **Release**: v1.7.0 when all 870+ tests pass, v1.7.1 with observability

### Your Role

- **Week 1**: Review Story 0 implementation, verify tests pass
- **Weeks 2-3**: Approve each story only if tests still pass
- **Week 3**: Validate THE CRITICAL TEST passes with unified architecture (key milestone)
- **Week 4**: Review integration tests and documentation
- **Week 5**: Review observability features, approve releases

---

**Document Version**: 1.0
**Created**: 2025-11-12
**Status**: Complete - Ready for Implementation
**Approach**: Test-First Architectural Refactoring
**Total Investment**: 4-5 weeks (84-104 hours)
**Expected ROI**: 100+ hours/year saved, 20-30 incidents prevented
