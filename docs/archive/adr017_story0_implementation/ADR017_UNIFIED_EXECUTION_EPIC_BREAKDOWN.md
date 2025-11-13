# Epic: Unified Execution Architecture (ADR-017)

**Epic ID**: TBD (assigned during creation)
**Version**: v1.7.0 - v1.7.1
**Priority**: HIGH (Technical Debt - Architectural Consistency)
**Estimated Duration**: 2-3 weeks (60-80 hours)
**Owner**: Omar
**Status**: Proposed

---

## Executive Summary

This epic addresses a critical architectural misalignment where the Natural Language (NL) command interface bypasses Obra's core multi-stage validation and quality control pipeline. Currently, Obra has two parallel execution paths with fundamentally different quality guarantees, violating the system's core value proposition of "autonomous development with intelligent oversight."

**Problem**:
- Task execution path → Full orchestration (validation, quality scoring, iterative improvement)
- Natural language path → Direct CRUD execution (no validation, no quality control)

**Solution**:
Unify both paths so ALL user inputs flow through the orchestrator's proven 8-step validation pipeline, while preserving the excellent NL parsing infrastructure from ADR-016.

---

## Business Value

### Current Pain Points
1. **Inconsistent Quality**: Users get different quality guarantees depending on interface used
2. **Architectural Drift**: Two execution paths = 2x maintenance burden + edge case complexity
3. **Trust Erosion**: Power users learn to avoid NL for critical operations
4. **Technical Debt Compounding**: Every new NL feature inherits the bypass problem

### Expected Benefits
1. **Consistent Quality**: All commands validated through multi-stage pipeline (95%+ success rate)
2. **Simplified Architecture**: Single execution model eliminates duplicate paths
3. **Enhanced Safety**: Destructive operations get human-in-the-loop confirmation
4. **Future-Proof**: NL features can leverage orchestration infrastructure (retry, dependencies, git)
5. **Reduced Maintenance**: ~40% less integration test surface area

### ROI Calculation
- **Investment**: 60-80 hours development + 20 hours testing
- **Return**:
  - ~200 hours/year saved on maintenance (dual path synchronization)
  - ~100 hours/year saved on bug fixes (inconsistent execution edge cases)
  - Enables v1.8+ NL features without architectural redesign

---

## Architecture Overview

### Current Architecture (v1.6.0)
```
User Input
    ↓
┌───────────────────────────────┐
│ Two Parallel Execution Paths  │
├───────────────────────────────┤
│                               │
│  PATH 1: Task Execution       │  PATH 2: NL Commands
│  /task execute 1              │  create epic for auth
│        ↓                      │        ↓
│  orchestrator.execute_task()  │  nl_processor.process()
│        ↓                      │        ↓
│  8-step validation pipeline   │  5-stage parsing
│        ↓                      │        ↓
│  Agent with quality control   │  Direct StateManager CRUD
│        ↓                      │        ↓
│  Iterative improvement        │  Single-shot execution
│        ↓                      │        ↓
│  Result with confidence       │  Result (no validation)
│                               │
└───────────────────────────────┘
```

### Target Architecture (v1.7.0)
```
User Input (any interface: CLI, NL, interactive)
    ↓
┌─────────────────────────────────────────────┐
│ Unified Entry Point: orchestrator           │
└─────────────────────────────────────────────┘
    ↓
Is Natural Language?
    ├─ YES → NL Parsing Pipeline (intent → task)
    │         ↓
    │    IntentToTaskConverter
    │         ↓
    │    Task object with NL context
    │         ↓
    └─ NO  → Task from CLI/API
         ↓
orchestrator.execute_task()
         ↓
┌─────────────────────────────────────────────┐
│ UNIFIED EXECUTION PIPELINE (8 steps)        │
├─────────────────────────────────────────────┤
│ 1. Context Building (ContextManager)        │
│ 2. Prompt Generation (StructuredPromptBuilder)│
│ 3. Agent Execution (Claude Code)            │
│ 4. Response Validation (ResponseValidator)  │
│ 5. Quality Control (QualityController)      │
│ 6. Confidence Scoring (ConfidenceScorer)    │
│ 7. Decision Making (DecisionEngine)         │
│ 8. Action Handling (proceed/retry/escalate) │
└─────────────────────────────────────────────┘
         ↓
Result with full quality guarantees
```

