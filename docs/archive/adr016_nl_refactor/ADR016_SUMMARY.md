# ADR-016 Implementation Summary

**Version**: 1.0
**Created**: 2025-11-11
**Status**: Proposed (Planning Phase)

## Quick Overview

**What**: Decompose the monolithic `EntityExtractor` into a five-stage pipeline with single-responsibility components.

**Why**: Current NL interface accuracy is 80-85% due to EntityExtractor trying to do too much in one LLM call. Three critical issues (ISSUE-001, ISSUE-002, ISSUE-003) block production deployment.

**Goal**: Achieve 95%+ accuracy by decomposing extraction into focused components.

**Effort**: 8-10 days

**Target**: v1.6.0

---

## The Problem

### Current Architecture (ADR-014)
```
IntentClassifier → EntityExtractor → CommandValidator → CommandExecutor
                   (monolithic - does 4+ things)
```

**EntityExtractor Tries to Do Too Much**:
1. Classify entity type (project/task/epic/story)
2. Extract entity identifier (name or ID)
3. Infer operation type (create/update/delete/query) - IMPLICIT
4. Extract parameters (status, priority, etc.) - IMPLICIT

**Result**: Low accuracy (80-85%), critical bugs

### Critical Issues Identified

**ISSUE-001 (HIGH)**: Entity type misclassification
- Command: "Mark the manual tetris test as INACTIVE"
- Expected: Update project status
- Actual: Created new task (wrong!)

**ISSUE-002 (MEDIUM)**: Vocabulary gap
- Command: "List the workplans for the projects"
- Expected: Show task hierarchies
- Actual: Showed simple project list (not useful)

**ISSUE-003 (MEDIUM)**: Questions rejected
- Command: "What's next for the tetris game development"
- Expected: Informational response
- Actual: "Invalid command syntax" (bad UX)

---

## The Solution

### New Architecture (ADR-016)
```
IntentClassifier
    ↓
    ├─── COMMAND Path ────────────────────┐
    │    OperationClassifier              │ ← NEW: Classify CREATE/UPDATE/DELETE/QUERY
    │    EntityTypeClassifier             │ ← NEW: Classify project/task/epic/story
    │    EntityIdentifierExtractor        │ ← NEW: Extract name or ID
    │    ParameterExtractor               │ ← NEW: Extract status, priority, etc.
    │    CommandValidator                 │ ← UPDATED: Validate OperationContext
    │    CommandExecutor                  │ ← UPDATED: Add hierarchical queries
    └─────────────────────────────────────┘
    │
    └─── QUESTION Path ───────────────────┐
         QuestionHandler                  │ ← NEW: Answer questions gracefully
    ──────────────────────────────────────┘
```

### Key Principles

1. **Single Responsibility**: Each component has one clear job
2. **Explicit Context**: Operation type flows explicitly through pipeline
3. **Progressive Refinement**: Each stage narrows down classification
4. **Fail-Fast Validation**: Validate at each stage
5. **Extensibility**: Easy to add new operations, entity types, query patterns

### Expected Results

| Command Type | Before | After | Improvement |
|--------------|--------|-------|-------------|
| Simple (create, list) | 90-95% | 98% | +3-8% |
| Status updates | 80% | 95% | +15% |
| Hierarchical queries | 70% | 90% | +20% |
| Natural questions | 60% | 92% | +32% |
| **Overall** | **80-85%** | **95%+** | **+10-15%** |

---

## Implementation Plan

### 7 Stories, 10 Days

**Story 1**: Foundation and Design (1 day)
- Approve ADR-016
- Create data structures (OperationType, OperationContext, etc.)
- Design component interfaces

**Story 2**: Single-Purpose Classifiers (2 days)
- Implement OperationClassifier (20 tests)
- Implement EntityTypeClassifier (25 tests)

**Story 3**: Entity and Parameter Extraction (2 days)
- Implement EntityIdentifierExtractor (20 tests)
- Implement ParameterExtractor (25 tests)

**Story 4**: Question Handling (1 day)
- Implement QuestionHandler (30 tests)
- Support 5 question types (NEXT_STEPS, STATUS, BLOCKERS, PROGRESS, GENERAL)

**Story 5**: Update Core Components (2 days)
- Update CommandValidator (15 tests)
- Update CommandExecutor (20 tests)
- Update NLCommandProcessor (10 tests)

**Story 6**: Comprehensive Testing (2 days)
- Run 165 unit tests
- Run 130 integration tests (30 new + 103 existing)
- Manual testing (30+ diverse commands)
- Performance testing (latency, throughput, memory)

**Story 7**: Documentation and Migration (1 day)
- Update NL_COMMAND_GUIDE.md
- Update ARCHITECTURE.md
- Create ADR016_MIGRATION_GUIDE.md
- Update CHANGELOG.md

