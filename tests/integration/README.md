# Integration Tests

**Purpose**: Validate real LLM connectivity and full system integration
**Speed**: 5-15 minutes
**Run**: Before merge, nightly CI

## Test Categories

### LLM Connectivity (`test_llm_connectivity.py`)
- Ollama connection success/failure
- OpenAI Codex connection (if API key available)
- LLM provider switching
- Timeout handling
- Health check endpoints

**Run**:
```bash
pytest tests/integration/test_llm_connectivity.py -v -m integration
```

### LLM Performance (`test_llm_performance.py`)
- Intent classification latency baselines
- Entity extraction accuracy baselines
- Full pipeline performance

**Run**:
```bash
pytest tests/integration/test_llm_performance.py -v -m "integration and slow"
```

## Prerequisites

### Ollama Tests
- Ollama running on `http://10.0.75.1:11434`
- Qwen model pulled: `ollama pull qwen2.5-coder:32b`

Verify:
```bash
curl http://10.0.75.1:11434/api/tags
```

### OpenAI Codex Tests (Optional)
- Set environment variable: `export OPENAI_API_KEY=sk-...`
- Tests will skip if not set

## Running Tests

```bash
# All integration tests
pytest tests/integration/ -v -m integration

# Only Ollama tests
pytest tests/integration/ -v -m "integration and requires_ollama"

# Skip slow tests
pytest tests/integration/ -v -m "integration and not slow"

# With coverage
pytest tests/integration/ -v -m integration --cov=src --cov-report=term
```

## Expected Performance

| Test Suite | Duration | Pass Rate |
|------------|----------|-----------|
| LLM Connectivity | 2-5 min | 100% |
| LLM Performance | 10-15 min | 100% |

## Troubleshooting

**Ollama connection failed**:
```bash
# Check Ollama running
curl http://10.0.75.1:11434/api/tags

# Restart Ollama
# (On Windows host)
```

**Slow performance**:
- Check RTX 5090 GPU utilization
- Verify no other LLM workloads running
- Check network latency to host