### Key Architectural Changes

1. **NL Pipeline Role Change**:
   - **Before**: Intent Parser + Executor (does everything)
   - **After**: Intent Parser ONLY (generates Task objects)

2. **CommandExecutor Refactor**:
   - **Before**: `execute()` method calls StateManager directly
   - **After**: `build_query_context()` helper for read-only operations

3. **New Component**: `IntentToTaskConverter`
   - Converts parsed NL intent → Task object for orchestrator
   - Enriches task with NL context for agent understanding
   - Handles parameter mapping (NL params → Task fields)

4. **Safety Integration**:
   - Destructive operations trigger BreakpointManager
   - Human-in-the-loop confirmation before execution
   - Consistent with existing orchestrator checkpoint system

---

## Stories Breakdown

### Story 1: Architecture Documentation (ADR-017)
**Priority**: P0 (Prerequisite)
**Estimate**: 8 hours
**Assignee**: Claude Code

**Objective**: Document architectural decision and create design specifications

**Tasks**:
1. Create ADR-017 (Architecture Decision Record)
   - Problem statement (parallel execution paths)
   - Decision (unified orchestrator routing)
   - Consequences (breaking changes, benefits, risks)
   - Implementation approach

2. Update ARCHITECTURE.md
   - Add "Unified Execution Architecture" section
   - Update data flow diagrams
   - Document new components (IntentToTaskConverter)

3. Create migration guide
   - Changes for developers using Obra programmatically
   - Changes for NL command users (none visible)
   - Rollback procedure if needed

**Acceptance Criteria**:
- [ ] ADR-017 created in `docs/decisions/`
- [ ] ARCHITECTURE.md updated with v1.7.0 changes
- [ ] Migration guide created in `docs/guides/`
- [ ] All docs reviewed for accuracy and completeness

**Dependencies**: None

---

### Story 2: Create IntentToTaskConverter Component
**Priority**: P0 (Core Infrastructure)
**Estimate**: 12 hours
**Assignee**: Claude Code

**Objective**: Build component that converts parsed NL intent into Task objects for orchestrator

**Tasks**:
1. Create `src/orchestration/intent_to_task_converter.py`
   - Class: `IntentToTaskConverter`
   - Method: `convert(parsed_intent: OperationContext, project_id: int) -> Task`
   - Method: `_enrich_with_nl_context(task: Task, original_message: str) -> Task`
   - Method: `_map_parameters(op_context: OperationContext) -> Dict[str, Any]`

2. Implement conversion logic
   - CREATE operation → Create Task with title/description from parsed params
   - UPDATE operation → Create Task with "Update X" title + update instructions
   - DELETE operation → Create Task with "Delete X" title + safety context
   - QUERY operation → Create Task with "Show X" title + query parameters

3. Context enrichment
   - Include original NL message in task context
   - Add parsed entities as structured metadata
   - Include confidence scores from NL pipeline
   - Add flag: `source='natural_language'`

4. Parameter mapping
   - Map NL parameters to Task model fields
   - Handle epic_id, story_id, parent_task_id references
   - Validate required fields based on operation type

**Acceptance Criteria**:
- [ ] IntentToTaskConverter class implemented
- [ ] All 4 operation types (CREATE/UPDATE/DELETE/QUERY) supported
- [ ] Unit tests: 25+ tests covering all operation types and edge cases
- [ ] Code coverage: ≥90%
- [ ] Integration test: NL input → Task object → verified structure
- [ ] Documentation: Docstrings with examples for all public methods

**Dependencies**: None (can start immediately)

---

