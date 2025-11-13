# Story 0 + Enhancements - Startup Prompt

**Version**: 1.0
**Date**: November 13, 2025
**Target Release**: v1.7.2
**Total Effort**: 25-27 hours (3-4 days)

---

## Quick Start

```
I need you to complete Story 0 (Testing Infrastructure Foundation) and implement
Enhancements 3-5 for the Obra project, targeting v1.7.2 release.

COMPREHENSIVE PLAN AVAILABLE:
docs/development/STORY0_AND_ENHANCEMENTS_IMPLEMENTATION_PLAN.md (400+ lines)

READ THIS PLAN FIRST - It contains detailed implementation guidance for:
- Story 0: Testing Infrastructure (44 tests across 3 tiers)
- Enhancement 3: NL Command Completion Tests (4h)
- Enhancement 4: Consolidate Test Documentation (2h)
- Enhancement 5: Extract Common Test Fixtures (3h)

WORK IN PHASES:

Phase 1: Story 0 Testing Infrastructure (16 hours, 2 days)
  - Part A: LLM Integration Tests (15 tests)
  - Part B: Agent Integration Tests (12 tests) + THE CRITICAL TEST ⭐
  - Part C: Structured Logging & Metrics Foundation
  - Part D: obra health CLI command

Phase 2: Test Execution & Validation (2 hours)
  - Run all test tiers (Tier 1, 2, 3)
  - Validate THE CRITICAL TEST passes
  - Document performance baselines

Phase 3: Enhancement 3 - NL Command Completion Tests (4 hours)
  - Discovery: Check if feature exists
  - Implementation: 10-15 tests OR proposal document

Phase 4: Enhancement 4 - Consolidate Documentation (2 hours)
  - Archive 11+ historical ADR017 files
  - Create implementation summary

Phase 5: Enhancement 5 - Extract Test Fixtures (3 hours)
  - Extract 6 common fixtures to tests/conftest.py
  - Update 50-70 test functions

Phase 6: Documentation & Release (1 hour)
  - Update CHANGELOG.md, CLAUDE.md
  - Create release notes for v1.7.2
  - Git tag: v1.7.2

CRITICAL REQUIREMENTS:

1. THE CRITICAL TEST must pass before proceeding to enhancements
   - This is the single most important validation
   - If it fails, stop and debug immediately

2. All test tiers must pass (100% pass rate required)
   - Tier 1 (17 tests): <2 min
   - Tier 2 (15 tests): 5-8 min
   - Tier 3 (12 tests): 10-15 min

3. Follow TEST_GUIDELINES.md
   - Max sleep: 0.5s per test
   - Max threads: 5 per test with mandatory timeout
   - No WSL2 crashes

4. Use TodoWrite tool to track progress
   - Create todos for each phase
   - Update status as you work
   - Mark complete only when validated

VALIDATION GATES:

After Story 0 (Phase 1-2):
  - All 44 tests implemented and passing
  - THE CRITICAL TEST passing (<2 min) ⭐
  - obra health command working
  - Performance baselines documented

After Enhancements (Phase 3-5):
  - NL completion: Tests added OR proposal created
  - Documentation: 11+ files archived, summary created
  - Fixtures: 6 extracted, 50-70 tests updated
  - All tests still passing (100% pass rate)

Before Release (Phase 6):
  - CHANGELOG.md updated
  - CLAUDE.md version updated to v1.7.2
  - Release notes created
  - Git tag created

IMPORTANT NOTES:

- Read the full implementation plan before starting
- Ask questions if anything is unclear
- Report progress after each phase
- Run tests frequently (pytest tests/health tests/smoke -v)
- THE CRITICAL TEST is the most important validation

Let's begin with Phase 1: Story 0 Testing Infrastructure.
Please confirm you've read the plan and are ready to start.
```

---

## Alternative: Ultra-Concise (If Plan Already Read)

