# Test Profile System - Implementation Startup Prompt

**Status**: Ready for Implementation
**Estimated Time**: 4-6 hours
**Prerequisites**: None (all dependencies met)

---

## What You're Building

A **profile-based test configuration system** that enables easy testing with multiple LLM providers without manual environment variable setup.

**Goal**: Enable `pytest --profile=openai` to automatically configure OpenAI Codex for testing.

---

## Quick Context

### Current State ❌
```bash
# Manual, error-prone
export ORCHESTRATOR_LLM_TYPE=openai-codex
export ORCHESTRATOR_LLM_MODEL=gpt-5-codex
export OPENAI_API_KEY=sk-...
export LLM_TIMEOUT=120

pytest tests/integration/ -v
```

### Desired State ✅
```bash
# One command, automatic configuration
pytest --profile=openai tests/integration/ -v
```

---

## Implementation Plan Overview

### Phase 1: Core Infrastructure (2 hours)

1. **Profile Loader Utility** (`src/testing/profile_loader.py`)
   - Load profile YAML files
   - Validate profile structure
   - Merge with base config
   - Check required environment variables

2. **Pytest Integration** (`tests/conftest.py`)
   - Add `--profile` CLI option to pytest
   - Modify `test_config` fixture to use profiles
   - Default to `ollama` profile

3. **Profile Files** (`config/profiles/`)
   - Create `test-ollama.yaml` (default)
   - Create `test-openai.yaml` (OpenAI Codex)

### Phase 2: Testing & Documentation (1 hour)

4. **Unit Tests** (`tests/unit/`)
   - Test profile loader (10 tests)
   - Test pytest integration (6 tests)

5. **Documentation**
   - Create `docs/guides/TEST_PROFILES_GUIDE.md`
   - Update `docs/development/TEST_GUIDELINES.md`

### Phase 3: Validation (1 hour)

6. **Integration Tests** (`tests/integration/`)
   - E2E profile system tests (5 tests)

7. **Manual Validation**
   - Test with Ollama profile
   - Test with OpenAI profile (if API key available)
   - Verify error messages

---

## Implementation Details

### Task 1: Profile Loader Utility

**File**: `src/testing/profile_loader.py` (200 lines)

**Functions to Implement**:

```python
def load_profile(profile_name: str, base_config: Config) -> Config:
    """Load profile and merge with base config.

    Args:
        profile_name: Profile name (e.g., 'ollama', 'openai')
        base_config: Base configuration to merge with

    Returns:
        Merged Config object

    Raises:
        ProfileNotFoundError: Profile file not found
        ProfileValidationError: Profile validation failed
    """
    # 1. Get profile path: config/profiles/test-{profile_name}.yaml
    # 2. Load YAML file
    # 3. Validate profile structure
    # 4. Check required env vars
    # 5. Merge with base config
    # 6. Return merged config

def validate_profile(profile_data: dict) -> None:
    """Validate profile structure.

    Checks:
    - Required fields: profile_name, llm.type, llm.model
    - LLM type is supported
    - Required env vars are set

    Raises:
        ProfileValidationError: Validation failed
    """
    pass

def merge_with_config(profile_data: dict, base_config: Config) -> Config:
    """Deep merge profile into config object."""
    # Profile values override base config values
    pass

def check_required_env_vars(required: List[str]) -> List[str]:
    """Check which required env vars are missing."""
    # Return list of missing env var names
    pass

def get_profile_path(profile_name: str) -> Path:
    """Get path to profile file."""
    # Returns: config/profiles/test-{profile_name}.yaml
    pass
```

**Exceptions**:
```python
class ProfileNotFoundError(Exception):
    """Profile file not found."""
    pass

class ProfileValidationError(Exception):
    """Profile validation failed."""
    pass
```

**Error Messages** (must be helpful):
- Profile not found: "Profile 'xyz' not found. Available: ollama, openai"
- Missing API key: "OPENAI_API_KEY environment variable required. Set it with: export OPENAI_API_KEY=sk-..."
- Invalid YAML: "Profile YAML invalid: {reason}"

---

### Task 2: Pytest Integration

**File**: `tests/conftest.py` (modify existing)

**Add CLI Option**:
```python
def pytest_addoption(parser):
    """Add --profile option to pytest."""
    parser.addoption(
        "--profile",
        action="store",
        default="ollama",
        help="Test profile to use (ollama, openai, etc.)"
    )
```

**Modify test_config Fixture**:
```python
@pytest.fixture
def test_config(request):
    """Load config, optionally from profile."""
    profile_name = request.config.getoption("--profile")
    base_config = Config.load()

    if profile_name:
        from src.testing.profile_loader import load_profile
        try:
            return load_profile(profile_name, base_config)
        except ProfileNotFoundError as e:
            pytest.exit(f"Profile error: {e}")
        except ProfileValidationError as e:
            pytest.exit(f"Profile validation error: {e}")

    return base_config
```

