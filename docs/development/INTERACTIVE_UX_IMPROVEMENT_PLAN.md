# Interactive Mode UX Improvement - Implementation Plan

**Version:** v1.5.0
**Date:** 2025-11-11
**Status:** Ready for implementation

## Overview

Change interactive mode default behavior to eliminate friction for the primary use case (communicating with orchestrator).

### Current Behavior
- Natural text → ignored (no default action)
- `/to-obra <msg>` → Send to orchestrator
- `/to-claude <msg>` → Send to implementer
- `help` → Show help (no slash required)
- Other commands → Slash optional

### New Behavior
- **Natural text → Send to orchestrator (DEFAULT)**
- `/to-claude <msg>` → Send to implementer
- `/help`, `/status`, `/pause`, etc. → All require slash prefix
- **Slash commands must be first character**
- **Invalid slash commands rejected with error**

---

## Design Decisions

### Q1: Slash prefix requirement
✅ **ALL system commands require slash as first character**

### Q2: Asymmetry between orch/claude
✅ **Accept asymmetry** - Orchestrator is primary interface, Claude is secondary

### Q3: Discoverability
✅ **`/help` command sufficient** - No additional discoverability needed

### Q4: Breaking changes
✅ **No transition period** - Full bang implementation, breaking change acceptable

### Q5: Escape edge cases
✅ **Reject messages starting with '/' if not valid command** - No escape syntax needed

---

## Implementation Plan

### Phase 1: Core Logic Changes

#### 1.1 Update CommandProcessor (`src/interactive/command_processor.py`)

**File:** `src/interactive/command_processor.py`
**Lines:** ~60-120 (process_command method)

**Changes:**
1. Modify `process_command()` routing logic:
   ```python
   def process_command(self, user_input: str) -> CommandResult:
       """Process user input with new default-to-orch behavior.

       Rules:
       - Starts with '/' → System command (must be valid)
       - No '/' → Natural language to orchestrator
       """
       user_input = user_input.strip()

       if not user_input:
           return CommandResult(success=False, message="Empty input")

       if user_input.startswith('/'):
           return self._process_slash_command(user_input)
       else:
           return self._send_to_orchestrator(user_input)
   ```

2. Add `_process_slash_command()` method:
   ```python
   def _process_slash_command(self, command_str: str) -> CommandResult:
       """Process slash command with validation.

       Args:
           command_str: User input starting with '/'

       Returns:
           CommandResult with success/error

       Raises:
           CommandValidationError: If slash command is invalid
       """
       parts = command_str[1:].split(maxsplit=1)
       command = parts[0].lower()
       args = parts[1] if len(parts) > 1 else ""

       if command not in self.COMMANDS:
           raise CommandValidationError(
               f"Unknown command: /{command}",
               available_commands=list(self.COMMANDS.keys())
           )

       return self._execute_command(command, args)
   ```

3. Add `_send_to_orchestrator()` method:
   ```python
   def _send_to_orchestrator(self, message: str) -> CommandResult:
       """Send natural language message to orchestrator.

       This is the default action for non-slash input.

       Args:
           message: Natural language text from user

       Returns:
           CommandResult with orchestrator response
       """
       self.logger.debug(f"Sending to orchestrator: {message[:50]}...")

       # Reuse existing to-obra logic
       return self._handle_to_obra(message)
   ```

4. Update `COMMANDS` dict - all require slash:
   ```python
   COMMANDS = {
       'help': self._handle_help,
       'status': self._handle_status,
       'pause': self._handle_pause,
       'resume': self._handle_resume,
       'stop': self._handle_stop,
       'to-claude': self._handle_to_claude,
       'override-decision': self._handle_override_decision,
   }
   # NOTE: 'to-obra' removed - natural text is default
   ```