```
Begin Story 0 + Enhancements implementation for v1.7.2.

Plan: docs/development/STORY0_AND_ENHANCEMENTS_IMPLEMENTATION_PLAN.md

Start with Phase 1 (Story 0 - Testing Infrastructure):
- 15 LLM integration tests
- 12 agent integration tests
- THE CRITICAL TEST (most important)
- Structured logging & metrics
- obra health command

Validation: All 44 tests passing, THE CRITICAL TEST <2 min.

Ready to start Phase 1?
```

---

## What to Expect

### Phase 1 (Days 1-2: Story 0 Foundation)

**Claude will**:
1. Read the implementation plan
2. Create `tests/integration/test_llm_connectivity.py` (15 tests)
3. Create `tests/integration/test_agent_connectivity.py` (12 tests)
4. Enhance `src/core/logging_config.py` (structured logging)
5. Enhance `src/core/metrics.py` (metrics collection)
6. Add `obra health` command to `src/cli.py`
7. Run all tests and report results
8. **Run THE CRITICAL TEST** and verify it passes

**Expected Output**:
```
Story 0 Implementation Complete ✅

Tests Created:
- tests/integration/test_llm_connectivity.py (15 tests)
- tests/integration/test_agent_connectivity.py (12 tests)
- tests/health/test_system_health.py (7 tests - existing)
- tests/smoke/test_smoke_workflows.py (10 tests - existing)

Test Results:
- Tier 1 (17 tests): PASSED in 1.2 min ✓
- Tier 2 (15 tests): PASSED in 6.3 min ✓
- Tier 3 (12 tests): PASSED in 12.1 min ✓
- THE CRITICAL TEST: PASSED in 1.8 min ⭐

Infrastructure:
- Structured logging: Integrated
- Metrics collection: Functional
- obra health command: Working

Performance Baselines:
- Intent classification P95: 987ms
- Entity extraction P95: 1432ms
- Full NL pipeline P95: 2.8s

Ready for Phase 2: Test Validation
```

---

### Phase 2 (Day 3: Test Validation)

**Claude will**:
1. Run comprehensive test suite
2. Validate all test tiers pass
3. Document performance baselines
4. Generate test report

**Expected Output**:
```
Test Validation Complete ✅

Full Test Suite:
- Total tests: 844+ (800 existing + 44 new)
- Pass rate: 100%
- Coverage: 88% (maintained)
- Duration: ~28 minutes

Performance:
- P95 latency: 2.8s < 3s ✓
- Throughput: 45 cmd/min > 40 ✓

THE CRITICAL TEST: PASSING ⭐
This validates the core product works end-to-end.

Baselines documented in test output.

Ready for Phase 3: Enhancement 3
```

---

### Phase 3 (Day 4: NL Command Completion)

**Claude will**:
1. Search for NL command completion feature
2. If found: Implement 10-15 tests
3. If not found: Create proposal document
4. Report findings

**Expected Output (If Feature Exists)**:
```
Enhancement 3 Complete ✅

Discovery:
- Feature found: src/cli.py (tab completion)
- Implementation: Click shell completion

Tests Created:
- tests/test_nl_command_completion.py (12 tests)
- All tests passing

Documentation:
- docs/guides/NL_COMMAND_COMPLETION_GUIDE.md (created)

Ready for Phase 4: Documentation Consolidation
```

**Expected Output (If Feature Does NOT Exist)**:
```
Enhancement 3 Complete ✅

Discovery:
- Feature not found in codebase
- Git history: No completion commits

Proposal Created:
- docs/design/enhancements/NL_COMMAND_COMPLETION_PROPOSAL.md
- Estimated effort: 8-12 hours

Ready for Phase 4: Documentation Consolidation
```

---

### Phase 4 (Day 5: Documentation Consolidation)

**Claude will**:
1. Audit ADR017 documentation files (14+)
2. Move 11+ files to archive
3. Create archive README
4. Create implementation summary

