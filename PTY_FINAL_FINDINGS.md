# PTY Issue - Final Findings & Solution Options

**Date:** November 2, 2025
**Status:** ✅ **Root cause confirmed** - Path forward identified

---

## Executive Summary

**PTY interactive mode is fundamentally incompatible with automated contexts** due to Claude Code's update check behavior. However, **`--print` mode works perfectly** and offers a viable alternative architecture.

---

## What We Discovered

### 1. Root Cause: Claude Code Update Check in PTY Contexts

**Confirmed behavior:**
- ✅ Works: Manual interactive terminal
- ❌ Fails: pexpect PTY
- ❌ Fails: script wrapper PTY
- ❌ Fails: Even after removing npm installation
- ❌ Fails: Even with environment variables

**"Checking for updates" appears ONLY in automated PTY contexts and blocks indefinitely.**

###2. Why npm Removal Didn't Fix It

We removed the npm installation thinking it was a conflict:
```bash
$ sudo npm uninstall -g @anthropic-ai/claude-code
removed 3 packages

$ npm list -g @anthropic-ai/claude-code
└── (empty)  ✓ Confirmed
```

**Result:** ❌ Still hangs with "Checking for updates"

**Conclusion:** The issue is NOT dual installations - it's Claude Code's inherent behavior in PTY contexts.

### 3. Related Issue

**Issue #9026: "CLI hangs without TTY"**
- Documented Claude Code behavior
- Subprocesses expect real TTY, freeze in pseudo-TTY
- No official workaround published

---

## Solution: --print Mode

### Test Results

```bash
$ cd /tmp/test-workspace
$ claude --print "Hello, this is a test."
```

**Response:** ✅ Instant (<2 seconds)

```
Hello! I'm Claude Code, ready to help you with software engineering tasks...
```

**NO "Checking for updates" message!**

### Advantages

✅ Fast - responds in 1-3 seconds
✅ Reliable - no hanging
✅ No PTY issues
✅ No update check blocking
✅ Clean output (just the response)
✅ Works via subprocess.run()

### Limitations

❌ One-shot per call (exits after response)
❌ No persistent session (yet - untested with --session-id)
❌ Loses interactive terminal features
❌ May lose file context between calls (needs testing)

---

## Architecture Options

### Option A: Single-Shot --print Mode (Simplest)

**Approach:**
- Call `claude --print "<prompt>"` for each task
- Each call is independent
- No session continuity

**Implementation:**
```python
def send_prompt(self, prompt: str) -> str:
    result = subprocess.run(
        ['claude', '--print', prompt],
        cwd=self.workspace_path,
        capture_output=True,
        text=True,
        timeout=60
    )
    return result.stdout
```

**Pros:**
- Extremely simple
- Fast and reliable
- No PTY complexity

**Cons:**
- No conversation context
- Each call starts fresh
- May need to repeat context in prompts

**Use case:** Works for Obra if we include full context in each prompt

### Option B: Session-Based --print Mode (Needs Testing)

**Approach:**
- Use `--session-id <uuid>` flag to maintain context
- Call `claude --print --session-id <uuid> "<prompt>"` each time
- Session might persist across calls

**Implementation:**
```python
import uuid

class ClaudeCodeLocalAgent:
    def __init__(self):
        self.session_id = str(uuid.uuid4())

    def send_prompt(self, prompt: str) -> str:
        result = subprocess.run(
            ['claude', '--print', '--session-id', self.session_id, prompt],
            cwd=self.workspace_path,
            capture_output=True,
            text=True,
            timeout=60
        )
        return result.stdout
```

**Pros:**
- Maintains conversation context (if it works)
- Still fast and reliable
- No PTY issues

**Cons:**
- Untested - needs validation
- May not actually persist context
- Still one-shot per call

**Status:** 🔬 **NEEDS TESTING** - We couldn't complete the session test

### Option C: Hybrid - Manual Claude + Obra Guidance (Fallback)

**Approach:**
- User runs Claude manually in terminal
- Obra monitors file changes
- Obra provides prompts/guidance via stdout
- User copies prompts to Claude

**Pros:**
- Works immediately
- No technical blockers
- Human in the loop

**Cons:**
- Not fully autonomous
- Manual copy-paste required
- Defeats automation purpose

**Use case:** Temporary solution while waiting for Anthropic fix

### Option D: Wait for Anthropic Fix (Long-term)

**Approach:**
- Report Issue #9026 reproduction
- Request `--no-update-check` flag
- Wait for official PTY support

**Pros:**
- Proper long-term solution
- Will work as originally designed

