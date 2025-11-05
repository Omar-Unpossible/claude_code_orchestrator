# ADR-011: Interactive Streaming Interface

**Status**: Accepted
**Date**: 2025-11-04
**Deciders**: Omar (Unpossible Creations), Claude Code
**Related**: [INTERACTIVE_STREAMING_IMPLEMENTATION_PLAN.md](../development/INTERACTIVE_STREAMING_IMPLEMENTATION_PLAN.md)

---

## Context

During the Tetris game test (November 4, 2025), we identified a critical gap in Obra's user experience:

**Problem Statement**:
- Users cannot see Obra↔Claude conversation during execution
- No ability to guide or correct agents mid-task
- Must wait for task completion to see results
- Logs are write-only with no interactive feedback loop

**User Need**:
> "Are we able to run Obra in a terminal/interface which prints out the Obra + Claude prompts/responses and allows the user (me) to send chats directed at either agent?"

**Context**:
- Attempted PTY implementation failed (Claude Code doesn't work with PTY)
- Current headless mode works but provides no visibility
- Need terminal-based solution (no web UI dependencies)

---

## Decision

We will implement **Option 2: Log Streaming + Command Injection** as the initial solution, with a clear path to evolve into **Option 1: TUI** later.

**Rationale**:
1. ✅ Fastest time-to-value (can implement in 4-6 hours)
2. ✅ No new UI framework dependencies initially
3. ✅ Works with existing headless architecture
4. ✅ Provides foundation for TUI evolution
5. ✅ Terminal-based (aligns with Obra's CLI-first philosophy)

---

## Options Considered

### Option 1: Full TUI (textual-based)

**Pros**:
- ✅ Best user experience (split panels, rich formatting)
- ✅ Multiple views simultaneously (Obra/Claude/Qwen)
- ✅ Modern and polished interface

**Cons**:
- ❌ Longer implementation time (6-9 hours)
- ❌ New dependency (textual framework)
- ❌ More complex testing
- ❌ Harder to debug

**Verdict**: ⏳ Defer to future enhancement

---

### Option 2: Log Streaming + Command Injection (SELECTED)

**Pros**:
- ✅ Quick to implement (4-6 hours)
- ✅ Minimal dependencies (colorama, prompt_toolkit)
- ✅ Works with existing logging infrastructure
- ✅ Easy to test and debug
- ✅ Can evolve into TUI later

**Cons**:
- ⚠️ Less visual appeal than TUI
- ⚠️ Linear output (no split panels)
- ⚠️ Requires scrolling for history

**Verdict**: ✅ **SELECTED** - Best balance of speed and functionality

---

### Option 3: Web UI Dashboard

**Pros**:
- ✅ Remote monitoring capability
- ✅ Multi-session support
- ✅ Rich visualizations

**Cons**:
- ❌ Much longer implementation (12+ hours)
- ❌ Requires web framework (FastAPI, React)
- ❌ Adds deployment complexity
- ❌ Overkill for single-user local development

**Verdict**: ❌ Rejected - Out of scope for current needs

---

### Option 4: Enhanced Breakpoints Only

**Pros**:
- ✅ Minimal implementation (2 hours)
- ✅ Reuses existing breakpoint system

**Cons**:
- ❌ No real-time visibility
- ❌ Only interrupts at breakpoints
- ❌ No streaming output
- ❌ Doesn't solve core problem

**Verdict**: ❌ Rejected - Insufficient solution

---

## Implementation Approach

### Phase 1: Real-Time Streaming (P0)
**Duration**: 1-2 hours
- Create `StreamingHandler` for colored log output
- Add `--stream` CLI flag
- Stream Obra→Claude, Claude→Obra, Qwen validation in real-time

**Acceptance**: `./venv/bin/python -m src.cli task execute 3 --stream` shows live colored output

---

### Phase 2: Interactive Command Injection (P0)
**Duration**: 2-3 hours
- Create `CommandProcessor` for command parsing
- Add `--interactive` CLI flag
- Implement commands: `/pause`, `/resume`, `/to-claude`, `/to-obra`, `/override-decision`
- Non-blocking input management with threads

**Acceptance**: User can inject commands and see immediate effect

---

### Phase 3: UX Enhancements (P1)
**Duration**: 1 hour
- Progress indicators (spinner)
- Better formatting (separators, token stats)
- Keyboard shortcuts
- Session transcript export

**Acceptance**: Professional-looking output with good UX

---

### Future: TUI Evolution (P2)
**Duration**: 2-3 hours
- Migrate to `textual` framework
- Split panels for simultaneous views
- Command autocomplete
- Syntax highlighting

**Acceptance**: `./venv/bin/python -m src.cli task execute 3 --tui` launches full TUI

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│ User Input (Terminal)                                   │
│   ↓ /to-claude "message"                               │
├─────────────────────────────────────────────────────────┤
│ InputManager (Thread-safe input)                        │
│   ↓ Queue → CommandProcessor                           │
├─────────────────────────────────────────────────────────┤
│ Orchestrator (Interactive Mode)                         │
│   ├─ Inject context into prompts                       │
│   ├─ Override decisions                                 │
│   └─ Pause/resume execution                            │
├─────────────────────────────────────────────────────────┤
│ StreamingHandler (Colored output)                       │
│   ├─ [OBRA→CLAUDE] (blue)                             │
│   ├─ [CLAUDE→OBRA] (green)                            │
│   └─ [QWEN] (yellow)                                   │
└─────────────────────────────────────────────────────────┘
```

---

## Consequences

### Positive

1. **Immediate Value**: Users get visibility and control within days
2. **Incremental Adoption**: Can use `--stream` alone or with `--interactive`
3. **Testing**: Easy to test streaming vs TUI complexity
4. **Evolution Path**: Clear migration to TUI when ready
5. **Debugging**: Easier to debug streaming logs than TUI state

### Negative

1. **Two Iterations**: Will need to refactor when moving to TUI
2. **UX Limitations**: Linear output less intuitive than split panels
3. **Technical Debt**: Streaming code may need partial rewrite for TUI

### Mitigations

- Design streaming code with TUI evolution in mind
- Keep clear separation between data (what to show) and presentation (how to show)
- Document TUI migration path early

---

## Dependencies

### New Dependencies

```json
{
  "phase_1_2": [
    "colorama>=0.4.6",
    "prompt_toolkit>=3.0.0"
  ],
  "phase_3": [
    "textual>=0.40.0",
    "pygments>=2.16.0"
  ]
}
```

### License Compatibility

All dependencies are permissive licenses:
- colorama: BSD-3-Clause ✅
- prompt_toolkit: BSD-3-Clause ✅
- textual: MIT ✅
- pygments: BSD-2-Clause ✅

No licensing conflicts with Obra (MIT).

---

## Alternatives Considered (Lower Priority)

### Voice Control
- Use SpeechRecognition for voice commands
- Priority: P4 (future consideration)
- Effort: 6-8 hours

### Mobile App Notifications
- Push notifications on task completion
- Priority: P4 (future consideration)
- Effort: 12-16 hours

### Multi-Session Dashboard
- Monitor multiple Obra tasks simultaneously
- Priority: P3 (after TUI stable)
- Effort: 4-6 hours

---

## Success Criteria

### Phase 1-2 Success

```json
{
  "user_experience": {
    "visibility": "User sees all agent communication in real-time",
    "responsiveness": "Commands execute within 50ms",
    "reliability": "0% crash rate in 100 test runs"
  },
  "adoption": {
    "usage_rate": ">80% of long-running tasks use --stream",
    "interactive_usage": ">50% of tasks use --interactive"
  }
}
```

### TUI Evolution Success (Future)

```json
{
  "user_experience": {
    "panels": "3-panel layout (Obra/Claude/Qwen) works smoothly",
    "performance": "No lag or stuttering in TUI",
    "features": "All Phase 2 commands work in TUI"
  }
}
```

---

## Timeline

```
Week 1 (Nov 4-8, 2025):
  - Day 1-2: Implement Phase 1 (streaming)
  - Day 2-3: Implement Phase 2 (interactive)
  - Day 4: Testing and bug fixes
  - Day 5: Documentation

Future (TBD):
  - Phase 3 (TUI): When Phase 1-2 is stable and demand exists
```

---

## Related Documents

- **Implementation Plan**: [INTERACTIVE_STREAMING_IMPLEMENTATION_PLAN.md](../development/INTERACTIVE_STREAMING_IMPLEMENTATION_PLAN.md)
- **Related ADRs**:
  - [ADR-004: Local Agent Architecture](ADR-004-local-agent-architecture.md) - Headless mode foundation
  - [ADR-007: Headless Mode Enhancements](ADR-007-headless-mode-enhancements.md) - Session management
- **User Guide** (future): `docs/guides/INTERACTIVE_MODE_GUIDE.md`

---

## Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Thread safety issues | Medium | High | Use thread-safe queues, locks, thorough testing |
| Input blocking causes hangs | Low | High | Always use timeouts, daemon threads |
| Performance overhead | Low | Low | Make streaming optional, benchmark |
| Command parsing errors | Medium | Medium | Comprehensive error handling, helpful messages |

---

## Review and Approval

**Reviewed By**: Omar (Project Owner)
**Approved By**: Omar
**Date**: 2025-11-04
**Status**: ✅ Approved for Implementation

**Next Steps**:
1. Begin Phase 1 implementation
2. Test with Tetris project continuation
3. Gather user feedback
4. Iterate based on usage patterns

---

## Changelog

| Date | Author | Change |
|------|--------|--------|
| 2025-11-04 | Claude | Initial ADR created |
| 2025-11-04 | Omar | Reviewed and approved |

---

**Decision Outcome**: Implement Option 2 (Log Streaming + Command Injection) with a clear evolution path to TUI (Option 1).
