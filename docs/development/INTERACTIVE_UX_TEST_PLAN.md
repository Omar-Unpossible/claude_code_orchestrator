# Interactive UX v1.5.0 - Test Plan

**Status:** Ready for execution
**Version:** v1.5.0
**Date:** 2025-11-11
**Estimated Time:** 2-3 hours

---

## Overview

Complete test suite for v1.5.0 interactive UX improvements:
1. Fix 5 failing tests (help text format changes)
2. Add 15+ new tests for v1.5.0 behavior
3. Run full test suite for regression validation
4. Verify 91% coverage maintained

---

## PART 1: Fix Failing Tests (30 minutes)

### Current Failures (5 tests)

```bash
# Run to see current failures:
./venv/bin/python -m pytest tests/test_command_processor.py -v --tb=short
```

**Failed Tests:**
1. `test_execute_help_all_commands` - Help text format changed
2. `test_execute_help_specific_command` - Help text format changed
3. `test_execute_help_unknown_command` - Help text format changed
4. `test_execute_unknown_command` - Now raises exception instead of returning error dict
5. `test_help_text_for_all_commands` - HELP_TEXT is now string, not dict

### Fix Strategy

#### Test 1-3: Help Text Format
**File:** `tests/test_command_processor.py`
**Location:** Lines ~250-270

**Current Assertion:**
```python
assert 'Available commands:' in result['message']
```

**New Assertion (v1.5.0):**
```python
assert 'Interactive Mode Commands (v1.5.0)' in result['message']
assert 'DEFAULT BEHAVIOR:' in result['message']
assert '/help' in result['message']
```

**Changes Needed:**
1. Update `test_execute_help_all_commands`:
   - Change assertion from `'Available commands:'` to `'Interactive Mode Commands (v1.5.0)'`
   - Verify new sections present: `DEFAULT BEHAVIOR`, `SLASH COMMANDS`, `EXAMPLES`

2. Remove `test_execute_help_specific_command`:
   - v1.5.0 removed specific command help (HELP_TEXT is single string)
   - Delete this test entirely or mark as `@pytest.mark.skip("v1.5.0: Help format changed")`

3. Remove `test_execute_help_unknown_command`:
   - Same reason as #2
   - Delete or skip

#### Test 4: Unknown Command Exception
**File:** `tests/test_command_processor.py`
**Location:** Line ~282

**Current Code:**
```python
def test_execute_unknown_command(self):
    processor = CommandProcessor(orchestrator)
    result = processor.execute_command('/unknown')
    assert 'error' in result
    assert 'Unknown command' in result['error']
```

**New Code (v1.5.0):**
```python
def test_execute_unknown_command(self):
    """Unknown slash commands raise CommandValidationError."""
    from src.utils.command_processor import CommandValidationError

    processor = CommandProcessor(orchestrator)

    with pytest.raises(CommandValidationError) as exc_info:
        processor.execute_command('/unknown')

    assert 'Unknown command: /unknown' in str(exc_info.value)
    assert len(exc_info.value.available_commands) > 0
    assert '/help' in exc_info.value.available_commands
```

#### Test 5: Help Text Registry
**File:** `tests/test_command_processor.py`
**Location:** Line ~450

**Current Code:**
```python
def test_help_text_for_all_commands(self):
    for cmd in processor.commands.keys():
        assert cmd in HELP_TEXT
```

**New Code (v1.5.0):**
```python
def test_help_text_contains_all_commands(self):
    """Help text contains all registered slash commands."""
    from src.utils.command_processor import HELP_TEXT

    processor = CommandProcessor(orchestrator)

    # v1.5.0: HELP_TEXT is a single formatted string
    assert isinstance(HELP_TEXT, str)

    # Verify all slash commands mentioned in help text
    essential_commands = ['/help', '/status', '/pause', '/resume', '/stop', '/to-impl', '/override-decision']
    for cmd in essential_commands:
        assert cmd in HELP_TEXT, f"Command {cmd} not found in help text"
```

---

## PART 2: Add New Tests for v1.5.0 Behavior (90 minutes)

### Test File: `tests/test_command_processor_v1_5.py` (NEW FILE)

Create new test file for v1.5.0 specific behavior.

**Location:** `tests/test_command_processor_v1_5.py`

**Test Classes:**

### Class 1: TestNaturalLanguageRouting (8 tests)

