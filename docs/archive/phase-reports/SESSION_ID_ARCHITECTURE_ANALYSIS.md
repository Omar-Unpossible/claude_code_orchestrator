# Session ID Architecture Analysis

**Date**: 2025-11-04
**Context**: BUG-PHASE4-002 investigation
**Question**: What's the difference between Obra's and Claude's session IDs?

---

## TL;DR: They're Supposed to Be the SAME

**Key Finding**: There is (by design) **ONE session_id** shared between Obra and Claude Code. The confusion comes from fresh session mode breaking this assumption.

---

## Current Architecture (By Design)

### Milestone Session Flow (Working Correctly)

```
1. User calls: orchestrator.start_milestone_session(project_id=1)

2. Obra generates UUID:
   session_id = str(uuid.uuid4())  # e.g., "0a0d5a10-f948-4e92-89b3-7f17f1d04068"

3. Obra stores in database:
   state_manager.create_session_record(
       session_id=session_id,  # <-- INSERT into session_record table
       project_id=project_id
   )

4. Obra shares with agent:
   self.agent.session_id = session_id  # <-- Agent now knows Obra's UUID

5. Agent uses Obra's UUID when calling Claude:
   command = ['claude', '--print', '--session', session_id, prompt]
   # Claude Code uses THIS session_id internally

6. Claude returns response with SAME session_id:
   {
       "session_id": "0a0d5a10-f948-4e92-89b3-7f17f1d04068",  # <-- Same UUID!
       "result": "...",
       "usage": {...}
   }

7. Orchestrator updates database:
   state_manager.update_session_usage(
       session_id=metadata['session_id'],  # <-- UUID exists in DB ✅
       tokens=...,
       turns=...
   )
```

**Result**: ✅ **ONE session_id** flows through entire system

---

## The Problem: Fresh Session Mode

### Current Config Setting

From `config/config.yaml` line 30:
```yaml
agent:
  local:
    use_session_persistence: false  # ❌ Breaks shared session ID
```

### Fresh Session Flow (BROKEN)

```
1. User calls: orchestrator.execute_task(task_id=1)
   # No milestone session created!

2. Obra does NOT generate session_id
   # No database record created

3. Agent generates its OWN UUID:
   if not self.use_session_persistence:
       session_id = str(uuid.uuid4())  # <-- FRESH UUID, not in Obra DB
       logger.debug('Fresh session per call')

4. Agent calls Claude with fresh UUID:
   command = ['claude', '--print', '--session', session_id, prompt]
   # Claude uses agent's fresh UUID

5. Claude returns response with agent's fresh UUID:
   {
       "session_id": "b7f3c21a-8d4e-4a1b-9e2f-1c5d8a3f6b9e",  # <-- NEW UUID!
       "result": "...",
       "usage": {...}
   }

6. Orchestrator tries to update database:
   state_manager.update_session_usage(
       session_id="b7f3c21a...",  # <-- UUID DOES NOT EXIST in DB ❌
       tokens=...,
       turns=...
   )

7. Database query fails:
   SELECT * FROM session_record WHERE session_id = 'b7f3c21a...'
   # No rows found!

   ERROR: "Session b7f3c21a-8d4e-4a1b-9e2f-1c5d8a3f6b9e not found"
```

**Result**: ❌ **TWO different UUIDs** - Obra has none, Agent generates one

---

## Data Schema Analysis

### SessionRecord Model

From `src/core/models.py`:838-860:

```python
class SessionRecord(Base):
    """Session tracking model for milestone execution.

    Tracks Claude Code session lifecycle for milestone-based work.

    Attributes:
        id: Primary key
        session_id: Claude Code session UUID  # ❌ MISLEADING COMMENT!
        ...
    """
    __tablename__ = 'session_record'

    id = Column(Integer, primary_key=True)
    session_id = Column(String(64), unique=True, nullable=False, index=True)
    project_id = Column(Integer, ForeignKey('project_state.id'), nullable=False)
    ...
```

### The Misleading Comment

Line 846 says: `session_id: Claude Code session UUID`

**This is misleading!** It should say:

