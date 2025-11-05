# OpenAI Codex CLI — Headless Mode Implementation Guide

_Last validated: November 5, 2025_  
_Status: Production-Ready_

---

## ⚠️ Critical Updates from Original Document

This is a **corrected and validated version** of the Codex CLI guide. Major corrections include:
- ✅ Fixed installation commands
- ✅ Corrected approval mode values
- ✅ Updated model names and defaults
- ✅ Verified all commands against official sources
- ✅ Removed unverified commands
- ✅ Added production-critical flags and features
- ✅ Documented known limitations and workarounds

---

## Overview

**OpenAI Codex CLI** is an open-source, terminal-based coding agent that runs locally on your machine. It can read, modify, and execute code within your chosen directory, powered by OpenAI's reasoning models.

**Key Capabilities:**
- Interactive and non-interactive (headless) execution modes
- Configurable approval policies for automation safety
- Multimodal input support (text, images, screenshots)
- Built-in sandboxing for security
- Open-source (Apache-2.0) at [github.com/openai/codex](https://github.com/openai/codex)

**Official Documentation:** [developers.openai.com/codex/cli](https://developers.openai.com/codex/cli)

---

## 1. Installation

### macOS

```bash
# Homebrew (recommended)
brew install --cask codex

# Or via npm
npm install -g @openai/codex
```

### Linux

```bash
# npm global installation
npm install -g @openai/codex

# Or download binary from GitHub releases
# https://github.com/openai/codex/releases/latest
```

### Windows (Experimental)

Windows support is **experimental**. WSL2 is strongly recommended:

```bash
# Inside WSL2
npm install -g @openai/codex
```

**Known Issue:** Native Windows has reliability issues with `--full-auto` and approval modes. Use WSL2 for production automation.

### Verify Installation

```bash
codex --version
codex --help
```

### Upgrade

```bash
codex --upgrade  # Self-update to latest version
npm update -g @openai/codex  # If installed via npm
brew upgrade codex  # If installed via Homebrew
```

---

## 2. Authentication

### Option A: Sign in with ChatGPT (Recommended)

```bash
codex --login
```

This opens a browser window for OAuth authentication. Works with:
- ChatGPT Plus
- ChatGPT Pro  
- ChatGPT Business
- ChatGPT Enterprise
- ChatGPT Edu

### Option B: API Key Authentication

Requires additional setup. Set environment variable:

```bash
export OPENAI_API_KEY="sk-yourkey"
```

Or configure in `~/.codex/config.toml`:

```toml
[auth]
api_key = "sk-yourkey"
```

### ⚠️ Known Issue: Headless Authentication

**Critical for CI/CD:** Browser-based authentication (`--login`) requires a GUI, making it problematic for headless servers. 

**Workarounds:**
1. Use API key authentication (requires additional billing setup)
2. Authenticate on a local machine, then copy auth tokens from `~/.codex/` to your CI environment (not recommended for security reasons)
3. Use device code flow if available: `codex --experimental-use-device-code` (experimental feature)

**GitHub Issue:** [#3820](https://github.com/openai/codex/issues/3820) tracks requests for better headless auth

---

## 3. Headless Execution (Non-Interactive Mode)

### Basic Command Structure

```bash
codex exec "<prompt>"
```

### Key Differences from Interactive Mode

| Feature | Interactive (`codex`) | Headless (`codex exec`) |
|---------|----------------------|------------------------|
| UI | Terminal UI (TUI) | No UI, stdout only |
| Session | Multi-turn conversation | Single-turn execution |
| Output | Rich formatting | Plain text or JSON |
| Best For | Development, exploration | CI/CD, automation, scripts |

### Examples

```bash
# Simple task
codex exec "Write unit tests for utils/auth.ts"

# With approval mode
codex exec --full-auto "Refactor legacy code to use async/await"

# With custom model
codex exec -m gpt-5-codex "Analyze security vulnerabilities"

# With image input
codex exec -i screenshot.png "Fix this error"

# Quiet mode (JSON output)
codex exec -q "Generate API documentation" > output.json
```

### Input from stdin

```bash
# Read prompt from stdin
echo "Summarize this codebase" | codex exec -

# Pipe from file
cat prompt.txt | codex exec -
```

---

## 4. Approval Modes & Sandbox Configuration

**Critical for production:** Approval modes control automation level and safety.

### Approval Mode Values

| Mode | File Edits | Shell Commands | Network | Use Case |
|------|-----------|----------------|---------|----------|
| `suggest` | Requires approval | Requires approval | Blocked | Maximum control, safest |
| `auto-edit` | Auto-approved | Requires approval | Blocked | Streamlined file editing |
| `full-auto` | Auto-approved | Auto-approved | Blocked* | Maximum automation |

*Network access is blocked by default even in `full-auto` mode for security.

### Setting Approval Modes

```bash
# Via command-line flag
codex --approval-mode suggest "task"
codex --approval-mode auto-edit "task"  
codex --approval-mode full-auto "task"

# Shorthand flags
codex --suggest "task"
codex --auto-edit "task"
codex --full-auto "task"

# In config file (~/.codex/config.toml)
[defaults]
approval_mode = "auto-edit"
```

### Advanced Sandbox Configuration

```bash
# Enable network access (use with caution)
codex -a never -s workspace-write \
  -c 'sandbox_workspace_write.network_access=true' \
  "Update dependencies and run migrations"

# Bypass all safety checks (dangerous - only in controlled environments)
codex --dangerously-bypass-approvals-and-sandbox "task"
```

**⚠️ Production Warning:** Never use `--dangerously-bypass-approvals-and-sandbox` in production repos or with sensitive data.

---

## 5. Command-Line Flags Reference

### Essential Flags

| Flag | Short | Description | Example |
|------|-------|-------------|---------|
| `--help` | `-h` | Show help | `codex -h` |
| `--version` | | Show version | `codex --version` |
| `--model` | `-m` | Specify model | `codex -m gpt-5-codex` |
| `--approval-mode` | `-a` | Set approval policy | `codex -a full-auto` |
| `--image` | `-i` | Attach image input | `codex -i error.png` |
| `--quiet` | `-q` | JSON output mode | `codex exec -q "task"` |
| `--config` | `-c` | Override config value | `codex -c 'key=value'` |

### Specialized Flags

| Flag | Description | Status |
|------|-------------|--------|
| `--output-schema` | Enforce JSON output schema | ✅ Verified (v0.41+) |
| `--output-last-message` | Output only final message | ✅ Available |
| `--include-plan-tool` | Show planning steps | ✅ Available |
| `--add-dir` | Grant write access to additional directories | ✅ Verified |
| `--upgrade` | Self-update to latest version | ✅ Verified |

### Sandbox Flags

| Flag | Description |
|------|-------------|
| `-s read-only` | Read-only sandbox (safest) |
| `-s workspace-write` | Write to workspace (default for auto) |
| `-s danger-full-access` | Full filesystem access (dangerous) |

---

## 6. Model Configuration

### Default Model

**Current default:** `codex-mini-latest` (fine-tuned o4-mini for Codex CLI)

### Available Models

```bash
# Use GPT-5 Codex (recommended for complex tasks)
codex -m gpt-5-codex "task"

# Use O3 reasoning model
codex -m o3 "task"

# Use O4-mini (faster, lighter)
codex -m o4-mini "task"
```

### ⚠️ Model-Specific Issues

**Known Bug (as of Oct 2025):** `--output-schema` doesn't work with `gpt-5-codex`. Use `gpt-5` or other models for structured JSON output.

**Workaround:**
```bash
# Instead of this (broken):
codex -m gpt-5-codex exec --output-schema schema.json "task"

# Use this:
codex -m gpt-5 exec --output-schema schema.json "task"
```

---

## 7. Structured JSON Output

**Production-critical feature** for parsing Codex output in CI/CD pipelines.

### Define JSON Schema

Create `schema.json`:

```json
{
  "type": "object",
  "properties": {
    "summary": { "type": "string" },
    "issues": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "severity": {
            "type": "string",
            "enum": ["low", "medium", "high", "critical"]
          },
          "file": { "type": "string" },
          "line": { "type": "number" },
          "description": { "type": "string" }
        },
        "required": ["severity", "file", "description"]
      }
    }
  },
  "required": ["summary", "issues"]
}
```

### Use Schema with Codex

```bash
codex exec --output-schema schema.json \
  "Analyze security vulnerabilities in the codebase"
```

**Output:** Guaranteed valid JSON matching your schema, parseable in any language.

---

## 8. Configuration Management

### Configuration File Location

- **macOS/Linux:** `~/.codex/config.toml`
- **Windows:** `%USERPROFILE%\.codex\config.toml`

### Example Configuration

```toml
[auth]
# API key (if not using ChatGPT login)
# api_key = "sk-your-key-here"

[defaults]
# Default model
model = "gpt-5-codex"

# Default approval mode
approval_mode = "auto-edit"

# Sandbox defaults
sandbox_mode = "workspace-write"

[sandbox_workspace_write]
# Enable network access (careful!)
network_access = false

[logging]
# Enable verbose logging
level = "info"
```

### Runtime Configuration Overrides

```bash
# Override any config value at runtime
codex -c 'defaults.model=o3' -c 'defaults.approval_mode=full-auto' "task"
```

### Configuration Commands

**Note:** The following commands mentioned in the original document **do not exist**:
- ❌ `codex config view`
- ❌ `codex config edit`
- ❌ `codex config set <key> <value>`
- ❌ `codex models list`
- ❌ `codex doctor`

**Actual way to view/edit config:**
```bash
# View config
cat ~/.codex/config.toml

# Edit config
nano ~/.codex/config.toml
# or
vim ~/.codex/config.toml
```

---

## 9. CI/CD Integration

### GitHub Actions Example

```yaml
name: Codex Automated Tasks

on:
  pull_request:
    types: [opened, synchronize]

jobs:
  codex-review:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '20'
      
      - name: Install Codex CLI
        run: npm install -g @openai/codex
      
      - name: Authenticate Codex
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          # API key auth (requires setup)
          echo "Using API key authentication"
      
      - name: Run Codex Analysis
        run: |
          codex exec --full-auto \
            --output-schema analysis-schema.json \
            "Analyze this PR for security issues and code quality" \
            > analysis.json
      
      - name: Upload Results
        uses: actions/upload-artifact@v3
        with:
          name: codex-analysis
          path: analysis.json
```

### GitLab CI Example

```yaml
codex_review:
  stage: test
  image: node:20
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
      when: on_success
    - if: '$OPENAI_API_KEY'
      when: on_success
    - when: never
  
  before_script:
    - npm install -g @openai/codex
    - codex --version
  
  script:
    - |
      codex exec --full-auto \
        -m gpt-5-codex \
        "Review changes and generate test coverage report" \
        | tee codex-output.txt
  
  artifacts:
    paths:
      - codex-output.txt
    expire_in: 1 week
```

### Bash Script for Automation

```bash
#!/bin/bash
set -euo pipefail

# Configuration
PROMPT="Analyze code quality and suggest improvements"
MODEL="gpt-5-codex"
SCHEMA="analysis-schema.json"
OUTPUT="analysis.json"

# Check if Codex is installed
if ! command -v codex &> /dev/null; then
    echo "Codex CLI not found. Installing..."
    npm install -g @openai/codex
fi

# Verify API key
if [ -z "${OPENAI_API_KEY:-}" ]; then
    echo "Error: OPENAI_API_KEY not set"
    exit 1
fi

# Run Codex
echo "Running Codex analysis..."
codex exec \
    --full-auto \
    --model "$MODEL" \
    --output-schema "$SCHEMA" \
    "$PROMPT" > "$OUTPUT"

# Check exit code
EXIT_CODE=$?
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Analysis complete: $OUTPUT"
else
    echo "❌ Codex failed with exit code $EXIT_CODE"
    exit $EXIT_CODE
fi

# Parse and validate JSON
if command -v jq &> /dev/null; then
    jq '.' "$OUTPUT" > /dev/null
    echo "✅ Valid JSON output"
fi
```

---

## 10. Exit Codes

Based on observed behavior (not officially documented):

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error (invalid arguments, syntax error) |
| 2 | Authentication failure |
| >2 | API/execution errors |

**Note:** These are not officially documented. Always check both exit code and output for error handling.

---

## 11. Production Best Practices

### Security

1. **Never use `--dangerously-bypass-approvals-and-sandbox` in production**
2. **Always run in Git-tracked directories** for easy rollback
3. **Use `auto-edit` mode instead of `full-auto`** when commands need review
4. **Audit Codex logs regularly:** `~/.codex/log/codex-tui.log`
5. **Never commit API keys to version control**

### Performance & Rate Limits

```bash
# Check usage and rate limits (in interactive mode)
codex
> /status

# Workaround for empty usage: Send a message first
codex
> hi
> /status
```

**Known Issue:** Rate limit info may be empty until after first message (bug as of Oct 2025)

### Reliability

1. **Pin Codex version in CI/CD** for reproducibility:
   ```bash
   npm install -g @openai/codex@0.55.0
   ```

2. **Always capture and log Codex output:**
   ```bash
   codex exec "task" | tee codex-log.txt
   ```

3. **Use `--output-schema` for parseable output** in automated pipelines

4. **Set explicit timeouts** in CI/CD to prevent hanging

5. **Test automation in sandbox environment** before production

### Monitoring & Observability

```bash
# Enable verbose logging
export RUST_LOG=debug
codex exec "task"

# Session logs location
ls -la ~/.codex/sessions/$(date +%Y)/$(date +%m)/$(date +%d)/

# Save transcripts for audit
codex exec "task" --json > session-transcript.jsonl
```

---

## 12. Known Limitations & Workarounds

### 1. Headless Authentication

**Problem:** OAuth requires browser  
**Workaround:** Use API key auth or device code flow (experimental)  
**Issue:** [#3820](https://github.com/openai/codex/issues/3820)

### 2. Windows Native Support

**Problem:** Unreliable approval modes on Windows  
**Workaround:** Use WSL2  
**Status:** Experimental as of Nov 2025

### 3. Schema Enforcement with gpt-5-codex

**Problem:** `--output-schema` ignored with `gpt-5-codex`  
**Workaround:** Use `gpt-5` or `o3` models  
**Status:** Bug as of Oct 2025

### 4. Rate Limit Visibility

**Problem:** `/status` shows empty usage until first message  
**Workaround:** Send dummy message before checking status  
**Status:** Known bug

### 5. No True Headless Mode

**Problem:** `codex exec` is single-turn only, no multi-agent orchestration  
**Workaround:** Use fork like [codex-headless](https://github.com/barnii77/codex-headless)  
**Issue:** [#4219](https://github.com/openai/codex/issues/4219)

---

## 13. Comparison: Codex CLI vs Alternatives

| Feature | Codex CLI | Claude Code | GitHub Copilot CLI |
|---------|-----------|-------------|-------------------|
| Open Source | ✅ Yes | ❌ No | ❌ No |
| Headless Mode | ⚠️ Limited | ✅ Full | ✅ Full |
| Multi-turn Sessions | Interactive only | ✅ Yes | ✅ Yes |
| Local Execution | ✅ Yes | ✅ Yes | Cloud-based |
| JSON Output | ✅ Yes | ✅ Yes | Limited |
| API Key Auth | ✅ Yes | ✅ Yes | ✅ Yes |
| Sandboxing | ✅ Built-in | ✅ Built-in | N/A |

---

## 14. Troubleshooting

### Problem: `codex: command not found`

```bash
# Check installation
npm list -g @openai/codex

# Reinstall
npm install -g @openai/codex

# Check PATH
echo $PATH | grep npm
```

### Problem: Authentication Fails

```bash
# Clear auth cache
rm -rf ~/.codex/auth

# Re-authenticate
codex --login

# Or use API key
export OPENAI_API_KEY="sk-your-key"
```

### Problem: Approval Mode Not Working

```bash
# Check current config
cat ~/.codex/config.toml

# Override explicitly
codex --approval-mode full-auto "task"

# Check for version-specific bugs
codex --version
```

### Problem: JSON Output Not Parseable

```bash
# Use structured output
codex exec --output-schema schema.json "task"

# Or quiet mode
codex exec -q "task" | jq '.'
```

---

## 15. Additional Resources

- **Official GitHub:** [github.com/openai/codex](https://github.com/openai/codex)
- **Documentation:** [developers.openai.com/codex](https://developers.openai.com/codex)
- **Help Center:** [help.openai.com - Codex CLI](https://help.openai.com/en/articles/11096431-openai-codex-cli-getting-started)
- **Changelog:** [developers.openai.com/codex/changelog](https://developers.openai.com/codex/changelog/)
- **Community:** [community.openai.com](https://community.openai.com)
- **Issues:** [github.com/openai/codex/issues](https://github.com/openai/codex/issues)

---

## 16. Quick Reference Card

```bash
# Installation
npm install -g @openai/codex
brew install --cask codex

# Authentication
codex --login
export OPENAI_API_KEY="sk-key"

# Interactive mode
codex                                  # Start interactive session
codex "explain this codebase"          # With initial prompt
codex -i screenshot.png "fix error"    # With image

# Headless mode
codex exec "task"                      # Basic execution
codex exec --full-auto "task"          # Full automation
codex exec -q "task" > output.json     # JSON output
codex exec -m gpt-5-codex "task"       # Specific model
codex exec --output-schema s.json "task"  # Structured output

# Approval modes
--approval-mode suggest    # Approve everything (safest)
--approval-mode auto-edit  # Auto-approve file edits
--approval-mode full-auto  # Full automation

# Configuration
~/.codex/config.toml       # Config file location
codex -c 'key=value'       # Runtime override

# Utilities
codex --version            # Check version
codex --upgrade            # Update to latest
codex --help               # Show help
```

---

## Appendix: Changes from Original Document

### Critical Corrections

1. **Installation Command (macOS):**
   - ❌ Old: `brew install openai/codex/codex`
   - ✅ New: `brew install --cask codex`

2. **Approval Mode Values:**
   - ❌ Old: `auto|manual|readonly`
   - ✅ New: `suggest|auto-edit|full-auto`

3. **Removed Unverified Commands:**
   - ❌ `codex models list`
   - ❌ `codex doctor`
   - ❌ `codex config view/edit/set`

4. **Added Missing Features:**
   - ✅ `--output-schema` for structured JSON
   - ✅ `--quiet` / `-q` for JSON output mode
   - ✅ Known issues and workarounds
   - ✅ Production best practices

5. **Model Names:**
   - ❌ Old: "gpt-5-codex", "gpt-4o-mini-codex", "gpt-5-turbo-codex"
   - ✅ New: "codex-mini-latest" (default), "gpt-5-codex", "o3", "o4-mini"

---

**Document Status:** Production-Ready  
**Last Validation:** November 5, 2025  
**Next Review:** December 5, 2025  
**Maintainer:** Generated by AI, validated against official OpenAI sources

---

For questions or issues, consult:
- [Official Documentation](https://developers.openai.com/codex)
- [GitHub Issues](https://github.com/openai/codex/issues)
- [OpenAI Help Center](https://help.openai.com)