### Story 3: Refactor CommandExecutor → NLQueryHelper
**Priority**: P0 (Core Infrastructure)
**Estimate**: 10 hours
**Assignee**: Claude Code

**Objective**: Transform CommandExecutor from executor to query helper (read-only operations)

**Tasks**:
1. Rename and refactor
   - Rename: `CommandExecutor` → `NLQueryHelper`
   - Remove: All write operations (_execute_create, _execute_update, _execute_delete)
   - Keep: Query operations (_execute_query with hierarchical support)
   - Rename: `execute()` → `build_query_context()`

2. Update query methods
   - `build_query_context()` returns structured query metadata (not execution result)
   - Support: SIMPLE, HIERARCHICAL, NEXT_STEPS, BACKLOG, ROADMAP query types
   - Return: Dict with query type, filters, sort order, entity type

3. Deprecation handling
   - Add `@deprecated` decorator to old methods
   - Keep legacy methods in v1.7.0 with deprecation warnings
   - Schedule removal for v1.8.0

4. Update imports and references
   - Update `NLCommandProcessor` to use new API
   - Update tests to use new API
   - Update configuration references

**Acceptance Criteria**:
- [ ] CommandExecutor renamed to NLQueryHelper
- [ ] All write operations removed (create/update/delete)
- [ ] Query operations return metadata (not execution results)
- [ ] Legacy methods deprecated with warnings
- [ ] Unit tests updated: 30+ tests passing
- [ ] Code coverage: ≥90%
- [ ] Documentation: Updated docstrings and migration notes

**Dependencies**: None (parallel with Story 2)

---

### Story 4: Update NLCommandProcessor Routing
**Priority**: P0 (Integration)
**Estimate**: 10 hours
**Assignee**: Claude Code

**Objective**: Update NL pipeline to return ParsedIntent instead of executing commands

**Tasks**:
1. Update `process()` method signature
   - Change return type: `NLResponse` → `ParsedIntent` (new dataclass)
   - Remove execution logic from process()
   - Keep 5-stage parsing pipeline (ADR-016)

2. Create `ParsedIntent` dataclass
   ```python
   @dataclass
   class ParsedIntent:
       intent_type: str  # 'COMMAND' or 'QUESTION'
       operation_context: Optional[OperationContext]
       original_message: str
       confidence: float
       requires_execution: bool  # True for COMMAND, False for QUESTION
   ```

3. Update COMMAND path
   - Stages 1-4: Classification and extraction (unchanged)
   - Stage 5: Build OperationContext (unchanged)
   - NEW: Return ParsedIntent instead of calling executor

4. Update QUESTION path
   - Keep existing question handling
   - Return ParsedIntent with requires_execution=False
   - Include context for informational response

5. Update callers
   - `src/interactive.py`: Update `cmd_to_orch()` to handle ParsedIntent
   - Route COMMAND intents → IntentToTaskConverter → orchestrator.execute_task()
   - Route QUESTION intents → QuestionHandler (existing behavior)

**Acceptance Criteria**:
- [ ] ParsedIntent dataclass created
- [ ] NLCommandProcessor.process() returns ParsedIntent
- [ ] No execution logic in NLCommandProcessor
- [ ] All 5 ADR-016 stages still functional
- [ ] Unit tests updated: 40+ tests passing
- [ ] Integration test: NL message → ParsedIntent → verified structure
- [ ] Code coverage: ≥90%

**Dependencies**: Story 2 (needs IntentToTaskConverter)

---

### Story 5: Implement Unified Orchestrator Routing
**Priority**: P0 (Integration)
**Estimate**: 12 hours
**Assignee**: Claude Code

**Objective**: Route all NL commands through orchestrator.execute_task()

**Tasks**:
1. Update `src/interactive.py`
   - Modify `cmd_to_orch()` to use new routing
   - Get ParsedIntent from NLCommandProcessor
   - If COMMAND: Convert to Task → execute_task()
   - If QUESTION: Handle informational response (existing)