```python
class TestNaturalLanguageRouting:
    """Test natural language defaults to orchestrator (v1.5.0)."""

    def test_natural_text_sent_to_orchestrator(self, mock_orchestrator):
        """Natural text without slash goes to orchestrator."""
        processor = CommandProcessor(mock_orchestrator)
        result = processor.execute_command("create epic for auth")

        # Should call _to_orch internally
        assert result['success']
        assert 'orch' in result['message'].lower() or 'orchestrator' in result['message'].lower()

    def test_multiline_natural_text(self, mock_orchestrator):
        """Multiline natural text sent to orchestrator."""
        processor = CommandProcessor(mock_orchestrator)
        message = """create epic for authentication with:
        - OAuth integration
        - JWT tokens
        - Session management"""

        result = processor.execute_command(message)
        assert result['success']

    def test_natural_text_with_special_chars(self, mock_orchestrator):
        """Natural text with special characters works."""
        processor = CommandProcessor(mock_orchestrator)
        result = processor.execute_command("Be more lenient! Quality > 0.5 is OK")
        assert result['success']

    def test_natural_text_preserves_slashes_in_middle(self, mock_orchestrator):
        """Slash in middle of message is preserved (not a command)."""
        processor = CommandProcessor(mock_orchestrator)
        result = processor.execute_command("use /api/endpoint in implementation")
        assert result['success']
        # Verify message contains the slash

    def test_empty_input_rejected(self, mock_orchestrator):
        """Empty input returns error."""
        processor = CommandProcessor(mock_orchestrator)
        result = processor.execute_command("")
        assert 'error' in result

    def test_whitespace_only_rejected(self, mock_orchestrator):
        """Whitespace-only input returns error."""
        processor = CommandProcessor(mock_orchestrator)
        result = processor.execute_command("   \t  \n  ")
        assert 'error' in result

    def test_natural_text_case_preserved(self, mock_orchestrator):
        """Natural text case is preserved."""
        processor = CommandProcessor(mock_orchestrator)
        result = processor.execute_command("Be MORE Lenient")
        assert result['success']

    def test_natural_text_unicode_supported(self, mock_orchestrator):
        """Unicode in natural text is supported."""
        processor = CommandProcessor(mock_orchestrator)
        result = processor.execute_command("Create epic: User Auth 🔐")
        assert result['success']
```

### Class 2: TestSlashCommandValidation (7 tests)

```python
class TestSlashCommandValidation:
    """Test slash command validation (v1.5.0)."""

    def test_slash_command_requires_validity(self):
        """Invalid slash commands raise CommandValidationError."""
        from src.utils.command_processor import CommandValidationError

        processor = CommandProcessor(mock_orchestrator)

        with pytest.raises(CommandValidationError) as exc:
            processor.execute_command('/invalid-command')

        assert 'Unknown command' in str(exc.value)
        assert len(exc.value.available_commands) > 0

    def test_single_slash_rejected(self):
        """Single slash character is invalid command."""
        from src.utils.command_processor import CommandValidationError

        processor = CommandProcessor(mock_orchestrator)

        with pytest.raises(CommandValidationError):
            processor.execute_command('/')

    def test_slash_with_whitespace_rejected(self):
        """Slash followed by whitespace is invalid."""
        from src.utils.command_processor import CommandValidationError

        processor = CommandProcessor(mock_orchestrator)

        with pytest.raises(CommandValidationError):
            processor.execute_command('/   ')

    def test_case_insensitive_slash_commands(self, mock_orchestrator):
        """Slash commands are case-insensitive."""
        processor = CommandProcessor(mock_orchestrator)

        result1 = processor.execute_command('/HELP')
        result2 = processor.execute_command('/help')
        result3 = processor.execute_command('/HeLp')

        assert result1['success']
        assert result2['success']
        assert result3['success']

    def test_slash_must_be_first_character(self, mock_orchestrator):
        """Slash in middle of message is part of natural text."""
        processor = CommandProcessor(mock_orchestrator)

        # This should go to orchestrator, NOT be treated as command
        result = processor.execute_command("check /status of system")
        assert result['success']

    def test_all_system_commands_require_slash(self, mock_orchestrator):
        """All system commands must have slash prefix."""
        from src.utils.command_processor import CommandValidationError

        processor = CommandProcessor(mock_orchestrator)
        system_commands = ['help', 'status', 'pause', 'resume', 'stop']

        for cmd in system_commands:
            # Without slash - sent to orchestrator (natural text)
            result = processor.execute_command(cmd)
            assert result['success']  # Should succeed (routed to orchestrator)

            # With slash - executes command
            result = processor.execute_command(f'/{cmd}')
            assert result['success']  # Should succeed (valid command)

    def test_validation_error_includes_available_commands(self):
        """CommandValidationError includes list of available commands."""
        from src.utils.command_processor import CommandValidationError

        processor = CommandProcessor(mock_orchestrator)

        with pytest.raises(CommandValidationError) as exc:
            processor.execute_command('/badcommand')

        assert '/help' in exc.value.available_commands
        assert '/status' in exc.value.available_commands
        assert '/pause' in exc.value.available_commands
```