**Expected Output**:
```
Enhancement 4 Complete ✅

Files Archived:
- 8 startup prompts → docs/archive/adr017_startup_prompts/
- 3 planning docs → docs/archive/adr017_planning/

Files Kept (Active):
- ADR017_UNIFIED_EXECUTION_IMPLEMENTATION_PLAN.yaml
- ADR017_ENHANCED_WITH_TESTING.yaml
- ADR017_IMPLEMENTATION_EVALUATION_REPORT.md

Documentation Created:
- docs/archive/adr017_planning/README.md (navigation)
- docs/development/ADR017_IMPLEMENTATION_SUMMARY.md (lessons learned)

All links verified ✓

Ready for Phase 5: Extract Test Fixtures
```

---

### Phase 5 (Day 6: Extract Test Fixtures)

**Claude will**:
1. Audit test files for duplicate fixtures
2. Extract 6 common fixtures to tests/conftest.py
3. Update 50-70 test functions
4. Verify all tests still pass

**Expected Output**:
```
Enhancement 5 Complete ✅

Fixtures Extracted (tests/conftest.py):
- mock_parsed_intent() - Factory for ParsedIntent
- mock_operation_context() - Factory for OperationContext
- test_project_with_tasks() - Pre-populated project
- mock_llm_plugin() - Mock LLM with responses
- temp_workspace() - Enhanced temp workspace
- test_config() - Standard test configuration

Tests Updated:
- tests/test_intent_to_task_converter.py (33 functions)
- tests/integration/test_orchestrator_nl_integration.py (12 functions)
- tests/integration/test_adr017_*.py (17 functions)
- Total: 62 test functions updated

Benefits:
- LOC reduced: 247 lines
- Maintenance: 40% easier (1 fixture vs 5+ copies)
- Readability: Improved (less boilerplate)

All tests passing: 844/844 ✓

Ready for Phase 6: Documentation & Release
```

---

### Phase 6 (Day 7: Documentation & Release)

**Claude will**:
1. Update CHANGELOG.md with v1.7.2 entry
2. Update CLAUDE.md version to v1.7.2
3. Create release notes
4. Create git tag

**Expected Output**:
```
Phase 6 Complete - v1.7.2 Ready for Release ✅

Documentation Updated:
- CHANGELOG.md (v1.7.2 entry added)
- CLAUDE.md (version updated to v1.7.2)
- docs/release_notes/RELEASE_v1.7.2.md (created)

Git Tag Created:
- v1.7.2 (annotated tag)

Final Validation:
- All 844+ tests passing ✓
- Coverage: 88% ✓
- THE CRITICAL TEST: PASSING ⭐
- Performance: P95 < 3s ✓

READY TO SHIP v1.7.2!

Summary:
- Story 0: 44 tests added
- Enhancement 3: NL completion tests/proposal
- Enhancement 4: 11+ files archived
- Enhancement 5: 6 fixtures extracted, 62 tests updated
- Total effort: 25 hours (as estimated)
```

---

## Success Criteria

Before considering work complete:

### Story 0
- [x] All 44 tests implemented
- [x] THE CRITICAL TEST passing (<2 min)
- [x] obra health command working
- [x] Structured logging integrated
- [x] Metrics collection functional
- [x] Performance baselines documented

### Enhancements
- [x] Enhancement 3: Tests added OR proposal created
- [x] Enhancement 4: 11+ files archived, summary created
- [x] Enhancement 5: 6 fixtures extracted, 50-70 tests updated

### Release
- [x] CHANGELOG.md updated
- [x] CLAUDE.md version: v1.7.2
- [x] Release notes created
- [x] Git tag: v1.7.2
- [x] All tests passing (100% pass rate)

---

## Emergency Contacts

**If THE CRITICAL TEST fails**:
- STOP immediately
- Debug the failure
- Check LLM connectivity: `obra health`
- Check agent availability: `claude --version`
- Review orchestrator logs
- Do NOT proceed to enhancements until fixed

**If tests fail after fixture consolidation**:
- Revert conftest.py changes
- Revert test updates
- Fix incrementally (one fixture at a time)
- Run tests after each fixture extraction

---

**Ready to Begin?**

Confirm you've read the comprehensive implementation plan and understand:
1. The 6-phase approach
2. THE CRITICAL TEST importance
3. Validation gates between phases
4. Success criteria

Then let's start with Phase 1: Story 0 Testing Infrastructure!
