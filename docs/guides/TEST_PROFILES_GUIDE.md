# Test Profiles Guide

**Version**: 1.7.3
**Last Updated**: November 13, 2025

## Overview

Test profiles enable easy testing with multiple LLM providers without manual environment variable setup. Switch between Ollama, OpenAI Codex, Anthropic Claude, and other LLM providers with a single command.

**Problem Solved**: Testing with different LLMs required manual setup of multiple environment variables (`ORCHESTRATOR_LLM_TYPE`, `ORCHESTRATOR_LLM_MODEL`, API keys, etc.). This was error-prone, not scalable, and difficult to document.

**Solution**: Profile-based configuration where each LLM has a YAML file capturing all settings. One command switches LLMs: `pytest --profile=openai`

---

## Quick Start

### Test with Default Profile (Ollama)

```bash
# No profile flag = uses mock LLM for unit tests
pytest tests/unit/ -v

# Explicit Ollama profile (requires Ollama running locally)
pytest --profile=ollama tests/integration/ -v
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
# Run specific test with OpenAI
pytest --profile=openai tests/integration/test_llm_connectivity.py -v

# Run single test
pytest --profile=openai tests/integration/test_llm_connectivity.py::test_send_prompt -v
```

---

## Available Profiles

### ollama (Default)

**Location**: `config/profiles/test-ollama.yaml`

**Description**: Local Ollama with Qwen 2.5 Coder 32B (default for development)

**Requirements**:
- Ollama service running locally
- Qwen 2.5 Coder model downloaded
- No API keys needed

**Setup**:
```bash
# Install Ollama
curl https://ollama.ai/install.sh | sh

# Pull Qwen 2.5 Coder model
ollama pull qwen2.5-coder:32b

# Verify Ollama is running
curl http://localhost:11434/api/tags
```

**Usage**:
```bash
# Explicit Ollama profile
pytest --profile=ollama tests/integration/

# Ollama is default for integration tests
pytest tests/integration/
```

### openai (OpenAI Codex)

**Location**: `config/profiles/test-openai.yaml`

**Description**: OpenAI Codex (GPT-5) for testing with OpenAI API

**Requirements**:
- `OPENAI_API_KEY` environment variable
- OpenAI account with API access
- API credits (costs ~$0.10 per test run)

**Setup**:
```bash
# 1. Get API key from https://platform.openai.com/api-keys
# 2. Set environment variable
export OPENAI_API_KEY=sk-...

# 3. (Optional) Set organization ID
export OPENAI_ORG_ID=org-...

# 4. Verify setup
pytest --profile=openai tests/integration/test_llm_connectivity.py::test_connection -v
```

**Usage**:
```bash
# Run all integration tests with OpenAI
pytest --profile=openai tests/integration/ -v

# Run specific test
pytest --profile=openai tests/integration/test_llm_connectivity.py -v
```

**Cost Monitoring**:
- Monitor usage: https://platform.openai.com/usage
- Set usage limits in OpenAI dashboard
- Approximate cost: $0.10 per full test run

---

## Profile File Format

### Structure

Profiles are YAML files located in `config/profiles/test-{name}.yaml`:

```yaml
# Profile metadata
profile_name: example-profile
description: Example profile for XYZ LLM

# LLM configuration (required)
llm:
  type: llm-type           # Required: LLM provider type
  model: model-name        # Required: Model identifier
  timeout: 120             # Optional: Request timeout (seconds)
  temperature: 0.1         # Optional: Sampling temperature
  max_tokens: 8000         # Optional: Max tokens in response

# Environment variables
env_vars:
  required:                # Must be set before running tests
    - API_KEY_NAME
  optional:                # Can override defaults
    - OPTIONAL_VAR

# Test-specific configuration
test_config:
  skip_slow_tests: false
  max_test_duration: 300
```

### Required Fields

- `profile_name`: Profile identifier (string)
- `llm.type`: LLM provider type (e.g., `ollama`, `openai-codex`)
- `llm.model`: Model name (e.g., `qwen2.5-coder:32b`, `gpt-5-codex`)

### Optional Fields

- `llm.timeout`: Request timeout in seconds (default: 120)
- `llm.temperature`: Sampling temperature (default: 0.1)
- `llm.max_tokens`: Maximum tokens in response
- `llm.retry_attempts`: Number of retries on failure
- `env_vars.required`: List of required environment variables
- `env_vars.optional`: List of optional environment variables
- `test_config`: Test-specific settings

---

## Creating a Custom Profile

