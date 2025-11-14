# Testing Documentation Index

**Last Updated**: 2025-11-13

---

## Core Testing Guides

- **[Test Guidelines](TEST_GUIDELINES.md)** - WSL2-safe testing practices (CRITICAL) ⚠️
- **[NL Testing Strategy](NL_TESTING_STRATEGY.md)** - Mock vs Real LLM testing strategy
- **[Real LLM Testing Guide](REAL_LLM_TESTING_GUIDE.md)** - Running integration tests with Ollama/Qwen

## New: NL Query Testing Suite (2025-11-13) ⭐

**Bug Fix Release**: Comprehensive testing improvements for NL query system

- **[Implementation Guide for Claude Code](CLAUDE_IMPLEMENTATION_NL_QUERY_TESTS.md)** - Machine-optimized step-by-step implementation guide
- **[Implementation Plan](NL_QUERY_TESTING_IMPLEMENTATION_PLAN.md)** - Human-readable plan with timelines and risk assessment
- **[Testing Strategy](NL_QUERY_TESTING_STRATEGY.md)** - Complete testing strategy for NL queries

**What's New**:
- 4 new test files (100+ tests)
- Integration testing for FastPathMatcher
- StateManager API completeness validation
- Multi-project query filtering tests
- End-to-end NL command workflow tests

**Bugs Fixed**:
- FastPathMatcher API mismatch (entity_type → entity_types)
- Missing StateManager.list_epics() and list_stories() methods
- Query filtering by project_id (multi-project isolation)

## Test Suites

- **[NL Command User Stories](NL_COMMAND_USER_STORIES.md)** - 20 user stories for NL system
- **[NL Test Implementation Plan](NL_TEST_IMPLEMENTATION_PLAN.md)** - 3-phase test roadmap
- **[NL Test Quick Start](NL_TEST_QUICK_START.md)** - Fast onboarding for NL tests

## Phase Reports

- **[Phase 1 Completion](NL_PHASE1_COMPLETION_REPORT.md)** - Core pipeline tests
- **[Phase 2 Summary](NL_PHASE2_SUMMARY.md)** - Validation tests
- **[Phase 3 Final Report](NL_PHASE3_FINAL_REPORT.md)** - E2E and error tests

## Quick Reference

### Run All Tests
```bash
# All tests (mock + real LLM)
pytest tests/ -v -m ""

# Mock tests only (fast - 15s)
pytest tests/test_nl_*.py -v -m "not integration"

# Real LLM tests only (slow - 5-10min, requires Ollama)
pytest tests/test_nl_real_llm_integration.py -v -m integration
```

### Coverage Report
```bash
pytest tests/ --cov=src --cov-report=html --cov-report=term
open htmlcov/index.html
```

### Test File Overview

| Test File | Tests | Type | Time | Coverage |
|-----------|-------|------|------|----------|
| test_nl_intent_classifier.py | ~10 | Mock | 1s | IntentClassifier |
| test_nl_entity_extractor.py | ~15 | Mock | 2s | EntityExtractor |
| test_nl_command_validator.py | ~8 | Mock | 1s | CommandValidator |
| test_nl_command_processor_integration.py | 25 | Mock | 4s | NLCommandProcessor |
| test_nl_e2e_integration.py | 24 | Mock | 5s | Full pipeline |
| test_nl_entity_extractor_bug_prevention.py | 6 | Mock | 1s | Bug prevention |
| **test_nl_real_llm_integration.py** | **33** | **Real LLM** | **5-10min** | **Production validation** |

---

## Testing Philosophy

### Dual Testing Strategy

Obra NL command system uses two complementary test approaches:

1. **Mock Tests** (Fast - 15s)
   - Validate code logic and error handling
   - Run on every commit (CI/CD)
   - Fast feedback for development
   - **Coverage**: ~75% of NL system

2. **Real LLM Tests** (Slow - 5-10min)
   - Validate prompt engineering
   - Test actual LLM accuracy
   - Run before merge (validation gate)
   - **Coverage**: Production behavior validation

**See**: [NL Testing Strategy](NL_TESTING_STRATEGY.md) for complete decision matrix

---

## Prerequisites

### Mock Tests
- ✅ Python 3.12+
- ✅ Virtual environment activated
- ✅ `pip install -r requirements.txt`

### Real LLM Tests
- ✅ All mock test prerequisites
- ✅ Ollama running on `http://172.29.144.1:11434`
- ✅ Qwen 2.5 Coder model: `ollama pull qwen2.5-coder:32b`

---

## Common Workflows

### Local Development

