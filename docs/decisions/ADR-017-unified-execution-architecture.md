# ADR-017: Unified Execution Architecture

**Status**: ✅ IMPLEMENTED
**Date Proposed**: 2025-11-12
**Date Implemented**: 2025-11-13
**Deciders**: Omar (Project Owner), Claude Code (Implementation)
**Supersedes**: Partial - Refines ADR-014 (Natural Language Interface)

## Context

### Current Architecture Problem (v1.6.0)

Obra currently has **two parallel execution paths** with fundamentally different quality guarantees:

**Path 1: Task Execution** (`/task execute 1`)
```
orchestrator.execute_task()
    ↓
8-Step Validation Pipeline:
  1. Context Building
  2. Prompt Generation
  3. Agent Execution
  4. Response Validation
  5. Quality Control
  6. Confidence Scoring
  7. Decision Making
  8. Action Handling (proceed/retry/escalate)
    ↓
Result with full quality guarantees
```

**Path 2: Natural Language Commands** (`create epic for auth`)
```
nl_processor.process()
    ↓
5-Stage Parsing (ADR-016):
  1. OperationClassifier
  2. EntityTypeClassifier
  3. EntityIdentifierExtractor
  4. ParameterExtractor
  5. CommandValidator
    ↓
CommandExecutor.execute()
    ↓
Direct StateManager CRUD (no validation)
    ↓
Result without quality validation
```

### Alignment Review Findings

An independent alignment review (2025-11-12) identified this architectural misalignment:

> "The NL pipeline itself is a rigid CRUD classifier: it forces every message through operation/entity/identifier/parameter stages and rejects anything outside that schema. When classification fails, users get errors instead of the orchestrator improvising or asking for clarification, so the workflow stalls at step one. Even when the pipeline succeeds, execution goes straight to CommandExecutor/StateManager without involving the orchestrator, meaning no prompt optimization, implementer invocation, or multi-turn guidance occurs."

### Core Problem

**The natural language interface bypasses Obra's core value proposition**: multi-stage validation with quality-based iterative improvement.

**Impact**:
- **Inconsistent User Experience**: Different quality depending on interface used
- **Architectural Debt**: Two execution models increases maintenance burden
- **Lost Capabilities**: NL commands can't use retry logic, breakpoints, or quality scoring
- **Trust Erosion**: Users learn to avoid NL for critical operations

### Evidence

| Feature | Task Execution | Natural Language |
|---------|---------------|------------------|
| Validation | ✅ Multi-stage | ❌ None |
| Quality Control | ✅ LLM-based scoring | ❌ None |
| Confidence | ✅ Heuristic + LLM | ❌ Pipeline confidence only |
| Iterative Improvement | ✅ Max 3 retries | ❌ Single-shot |
| Breakpoints | ✅ 6 strategic checkpoints | ❌ None |
| Decision Engine | ✅ Proceed/retry/clarify/escalate | ❌ Execute or error |

## Decision

We will **unify both execution paths** by routing ALL commands (NL and CLI) through `orchestrator.execute_task()`.

### New Unified Architecture (v1.7.0)

```
User Input (any interface: CLI, NL, interactive)
    ↓
┌─────────────────────────────────────────────┐
│ Is Natural Language?                        │
├─────────────────────────────────────────────┤
│ YES → NL Parsing Pipeline (intent → task)   │
│       • IntentToTaskConverter (NEW)         │
│       • Task object with NL context         │
│ NO  → Task from CLI/API                     │
└─────────────────────────────────────────────┘
    ↓
orchestrator.execute_task() ← UNIFIED ENTRY POINT
    ↓
┌─────────────────────────────────────────────┐
│ UNIFIED EXECUTION PIPELINE (8 steps)        │
├─────────────────────────────────────────────┤
│ 1. Context Building                         │
│ 2. Prompt Generation                        │
│ 3. Agent Execution                          │
│ 4. Response Validation                      │
│ 5. Quality Control                          │
│ 6. Confidence Scoring                       │
│ 7. Decision Making                          │
│ 8. Action Handling                          │
└─────────────────────────────────────────────┘
    ↓
Result with full quality guarantees (ALL interfaces)
```

### Key Architectural Changes

1. **NL Pipeline Role Change**:
   - **Before**: Intent Parser + Executor (does everything)
   - **After**: Intent Parser ONLY (generates Task objects)

2. **CommandExecutor Refactor**:
   - **Rename**: `CommandExecutor` → `NLQueryHelper`
   - **Remove**: All write operations (create/update/delete)
   - **Keep**: Read-only query operations (as helper for orchestrator)

