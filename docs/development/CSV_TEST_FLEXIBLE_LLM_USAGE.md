# CSV Tool Creation Test - Flexible LLM Usage Guide

**Test File**: `tests/test_csv_tool_flexible_llm.py`
**Purpose**: Validate end-to-end orchestration with both Ollama and OpenAI Codex
**Created**: November 5, 2025

---

## Overview

This test validates the flexible LLM orchestrator by having Claude Code create a Python script to read a CSV file and calculate average ages. It tests with **both Ollama and OpenAI Codex** to ensure quality scoring, confidence calculation, and decision logic work correctly with different LLM types.

**Key Feature**: Tests run **SEQUENTIALLY** to avoid Claude Code rate limiting (cooldown between prompts).

---

## Test Structure

### Main Test: `test_csv_tool_creation_flexible_llm`

**Parameterized test** that runs twice:
1. **First run**: Ollama (`llm.type: ollama`)
2. **Second run**: OpenAI Codex (`llm.type: openai-codex`)

Each test:
- Creates a temporary workspace with sample CSV (3 people, ages 25-35)
- Configures orchestrator with specific LLM type
- Creates a task to process the CSV
- Mocks agent response (avoids actual Claude execution)
- Validates orchestration flow
- **Adds 5-second delay** between runs to avoid rate limiting

### Documentation Test: `test_csv_tool_sequential_execution_note`

Explains why sequential execution is required (Claude rate limiting).

### Comparison Test: `test_csv_tool_llm_comparison`

**Skipped by default** - Manual execution only for comparative analysis.

---

## Running the Tests

### Quick Test (Both LLM Types, Sequential)

```bash
# Activate venv
source venv/bin/activate

# Run both parameterized tests (Ollama + Codex)
pytest tests/test_csv_tool_flexible_llm.py::test_csv_tool_creation_flexible_llm -v -s

# OR: Run all slow tests in this file
pytest tests/test_csv_tool_flexible_llm.py -m slow -v -s
```

**Expected output**:
```
test_csv_tool_flexible_llm[ollama] PASSED
test_csv_tool_flexible_llm[codex] PASSED
```

### Run Only Ollama Test

```bash
pytest tests/test_csv_tool_flexible_llm.py::test_csv_tool_creation_flexible_llm[ollama] -v -s
```

### Run Only Codex Test

```bash
pytest tests/test_csv_tool_flexible_llm.py::test_csv_tool_creation_flexible_llm[codex] -v -s
```

### Run Comparison Test (Manual)

```bash
# Explicitly run the skipped comparison test
pytest tests/test_csv_tool_flexible_llm.py::test_csv_tool_llm_comparison -v -s
```

This will run both LLM types sequentially and print a comparison table.

---

## Important Notes

### ⚠️ Sequential Execution Required

**DO NOT run these tests in parallel!**

```bash
# ❌ WRONG - Will cause rate limiting
pytest -n 4 tests/test_csv_tool_flexible_llm.py

# ✅ CORRECT - Sequential execution
pytest tests/test_csv_tool_flexible_llm.py
```

**Why?** Claude Code enforces a cooldown between prompts. Concurrent tests will trigger rate limiting and fail.

**How it's enforced**:
- Pytest `@pytest.mark.parametrize` runs tests **sequentially by default**
- 5-second delay added between Ollama and Codex tests
- `fast_time` fixture makes delay instant in test environment

### Test Isolation

Each test run:
- Creates isolated temporary workspace
- Uses separate database file
- Cleans up after completion

### Mocking Strategy

**Ollama Test**:
- Mocks `requests.get` for HTTP API health checks
- Returns mock model list

**Codex Test**:
- Mocks `shutil.which` to find codex CLI
- Returns mock CLI path

**Agent Responses**:
- Both tests mock `agent.send_prompt()` to avoid actual Claude execution
- Simulates Claude creating a Python CSV processing script

---

## Test Configuration

### Ollama Configuration
```python
llm_type = 'ollama'
llm_config = {
    'model': 'qwen2.5-coder:32b',
    'base_url': 'http://localhost:11434',
    'endpoint': 'http://localhost:11434'
}
```

### OpenAI Codex Configuration
```python
llm_type = 'openai-codex'
llm_config = {
    'model': 'codex-mini-latest',
    'codex_command': 'codex',
    'timeout': 60
}
```

---

## Expected Behavior

### Success Criteria

