# Quick Reference: Original vs Corrected Commands

**Purpose:** Side-by-side comparison for quick lookup  
**Date:** November 5, 2025

---

## Installation Commands

| Original Document ❌ | Corrected ✅ | Status |
|---------------------|-------------|---------|
| `brew install openai/codex/codex` | `brew install --cask codex` | CRITICAL FIX |
| `npm install -g @openai/codex` | `npm install -g @openai/codex` | ✅ CORRECT |

---

## Approval Modes

| Original Document ❌ | Corrected ✅ | Status |
|---------------------|-------------|---------|
| `--approval-mode auto` | `--approval-mode full-auto` | CRITICAL FIX |
| `--approval-mode manual` | `--approval-mode suggest` | CRITICAL FIX |
| `--approval-mode readonly` | `--approval-mode suggest` (read-only) | CRITICAL FIX |

**Note:** "auto-edit" mode also exists (not in original doc)

---

## Non-Existent Commands (Remove These)

| Original Document Claims ❌ | Reality ✅ |
|---------------------------|----------|
| `codex models list` | Does not exist - check docs instead |
| `codex doctor` | Does not exist - use `codex --version` |
| `codex config view` | Does not exist - use `cat ~/.codex/config.toml` |
| `codex config edit` | Does not exist - use `vim ~/.codex/config.toml` |
| `codex config set <key> <value>` | Does not exist - use `-c` flag or edit toml |

---

## File Input

| Original Document | Corrected | Status |
|------------------|-----------|---------|
| `codex exec -f input.txt` | `cat input.txt \| codex exec -` | UNDOCUMENTED FLAG |
| | `echo "prompt" \| codex exec -` | USE STDIN INSTEAD |

---

## Model Names

| Original Document | Corrected | Notes |
|------------------|-----------|-------|
| `gpt-5-codex` | `gpt-5-codex` | ✅ Correct |
| `gpt-4o-mini-codex` | `codex-mini-latest` or `o4-mini` | Wrong name |
| `gpt-5-turbo-codex` | No such model | Does not exist |
| | `o3` | Missing from original |
| | `gpt-5` | Missing from original |

**Default model:** `codex-mini-latest` (fine-tuned o4-mini)

---

## Missing Critical Flags (Add These)

| Flag | Purpose | Example |
|------|---------|---------|
| `--output-schema` | Structured JSON output | `codex exec --output-schema schema.json "task"` |
| `-q, --quiet` | JSON output mode | `codex exec -q "task"` |
| `--output-last-message` | Output only final message | `codex exec --output-last-message "task"` |
| `--include-plan-tool` | Show planning steps | `codex exec --include-plan-tool "task"` |
| `--add-dir` | Grant write to specific dir | `codex --add-dir /path "task"` |
| `--dangerously-bypass-approvals-and-sandbox` | ⚠️ Full bypass (dangerous) | Use only in controlled environments |

---

## Configuration

| Task | Original Doc Says ❌ | Actual Method ✅ |
|------|---------------------|-----------------|
| View config | `codex config view` | `cat ~/.codex/config.toml` |
| Edit config | `codex config edit` | `vim ~/.codex/config.toml` |
| Set value | `codex config set key value` | Edit toml or use `-c 'key=value'` |
| Override at runtime | Not mentioned | `codex -c 'key=value' "task"` |

---

## Common Workflows

### Original Document Workflow (BROKEN)

```bash
# Installation ❌
brew install openai/codex/codex

# Authentication ✅ (this part is correct)
codex --login

# Run with wrong approval mode ❌
codex exec --approval-mode auto "write tests"

# Check models ❌
codex models list

# Configure ❌
codex config set model gpt-5-codex
```

### Corrected Workflow (WORKING)

```bash
# Installation ✅
brew install --cask codex

# Authentication ✅
codex --login

# Run with correct approval mode ✅
codex exec --approval-mode full-auto "write tests"

# Check available models ✅
# (Consult official docs at developers.openai.com/codex)

# Configure ✅
echo 'model = "gpt-5-codex"' >> ~/.codex/config.toml
# Or override at runtime:
codex -c 'defaults.model=gpt-5-codex' "task"
```

---

## CI/CD Production Pattern

### Original Document Pattern (BROKEN)

```bash
#!/bin/bash
codex doctor  # ❌ Does not exist
codex models list  # ❌ Does not exist
codex exec -f prompt.txt --approval-mode auto  # ❌ Wrong flag & mode
```

### Corrected Production Pattern (WORKING)

```bash
#!/bin/bash
set -euo pipefail

# Verify installation
codex --version || exit 1

# Set API key
export OPENAI_API_KEY="${OPENAI_API_KEY}"

# Run with proper flags
codex exec \
    --approval-mode full-auto \
    --model gpt-5-codex \
    --output-schema schema.json \
    "Analyze code quality" > output.json

# Validate output
jq '.' output.json || exit 1
```

---

## Quick Syntax Reference

### Basic Commands

```bash
# Interactive mode
codex                          # ✅ Correct
codex "initial prompt"         # ✅ Correct

# Non-interactive mode
codex exec "task"              # ✅ Correct

# With image
codex -i screenshot.png "fix this"  # ✅ Correct

# With specific model
codex -m gpt-5-codex "task"    # ✅ Correct

# JSON output
codex exec -q "task"           # ✅ Correct
```

### Approval Modes (CORRECTED)

```bash
# Three valid modes:
codex --approval-mode suggest "task"     # Ask for everything
codex --approval-mode auto-edit "task"   # Auto file edits
codex --approval-mode full-auto "task"   # Full automation

# Shorthand:
codex --suggest "task"
codex --auto-edit "task"
codex --full-auto "task"
```

### Structured Output (NEW)

```bash
# Create schema
cat > schema.json << 'EOF'
{
  "type": "object",
  "properties": {
    "result": {"type": "string"}
  }
}
EOF

# Use schema
codex exec --output-schema schema.json "task"
```

---

## Known Issues Quick Reference

| Issue | Workaround |
|-------|-----------|
| OAuth needs browser | Use API key or device code flow |
| Windows unreliable | Use WSL2 |
| `--output-schema` broken with `gpt-5-codex` | Use `gpt-5` or `o3` instead |
| `/status` shows empty usage | Send a message first, then check |
| No multi-turn in exec | Use interactive mode or forks |

---

## Critical Reminders

⚠️ **DO NOT USE:**
- ❌ `brew install openai/codex/codex`
- ❌ `codex models list`
- ❌ `codex doctor`
- ❌ `codex config view/edit/set`
- ❌ `--approval-mode auto/manual/readonly`

✅ **DO USE:**
- ✅ `brew install --cask codex`
- ✅ Consult official docs for models
- ✅ `codex --version` for diagnostics
- ✅ Direct file editing for config
- ✅ `--approval-mode suggest/auto-edit/full-auto`

---

## For Emergency Reference

```bash
# If something breaks, start here:

# 1. Check version
codex --version

# 2. Check config
cat ~/.codex/config.toml

# 3. Check logs
tail -f ~/.codex/log/codex-tui.log

# 4. Re-authenticate
rm -rf ~/.codex/auth
codex --login

# 5. Reinstall
npm uninstall -g @openai/codex
npm install -g @openai/codex
```

---

**Last Updated:** November 5, 2025  
**Sources:** Official OpenAI documentation and GitHub repository  
**Full Details:** See `OpenAI_Codex_CLI_Headless_Guide_CORRECTED.md`