### Example: Anthropic Claude Profile

Create `config/profiles/test-anthropic.yaml`:

```yaml
# Anthropic Claude Profile
profile_name: anthropic-claude
description: Anthropic Claude for testing

llm:
  type: anthropic-claude
  model: claude-3-opus
  timeout: 120
  temperature: 0.1
  max_tokens: 8000

env_vars:
  required:
    - ANTHROPIC_API_KEY
  optional:
    - ANTHROPIC_BASE_URL

test_config:
  skip_slow_tests: false
  max_test_duration: 300

notes: |
  Requires ANTHROPIC_API_KEY environment variable.
  Get API key from: https://console.anthropic.com/

  Setup:
    export ANTHROPIC_API_KEY=sk-ant-...
    pytest --profile=anthropic tests/integration/
```

### Steps to Create Profile

1. **Create YAML file** in `config/profiles/test-{name}.yaml`
2. **Add required fields**: `profile_name`, `llm.type`, `llm.model`
3. **Specify environment variables**: List required API keys
4. **Document setup**: Add helpful notes for other developers
5. **Test the profile**: Run tests to verify it works
6. **Commit to repo**: Add profile to version control (without secrets!)

### Testing Your Profile

```bash
# 1. Set required environment variables
export API_KEY=...

# 2. Run a simple test
pytest --profile=your-profile tests/integration/test_llm_connectivity.py::test_connection -v

# 3. Run full integration tests
pytest --profile=your-profile tests/integration/ -v
```

---

## Usage Examples

### Unit Tests (No Profile)

Unit tests use mock LLM by default (no real API calls):

```bash
# All unit tests use mock LLM
pytest tests/unit/ -v

# Specific unit test
pytest tests/unit/test_profile_loader.py -v
```

### Integration Tests with Ollama

```bash
# Default profile (Ollama)
pytest tests/integration/ -v

# Explicit Ollama profile
pytest --profile=ollama tests/integration/ -v

# Single integration test
pytest --profile=ollama tests/integration/test_llm_connectivity.py -v
```

### Integration Tests with OpenAI

```bash
# Requires OPENAI_API_KEY
export OPENAI_API_KEY=sk-...

# Run all integration tests
pytest --profile=openai tests/integration/ -v

# Run specific test file
pytest --profile=openai tests/integration/test_nl_commands.py -v
```

### CI/CD Matrix Testing

Test across multiple LLM providers in CI/CD:

```yaml
# .github/workflows/test-matrix.yml
jobs:
  test:
    strategy:
      matrix:
        profile: [ollama, openai]
    steps:
      - name: Run tests with profile
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: pytest --profile=${{ matrix.profile }} tests/integration/
```

---

## Troubleshooting

### Profile Not Found

**Error**:
```
ProfileNotFoundError: Profile 'xyz' not found in config/profiles/.
Available profiles: ollama, openai
```

**Solution**:
1. Check profile name spelling
2. List available profiles: `ls config/profiles/test-*.yaml`
3. Create the profile if it doesn't exist

### Missing API Key

**Error**:
```
ProfileValidationError: Required environment variables not set: OPENAI_API_KEY

Set them with:
  export OPENAI_API_KEY=<value>
```

**Solution**:
```bash
# Set the required environment variable
export OPENAI_API_KEY=sk-...

# Verify it's set
echo $OPENAI_API_KEY

# Run tests again
pytest --profile=openai tests/integration/
```

### Invalid YAML Syntax

**Error**:
```
ProfileValidationError: Invalid YAML syntax: ...
```

**Solution**:
1. Open profile file in editor
2. Check for syntax errors (indentation, colons, quotes)
3. Validate YAML: https://www.yamllint.com/
4. Common issues:
   - Missing colons after keys
   - Inconsistent indentation (use 2 spaces)
   - Unquoted special characters

### LLM Connection Failed

**Error**:
```
ConnectionError: Failed to connect to LLM at http://localhost:11434
```

**Solution (Ollama)**:
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama if not running
systemctl start ollama  # Linux
brew services start ollama  # macOS

