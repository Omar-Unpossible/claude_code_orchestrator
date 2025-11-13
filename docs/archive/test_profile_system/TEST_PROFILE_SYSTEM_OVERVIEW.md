# Test Profile System - Implementation Overview

**Created**: 2025-11-13
**Status**: Proposed
**Estimated Effort**: 2-4 hours
**Priority**: P2 (High value, not blocking)

---

## Executive Summary

Implement a profile-based test configuration system to enable easy testing with multiple LLM providers (Ollama, OpenAI Codex, Anthropic Claude, etc.) without manual environment variable management.

**Current State**: Tests can use different LLMs via environment variables, but it's manual and error-prone.

**Desired State**: One command to switch LLMs: `pytest --profile=openai`

---

## Problem Statement

### Current Limitations

1. **Manual Configuration Required**
   - Must set multiple environment variables: `ORCHESTRATOR_LLM_TYPE`, `ORCHESTRATOR_LLM_MODEL`, API keys
   - Easy to forget parameters or set them incorrectly
   - Not documented or discoverable

2. **Not Scalable**
   - Each new LLM requires remembering different parameters
   - Model-specific settings (timeout, temperature, max_tokens) not captured
   - Hard to test across multiple LLMs systematically

3. **CI/CD Challenges**
   - Difficult to create matrix tests across multiple models
   - No clean way to test "does this work with all our supported LLMs?"

4. **Team Friction**
   - Onboarding: "How do I test with OpenAI?" → long explanation
   - No self-documenting configuration
   - Inconsistent test practices across team

### Example: Current Workflow (Manual)

```bash
# Developer wants to test with OpenAI Codex
export ORCHESTRATOR_LLM_TYPE=openai-codex
export ORCHESTRATOR_LLM_MODEL=gpt-5-codex
export OPENAI_API_KEY=sk-...
export LLM_TIMEOUT=120
export LLM_TEMPERATURE=0.1

pytest tests/integration/ -v -m integration

# Repeat this every time, or forget and get confused why tests fail
```

---

## Solution: Profile-Based Configuration

### Desired Workflow

```bash
# Developer wants to test with OpenAI Codex
pytest tests/integration/ -v --profile=openai

# Or test with default (Ollama)
pytest tests/integration/ -v

# Or test with Anthropic Claude (future)
pytest tests/integration/ -v --profile=anthropic
```

**Key Insight**: Profile files capture all model-specific configuration in one place, discoverable and version-controlled.

---

## Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Test Execution                            │
│  pytest tests/integration/ -v --profile=openai              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Pytest Plugin/Fixture                           │
│  - Parse --profile flag                                      │
│  - Load profile from config/profiles/{name}.yaml            │
│  - Merge with base config                                    │
│  - Validate required env vars (API keys)                     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  Profile Files                               │
│  config/profiles/                                            │
│    ├── test-ollama.yaml      (default)                      │
│    ├── test-openai.yaml      (OpenAI Codex)                 │
│    ├── test-anthropic.yaml   (future)                       │
│    └── test-llama3.yaml      (future)                       │
└─────────────────────────────────────────────────────────────┘
```

### Profile File Structure

**Format**: Simple YAML with LLM-specific settings

```yaml
# config/profiles/test-openai.yaml
profile_name: openai-codex
description: OpenAI Codex (GPT-5) for testing

llm:
  type: openai-codex
  model: gpt-5-codex
  timeout: 120
  temperature: 0.1
  max_tokens: 8000
  retry_attempts: 3

# API key from environment (never stored in file)
env_vars:
  required:
    - OPENAI_API_KEY
  optional:
    - OPENAI_ORG_ID

# Test-specific overrides
test_config:
  skip_slow_tests: false
  max_test_duration: 300  # seconds
