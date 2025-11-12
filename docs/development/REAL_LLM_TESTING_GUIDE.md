# Real LLM Testing Guide

**Created**: 2025-11-11
**Purpose**: Guide for running integration tests with actual Ollama/Qwen LLM

---

## Overview

The Obra NL command system has two test suites:

1. **Mock Tests** (Fast) - Use `mock_llm_smart` fixture - 55 tests in ~10s
2. **Real LLM Tests** (Slow) - Use actual Ollama/Qwen - 30 tests in ~5-10min

**Real LLM tests validate**:
- Prompt engineering quality
- Production LLM behavior
- Intent classification accuracy
- Entity extraction accuracy
- Full pipeline integration
- Error handling with real timeouts

---

## Prerequisites

### 1. Ollama Service Running

**On Host Machine** (Windows 11 with RTX 5090):
```bash
# Start Ollama service
ollama serve

# Pull Qwen model (if not already)
ollama pull qwen2.5-coder:32b

# Verify service is running
curl http://172.29.144.1:11434/api/tags
```

**Expected Output**:
```json
{
  "models": [
    {
      "name": "qwen2.5-coder:32b",
      "modified_at": "2025-11-11T...",
      ...
    }
  ]
}
```

### 2. Network Connectivity

From WSL2, verify you can reach the host Ollama service:
```bash
# Test connection
curl http://172.29.144.1:11434/api/tags

# If connection fails, check Windows firewall
# Allow incoming on port 11434 for WSL2 subnet
```

### 3. Python Environment

```bash
# Activate venv
source venv/bin/activate

# Verify dependencies
pip list | grep -E "(pytest|requests|ollama)"
```

---

## Running Real LLM Tests

### Quick Start

```bash
# Run ALL real LLM tests (5-10 minutes)
pytest tests/test_nl_real_llm_integration.py -v -m integration --tb=short

# Expected output:
# ===================== 30 passed in ~5-10min =====================
```

### Run Specific Test Categories

```bash
# Intent classification only (8 tests, ~1-2 min)
pytest tests/test_nl_real_llm_integration.py::TestRealLLMIntentClassification -v

# Entity extraction only (10 tests, ~2-3 min)
pytest tests/test_nl_real_llm_integration.py::TestRealLLMEntityExtraction -v

# Full pipeline E2E (8 tests, ~2-3 min)
pytest tests/test_nl_real_llm_integration.py::TestRealLLMFullPipeline -v

# Failure modes (4 tests, ~1-2 min)
pytest tests/test_nl_real_llm_integration.py::TestRealLLMFailureModes -v
```

### Run Individual Tests

```bash
# Test specific intent classification
pytest tests/test_nl_real_llm_integration.py::TestRealLLMIntentClassification::test_clear_command_create_task -v

# Test epic extraction
pytest tests/test_nl_real_llm_integration.py::TestRealLLMEntityExtraction::test_extract_epic_from_natural_language -v
```

---

## Test Execution Modes

### Mode 1: Development (Skip Slow Tests)

**Default** - Skips real LLM tests for fast feedback:
```bash
# Run all tests EXCEPT real LLM (default)
pytest tests/test_nl_*.py

# Uses mock fixtures, completes in ~15s
# ===================== 55 passed in ~15s =====================
```

### Mode 2: Pre-Commit (Mock Tests Only)

Run before committing to verify mock tests:
```bash
# Run only mock-based tests
pytest tests/test_nl_*.py -m "not integration" -v

# Fast validation: 55 passed in ~15s
```

### Mode 3: CI/Merge (Full Validation)

Run before merging to validate production behavior:
```bash
# Run ALL tests (mock + real LLM)
pytest tests/test_nl_*.py -m "" --tb=short

# Expected: 85 passed (55 mock + 30 real LLM) in ~10min
```

### Mode 4: Performance Benchmarking

```bash
# Run with pytest-benchmark (requires plugin)
pip install pytest-benchmark

pytest tests/test_nl_real_llm_integration.py::TestRealLLMPerformance -v --benchmark-only

# Generates performance report with stats
```

---

## Understanding Test Output

### Successful Test

```
tests/test_nl_real_llm_integration.py::TestRealLLMIntentClassification::test_clear_command_create_task PASSED [12%]
```