5. Update help text in `_handle_help()`:
   ```python
   def _handle_help(self, args: str) -> CommandResult:
       """Show help with updated command syntax."""
       help_text = """
   Interactive Mode Commands:

   DEFAULT BEHAVIOR:
     <natural text>              Send message to orchestrator (no prefix needed)

   SLASH COMMANDS (must start with '/'):
     /help                       Show this help message
     /status                     Show current orchestration status
     /pause                      Pause orchestration (before next checkpoint)
     /resume                     Resume paused orchestration
     /stop                       Stop orchestration gracefully
     /to-claude <message>        Send message directly to Claude Code implementer
     /override-decision <choice> Override orchestrator's decision
                                 Choices: proceed, retry, clarify, escalate

   EXAMPLES:
     create epic for authentication system          → Sent to orchestrator
     implement login with JWT                      → Sent to orchestrator
     /to-claude fix the type error in auth.py      → Sent to Claude
     /status                                        → Show status
     /pause                                         → Pause before next checkpoint

   NOTE: Messages starting with '/' must be valid commands. To send natural
         language to the orchestrator, do not start with '/'.
   """
       return CommandResult(success=True, message=help_text)
   ```

#### 1.2 Add Custom Exception

**File:** `src/interactive/command_processor.py`
**Lines:** Top of file (after imports)

```python
class CommandValidationError(Exception):
    """Raised when slash command is invalid."""

    def __init__(self, message: str, available_commands: list[str]):
        super().__init__(message)
        self.available_commands = available_commands
```

#### 1.3 Update Error Handling in Interactive Loop

**File:** `src/cli/interactive.py`
**Lines:** ~150-200 (main interactive loop)

**Changes:**
1. Catch `CommandValidationError`:
   ```python
   try:
       result = command_processor.process_command(user_input)
       console.print(result.message)
   except CommandValidationError as e:
       console.print(f"[red]Error: {e}[/red]")
       console.print(f"[yellow]Available commands: {', '.join(e.available_commands)}[/yellow]")
       console.print("[dim]Type /help for usage information[/dim]")
   except Exception as e:
       logger.exception("Unexpected error processing command")
       console.print(f"[red]Unexpected error: {e}[/red]")
   ```

2. Update prompt indicator:
   ```python
   # Show current mode in prompt
   prompt_text = "obra[orch]> "  # Changed from "obra> "
   ```

---

### Phase 2: Input Handling Updates

#### 2.1 Update Tab Completion

**File:** `src/interactive/input_manager.py`
**Lines:** ~80-120 (completer setup)

**Changes:**
1. Update command list for completion:
   ```python
   SLASH_COMMANDS = [
       '/help',
       '/status',
       '/pause',
       '/resume',
       '/stop',
       '/to-claude',
       '/override-decision',
   ]
   ```

2. Add context-aware completion:
   ```python
   def get_completions(self, document, complete_event):
       """Provide tab completions for slash commands."""
       text = document.text_before_cursor

       # Only complete if text starts with '/'
       if text.startswith('/'):
           word = text[1:]  # Remove leading slash
           for cmd in self.SLASH_COMMANDS:
               if cmd[1:].startswith(word):  # Match without slash
                   yield Completion(cmd, start_position=-len(text))
   ```

3. Add inline hints:
   ```python
   # In PromptSession setup
   session = PromptSession(
       message="obra[orch]> ",
       completer=CommandCompleter(),
       complete_while_typing=True,
       bottom_toolbar="Type naturally to talk to orchestrator, or /help for commands",
   )
   ```

---

### Phase 3: Testing

#### 3.1 Unit Tests - CommandProcessor

**File:** `tests/test_command_processor.py`