```

### Profile Loader Utility

**Location**: `src/testing/profile_loader.py`

**Responsibilities**:
1. Load profile YAML file
2. Merge with base config
3. Validate required environment variables
4. Inject into Config object
5. Provide helpful error messages if setup incomplete

### Pytest Integration

**Location**: `tests/conftest.py` (enhance existing)

**Mechanism**:
- Custom pytest plugin to add `--profile` CLI option
- Override `test_config` fixture to use profile if specified
- Fallback to default profile (Ollama) if not specified

---

## Implementation Plan

### Phase 1: Core Infrastructure (2 hours)

1. **Profile Loader Utility** (45 min)
   - Create `src/testing/profile_loader.py`
   - Functions: `load_profile()`, `validate_profile()`, `merge_with_config()`
   - Error handling for missing profiles, invalid YAML, missing env vars

2. **Pytest Plugin** (45 min)
   - Add `--profile` option to pytest via conftest.py
   - Modify `test_config` fixture to use profile
   - Default to `test-ollama` profile

3. **Profile Files** (30 min)
   - Create `config/profiles/` directory
   - Create `test-ollama.yaml` (default)
   - Create `test-openai.yaml` (OpenAI Codex)
   - Document profile format with comments

### Phase 2: Testing & Documentation (1 hour)

4. **Unit Tests** (30 min)
   - Test profile loader: load, validate, merge
   - Test pytest plugin: --profile flag parsing
   - Test error cases: missing profile, missing API key

5. **Documentation** (30 min)
   - Update `docs/development/TEST_GUIDELINES.md` with profile usage
   - Create `docs/guides/TEST_PROFILES_GUIDE.md` with examples
   - Document how to create new profiles

### Phase 3: Enhancement (1 hour - optional)

6. **CI/CD Integration** (30 min)
   - Update GitHub Actions to use profiles
   - Create matrix test workflow for multiple LLMs
   - Document secrets management

7. **Additional Profiles** (30 min)
   - Create `test-anthropic.yaml` (placeholder for future)
   - Create `test-llama3.yaml` (placeholder for future)

---

## Benefits

### Immediate (Week 1)

✅ **Simplified Commands**: `pytest --profile=openai` instead of manual env vars
✅ **Self-Documenting**: All profiles visible in `config/profiles/`
✅ **Fewer Errors**: Profile validates settings before running tests
✅ **Better UX**: Clear error messages if API key missing

### Medium-Term (Month 1)

✅ **Team Adoption**: Consistent testing practices across team
✅ **Easy Onboarding**: New developers understand immediately
✅ **CI/CD Ready**: Matrix tests across multiple models
✅ **Quality Assurance**: Test with production LLM regularly

### Long-Term (Quarter 1)

✅ **Extensibility**: Adding new LLM is just creating a profile file
✅ **Maintainability**: Model-specific settings in version control
✅ **Professionalism**: Production-quality test infrastructure
✅ **Debugging**: Reproduce issues with specific LLM configurations

---

## Success Metrics

### Technical

- [ ] Profile loader loads YAML and merges with config correctly
- [ ] `pytest --profile=openai` works without manual env var setup
- [ ] Clear error if API key missing: "OPENAI_API_KEY not found"
- [ ] All integration tests pass with both Ollama and OpenAI profiles
- [ ] <5 second overhead to load and validate profile

### Usability

- [ ] Developer can test with OpenAI in one command
- [ ] Profile files are self-documenting (good comments)
- [ ] Error messages are actionable ("Set OPENAI_API_KEY env var")
- [ ] Documentation explains profile creation clearly

### Quality

- [ ] ≥90% test coverage on profile loader
- [ ] Unit tests for profile validation edge cases
- [ ] Integration tests verify profile switching works
- [ ] Pre-commit checks pass with new code

---

## Risks & Mitigations

### Risk 1: API Key Security

**Risk**: Developers might accidentally commit API keys to profile files

**Mitigation**:
- Document clearly: "Never put API keys in profile files"
- Use `.gitignore` pattern for `*secret*.yaml`
- Profile loader only accepts env vars for sensitive data
- Pre-commit hook to scan for potential secrets

### Risk 2: Profile Drift

**Risk**: Profiles become outdated as LLM APIs change

**Mitigation**:
- Document profile format with schema comments
- Version profile format (e.g., `schema_version: 1`)
- Periodic review of profiles (quarterly)
- Validation checks for deprecated fields

### Risk 3: Test Inconsistency

**Risk**: Different models behave differently, tests may pass with one but fail with another

**Mitigation**:
- Document expected behaviors per profile
- Use pytest markers for model-specific tests
- CI/CD runs tests with default profile (Ollama) always
- Optional: Matrix test on PR, required on release

---

## Dependencies

### Prerequisites

- ✅ Existing LLM plugin architecture (supports multiple providers)
- ✅ Existing test infrastructure (pytest, conftest.py)
- ✅ Config system with merge capability
- ✅ Environment variable support for API keys

### External

- [ ] API keys for target LLMs (OpenAI, Anthropic, etc.)
- [ ] Access to test with real LLMs (or willingness to pay API costs)

### Internal

- [ ] Profile loader utility (new)
- [ ] Pytest plugin enhancement (modify existing)
- [ ] Profile files (new)
- [ ] Documentation updates (modify existing)

---

## Timeline

### Immediate (Today)

- Create planning documents ✅
- Review with stakeholders
- Approve implementation

### Phase 1 (4 hours - Day 1)

- Implement core infrastructure
- Create initial profiles (Ollama, OpenAI)
- Basic pytest integration

### Phase 2 (2 hours - Day 2)

- Write tests
- Documentation
- Validate with real LLMs

### Phase 3 (Optional - Day 3)

- CI/CD integration
- Additional profiles
- Advanced features

**Total Estimated Time**: 2-4 hours (core) + 2 hours (polish) = 4-6 hours

---

## Alternatives Considered

### Alternative 1: Environment Variables Only (Status Quo)

**Pros**: Already works, no code needed
**Cons**: Manual, error-prone, not scalable
**Decision**: Rejected - doesn't solve core problem

### Alternative 2: Bash Scripts per Model

**Pros**: Simple, quick to implement
**Cons**: Not portable (Windows), fragile, not integrated with pytest
**Decision**: Rejected - doesn't scale, not professional

### Alternative 3: Tox Environments

**Pros**: Standard Python tool for multiple test environments
**Cons**: Heavy-weight, requires separate tox.ini, less intuitive
**Decision**: Rejected - overkill for this use case

### Alternative 4: Pytest Parametrization

**Pros**: Built-in pytest feature
**Cons**: Requires code changes to every test, verbose
**Decision**: Rejected - too invasive to test code

### Alternative 5: Profile System (Chosen)

**Pros**: Clean, scalable, self-documenting, CI/CD friendly
**Cons**: Requires 4-6 hours implementation
**Decision**: **Selected** - Best ROI long-term

---

## Future Enhancements

### V1.1 (Post-MVP)

- Profile inheritance (base profile + overrides)
- Profile validation schema (JSON Schema)
- Interactive profile creator CLI: `obra test profile create`
- Profile performance comparison report

### V1.2 (Future)

- Remote profile repository (shared across team)
- Profile versioning and migration
- Automatic profile selection based on test type
- Integration with cost tracking (API usage per profile)

---

## Questions & Answers

### Q: Should profiles be in version control?

**A**: Yes, profiles should be committed (without secrets). They document supported LLM configurations and enable consistent testing across team.

### Q: How do we handle API keys?

**A**: Always via environment variables, never in profile files. Profile specifies which env vars are required, but doesn't contain the values.

### Q: Can profiles override agent configuration too?

**A**: Yes, profiles can override any config value (agent type, orchestration settings, etc.). Start simple (LLM only), expand as needed.

### Q: What if a test needs a specific LLM feature?

**A**: Use pytest markers: `@pytest.mark.requires_profile("openai")` to skip test if wrong profile active.

### Q: How do we test profile loading itself?

**A**: Unit tests with fixture profiles in `tests/fixtures/profiles/`. Mock file system for edge cases.

---

## Approval Checklist

- [ ] Architecture reviewed and approved
- [ ] Estimated effort acceptable (4-6 hours)
- [ ] No blocking dependencies
- [ ] Success metrics clear
- [ ] Risks understood and mitigations planned
- [ ] Timeline realistic
- [ ] Ready for implementation

---

**Status**: Ready for Implementation
**Next Step**: Review this plan, then implement using machine-optimized YAML plan

**See Also**:
- `docs/development/TEST_PROFILE_SYSTEM_IMPLEMENTATION.yaml` - Machine-optimized implementation plan
- `docs/development/TEST_PROFILE_SYSTEM_STARTUP_PROMPT.md` - Implementation startup prompt