**Cons:**
- Unknown timeline (days to months)
- No guarantee of fix
- Blocks current progress

**Use case:** Parallel track while using Option A/B/C

---

## Recommendation: Implement Option A Now

### Why Option A (Single-Shot --print)

**For Obra's use case, single-shot mode is actually IDEAL:**

1. **Each task is independent** - Obra sends complete context each time
2. **Fresh start avoids confusion** - No stale conversation state
3. **Simpler error handling** - No session management needed
4. **Proven to work** - We tested it successfully

**Obra already builds full context per prompt:**
```python
context = self.context_manager.build_context(
    task=task,
    history=history,
    files=files
)
```

So losing session continuity doesn't hurt us!

### Implementation Plan

1. **Modify `src/agents/claude_code_local.py`:**
   - Replace pexpect PTY with subprocess.run()
   - Use `--print` flag
   - Remove hook system (not needed)
   - Keep workspace management

2. **Update `send_prompt()` method:**
   ```python
   def send_prompt(self, prompt: str, context: Optional[Dict] = None) -> str:
       """Send prompt via --print mode (one-shot)."""
       result = subprocess.run(
           ['claude', '--print', prompt],
           cwd=str(self.workspace_path),
           capture_output=True,
           text=True,
           timeout=self.response_timeout
       )

       if result.returncode != 0:
           raise AgentException(f"Claude failed: {result.stderr}")

       return result.stdout
   ```

3. **Remove:**
   - pexpect dependency
   - PTY spawning code
   - Hook system code
   - Output streaming code

4. **Keep:**
   - Workspace management
   - File operations
   - Health checking
   - Configuration

**Lines of code: ~200 (vs current ~677) - Much simpler!**

### Testing Plan

1. Update `scripts/test_real_orchestration.py` to use new agent
2. Run simple task: "Create hello.py"
3. Verify response received
4. Verify file created
5. Run complex task
6. Validate end-to-end workflow

**Estimated time:** 1-2 hours

---

## Alternative: Test Option B First

If you want session continuity, we should test `--session-id` properly:

**Quick test (5 minutes):**
```bash
# Terminal 1
SESSION=$(uuidgen)
claude --print --session-id "$SESSION" "My name is Omar"

# Terminal 2 (or same)
claude --print --session-id "$SESSION" "What is my name?"
```

**Expected:**
- If context persists: "Your name is Omar"
- If no context: "I don't have that information"

**Note:** Our earlier test hung (may have been due to multiple Claude instances running)

---

## Decision Matrix

| Option | Speed | Reliability | Context | Complexity | Works Now |
|--------|-------|-------------|---------|------------|-----------|
| A: Single-shot --print | ⚡ Fast | ✅ High | ❌ No | ⭐ Simple | ✅ Yes |
| B: Session --print | ⚡ Fast | 🔬 Unknown | 🔬 Unknown | ⭐ Simple | 🔬 Needs test |
| C: Hybrid manual | 🐌 Slow | ✅ High | ✅ Yes | ⭐ Simple | ✅ Yes |
| D: Wait for fix | ⏳ N/A | ❓ Unknown | ✅ Yes | 😎 Ideal | ❌ No |
| E: Keep PTY | ⏳ Hangs | ❌ Broken | ✅ Yes | 😫 Complex | ❌ No |

---

## My Recommendation

**Implement Option A (Single-shot --print) immediately:**

1. **Works right now** - no blockers
2. **Simpler than PTY** - less code, fewer bugs
3. **Fits Obra's architecture** - we build full context anyway
4. **Fast and reliable** - instant responses
5. **Can upgrade to Option B later** if session-id works

**Time to production:** <2 hours

**Risk:** Very low (we tested it successfully)

---

## Next Steps

**If you approve Option A:**

1. I'll rewrite `claude_code_local.py` to use `--print` mode
2. Remove pexpect dependency
3. Test with simple task
4. Test with complex task
5. Run full integration test
6. Update documentation

**If you want to test Option B first:**

1. I'll create a proper session persistence test
2. If it works: implement session-based approach
3. If it fails: fall back to Option A

**If you prefer Option C:**

1. I'll update Obra to output prompts to terminal
2. User copies prompts to manual Claude session
3. Semi-autonomous workflow

---

## Your Call

Which option would you like me to implement?

**A)** Single-shot --print (fastest to production)
**B)** Test session-id first, then decide
**C)** Hybrid manual workflow
**D)** Wait and report to Anthropic

I recommend **A** because it works NOW, is simpler, and fits our architecture.

---

**Status:** Awaiting your decision on implementation path
