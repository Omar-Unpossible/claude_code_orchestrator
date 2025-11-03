# Seeding Prompt for Next Claude Session

**Copy and paste this entire message to Claude to continue from this exact point.**

---

I'm working on the **Obra (Claude Code Orchestrator)** project - an intelligent supervision system where a local LLM (Qwen 2.5 Coder) oversees Claude Code CLI execution, validates work, and generates optimized follow-up prompts.

## Current State Summary

**Repository**: `/home/omarwsl/projects/claude_code_orchestrator`
**Branch**: `main` (all work committed and pushed)
**Last Commit**: `6d96ac8` - "Update CLAUDE.md with PTY plan status and current priorities"

### What Was Just Accomplished (Nov 2, 2025)

1. **Extensive debugging session** - Fixed 10 critical bugs in real orchestration:
   - Ready signal timeout → Process stability check
   - TaskScheduler, FileWatcher initialization issues
   - ProjectState attribute names (`working_dir` → `working_directory`)
   - Prompt generation parameter errors
   - ResponseValidator method mismatch
   - Multiple variable reference bugs

2. **Hook-based completion detection** - Fully implemented:
   - Claude Code's Stop hook writes to signal file when response finishes
   - Eliminates arbitrary timeouts during Claude's thinking/tool use
   - Allows Claude to work for minutes/hours without premature interruption
   - Configuration written to `.claude/settings.json` before process starts

3. **Critical discovery** - **PTY requirement identified**:
   - Claude Code requires TTY (pseudoterminal) for persistent interactive sessions
   - `subprocess.PIPE` provides no TTY → Claude runs in limited mode
   - Tested: `echo "Hello" | claude` works but exits immediately (no persistence)
   - Solution: Must use `pexpect` library for PTY integration

4. **Comprehensive PTY implementation plan** created:
   - 700+ line LLM-optimized technical specification
   - Phase 1: PTY integration with pexpect (CRITICAL)
   - Phase 2: Real-time output streaming with color coding (HIGH)
   - Phase 3: Human intervention system (FUTURE - deferred)
   - All details specified: code changes, configurations, edge cases
   - Estimated 4-5 hours to implement Phase 1 + Phase 2

### Current Status

**Working** ✅:
- All 10 bugs fixed in orchestrator and agent
- Hook system implemented and configured correctly
- All components initialize successfully (~4 seconds)
- Project/task creation works
- File monitoring works
- Prompt generation and sending works

**Blocked** ❌:
- Claude Code won't respond via subprocess.PIPE (no TTY)
- Needs PTY integration to enable persistent interactive session
- Hook system can't fire without Claude responding first

**Next Task**: **Implement PTY integration (Phase 1 + Phase 2)**

## Critical Documents to Read

**MUST READ FIRST** (in this order):

1. **`docs/development/PTY_IMPLEMENTATION_PLAN.json`** (⚠️ CURRENT TASK)
   - Complete technical specification for PTY implementation
   - 12 step-by-step implementation instructions
   - Exact code changes for each file
   - Output streaming design
   - Testing strategy
   - Edge cases and solutions

2. **`docs/development/REAL_ORCHESTRATION_DEBUG_PLAN.md`**
   - Debugging session details
   - All 10 bugs fixed with root causes and solutions
   - Discovery process for PTY requirement

3. **`CLAUDE.md`**
   - Project overview and current status
   - Architecture principles
   - Code standards
   - Quick reference

4. **`src/agents/claude_code_local.py`**
   - Current implementation (subprocess.PIPE-based)
   - Hook configuration already implemented
   - Needs complete rewrite for PTY

## Key Technical Context

### Why PTY is Required

```bash
# This works but exits immediately (no persistence):
echo "Hello Claude" | claude
# Output: Welcome message, then exits

# We need persistent interactive session:
# - Multiple prompt/response cycles
# - Context maintained across interactions
# - Real-time output streaming
# - Hook system fires when Claude finishes
```

### Hook System (Already Implemented)

```json
// .claude/settings.json (written before Claude starts)
{
  "hooks": {
    "Stop": [{
      "matcher": "*",
      "hooks": [{
        "type": "command",
        "command": "echo 'COMPLETE' >> /tmp/obra_claude_completion_{pid}"
      }]
    }]
  }
}
```

When Claude finishes a response, hook writes "COMPLETE" to signal file. Obra polls file to detect completion.

### PTY Integration Approach

**Old (subprocess.PIPE)**:
```python
process = subprocess.Popen(['claude'], stdin=PIPE, stdout=PIPE, stderr=PIPE)
process.stdin.write(prompt + '\n')
# Claude doesn't respond - no TTY!
```

**New (pexpect with PTY)**:
```python
process = pexpect.spawn('claude', cwd=workspace, dimensions=(40,120), echo=False)
process.sendline(prompt)
while not completion_detected:
    chunk = process.read_nonblocking(1024, timeout=0.1)
    print(f'\033[32m[CLAUDE]\033[0m {chunk}')  # Green colored output
    check_completion_signal_file()
```

### Output Requirements