2. Update `Orchestrator` class
   - Add method: `execute_nl_task(parsed_intent: ParsedIntent, project_id: int) -> Dict`
   - Use IntentToTaskConverter to create Task
   - Call existing execute_task() with NL-sourced task
   - Add logging: "Executing NL-sourced task: {original_message}"

3. Handle NL-specific context
   - Detect `source='natural_language'` flag in task
   - Include parsed entities in prompt context
   - Add user's original message to agent prompt
   - Example: "User requested via natural language: 'create epic for auth'"

4. Update CLI integration
   - Add `--nl` flag to `obra task execute` for testing
   - Example: `obra task execute --nl "create epic for authentication"`
   - Useful for debugging NL routing without interactive mode

5. Error handling
   - Low confidence (<0.7) → Trigger clarification breakpoint
   - Validation failure → Same as regular task execution
   - Agent failure → Same retry logic as regular tasks

**Acceptance Criteria**:
- [ ] All NL commands route through orchestrator.execute_task()
- [ ] execute_nl_task() method implemented
- [ ] NL context included in agent prompts
- [ ] Error handling consistent with regular task execution
- [ ] CLI flag `--nl` implemented for testing
- [ ] Integration test: "create epic" → full orchestration → epic created
- [ ] Integration test: Low confidence → clarification checkpoint triggered
- [ ] Code coverage: ≥90% on new orchestrator methods

**Dependencies**: Story 2, Story 3, Story 4

---

### Story 6: Integration Testing for Unified Path
**Priority**: P0 (Quality Assurance)
**Estimate**: 16 hours
**Assignee**: Claude Code

**Objective**: Comprehensive testing of unified execution architecture

**Tasks**:
1. Create test file: `tests/integration/test_unified_execution.py`
   - Test: NL CREATE → orchestrator → validation → agent → epic created
   - Test: NL UPDATE → orchestrator → validation → agent → task updated
   - Test: NL DELETE → orchestrator → safety checkpoint → confirmation → deleted
   - Test: NL QUERY → orchestrator → NLQueryHelper → results returned

2. Quality validation tests
   - Test: NL command with low quality response → iterative improvement triggered
   - Test: NL command with validation failure → retry with refined prompt
   - Test: NL command with max iterations exceeded → escalation

3. Confidence and breakpoint tests
   - Test: Low confidence NL intent (<0.7) → clarification checkpoint
   - Test: Destructive NL operation → safety breakpoint before execution
   - Test: User confirmation required → interactive prompt shown

4. Context enrichment tests
   - Test: Original NL message included in agent prompt
   - Test: Parsed entities available to agent
   - Test: Confidence scores tracked through pipeline

5. Regression tests (ensure old functionality still works)
   - Test: Regular task execution (non-NL) unchanged
   - Test: Slash commands (/task execute) still work
   - Test: Epic/story execution unchanged

6. Performance tests
   - Measure: NL command latency (target: <3s for simple commands)
   - Measure: Memory overhead (target: <50MB additional)
   - Compare: v1.6.0 direct execution vs v1.7.0 orchestrated execution

7. End-to-end workflow tests
   - Test: "Create epic, add 3 stories, execute first story" (multi-turn NL)
   - Test: "Show workplan" → hierarchical query → formatted output
   - Test: "What's next for project 1?" → NEXT_STEPS query → prioritized tasks

**Acceptance Criteria**:
- [ ] 30+ integration tests created
- [ ] All tests passing (100% pass rate)
- [ ] Coverage: ≥85% on orchestration and NL integration paths
- [ ] Performance: NL commands complete in <3s (P95)
- [ ] No regressions: All existing tests still passing (770+ tests)
- [ ] Documentation: Test report summarizing results

**Dependencies**: Story 5

---

### Story 7: Documentation Updates
**Priority**: P1 (Release Blocker)
**Estimate**: 8 hours
**Assignee**: Claude Code

**Objective**: Update all documentation to reflect unified architecture

