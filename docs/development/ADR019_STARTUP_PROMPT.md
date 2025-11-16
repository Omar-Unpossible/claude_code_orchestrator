# Claude Code Startup Prompt: ADR-019 Implementation

**Task**: Implement Orchestrator Session Continuity Enhancements
**Prerequisites**: ✅ ADR-018 complete (merged to main)
**Timeline**: 4 weeks | **Scope**: 5 components, ~1,500 LOC

## Objective

Implement session continuity for Obra Orchestrator:
1. Orchestrator self-handoff (restart LLM at >85% context)
2. Automated decision records (ADR format, privacy-compliant)
3. Structured progress reporting (JSON monitoring)
4. Checkpoint verification (pre/post integrity checks)
5. Session metrics tracking

## Critical Documents

**Load in order**:
1. `docs/decisions/ADR-019-orchestrator-session-continuity.md` - Architecture decision
2. `docs/analysis/ADR018_GAP_ANALYSIS.md` - Gap analysis & patterns
3. `CLAUDE.md` - Project guidelines
4. `docs/testing/TEST_GUIDELINES.md` - WSL2 crash prevention

## Implementation Plan

### Phase 1: Core Session Management (Weeks 1-2)

**Create**:
- `src/orchestration/session/orchestrator_session_manager.py`
- `src/orchestration/session/checkpoint_verifier.py`
- Tests with ≥90% coverage

**Integration**:
- `Orchestrator.execute_task()` - add self-handoff trigger
- `Orchestrator.execute_nl_command()` - add self-handoff trigger
- `CheckpointManager` - add verification calls

**Verification Gate P1**:
- [ ] Self-handoff works (Orchestrator restarts with checkpoint)
- [ ] Checkpoint verification blocks on failures
- [ ] Tests pass (≥90% coverage)

### Phase 2: Decision Records & Progress (Week 3)

**Create**:
- `src/orchestration/session/decision_record_generator.py`
- `src/orchestration/session/progress_reporter.py`
- Tests with ≥90% coverage

**Integration**:
- `DecisionEngine.decide_next_action()` - add DR generation
- `ProductionLogger` - consume progress reports

**Verification Gate P2**:
- [ ] DRs auto-generated (ADR format, NO raw reasoning)
- [ ] Progress reports logged (JSON Lines)
- [ ] Tests pass (≥90% coverage)

### Phase 3: Metrics & Testing (Week 4)

**Create**:
- `src/orchestration/session/session_metrics_collector.py`
- Integration tests (multi-session workflows)
- Documentation (user guide, API docs)

**Verification Gate P3 (FINAL)**:
- [ ] Multi-session workflows work (50+ NL commands)
- [ ] Metrics tracked (handoff frequency, context usage)
- [ ] Documentation complete
- [ ] Performance: <5s handoff, <500ms verification

## Start Here

```bash
# Create feature branch
git checkout -b obra/adr-019-session-continuity

# Create structure
mkdir -p src/orchestration/session tests/orchestration/session

# Begin implementation
# Phase 1, Task 1: Design OrchestratorSessionManager class
```

## Context Management (CRITICAL!)

**Monitor YOUR context window**:
- Check after each task (~5-10K tokens)
- **At 80%**: Generate continuation prompt
- **Template**: `docs/development/.continuation_prompts/TEMPLATE_continuation.md`
- **Save to**: `docs/development/.continuation_prompts/adr019_session_N_continue.md`

**Estimated**: 8-12 sessions to complete

## Code Standards

```python
# Type hints + Google docstrings required
def restart_orchestrator_with_checkpoint(
    self, checkpoint_id: Optional[str] = None
) -> str:
    """Restart Orchestrator LLM with checkpoint.
    
    Args:
        checkpoint_id: Checkpoint to load (None = create new)
        
    Returns:
        Checkpoint ID used
        
    Raises:
        OrchestratorException: If restart fails
    """
```

## Privacy (CRITICAL!)

**Decision Records**:
- ✅ ADR format: Context, Decision, Consequences, Alternatives
- ❌ NEVER: Raw LLM reasoning, chain-of-thought, scratchpad

**Sanitize**:
- Remove "I think", "Let me consider" (reasoning indicators)
- Redact API keys, secrets

## Configuration

```yaml
orchestrator:
  session_continuity:
    self_handoff:
      enabled: true
      trigger_zone: 'red'  # 85%
    decision_logging:
      enabled: true
      significance_threshold: 0.7
    progress_reporting:
      enabled: true
```

## Success Criteria

- ✅ Orchestrator self-handoff at >85% context
- ✅ Decision records auto-generated (privacy-compliant)
- ✅ Progress reports in JSON format
- ✅ Checkpoint verification working
- ✅ Multi-session workflows (50+ commands)
- ✅ Tests ≥90% coverage
- ✅ Performance targets met

---

**Begin**: `git checkout -b obra/adr-019-session-continuity && mkdir -p src/orchestration/session`
**Estimated**: 4 weeks (8-12 continuation sessions)