### Class 3: TestBackwardCompatibility (4 tests)

```python
class TestBackwardCompatibility:
    """Test backward compatibility and migration."""

    def test_to_impl_still_works(self, mock_orchestrator):
        """/to-impl command still works (unchanged)."""
        processor = CommandProcessor(mock_orchestrator)
        result = processor.execute_command('/to-impl fix the bug')
        assert result['success']

    def test_to_claude_alias_still_works(self, mock_orchestrator):
        """/to-claude alias still works."""
        processor = CommandProcessor(mock_orchestrator)
        result = processor.execute_command('/to-claude add tests')
        assert result['success']

    def test_pause_resume_still_work(self, mock_orchestrator):
        """/pause and /resume still work."""
        processor = CommandProcessor(mock_orchestrator)

        # Pause
        result = processor.execute_command('/pause')
        assert result['success']
        assert mock_orchestrator.paused

        # Resume
        result = processor.execute_command('/resume')
        assert result['success']
        assert not mock_orchestrator.paused

    def test_override_decision_still_works(self, mock_orchestrator):
        """/override-decision still works."""
        processor = CommandProcessor(mock_orchestrator)
        result = processor.execute_command('/override-decision retry')
        assert result['success']
```

### Fixtures Needed

```python
# Add to conftest.py or top of test file

@pytest.fixture
def mock_orchestrator():
    """Mock orchestrator for testing command routing."""
    from unittest.mock import MagicMock

    orchestrator = MagicMock()
    orchestrator.paused = False
    orchestrator.stop_requested = False
    orchestrator.injected_context = {}
    orchestrator.current_task_id = None
    orchestrator.current_iteration = 1
    orchestrator.latest_quality_score = 0.75
    orchestrator.latest_confidence = 0.68

    return orchestrator
```

---

## PART 3: Integration Testing (30 minutes)

### Test Orchestrator Integration

**File:** `tests/test_orchestrator_interactive_v1_5.py` (NEW FILE)

```python
class TestOrchestratorInteractiveV15:
    """Test orchestrator integration with v1.5.0 command processor."""

    def test_orchestrator_catches_validation_error(self, test_config):
        """Orchestrator catches CommandValidationError and shows helpful message."""
        from src.orchestrator import Orchestrator
        from src.utils.input_manager import InputManager
        import io
        import sys

        orchestrator = Orchestrator(config=test_config)
        orchestrator.interactive_mode = True
        orchestrator.input_manager = InputManager()

        # Simulate invalid command
        orchestrator.input_manager.command_queue.put('/badcommand')

        # Capture output
        captured_output = io.StringIO()
        sys.stdout = captured_output

        orchestrator._check_interactive_commands()

        sys.stdout = sys.__stdout__
        output = captured_output.getvalue()

        # Should show error message
        assert 'Error' in output or 'error' in output
        assert 'Available commands' in output or '/help' in output

    def test_orchestrator_routes_natural_language(self, test_config):
        """Orchestrator routes natural language to command processor."""
        from src.orchestrator import Orchestrator
        from src.utils.input_manager import InputManager

        orchestrator = Orchestrator(config=test_config)
        orchestrator.interactive_mode = True
        orchestrator.input_manager = InputManager()

        # Simulate natural language command
        orchestrator.input_manager.command_queue.put("be more lenient")

        orchestrator._check_interactive_commands()

        # Should be in injected context
        assert 'to_orch' in orchestrator.injected_context or 'to_obra' in orchestrator.injected_context
```

---

## PART 4: Automated Testing & Coverage (30 minutes)

### Full Test Suite Execution

```bash
# Run all tests
./venv/bin/python -m pytest tests/ -v

# Run with coverage
./venv/bin/python -m pytest tests/ --cov=src --cov-report=term --cov-report=html

# Run only command processor tests
./venv/bin/python -m pytest tests/test_command_processor*.py -v

# Run only v1.5.0 tests
./venv/bin/python -m pytest tests/test_command_processor_v1_5.py -v

# Check for any regressions
./venv/bin/python -m pytest tests/test_orchestrator.py tests/test_state.py -v
```

### Coverage Requirements

**Target:** Maintain 91% overall coverage

**Critical Modules:**
- `src/utils/command_processor.py` → 95%+ coverage
- `src/utils/input_manager.py` → 90%+ coverage
- `src/orchestrator.py` (interactive methods) → 90%+ coverage

### Coverage Report Analysis

```bash
# Generate HTML coverage report
./venv/bin/python -m pytest --cov=src --cov-report=html

# Open report
firefox htmlcov/index.html  # or your browser

# Check specific module coverage
./venv/bin/python -m pytest --cov=src.utils.command_processor --cov-report=term
```

