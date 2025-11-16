# ADR-019: Orchestrator Session Continuity Enhancements

**Status**: Proposed | **Date**: 2025-11-15 | **Depends On**: ADR-018

## Context

ADR-018 implements context management infrastructure but lacks orchestration logic for multi-session continuity:
- ❌ No Orchestrator self-handoff (LLM restart with checkpoint)
- ❌ No automated decision records (privacy-compliant ADR format)
- ❌ No structured progress reporting (JSON for monitoring)
- ❌ No checkpoint verification (pre-create, post-resume)

## Decision

Implement **5 new components** for session continuity:

1. **OrchestratorSessionManager** - LLM lifecycle, self-handoff at >85% context
2. **CheckpointVerifier** - Pre/post checkpoint validation  
3. **DecisionRecordGenerator** - Auto-generate ADR-format DRs (no raw reasoning)
4. **ProgressReporter** - Structured JSON progress reports
5. **SessionMetricsCollector** - Track handoff frequency, context patterns

### Architecture

```
Self-Handoff Flow:
Context >85% → Verify Ready (git clean, tests pass) → 
Create Checkpoint → Disconnect LLM → Reconnect Fresh LLM → 
Load Checkpoint Context → Resume Operation
```

### Configuration

```yaml
orchestrator:
  session_continuity:
    self_handoff:
      enabled: true
      trigger_zone: 'red'  # 85%
      max_handoffs_per_session: 10
    decision_logging:
      enabled: true
      significance_threshold: 0.7
    progress_reporting:
      enabled: true
      destination: production_log
  checkpoint:
    verification:
      verify_git_clean: true
      verify_tests_passing: true
      min_coverage: 0.90
```

## Consequences

**Positive**:
- Multi-session continuity (50+ NL commands seamless)
- Decision transparency (auto-generated ADRs)
- Monitoring enablement (structured JSON reports)
- State integrity (checkpoint verification)
- Privacy compliance (no raw reasoning logged)

**Negative**:
- Complexity: +1,500 LOC, 5 components
- Overhead: ~5s handoff latency, ~500ms verification
- Storage: DRs (~5KB each), progress reports (~2KB each)

**Mitigations**:
- Comprehensive tests (≥90% coverage)
- Feature flags for gradual rollout
- Performance benchmarks to validate targets

## Implementation

**Timeline**: 4 weeks (3 phases)

**Phase 1** (Weeks 1-2): Session Manager + Checkpoint Verifier
**Phase 2** (Week 3): Decision Records + Progress Reporting  
**Phase 3** (Week 4): Session Metrics + Integration Tests + Docs

**Verification Gates**: P1 → P2 → P3 (all criteria must pass)

See: `docs/development/ADR019_IMPLEMENTATION_PLAN_MACHINE.json`

## Success Criteria

- ✅ Orchestrator hands off to fresh LLM when context >85%
- ✅ Decision records auto-generated (ADR format, privacy-compliant)
- ✅ Progress reports logged (JSON schema valid)
- ✅ Checkpoints verified (pre-create and post-resume)
- ✅ Multi-session workflows work (50+ NL commands)
- ✅ Performance: <5s handoff, <500ms verification
- ✅ Test coverage ≥90%

---

**Decision ID**: ADR-019
**Next Steps**: Review, approve, implement after ADR-018 completes
