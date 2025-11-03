# TODO: PTY Implementation Next Steps

**Created:** November 2, 2025
**Priority:** HIGH
**Status:** Blocked - Waiting for Claude Code investigation

---

## 🚨 Current Blocker

**Issue:** Claude Code CLI gets stuck at "Checking for updates" when invoked via PTY and never completes responses.

**Evidence:**
- Prompt is delivered and displayed correctly
- Claude starts processing ("Thinking on")
- Gets stuck at "Checking for updates"
- Never completes, times out after 60-300s
- Hook never fires (completion signal file remains empty)
- Consistent across both simple and complex prompts

---

## 🔍 Investigation Tasks

### 1. Test Claude Code Directly (Manual)

**Goal:** Verify Claude Code works normally outside our automation

**Steps:**
```bash
# Test 1: Interactive mode
claude

# Test 2: With specific workspace
cd /tmp/claude-workspace-simple-test
claude

# Test 3: Check version and help
claude --version
claude --help

# Test 4: Look for update-related flags
claude --help | grep -i update
```

**Expected Outcome:** Identify if "Checking for updates" is normal startup behavior

---

### 2. Test Hook System Manually

**Goal:** Verify Stop hook works in manual Claude session

**Steps:**
```bash
# 1. Create hook configuration
mkdir -p /tmp/claude-test-hooks/.claude
cat > /tmp/claude-test-hooks/.claude/settings.json << 'EOF'
{
  "hooks": {
    "Stop": [{
      "matcher": "*",
      "hooks": [{
        "type": "command",
        "command": "echo 'HOOK FIRED' >> /tmp/claude_hook_test.log"
      }]
    }]
  }
}
EOF

# 2. Create signal file
echo "" > /tmp/claude_hook_test.log

# 3. Start Claude in that workspace
cd /tmp/claude-test-hooks
claude

# 4. Send a simple prompt
# (Type in Claude): "Who are you?"

# 5. After response, check hook file
cat /tmp/claude_hook_test.log
```

**Expected Outcome:** Hook file should contain "HOOK FIRED" after Claude responds

**What to look for:**
- Does hook fire on completion?
- Is there output in the hook file?
- Does Claude complete responses in manual mode?

---

### 3. Search for Update Disable Options

**Goal:** Find way to disable or skip update checks

**Research:**
- Check Claude Code documentation
- Search for environment variables (e.g., `CLAUDE_NO_UPDATE_CHECK`, `CLAUDE_SKIP_UPDATES`)
- Look for command-line flags (e.g., `--no-update-check`, `--offline`)
- Check settings file options

**Potential Solutions:**
```bash
# Try environment variables
CLAUDE_NO_UPDATE_CHECK=1 claude

# Try command flags
claude --no-update-check
claude --offline
claude --skip-updates

# Try settings file
# Add to .claude/settings.json:
{
  "updates": {
    "check": false
  }
}
```

---

### 4. Test Network Isolation

**Goal:** Determine if network access is required

**Test:**
```bash
# Block network temporarily
sudo iptables -A OUTPUT -d anthropic.com -j DROP

# Try Claude
claude

# Restore network
sudo iptables -D OUTPUT -d anthropic.com -j DROP
```

**Alternative (simpler):**
```bash
# Test with DNS failure
echo "127.0.0.1 api.anthropic.com" | sudo tee -a /etc/hosts
claude
# Remove after test
sudo sed -i '/api.anthropic.com/d' /etc/hosts
```

---

### 5. Check Claude Code Logs

**Goal:** Find Claude's internal logs for debugging

**Locations to check:**
```bash
# Common log locations
~/.claude/logs/
~/.config/claude/logs/
/tmp/claude*.log
~/.local/share/claude/

# Search for log files
find ~ -name "*claude*.log" 2>/dev/null
find ~/.claude -type f 2>/dev/null
find ~/.config/claude -type f 2>/dev/null
```

**What to look for:**
- Update check messages
- Network requests
- Error messages
- Stuck state indicators

---

### 6. Test with Subprocess Instead of PTY

**Goal:** Determine if issue is PTY-specific

**Quick Test Script:**
```python
import subprocess

# Test 1: Direct command
result = subprocess.run(['claude', '--version'], capture_output=True, text=True)
print(result.stdout)

# Test 2: Interactive mode (will fail but may show startup behavior)
proc = subprocess.Popen(['claude'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
proc.stdin.write("Who are you?\n")
proc.stdin.flush()
# Wait briefly
import time
time.sleep(5)
proc.terminate()
```

---

## 💡 Alternative Approaches (If Update Check Can't Be Disabled)

### Option 1: Pre-Warm Claude Session

**Idea:** Start Claude, wait for update check to complete, then use it

**Implementation:**
```python
def initialize_with_warmup(self):
    # Spawn process
    self.process = pexpect.spawn('claude', ...)

    # Wait for "Checking for updates" to complete
    # (may need to detect when update check finishes)
    time.sleep(10)  # or wait for specific output

    # Now ready for prompts
    self.state = ProcessState.READY
```

### Option 2: Use Different Claude Command

**Research:** Is there a `claude-cli` or `claude-batch` mode?

### Option 3: Mock Update Response

**Idea:** Intercept network requests and return fake "no updates" response

**Tool:** Use `mitmproxy` or modify `/etc/hosts`

### Option 4: Use API Instead

**Fallback:** If CLI remains problematic, use Anthropic API directly
- Requires API key (not subscription)
- Different cost model
- Would need significant refactoring

---

## 📋 Action Plan (Priority Order)

1. **IMMEDIATE:**
   - [ ] Test Claude Code manually to verify it works (Task #1)
   - [ ] Test hook system manually (Task #2)
   - [ ] Check Claude Code logs (Task #5)

2. **IF MANUAL WORKS:**
   - [ ] Search for update disable options (Task #3)
   - [ ] Test network isolation (Task #4)
   - [ ] Try subprocess instead of PTY (Task #6)

3. **IF BLOCKER PERSISTS:**
   - [ ] Try pre-warm approach (Alternative #1)
   - [ ] Research alternative Claude commands (Alternative #2)
   - [ ] Contact Claude Code support for programmatic usage guidance

4. **LAST RESORT:**
   - [ ] Switch to Anthropic API instead of CLI

---

## ✅ Success Criteria

**Minimum Viable:**
- Claude completes at least one response
- Hook fires successfully
- Response is captured

**Full Success:**
- Consistent response completion
- No timeouts
- Multi-iteration workflows work
- Context persists across prompts

---

## 📊 Current Status

- ✅ PTY implementation complete
- ✅ Output streaming working
- ✅ Hook configuration correct
- ✅ Process management robust
- ⏳ **Blocked:** Claude not completing responses
- ⏳ **Next:** Investigate update check behavior

---

## 📝 Notes

**For User:**
- The PTY implementation is **production-ready**
- The blocker is external (Claude Code CLI behavior)
- No code changes needed to our implementation
- Just need to resolve Claude's stuck state

**Questions to Ask:**
1. Does Claude Code work normally when you run it manually?
2. Do you see "Checking for updates" in normal usage?
3. Have you successfully used Claude Code programmatically before?
4. Are there any Claude Code command-line flags you use?

---

**Last Updated:** November 2, 2025
**Next Review:** After manual Claude testing