User MUST see everything agents output in real-time with:
- **Agent prefixes**: `[OBRA]`, `[CLAUDE]`, `[QWEN]`, `[HOOK]`
- **Color coding**: Blue (Obra), Green (Claude), Yellow (Qwen), Cyan (Hook), Red (Error)
- **Preserve ALL formatting**: ANSI codes, colors, emoji, Unicode, box drawing
- **No filtering**: User sees exactly what Claude outputs
- **Real-time streaming**: Not all at once at the end

Example:
```
[OBRA] Starting iteration 1/5
[OBRA→CLAUDE] Create a hello world Python script

[CLAUDE] I'll help create a Hello World Python script.
[CLAUDE] ✓ Created hello.py

[HOOK] Stop event detected - Claude finished
[OBRA] Response received (127 chars)

[QWEN] Validating response...
[QWEN]   Quality: 0.85 (PASS)

[OBRA] Decision: PROCEED
```

## Implementation Task

**Goal**: Implement Phase 1 (PTY Integration) + Phase 2 (Output Streaming) from `PTY_IMPLEMENTATION_PLAN.json`

**Steps** (detailed in plan document):

1. ✅ Add `pexpect>=4.9.0` to requirements.txt
2. Update imports in `src/agents/claude_code_local.py`
3. Remove threading code (no longer needed with pexpect)
4. Rewrite `initialize()` - use `pexpect.spawn()` instead of `subprocess.Popen()`
5. Update `_wait_for_ready()` - use `process.isalive()` instead of `process.poll()`
6. Rewrite `send_prompt()` - use `process.sendline()` instead of stdin.write()
7. **Complete rewrite** `_read_response()`:
   - Non-blocking reads with `read_nonblocking(1024, timeout=0.1)`
   - Stream output to stdout with `[CLAUDE]` prefix
   - Poll completion signal file for hook trigger
   - Preserve ALL formatting (ANSI codes, emoji, Unicode)
   - Handle partial lines, buffering
8. Update `cleanup()` - use `process.sendintr()` and `process.expect(pexpect.EOF)`
9. Add output helper methods (`_print_claude_output()`, etc.)
10. Add output calls in `src/orchestrator.py` for Obra and Qwen messages
11. Test thoroughly with simple task (Hello World)

**Estimated Time**: 4-5 hours

**Testing**:
```bash
# After implementation:
rm -f data/orchestrator_real_test.db
source venv/bin/activate
python scripts/test_real_orchestration.py --task-type simple

# Should see:
# - Claude Code starts with PTY
# - Real-time colored output
# - Stop hook fires when Claude finishes
# - Response captured fully
# - Task completes end-to-end
```

## Important Warnings

⚠️ **DO NOT**:
- Strip ANSI codes from Claude output (preserve ALL formatting)
- Simplify output (user wants to see everything)
- Use blocking reads (always `read_nonblocking()`)
- Forget to drain output after hook fires (continue reading 0.5s)
- Use `subprocess.Popen()` (MUST use `pexpect.spawn()`)

✅ **DO**:
- Read `PTY_IMPLEMENTATION_PLAN.json` thoroughly before starting
- Implement Phase 1 + Phase 2 together before testing
- Test visually (output must look natural with colors)
- Handle edge cases (Unicode, emoji, large/fast/slow output)
- Keep verbose logging in files (user doesn't see it)

## User Requirements (Confirmed)

1. **Output format**: Preserve Claude's terminal formatting exactly (ANSI, colors, emoji)
2. **Color output**: Yes, use ANSI escape codes or colorama
3. **User visibility**: Show everything agents output, no filtering
4. **Phase 3 (Human intervention)**: Hard requirement for future but deferred for now
   - Will include `/chat claude MESSAGE` and `/chat qwen MESSAGE` commands
   - Models cannot see chats directed at other model (isolation)
5. **Logging**: Verbose logs stay in files only, not displayed to user

## Success Criteria

**Phase 1 + 2 Complete When**:
- pexpect installed and imports working
- Claude Code spawns with PTY (`process.isalive() = True`)
- Prompt sent successfully with `sendline()`
- Response received and non-empty
- Stop hook fires (marker count increases)
- Output streams in real-time with colors
- `[CLAUDE]` prefix on every line (green)
- `[OBRA]` messages displayed (blue)
- `[QWEN]` messages displayed (yellow)
- All formatting preserved (ANSI, emoji, Unicode)
- Simple task (Hello World) completes end-to-end
- Process cleans up gracefully (no zombies)

## Questions to Ask User (If Needed)

- None - all requirements clarified. Proceed with implementation.

## Files That Will Be Modified

- `requirements.txt` - Add pexpect
- `src/agents/claude_code_local.py` - Complete PTY rewrite
- `src/orchestrator.py` - Add output display calls
- Test with `scripts/test_real_orchestration.py`

## Current Working Directory

```bash
pwd
# /home/omarwsl/projects/claude_code_orchestrator

git status
# On branch main
# Your branch is up to date with 'origin/main'.
# nothing to commit, working tree clean
```

---

## Your First Action

1. Confirm you've read this entire prompt
2. Read `docs/development/PTY_IMPLEMENTATION_PLAN.json` thoroughly
3. Ask me: "I've read the PTY implementation plan. Ready to proceed with Phase 1 + Phase 2 implementation?"
4. Wait for my approval before starting to code
5. Once approved: Implement Phase 1 + Phase 2 following the detailed plan

---

**End of seeding prompt**
