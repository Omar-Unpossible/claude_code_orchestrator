# Obra Authentication Model - Clarification

**Date**: 2025-11-02
**Status**: Corrected

---

## ❌ Previous Misunderstanding

The original plans incorrectly assumed **Claude API** authentication model:
```bash
# WRONG - Not needed for Claude Code!
export ANTHROPIC_API_KEY=sk-ant-...
```

This is **NOT** how Claude Code works!

---

## ✅ How Claude Code Actually Works

### Authentication Model

**Claude Code uses session-based authentication**, not API keys.

```
┌─────────────────────────────────────────────┐
│ Your Machine                                │
│                                             │
│  You → claude login → Credentials Saved    │
│                                             │
│  Now all `claude` commands are              │
│  authenticated automatically!               │
│                                             │
│  Obra → subprocess.run(['claude', ...])    │
│         └─→ Inherits your auth! ✅         │
└─────────────────────────────────────────────┘
```

### Setup Process

**One-time setup** (you've probably already done this):
```bash
# Install Claude Code CLI
npm install -g @anthropics/claude-code

# Login (opens browser, saves credentials locally)
claude login

# Test (should work without any API key)
claude --version
```

**That's it!** No API keys, no environment variables needed.

### How Obra Uses It

**ClaudeCodeLocalAgent** (`src/agents/claude_code_local.py`):
```python
# Starts subprocess
self._process = subprocess.Popen(
    [self.command],  # Just 'claude'
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

# The subprocess inherits YOUR authentication!
# No API key configuration needed.
```

---

## 📊 Comparison: Claude Code vs Claude API

| Feature | Claude Code (You) | Claude API (Not You) |
|---------|-------------------|----------------------|
| **Authentication** | Session (login) | API key |
| **Command** | `claude` CLI | HTTP requests |
| **Credentials** | Browser login | `ANTHROPIC_API_KEY` |
| **Metering** | Subscription | Per-token billing |
| **What Obra Uses** | ✅ This one! | ❌ Not this |

---

## 🔧 Updated Prerequisites

### For Real Orchestration Testing

**Required**:
1. ✅ Claude Code CLI installed: `npm install -g @anthropics/claude-code`
2. ✅ Logged in: `claude login` (one time)
3. ✅ Verify: `claude --version` works without errors
4. ✅ Ollama running: `curl http://localhost:11434/api/tags`
5. ✅ Qwen model: `ollama pull qwen2.5-coder:32b`

**NOT Required**:
- ❌ No API key needed
- ❌ No `ANTHROPIC_API_KEY` environment variable
- ❌ No `.env` file
- ❌ No credentials in config files

---

## 🚀 Simplified Quick Start

### Check if You're Ready

```bash
# 1. Is Claude Code installed and authenticated?
claude --version
# Expected: Shows version (e.g., "2.0.31")
# If error: Run 'claude login'

# 2. Is Ollama running with Qwen?
curl http://localhost:11434/api/tags | grep qwen
# Expected: Shows qwen2.5-coder model
# If error: Run 'ollama pull qwen2.5-coder:32b'

# 3. That's it! No API key needed.
```

### Run First Test

```bash
cd /home/omarwsl/projects/claude_code_orchestrator
source venv/bin/activate

# Run simple test (no API key needed!)
python scripts/test_real_orchestration.py --task-type simple
```

---

## 🔍 How to Verify Authentication

### Check Claude Code Login Status

```bash
# Try running Claude directly
claude --help

# If you get output, you're logged in ✅
# If you get "not authenticated", run:
claude login
```

### What Happens When Obra Runs

```python
# Obra does this internally:
import subprocess

# Start Claude Code subprocess
process = subprocess.Popen(['claude'], ...)

# Claude Code checks:
# 1. Are credentials saved locally? → Yes (from your login)
# 2. Is session valid? → Yes (Anthropic validates)
# 3. Start interactive session → Success!

# Your task executes with YOUR credentials
# Metered against YOUR subscription
```

---

## 💡 Key Insights

### 1. Obra Doesn't Authenticate
Obra just runs `claude` command. The authentication is handled by:
- Your one-time `claude login`
- Claude Code CLI's credential storage
- Anthropic's session validation

### 2. Subprocess Inherits Auth
When Obra starts a subprocess:
```python
subprocess.Popen(['claude'], ...)
```

The subprocess runs as **you**, with **your credentials**, charged to **your subscription**.

### 3. No Configuration Needed
Obra's config files don't need any authentication settings:
```yaml
agent:
  type: claude_code_local
  local:
    command: claude  # ← Just the command, no auth config!
    workspace_dir: /tmp/workspace
    # No API keys, no tokens, nothing!
```

### 4. Same as Running Manually
Running Obra with Claude Code is exactly the same as if you:
```bash
# Type this yourself:
claude

# vs Obra doing:
subprocess.run(['claude'])
```

Both use the same authentication - **yours**.

---

## 🎯 Updated Testing Prerequisites

### Before First Real Test

**Check Authentication** (1 minute):
```bash
# Test 1: Can I run Claude?
claude --version
# ✅ If this works, authentication is fine
# ❌ If this fails, run: claude login

# Test 2: Can Claude start?
echo "Hello" | claude
# ✅ If Claude responds, it's working
# ❌ If timeout/error, check subscription status
```

**Check Ollama** (1 minute):
```bash
# Test: Is Ollama accessible?
curl http://localhost:11434/api/tags

# If fails: Start Ollama
systemctl start ollama  # or: ollama serve &
```

**That's all you need!**

---

## 📝 Documentation Updates Needed

The following docs incorrectly mention API keys and need updating:

1. ❌ `REAL_ORCHESTRATION_READINESS_PLAN.md` - References ANTHROPIC_API_KEY
2. ❌ `READINESS_SUMMARY.md` - Mentions API key in prerequisites
3. ❌ `REAL_WORLD_TEST_PLAN.md` - May mention API keys
4. ✅ `scripts/test_real_orchestration.py` - Fixed! ✅

**Correct information is in this document.**

---

## 🔐 Security Implications

### Good News
- ✅ No API keys to manage
- ✅ No credentials in config files
- ✅ No secrets to leak
- ✅ Session handled by Claude Code CLI

### Important Notes
- Obra runs with **your** authentication
- Tasks are charged to **your** subscription
- Rate limits are **your** account limits
- No way to separate Obra's usage from manual usage

---

## 🚦 Next Steps

### You're Ready If:
- [ ] `claude --version` works
- [ ] `claude --help` shows output
- [ ] Ollama responds to curl
- [ ] Qwen model is pulled

### Run First Test:
```bash
python scripts/test_real_orchestration.py --task-type simple
```

**No API key setup needed!** Just run it.

---

## ❓ FAQ

**Q: Do I need to set ANTHROPIC_API_KEY?**
A: No! That's for Claude API (different product). Claude Code uses session auth.

**Q: How does Obra authenticate?**
A: It doesn't. It just runs `claude` command, which uses YOUR authentication.

**Q: Will this use my subscription?**
A: Yes. Obra's usage is charged to your Claude Code subscription, just like manual usage.

**Q: What if my session expires?**
A: Re-run `claude login`. Sessions are long-lived (days/weeks).

**Q: Can I use a different account?**
A: Yes, logout and login with different account: `claude logout && claude login`

**Q: Does this work on all platforms?**
A: Yes - Windows, Mac, Linux. Wherever Claude Code CLI works.

---

## 📚 References

**Claude Code Documentation**:
- Installation: https://docs.claude.com/claude-code
- Authentication: https://docs.claude.com/claude-code/authentication

**NOT Relevant** (different product):
- Claude API keys: https://console.anthropic.com/ (not used by Claude Code)

---

**Status**: Authentication model clarified ✅
**Action**: Remove all API key references from documentation
**Next**: Run real test (no API key needed!)
