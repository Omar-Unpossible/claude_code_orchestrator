# PTY Debugging Findings

**Date:** November 2, 2025
**Status:** Investigating Claude Code stuck state via pexpect

---

## Summary

Claude Code responds **immediately** when run manually in a terminal, but **always gets stuck** when invoked via pexpect PTY. The "Checking for updates" message appears in pexpect tests but not in manual tests.

---

## Test Results

### ✅ Manual Test (User - Works Perfect)

```bash
cd /tmp/claude-workspace
claude
> who are you?

● I'm Claude Code, an AI assistant made by Anthropic...
```

**Result:** Immediate response (< 1 second)
**Status Bar:** Shows "Thinking on" - NO "Checking for updates" message

---

### ❌ pexpect Test (Automated - Always Stuck)

```python
process = pexpect.spawn('claude', cwd='/tmp/claude-workspace', ...)
process.sendline("who are you?")
```

**Result:** Timeout after 10-60 seconds with no response
**Status Bar:** Shows "Thinking on" → "Checking for updates" (cycles)
**Hook:** Never fires (Claude never completes)

---

## Things We've Tested

| Test | Configuration | Result |
|------|---------------|--------|
| With hooks | Hook in `.claude/settings.json` | ❌ Stuck |
| **Without hooks** | No settings.json | ❌ **Still stuck** (not hook related) |
| echo=False | `pexpect.spawn(..., echo=False)` | ❌ Stuck |
| echo=True | `pexpect.spawn(..., echo=True)` | ❌ Stuck |
| --dangerously-skip-permissions | Added flag to command | ❌ Stuck |
| Different workspaces | Multiple /tmp directories | ❌ All stuck |
| Simple prompt | "who are you?" (same as manual) | ❌ Stuck |

**Conclusion:** The issue is NOT:
- ✗ Hook configuration
- ✗ Echo setting
- ✗ Permissions
- ✗ Workspace location
- ✗ Prompt content

---

## Key Observations

### 1. "Checking for updates" Only Appears in pexpect
- **Manual test:** No "Checking for updates" message
- **pexpect test:** "Checking for updates" appears in status bar

This is the **smoking gun** - something about pexpect triggers this behavior.

### 2. Prompt is Delivered Successfully
```
> who are you?
  [cursor]
────────────────────────────────────────────
  Thinking on (tab to toggle)
  Checking for updates              <-- Only in pexpect
```

Claude IS receiving the prompt and starting to process it.

### 3. Process Stays Alive
- Process doesn't crash
- `isalive()` returns True
- No error messages
- Just... stuck

---

## Hypothesis

**Primary Theory:** Claude Code detects it's running in a non-interactive PTY and behaves differently.

**Possible Causes:**
1. **Update check requires network and blocks:** PTY environment might trigger a different code path that checks for updates synchronously
2. **Input not being recognized as complete:** Maybe Claude is waiting for additional input that we're not providing
3. **PTY signal handling:** Maybe Claude is waiting for a specific signal or terminal response
4. **Terminal detection:** Claude might detect pexpect's PTY as "non-standard" and switch to a different mode

---

## What's Different Between Manual and pexpect?

| Aspect | Manual Terminal | pexpect PTY |
|--------|----------------|-------------|
| **TERM variable** | Usually "xterm-256color" | Set by pexpect |
| **Terminal capabilities** | Full terminfo | Limited |
| **Signal handling** | Normal | May differ |
| **stdin isatty()** | True | True (but pexpect) |
| **Process group** | Interactive session | Subprocess |

---

## Next Steps to Try

### 1. Check Environment Variables
```python
import os
env = os.environ.copy()
env['TERM'] = 'xterm-256color'  # Match normal terminal
env['COLORTERM'] = 'truecolor'
process = pexpect.spawn('claude', env=env, ...)
```

### 2. Try with `--print` Mode (Non-Interactive)
```python
# Claude has a --print flag for non-interactive use
result = subprocess.run(
    ['claude', '--print', 'who are you?'],
    capture_output=True,
    text=True,
    cwd='/tmp/claude-workspace'
)
```

### 3. Check Terminal Size
```python
# Maybe dimensions matter?
process = pexpect.spawn('claude', dimensions=(24, 80))  # Standard size
# or
process = pexpect.spawn('claude', dimensions=(60, 200))  # Larger
```

### 4. Test with `script` Command
```python
# Use Unix 'script' to create a real PTY
process = pexpect.spawn('script -q -c "claude" /dev/null', ...)
```

### 5. Monitor with strace
```bash
strace -f -e trace=network,read,write claude 2>&1 | tee claude_strace.log
# See what Claude is waiting for
```

### 6. Check for Update Check Disable
```bash
# Look for environment variable
CLAUDE_NO_UPDATE_CHECK=1 claude
# or
CLAUDE_SKIP_UPDATES=1 claude
```

### 7. Try Older Claude Version
```bash
# Check if different version works
claude install 2.0.30
```

---

## Recommended Action Plan

**Option A: Use `--print` Mode (If Available)**
- Bypass interactive mode entirely
- Use Claude in "print and exit" mode
- No PTY needed
- Update architecture to use subprocess instead

**Option B: Debug pexpect Environment**
- Test with different TERM values
- Try different dimensions
- Match user's exact environment

**Option C: Ask Anthropic Support**
- This might be a known issue
- They may have programmatic usage guidance
- Could be a bug in Claude Code

**Option D: Wait for Manual Testing**
- User should run our pexpect test script
- See if they get same stuck behavior
- Rules out environment-specific issues

---

## Files for User to Test

Created test scripts:
- `scripts/test_pty_no_hook.py` - Tests without hooks
- `/tmp/test_pty_bypass.py` - Tests with --dangerously-skip-permissions

**User action:**
```bash
source venv/bin/activate
python scripts/test_pty_no_hook.py
```

If user also gets stuck → It's a pexpect/Claude interaction issue
If user gets response → It's environment-specific

---

## Code Changes Pending

Once we solve this, need to add to `claude_code_local.py`:
```python
self.claude_command = config.get('claude_command', 'claude --dangerously-skip-permissions')
```

Or potentially switch to `--print` mode entirely.

---

**Status:** Blocked pending further investigation or user testing
**Next:** Try `--print` mode or have user test pexpect script
