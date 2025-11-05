# Headless Mode Enhancement - Executive Summary

**Plan Document**: `HEADLESS_MODE_ENHANCEMENT_PLAN.yaml`
**Version**: v1.2 → v1.3
**Status**: APPROVED - Ready for Implementation
**Estimated Effort**: 4-5 weeks (110-136 hours)

---

## 🎯 Objective

Enhance Obra's Claude Code integration with production-ready session management, context window handling, and intelligent max_turns control to enable safe session persistence.

---

## 📊 Quick Stats

| Metric | Value |
|--------|-------|
| **Total Duration** | 4-5 weeks |
| **Total Effort** | 110-136 hours |
| **Phases** | 5 phases |
| **Files Created** | ~15 new files |
| **Files Modified** | ~10 existing files |
| **Database Migrations** | 2-3 migrations |
| **Test Coverage Target** | >85% |

---

## 🚀 5 Phases Overview

### Phase 1: Foundation - JSON Output & Testing (Week 1)
**Effort**: 24-30 hours | **Priority**: CRITICAL

**Goal**: Implement JSON output mode and discover Claude Code's capabilities

**Key Tasks**:
1. Test Claude Code JSON responses to document available fields
2. Update AgentResponse model with token/performance fields
3. Implement JSON parsing in ClaudeCodeLocalAgent
4. Comprehensive testing

**Deliverables**:
- JSON response schema documentation
- AgentResponse with metadata fields
- JSON parsing implementation
- **Decision**: Does Claude provide context window %? (impacts Phase 3)

**Success Criteria**:
- ✅ JSON parsing works for all responses
- ✅ Metadata extracted and stored
- ✅ Context window availability determined
- ✅ Tests pass >90% coverage

---

### Phase 2: Session Management (Week 2)
**Effort**: 24-30 hours | **Priority**: HIGH

**Goal**: Implement milestone-based session lifecycle

**Key Tasks**:
1. Session lifecycle in Orchestrator (start/end milestone sessions)
2. Session summary generation using Qwen
3. Database schema for session tracking
4. Inject milestone context into task execution

**Deliverables**:
- `execute_milestone()` with session management
- Session summaries generated
- Workplan context injection
- Database migration for sessions table

**Success Criteria**:
- ✅ Milestone-based sessions working
- ✅ Workplan context injected
- ✅ Session summaries generated
- ✅ Tests pass >85% coverage

---

### Phase 3: Context Window Management (Week 3)
**Effort**: 12-36 hours (depends on Phase 1 decision) | **Priority**: CRITICAL

**Goal**: Track context window usage and auto-refresh at thresholds

**Two Implementation Paths**:
- **Path A** (if Claude provides context %): 12-16 hours - Read from JSON
- **Path B** (if not provided): 30-36 hours - Manual token tracking

**Key Tasks**:
1. Threshold checks (70% warning, 80% refresh, 95% critical)
2. Session refresh mechanism with summary
3. Emergency handling (task decomposition)
4. Configuration for thresholds

**Deliverables**:
- Context window tracking (Claude or manual)
- Auto-refresh at 80%
- Emergency handling at 95%
- Database migration (if Path B)

**Success Criteria**:
- ✅ Context tracking implemented
- ✅ Threshold warnings working
- ✅ Auto-refresh tested
- ✅ No unexpected context errors
- ✅ Tests pass >85% coverage

---

### Phase 4: Dynamic Max Turns (Week 4)
**Effort**: 20-24 hours | **Priority**: MEDIUM-HIGH

**Goal**: Adaptive max_turns calculation with auto-retry

**Key Tasks**:
1. Implement MaxTurnsCalculator (based on guide)
2. Auto-retry on error_max_turns
3. Integration with Orchestrator
4. Configuration

**Deliverables**:
- MaxTurnsCalculator class
- Adaptive calculation (3-30 turns based on complexity)
- Auto-retry with doubled limit
- Task type overrides

**Success Criteria**:
- ✅ Adaptive calculation working
- ✅ Task type overrides functional
- ✅ Auto-retry on error_max_turns
- ✅ Tests pass >85% coverage

