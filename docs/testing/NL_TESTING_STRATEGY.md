# Natural Language Command Testing Strategy

**Created**: 2025-11-11
**Status**: Active
**Applies To**: NL Command System (v1.3.0+)

---

## Overview

The NL Command System uses a **dual testing strategy**:

1. **Mock LLM Tests (Fast)**: Unit and integration tests with mocked LLM responses
2. **Real LLM Tests (Slow)**: End-to-end validation with actual Ollama/Qwen

**Why Both?**
- Mock tests catch code logic errors (15s feedback loop)
- Real LLM tests catch prompt engineering issues (5-10min validation)
- Combined coverage ensures both correctness and production accuracy

---

## Decision Matrix

### When to Use Mock LLM Tests

| Scenario | Use Mocks | Rationale |
|----------|-----------|-----------|
| Unit testing single component | ✅ Yes | Fast, isolated, deterministic |
| Testing error handling logic | ✅ Yes | Control failure modes precisely |
| Testing validation rules | ✅ Yes | No LLM needed for business logic |
| Testing database operations | ✅ Yes | LLM irrelevant to CRUD |
| CI/CD on every commit | ✅ Yes | Fast feedback (15s) |
| Local development TDD | ✅ Yes | Instant feedback loop |

### When to Use Real LLM Tests

| Scenario | Use Real LLM | Rationale |
|----------|--------------|-----------|
| Validating prompt quality | ✅ Yes | Only real LLM can validate |
| Testing intent classification accuracy | ✅ Yes | Mock can't test actual accuracy |
| Testing entity extraction accuracy | ✅ Yes | Mock can't test extraction logic |
| Full E2E pipeline validation | ✅ Yes | Must test production behavior |
| Before merge to main | ✅ Yes | Final validation gate |
| After prompt template changes | ✅ Yes | Verify no regression |
| Debugging LLM issues | ✅ Yes | Reproduce real failure |

### When to Use Both

| Scenario | Approach |
|----------|----------|
| Integration tests | Mock for speed, real LLM subset for validation |
| Bug prevention tests | Mock for regression, real LLM for root cause |
| Performance testing | Mock for baseline, real LLM for actual timing |

---

## Test Suite Organization

### Mock LLM Tests (55 tests, ~15s)

**Files**:
- `tests/test_nl_intent_classifier.py` (10 tests)
- `tests/test_nl_entity_extractor.py` (15 tests)
- `tests/test_nl_command_validator.py` (8 tests)
- `tests/test_nl_command_processor_integration.py` (25 tests, including 4 fixed)
- `tests/test_nl_e2e_integration.py` (24/30 tests passing)
- `tests/test_nl_entity_extractor_bug_prevention.py` (6 tests, all fixed)

**Run Command**:
```bash
# All mock tests
pytest tests/test_nl_*.py --ignore=tests/test_nl_real_llm_integration.py -v

# Expected: 55+ passed in ~15s
```

**Coverage**: ~75% of NL command system

### Real LLM Tests (33 tests, ~5-10min)

**File**: `tests/test_nl_real_llm_integration.py`

**Test Classes**:
- `TestRealLLMIntentClassification` (8 tests) - Intent accuracy
- `TestRealLLMEntityExtraction` (10 tests) - Extraction accuracy
- `TestRealLLMFullPipeline` (8 tests) - E2E workflows
- `TestRealLLMFailureModes` (4 tests) - Error handling
- `TestRealLLMPerformance` (3 tests) - Benchmarking

**Run Command**:
```bash
# All real LLM tests
pytest tests/test_nl_real_llm_integration.py -v -m integration

# Expected: 33 passed in 5-10 minutes
```

**Prerequisites**:
- Ollama running on `http://172.29.144.1:11434`
- Qwen 2.5 Coder model: `ollama pull qwen2.5-coder:32b`

---

## Running Tests

### Development Workflow (Fast Feedback)

```bash
# Run mock tests only (15s)
pytest tests/test_nl_*.py -v -m "not integration"

# Run specific component
pytest tests/test_nl_intent_classifier.py -v

# Watch mode for TDD
pytest-watch tests/test_nl_intent_classifier.py
```

### Pre-Commit Validation (Moderate)

```bash
# Run all mock tests with coverage
pytest tests/test_nl_*.py --ignore=tests/test_nl_real_llm_integration.py \
    --cov=src/nl --cov-report=term --cov-report=html

# Expected: 55+ passed, ~75% coverage, ~15s
```

### Pre-Merge Validation (Full)

```bash
# Run BOTH mock and real LLM tests
pytest tests/test_nl_*.py -v && \
pytest tests/test_nl_real_llm_integration.py -v -m integration

# Expected: 88+ passed total (55 mock + 33 real), ~6-11 minutes
```