**New test cases:**
```python
class TestCommandProcessorNewBehavior:
    """Test new default-to-orch behavior."""

    def test_natural_text_sent_to_orchestrator(self):
        """Natural text without slash goes to orchestrator."""
        processor = CommandProcessor()
        result = processor.process_command("create epic for auth")
        assert result.success
        assert "orchestrator" in result.message.lower()

    def test_slash_command_requires_validity(self):
        """Invalid slash commands raise error."""
        processor = CommandProcessor()
        with pytest.raises(CommandValidationError) as exc:
            processor.process_command("/invalid-command")
        assert "Unknown command" in str(exc.value)
        assert "/invalid-command" in str(exc.value)

    def test_help_requires_slash(self):
        """Help command now requires slash prefix."""
        processor = CommandProcessor()

        # Without slash - sent to orchestrator
        result = processor.process_command("help")
        assert result.success
        assert "orchestrator" in result.message.lower()

        # With slash - shows help
        result = processor.process_command("/help")
        assert result.success
        assert "Interactive Mode Commands" in result.message

    def test_status_requires_slash(self):
        """Status command now requires slash prefix."""
        processor = CommandProcessor()

        # Without slash - sent to orchestrator
        result = processor.process_command("status")
        assert result.success
        assert "orchestrator" in result.message.lower()

        # With slash - shows status
        result = processor.process_command("/status")
        assert result.success

    def test_to_claude_requires_slash(self):
        """to-claude command requires slash prefix."""
        processor = CommandProcessor()

        # Without slash - sent to orchestrator
        result = processor.process_command("to-claude fix bug")
        assert result.success
        assert "orchestrator" in result.message.lower()

        # With slash - sent to Claude
        result = processor.process_command("/to-claude fix bug")
        assert result.success

    def test_empty_input_rejected(self):
        """Empty input returns error."""
        processor = CommandProcessor()
        result = processor.process_command("")
        assert not result.success
        assert "Empty input" in result.message

    def test_whitespace_only_rejected(self):
        """Whitespace-only input returns error."""
        processor = CommandProcessor()
        result = processor.process_command("   ")
        assert not result.success

    def test_slash_must_be_first_character(self):
        """Slash in middle of message is part of natural text."""
        processor = CommandProcessor()
        result = processor.process_command("use /api/endpoint in implementation")
        assert result.success
        assert "orchestrator" in result.message.lower()

    def test_all_system_commands_require_slash(self):
        """All system commands must have slash prefix."""
        processor = CommandProcessor()
        system_commands = ['pause', 'resume', 'stop', 'override-decision']

        for cmd in system_commands:
            # Without slash - sent to orchestrator
            result = processor.process_command(cmd)
            assert result.success
            assert "orchestrator" in result.message.lower()

            # With slash - executes command
            result = processor.process_command(f"/{cmd}")
            assert result.success  # May fail if not in correct state, but parsed correctly
```

#### 3.2 Integration Tests

**File:** `tests/test_integration_interactive.py`

**New test cases:**
```python
class TestInteractiveModeIntegration:
    """Integration tests for new interactive behavior."""

    def test_full_interactive_session_with_natural_language(self):
        """Full session using natural language for orchestrator."""
        # Simulate interactive session
        inputs = [
            "create epic for user authentication",
            "show me the current status",  # Natural language, not /status
            "/status",  # System command
            "/to-claude implement login endpoint",
            "/stop"
        ]
        # Verify correct routing...

    def test_invalid_slash_command_shows_help_hint(self):
        """Invalid slash commands show helpful error."""
        # Test that error includes available commands
        # Test that error suggests /help
```

#### 3.3 Edge Case Tests

**File:** `tests/test_command_processor_edge_cases.py`

```python
class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_single_slash_rejected(self):
        """Single slash character is invalid command."""
        processor = CommandProcessor()
        with pytest.raises(CommandValidationError):
            processor.process_command("/")

    def test_slash_with_whitespace(self):
        """Slash followed by whitespace is invalid."""
        processor = CommandProcessor()
        with pytest.raises(CommandValidationError):
            processor.process_command("/   ")

    def test_case_insensitive_commands(self):
        """Slash commands are case-insensitive."""
        processor = CommandProcessor()
        result1 = processor.process_command("/HELP")
        result2 = processor.process_command("/help")
        assert result1.success == result2.success

    def test_multiline_natural_text(self):
        """Multiline natural text sent to orchestrator."""
        processor = CommandProcessor()
        message = """create epic for authentication with:
        - OAuth integration
        - JWT tokens
        - Session management"""
        result = processor.process_command(message)
        assert result.success
        assert "orchestrator" in result.message.lower()
```

---

### Phase 4: Documentation Updates

#### 4.1 Update Quick Reference

**File:** `docs/development/INTERACTIVE_STREAMING_QUICKREF.md`

**Changes:**
1. Update command syntax section
2. Add examples showing natural language usage
3. Clarify slash command requirements
4. Update decision tree diagram