**Add profile_name Fixture**:
```python
@pytest.fixture
def profile_name(request):
    """Get active profile name."""
    return request.config.getoption("--profile")
```

---

### Task 3: Profile Files

**File**: `config/profiles/test-ollama.yaml`

```yaml
# Ollama Local LLM Profile (Default)
# Qwen 2.5 Coder 32B on local Ollama instance

profile_name: ollama
description: Local Ollama with Qwen 2.5 Coder 32B (default for development)

llm:
  type: ollama
  model: qwen2.5-coder:32b
  base_url: http://localhost:11434
  timeout: 120
  temperature: 0.1

env_vars:
  required: []  # No API keys needed
  optional:
    - OLLAMA_HOST  # Override default host if needed

test_config:
  skip_slow_tests: false
  max_test_duration: 300

notes: |
  Default profile for local development and CI/CD.
  Requires Ollama service running locally or at base_url.

  Installation:
    curl https://ollama.ai/install.sh | sh
    ollama pull qwen2.5-coder:32b

  Verify:
    curl http://localhost:11434/api/tags
```

**File**: `config/profiles/test-openai.yaml`

```yaml
# OpenAI Codex Profile
# GPT-5 Codex for testing with OpenAI API

profile_name: openai-codex
description: OpenAI Codex (GPT-5) for testing

llm:
  type: openai-codex
  model: gpt-5-codex
  timeout: 120
  temperature: 0.1
  max_tokens: 8000
  retry_attempts: 3

env_vars:
  required:
    - OPENAI_API_KEY  # Get from https://platform.openai.com/api-keys
  optional:
    - OPENAI_ORG_ID      # Organization ID (if applicable)
    - OPENAI_BASE_URL    # Override API endpoint

test_config:
  skip_slow_tests: false
  max_test_duration: 300

notes: |
  Requires OPENAI_API_KEY environment variable.

  Setup:
    1. Get API key: https://platform.openai.com/api-keys
    2. Export key: export OPENAI_API_KEY=sk-...
    3. Run tests: pytest --profile=openai tests/integration/

  Cost:
    - GPT-5 Codex: ~$0.10 per test run
    - Monitor usage: https://platform.openai.com/usage
```

---

### Task 4: Unit Tests

**File**: `tests/unit/test_profile_loader.py` (10 tests)

```python
def test_load_valid_profile_ollama(tmpdir):
    """Test loading valid Ollama profile."""
    # Create profile file in tmpdir
    # Load profile
    # Assert config has Ollama settings

def test_load_profile_not_found():
    """Test error when profile not found."""
    with pytest.raises(ProfileNotFoundError, match="Profile 'nonexistent' not found"):
        load_profile("nonexistent", Config.load())

def test_validate_profile_success():
    """Test profile validation succeeds."""
    profile_data = {
        'profile_name': 'test',
        'llm': {'type': 'ollama', 'model': 'qwen2.5-coder:32b'},
        'env_vars': {'required': [], 'optional': []}
    }
    validate_profile(profile_data)  # Should not raise

def test_validate_profile_missing_field():
    """Test validation fails for missing field."""
    profile_data = {'profile_name': 'test'}  # Missing llm
    with pytest.raises(ProfileValidationError, match="Missing required field: llm"):
        validate_profile(profile_data)

def test_check_required_env_vars_all_set(monkeypatch):
    """Test env var check when all set."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    missing = check_required_env_vars(["OPENAI_API_KEY"])
    assert missing == []

def test_check_required_env_vars_missing():
    """Test env var check when missing."""
    missing = check_required_env_vars(["NONEXISTENT_VAR"])
    assert missing == ["NONEXISTENT_VAR"]

# ... 4 more tests (see implementation plan YAML)
```

**File**: `tests/unit/test_pytest_profile_integration.py` (6 tests)

```python
def test_default_profile_ollama(pytestconfig):
    """Test default profile is Ollama."""
    # No --profile flag
    profile = pytestconfig.getoption("--profile")
    assert profile == "ollama"

def test_profile_flag_openai(pytestconfig):
    """Test --profile=openai flag."""
    # Run with: pytest --profile=openai
    # This test would need to be parametrized or use testdir fixture

# ... 4 more tests (see implementation plan YAML)
```

---

### Task 5: Integration Tests

**File**: `tests/integration/test_profile_system_e2e.py` (5 tests)