### CI/CD Configuration

**On Every Commit** (GitHub Actions):
```yaml
- name: Run mock tests
  run: pytest tests/test_nl_*.py --ignore=tests/test_nl_real_llm_integration.py -v
  # Fast feedback (15s)
```

**On Merge to Main** (GitHub Actions):
```yaml
- name: Start Ollama
  run: docker run -d -p 11434:11434 ollama/ollama
- name: Pull Qwen model
  run: docker exec ollama ollama pull qwen2.5-coder:32b
- name: Run real LLM tests
  run: pytest tests/test_nl_real_llm_integration.py -v -m integration
  # Full validation (5-10 min)
```

---

## Pytest Markers

### Available Markers

```python
# Integration tests (requires Ollama)
@pytest.mark.integration

# Slow tests (> 1 second per test)
@pytest.mark.slow

# Requires Ollama running
@pytest.mark.requires_ollama

# Performance benchmarks
@pytest.mark.benchmark
```

### Running by Marker

```bash
# Skip integration tests (fast)
pytest tests/test_nl_*.py -v -m "not integration"

# Only integration tests
pytest tests/test_nl_*.py -v -m integration

# Skip slow tests
pytest tests/test_nl_*.py -v -m "not slow"
```

---

## Mock Fixtures Reference

### Available Fixtures (conftest.py)

| Fixture | Type | Returns | Use Case |
|---------|------|---------|----------|
| `mock_llm_responses` | Dict | Valid JSON responses | Response templates |
| `mock_llm_smart` | Mock | Context-aware mock | Most tests |
| `mock_llm_simple` | Mock | Always returns task | Basic tests |
| `real_llm_config` | Config | Real LLM config | Integration tests |
| `real_state_manager` | StateManager | DB with real config | Integration tests |
| `real_llm_interface` | LLMInterface | Real Ollama connection | Integration tests |
| `real_intent_classifier` | IntentClassifier | Real component | Integration tests |
| `real_entity_extractor` | EntityExtractor | Real component | Integration tests |
| `real_nl_processor` | NLCommandProcessor | Full pipeline | E2E tests |

### Example Usage

**Mock Tests**:
```python
def test_with_smart_mock(mock_llm_smart, test_config, test_state):
    extractor = EntityExtractor(llm_plugin=mock_llm_smart)

    result = extractor.extract("Create epic 'Test'", "COMMAND")
    assert result.entity_type == "epic"
```

**Real LLM Tests**:
```python
@pytest.mark.integration
def test_with_real_llm(real_entity_extractor):
    # No mock injection - uses real Ollama
    result = real_entity_extractor.extract("Create epic 'Test'", "COMMAND")
    assert result.entity_type == "epic"
    assert result.confidence >= 0.7  # Real accuracy threshold
```

---

## Coverage Goals

| Component | Mock Tests | Real LLM Tests | Combined |
|-----------|------------|----------------|----------|
| IntentClassifier | 85% | Accuracy validation | 90% |
| EntityExtractor | 90% | Accuracy validation | 95% |
| CommandValidator | 100% | N/A (no LLM) | 100% |
| CommandExecutor | 95% | N/A (no LLM) | 95% |
| NLCommandProcessor | 80% | E2E workflows | 90% |
| ResponseFormatter | 90% | N/A (formatting) | 90% |

**Overall Target**: 90% code coverage, 85% real LLM accuracy

---

## Performance Benchmarks

### Mock Tests

| File | Tests | Time | Per Test |
|------|-------|------|----------|
| test_nl_intent_classifier.py | ~10 | 1s | 0.1s |
| test_nl_entity_extractor.py | ~15 | 2s | 0.13s |
| test_nl_command_validator.py | ~8 | 1s | 0.13s |
| test_nl_command_processor_integration.py | 25 | 4s | 0.16s |
| test_nl_e2e_integration.py | 24 | 5s | 0.21s |
| test_nl_entity_extractor_bug_prevention.py | 6 | 1s | 0.17s |
| **TOTAL** | **~88** | **~15s** | **0.17s** |

### Real LLM Tests

| Test Class | Tests | Time | Per Test |
|------------|-------|------|----------|
| TestRealLLMIntentClassification | 8 | 30-60s | 4-8s |
| TestRealLLMEntityExtraction | 10 | 90-150s | 9-15s |
| TestRealLLMFullPipeline | 8 | 120-180s | 15-23s |
| TestRealLLMFailureModes | 4 | 30-60s | 8-15s |
| TestRealLLMPerformance | 3 | 30-60s | 10-20s |
| **TOTAL** | **33** | **5-10min** | **10-18s** |