**Tasks**:
1. Update `CLAUDE.md`
   - Add Architecture Principle #15: "Unified Execution - All Commands Through Orchestrator"
   - Update Data Flow diagram to show NL → Task conversion
   - Add to "Common Pitfalls": ~~Don't bypass orchestrator~~ (RESOLVED in v1.7.0)
   - Update version to v1.7.0

2. Update `OBRA_SYSTEM_OVERVIEW.md`
   - Update "Core Capabilities" section with unified architecture
   - Update data flow diagrams (remove parallel paths)
   - Add "v1.7 Features" section documenting changes

3. Update `NL_COMMAND_GUIDE.md`
   - Add note: "All NL commands validated through orchestrator (v1.7.0+)"
   - Update latency expectations (~500ms increase due to validation)
   - Document quality guarantees for NL commands
   - Add troubleshooting section for validation failures

4. Update `CHANGELOG.md`
   - Add v1.7.0 section with breaking changes
   - Document architectural refactor (ADR-017)
   - List benefits and migration notes
   - Note: Internal breaking change (user-facing commands unchanged)

5. Update `ARCHITECTURE.md`
   - Remove "Two parallel execution paths" section
   - Add "Unified Execution Architecture (v1.7.0)" section
   - Update component interaction diagrams
   - Document IntentToTaskConverter component

6. Create `docs/guides/ADR017_MIGRATION_GUIDE.md`
   - For programmatic API users (if any)
   - For contributors working on NL features
   - Explain changes to NLCommandProcessor API
   - Provide code examples (before/after)

**Acceptance Criteria**:
- [ ] All 6 documentation files updated
- [ ] Version numbers updated to v1.7.0
- [ ] Migration guide created
- [ ] Diagrams updated to reflect new architecture
- [ ] All links verified (no broken references)
- [ ] Technical review completed

**Dependencies**: Story 6 (need test results for documentation)

---

### Story 8: Safety Enhancements - Destructive Operation Breakpoints
**Priority**: P1 (Safety Critical)
**Estimate**: 10 hours
**Assignee**: Claude Code
**Part of**: v1.7.1 (follow-up release)

**Objective**: Add human-in-the-loop confirmation for destructive NL operations

**Tasks**:
1. Update `BreakpointManager` rules
   - Add rule: `destructive_nl_operation`
   - Trigger conditions: operation=UPDATE/DELETE AND source=natural_language
   - Severity: HIGH (requires confirmation)

2. Implement confirmation workflow
   - In `orchestrator.execute_task()`: Check for destructive NL operations
   - Trigger breakpoint before agent execution
   - Interactive mode: Prompt user for confirmation
   - Non-interactive mode: Log warning and abort (safe default)

3. Update interactive mode UI
   - Display operation details: "About to UPDATE project 'Tetris' status → INACTIVE"
   - Show confirmation prompt: "Confirm destructive operation? (y/n/details)"
   - If 'details': Show full OperationContext
   - If 'y': Proceed with execution
   - If 'n': Abort task with TaskStoppedException

4. Add override mechanism
   - CLI flag: `--confirm-destructive` (skip confirmation, auto-approve)
   - Config option: `nl_commands.auto_confirm_destructive: false` (default)
   - For automation: Allow pre-approved destructive operations

5. Logging and audit trail
   - Log all destructive operations with user confirmation status
   - Include: timestamp, user, operation, entity, confirmation_method
   - Useful for security audits and debugging

**Acceptance Criteria**:
- [ ] BreakpointManager rule for destructive_nl_operation added
- [ ] Confirmation workflow implemented in orchestrator
- [ ] Interactive UI prompts user for confirmation
- [ ] Non-interactive mode aborts by default
- [ ] Override mechanism (CLI flag + config) implemented
- [ ] Audit logging for all destructive operations
- [ ] Unit tests: 15+ tests covering all confirmation scenarios
- [ ] Integration test: DELETE operation → confirmation prompt → user confirms → executed
- [ ] Integration test: DELETE operation → confirmation prompt → user declines → aborted
- [ ] Code coverage: ≥90%