```python
session_id: Shared session UUID used by BOTH Obra and Claude Code.
           Obra generates this UUID and passes it to Claude for coordinated session tracking.
```

### Schema is Correct, Comment is Wrong

The schema has **ONE `session_id` field** - which is correct. The design is:

1. **Obra owns the session lifecycle** (creates, tracks, ends)
2. **Obra generates the UUID** and stores it as primary identifier
3. **Obra shares UUID with Claude** so both systems reference the same session
4. **Claude returns this UUID** in metadata for confirmation
5. **Obra uses returned UUID** to update the same database record

**There are NOT two separate IDs** - there's one ID shared between systems.

---

## Why Fresh Sessions Break This

### The Use Case for Fresh Sessions

From CLAUDE.md (Headless Mode section):

```markdown
- **Fresh Sessions**: Each call uses a new session (no persistent state) for 100% reliability
- **Why This Works**: Obra provides context continuity across fresh sessions
```

Fresh sessions were designed to:
- Avoid Claude Code's PTY/session state bugs
- Ensure 100% reliability (no session conflicts)
- Let Obra handle context continuity, not Claude

### The Oversight

Fresh sessions were implemented without accounting for session tracking:

1. ✅ Reliability improved (no session conflicts)
2. ✅ Context continuity via Obra prompts
3. ❌ Session usage tracking broken (UUID mismatch)
4. ❌ Database updates fail (no session record)

---

## Answering Your Questions

### Q1: What's the difference between Obra's and Claude's session IDs?

**A**: **By design, there is NO difference** - they should be the SAME UUID.

- **Milestone session mode**: Obra generates UUID, Claude uses it ✅
- **Fresh session mode**: Agent generates UUID, Obra doesn't know about it ❌

### Q2: Is our data schema appropriately designed to accommodate both?

**A**: **YES**, the schema is correct. There's ONE `session_id` field because there's supposed to be ONE shared UUID.

The problem is NOT the schema - it's the fresh session implementation bypassing session record creation.

### Q3: If Option A generates a temp ID, WHICH temp ID (Obra's or Claude's)?

**A**: **OBRA's temp ID**, which then gets shared with Claude.

The correct flow for Option A:

```python
def execute_task(self, task_id: int, session_id: Optional[str] = None, ...):
    """Execute task with optional session context."""

    # Create temporary Obra session if none provided
    if session_id is None:
        session_id = str(uuid.uuid4())  # <-- OBRA generates UUID

        # Store in Obra database
        self.state_manager.create_session_record(
            session_id=session_id,
            project_id=self.current_project.id,
            milestone_id=None  # Temporary session, no milestone
        )

        # Share with agent
        if hasattr(self.agent, 'session_id'):
            self.agent.session_id = session_id  # <-- Agent uses Obra's UUID

        cleanup_session = True
    else:
        cleanup_session = False

    try:
        # Execute task - agent will use Obra's session_id
        result = self._execute_single_task(task_id, max_iterations, context)

        # update_session_usage() now finds session_id in database ✅
        return result

    finally:
        if cleanup_session:
            # Mark temporary session as completed
            self.state_manager.complete_session_record(
                session_id=session_id,
                ended_at=datetime.now(UTC)
            )
```

### Q4: Should we replace with Claude's ID after Claude supplies it?

**A**: **NO replacement needed** - if we do it correctly, Claude returns the SAME ID we gave it.

The flow should be:
1. Obra generates UUID: `"abc-123"`
2. Obra gives to agent: `agent.session_id = "abc-123"`
3. Agent gives to Claude: `--session abc-123`
4. Claude returns metadata: `{"session_id": "abc-123"}`  ← Same!
5. Obra updates DB: `UPDATE session_record WHERE session_id='abc-123'` ✅

**No replacement, no mapping, just one ID flowing through the system.**

---

## The Real Issue: Fresh Sessions vs Session Tracking

### The Conflict

Two goals in tension:

1. **Reliability** (fresh sessions): Don't persist Claude state, avoid bugs
2. **Tracking** (session records): Track token usage, turns, cost per session

Current implementation chooses #1 (reliability) at expense of #2 (tracking).

