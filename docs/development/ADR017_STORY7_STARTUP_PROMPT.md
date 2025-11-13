# ADR-017 Story 7 Startup Prompt

**Context**: You're implementing ADR-017 (Unified Execution Architecture) for Obra. Stories 0-6 are complete. Now implement Story 7.

---

## What You're Building

**Story 7**: Documentation Updates (8 hours)

**Purpose**: Update all user-facing documentation to reflect the unified execution architecture and provide migration guidance for internal API changes.

**Key Objectives**:
- Update user guides with new unified architecture
- Update API documentation for internal changes
- Update CHANGELOG.md for v1.7.0 release
- Create migration guide for developers
- Update architecture diagrams
- Document breaking changes (if any)
- Update README if needed

---

## What's Already Complete

### Story 0: Testing Infrastructure ✅
- Health checks, smoke tests, integration tests framework
- THE CRITICAL TEST baseline established

### Story 1: Architecture Documentation ✅
- ADR-017 written and approved
- Architecture diagrams completed

### Story 2: IntentToTaskConverter ✅
- **Component**: `src/orchestration/intent_to_task_converter.py`
- **Function**: Converts `OperationContext` → `Task` objects
- **Tests**: 32 tests, 93% coverage

### Story 3: NLQueryHelper ✅
- **Component**: `src/nl/nl_query_helper.py`
- **Function**: Query-only operations (read-only)
- **Tests**: 17 tests, 97% coverage

### Story 4: NLCommandProcessor Routing ✅
- **Changes**: Returns `ParsedIntent` instead of `NLResponse`
- **New Type**: `ParsedIntent` dataclass
- **Tests**: 18 tests for ParsedIntent structure

### Story 5: Unified Orchestrator Routing ✅
- **Component**: `src/orchestrator.py::execute_nl_command()`
- **Integration**: Routes ALL NL commands through orchestrator
- **Components**: IntentToTaskConverter and NLQueryHelper initialized
- **Tests**: 12 new integration tests, E2E test updated

### Story 6: Integration Testing ✅
- **NL Integration Tests**: 12/12 passing (100%) ✅
- **E2E Test**: Executes successfully (task created, quality 0.84, completed) ✅
- **Regression Tests**: 8/8 passing (backward compatibility validated) ✅
- **Performance Tests**: 4/4 passing (latency < 3s P95, throughput > 40 cmd/min) ✅
- **Total New Tests**: 24 tests added

---

## The Problem

Story 6 integration testing is complete and ADR-017 unified execution architecture is functionally validated. However, documentation is now outdated:

1. **User guides** still describe the old NL command flow
2. **API documentation** doesn't reflect internal API changes
3. **CHANGELOG.md** needs v1.7.0 entry
4. **No migration guide** for developers using internal APIs
5. **Architecture diagrams** may need updates
6. **README** may need updates for new capabilities

Additionally:
- Need to document any breaking changes for internal APIs
- Need to update configuration examples if applicable
- Need to update NL command guide with unified routing behavior

---

## The Solution

**Documentation Update Strategy**:
```
1. Identify all documentation that needs updates
   ↓
2. Update user-facing guides (NL commands, workflow)
   ↓
3. Update internal API documentation
   ↓
4. Create migration guide for developers
   ↓
5. Update CHANGELOG.md for v1.7.0
   ↓
6. Update architecture diagrams if needed
   ↓
7. Update README if needed
   ↓
8. Review and validate all documentation changes
```

---

## Implementation Plan

### Step 1: Identify Documentation That Needs Updates

**Action**: Create a checklist of all documentation files to update

**Files to Review**:
```bash
# User guides
docs/guides/NL_COMMAND_GUIDE.md
docs/guides/AGILE_WORKFLOW_GUIDE.md
docs/guides/CONFIGURATION_PROFILES_GUIDE.md

# Architecture docs
docs/architecture/ARCHITECTURE.md
docs/design/OBRA_SYSTEM_OVERVIEW.md

# Decision records
docs/decisions/ADR-017-unified-execution-architecture.md

# Development docs
docs/development/TEST_GUIDELINES.md
docs/development/INTERACTIVE_STREAMING_QUICKREF.md

# Root docs
README.md
CHANGELOG.md
CLAUDE.md
```

**Create Checklist**:
```markdown
- [ ] NL_COMMAND_GUIDE.md - Update NL command flow diagram
- [ ] AGILE_WORKFLOW_GUIDE.md - Update if epic/story execution changed
- [ ] ARCHITECTURE.md - Add unified routing section
- [ ] OBRA_SYSTEM_OVERVIEW.md - Update data flow diagram
- [ ] CHANGELOG.md - Add v1.7.0 entry
- [ ] ADR-017 - Mark as IMPLEMENTED
- [ ] README.md - Update if needed
- [ ] CLAUDE.md - Add ADR-017 to architecture principles
```

