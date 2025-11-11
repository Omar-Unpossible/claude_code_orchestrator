# Resume Prompt for Interactive UX Testing (v1.5.0)

## Short Prompt for Fresh Claude Code Session

Copy and paste this into a new Claude Code session:

---

**Prompt:**

```
I need you to implement the test plan for Obra v1.5.0 interactive UX improvements.

Context:
- v1.5.0 changed interactive mode so natural language defaults to orchestrator (no /to-orch prefix needed)
- 5 tests are failing due to help text format changes
- We need 15+ new tests for the new behavior

Tasks:
1. Read the test plan: docs/development/INTERACTIVE_UX_TEST_PLAN.md
2. Fix the 5 failing tests in tests/test_command_processor.py
3. Create tests/test_command_processor_v1_5.py with new tests
4. Run full test suite and verify 91% coverage maintained
5. Commit changes

Key files:
- Test plan: docs/development/INTERACTIVE_UX_TEST_PLAN.md (detailed instructions)
- Implementation: docs/development/INTERACTIVE_UX_IMPROVEMENT_PLAN.md (context)
- CHANGELOG: CHANGELOG.md (v1.5.0 section shows what changed)

Start by reading the test plan, then execute steps 1-5 sequentially. Track progress with TodoWrite tool.
```

---

## Alternative: Even Shorter Prompt

If you need an ultra-concise prompt:

```
Implement the test plan in docs/development/INTERACTIVE_UX_TEST_PLAN.md for Obra v1.5.0 interactive UX. Fix 5 failing tests, add 15+ new tests, verify 91% coverage, commit changes. Track progress with todos.
```

---

## What to Expect

Claude Code will:
1. Read `INTERACTIVE_UX_TEST_PLAN.md` for detailed instructions
2. Read `INTERACTIVE_UX_IMPROVEMENT_PLAN.md` for context
3. Fix failing tests in `tests/test_command_processor.py`
4. Create `tests/test_command_processor_v1_5.py` with new tests
5. Run pytest and verify coverage
6. Commit all changes

**Estimated completion time:** 2-3 hours (with Claude Code automation)

---

## Files Claude Code Will Need

Claude Code will automatically read these files (all already in the repo):

**Primary:**
- `docs/development/INTERACTIVE_UX_TEST_PLAN.md` - Step-by-step test plan
- `tests/test_command_processor.py` - Existing tests to fix

**Context (auto-referenced via CLAUDE.md):**
- `CLAUDE.md` - Project overview
- `CHANGELOG.md` - v1.5.0 changes
- `docs/development/INTERACTIVE_UX_IMPROVEMENT_PLAN.md` - Implementation details

**Source files:**
- `src/utils/command_processor.py` - Code being tested
- `src/utils/input_manager.py` - Input handling
- `src/orchestrator.py` - Orchestrator integration

---

## Verification After Completion

Check these indicators to confirm success:

```bash
# All tests should pass
./venv/bin/python -m pytest tests/ -v | grep "passed"

# Should show 810+ tests passing
# Expected output: "810 passed in X.XXs"

# Coverage should be ≥91%
./venv/bin/python -m pytest --cov=src --cov-report=term | grep TOTAL

# Should show git commit
git log -1 --oneline
# Expected: "test: Add comprehensive tests for v1.5.0 interactive UX"
```

---

## Troubleshooting

**If Claude Code asks for clarification:**

Provide this context:
- v1.5.0 is a BREAKING CHANGE
- Natural text (no slash) now routes to orchestrator by default
- ALL system commands require `/` prefix as first character
- Help text changed from dict to formatted string
- Unknown slash commands now raise `CommandValidationError` exception

**If tests are still failing:**

Ask Claude Code to:
1. Show the failing test output
2. Read the error messages carefully
3. Check if mock fixtures have all required attributes
4. Verify imports are correct

**If coverage is below 91%:**

Ask Claude Code to:
1. Generate coverage report: `pytest --cov=src --cov-report=term-missing`
2. Identify uncovered lines
3. Add tests for those specific lines

---

## Success Checklist

When Claude Code finishes, you should see:

- ✅ All 810+ tests passing
- ✅ Coverage ≥91% (shown in terminal)
- ✅ New files created:
  - `tests/test_command_processor_v1_5.py`
  - `tests/test_orchestrator_interactive_v1_5.py` (optional)
- ✅ Modified files:
  - `tests/test_command_processor.py` (5 tests fixed)
- ✅ Git commit created with semantic message
- ✅ No regressions (all existing tests still pass)

---

**Ready to use!** Copy the short prompt above and paste it into a fresh Claude Code session.
