# Integration Testing Implementation - Startup Prompt

**Purpose**: Start fresh Claude session to implement integration testing enhancements
**Created**: 2025-11-12

---

## Copy This Prompt to Fresh Claude Session

```
I need you to implement the integration testing enhancement plan for the Obra project.

Please read and follow this startup guide:
docs/development/INTEGRATION_TESTING_IMPLEMENTATION_PLAN.md

CRITICAL PREREQUISITES:
1. Read docs/development/TEST_GUIDELINES.md FIRST to avoid WSL2 crashes
2. Understand the 4-tier testing strategy
3. Work tier by tier with BREAKPOINTS after each tier

KEY CONSTRAINTS FROM TEST_GUIDELINES.md:
- Max sleep per test: 0.5s (use `fast_time` fixture for longer)
- Max threads per test: 5 (with mandatory `timeout=` on join)
- Max memory allocation: 20KB per test
- Mark slow tests: @pytest.mark.slow
- Mark integration tests: @pytest.mark.integration

IMPLEMENTATION APPROACH:
- Start with Tier 1 (Health Checks & Smoke Tests - 17 tests)
- Stop at BREAKPOINT 1 and verify all tests pass
- Report to user before proceeding to Tier 2
- Continue tier by tier with breakpoints

TIER 1 DELIVERABLES:
- tests/health/test_system_health.py (7 tests)
- tests/smoke/test_smoke_workflows.py (10 tests)
- tests/health/README.md
- tests/smoke/README.md
- pytest.ini updates

VERIFICATION AT BREAKPOINT 1:
Run: pytest tests/health/ tests/smoke/ -v
Expected: 16-17 tests passing in <2 minutes

Start with Tier 1 and let me know when you've completed it and all tests pass.
```

---

## Alternative Minimal Prompt (If First Is Too Long)

```
Implement integration testing for Obra project following:
docs/development/INTEGRATION_TESTING_IMPLEMENTATION_PLAN.md

Read docs/development/TEST_GUIDELINES.md FIRST (avoid WSL2 crashes).

Start with Tier 1 (Health & Smoke tests). Stop at BREAKPOINT 1.
Verify: pytest tests/health/ tests/smoke/ -v (expect 17 tests passing).

Let me know when Tier 1 complete.
```

---

## What Claude Will Do

### Tier 1 Session (First)
1. Read TEST_GUIDELINES.md
2. Read INTEGRATION_TESTING_IMPLEMENTATION_PLAN.md
3. Create tests/health/test_system_health.py
4. Create tests/smoke/test_smoke_workflows.py
5. Create README files
6. Update pytest.ini
7. Run verification: `pytest tests/health/ tests/smoke/ -v`
8. Report results and wait for approval to continue

### Tier 2 Session (After Tier 1 Approved)
1. Create tests/integration/test_llm_connectivity.py
2. Create tests/integration/test_llm_performance.py
3. Create tests/integration/README.md
4. Run verification: `pytest tests/integration/test_llm_*.py -v -m integration`
5. Report results

### Tier 3 Session (After Tier 2 Approved)
1. Create tests/integration/test_agent_connectivity.py
2. Create tests/integration/test_orchestrator_workflows.py (CRITICAL)
3. Update tests/conftest.py
4. Run verification: `pytest tests/integration/test_agent*.py tests/integration/test_orchestrator*.py -v -m integration`
5. Report results

### Tier 4 Session (After Tier 3 Approved)
1. Create tests/integration/test_configuration_management.py
2. Create tests/integration/test_logging_and_metrics.py
3. Create src/core/logging_config.py
4. Create src/core/metrics.py
5. Update src/cli.py (add health command)
6. Run verification: `pytest tests/integration/test_configuration*.py tests/integration/test_logging*.py -v`
7. Report results

---

## User Commands at Each Breakpoint

### After Tier 1 Complete
```bash
# Verify
pytest tests/health/ tests/smoke/ -v

# If passing, tell Claude: "Continue to Tier 2"
# If failing, debug issues first
```

### After Tier 2 Complete
```bash
# Verify (requires Ollama running)
pytest tests/integration/test_llm_*.py -v -m integration

# If passing, tell Claude: "Continue to Tier 3"
```

### After Tier 3 Complete
```bash
# Verify (SLOW - 20-30 minutes)
pytest tests/integration/test_agent*.py tests/integration/test_orchestrator*.py -v -m integration

# If passing, tell Claude: "Continue to Tier 4"
```

### After Tier 4 Complete
```bash
# Verify
pytest tests/integration/test_configuration*.py tests/integration/test_logging*.py -v

# Test health command
python -m src.cli health

# If all passing, tell Claude: "Implementation complete, generate summary"
```

---

## Expected Timeline

| Tier | Development | Testing | Total |
|------|------------|---------|-------|
| Tier 1 | 1 hour | 5 min | ~1-2 hours |
| Tier 2 | 2 hours | 15 min | ~2-3 hours |
| Tier 3 | 3 hours | 30 min | ~3-4 hours |
| Tier 4 | 2 hours | 10 min | ~2-3 hours |
| **Total** | **8 hours** | **1 hour** | **8-12 hours** |

With breakpoints and user approval, expect 2-3 days of wall-clock time.

---

## Success Metrics

### After Full Implementation
- ✅ 50+ new tests created
- ✅ All tiers passing (health, smoke, LLM, agent, config)
- ✅ Structured logging infrastructure in place
- ✅ Metrics collection working
- ✅ Health CLI command functional
- ✅ 90%+ test coverage
- ✅ No WSL2 crashes
- ✅ All guidelines followed

### Coverage Improvement
- **Before**: 88% code coverage, 0% workflow coverage
- **After**: 90%+ code coverage, 95%+ workflow coverage

### Manual Testing Reduction
- **Before**: 30 min/feature manual testing
- **After**: 5 min/feature (95% automated)

---

## Troubleshooting

### If Tests Fail at Breakpoint

**Health checks fail**:
- Check Ollama running: `curl http://10.0.75.1:11434/api/tags`
- Check database accessible
- Check virtual environment active

**LLM integration tests fail**:
- Verify Ollama has qwen2.5-coder:32b pulled
- Check network connectivity to host
- Verify timeout values appropriate

**Orchestrator tests fail**:
- Check Claude Code CLI installed
- Verify workspace permissions
- Check agent configuration

**WSL2 crashes**:
- Review TEST_GUIDELINES.md constraints
- Check for sleep > 0.5s
- Check for threads > 5 without timeout
- Reduce test parallelism

---

## Post-Implementation

After all 4 tiers complete:

1. Run full test suite: `pytest tests/ -v --cov=src --cov-report=html`
2. Review coverage report: `open htmlcov/index.html`
3. Update CHANGELOG.md
4. Commit changes
5. Create PR with test results

---

## Questions?

If Claude gets stuck or needs clarification:
- Review the implementation plan
- Check TEST_GUIDELINES.md for constraints
- Look at existing tests for patterns
- Ask user for guidance