---

### Phase 5: Timeouts & Polish (Week 5)
**Effort**: 12-16 hours | **Priority**: MEDIUM

**Goal**: Extended timeouts, logging, and documentation

**Key Tasks**:
1. Increase timeout to 7200s (2 hours)
2. Comprehensive logging
3. Write documentation (guides + ADR)
4. Integration testing
5. Configuration validation

**Deliverables**:
- 2-hour timeout
- Detailed logging
- SESSION_MANAGEMENT_GUIDE.md
- HEADLESS_MODE_IMPLEMENTATION.md
- ADR-007
- Integration tests

**Success Criteria**:
- ✅ 2-hour timeout configured
- ✅ Logging comprehensive
- ✅ Documentation complete
- ✅ Integration tests pass

---

## 🔑 Key Features Delivered

### 1. JSON Output Mode
- Structured responses from Claude Code
- Token usage tracking (input, cache, output)
- Performance metrics (duration, turns)
- Error subtypes (error_max_turns, etc.)

### 2. Milestone-Based Sessions
- Session created at milestone start
- Workplan context injected
- Session persists across all milestone tasks
- Summary generated at milestone end
- Next milestone gets previous summary

### 3. Context Window Management
- Track cumulative token usage per session
- **70% threshold**: Warning logged
- **80% threshold**: Auto-refresh (summarize + new session)
- **95% threshold**: Emergency handling (decompose or force refresh)
- Configurable limits (default 200k tokens)

### 4. Dynamic Max Turns
- Adaptive calculation based on task complexity:
  - Simple (3 turns): Single file, specific fix
  - Medium (6 turns): Small feature, module refactor
  - Complex (12 turns): Complete feature, multi-file
  - Very Complex (20 turns): Large refactor, migrations
- Task type overrides (validation=5, debugging=20, etc.)
- Auto-retry on error_max_turns with doubled limit
- Safety bounds (3-30 turns)

### 5. Extended Timeouts
- 2-hour timeout for complex workflows
- Max turns prevents runaway loops (semantic limit)
- Timeout catches hangs/crashes (technical failures)

---

## 📋 Database Changes

### New Tables
1. **sessions** - Track session lifecycle
   - session_id, milestone_id, started_at, ended_at, summary, status

2. **context_window_usage** - Token tracking (if Path B)
   - session_id, task_id, cumulative_tokens, breakdown, timestamp

### Modified Tables
1. **agent_responses** - Add JSON metadata fields
   - Token fields: input_tokens, cache_creation_tokens, cache_read_tokens, output_tokens
   - Context: context_window_used, context_window_limit, context_window_pct
   - Performance: duration_ms, duration_api_ms, num_turns
   - Session: session_id, error_subtype, cost_usd

---

## 📦 Files Created (~15 files)

### Code
- `src/orchestration/max_turns_calculator.py`
- `alembic/versions/xxx_add_agent_response_json_fields.py`
- `alembic/versions/xxx_add_session_management.py`
- `alembic/versions/xxx_add_context_window_tracking.py` (if Path B)

### Tests
- `tests/agents/test_claude_code_local_json.py`
- `tests/integration/test_milestone_sessions.py`
- `tests/orchestration/test_context_window_management.py`
- `tests/orchestration/test_max_turns_calculator.py`
- `tests/orchestration/test_max_turns_retry.py`
- `tests/integration/test_full_milestone_execution.py`

### Documentation
- `docs/research/claude-code-json-response-schema.md`
- `docs/guides/SESSION_MANAGEMENT_GUIDE.md`
- `docs/development/HEADLESS_MODE_IMPLEMENTATION.md`
- `docs/decisions/ADR-007-headless-mode-enhancements.md`
- `config/config.example.yaml`

---

## 🔧 Configuration Example