3. **New Component**: `IntentToTaskConverter`
   - Converts `OperationContext` → `Task` object
   - Enriches task with NL metadata (original message, confidence, parsed entities)
   - Routes different operations appropriately

4. **Safety Integration**:
   - Destructive NL operations (UPDATE/DELETE) trigger BreakpointManager
   - Human-in-the-loop confirmation before execution
   - Consistent with existing orchestrator checkpoint system

## Consequences

### Positive

1. **Consistent Quality Across All Interfaces**
   - All commands validated through multi-stage pipeline
   - Same quality guarantees whether using CLI or NL
   - Users can trust NL for critical operations

2. **Simplified Architecture**
   - Single execution model (orchestrator)
   - Eliminates parallel paths and synchronization issues
   - ~40% reduction in integration test surface area

3. **Enhanced Capabilities for NL Commands**
   - Retry logic with exponential backoff
   - Iterative improvement for low-quality responses
   - Breakpoints and human-in-the-loop checkpoints
   - Quality scoring and confidence tracking

4. **Preserved Investment**
   - ADR-016 components (5-stage pipeline) remain valuable
   - High accuracy (95%+) parsing still leveraged
   - Only architectural layer changes, not parsing logic

5. **Future-Proof Foundation**
   - Multi-action NL commands can use orchestrator infrastructure
   - Voice input can leverage unified execution
   - Complex workflows (dependencies, epics) work with NL

### Negative

1. **Latency Increase**
   - ~500ms additional latency for NL commands
   - Full orchestration has more steps than direct CRUD
   - **Mitigation**: Acceptable trade-off (quality > speed), optimize hot paths

2. **Breaking Changes (Internal APIs)**
   - `NLCommandProcessor.process()` returns `ParsedIntent`, not `NLResponse`
   - `CommandExecutor` renamed to `NLQueryHelper` (write operations removed)
   - **Mitigation**: Deprecation warnings v1.7.0, remove v1.8.0, migration guide

3. **Increased Complexity for Simple Operations**
   - Simple queries now go through full pipeline
   - **Mitigation**: Fast path for read-only queries (NLQueryHelper)

4. **User Perception**
   - Users may expect fast NL commands
   - **Mitigation**: Clear communication of benefits, progress indicators

### Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Latency complaints | HIGH | Medium | Set expectations, optimize, provide fast path |
| API breaking changes | LOW | Low | Few external users, deprecation warnings |
| Test coverage gaps | MEDIUM | High | Dedicated testing story (16 hours), real LLM tests |
| User confusion | LOW | Low | Clear CHANGELOG, emphasize quality benefits |

## Alternatives Considered

### Alternative 1: Synchronize Validation Logic Across Both Paths

**Approach**: Keep parallel paths, but ensure both apply same validation

**Pros**:
- No breaking changes
- Maintains fast NL commands

**Cons**:
- Duplicate code (validation in 2 places)
- Ongoing synchronization burden
- Still 2x test surface area
- Doesn't solve architectural inconsistency

**Rejected**: Doesn't address root cause (parallel execution models)

### Alternative 2: Make Orchestrator Optional for Simple Operations

**Approach**: Fast path for simple CRUD, orchestrator for complex operations

**Pros**:
- Best of both worlds (speed + quality)
- Minimal latency for simple commands

**Cons**:
- Complex routing logic (when to use which path?)
- Still maintains 2 execution models
- Edge cases: what is "simple"?
- User confusion (inconsistent quality)

**Rejected**: Adds complexity without solving architectural drift

### Alternative 3: Hybrid - NL for Simple, Orchestrator for Complex

**Approach**: Simple NL commands bypass orchestrator, complex ones use it

**Pros**:
- Performance for common cases
- Quality for critical operations

**Cons**:
- Requires complexity classifier
- Subjective boundary (simple vs complex)
- Still maintains dual architecture
- User uncertainty about which path taken

**Rejected**: Complexity classifier adds overhead, maintains dual paths

### Selected: Unified Execution Through Orchestrator

**Why**: Simplest architecture, consistent quality, leverages existing infrastructure

## Implementation

**Epic**: ADR-017 Unified Execution Architecture
**Duration**: 2-3 weeks (60-80 hours)
**Releases**: v1.7.0 (core refactor), v1.7.1 (safety enhancements)

### Stories

