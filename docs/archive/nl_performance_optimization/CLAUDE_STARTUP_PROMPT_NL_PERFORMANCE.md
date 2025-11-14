# STARTUP PROMPT: NL Performance Optimization

**COPY-PASTE THIS INTO CLAUDE CODE:**

---

I need you to implement NL command performance optimizations for the Obra orchestrator. The Natural Language pipeline is currently **6.3x slower** than target (6.3s vs <1s).

## Context

**Problem**: "list all projects" takes 6.3 seconds (should be <1 second)
**Root Cause**: Sequential LLM calls (~2s each), no caching, no fast path
**Goal**: Reduce to <500ms average (12.6x improvement)

## Implementation Guide

**Primary Reference**: `docs/implementation/NL_PERFORMANCE_OPTIMIZATION_IMPLEMENTATION.md`
- This is a machine-optimized guide with exact file paths, line numbers, and code
- Follow it sequentially: Phase 1 (Tasks 1.1-1.4), then Phase 2 (Tasks 2.1-2.3)

**User Guide**: `docs/guides/NL_PERFORMANCE_OPTIMIZATION_GUIDE.md`
- Background, strategy explanations, success criteria

## What to Implement

### Phase 1 (2 hours, 60x improvement for 50% traffic)

**Task 1.1**: Add metrics recording to NL pipeline
- Files: `src/nl/intent_classifier.py`, `operation_classifier.py`, `entity_type_classifier.py`, `entity_identifier_extractor.py`, `parameter_extractor.py`, `nl_command_processor.py`
- Add `get_metrics_collector()` and record latency in each `classify()`/`extract()` method

**Task 1.2**: Implement fast path matcher
- Create: `src/nl/fast_path_matcher.py` (rule-based pattern matching)
- Modify: `src/nl/nl_command_processor.py` (integrate fast path)
- Benefit: 126x faster for common queries (6.3s → 50ms)

**Task 1.3**: Enable LLM keep-alive
- Modify: `src/llm/local_interface.py` (add `keep_alive: -1` to API calls)
- Benefit: Eliminate model cold start (1.4x faster)

**Task 1.4**: Add metrics CLI commands
- Modify: `src/cli.py` (add `obra metrics nl/llm/health` commands)

### Phase 2 (4 hours, additional 12x improvement)

**Task 2.1**: Implement query caching
- Create: `src/nl/query_cache.py` (LRU cache with TTL)
- Modify: `src/nl/nl_command_processor.py` (check cache before LLM)
- Benefit: 630x faster for repeated queries (6.3s → 10ms)

**Task 2.2**: Optimize LLM prompts
- Modify: All 5 classifiers (reduce from 250 tokens → 45 tokens)
- Benefit: 1.5x faster

**Task 2.3**: Tune LLM generation parameters
- Modify: All 5 classifiers (add `max_tokens=50`, `temperature=0.1`, etc.)
- Benefit: 2x faster

## Testing Requirements

**Unit Tests** (required for each task):
- `tests/nl/test_fast_path_matcher.py` (20 tests)
- `tests/nl/test_query_cache.py` (15 tests)
- Run: `pytest tests/nl/` after each task

**Integration Tests**:
- `tests/integration/test_nl_performance.py` (latency assertions)

## Success Criteria

**Phase 1 Complete**:
- ✅ "list all projects" completes in <100ms (was: 6.3s)
- ✅ Fast path hit rate >50%
- ✅ All unit tests passing

**Phase 2 Complete**:
- ✅ Average latency <500ms (was: 6.3s)
- ✅ P95 latency <1,500ms
- ✅ Cache hit rate >30%

## Verification

After Phase 1:
```bash
python -m src.cli interactive
> list all projects
# Should show: "Fast path matched: list all projects → project"
# Latency should be ~50ms
> exit

python -m src.cli metrics nl
# Should show fast path hit rate >50%
```

After Phase 2:
```bash
python -m src.cli interactive
> list all projects
# First time: ~50ms (fast path)
> list all projects
# Second time: ~10ms (cache hit)
```

## Important Notes

1. **Read the implementation guide first** (`docs/implementation/NL_PERFORMANCE_OPTIMIZATION_IMPLEMENTATION.md`)
2. **Complete Phase 1 before Phase 2** (dependencies)
3. **Run tests after each task** (catch regressions early)
4. **Follow exact file paths and line numbers** in implementation guide
5. **Existing metrics system already exists** (`src/core/metrics.py`) - just integrate it

## Current Performance Baseline

```
Intent Classification:         1ms ✅
Operation Classification:   2,050ms ❌ (13.7x slower than target)
Entity Type Classification: 2,128ms ❌ (14.2x slower)
Entity Identifier Extract:  1,798ms ❌ (12.0x slower)
Parameter Extraction:         299ms ⚠️ (2x slower)
TOTAL:                      6,276ms ❌ (6.3x slower than <1s target)
```

## Questions to Ask User

If stuck:
- "Should I prioritize fast path (immediate 60x for common queries) or caching (gradual improvement)?"
- "What's the acceptable cache TTL? (default: 60 seconds)"
- "Should I implement all 20 fast path patterns or start with top 10?"

## Expected Timeline

- Phase 1: 2 hours
- Phase 2: 4 hours
- Total: 6 hours

---

**START WITH**: Read `docs/implementation/NL_PERFORMANCE_OPTIMIZATION_IMPLEMENTATION.md` from start to finish, then begin Task 1.1.