**Timing**: Real LLM tests take 0.3-2.0s per test
- Fast: Intent classification (~0.3-0.5s)
- Medium: Entity extraction (~0.5-1.0s)
- Slow: Full pipeline (~1.0-2.0s)

### Failed Test Example

```
FAILED tests/test_nl_real_llm_integration.py::TestRealLLMEntityExtraction::test_extract_epic_from_natural_language

AssertionError: Confidence 0.65 below threshold 0.8
```

**Common Failure Reasons**:
1. **Low confidence** - LLM uncertain (may need prompt tuning)
2. **Wrong entity type** - LLM misclassified (prompt ambiguity)
3. **Missing fields** - LLM didn't extract required field
4. **Timeout** - LLM took too long (increase timeout or optimize)

---

## Troubleshooting

### Issue 1: Connection Timeout

**Error**:
```
requests.exceptions.ConnectionError: ('Connection aborted.', timeout('timed out'))
```

**Solutions**:
1. Verify Ollama is running: `curl http://172.29.144.1:11434/api/tags`
2. Check Windows firewall allows port 11434
3. Verify WSL2 can reach host: `ping 172.29.144.1`
4. Increase timeout in `real_llm_config` fixture (30s → 60s)

### Issue 2: Model Not Found

**Error**:
```
ollama.exceptions.ResponseError: model 'qwen2.5-coder:32b' not found
```

**Solution**:
```bash
# Pull the model on host
ollama pull qwen2.5-coder:32b

# Verify it exists
ollama list
```

### Issue 3: Low Confidence Scores

**Error**:
```
AssertionError: Confidence 0.55 below threshold 0.7
```

**Diagnosis**:
- LLM is uncertain about classification
- Prompt may be ambiguous
- Temperature too high (should be 0.1)

**Solutions**:
1. Check prompt clarity in test input
2. Lower confidence threshold temporarily to 0.6
3. Review LLM reasoning: `print(result.reasoning)`
4. Consider prompt engineering improvements

### Issue 4: Inconsistent Results

**Symptom**: Same test passes sometimes, fails others

**Causes**:
- Temperature too high (use 0.1 for consistency)
- LLM under load (slow response)
- Prompt needs more specificity

**Solutions**:
```python
# In real_llm_config fixture
config.set('llm.temperature', 0.05)  # Even lower for max consistency
config.set('llm.top_p', 0.9)        # Reduce randomness
```

---

## Performance Expectations

### Test Execution Time

| Test Category | Count | Avg Time | Total Time |
|--------------|-------|----------|------------|
| Intent Classification | 8 | 0.4s | ~3s |
| Entity Extraction | 10 | 0.7s | ~7s |
| Full Pipeline E2E | 8 | 1.5s | ~12s |
| Failure Modes | 4 | 1.0s | ~4s |
| **Total** | **30** | **0.9s** | **~26s** |

**Note**: Actual time varies based on:
- LLM hardware (RTX 5090 = fast)
- Model size (32B = slower than 7B)
- System load
- Network latency (WSL2 → Host)

### Optimization Tips

1. **Use Module-Scoped Fixtures**
   - `real_llm_config` - Shared across all tests
   - `real_state_manager` - Reused database
   - Saves ~5-10s setup time

2. **Run in Parallel** (Experimental)
   ```bash
   # Requires pytest-xdist
   pip install pytest-xdist
   pytest tests/test_nl_real_llm_integration.py -n 4 -v
   ```
   **Warning**: May cause Ollama concurrency issues

3. **Cache Results** (Future Enhancement)
   - Cache LLM responses by input hash
   - Reduces repeat calls for same input

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Real LLM Tests

on:
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM

jobs:
  test-real-llm:
    runs-on: self-hosted  # Requires machine with Ollama
    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Verify Ollama
        run: curl http://172.29.144.1:11434/api/tags

      - name: Run Real LLM Tests
        run: pytest tests/test_nl_real_llm_integration.py -v -m integration --tb=short

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: test-results
          path: tests/test_run.log
