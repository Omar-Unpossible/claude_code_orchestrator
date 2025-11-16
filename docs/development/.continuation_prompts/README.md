# Continuation Prompts Directory

**Purpose**: Store continuation prompts for Claude Code sessions when context window reaches 80%

## Pattern

When Claude Code reaches 80% context usage during ADR-018 implementation:

1. Claude Code generates `session_<N>_continue.md` in this directory
2. Claude Code commits all work and provides handoff message
3. User starts fresh Claude Code session
4. User copies and pastes the file location: `docs/development/.continuation_prompts/session_<N>_continue.md`
5. Claude Code loads continuation prompt and resumes work
6. Process repeats for entire 8-week implementation (15-25 sessions estimated)

## Directory Contents

```
.continuation_prompts/
  README.md                          # This file
  TEMPLATE_continuation.md           # Template for Claude Code to use
  session_2_continue.md              # Resume after session 1 (80% context)
  session_3_continue.md              # Resume after session 2 (80% context)
  session_4_continue.md              # Resume after session 3 (80% context)
  ...
  session_N_continue.md              # Current continuation prompt
```

## File Naming Convention

- **Session 1**: Original startup prompt (parent directory)
- **Session 2+**: `session_<N>_continue.md` where N is session number

## What's Included in Continuation Prompts

Each continuation prompt contains:
- ✅ Current state (completed/in-progress tasks)
- ✅ Next steps (ordered task list)
- ✅ Files created/modified
- ✅ Test status and coverage
- ✅ Issues encountered and resolutions
- ✅ Decision records created
- ✅ Critical context for resuming
- ✅ Reference to original documentation
- ✅ Handoff checklist

## User Workflow

```bash
# Claude Code reaches 80% context
# Claude Code generates: session_2_continue.md
# Claude Code outputs: "⚠️ CONTEXT WINDOW AT 80% - SESSION HANDOFF REQUIRED"

# User opens new Claude Code session
claude

# User pastes file location
> docs/development/.continuation_prompts/session_2_continue.md

# Claude Code loads prompt and resumes work from where session 1 left off
```

## Session Tracking

Track session progress:
- Session 1: Tasks T1.1 - T1.5 (Story 1 complete)
- Session 2: Tasks T2.1 - T2.4 (Story 2 partial)
- Session 3: Tasks T2.5 - T3.2 (Story 2 complete, Story 3 partial)
- etc.

## Benefits

1. **No context loss**: Each session preserves exact state
2. **Clean handoffs**: Clear what's done, what's next
3. **Git safety**: All work committed before handoff
4. **Resumability**: Can resume days/weeks later
5. **Tracking**: Session files document progress
6. **Scalability**: Supports projects requiring 20+ sessions

---

**Last Updated**: 2025-01-15
**Related**: ADR-018 Implementation (8-week project, 15-25 sessions estimated)