### Step 2: Update NL Command Guide

**File**: `docs/guides/NL_COMMAND_GUIDE.md`

**Changes Needed**:
1. Update "How It Works" section to show unified routing
2. Add diagram showing: `NLCommandProcessor → ParsedIntent → Orchestrator.execute_nl_command() → IntentToTaskConverter/NLQueryHelper`
3. Update example flows to show new routing
4. Document that ALL NL commands now go through orchestrator validation pipeline

**Old Flow**:
```
NLCommandProcessor → EntityExtractor → CommandValidator → CommandExecutor → StateManager
```

**New Flow**:
```
NLCommandProcessor → ParsedIntent → Orchestrator.execute_nl_command()
  ↓
  ├─ QUERY → NLQueryHelper → StateManager (read-only)
  └─ COMMAND → IntentToTaskConverter → Task → Full Orchestration Pipeline
```

### Step 3: Update Architecture Documentation

**File**: `docs/architecture/ARCHITECTURE.md`

**Changes Needed**:
1. Add "Unified Execution Architecture (ADR-017)" section
2. Update data flow diagram to show NL routing through orchestrator
3. Document IntentToTaskConverter and NLQueryHelper components
4. Update component interaction diagrams

**New Section**:
```markdown
## Unified Execution Architecture (ADR-017)

All Natural Language commands route through the orchestrator's unified execution pipeline,
ensuring consistent validation, quality scoring, and confidence tracking.

### Components:
- **IntentToTaskConverter**: Converts OperationContext → Task objects
- **NLQueryHelper**: Handles query-only operations (no task creation)
- **Orchestrator.execute_nl_command()**: Unified entry point for all NL commands

### Benefits:
- Consistent quality control for all commands
- Unified validation pipeline
- Single entry point for monitoring and metrics
- Simplified testing and debugging
```

### Step 4: Create Migration Guide

**New File**: `docs/guides/ADR017_MIGRATION_GUIDE.md`

**Content**:
```markdown
# ADR-017 Migration Guide

## Internal API Changes

### Breaking Changes

**None** - All user-facing APIs remain unchanged.

### Internal API Changes (for contributors)

#### 1. IntentToTaskConverter.convert() Signature

**Old** (Story 5 initial):
```python
task = converter.convert(
    operation_context=context,  # WRONG
    project_id=1,
    confidence=0.95  # WRONG
)
```

**New** (Story 6 corrected):
```python
task = converter.convert(
    parsed_intent=context,  # Correct parameter name
    project_id=1,
    original_message="create task..."  # Required
    # confidence removed - stored in OperationContext
)
```

#### 2. NLCommandProcessor Initialization

**Old**:
```python
processor = NLCommandProcessor(
    state_manager=sm,
    llm_plugin=llm
)
```

**New**:
```python
processor = NLCommandProcessor(
    llm_plugin=llm,  # Order changed
    state_manager=sm,
    config=config  # New required parameter
)
```

### Non-Breaking Changes

#### StateManager API (unchanged)

All StateManager CRUD methods remain unchanged:
- `create_task(project_id, task_data={...})`
- `create_epic(project_id, title, description, **kwargs)`
- `create_story(project_id, epic_id, title, description, **kwargs)`

These were **not** changed by ADR-017.

### Migration Checklist

If you have custom code using internal APIs:

- [ ] Check IntentToTaskConverter calls - update parameter names
- [ ] Check NLCommandProcessor initialization - add config parameter
- [ ] Test fixtures - ensure shared StateManager for database isolation
- [ ] LLM mocks - ensure `is_available()` method is mocked
- [ ] Update any custom orchestrator integrations

### Testing Your Code

Run integration tests to validate:
```bash
pytest tests/integration/test_adr017_regression.py -v
```

All 8 regression tests should pass, confirming backward compatibility.
```

### Step 5: Update CHANGELOG.md

**File**: `CHANGELOG.md`

