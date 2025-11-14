# Claude Startup Prompt: NL Bulk Operations Implementation

## Task Overview

Implement bulk/batch operations for the Natural Language command processor to fix the error:

```
ValueError: delete operation requires an identifier
```

**User command that failed**: `"delete all epics stories and tasks for this project"`

## What You Need to Do

1. **Read the implementation guide**: `/home/omarwsl/projects/claude_code_orchestrator/docs/development/NL_BULK_OPERATIONS_IMPLEMENTATION.md`

2. **Follow the 10-step implementation sequence** in the guide:
   - STEP 1: Bulk Identifier Detection (1 hour)
   - STEP 2: OperationContext Validation (1 hour)
   - STEP 3: BulkCommandExecutor (3 hours)
   - STEP 4: StateManager Bulk Methods (2 hours)
   - STEP 5: Multi-Entity Type Classification (2 hours)
   - STEP 6: IntentToTaskConverter Integration (1 hour)
   - STEP 7: Parameter Extraction Enhancement (1 hour)
   - STEP 8: NLCommandProcessor Integration (1 hour)
   - STEP 9: Integration Tests (2 hours)
   - STEP 10: Documentation Updates (1 hour)

3. **Write tests as you go** (TDD approach):
   - Each step includes test code in the implementation guide
   - Run tests after each step to validate
   - Target: ≥90% coverage for new components

4. **Test coverage requirements**:
   - Follow `/home/omarwsl/projects/claude_code_orchestrator/docs/testing/TEST_GUIDELINES.md`
   - ⚠️ Max sleep per test: 0.5s (use `fast_time` fixture if needed)
   - ⚠️ Max threads per test: 5 (with mandatory `timeout=` on join)
   - ⚠️ Max memory allocation: 20KB per test

5. **Real-world validation** (after all steps):
   - Test with actual Obra database
   - Verify commands work: `"delete all tasks"`, `"delete all epics stories and tasks"`
   - Verify confirmation prompts appear
   - Verify cascade delete works correctly

## Important Constraints

- **DO NOT** skip tests - Each step has test code provided
- **DO NOT** exceed WSL2 resource limits (see TEST_GUIDELINES.md)
- **DO** use the exact code snippets from the implementation guide
- **DO** follow the dependency order (some steps can run in parallel)
- **DO** update CHANGELOG.md when complete

## Success Criteria

- ✅ All 20+ new tests pass
- ✅ Coverage ≥90% for new components
- ✅ User can execute `"delete all epics stories and tasks"` without error
- ✅ Confirmation prompt shown before deletion
- ✅ Cascade delete works (epic → story → task)
- ✅ Transaction safety (rollback on failure)
- ✅ Real-world validation passes

## Files to Read Before Starting

1. **Implementation guide** (required): `docs/development/NL_BULK_OPERATIONS_IMPLEMENTATION.md`
2. **Test guidelines** (required): `docs/testing/TEST_GUIDELINES.md`
3. **Planning document** (optional): `docs/development/NL_BULK_OPERATIONS_PLAN.md`
4. **NL Command architecture** (optional): `docs/guides/NL_COMMAND_GUIDE.md`

## Recommended Approach

**Option 1: Sequential (safest)**
- Complete STEP 1 → test → STEP 2 → test → ... → STEP 10

**Option 2: Parallel (faster, if comfortable)**
- Phase 1: STEP 1, 2, 3, 4, 7 in parallel
- Phase 2: STEP 5, 6 after Phase 1
- Phase 3: STEP 8 after Phase 2
- Phase 4: STEP 9, 10 after Phase 3

## Questions to Answer

Before you start, decide on these design choices (or use recommendations):

1. **Cascade delete behavior**: Should deleting an epic automatically delete its stories and tasks?
   - **Recommended**: Yes, with confirmation showing cascade impact

2. **Soft delete vs hard delete**: Should bulk deletes be recoverable?
   - **Recommended**: Hard delete with confirmation (soft delete = future enhancement)

3. **Confirmation prompt**: CLI interactive prompt or require `--force` flag?
   - **Recommended**: Interactive prompt for better UX

4. **Scope**: Should "all" mean "all in current project" or "all in database"?
   - **Recommended**: Current project (safer default)

## Ready?

When you're ready, respond with:

1. Your implementation approach (sequential vs parallel)
2. Your answers to the 4 design questions above (or confirm recommendations)
3. Start with STEP 1 (or Phase 1 if parallel)

**Estimated total time**: 13-18 hours (17 hours in guide)

---

**Good luck!** 🚀