**Dependencies**: Story 5 (needs unified routing first)

---

### Story 9: Confirmation Workflow UI Polish
**Priority**: P2 (User Experience)
**Estimate**: 6 hours
**Assignee**: Claude Code
**Part of**: v1.7.1 (follow-up release)

**Objective**: Enhance confirmation UX with rich context and safety warnings

**Tasks**:
1. Rich confirmation prompts
   - Color-coded warnings (red for DELETE, yellow for UPDATE)
   - Show before/after state for UPDATE operations
   - Example: "project.status: ACTIVE → INACTIVE"
   - Show affected dependencies (if any)

2. Safety context
   - For DELETE: Show cascade implications ("Will also delete 5 child tasks")
   - For UPDATE: Show dependent entities that might be affected
   - Risk level indicator: LOW/MEDIUM/HIGH

3. Confirmation options
   - `y` / `yes` - Confirm and proceed
   - `n` / `no` - Abort operation
   - `d` / `details` - Show full operation details (OperationContext dump)
   - `s` / `simulate` - Dry-run (show what would happen, don't execute)

4. Help text
   - `/help-confirm` command during confirmation prompt
   - Explains options and safety considerations
   - Links to relevant documentation

5. Timeout handling
   - Default timeout: 60 seconds for confirmation
   - After timeout: Abort operation (safe default)
   - Configurable: `breakpoints.confirmation_timeout_seconds`

**Acceptance Criteria**:
- [ ] Rich confirmation prompts with color coding
- [ ] Before/after state shown for UPDATE operations
- [ ] Cascade implications shown for DELETE operations
- [ ] 4 confirmation options implemented (y/n/d/s)
- [ ] Simulate mode (dry-run) functional
- [ ] Timeout handling with safe default
- [ ] Help text available during confirmation
- [ ] User testing: 3 users test confirmation flow, gather feedback
- [ ] Documentation: Updated NL_COMMAND_GUIDE.md with confirmation screenshots

**Dependencies**: Story 8

---

## Testing Strategy

### Unit Tests
- **Target Coverage**: ≥90% on all new components
- **Total New Tests**: 120+ tests
  - IntentToTaskConverter: 25 tests
  - NLQueryHelper: 30 tests
  - NLCommandProcessor updates: 20 tests
  - Orchestrator routing: 15 tests
  - BreakpointManager rules: 15 tests
  - Confirmation workflow: 15 tests

### Integration Tests
- **Target Coverage**: ≥85% on execution paths
- **Total New Tests**: 40+ tests
  - End-to-end NL → orchestrator: 15 tests
  - Quality validation integration: 10 tests
  - Breakpoint integration: 8 tests
  - Regression tests: 7 tests

### Performance Tests
- **Latency**: NL commands <3s (P95)
- **Memory**: <50MB additional overhead
- **Throughput**: ≥40 NL commands/minute (down from 50, acceptable trade-off)

### Regression Tests
- **All 770+ existing tests must pass**
- **No breaking changes to user-facing commands**
- **Backward compatibility for CLI slash commands**

---

## Risks and Mitigations

### Risk 1: Latency Increase
**Impact**: Users notice slower NL commands
**Probability**: HIGH (inevitable due to full orchestration)
**Mitigation**:
- Set expectation in docs: "Quality validation adds ~500ms"
- Optimize hot paths (caching, async where possible)
- Provide fast path for low-risk operations (read-only queries)

### Risk 2: Breaking Changes for Programmatic Users
**Impact**: External code calling NLCommandProcessor breaks
**Probability**: LOW (Obra has minimal external users currently)
**Mitigation**:
- Keep legacy methods with deprecation warnings (v1.7.0)
- Remove legacy methods in v1.8.0 (6 months notice)
- Provide migration guide with code examples

### Risk 3: Test Coverage Gaps
**Impact**: Bugs in production due to untested edge cases
**Probability**: MEDIUM (complex integration, many execution paths)
**Mitigation**:
- Dedicated Story 6 for integration testing (16 hours)
- Real LLM integration tests (not just mocks)
- Regression testing of all 770+ existing tests

### Risk 4: User Confusion (Different Behavior)
**Impact**: Users expect fast NL commands, get validation delays
**Probability**: LOW (most users haven't used v1.6.0 NL extensively)
**Mitigation**:
- Clear communication in CHANGELOG and NL_COMMAND_GUIDE
- Emphasize benefits: "NL commands now have same quality as task execution"
- Provide feedback during execution: "Validating..." progress indicator

---

## Success Metrics

### Technical Metrics
- [ ] **100% of NL commands** route through orchestrator
- [ ] **0 direct StateManager calls** from NL pipeline (except NLQueryHelper read-only)
- [ ] **≥90% test coverage** on all new components
- [ ] **All 770+ existing tests** still passing (no regressions)
- [ ] **<3s latency (P95)** for NL commands

### Quality Metrics
- [ ] **Validation applied to 100% of NL commands**
- [ ] **Confidence scoring tracked** for all NL operations
- [ ] **Iterative improvement triggered** for low-quality NL responses
- [ ] **Safety breakpoints triggered** for destructive operations

### User Experience Metrics
- [ ] **0 user-visible breaking changes** (commands work identically)
- [ ] **Confirmation UX rated 4/5+** by test users
- [ ] **Documentation clarity rated 4/5+** by reviewers

### Architectural Metrics
- [ ] **1 execution path** (down from 2)
- [ ] **~40% reduction** in integration test surface area
- [ ] **Simplified codebase**: NL pipeline 300 lines smaller (executor → helper)

---

## Release Plan

### v1.7.0 Release (Stories 1-7)
**Release Date**: 3 weeks from epic start
**Scope**: Core architectural refactor

**Deliverables**:
- ✅ ADR-017 and updated architecture docs
- ✅ IntentToTaskConverter component
- ✅ NLQueryHelper (refactored CommandExecutor)
- ✅ Updated NLCommandProcessor routing
- ✅ Unified orchestrator routing
- ✅ 160+ new tests (120 unit + 40 integration)
- ✅ Updated documentation (6 files)

**Release Notes**:
```markdown
# v1.7.0 - Unified Execution Architecture

## Breaking Changes (Internal)
- NLCommandProcessor API changed (returns ParsedIntent, not NLResponse)
- CommandExecutor renamed to NLQueryHelper (write operations removed)

## New Features
- All NL commands validated through orchestrator's multi-stage pipeline
- Consistent quality guarantees across CLI and NL interfaces
- NL commands support iterative improvement and retry logic

## Benefits
- 35% token efficiency (inherited from orchestrator's structured prompts)
- Quality scoring and confidence tracking for NL commands
- Simplified architecture (single execution path)

## Migration
- User-facing commands unchanged (no migration needed)
- Programmatic API users: See ADR017_MIGRATION_GUIDE.md
```

### v1.7.1 Release (Stories 8-9)
**Release Date**: 1 week after v1.7.0
**Scope**: Safety enhancements

**Deliverables**:
- ✅ Destructive operation breakpoints
- ✅ Confirmation workflow with rich UI
- ✅ Simulate (dry-run) mode
- ✅ Audit logging for destructive operations

**Release Notes**:
```markdown
# v1.7.1 - Safety Enhancements

## New Features
- Human-in-the-loop confirmation for destructive NL operations
- Rich confirmation prompts with before/after state
- Simulate mode (dry-run) for destructive operations
- Audit logging for all destructive operations

## Configuration
- `nl_commands.auto_confirm_destructive: false` (default: prompt user)
- `breakpoints.confirmation_timeout_seconds: 60` (default: 60s)
```

---

## Rollback Plan

### If Critical Issues Found in v1.7.0

**Option 1: Emergency Patch**
- Fix critical bug within 24 hours
- Release v1.7.0.1 patch

**Option 2: Revert to v1.6.0**
- Git rollback: `git revert <v1.7.0-commit>`
- Re-release as v1.7.0-rollback
- Investigate issue, fix, re-release as v1.7.1

**Rollback Safety**:
- Database schema unchanged (no migrations)
- Configuration backward compatible (old config still works)
- User-facing commands unchanged (no relearning needed)

### Legacy Mode (Escape Hatch)

For v1.7.0, keep legacy NL execution as fallback:

```yaml
nl_commands:
  use_legacy_executor: false  # Set to true to bypass orchestrator (emergency only)
```

Remove this option in v1.8.0 after 3 months of v1.7.0 stability.

---

## Definition of Done

### For the Epic
- [ ] All 9 stories completed and accepted
- [ ] 160+ new tests passing (100% pass rate)
- [ ] All 770+ existing tests passing (no regressions)
- [ ] Code coverage: ≥90% on new components, ≥88% overall (maintained)
- [ ] Documentation updated (10 files)
- [ ] ADR-017 reviewed and approved
- [ ] User testing completed (confirmation workflow)
- [ ] Performance benchmarks met (<3s latency)
- [ ] v1.7.0 and v1.7.1 released

### For Each Story
- [ ] All tasks completed
- [ ] Unit tests written and passing
- [ ] Integration tests written and passing
- [ ] Code reviewed (self-review + automated checks)
- [ ] Documentation updated
- [ ] Acceptance criteria met

---

## Dependencies and Sequencing

**Critical Path**: Story 1 → 2 → 4 → 5 → 6 → 7 → 8 → 9

**Parallel Work Possible**:
- Story 2 (IntentToTaskConverter) || Story 3 (NLQueryHelper refactor)
- Story 7 (Documentation) can start after Story 6 (Integration tests)
- Story 8 (Breakpoints) can start after Story 5 (Orchestrator routing)

**Blocking Relationships**:
- Story 4 depends on Story 2 (needs IntentToTaskConverter)
- Story 5 depends on Stories 2, 3, 4 (needs all components ready)
- Story 6 depends on Story 5 (needs unified routing to test)
- Story 8 depends on Story 5 (needs unified routing first)
- Story 9 depends on Story 8 (needs confirmation framework first)

---

## Communication Plan

### Weekly Progress Updates
- **Audience**: Omar (product owner), team
- **Format**: Email/Slack summary
- **Contents**: Completed stories, blockers, next week's focus

### Documentation Reviews
- **Reviewers**: Omar (technical review), Claude Code (self-review)
- **Artifacts**: ADR-017, ARCHITECTURE.md, migration guide
- **Timeline**: During Story 1, before Story 2 starts

### User Testing
- **Participants**: 3 internal users (if available)
- **Focus**: Confirmation workflow UX (Story 9)
- **Timeline**: During v1.7.1 development

### Release Communication
- **Channels**: CHANGELOG.md, GitHub release notes, docs
- **Audience**: Obra users (current: primarily Omar, future: external users)
- **Timing**: On v1.7.0 and v1.7.1 release dates

---

## Notes and Assumptions

### Assumptions
1. **No external users**: Obra is currently single-user (Omar), so breaking internal APIs is acceptable
2. **Database schema stable**: No migrations needed for this refactor
3. **LLM availability**: Ollama/Qwen or OpenAI Codex available for testing
4. **Development environment**: WSL2 Ubuntu with full Obra stack

### Open Questions
1. Should we add telemetry for NL command success rates? (Deferred to v1.8)
2. Should we add A/B testing framework for v1.6 vs v1.7 NL? (Deferred, single user)
3. Should we support async execution for long-running NL commands? (Deferred to v1.8)

### Future Enhancements (Not in v1.7)
- Async NL command execution (for long operations)
- Multi-action NL commands ("create epic AND add 3 stories")
- Voice input integration (speech-to-text → NL pipeline)
- NL command history and replay
- Undo/redo for NL commands

---

**Last Updated**: 2025-11-12
**Epic Owner**: Omar
**Epic Status**: Proposed (awaiting approval)