```

### Pre-Merge Checklist

Before merging NL command changes:
- [ ] All mock tests pass (55/55)
- [ ] All real LLM tests pass (30/30)
- [ ] No new test failures introduced
- [ ] Confidence thresholds maintained (≥0.7)
- [ ] Execution time acceptable (<12 min total)

---

## Test Development Guidelines

### Adding New Real LLM Tests

1. **Choose Appropriate Category**
   - Intent classification → `TestRealLLMIntentClassification`
   - Entity extraction → `TestRealLLMEntityExtraction`
   - Full pipeline → `TestRealLLMFullPipeline`
   - Error handling → `TestRealLLMFailureModes`

2. **Use Proper Fixtures**
   ```python
   def test_new_feature(self, real_intent_classifier):
       """REAL LLM: Test description"""
       result = real_intent_classifier.classify("Test input")
       assert_valid_intent_result(result, "COMMAND", min_confidence=0.8)
   ```

3. **Set Confidence Thresholds**
   - High confidence (0.8-0.9): Clear, unambiguous inputs
   - Medium confidence (0.7-0.8): Standard cases
   - Low confidence (0.6-0.7): Edge cases, complex inputs

4. **Add Descriptive Docstrings**
   ```python
   def test_extract_epic_with_priority(self, real_entity_extractor):
       """REAL LLM: Extract epic with priority field from natural language"""
   ```

5. **Use Timeouts for Failure Tests**
   ```python
   @pytest.mark.timeout(35)
   def test_timeout_handling(self, real_llm_config):
       """Test with shorter timeout"""
   ```

---

## Metrics and Monitoring

### Key Metrics to Track

1. **Pass Rate**: Target 100% (30/30)
2. **Avg Confidence**: Target ≥0.85
3. **Execution Time**: Target <10 minutes
4. **Consistency**: Same test should have same result 95% of time

### Monitoring Script

```python
# scripts/monitor_llm_tests.py
import subprocess
import json

def run_and_analyze():
    result = subprocess.run(
        ["pytest", "tests/test_nl_real_llm_integration.py", "-v", "--json-report"],
        capture_output=True
    )

    # Parse results
    with open(".report.json") as f:
        data = json.load(f)

    print(f"Pass Rate: {data['summary']['passed']}/{data['summary']['total']}")
    print(f"Avg Duration: {data['summary']['duration'] / data['summary']['total']:.2f}s")
```

---

## FAQ

### Q: Why do real LLM tests take so long?

**A**: Each test makes actual LLM API calls which take 0.3-2.0s each. Mock tests return instantly. Real LLM tests validate production behavior, not just code logic.

### Q: Can I run real LLM tests without Ollama?

**A**: No. Real LLM tests require actual Ollama service. Use mock tests for development without Ollama.

### Q: What if a real LLM test fails but mock test passes?

**A**: This indicates a prompt engineering issue. The mock expects certain behavior, but the real LLM doesn't follow it. Fix the prompt or adjust expectations.

### Q: How often should I run real LLM tests?

**A**:
- **Development**: Run mock tests (fast feedback)
- **Pre-commit**: Run mock tests
- **Pre-merge**: Run real LLM tests (validate production)
- **CI**: Run real LLM tests nightly or on main branch

### Q: Can I use a different LLM model?

**A**: Yes. Modify `real_llm_config` fixture:
```python
config.set('llm.model', 'qwen2.5-coder:14b')  # Smaller, faster
config.set('llm.model', 'llama3.1:70b')       # Larger, smarter
```

**Note**: Confidence thresholds may need adjustment for different models.

---

## Next Steps

1. **Run your first real LLM test**:
   ```bash
   pytest tests/test_nl_real_llm_integration.py::TestRealLLMIntentClassification::test_clear_command_create_task -v
   ```

2. **Verify full suite passes**:
   ```bash
   pytest tests/test_nl_real_llm_integration.py -v -m integration
   ```

3. **Review test output** for any failures and investigate

4. **Integrate into your workflow** (pre-merge validation)

---

## References

- **Test File**: `tests/test_nl_real_llm_integration.py`
- **Mock Fixtures**: `tests/conftest.py` (`mock_llm_smart`)
- **NL Command Guide**: `docs/guides/NL_COMMAND_GUIDE.md`
- **Test Plan**: `docs/development/NL_TEST_SUITE_FIX_AND_ENHANCEMENT_PLAN.md`

---

**Last Updated**: 2025-11-11
**Maintained by**: Obra Development Team