# Verify model is downloaded
ollama list
ollama pull qwen2.5-coder:32b  # If missing
```

**Solution (OpenAI)**:
```bash
# Verify API key is valid
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# Check for network connectivity
ping api.openai.com
```

### Tests Pass with Ollama but Fail with OpenAI

**Possible Causes**:
1. **Model capabilities differ**: OpenAI may have different context limits
2. **Response format differences**: Check prompt engineering
3. **Timeout too short**: Increase `llm.timeout` in profile
4. **Rate limiting**: OpenAI has rate limits, add delays or retry logic

**Solution**:
1. Check test assumptions about LLM capabilities
2. Use `@pytest.mark.skip` for LLM-specific tests
3. Adjust timeouts in profile
4. Review test logs for specific errors

---

## Best Practices

### Security

✅ **DO**:
- Store API keys in environment variables
- Add `*secret*.yaml` and `*private*.yaml` to `.gitignore`
- Use different API keys for dev/staging/prod
- Rotate API keys regularly
- Use secrets management (Vault, AWS Secrets Manager)

❌ **DON'T**:
- Commit API keys to version control
- Share API keys in chat/email
- Use production API keys for testing
- Store keys in profile files

### Testing Strategy

✅ **Recommended**:
- Unit tests: Always use mock LLM (fast, no cost)
- Integration tests: Use Ollama by default (local, no cost)
- Pre-release: Test with OpenAI/Anthropic (validate real LLM behavior)
- CI/CD: Ollama for all PRs, OpenAI for releases

❌ **Avoid**:
- Running all tests with paid APIs (expensive)
- Skipping integration tests (misses real LLM issues)
- Using only one LLM provider (limits validation)

### Profile Maintenance

✅ **Good Practices**:
- Document profile purpose in `description` field
- Add setup instructions in `notes` field
- Keep profiles up-to-date with model changes
- Test profiles after creating/modifying
- Version control all profiles (except secrets)

❌ **Bad Practices**:
- Hardcoding values that should be env vars
- Creating profiles without documentation
- Leaving outdated profiles in repo
- Copying profiles without understanding fields

---

## Advanced Usage

### Override Profile Values

Override profile values via environment variables:

```bash
# Override model in profile
export ORCHESTRATOR_LLM_MODEL=gpt-4-turbo
pytest --profile=openai tests/integration/

# Override timeout
export ORCHESTRATOR_LLM_TIMEOUT=180
pytest --profile=openai tests/integration/
```

### Profile-Specific Tests

Skip tests that require specific profiles:

```python
import pytest

@pytest.mark.skipif(
    pytest.config.getoption("--profile") != "openai",
    reason="Requires OpenAI profile"
)
def test_openai_specific_feature(test_config):
    # Test that only works with OpenAI
    pass
```

### Programmatic Profile Access

Access profile information in tests:

```python
def test_uses_correct_llm(profile_name, test_config):
    """Test adapts to active profile."""
    if profile_name == "openai":
        assert test_config.get('llm.type') == 'openai-codex'
        assert test_config.get('llm.model').startswith('gpt')
    elif profile_name == "ollama":
        assert test_config.get('llm.type') == 'ollama'
        assert 'qwen' in test_config.get('llm.model').lower()
```

---

## FAQ

### Q: How do I list all available profiles?

```bash
ls config/profiles/test-*.yaml | sed 's/.*test-//; s/.yaml//'
```

### Q: Can I create project-specific profiles?

Yes, create profiles in `config/profiles/` and commit them to the repo. Just ensure no secrets are included.

### Q: How do I test with multiple models from the same provider?

Create multiple profiles:
- `test-openai-gpt5.yaml` (GPT-5)
- `test-openai-gpt4.yaml` (GPT-4)
- `test-openai-mini.yaml` (GPT-4 Mini)

### Q: What if I want to use a profile for runtime (not tests)?

Test profiles are specifically for testing. For runtime configuration, use the main config system with profiles in `config/profiles/{name}.yaml` (without `test-` prefix).

### Q: How do I handle API rate limits?

1. Add retry logic to tests
2. Increase `llm.timeout` in profile
3. Add delays between tests: `time.sleep(1)` or use `pytest-xdist`
4. Use cheaper models for bulk testing

### Q: Can profiles override agent configuration?

Yes, profiles can override any config value, not just LLM settings:

```yaml
profile_name: custom
llm:
  type: openai-codex
  model: gpt-5-codex
agent:
  type: claude-code-local  # Override agent type
  timeout: 180
```

---

## See Also

- [Test Guidelines](../development/TEST_GUIDELINES.md) - Testing best practices
- [Configuration Guide](CONFIGURATION_PROFILES_GUIDE.md) - Runtime configuration profiles
- [LLM Management](../../CLAUDE.md#llm-management) - LLM setup and troubleshooting

---

**Last Updated**: November 13, 2025
**Version**: 1.7.3
**Author**: Claude Code
**Status**: Complete
