# testing-guidelines

**Description**: Comprehensive pytest patterns for Obra including WSL2 resource limits (0.5s sleep, 5 threads, 20KB memory), shared fixtures (test_config, fast_time), threading patterns, and crash prevention. Includes detailed examples of mocking, cleanup, and integration testing.

**Triggers**: pytest, testing, test patterns, fixtures, fast_time, WSL2 crashes, thread safety, test_config, threading, test guidelines

**Token Cost**: ~600 tokens when loaded

**Dependencies**: pytest, test fixtures from conftest.py

---

## Critical Resource Limits (WSL2 Crash Prevention)

MUST follow these limits to prevent WSL2 kernel panics:

- **Max sleep**: 0.5s per test
- **Max threads**: 5 per test
- **Max memory**: 20KB per test allocation
- **Mandatory**: `timeout=` on all thread joins
- **Mark heavy tests**: `@pytest.mark.slow`

**Why**: M2 testing caused WSL2 crashes from 75s cumulative sleeps, 25+ threads, 100KB+ memory.

**Full Documentation**: `docs/testing/TEST_GUIDELINES.md`

---

## Shared Fixtures

ALWAYS use these fixtures from conftest.py:

### test_config
```python
def test_orchestrator(test_config):
    """Use shared test configuration."""
    orchestrator = Orchestrator(config=test_config)
    assert orchestrator.config is not None
```

### fast_time
```python
def test_completion(fast_time):
    """Mock time for sleeps >0.5s."""
    monitor.mark_complete()
    time.sleep(2.0)  # Instant with fast_time mock
    assert monitor.is_complete()
```

---

## Threading Patterns

MUST use timeouts on all joins:

```python
def test_concurrent(test_config):
    """Test concurrent operations."""
    threads = [Thread(target=worker) for _ in range(3)]  # Max 5
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5.0)  # MANDATORY - prevents hangs
```

---

## Test Commands

```bash
pytest                           # All tests
pytest --cov=src --cov-report=term  # With coverage
pytest -m "not slow"             # Fast tests only
pytest tests/test_state.py       # Specific module
watchexec -e py pytest           # Auto-run on changes
```

---

## Common Patterns

### Cleanup
```python
def test_with_cleanup():
    resource = acquire_resource()
    try:
        # Test code
        pass
    finally:
        resource.cleanup()
```

### Mocking
```python
def test_with_mock(mocker):
    mock_llm = mocker.patch('src.core.orchestrator.LLMInterface')
    mock_llm.send_prompt.return_value = "response"
```

---

## Critical Notes

- 88% unit test coverage missed 6 bugs
- MUST write integration tests
- NEVER skip thread cleanup → WSL2 crash
- NEVER exceed resource limits → WSL2 crash
