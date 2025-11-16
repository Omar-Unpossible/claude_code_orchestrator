# Phase 3 - Automated Variation Testing Guide

**Status**: ✅ Complete (Infrastructure ready for execution)

## Overview

Phase 3 adds **automated variation stress testing** with 1000+ test cases to validate NL parsing robustness.

**Goal**: Ensure NL command parser handles diverse phrasings, synonyms, typos, and verbosity with ≥90% pass rate.

## Components Created

### 1. NL Variation Generator (`tests/fixtures/nl_variation_generator.py`)

Generates semantic variations using real LLM (OpenAI Codex or configured provider).

**Features**:
- 5 variation categories (synonyms, phrasings, case, typos, verbose)
- Configurable distribution (default: 100 variations per command)
- LLM-based semantic validation
- Category-specific generation strategies

**Example**:
```python
from tests.fixtures.nl_variation_generator import NLVariationGenerator

generator = NLVariationGenerator(llm_plugin)
variations = generator.generate_variations("create epic for auth", count=100)
# Returns: ["add epic for auth", "CREATE EPIC FOR AUTH", "crete epic for auth", ...]
```

### 2. Variation Test Suite (`tests/integration/test_nl_variations.py`)

**1000+ test cases** across 10 test methods:

| Test Class | Test Methods | Variations | Total |
|------------|--------------|------------|-------|
| `TestNLCreateVariations` | 3 (epic, story, task) | 100 each | 300 |
| `TestNLUpdateVariations` | 2 (status, title) | 100 each | 200 |
| `TestNLQueryVariations` | 2 (list, count) | 100 each | 200 |
| `TestNLDeleteVariations` | 1 (delete task) | 100 | 100 |
| `TestNLCategoryValidation` | 3 (synonyms, typos, verbose) | 50 each | 150 |
| **TOTAL** | **11 tests** | | **950** |

**Pass Rate Thresholds**:
- Main tests: ≥90% pass rate
- Synonym/Verbose: ≥90% pass rate (should handle well)
- Typos: ≥70% pass rate (harder to handle)

### 3. Performance Benchmarks (`tests/performance/test_nl_performance.py`)

**5 benchmark tests**:

| Benchmark | Metric | Target |
|-----------|--------|--------|
| Latency Distribution | P95 / P99 | < 3s / < 5s |
| Throughput | Commands/minute | > 40 cmd/min |
| Cache Hit Rate | Speedup ratio | Informational |
| Concurrent Parsing | 5 threads | 0 failures |
| Token Usage | Avg tokens/cmd | Informational |

### 4. Failure Analysis Tool (`tests/fixtures/generate_failure_report.py`)

Generates comprehensive failure reports with:
- Categorized failures by root cause
- Actionable recommendations
- Example failures per category
- Prioritized improvement suggestions

**Example report**:
```markdown
# NL Variation Failure Report

## Summary
- Total failures: 50
- Unique categories: 3

## Failure Categories

### Low Confidence (30 failures, 60%)
**Recommendation**: Improve confidence scoring or lower threshold

**Examples**:
1. Variation: "crete epic for auth" - confidence: 0.45
2. Variation: "epik for authentication" - confidence: 0.52
```

## Running Tests

### Prerequisites

1. **LLM Provider**: OpenAI Codex (or configured LLM provider)
   - Auth-based subscription (no API key needed)
   - Auto-selects model based on account

2. **Environment**: Ensure LLM is authenticated and accessible

### Quick Commands

```bash
# Run ALL Phase 3 tests (stress + benchmarks)
pytest tests/integration/test_nl_variations.py tests/performance/test_nl_performance.py -v -m "real_llm"

# Run ONLY stress tests (1000+ variations)
pytest tests/integration/test_nl_variations.py -v -m "real_llm and stress_test"

# Run ONLY performance benchmarks
pytest tests/performance/test_nl_performance.py -v -m "benchmark"

# Run specific test (e.g., CREATE variations)
pytest tests/integration/test_nl_variations.py::TestNLCreateVariations -v -m "real_llm"

# Run with detailed logging
pytest tests/integration/test_nl_variations.py -v -m "real_llm" --log-cli-level=INFO
```

### Generate Failure Report

After running tests:

```bash
# Generate failure analysis report
python tests/fixtures/generate_failure_report.py \
    --test-log tests/test_run.log \
    --output tests/reports/nl_variation_failures.md \
    --json

# View report
cat tests/reports/nl_variation_failures.md
```

## Test Execution Time Estimates

