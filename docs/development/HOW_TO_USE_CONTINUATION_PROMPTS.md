# How to Use Continuation Prompts for ADR-018 Implementation

**Quick Guide for Users**

---

## What Are Continuation Prompts?

Continuation prompts are automatically generated files that allow Claude Code to resume work from a fresh session when its context window reaches 80% capacity.

**Why needed**: ADR-018 implementation is an 8-week project. Claude Code will need 15-25 sessions to complete it, generating a new continuation prompt each time context fills up.

---

## User Workflow

### Session 1 (Initial Startup)

```bash
# Start Claude Code
claude

# Paste this file location when prompted:
docs/development/ORCHESTRATOR_CONTEXT_MGMT_STARTUP_PROMPT.md

# Claude Code begins implementation
# Works through tasks until context reaches 80%
```

### Claude Code Reaches 80% Context

Claude Code will output:
```
⚠️ CONTEXT WINDOW AT 80% - SESSION HANDOFF REQUIRED

**Session 1 Summary**:
- Completed: Tasks T1.1 through T2.3
- Story: Context Window Manager (75% complete)
- Tests: 45/45 passing, 92% coverage
- Git: All changes committed to obra/adr-018-context-management

**To Continue**:
Start new Claude Code session and paste this file location:
docs/development/.continuation_prompts/session_2_continue.md

**Next Session Will**:
- Complete Task T2.4: Implement Usage Tracking
- Continue with Story 2
- Estimated time: 3-4 hours
```

### Session 2 (Continuation)

```bash
# Exit current Claude Code session
# Start NEW Claude Code session
claude

# Copy and paste the file location provided:
docs/development/.continuation_prompts/session_2_continue.md

# Claude Code loads continuation prompt
# Resumes from exactly where Session 1 left off
# Works until context reaches 80% again
```

### Session 3, 4, 5... (Repeat Pattern)

Each session follows the same pattern:
1. Claude Code works until 80% context
2. Claude Code generates `session_<N>_continue.md`
3. Claude Code provides handoff message with file location
4. User starts new session with that file location
5. Repeat

---

## What You Do

**Your role is simple**:

1. ✅ Start new Claude Code session when notified
2. ✅ Copy/paste the continuation file location
3. ✅ Let Claude Code continue working

**You do NOT need to**:
- ❌ Manually track progress (Claude Code does this)
- ❌ Remember what was done (continuation prompt has it)
- ❌ Worry about losing work (everything committed before handoff)
- ❌ Edit or review continuation prompts (auto-generated)

---

## File Locations

**Startup (Session 1)**:
```
docs/development/ORCHESTRATOR_CONTEXT_MGMT_STARTUP_PROMPT.md
```

**Continuations (Session 2+)**:
```
docs/development/.continuation_prompts/session_2_continue.md
docs/development/.continuation_prompts/session_3_continue.md
docs/development/.continuation_prompts/session_4_continue.md
...
docs/development/.continuation_prompts/session_N_continue.md
```

---

## Tracking Progress

**Check session files** to see progress:

```bash
# List all continuation prompts
ls -l docs/development/.continuation_prompts/

# View latest continuation prompt
cat docs/development/.continuation_prompts/session_<N>_continue.md

# Check git commits
git log --oneline --graph obra/adr-018-context-management
```

Each continuation prompt shows:
- ✅ Tasks completed
- 🔄 Current task status
- 📊 Test coverage
- 📝 Files created/modified
- 🎯 Next steps

---

## Example Session Flow

**Session 1** (4 hours):
- Tasks: T1.1, T1.2, T1.3, T1.4, T1.5 (Story 1 complete)
- Context: 82%
- Generates: `session_2_continue.md`

**Session 2** (3 hours):
- Tasks: T2.1, T2.2, T2.3, T2.4 (Story 2 partial)
- Context: 79%
- Continues to T2.5...
- Context: 84%
- Generates: `session_3_continue.md`

**Session 3** (4 hours):
- Tasks: T2.5, T3.1, T3.2 (Story 2 complete, Story 3 partial)
- Context: 81%
- Generates: `session_4_continue.md`

... and so on for 15-25 sessions total

---

## What's in a Continuation Prompt?

Each continuation prompt contains:

**Current State**:
- ✅ Completed phases, stories, tasks
- 🔄 In-progress tasks with status
- 📋 Next steps (ordered)

**Work Summary**:
- 📁 Files created/modified
- ✅ Test status (passing/coverage)
- 🐛 Issues encountered and resolutions
- 📝 Decision records created

**Context**:
- 🔍 Critical discoveries for resuming
- 🔗 Reference documentation links
- 📊 Verification gate status

**Git State**:
- 🌿 Branch name
- 📝 Last commit message
- ✅ Clean working directory

---

## Benefits

**No Context Loss**:
- Every handoff preserves exact state
- Claude Code picks up exactly where it left off

**Clean Handoffs**:
- Clear what's done, what's next
- No ambiguity about progress

**Git Safety**:
- All work committed before handoff
- Can always rollback if needed

**Resumability**:
- Can resume days or weeks later
- Continuation prompts preserve all context

**Tracking**:
- Session files document progress
- Easy to see how far along implementation is

---

## Troubleshooting

### "Claude Code doesn't recognize the continuation prompt"

**Solution**: Make sure you're pasting the full file path:
```
docs/development/.continuation_prompts/session_2_continue.md
```

NOT just:
```
session_2_continue.md
```

### "Continuation prompt doesn't exist"

**Cause**: Claude Code hasn't generated it yet (context not at 80%)

**Solution**: Let current session continue working. Claude Code will generate it when needed.

### "Claude Code starts from beginning instead of continuing"

**Cause**: You pasted the original startup prompt instead of continuation prompt

**Solution**: Use the continuation prompt file location provided in handoff message

### "Progress seems lost"

**Check**:
1. Git commits: `git log obra/adr-018-context-management`
2. Files exist: `ls -la src/orchestration/memory/`
3. Latest continuation prompt for current state

All work is committed before handoffs - nothing is lost.

---

## Tips

**Optimal Session Length**: 3-5 hours per session
- Allows 3-5 tasks to complete before 80% context
- Manageable work chunks
- Good commit sizes

**Session Scheduling**:
- Can do multiple sessions per day
- Can take days/weeks between sessions
- Continuation prompts preserve state indefinitely

**Monitoring Progress**:
- Check continuation prompts for progress
- Review git commits for changes
- Test coverage reports show quality

**When to Review**:
- After each verification gate (P1, P2, P3, P4)
- After each story completion
- Before merging to main

---

## Summary

**Your workflow is simple**:

1. Start Claude Code session with continuation prompt location
2. Let Claude Code work until 80% context
3. Claude Code generates next continuation and hands off
4. Repeat until implementation complete

**Claude Code handles**:
- Progress tracking
- State preservation
- Git commits
- Test verification
- Continuation prompt generation

**You just**:
- Start new sessions when notified
- Paste continuation file location
- Monitor overall progress

---

**Last Updated**: 2025-01-15
**Related**: ADR-018 Implementation, ORCHESTRATOR_CONTEXT_MGMT_STARTUP_PROMPT.md
**Estimated Sessions**: 15-25 sessions for full 8-week implementation