```bash
# Run mock tests (fast feedback)
pytest tests/test_nl_intent_classifier.py -v

# Run with coverage
pytest tests/test_nl_*.py --ignore=tests/test_nl_real_llm_integration.py \
    --cov=src/nl --cov-report=term
```

### Before Commit

```bash
# Run all mock tests
pytest tests/test_nl_*.py -v -m "not integration"

# Expected: 55+ passed in ~15s
```

### Before Merge/PR

```bash
# 1. Run mock tests
pytest tests/test_nl_*.py -v -m "not integration"

# 2. Run real LLM tests (requires Ollama)
pytest tests/test_nl_real_llm_integration.py -v -m integration

# Expected: 88+ total passed (55 mock + 33 real) in ~6-11min
```

---

## Troubleshooting

### Mock Tests Failing

**Common Issue**: Mock LLM returning invalid JSON

**Solution**: Use `mock_llm_smart` fixture from `tests/conftest.py`

```python
def test_example(mock_llm_smart):
    extractor = EntityExtractor(llm_plugin=mock_llm_smart)  # ✅ Valid
    # Not: mock.generate.return_value = MagicMock()  # ❌ Broken
```

### Real LLM Tests Skipped

**Issue**: Tests marked as "deselected"

**Cause**: Default pytest config skips slow/integration tests

**Solution**: Use `-m` flag to include them

```bash
pytest tests/test_nl_real_llm_integration.py -v -m integration
# Or: pytest -m "" (remove all marker filters)
```

### Ollama Connection Errors

**Issue**: `Connection refused` or timeout

**Solutions**:
1. Verify Ollama running: `curl http://172.29.144.1:11434/api/tags`
2. Start Ollama: `ollama serve`
3. Check Windows firewall allows port 11434

---

## Best Practices

1. **Run mock tests first** - Get fast feedback
2. **Use smart fixtures** - Don't create inline mocks
3. **Test both success and failure** - Don't just test happy path
4. **Validate real LLM accuracy** - Set confidence thresholds (≥0.7)
5. **Keep tests fast** - Mock tests should be < 0.5s each
6. **Document failures** - Add bug prevention tests for each bug

---

## Contributing

When adding new NL command features:

1. **Write mock test first** (TDD)
2. **Implement feature**
3. **Add real LLM test** (if it involves prompts)
4. **Update this documentation** (if adding new test files)

**See**: [Test Guidelines](TEST_GUIDELINES.md) for WSL2-specific practices

---

## Testing Documentation Structure

```
docs/testing/
├── README.md                                    (This file)
├── TEST_GUIDELINES.md                           (WSL2-safe testing rules)
│
├── NL Query Testing (NEW - 2025-11-13)
│   ├── CLAUDE_IMPLEMENTATION_NL_QUERY_TESTS.md  (Machine-optimized guide)
│   ├── NL_QUERY_TESTING_IMPLEMENTATION_PLAN.md  (Human-readable plan)
│   └── NL_QUERY_TESTING_STRATEGY.md             (Testing strategy)
│
├── NL Command Testing (Original)
│   ├── NL_TESTING_STRATEGY.md                   (Mock vs Real LLM)
│   ├── REAL_LLM_TESTING_GUIDE.md                (Ollama/Qwen setup)
│   ├── NL_COMMAND_USER_STORIES.md               (20 user stories)
│   ├── NL_TEST_IMPLEMENTATION_PLAN.md           (3-phase roadmap)
│   └── NL_TEST_QUICK_START.md                   (Quick onboarding)
│
├── Coverage & Gap Analysis
│   ├── TEST_COVERAGE_GAP_ANALYSIS.md
│   ├── TESTING_GAP_ANALYSIS_SUMMARY.md
│   ├── WORKFLOW_TEST_GAP_ANALYSIS.md
│   └── WORKFLOW_TEST_FIX_PLAN.md
│
├── Infrastructure & Integration
│   ├── INFRASTRUCTURE_TESTING_STRATEGY.md
│   └── INTEGRATION_TESTING_ENHANCEMENT_PLAN.md
│
└── Phase Reports
    ├── NL_PHASE1_COMPLETION_REPORT.md
    ├── NL_PHASE2_SUMMARY.md
    └── NL_PHASE3_FINAL_REPORT.md
```

---

## Contact

For questions about testing:
- **NL Query Testing**: See [NL_QUERY_TESTING_STRATEGY.md](NL_QUERY_TESTING_STRATEGY.md)
- **NL Command Testing**: See [NL_TESTING_STRATEGY.md](NL_TESTING_STRATEGY.md)
- **System Overview**: See [CLAUDE.md](../../CLAUDE.md)

---

**Maintained by**: Obra Development Team