### Test Coverage

- **165 unit tests** for new components
- **130 integration tests** (30 new + 103 existing)
- **30+ manual test scenarios**
- **Performance benchmarks**

**Total**: 295+ tests

---

## Success Metrics

### Accuracy
- ✅ 95%+ overall accuracy (up from 80-85%)
- ✅ 98% on simple commands (up from 90-95%)
- ✅ 95% on status updates (up from 80%)
- ✅ 90% on hierarchical queries (up from 70%)
- ✅ 92% on natural questions (up from 60%)

### Issues Resolved
- ✅ ISSUE-001 (HIGH): Status updates work correctly
- ✅ ISSUE-002 (MEDIUM): Hierarchical queries supported
- ✅ ISSUE-003 (MEDIUM): Questions answered gracefully

### Performance
- ✅ End-to-end latency <1.5 seconds (P95)
- ✅ Throughput ≥50 commands/minute
- ✅ Memory overhead <200MB

### Quality
- ✅ 295+ tests passing (100% pass rate)
- ✅ No regressions (all 103 existing tests pass)
- ✅ Test coverage ≥90% for all new components

---

## Documents

### Planning Documents (Created)
1. **[ADR-016](../decisions/ADR-016-decompose-nl-entity-extraction.md)** - Architecture decision record
2. **[Implementation Plan (Human)](ADR016_IMPLEMENTATION_PLAN.md)** - Detailed implementation plan
3. **[Implementation Plan (Machine)](ADR016_IMPLEMENTATION_PLAN.yaml)** - YAML for LLM consumption
4. **[Epic Breakdown](ADR016_EPIC_BREAKDOWN.md)** - Story hierarchy and task breakdown
5. **[Summary](ADR016_SUMMARY.md)** - This document

### Documents to Create During Implementation
1. **ADR016_MIGRATION_GUIDE.md** - Migration guide for users (Story 7)
2. **Updated NL_COMMAND_GUIDE.md** - User guide with new patterns (Story 7)
3. **Updated ARCHITECTURE.md** - Architecture docs with new design (Story 7)

---

## Risks and Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Breaking changes | High | Medium | Legacy pipeline fallback via config |
| Performance degradation | Low | Medium | Benchmark before/after; optimize if needed |
| Test failures | Medium | High | Comprehensive test coverage before merge |
| User confusion | Medium | Low | Clear migration guide with examples |

### Rollback Plan
If issues arise post-deployment:
1. Set config: `nl_commands.use_legacy_pipeline: true`
2. Restart Obra
3. Investigate and fix issues
4. Re-deploy when ready

Legacy pipeline will be removed in v1.7.0.

---

## Timeline

```
Week 1:
  Day 1: Story 1 (Foundation)
  Day 2-3: Story 2 (Classifiers) + Story 3 (Extraction) - parallel
  Day 4: Story 4 (Question Handling)
  Day 5: Buffer / catch-up

Week 2:
  Day 6-7: Story 5 (Core Updates)
  Day 8-9: Story 6 (Testing)
  Day 10: Story 7 (Documentation)
```

**Total**: 2 weeks (10 working days)

---

## Dependencies

**Prerequisites**:
- ✅ ADR-016 approval
- ✅ StateManager API stable
- ✅ Ollama/Qwen available (local LLM)

**Blockers**: None identified

**Follow-up Work** (v1.7.0+):
- Performance optimization (caching)
- Multi-turn context (follow-up questions)
- Advanced query patterns (filters, sorting)
- Multi-language support (Spanish, French)

---

## Next Steps

1. **Review ADR-016** - Read and approve architecture decision
2. **Review Implementation Plan** - Understand detailed tasks
3. **Review Epic Breakdown** - Understand story hierarchy
4. **Approve Plan** - Give go-ahead to start implementation
5. **Begin Story 1** - Create data structures and interfaces

---

## Questions to Resolve

1. **Should we deprecate EntityExtractor immediately or keep for migration period?**
   - Recommendation: Keep for v1.6.0 with config flag, remove in v1.7.0

2. **Should we implement performance optimizations now or defer to v1.7.0?**
   - Recommendation: Defer to v1.7.0; focus on accuracy first

3. **Should we add multi-turn context (follow-up questions) in v1.6.0?**
   - Recommendation: Defer to v1.7.0; focus on single-turn accuracy first

---

## Approval

- [ ] **Omar**: Approve plan and architecture
- [ ] **Technical Review**: Validate design before implementation
- [ ] **Schedule**: Confirm 10-day timeline is acceptable

**Once approved, proceed to Story 1 (Foundation and Design).**

---

**Version**: 1.0
**Last Updated**: 2025-11-11
**Status**: Awaiting Approval