| Test Suite | Tests | Est. Time |
|------------|-------|-----------|
| CREATE variations (3 tests) | 300 variations | 15-20 min |
| UPDATE variations (2 tests) | 200 variations | 10-15 min |
| QUERY variations (2 tests) | 200 variations | 10-15 min |
| DELETE variations (1 test) | 100 variations | 5-10 min |
| Category validation (3 tests) | 150 variations | 8-12 min |
| **Total Stress Tests** | **950 variations** | **50-70 min** |
| Performance benchmarks | 5 tests | 10-15 min |
| **TOTAL PHASE 3** | **16 tests** | **60-85 min** |

**Note**: Times assume P95 latency ~2-3s per LLM call. Actual time depends on LLM provider speed.

## Success Criteria

### ✅ Phase 3 Complete When:

1. **Stress Tests**: ≥90% pass rate across all variation tests
2. **Performance**: P95 < 3s, P99 < 5s, throughput > 40 cmd/min
3. **Failure Analysis**: Auto-generated report with actionable recommendations
4. **Infrastructure**: All 4 components created and documented

### Current Status

| Component | Status | Notes |
|-----------|--------|-------|
| Variation Generator | ✅ Complete | 5 categories, LLM-based |
| Variation Tests | ✅ Complete | 11 tests, 950+ variations |
| Performance Benchmarks | ✅ Complete | 5 benchmarks |
| Failure Analysis | ✅ Complete | Auto-report generation |
| Documentation | ✅ Complete | This guide |
| **Infrastructure** | **✅ Ready** | **Needs execution** |

## Next Steps

1. **Run Stress Tests**: Execute `pytest tests/integration/test_nl_variations.py -v -m "real_llm"`
2. **Analyze Results**: Generate failure report and review pass rates
3. **Run Benchmarks**: Execute performance tests and validate targets
4. **Iterate if Needed**: If pass rate < 90%, improve parser and re-run
5. **Document Results**: Update with actual metrics and learnings

## Example Workflow

```bash
# 1. Run stress tests
pytest tests/integration/test_nl_variations.py -v -m "real_llm and stress_test" \
    --log-cli-level=INFO

# 2. Generate failure report
python tests/fixtures/generate_failure_report.py \
    --test-log tests/test_run.log \
    --output tests/reports/nl_variation_failures.md \
    --json

# 3. Review results
cat tests/reports/nl_variation_failures.md

# 4. Run performance benchmarks
pytest tests/performance/test_nl_performance.py -v -m "benchmark"

# 5. Review metrics
tail -n 100 tests/test_run.log | grep "Latency\|Throughput"
```

## Cost Estimate

**LLM API Calls**:
- Variation generation: ~100 variations × 10 commands = ~1000 LLM calls (generation)
- Variation testing: ~950 variations × 3 LLM calls each (intent, operation, entity) = ~2850 LLM calls
- Performance benchmarks: ~100 commands × 3 LLM calls = ~300 LLM calls
- **Total**: ~4150 LLM calls

**Subscription Note**: Using auth-based flat-rate subscription (no per-token billing), so cost is **$0** (included in subscription).

## Troubleshooting

### Issue: LLM Not Authenticated

**Error**: `LLMConnectionException: Codex CLI not authenticated`

**Solution**:
```bash
# Check LLM status
pytest tests/integration/test_nl_variations.py::TestNLCreateVariations::test_create_epic_variations -v

# If fails, check fixture initialization in tests/conftest.py
# Ensure real_llm fixture is working
```

### Issue: Tests Too Slow

**Symptoms**: Tests taking > 2 hours

**Solutions**:
- Run smaller batches: `pytest -k "test_create_epic_variations"`
- Reduce variation count (edit generator calls in test)
- Check LLM latency with benchmark tests first

### Issue: Low Pass Rate

**Symptoms**: Pass rate < 90%

**Solutions**:
1. Generate failure report: `python tests/fixtures/generate_failure_report.py`
2. Review top failure categories
3. Implement recommended improvements to parser
4. Re-run specific test: `pytest -k "test_create_epic_variations"`

## Related Documentation

- **Phase 2 Completion Summary**: `docs/testing/INTEGRATED_NL_TESTING_COMPLETION_SUMMARY.md`
- **Testing Strategy**: `docs/testing/INTEGRATED_NL_TESTING_STRATEGY.md`
- **Test Guidelines**: `docs/testing/TEST_GUIDELINES.md`
- **Fixture README**: `tests/fixtures/README.md`

---

**Last Updated**: 2025-11-13 (Phase 3 Infrastructure Complete)