**Add v1.7.0 Entry**:
```markdown
## [1.7.0] - 2025-11-13

### Added
- **Unified Execution Architecture (ADR-017)**: All NL commands now route through orchestrator for consistent validation
  - IntentToTaskConverter component for OperationContext → Task conversion
  - NLQueryHelper component for query-only operations
  - Unified `execute_nl_command()` entry point in orchestrator
  - 12 new integration tests for NL routing (100% passing)
  - 8 regression tests for backward compatibility (100% passing)
  - 4 performance tests validating latency < 3s P95 (100% passing)

### Changed
- **Internal API**: IntentToTaskConverter.convert() parameter names (see migration guide)
- **Internal API**: NLCommandProcessor requires config parameter (see migration guide)
- E2E test updated to validate unified NL routing through orchestrator

### Performance
- P50 latency: < 2s for NL commands ✅
- P95 latency: < 3s for NL commands ✅
- Throughput: > 40 commands/minute ✅
- NL routing overhead: < 500ms vs direct access ✅

### Documentation
- Added ADR-017 migration guide for internal API changes
- Updated NL command guide with unified routing flow
- Updated architecture documentation with new components

### Tests
- **Total Tests Added**: 24 (12 integration + 8 regression + 4 performance)
- **All Tests Passing**: 794+ tests (770 existing + 24 new)
- **Coverage**: Maintained at 88%

### Fixed
- Database isolation in integration tests (shared StateManager fixture)
- LLM mocking in test fixtures (added is_available() mock)
- File watcher directory creation in test fixtures
- NLCommandProcessor initialization in E2E tests

[1.7.0]: https://github.com/Omar-Unpossible/claude_code_orchestrator/compare/v1.6.0...v1.7.0
```

### Step 6: Update README (If Needed)

**File**: `README.md`

**Check if Updates Needed**:
- Does README mention NL command architecture?
- Are there examples showing old NL flow?
- Do we need to highlight unified routing as a feature?

**Potential Addition** (if not already there):
```markdown
## Unified Execution Architecture

All Natural Language commands route through Obra's orchestration pipeline,
ensuring consistent quality control and validation:

- **IntentToTaskConverter**: Converts NL intents to executable tasks
- **NLQueryHelper**: Handles query-only operations efficiently
- **Unified Pipeline**: Quality scoring, confidence tracking, validation for all commands

Performance: <3s latency (P95), >40 commands/minute throughput.
```

### Step 7: Update CLAUDE.md

**File**: `CLAUDE.md`

**Add to Architecture Principles**:
```markdown
### 15. Unified Execution Architecture (v1.7.0 - ADR-017)
**All NL commands route through orchestrator for consistent validation:**

- **Architecture**: Single entry point `execute_nl_command()` routes all NL commands
- **Components**:
  - `IntentToTaskConverter`: Converts OperationContext → Task objects
  - `NLQueryHelper`: Handles query-only operations (no task creation)
- **Pipeline**: NLCommandProcessor → ParsedIntent → Orchestrator → Validation Pipeline

- **Benefits**:
  - Consistent quality control for all NL commands
  - Unified validation and scoring
  - Single entry point for monitoring
  - Simplified testing (24 new tests)

- **Performance** (validated in Story 6):
  - P50 latency: < 2s
  - P95 latency: < 3s
  - Throughput: > 40 cmd/min
  - Overhead: < 500ms vs direct access

**See**: `docs/guides/ADR017_MIGRATION_GUIDE.md` for internal API changes
**See**: `docs/decisions/ADR-017-unified-execution-architecture.md` for architecture
```

### Step 8: Mark ADR-017 as Implemented

**File**: `docs/decisions/ADR-017-unified-execution-architecture.md`

**Update Status Section**:
```markdown
## Status

**IMPLEMENTED** - November 13, 2025

Implementation completed across Stories 0-6:
- Story 2: IntentToTaskConverter (32 tests, 93% coverage) ✅
- Story 3: NLQueryHelper (17 tests, 97% coverage) ✅
- Story 4: NLCommandProcessor routing (18 tests) ✅
- Story 5: Orchestrator integration (12 integration tests) ✅
- Story 6: Integration testing (24 tests total, all passing) ✅
- Story 7: Documentation updates ✅

**Test Results**:
- NL Integration Tests: 12/12 ✅
- E2E Test: Passing (task execution validated) ✅
- Regression Tests: 8/8 ✅
- Performance Tests: 4/4 ✅

**Version**: v1.7.0
```

---

## Acceptance Criteria

✅ **Documentation Updated**:
- [ ] NL_COMMAND_GUIDE.md updated with unified routing flow
- [ ] ARCHITECTURE.md updated with ADR-017 section
- [ ] OBRA_SYSTEM_OVERVIEW.md data flow diagram updated
- [ ] ADR-017 marked as IMPLEMENTED
- [ ] CLAUDE.md updated with unified architecture principle

✅ **Migration Guide**:
- [ ] ADR017_MIGRATION_GUIDE.md created
- [ ] Breaking changes documented (none for users)
- [ ] Internal API changes documented
- [ ] Migration checklist provided