```python
def test_profile_ollama_loads_and_connects(test_config):
    """Test Ollama profile loads and connects."""
    # Assumes --profile=ollama (default)
    assert test_config.get('llm.type') == 'ollama'

    # Try to connect to LLM
    from src.llm.llm_plugin_manager import LLMPluginManager
    llm = LLMPluginManager.create_llm_plugin(test_config)

    # Send test prompt
    response = llm.send_prompt("Hello, test")
    assert response is not None

@pytest.mark.requires_api_key
def test_profile_openai_loads_with_api_key(test_config):
    """Test OpenAI profile works with API key."""
    # Run with: pytest --profile=openai
    # Skip if OPENAI_API_KEY not set
    if not os.getenv('OPENAI_API_KEY'):
        pytest.skip("OPENAI_API_KEY not set")

    assert test_config.get('llm.type') == 'openai-codex'

    # Try to connect to LLM
    from src.llm.llm_plugin_manager import LLMPluginManager
    llm = LLMPluginManager.create_llm_plugin(test_config)

    # Send test prompt
    response = llm.send_prompt("Hello, test")
    assert response is not None

# ... 3 more tests (see implementation plan YAML)
```

---

### Task 6: Documentation

**File**: `docs/guides/TEST_PROFILES_GUIDE.md`

**Contents**:
1. Overview of profile system
2. Quick start
3. Available profiles
4. Using profiles
5. Creating custom profiles
6. Troubleshooting

**Example Section - Quick Start**:
```markdown
## Quick Start

### Test with Default Profile (Ollama)
```bash
pytest tests/integration/ -v
```

### Test with OpenAI Codex
```bash
# 1. Set API key
export OPENAI_API_KEY=sk-...

# 2. Run tests
pytest --profile=openai tests/integration/ -v
```

### Test Specific File
```bash
pytest --profile=openai tests/integration/test_llm_connectivity.py -v
```
```

---

## Validation Checklist

### Functional Tests
- [ ] `pytest --profile=ollama` works
- [ ] `pytest --profile=openai` works (with API key)
- [ ] `pytest` (no flag) defaults to Ollama
- [ ] `pytest --profile=invalid` shows helpful error
- [ ] Missing API key shows clear error with setup instructions

### Quality Tests
- [ ] All unit tests pass (16 tests)
- [ ] All integration tests pass (5 tests)
- [ ] Test coverage ≥90% on profile loader
- [ ] No secrets committed to repo

### Usability Tests
- [ ] Documentation is clear
- [ ] Error messages are actionable
- [ ] Profile files are self-documenting
- [ ] Creating new profile takes <10 minutes

---

## Common Pitfalls to Avoid

❌ **Don't commit API keys** - Always use environment variables
❌ **Don't hardcode profile paths** - Use Path and make it configurable
❌ **Don't silently fall back** - Explicit errors are better than silent failures
❌ **Don't skip validation** - Catch errors early with clear messages
❌ **Don't forget .gitignore** - Add pattern for *secret*.yaml files

---

## Success Criteria

### Must Have
- ✅ `pytest --profile=openai` loads OpenAI config automatically
- ✅ Clear error if profile not found or API key missing
- ✅ All tests pass with both Ollama and OpenAI profiles
- ✅ Documentation explains usage clearly

### Nice to Have
- ✅ Profile loading takes <100ms
- ✅ Error messages suggest solutions
- ✅ CI/CD matrix testing across profiles
- ✅ Profile inheritance (future enhancement)

---

## After Implementation

### Test It
```bash
# Test with default
pytest tests/integration/ -v

# Test with OpenAI (if key available)
export OPENAI_API_KEY=sk-...
pytest --profile=openai tests/integration/ -v

# Test error handling
pytest --profile=invalid tests/integration/
# Should show: ProfileNotFoundError with helpful message
```

### Update CHANGELOG
```markdown
## [1.7.3] - 2025-11-13

### Added
- **Test Profile System**: Easy testing with multiple LLM providers
  - `pytest --profile=openai` for OpenAI Codex testing
  - Profile files in config/profiles/ (ollama, openai)
  - Profile loader utility with validation
  - 21 new tests (16 unit + 5 integration)
  - Comprehensive documentation
```

### Commit
```bash
git add -A
git commit -m "feat: Add test profile system for multi-LLM testing

Enables easy testing with multiple LLM providers without manual env var setup.

Features:
- Profile-based configuration (config/profiles/)
- pytest --profile=openai CLI flag
- Profile loader with validation
- Clear error messages for missing API keys
- 21 new tests (16 unit + 5 integration)

Usage:
  pytest --profile=openai tests/integration/

Benefits:
- One command to switch LLMs
- Self-documenting profiles
- CI/CD matrix testing ready
- Team-friendly"
```

---

## Ready to Start?

**Order of Implementation**:
1. Profile loader utility (45 min)
2. Pytest integration (45 min)
3. Profile files (30 min)
4. Unit tests (30 min)
5. Documentation (30 min)
6. Integration tests (30 min)
7. Validation (30 min)

**Total**: 4-6 hours

**Start with Task 1**: Create `src/testing/profile_loader.py`

Good luck! 🚀
