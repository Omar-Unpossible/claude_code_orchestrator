# Claude Code Startup Prompt: NL Command Completion

**Copy this entire prompt into a fresh Claude Code context window to start implementation.**

---

Hello! I need you to implement the remaining features for the Natural Language command system in the Obra project. This is a straightforward completion task with clear specifications.

## Quick Context

**Project**: Obra (Claude Code Orchestrator) - AI orchestration platform
**Your Role**: Complete the NL command system by implementing missing features
**Current State**: 92% functional (233/253 tests passing), 3 specific features need implementation
**Time Estimate**: 1-2 days per phase (3 phases total)

## What You'll Be Doing

**Phase 1** (Priority 1): Implement interactive confirmation workflow
- Problem: UPDATE/DELETE show confirmation prompts but don't handle "yes/no" responses
- Solution: Add state machine to track pending operations and handle confirmation responses

**Phase 2** (Priority 2): Add missing StateManager methods
- Problem: Task UPDATE/DELETE fail because methods don't exist
- Solution: Add `update_task()` and `delete_task()` methods following existing patterns

**Phase 3** (Priority 3): Polish error handling
- Improve error messages with recovery suggestions
- Add retry logic for transient failures
- (This can be done later if time-constrained)

## Start Here

**Step 1**: Read the implementation guide
```bash
cat docs/development/NL_COMPLETION_IMPLEMENTATION_GUIDE.md
```

This machine-optimized guide has:
- Complete code implementations ready to copy
- File locations and line numbers
- Test specifications
- Success criteria

**Step 2**: Optionally read the detailed plan
```bash
cat docs/development/NL_COMPLETION_PLAN.md
```

This human-readable plan has:
- Detailed explanations and rationale
- Architecture diagrams
- Risk mitigation strategies
- (Helpful for understanding "why" but not required for implementation)

**Step 3**: Start with Phase 1
1. Read Phase 1 section in implementation guide
2. Modify the 2 files specified
3. Create the test file
4. Run tests to verify
5. Commit when tests pass

**Step 4**: Continue to Phase 2
1. Same process as Phase 1
2. Commit when tests pass

**Step 5**: (Optional) Phase 3
1. Can be done later if time-constrained

## Key Files You'll Be Editing

**Phase 1 (Confirmation Workflow)**:
- `src/nl/nl_command_processor.py` - Add confirmation state machine
- `src/nl/response_formatter.py` - Update confirmation message
- `tests/nl/test_confirmation_workflow.py` - NEW test file

**Phase 2 (StateManager Extensions)**:
- `src/core/state.py` - Add `update_task()` and `delete_task()` methods
- `src/nl/command_executor.py` - Update to use new methods
- `tests/test_state_manager_task_operations.py` - NEW test file

## Important Guidelines

1. **Read TEST_GUIDELINES.md first** to avoid WSL2 crashes:
   ```bash
   cat docs/development/TEST_GUIDELINES.md
   ```
   - Max 0.5s sleep per test
   - Max 5 threads per test
   - Mandatory timeouts on thread joins

2. **Follow existing code patterns** - The project has established patterns in StateManager, follow them exactly

3. **No breaking changes** - All existing tests must still pass

4. **Test thoroughly** after each phase:
   ```bash
   # Phase 1
   pytest tests/nl/test_confirmation_workflow.py -v

   # Phase 2
   pytest tests/test_state_manager_task_operations.py -v
   pytest tests/nl/test_command_executor.py::TestExecuteUpdate -v

   # All NL tests
   pytest tests/nl/ -v
   ```

## Success Criteria

**You're done when**:
- ✅ Phase 1 tests all pass
- ✅ Phase 2 tests all pass
- ✅ All previously failing UPDATE/DELETE tests now pass
- ✅ No existing tests broken
- ✅ Code follows existing patterns

## Questions?

All implementation details are in the guide. If you need clarification:
1. Check the implementation guide first
2. Look at similar existing code in the same file
3. Read the detailed plan for architectural context
4. Ask me if still unclear

**Let's start!** Begin by reading the implementation guide and then implementing Phase 1.