### The Solution: Separate Concerns

**Obra sessions** (tracking) ≠ **Claude sessions** (state persistence)

We can have:
- **Obra session records**: ALWAYS created (for tracking)
- **Claude session persistence**: OPTIONAL (for state)

```python
# Obra ALWAYS creates session record (for tracking)
session_id = str(uuid.uuid4())
self.state_manager.create_session_record(session_id=session_id, ...)

# Agent uses this session_id for tracking...
self.agent.session_id = session_id

# ...but can still use fresh Claude sessions internally
if not self.use_session_persistence:
    # Agent can call Claude with --no-cache or without --session
    # But still reports session_id in metadata for Obra tracking
    command = ['claude', '--print', '--no-cache', prompt]
    # After execution, add session_id to metadata manually
    self.last_metadata['session_id'] = self.session_id
```

This separates:
- **Session tracking** (Obra's responsibility, always on)
- **Session state persistence** (Claude's responsibility, optional)

---

## Recommended Fix

### Option A-Refined: Session-Aware execute_task()

```python
def execute_task(self, task_id: int, max_iterations: int = 10,
                 context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Execute task with automatic session management.

    Creates temporary session if not in milestone context.
    """

    # Check if we're already in a milestone session
    in_milestone_session = hasattr(self, 'current_session_id') and self.current_session_id

    if not in_milestone_session:
        # Create temporary session for tracking
        temp_session_id = str(uuid.uuid4())

        # Get project from task
        task = self.state_manager.get_task(task_id)
        project_id = task.project_id

        # Create session record
        self.state_manager.create_session_record(
            session_id=temp_session_id,
            project_id=project_id,
            milestone_id=None  # Temporary, not milestone-bound
        )

        # Configure agent to use this session_id for tracking
        if hasattr(self.agent, 'session_id'):
            old_session_id = self.agent.session_id
            self.agent.session_id = temp_session_id

        logger.info(
            f"TEMP_SESSION: session_id={temp_session_id[:8]}..., "
            f"task_id={task_id}, mode=standalone"
        )

        cleanup_temp_session = True
        self.current_session_id = temp_session_id
    else:
        cleanup_temp_session = False

    try:
        # Execute task normally - session tracking now works
        result = self._execute_single_task(task_id, max_iterations, context)
        return result

    finally:
        if cleanup_temp_session:
            # Clean up temporary session
            try:
                self.state_manager.complete_session_record(
                    session_id=temp_session_id,
                    ended_at=datetime.now(UTC)
                )
                logger.info(f"TEMP_SESSION_END: session_id={temp_session_id[:8]}...")
            except Exception as e:
                logger.warning(f"Failed to clean up temp session: {e}")

            # Restore agent state
            if hasattr(self.agent, 'session_id'):
                self.agent.session_id = old_session_id

            self.current_session_id = None
```

---

## Summary

### Architecture is Sound ✅

- ONE `session_id` field in database
- ONE UUID shared between Obra and Claude
- Clean separation of concerns (Obra owns lifecycle)

### Implementation Has Gap ❌

- Fresh sessions mode bypasses session creation
- Agent generates UUID that's not in database
- `update_session_usage()` fails on lookup

### Fix is Straightforward ✅

- Create temporary Obra session for standalone `execute_task()` calls
- Share Obra's UUID with agent
- Agent reports same UUID back in metadata
- Database updates work correctly

### Key Insight 💡

**Session tracking (Obra) and session state persistence (Claude) are orthogonal concerns.**

We can:
- ALWAYS track sessions in Obra database (for metrics)
- OPTIONALLY persist Claude state (for context continuity)

Fresh sessions disable Claude state persistence but shouldn't disable Obra session tracking.

---

## Next Steps

1. **Implement Option A-Refined** (above)
2. **Update SessionRecord docstring** to clarify shared UUID
3. **Add integration test** for standalone `execute_task()`
4. **Document session architecture** in ARCHITECTURE.md

---

**Analysis Generated**: 2025-11-04
**Bug Reference**: BUG-PHASE4-002
**Recommendation**: Implement Option A-Refined with session tracking always on