**Note**: Real LLM test time varies based on:
- LLM model size (Qwen 32B vs 7B)
- GPU availability (RTX 5090 vs CPU)
- Network latency (local vs remote Ollama)
- Context length (longer prompts = slower)

---

## Troubleshooting

### Mock Tests Failing

**Symptom**: `EntityExtractionException: Missing required fields`

**Cause**: Mock LLM returning invalid JSON

**Fix**:
```python
# Use smart mock fixture instead of inline mock
def test_example(mock_llm_smart, ...):  # ✅
    extractor.llm_plugin = mock_llm_smart

# Don't create broken inline mocks
mock.generate.return_value = MagicMock()  # ❌
```

### Real LLM Tests Failing

**Symptom**: `Connection refused` or `Timeout`

**Cause**: Ollama not running

**Fix**:
```bash
# Start Ollama on host
ollama serve

# Pull model
ollama pull qwen2.5-coder:32b

# Verify
curl http://172.29.144.1:11434/api/tags
```

**Symptom**: Low confidence scores (< 0.7)

**Cause**: Prompt template needs improvement

**Fix**:
1. Check prompt templates in `prompts/`
2. Review LLM reasoning: `print(result.reasoning)`
3. Update templates based on findings
4. Re-run real LLM tests to validate

### Performance Issues

**Symptom**: Real LLM tests taking > 15 minutes

**Cause**: Network latency or slow GPU

**Fix**:
1. Use local Ollama (not remote)
2. Use smaller model for testing (qwen2.5-coder:7b)
3. Reduce context length in prompts
4. Check GPU utilization: `nvidia-smi`

---

## Best Practices

### Mock Test Best Practices

1. **Use Smart Mock Fixture**: `mock_llm_smart` auto-detects entity type
2. **Validate Schema**: Ensure mock responses match `obra_schema.json`
3. **Test Error Cases**: Don't just test happy path
4. **Fast Execution**: Keep per-test time < 0.5s
5. **Deterministic**: Same input = same output (no randomness)

### Real LLM Test Best Practices

1. **Set Confidence Thresholds**: Validate accuracy, not just success
2. **Verify DB State**: Check database after execution (E2E)
3. **Test Edge Cases**: Emojis, code blocks, special chars
4. **Use Low Temperature**: 0.1 for consistency (not 0.7)
5. **Module-Scoped Fixtures**: Reuse config/state across tests

### General Testing Best Practices

1. **Run Mocks First**: Fast feedback before slow validation
2. **CI/CD Strategy**: Mocks on every commit, real LLM on merge
3. **Monitor Performance**: Track test execution time trends
4. **Update Baselines**: When prompts change, update expected accuracy
5. **Document Failures**: Add bug prevention tests for every bug found

---

## Migration Guide

### Updating Existing Tests to Use New Fixtures

**Before** (broken mock):
```python
def test_old_way(test_config, state_manager):
    mock_llm = MagicMock()
    mock_llm.generate.return_value = MagicMock()  # ❌ Invalid
    # ...
```

**After** (fixed with smart mock):
```python
def test_new_way(mock_llm_smart, test_config, test_state):
    extractor = EntityExtractor(llm_plugin=mock_llm_smart)
    result = extractor.extract("Create epic 'Test'", "COMMAND")
    # ...
```

### Adding Real LLM Coverage for Existing Feature

1. Identify feature to test (e.g., new entity type)
2. Write mock test first (fast feedback)
3. Add real LLM test in `test_nl_real_llm_integration.py`
4. Run both to validate
5. Update this strategy doc if needed

---

## Future Enhancements

**Planned Improvements**:
- [ ] LLM caching to speed up real LLM tests (30% faster)
- [ ] Parallel real LLM test execution (`pytest-xdist`)
- [ ] A/B testing integration (compare prompt versions)
- [ ] Real LLM test result analytics dashboard
- [ ] Automated prompt optimization based on test failures

**See**: `docs/design/enhancements/` for detailed proposals

---

## References

- **Test Files**: `tests/test_nl_*.py`
- **Real LLM Tests**: `tests/test_nl_real_llm_integration.py`
- **Mock Fixtures**: `tests/conftest.py`
- **Real LLM Guide**: `docs/development/REAL_LLM_TESTING_GUIDE.md`
- **Obra Schema**: `src/nl/schemas/obra_schema.json`
- **Prompt Templates**: `prompts/intent_classification.txt`, `prompts/entity_extraction.txt`
- **Test Guidelines**: `docs/development/TEST_GUIDELINES.md`
- **NL Command Guide**: `docs/guides/NL_COMMAND_GUIDE.md`

---

**Last Updated**: 2025-11-11
**Version**: 1.0
**Maintainer**: Obra Development Team