```yaml
# Session Management
session:
  context_window:
    limit: 200000  # Claude Pro default
    thresholds:
      warning: 0.70   # 140k - log warning
      refresh: 0.80   # 160k - auto-refresh
      critical: 0.95  # 190k - emergency handling
    refresh_strategy:
      method: "summarize_and_continue"
      include_workplan: true
      max_summary_tokens: 5000
    decomposition:
      enabled: true
      max_subtasks: 5

# Max Turns
orchestration:
  max_turns:
    adaptive: true
    default: 10
    by_task_type:
      validation: 5
      code_generation: 12
      refactoring: 15
      debugging: 20
    min: 3
    max: 30
    auto_retry: true
    max_retries: 1
    retry_multiplier: 2

# Agent Timeout
agent:
  config:
    response_timeout: 7200  # 2 hours
```

---

## ⚠️ Critical Decisions

### Decision 1: Context Window Tracking Method (Phase 1)
**Question**: Does Claude Code provide context window % in JSON responses?

**Option A** (Claude provides it):
- Effort: 12-16 hours
- Implementation: Read from JSON response
- Risk: Low (simpler)

**Option B** (Manual tracking needed):
- Effort: 30-36 hours
- Implementation: Track cumulative tokens in database
- Risk: Medium (more complex, potential sync issues)

**Timeline Impact**: 18-20 hour difference between paths

---

## 🎯 Success Criteria

### Functional
- ✅ JSON parsing works for all Claude Code responses
- ✅ Session persistence enabled without crashes
- ✅ Context window never exceeds limit unexpectedly
- ✅ Tasks complete with appropriate turn limits
- ✅ 2-hour timeout supports complex workflows

### Technical
- ✅ All tests pass with >85% coverage
- ✅ No regressions in performance
- ✅ Database migrations successful
- ✅ Configuration validation working

### Documentation
- ✅ User guide complete and clear
- ✅ Technical implementation documented
- ✅ ADR-007 written
- ✅ README and CLAUDE.md updated

---

## 📅 Timeline

```
Week 1: Foundation (JSON Output & Testing)
├─ Test Claude Code JSON responses
├─ Implement JSON parsing
├─ Update AgentResponse model
└─ DECISION: Path A vs B for Phase 3

Week 2: Session Management
├─ Milestone-based session lifecycle
├─ Session summary generation
├─ Database migration
└─ Context injection

Week 3: Context Window Management
├─ Implement Path A or B (based on Week 1 decision)
├─ Threshold checks
├─ Auto-refresh mechanism
└─ Emergency handling

Week 4: Dynamic Max Turns
├─ MaxTurnsCalculator implementation
├─ Auto-retry logic
├─ Integration
└─ Configuration

Week 5: Polish
├─ Extended timeouts
├─ Comprehensive logging
├─ Documentation
└─ Integration testing
```

---

## 🚧 Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| JSON parsing failures | HIGH | Comprehensive error handling, fallback to text |
| Context refresh interrupts work | MEDIUM | Detailed summaries, extensive continuity testing |
| Max turns retries burn tokens | MEDIUM | Limit retries to 1, enforce 30-turn cap |
| Manual token tracking out of sync | MEDIUM | Validation, threshold buffers |
| 2-hour timeout insufficient | LOW | Configurable, max_turns prevents runaway |
| Database migrations fail | MEDIUM | Test in dev/staging, backups |

---

## ✅ Ready to Proceed

This plan is **APPROVED** and ready for implementation. The detailed machine-optimized plan is available in:

📄 **`docs/development/HEADLESS_MODE_ENHANCEMENT_PLAN.yaml`**

### Next Steps:
1. Review detailed YAML plan
2. Create GitHub issues/tasks for each phase
3. Set up development branch (`feature/headless-enhancements`)
4. Begin Phase 1 testing (TASK 1.1)

### Phase 1 First Task:
**Test Claude Code JSON responses** to determine Path A vs Path B for Phase 3.

```bash
# Test command
claude -p "Simple task" --output-format json --session-id test-001

# Document all fields in:
# docs/research/claude-code-json-response-schema.md
```

---

**Plan Version**: 1.0
**Created**: 2025-11-03
**Status**: APPROVED
**Target Version**: v1.3-headless-enhancements