#### 4.2 Update CHANGELOG

**File:** `CHANGELOG.md`

**Entry:**
```markdown
## [1.5.0] - 2025-11-11

### Changed - BREAKING
- **Interactive Mode UX**: Natural text now defaults to orchestrator
  - Natural language messages (no slash prefix) sent directly to orchestrator
  - ALL system commands now require '/' prefix (including /help, /status)
  - Invalid slash commands rejected with helpful error message
  - Removed `/to-obra` command (natural text is default)
  - Prompt indicator changed to `obra[orch]>` for clarity

### Migration
- Old: `/to-obra create epic for auth` → New: `create epic for auth`
- Old: `help` → New: `/help`
- Old: `status` → New: `/status`
- All other slash commands unchanged (already required prefix)
```

#### 4.3 Update Architecture Docs

**File:** `docs/architecture/ARCHITECTURE.md`

**Section:** Interactive Mode
- Update command processing flow diagram
- Document new routing logic
- Add rationale for UX change

---

## Testing Checklist

- [ ] All unit tests pass (790+ existing tests)
- [ ] New unit tests added (15+ new tests)
- [ ] Integration tests pass
- [ ] Edge case tests pass
- [ ] Tab completion works for all slash commands
- [ ] Invalid slash commands show helpful errors
- [ ] Natural language routes to orchestrator correctly
- [ ] `/to-claude` still works for implementer communication
- [ ] Prompt indicator shows `obra[orch]>`
- [ ] `/help` shows updated command syntax
- [ ] Empty/whitespace input handled gracefully
- [ ] Multiline input works correctly

---

## Implementation Order

1. **Update CommandProcessor** (Core logic)
   - Add `_process_slash_command()` method
   - Add `_send_to_orchestrator()` method
   - Modify `process_command()` routing
   - Update `COMMANDS` dict
   - Add `CommandValidationError` exception

2. **Update CLI interactive loop** (Error handling)
   - Catch `CommandValidationError`
   - Update prompt indicator
   - Add helpful error messages

3. **Update InputManager** (Tab completion)
   - Update `SLASH_COMMANDS` list
   - Modify completer logic
   - Add bottom toolbar hint

4. **Write tests** (Validation)
   - Unit tests for CommandProcessor
   - Integration tests for interactive flow
   - Edge case tests

5. **Update documentation** (Communication)
   - INTERACTIVE_STREAMING_QUICKREF.md
   - CHANGELOG.md
   - ARCHITECTURE.md

6. **Final validation** (Quality assurance)
   - Run full test suite
   - Manual testing in interactive mode
   - Verify all checklist items

---

## Risk Assessment

### Low Risk
- ✅ Project is v1.4.0 with limited external users
- ✅ Breaking change is acceptable (per requirements)
- ✅ Clear migration path (documented in CHANGELOG)
- ✅ Comprehensive test coverage ensures no regressions

### Medium Risk
- ⚠️ Muscle memory for existing users (if any)
  - Mitigation: Clear error messages guide users to new syntax

### High Risk
- ❌ None identified

---

## Success Criteria

1. ✅ Natural language input defaults to orchestrator (no slash prefix)
2. ✅ All system commands require slash as first character
3. ✅ Invalid slash commands rejected with helpful error
4. ✅ Tab completion works for all slash commands
5. ✅ All tests pass (existing + new)
6. ✅ Documentation updated and accurate
7. ✅ No performance degradation
8. ✅ Error messages are clear and actionable

---

## Estimated Effort

- **Implementation**: 3-4 hours
- **Testing**: 2-3 hours
- **Documentation**: 1-2 hours
- **Total**: 6-9 hours

---

## Notes

- This change significantly improves UX for the primary use case (orchestrator communication)
- Asymmetry between orchestrator (default) and Claude (/to-claude) is intentional
- No escape syntax needed - slash prefix is reserved for system commands only
- Future enhancement: Consider `/mode orch` / `/mode claude` for context switching if needed

---

**Status**: ✅ Ready for implementation
**Approver**: Omar (Product Owner)
**Next Steps**: Execute implementation plan, run tests, update docs, commit changes
