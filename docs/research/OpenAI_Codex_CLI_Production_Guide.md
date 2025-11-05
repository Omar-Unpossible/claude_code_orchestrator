# OpenAI Codex CLI: Production Headless Mode Guide

**Version:** 1.0  
**Last Updated:** November 5, 2025  
**Status:** Production-Ready

---

## Overview

OpenAI Codex CLI is an open-source terminal-based coding agent that runs locally on your machine. It provides both interactive and headless execution modes, with built-in sandboxing and configurable approval policies.

**Key Features:**
- Interactive and non-interactive (headless) execution
- Multimodal input (text, images, screenshots)
- Configurable approval policies for automation safety
- Built-in sandboxing (Seatbelt on macOS, Landlock on Linux)
- Structured JSON output for CI/CD integration
- Open-source under Apache-2.0 license

**Official Resources:**
- Repository: [github.com/openai/codex](https://github.com/openai/codex)
- Documentation: [developers.openai.com/codex](https://developers.openai.com/codex)
- Changelog: [developers.openai.com/codex/changelog](https://developers.openai.com/codex/changelog)

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
npm install -g @openai/codex
```

### Windows

Windows support is experimental. **Use WSL2 for production:**

```bash
# Inside WSL2
npm install -g @openai/codex
```

### Verify Installation

```bash
codex --version
codex --help
```

### Keeping Updated

```bash
codex --upgrade              # Self-update
npm update -g @openai/codex  # If installed via npm
```

---

## 2. Authentication

### ChatGPT Account (Recommended)

```bash
codex --login
```

Opens browser for OAuth. Works with ChatGPT Plus, Pro, Business, Enterprise, and Edu plans.

### API Key Authentication

For CI/CD environments where browser auth isn't feasible:

```bash
export OPENAI_API_KEY="sk-your-api-key"
```

Or in `~/.codex/config.toml`:

```toml
[auth]
api_key = "sk-your-api-key"
```

**Note:** API key usage requires separate billing setup with OpenAI.

### Headless/CI Authentication

For environments without browser access:

1. **API Key Method** (recommended for CI/CD)
2. **Device Code Flow** (experimental): `codex --experimental-use-device-code`
3. **Pre-authenticated Token** (copy `~/.codex/` from authenticated machine - not recommended)

---

## 3. Execution Modes

### Interactive Mode

```bash
# Start interactive session
codex

# With initial prompt
codex "explain this codebase"

# With image input
codex -i screenshot.png "fix this error"
```

### Headless Mode (Non-Interactive)

```bash
# Basic headless execution
codex exec "write unit tests for utils/auth.ts"

# With approval mode
codex exec --full-auto "refactor to use async/await"

# With custom model
codex exec -m gpt-5-codex "analyze security vulnerabilities"

# With structured JSON output
codex exec --output-schema schema.json "analyze code quality"

# Quiet mode (JSON events)
codex exec -q "generate documentation" > output.json
```

### Input from stdin

```bash
# Pipe prompt
echo "summarize codebase" | codex exec -

# From file
cat prompt.txt | codex exec -
```

---

## 4. Approval Modes & Automation

Approval modes control the level of automation and safety:

| Mode | File Edits | Shell Commands | Network | Best For |
|------|-----------|----------------|---------|----------|
| `suggest` | Requires approval | Requires approval | Blocked | Maximum safety, learning |
| `auto-edit` | Auto-approved | Requires approval | Blocked | Streamlined file ops |
| `full-auto` | Auto-approved | Auto-approved | Blocked* | Full automation in safe environments |

*Network is blocked by default even in `full-auto` mode.

### Setting Approval Modes

```bash
# Via flag
codex --approval-mode suggest "task"
codex --approval-mode auto-edit "task"
codex --approval-mode full-auto "task"

# Shorthand
codex --suggest "task"
codex --auto-edit "task"
codex --full-auto "task"

# In config file
[defaults]
approval_mode = "auto-edit"
```

### Advanced Sandbox Configuration

```bash
# Enable network access (use cautiously)
codex -a full-auto -s workspace-write \
  -c 'sandbox_workspace_write.network_access=true' \
  "update dependencies"

# Grant write access to additional directory
codex --add-dir /path/to/dir "task"

# Full bypass (dangerous - only in isolated environments)
codex --dangerously-bypass-approvals-and-sandbox "task"
```

**Production Warning:** Never use `--dangerously-bypass-approvals-and-sandbox` on production repositories or with sensitive data.

---

## 5. Command-Line Flags

### Essential Flags

| Flag | Short | Description | Example |
|------|-------|-------------|---------|
| `--help` | `-h` | Show help | `codex -h` |
| `--version` | | Show version | `codex --version` |
| `--model` | `-m` | Specify model | `codex -m gpt-5-codex` |
| `--approval-mode` | `-a` | Set approval policy | `codex -a full-auto` |
| `--image` | `-i` | Attach image input | `codex -i error.png` |
| `--config` | `-c` | Override config | `codex -c 'key=value'` |

### Output Control Flags

| Flag | Short | Description |
|------|-------|-------------|
| `--quiet` | `-q` | JSON output mode |
| `--output-schema` | | Enforce JSON schema |
| `--output-last-message` | | Output final message only |
| `--include-plan-tool` | | Show planning steps |

### Sandbox Flags

| Flag | Description |
|------|-------------|
| `-s read-only` | Read-only access (safest) |
| `-s workspace-write` | Write to workspace (default for auto modes) |
| `-s danger-full-access` | Full filesystem access (dangerous) |

---

## 6. Model Configuration

### Default Model

The default model is `codex-mini-latest`, a fine-tuned version of o4-mini optimized for Codex CLI.

### Available Models

```bash
codex -m gpt-5-codex "task"       # GPT-5 Codex (recommended for complex tasks)
codex -m gpt-5 "task"             # GPT-5
codex -m o3 "task"                # O3 reasoning model
codex -m o4-mini "task"           # O4-mini (faster, lighter)
codex -m codex-mini-latest "task" # Default fine-tuned model
```

### Model Selection Guidelines

- **Complex reasoning:** `gpt-5-codex` or `o3`
- **Speed/efficiency:** `codex-mini-latest` or `o4-mini`
- **Structured output:** `gpt-5` or `o3` (avoid `gpt-5-codex` with `--output-schema`)

### Set Default Model

```toml
# ~/.codex/config.toml
[defaults]
model = "gpt-5-codex"
```

---

## 7. Structured JSON Output

Critical for CI/CD pipelines requiring parseable output.

### Define Schema

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

### Apply Schema

```bash
codex exec --output-schema schema.json \
  "analyze security vulnerabilities"
```

**Important:** Use `gpt-5` or `o3` models with `--output-schema`. The `gpt-5-codex` model currently has a known issue with schema enforcement.

---

## 8. Configuration Management

### Configuration File Location

- **macOS/Linux:** `~/.codex/config.toml`
- **Windows:** `%USERPROFILE%\.codex\config.toml`

### Example Configuration

```toml
[auth]
# Uncomment to use API key
# api_key = "sk-your-key"

[defaults]
model = "gpt-5-codex"
approval_mode = "auto-edit"
sandbox_mode = "workspace-write"

[sandbox_workspace_write]
network_access = false

[logging]
level = "info"
```

### View/Edit Configuration

```bash
# View
cat ~/.codex/config.toml

# Edit
vim ~/.codex/config.toml
```

### Runtime Overrides

```bash
# Override any config value at runtime
codex -c 'defaults.model=o3' -c 'defaults.approval_mode=full-auto' "task"
```

---

## 9. CI/CD Integration

### GitHub Actions

```yaml
name: Codex Code Analysis

on:
  pull_request:
    types: [opened, synchronize]

jobs:
  codex-analysis:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
      
      - name: Install Codex CLI
        run: npm install -g @openai/codex@0.55.0
      
      - name: Run Analysis
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          codex exec --full-auto \
            --model gpt-5-codex \
            --output-schema analysis-schema.json \
            "Analyze code quality and security issues" \
            > analysis.json
      
      - name: Upload Results
        uses: actions/upload-artifact@v4
        with:
          name: codex-analysis
          path: analysis.json
```

### GitLab CI

```yaml
codex_review:
  stage: test
  image: node:20
  
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
    - if: '$OPENAI_API_KEY'
  
  before_script:
    - npm install -g @openai/codex@0.55.0
  
  script:
    - |
      codex exec --full-auto \
        --model gpt-5-codex \
        --output-schema schema.json \
        "Review code changes" > output.json
  
  artifacts:
    paths:
      - output.json
    expire_in: 1 week
```

### Bash Script Template

```bash
#!/bin/bash
set -euo pipefail

# Configuration
PROMPT="Analyze code quality and suggest improvements"
MODEL="gpt-5-codex"
SCHEMA="analysis-schema.json"
OUTPUT="analysis.json"

# Verify prerequisites
if ! command -v codex &> /dev/null; then
    echo "Installing Codex CLI..."
    npm install -g @openai/codex@0.55.0
fi

if [ -z "${OPENAI_API_KEY:-}" ]; then
    echo "Error: OPENAI_API_KEY not set"
    exit 1
fi

# Run analysis
echo "Running Codex analysis..."
if codex exec \
    --full-auto \
    --model "$MODEL" \
    --output-schema "$SCHEMA" \
    "$PROMPT" > "$OUTPUT" 2> error.log; then
    echo "✅ Analysis complete: $OUTPUT"
    
    # Validate JSON
    if command -v jq &> /dev/null; then
        jq '.' "$OUTPUT" > /dev/null && echo "✅ Valid JSON"
    fi
else
    echo "❌ Analysis failed"
    cat error.log
    exit 1
fi
```

---

## 10. Production Best Practices

### Security

1. **Always use Git version control** - Codex warns if directory isn't tracked
2. **Start with restrictive modes** - Use `auto-edit` before `full-auto`
3. **Never commit API keys** - Use environment variables or secrets management
4. **Audit logs regularly** - Check `~/.codex/log/codex-tui.log`
5. **Use `--add-dir` instead of full access** - Principle of least privilege
6. **Avoid `--dangerously-bypass-approvals-and-sandbox`** in production

### Reliability

```bash
# Pin version for reproducibility
npm install -g @openai/codex@0.55.0

# Always capture output
codex exec "task" 2>&1 | tee codex-log.txt

# Use structured output for parsing
codex exec --output-schema schema.json "task"

# Set explicit timeouts in CI
timeout 300 codex exec "task"
```

### Performance & Rate Limits

```bash
# Check usage (interactive mode)
codex
> /status
```

**Note:** Send a message first if status appears empty (known display issue).

### Monitoring

```bash
# Enable verbose logging
export RUST_LOG=debug
codex exec "task"

# Session logs location
~/.codex/sessions/YYYY/MM/DD/

# JSON event stream
codex exec --json "task" > events.jsonl
```

---

## 11. Troubleshooting

### Installation Issues

```bash
# Command not found
npm list -g @openai/codex
npm install -g @openai/codex

# Check PATH
echo $PATH | grep npm

# Permissions error
sudo npm install -g @openai/codex
```

### Authentication Issues

```bash
# Clear auth cache
rm -rf ~/.codex/auth
codex --login

# Verify API key
echo $OPENAI_API_KEY
```

### Execution Issues

```bash
# Approval mode not working
codex --version  # Check version
codex --approval-mode full-auto "task"  # Explicit override

# JSON parsing errors
codex exec --output-schema schema.json "task"  # Use schema
codex exec -q "task" | jq '.'  # Quiet mode with jq

# Windows issues
# Use WSL2 instead of native Windows
```

### Common Errors

| Error | Solution |
|-------|----------|
| "OAuth requires browser" | Use API key auth in CI/CD |
| Approval prompts in full-auto | Check Windows vs WSL2, verify mode setting |
| Schema not enforced | Use `gpt-5` instead of `gpt-5-codex` |
| Empty usage in /status | Send a message first, then check status |

---

## 12. Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error (invalid arguments) |
| 2 | Authentication failure |
| >2 | Execution or API errors |

**Best Practice:** Always check both exit code and output for robust error handling.

---

## 13. Quick Reference

### Installation

```bash
brew install --cask codex           # macOS
npm install -g @openai/codex        # Cross-platform
```

### Authentication

```bash
codex --login                       # ChatGPT account
export OPENAI_API_KEY="sk-key"      # API key
```

### Execution

```bash
# Interactive
codex                               # Start session
codex "prompt"                      # With prompt
codex -i img.png "prompt"           # With image

# Headless
codex exec "task"                   # Basic
codex exec --full-auto "task"       # Full automation
codex exec -q "task" > out.json     # JSON output
codex exec -m gpt-5-codex "task"    # Specific model
codex exec --output-schema s.json "task"  # Structured output
```

### Approval Modes

```bash
--approval-mode suggest             # Approve everything
--approval-mode auto-edit           # Auto file edits
--approval-mode full-auto           # Full automation
```

### Configuration

```bash
~/.codex/config.toml                # Config location
codex -c 'key=value' "task"         # Runtime override
cat ~/.codex/config.toml            # View config
vim ~/.codex/config.toml            # Edit config
```

### Utilities

```bash
codex --version                     # Version
codex --upgrade                     # Update
codex --help                        # Help
```

---

## 14. Known Limitations

### Authentication in Headless Environments

**Issue:** Browser OAuth doesn't work in CI/CD  
**Solution:** Use API key authentication or experimental device code flow

### Windows Support

**Issue:** Native Windows has reliability issues with approval modes  
**Solution:** Use WSL2 for production environments

### Schema Enforcement

**Issue:** `--output-schema` doesn't work with `gpt-5-codex` model  
**Solution:** Use `gpt-5`, `o3`, or other models for structured output

### Multi-Turn Automation

**Issue:** `codex exec` is single-turn only  
**Solution:** Use interactive mode or implement retry logic in wrapper scripts

---

## 15. Advanced Usage

### Custom System Prompt

Edit `~/.codex/instructions.md` to customize AI behavior:

```markdown
# Custom Instructions

- Follow project style guide in STYLE.md
- Always run tests before committing
- Use TypeScript strict mode
- Prefer functional programming patterns
```

### Project-Specific Configuration

Create `AGENTS.md` in your repository root:

```markdown
# Project Agent Instructions

## Testing
- Run `npm test` before code changes
- Maintain >80% coverage

## Code Style
- Use Prettier with config in .prettierrc
- Follow ESLint rules

## Commands
- Build: `npm run build`
- Test: `npm test`
- Lint: `npm run lint`
```

### Model Context Protocol (MCP)

Configure MCP servers in `~/.codex/config.toml`:

```toml
[mcp_servers]
# Custom tools via MCP
[mcp_servers.my_tool]
command = "node"
args = ["/path/to/mcp-server.js"]
```

---

## 16. Additional Resources

- **GitHub Repository:** [github.com/openai/codex](https://github.com/openai/codex)
- **Official Documentation:** [developers.openai.com/codex](https://developers.openai.com/codex)
- **Help Center:** [help.openai.com - Codex](https://help.openai.com/en/articles/11096431-openai-codex-cli-getting-started)
- **Changelog:** [developers.openai.com/codex/changelog](https://developers.openai.com/codex/changelog/)
- **Issues:** [github.com/openai/codex/issues](https://github.com/openai/codex/issues)
- **Community:** [community.openai.com](https://community.openai.com)

---

## License

OpenAI Codex CLI is open-source under the Apache-2.0 License.

---

**Document Version:** 1.0  
**Last Updated:** November 5, 2025  
**Next Review:** December 2025