Both tests should:
- ✅ Initialize orchestrator with correct LLM type
- ✅ Verify LLM interface is correct class (LocalLLMInterface vs OpenAICodexLLMPlugin)
- ✅ Create project and task successfully
- ✅ Execute task without errors
- ✅ Return valid result with status
- ✅ Complete within max_iterations (3)

### Possible Outcomes

1. **`completed`**: Task finished successfully (ideal)
2. **`escalated`**: Task needs human review (acceptable for complex tasks)
3. **`max_iterations`**: Exceeded iteration limit (acceptable for test, indicates clarification loop)

### Validation Checks

```python
assert result is not None
assert 'status' in result
assert result['status'] in ['completed', 'escalated', 'max_iterations']
assert 'iterations' in result
assert result['iterations'] >= 1
```

---

## Troubleshooting

### Test Skipped (Deselected)

**Problem**: Tests not running
```bash
$ pytest tests/test_csv_tool_flexible_llm.py
collected 4 items / 4 deselected / 0 selected
```

**Solution**: Run with `-m slow` to include slow tests
```bash
pytest tests/test_csv_tool_flexible_llm.py -m slow -v
```

### Rate Limiting Error

**Problem**: Tests fail with "Too many requests" or similar
```
AgentException: Rate limit exceeded
```

**Solution**:
1. Ensure tests run sequentially (not parallel)
2. Increase delay between tests in code (currently 5s)
3. Wait before re-running tests

### LLM Not Found Error

**Problem**: `PluginNotFoundError: LLM type 'openai-codex' not found`

**Solution**: Ensure registry initialization in `conftest.py` includes:
```python
from src.llm.openai_codex_interface import OpenAICodexLLMPlugin
register_llm('openai-codex')(OpenAICodexLLMPlugin)
```

### Mock Not Working

**Problem**: Tests trying to connect to real Ollama/Codex

**Solution**: Check `monkeypatch` is working correctly:
- Ollama: Verify `requests.get` is mocked
- Codex: Verify `shutil.which` is mocked

---

## Test Maintenance

### Adding New LLM Types

To test with additional LLM types (e.g., Claude API, Gemini):

1. Add new parameter to `@pytest.mark.parametrize`:
```python
@pytest.mark.parametrize('llm_type,llm_config', [
    ('ollama', {...}),
    ('openai-codex', {...}),
    ('claude-api', {...})  # NEW
])
```

2. Add appropriate mocking in test
3. Update expected instance checks
4. Ensure sequential execution maintained

### Updating CSV Task

Current task:
```
Read the CSV file at {path} and calculate the average age of all people.
Print the result as "Average age: X".
```

To change task complexity, modify `task['description']` in test.

### Adjusting Iteration Limits

Current: `max_iterations=3` (fast test)

For real orchestration validation:
```python
result = orchestrator.execute_task(task.id, max_iterations=10)
```

---

## Performance Expectations

### Timing (with fast_time fixture)

- **Per test**: ~2-5 seconds (mocked, no actual LLM calls)
- **Between tests**: 5 seconds delay (instant with fast_time)
- **Total suite**: ~10-15 seconds

### Without Mocking (Real Orchestration)

- **Per test**: 5-10 minutes (actual Claude + LLM orchestration)
- **Between tests**: 5 seconds delay (real time)
- **Total suite**: 10-20 minutes

---

## Related Documentation

- **Analysis**: `docs/development/CSV_TEST_FLEXIBLE_LLM_ANALYSIS.md`
- **Integration Tests**: `tests/test_integration_flexible_llm.py`
- **Unit Tests**: `tests/test_openai_codex_interface.py`
- **Test Guidelines**: `docs/development/TEST_GUIDELINES.md`

---

## CI/CD Integration

### GitHub Actions

```yaml
- name: Run CSV Flexible LLM Tests
  run: |
    source venv/bin/activate
    pytest tests/test_csv_tool_flexible_llm.py -m slow -v
  timeout-minutes: 5
```

### Pre-commit Hook

Tests are marked as `@pytest.mark.slow` and excluded from pre-commit by default.

To run in pre-commit, update `.pre-commit-config.yaml`:
```yaml
- id: pytest
  args: ['-m', 'slow']
```

---

**Last Updated**: November 5, 2025
**Test Status**: ✅ Implemented, syntax verified, collection confirmed
**Next Step**: Run tests to validate both LLM types