✅ **CHANGELOG**:
- [ ] v1.7.0 entry added
- [ ] All features, changes, and fixes documented
- [ ] Performance results included
- [ ] Test results summary included

✅ **README** (if applicable):
- [ ] Updated with unified architecture feature
- [ ] Examples updated if needed
- [ ] No outdated information

✅ **Review**:
- [ ] All documentation changes reviewed for accuracy
- [ ] All code examples tested
- [ ] All links verified
- [ ] No broken references

---

## Validation Commands

**Check documentation consistency**:
```bash
# Verify all ADR-017 references are consistent
grep -r "ADR-017" docs/

# Check for outdated references to old NL flow
grep -r "CommandExecutor" docs/ | grep -v "archive"

# Verify CHANGELOG version
grep "1.7.0" CHANGELOG.md
```

**Validate code examples in docs**:
```bash
# Extract and test code examples (if applicable)
# Ensure all documented APIs actually exist
```

---

## Key Design Decisions

### Decision 1: How Much Internal API Detail to Document?

**Options**:
1. Document all internal API changes in detail
2. Only document user-facing changes
3. Hybrid: Brief internal changes + detailed migration guide

**Choice**: Option 3 (Hybrid)

**Rationale**:
- Users don't need internal API details
- Contributors need migration guidance
- Separate migration guide keeps user docs clean

### Decision 2: Should We Update All Architecture Diagrams?

**Options**:
1. Regenerate all diagrams
2. Only update affected diagrams
3. Add new diagrams, keep old ones with "legacy" note

**Choice**: Option 2 (Only update affected)

**Rationale**:
- Most diagrams unchanged
- Updating unnecessary diagrams risks introducing errors
- Focus on NL routing and data flow diagrams

### Decision 3: Version Number - 1.7.0 or 2.0.0?

**Options**:
1. v1.7.0 (minor version bump)
2. v2.0.0 (major version bump)

**Choice**: v1.7.0 (minor version)

**Rationale**:
- No breaking changes for users
- Internal API changes don't affect user code
- Backward compatible (proven by regression tests)
- Major version for user-facing breaking changes only

---

## Common Pitfalls to Avoid

1. ❌ **Don't forget to update CLAUDE.md**: This is critical for future AI sessions
2. ❌ **Don't leave ADR-017 status as "Accepted"**: Must mark as "IMPLEMENTED"
3. ❌ **Don't skip migration guide**: Contributors need this for internal API changes
4. ❌ **Don't forget CHANGELOG**: Users depend on this for upgrade decisions
5. ❌ **Don't update docs without testing examples**: All code examples must work
6. ❌ **Don't break existing documentation links**: Verify all references
7. ❌ **Don't leave outdated architecture diagrams**: Update or remove

---

## References

**Key Files**:
- `docs/guides/NL_COMMAND_GUIDE.md` - User guide for NL commands
- `docs/architecture/ARCHITECTURE.md` - System architecture
- `docs/design/OBRA_SYSTEM_OVERVIEW.md` - System overview
- `CHANGELOG.md` - Version history
- `CLAUDE.md` - AI session instructions
- `README.md` - Project overview

**Implementation Files** (for code examples):
- `src/orchestrator.py` - execute_nl_command() implementation
- `src/orchestration/intent_to_task_converter.py` - IntentToTaskConverter
- `src/nl/nl_query_helper.py` - NLQueryHelper
- `src/nl/nl_command_processor.py` - NLCommandProcessor

**Test Files** (for validation):
- `tests/integration/test_orchestrator_nl_integration.py` - NL routing tests
- `tests/integration/test_adr017_regression.py` - Backward compatibility
- `tests/integration/test_adr017_performance.py` - Performance validation

---

## Upon Completion of Story 7

**Status**: ADR-017 FULLY COMPLETE!

After Story 7, you will have:
- ✅ All Stories 0-7 complete
- ✅ All 24 integration/regression/performance tests passing
- ✅ All documentation updated and accurate
- ✅ Migration guide for contributors
- ✅ CHANGELOG.md ready for v1.7.0 release
- ✅ Production-ready unified execution architecture

**Next Steps**: Prepare for v1.7.0 release
- Tag release in git
- Create release notes
- Update project version numbers
- Announce unified execution architecture

---

**Ready to start? Implement Story 7: Documentation Updates.**

Remember:
- Update user guides with unified routing flow
- Create migration guide for internal API changes
- Update CHANGELOG.md with comprehensive v1.7.0 entry
- Mark ADR-017 as IMPLEMENTED
- Update CLAUDE.md with new architecture principle
- Review all documentation for accuracy and consistency