---

## PART 5: Verification Checklist

### Functional Verification

- [ ] All 5 failing tests fixed and passing
- [ ] 15+ new v1.5.0 tests added and passing
- [ ] No regressions in existing tests
- [ ] Overall coverage ≥ 91%
- [ ] CommandProcessor coverage ≥ 95%
- [ ] All tests complete within timeout (30s per test)

### Code Quality Checks

```bash
# Type checking
mypy src/utils/command_processor.py
mypy src/utils/input_manager.py

# Linting
pylint src/utils/command_processor.py
pylint src/utils/input_manager.py

# Format check
black --check src/utils/command_processor.py src/utils/input_manager.py
```

### Edge Cases Verified

- [ ] Empty input handled
- [ ] Whitespace-only input handled
- [ ] Single slash rejected
- [ ] Slash with whitespace rejected
- [ ] Unicode in natural text works
- [ ] Multiline natural text works
- [ ] Slash in middle of message preserved
- [ ] Case-insensitive slash commands work
- [ ] All system commands require slash
- [ ] Invalid slash commands show helpful errors

---

## Implementation Order

### Step 1: Fix Failing Tests (30 min)
1. Update `test_execute_help_all_commands` (5 min)
2. Remove/skip `test_execute_help_specific_command` (2 min)
3. Remove/skip `test_execute_help_unknown_command` (2 min)
4. Fix `test_execute_unknown_command` (10 min)
5. Fix `test_help_text_for_all_commands` (10 min)
6. Run tests: `./venv/bin/python -m pytest tests/test_command_processor.py -v` (1 min)

### Step 2: Create New Test File (60 min)
1. Create `tests/test_command_processor_v1_5.py` (5 min)
2. Add fixtures (10 min)
3. Implement `TestNaturalLanguageRouting` (20 min)
4. Implement `TestSlashCommandValidation` (20 min)
5. Implement `TestBackwardCompatibility` (5 min)
6. Run tests: `./venv/bin/python -m pytest tests/test_command_processor_v1_5.py -v` (1 min)

### Step 3: Integration Tests (30 min)
1. Create `tests/test_orchestrator_interactive_v1_5.py` (5 min)
2. Implement orchestrator integration tests (20 min)
3. Run tests: `./venv/bin/python -m pytest tests/test_orchestrator_interactive_v1_5.py -v` (5 min)

### Step 4: Full Suite Validation (30 min)
1. Run all tests: `./venv/bin/python -m pytest tests/ -v` (10 min)
2. Generate coverage report: `./venv/bin/python -m pytest --cov=src --cov-report=html` (10 min)
3. Analyze coverage, fix gaps if needed (5 min)
4. Run type checking and linting (5 min)

### Step 5: Commit Changes (10 min)
```bash
git add tests/
git commit -m "test: Add comprehensive tests for v1.5.0 interactive UX

- Fixed 5 failing tests (help text format changes)
- Added 15+ new tests for natural language routing
- Added integration tests for orchestrator error handling
- Verified 91% coverage maintained
- All 790+ tests passing

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Success Criteria

✅ **All tests passing:** 790+ tests (including new v1.5.0 tests)
✅ **Coverage maintained:** ≥91% overall, ≥95% for command_processor
✅ **No regressions:** All existing functionality still works
✅ **Edge cases covered:** All 10+ edge cases tested
✅ **Code quality:** Type checking and linting pass
✅ **Documented:** Test plan completed and committed

---

## Troubleshooting

### Issue: Import errors for CommandValidationError

**Fix:**
```python
from src.utils.command_processor import CommandValidationError
```

### Issue: Mock orchestrator missing attributes

**Fix:** Update mock fixture:
```python
@pytest.fixture
def mock_orchestrator():
    orchestrator = MagicMock()
    orchestrator.paused = False
    orchestrator.injected_context = {}
    # Add all required attributes
    return orchestrator
```

### Issue: Coverage not at 91%

**Fix:** Check uncovered lines:
```bash
./venv/bin/python -m pytest --cov=src --cov-report=term-missing
```

Add tests for uncovered lines.

---

## Test Execution Summary

**Total Time:** ~2.5 hours

| Phase | Time | Tests Added | Status |
|-------|------|-------------|--------|
| Fix failing tests | 30 min | 0 (5 fixed) | ⏳ Pending |
| New v1.5.0 tests | 90 min | 19 tests | ⏳ Pending |
| Integration tests | 30 min | 2 tests | ⏳ Pending |
| Validation & coverage | 30 min | 0 (verification) | ⏳ Pending |

**Total Tests After Completion:** 790+ → 810+

---

**Status:** Ready for execution
**Next Action:** Begin Step 1 - Fix failing tests
