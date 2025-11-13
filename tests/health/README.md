# Health Check Tests

**Purpose**: Fast validation that all critical systems are operational
**Speed**: <30 seconds total
**Run**: Every commit, before deployment

## Tests

- `test_llm_connectivity_ollama` - Ollama reachable
- `test_llm_connectivity_openai_codex` - OpenAI config valid
- `test_database_connectivity` - Database accessible
- `test_agent_registry_loaded` - Agents registered
- `test_llm_registry_loaded` - LLMs registered
- `test_configuration_valid` - Config loads
- `test_state_manager_initialization` - StateManager works

## Usage

```bash
# Run all health checks
pytest tests/health/ -v --timeout=30

# Run with coverage
pytest tests/health/ -v --cov=src --cov-report=term
```

## Expected Output

```
tests/health/test_system_health.py::TestSystemHealth::test_llm_connectivity_ollama PASSED
tests/health/test_system_health.py::TestSystemHealth::test_llm_connectivity_openai_codex SKIPPED
tests/health/test_system_health.py::TestSystemHealth::test_database_connectivity PASSED
tests/health/test_system_health.py::TestSystemHealth::test_agent_registry_loaded PASSED
tests/health/test_system_health.py::TestSystemHealth::test_llm_registry_loaded PASSED
tests/health/test_system_health.py::TestSystemHealth::test_configuration_valid PASSED
tests/health/test_system_health.py::TestSystemHealth::test_state_manager_initialization PASSED

6 passed, 1 skipped in <30s
```