1. **Story 1**: Architecture Documentation (8 hours) - **THIS DOCUMENT**
2. **Story 2**: Create IntentToTaskConverter (12 hours)
3. **Story 3**: Refactor CommandExecutor → NLQueryHelper (10 hours)
4. **Story 4**: Update NLCommandProcessor Routing (10 hours)
5. **Story 5**: Implement Unified Orchestrator Routing (12 hours)
6. **Story 6**: Integration Testing (16 hours)
7. **Story 7**: Documentation Updates (8 hours)
8. **Story 8**: Destructive Operation Breakpoints (10 hours) - v1.7.1
9. **Story 9**: Confirmation Workflow UI Polish (6 hours) - v1.7.1

**See**:
- `docs/development/ADR017_UNIFIED_EXECUTION_EPIC_BREAKDOWN.md` (human-readable plan)
- `docs/development/ADR017_UNIFIED_EXECUTION_IMPLEMENTATION_PLAN.yaml` (machine-optimized plan)

### Breaking Changes

**Internal APIs Only** (v1.7.0):
- `NLCommandProcessor.process()` signature changed
- `CommandExecutor` renamed to `NLQueryHelper`
- Write operations removed from executor

**User-Facing**: None (commands work identically)

**Migration Path**:
- Deprecation warnings in v1.7.0
- Legacy methods removed in v1.8.0 (6 months notice)
- See: `docs/guides/ADR017_MIGRATION_GUIDE.md`

### Rollback Plan

**Emergency Rollback** (if critical issues):
- Option 1: Emergency patch within 24 hours → v1.7.0.1
- Option 2: Git revert to v1.6.0

**Legacy Mode** (escape hatch):
```yaml
nl_commands:
  use_legacy_executor: false  # Set to true to bypass orchestrator (emergency only)
```

Remove legacy mode in v1.8.0 after 3 months of v1.7.0 stability.

## Validation

### Success Metrics

**Technical**:
- ✅ 100% of NL commands route through orchestrator
- ✅ 0 direct StateManager writes from NL pipeline (except read-only)
- ✅ ≥90% test coverage on new components
- ✅ All 770+ existing tests passing (no regressions)
- ✅ <3s latency (P95) for NL commands

**Quality**:
- ✅ Validation applied to 100% of NL commands
- ✅ Confidence scoring tracked for all operations
- ✅ Iterative improvement available
- ✅ Safety breakpoints triggered for destructive ops

**Architectural**:
- ✅ 1 execution path (down from 2)
- ✅ ~40% reduction in integration test surface
- ✅ Simplified codebase (NL pipeline 300 lines smaller)

### Testing Strategy

- **Unit Tests**: 120+ new tests (≥90% coverage)
- **Integration Tests**: 40+ E2E tests (≥85% coverage)
- **Regression**: All 770+ existing tests must pass
- **Performance**: <3s latency (P95), ≥40 cmd/min throughput

## References

- **Alignment Review**: `docs/code_review/20251112 Alignment Review.md`
- **Epic Breakdown**: `docs/development/ADR017_UNIFIED_EXECUTION_EPIC_BREAKDOWN.md`
- **Implementation Plan**: `docs/development/ADR017_UNIFIED_EXECUTION_IMPLEMENTATION_PLAN.yaml`
- **Related ADRs**:
  - ADR-014: Natural Language Command Interface (5-stage pipeline)
  - ADR-016: Decompose NL Entity Extraction (parsing improvements)

## Notes

**Assumptions**:
- Single-user deployment (Omar) - internal API breaks acceptable
- Database schema stable (no migrations needed)
- LLM available (Ollama/Qwen or OpenAI Codex)

**Future Enhancements** (not in v1.7):
- Async NL command execution for long operations
- Multi-action NL commands ("create epic AND add 3 stories")
- Voice input integration (speech-to-text → NL pipeline)
- NL command history and replay
- Undo/redo for NL commands

---

**Status**: This ADR is IMPLEMENTED.

**Implementation Summary**:
- Story 0: Testing Infrastructure ✅
- Story 1: Architecture Documentation ✅
- Story 2: IntentToTaskConverter ✅ (32 tests, 93% coverage)
- Story 3: NLQueryHelper ✅ (17 tests, 97% coverage)
- Story 4: NLCommandProcessor Routing ✅ (18 tests)
- Story 5: Orchestrator Integration ✅ (12 integration tests)
- Story 6: Integration Testing ✅ (24 tests total, 100% passing)
- Story 7: Documentation Updates ✅

**Test Results**:
- NL Integration Tests: 12/12 ✅
- E2E Test: Passing (task execution validated) ✅
- Regression Tests: 8/8 ✅
- Performance Tests: 4/4 ✅
- Total Tests: 794+ (770 existing + 24 new)

**Last Updated**: 2025-11-13
**Completed**: November 13, 2025 (v1.7.0)
