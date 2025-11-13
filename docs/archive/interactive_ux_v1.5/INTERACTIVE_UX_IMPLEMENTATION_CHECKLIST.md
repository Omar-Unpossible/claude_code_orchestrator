# Interactive UX Improvement - Machine-Optimized Implementation Checklist

**Version:** v1.5.0
**Execution Mode:** Sequential (dependencies between steps)
**Estimated Time:** 6-9 hours

---

## STEP 1: Update CommandProcessor Core Logic

**File:** `src/interactive/command_processor.py`
**Dependencies:** None
**Time:** 90 minutes

### 1.1 Add Exception Class
**Location:** Top of file, after imports
**Action:** INSERT

```python
class CommandValidationError(Exception):
    """Raised when slash command is invalid."""

    def __init__(self, message: str, available_commands: list[str]):
        super().__init__(message)
        self.available_commands = available_commands
```

### 1.2 Update COMMANDS Dict
**Location:** CommandProcessor class, COMMANDS dict
**Action:** REPLACE

**OLD:**
```python
COMMANDS = {
    'help': self._handle_help,
    'status': self._handle_status,
    'pause': self._handle_pause,
    'resume': self._handle_resume,
    'stop': self._handle_stop,
    'to-obra': self._handle_to_obra,
    'to-claude': self._handle_to_claude,
    'override-decision': self._handle_override_decision,
}
```

**NEW:**
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

### 1.3 Replace process_command() Method
**Location:** CommandProcessor class, process_command() method
**Action:** REPLACE entire method

```python
def process_command(self, user_input: str) -> CommandResult:
    """Process user input with new default-to-orch behavior.

    Rules:
    - Starts with '/' → System command (must be valid)
    - No '/' → Natural language to orchestrator

    Args:
        user_input: Raw user input from interactive prompt

    Returns:
        CommandResult with success status and message

    Raises:
        CommandValidationError: If slash command is invalid
    """
    user_input = user_input.strip()

    if not user_input:
        return CommandResult(success=False, message="Empty input")

    if user_input.startswith('/'):
        return self._process_slash_command(user_input)
    else:
        return self._send_to_orchestrator(user_input)
```

### 1.4 Add _process_slash_command() Method
**Location:** CommandProcessor class
**Action:** INSERT new method

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
    # Remove leading slash and split
    parts = command_str[1:].split(maxsplit=1)

    if not parts or not parts[0]:
        raise CommandValidationError(
            "Invalid command: slash with no command name",
            available_commands=list(self.COMMANDS.keys())
        )

    command = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""

    if command not in self.COMMANDS:
        raise CommandValidationError(
            f"Unknown command: /{command}",
            available_commands=list(self.COMMANDS.keys())
        )

    # Execute the command
    handler = self.COMMANDS[command]
    return handler(args)
```

### 1.5 Add _send_to_orchestrator() Method
**Location:** CommandProcessor class
**Action:** INSERT new method

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

### 1.6 Update _handle_help() Method
**Location:** CommandProcessor class, _handle_help() method
**Action:** REPLACE help text

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

**Verification:**
```bash
# Check syntax
python -m py_compile src/interactive/command_processor.py

# Run unit tests
pytest tests/test_command_processor.py -v
```

---

## STEP 2: Update CLI Interactive Loop

**File:** `src/cli/interactive.py`
**Dependencies:** STEP 1
**Time:** 30 minutes

### 2.1 Import CommandValidationError
**Location:** Top of file, imports section
**Action:** ADD to imports

```python
from src.interactive.command_processor import CommandProcessor, CommandValidationError
```

### 2.2 Update Error Handling in Main Loop
**Location:** Interactive loop (around line 150-200)
**Action:** REPLACE try-except block

**FIND:**
```python
try:
    result = command_processor.process_command(user_input)
    console.print(result.message)
except Exception as e:
    logger.exception("Unexpected error processing command")
    console.print(f"[red]Error: {e}[/red]")
```

**REPLACE WITH:**
```python
try:
    result = command_processor.process_command(user_input)
    console.print(result.message)
except CommandValidationError as e:
    console.print(f"[red]Error: {e}[/red]")
    console.print(f"[yellow]Available commands: /{', /'.join(e.available_commands)}[/yellow]")
    console.print("[dim]Type /help for usage information[/dim]")
except Exception as e:
    logger.exception("Unexpected error processing command")
    console.print(f"[red]Unexpected error: {e}[/red]")
```

### 2.3 Update Prompt Indicator
**Location:** Prompt setup (around line 100-150)
**Action:** REPLACE prompt text

**FIND:**
```python
prompt_text = "obra> "
```

**REPLACE WITH:**
```python
prompt_text = "obra[orch]> "
```

**Verification:**
```bash
# Check syntax
python -m py_compile src/cli/interactive.py

# Manual test (visual verification)
python -m src.cli interactive
# Try: help, /help, invalid, /invalid
```

---

## STEP 3: Update Input Manager (Tab Completion)

**File:** `src/interactive/input_manager.py`
**Dependencies:** STEP 1
**Time:** 45 minutes

### 3.1 Update SLASH_COMMANDS List
**Location:** InputManager class or module constants
**Action:** REPLACE slash commands list

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

### 3.2 Update Completer Logic
**Location:** CommandCompleter class, get_completions() method
**Action:** REPLACE method (if exists, otherwise INSERT)

```python
def get_completions(self, document, complete_event):
    """Provide tab completions for slash commands.

    Only completes if user input starts with '/'.
    """
    text = document.text_before_cursor

    # Only complete if text starts with '/'
    if text.startswith('/'):
        word = text[1:]  # Remove leading slash for matching
        for cmd in SLASH_COMMANDS:
            if cmd[1:].startswith(word):  # Match without slash
                yield Completion(
                    cmd,
                    start_position=-len(text),
                    display_meta="Command"
                )
```

### 3.3 Add Bottom Toolbar
**Location:** PromptSession setup
**Action:** ADD bottom_toolbar parameter

```python
session = PromptSession(
    message="obra[orch]> ",
    completer=CommandCompleter(),
    complete_while_typing=True,
    bottom_toolbar="Type naturally to talk to orchestrator, or /help for commands",
)
```

**Verification:**
```bash
# Check syntax
python -m py_compile src/interactive/input_manager.py

# Manual test (tab completion)
python -m src.cli interactive
# Type: /he<TAB> (should complete to /help)
# Type: /st<TAB> (should show /status, /stop)
```

---

## STEP 4: Write Unit Tests

**File:** `tests/test_command_processor.py`
**Dependencies:** STEP 1-3
**Time:** 120 minutes

### 4.1 Add Test Class for New Behavior
**Location:** End of file
**Action:** INSERT

```python
class TestCommandProcessorNewBehavior:
    """Test new default-to-orch behavior (v1.5.0)."""

    def test_natural_text_sent_to_orchestrator(self, mock_orchestrator):
        """Natural text without slash goes to orchestrator."""
        processor = CommandProcessor(orchestrator=mock_orchestrator)
        result = processor.process_command("create epic for auth")
        assert result.success
        assert mock_orchestrator.receive_message.called

    def test_slash_command_requires_validity(self):
        """Invalid slash commands raise error."""
        processor = CommandProcessor()
        with pytest.raises(CommandValidationError) as exc:
            processor.process_command("/invalid-command")
        assert "Unknown command" in str(exc.value)
        assert "invalid-command" in str(exc.value)
        assert len(exc.value.available_commands) > 0

    def test_help_requires_slash(self, mock_orchestrator):
        """Help command now requires slash prefix."""
        processor = CommandProcessor(orchestrator=mock_orchestrator)

        # Without slash - sent to orchestrator
        result = processor.process_command("help")
        assert result.success
        assert mock_orchestrator.receive_message.called

        # With slash - shows help
        mock_orchestrator.reset_mock()
        result = processor.process_command("/help")
        assert result.success
        assert "Interactive Mode Commands" in result.message
        assert not mock_orchestrator.receive_message.called

    def test_status_requires_slash(self, mock_orchestrator):
        """Status command now requires slash prefix."""
        processor = CommandProcessor(orchestrator=mock_orchestrator)

        # Without slash - sent to orchestrator
        result = processor.process_command("status")
        assert result.success
        assert mock_orchestrator.receive_message.called

        # With slash - shows status
        mock_orchestrator.reset_mock()
        result = processor.process_command("/status")
        assert result.success
        # Status logic depends on implementation

    def test_to_claude_requires_slash(self, mock_orchestrator, mock_claude):
        """to-claude command requires slash prefix."""
        processor = CommandProcessor(
            orchestrator=mock_orchestrator,
            claude=mock_claude
        )

        # Without slash - sent to orchestrator
        result = processor.process_command("to-claude fix bug")
        assert result.success
        assert mock_orchestrator.receive_message.called
        assert not mock_claude.send_message.called

        # With slash - sent to Claude
        mock_orchestrator.reset_mock()
        result = processor.process_command("/to-claude fix bug")
        assert result.success
        assert not mock_orchestrator.receive_message.called
        assert mock_claude.send_message.called

    def test_empty_input_rejected(self):
        """Empty input returns error."""
        processor = CommandProcessor()
        result = processor.process_command("")
        assert not result.success
        assert "Empty input" in result.message

    def test_whitespace_only_rejected(self):
        """Whitespace-only input returns error."""
        processor = CommandProcessor()
        result = processor.process_command("   \t  \n  ")
        assert not result.success

    def test_slash_must_be_first_character(self, mock_orchestrator):
        """Slash in middle of message is part of natural text."""
        processor = CommandProcessor(orchestrator=mock_orchestrator)
        result = processor.process_command("use /api/endpoint in implementation")
        assert result.success
        assert mock_orchestrator.receive_message.called
        # Verify message contains the slash
        call_args = mock_orchestrator.receive_message.call_args
        assert "/api/endpoint" in call_args[0][0]

    def test_all_system_commands_require_slash(self):
        """All system commands must have slash prefix."""
        processor = CommandProcessor()
        system_commands = ['pause', 'resume', 'stop']

        for cmd in system_commands:
            # Without slash - sent to orchestrator (won't error)
            result = processor.process_command(cmd)
            assert result.success

            # With slash - executes command (may fail if preconditions not met)
            try:
                result = processor.process_command(f"/{cmd}")
                # Command parsed correctly (execution may fail due to state)
            except CommandValidationError:
                pytest.fail(f"/{cmd} should be a valid command")

    def test_single_slash_rejected(self):
        """Single slash character is invalid command."""
        processor = CommandProcessor()
        with pytest.raises(CommandValidationError):
            processor.process_command("/")

    def test_slash_with_whitespace_rejected(self):
        """Slash followed by whitespace is invalid."""
        processor = CommandProcessor()
        with pytest.raises(CommandValidationError):
            processor.process_command("/   ")

    def test_case_insensitive_commands(self):
        """Slash commands are case-insensitive."""
        processor = CommandProcessor()
        result1 = processor.process_command("/HELP")
        result2 = processor.process_command("/help")
        result3 = processor.process_command("/HeLp")
        assert result1.success == result2.success == result3.success
        assert "Interactive Mode Commands" in result1.message

    def test_multiline_natural_text(self, mock_orchestrator):
        """Multiline natural text sent to orchestrator."""
        processor = CommandProcessor(orchestrator=mock_orchestrator)
        message = """create epic for authentication with:
        - OAuth integration
        - JWT tokens
        - Session management"""
        result = processor.process_command(message)
        assert result.success
        assert mock_orchestrator.receive_message.called
```

### 4.2 Add Fixtures (if needed)
**Location:** Top of test file or conftest.py
**Action:** INSERT

```python
@pytest.fixture
def mock_orchestrator():
    """Mock orchestrator for testing command routing."""
    orchestrator = MagicMock()
    orchestrator.receive_message.return_value = "Orchestrator received message"
    return orchestrator

@pytest.fixture
def mock_claude():
    """Mock Claude agent for testing /to-claude routing."""
    claude = MagicMock()
    claude.send_message.return_value = "Claude received message"
    return claude
```

**Verification:**
```bash
# Run new tests
pytest tests/test_command_processor.py::TestCommandProcessorNewBehavior -v

# Check coverage
pytest tests/test_command_processor.py --cov=src/interactive/command_processor --cov-report=term
```

---

## STEP 5: Update Documentation

**File:** `docs/development/INTERACTIVE_STREAMING_QUICKREF.md`
**Dependencies:** STEP 1-4
**Time:** 45 minutes

### 5.1 Update Command Reference Section
**Action:** REPLACE command list

**OLD:**
```
## Commands

- `help` - Show help
- `/to-obra <message>` - Send to orchestrator
- `/to-claude <message>` - Send to Claude
```

**NEW:**
```
## Commands

### Default Behavior
**Natural language (no prefix)** - Send message to orchestrator

### Slash Commands (require `/` prefix)
- `/help` - Show help message
- `/status` - Show orchestration status
- `/pause` - Pause before next checkpoint
- `/resume` - Resume paused orchestration
- `/stop` - Stop gracefully
- `/to-claude <message>` - Send to Claude Code implementer
- `/override-decision <choice>` - Override decision (proceed/retry/clarify/escalate)

**Important**: All slash commands MUST start with `/` as first character. Invalid slash commands are rejected.
```

### 5.2 Update Examples Section
**Action:** ADD examples

```markdown
## Examples

### Natural Language to Orchestrator (Default)
```
obra[orch]> create epic for user authentication system
obra[orch]> implement login with JWT
obra[orch]> show me the project status
```

### Slash Commands for System Operations
```
obra[orch]> /help
obra[orch]> /status
obra[orch]> /to-claude fix the type error in src/auth.py
obra[orch]> /pause
```

### Invalid Usage (Rejected)
```
obra[orch]> /invalid-command  ❌ Error: Unknown command
obra[orch]> /                 ❌ Error: Invalid command
```
```

---

## STEP 6: Update CHANGELOG

**File:** `CHANGELOG.md`
**Dependencies:** STEP 1-5
**Time:** 15 minutes

### 6.1 Add v1.5.0 Entry
**Location:** Top of file, after [Unreleased]
**Action:** INSERT

```markdown
## [1.5.0] - 2025-11-11

### Changed - BREAKING
- **Interactive Mode UX Improvement**: Natural text now defaults to orchestrator
  - Natural language messages (no slash prefix) sent directly to orchestrator
  - ALL system commands now require '/' prefix as first character
  - Updated commands: `/help`, `/status`, `/pause`, `/resume`, `/stop`, `/to-claude`, `/override-decision`
  - Removed `/to-obra` command (natural text is default)
  - Invalid slash commands rejected with helpful error message
  - Prompt indicator changed to `obra[orch]>` for clarity
  - Added tab completion for all slash commands
  - Added bottom toolbar with usage hint

### Migration Guide
**Old Syntax → New Syntax:**
- `help` → `/help`
- `status` → `/status`
- `/to-obra create epic for auth` → `create epic for auth`
- `/to-claude fix bug` → `/to-claude fix bug` (unchanged)
- `pause` → `/pause`

**Rationale:** Eliminates friction for primary use case (orchestrator communication). Asymmetry between orchestrator (default) and Claude (/to-claude) is intentional.

### Added
- `CommandValidationError` exception for invalid slash commands
- Tab completion for all slash commands
- Bottom toolbar with usage hints
- 15+ new unit tests for command routing
- Comprehensive documentation in `INTERACTIVE_UX_IMPROVEMENT_PLAN.md`

### Technical Details
- `CommandProcessor.process_command()`: New routing logic
- `CommandProcessor._process_slash_command()`: Slash command validation
- `CommandProcessor._send_to_orchestrator()`: Default routing for natural text
- Updated help text with new command syntax
- Error handling improvements in `src/cli/interactive.py`
```

---

## STEP 7: Final Verification

**Dependencies:** STEP 1-6
**Time:** 60 minutes

### 7.1 Run Full Test Suite
```bash
# All tests
pytest -v

# With coverage
pytest --cov=src --cov-report=term --cov-report=html

# Check coverage threshold (should still be ≥91%)
```

### 7.2 Manual Interactive Testing
```bash
# Launch interactive mode
python -m src.cli interactive

# Test cases:
# 1. Natural language routing
obra[orch]> create epic for authentication

# 2. Slash command validation
obra[orch]> /help
obra[orch]> /status

# 3. Invalid slash command
obra[orch]> /invalid
# Expected: Error with available commands list

# 4. to-claude routing
obra[orch]> /to-claude implement login endpoint

# 5. Tab completion
obra[orch]> /he<TAB>
# Expected: Completes to /help

# 6. Edge cases
obra[orch]> /
# Expected: Error
obra[orch]>
# Expected: Error (empty input)
obra[orch]> use /api/endpoint in code
# Expected: Sent to orchestrator (slash in middle)

# 7. System commands
obra[orch]> /pause
obra[orch]> /resume
obra[orch]> /stop
```

### 7.3 Regression Testing
```bash
# Ensure existing functionality still works
pytest tests/test_orchestrator.py -v
pytest tests/test_state.py -v
pytest tests/test_integration_e2e.py -v
```

### 7.4 Type Checking
```bash
# Run mypy
mypy src/interactive/command_processor.py
mypy src/cli/interactive.py
mypy src/interactive/input_manager.py
```

### 7.5 Code Quality
```bash
# Linting
pylint src/interactive/command_processor.py
pylint src/cli/interactive.py

# Formatting (if using black)
black --check src/interactive/
```

---

## STEP 8: Commit Changes

**Dependencies:** STEP 1-7 (all tests pass)
**Time:** 15 minutes

### 8.1 Stage Files
```bash
git add src/interactive/command_processor.py
git add src/cli/interactive.py
git add src/interactive/input_manager.py
git add tests/test_command_processor.py
git add docs/development/INTERACTIVE_STREAMING_QUICKREF.md
git add docs/development/INTERACTIVE_UX_IMPROVEMENT_PLAN.md
git add docs/development/INTERACTIVE_UX_IMPLEMENTATION_CHECKLIST.md
git add CHANGELOG.md
```

### 8.2 Commit
```bash
git commit -m "feat: Improve interactive UX - default to orchestrator for natural language

BREAKING CHANGE: Interactive mode command syntax updated

- Natural text (no prefix) now defaults to orchestrator
- ALL system commands require '/' prefix (/help, /status, etc.)
- Removed /to-obra command (natural text is default)
- Invalid slash commands rejected with helpful errors
- Prompt changed to 'obra[orch]>' for clarity
- Added tab completion for all slash commands

Migration:
  OLD: /to-obra create epic → NEW: create epic
  OLD: help → NEW: /help
  OLD: status → NEW: /status

This change eliminates friction for the primary use case (orchestrator
communication) while maintaining clear syntax for system commands.

Test coverage: 15+ new tests, 91% overall coverage maintained

Closes: #UX-001 (if applicable)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

### 8.3 Verify Commit
```bash
# Check commit
git show HEAD

# Verify all files included
git diff HEAD~1 --stat
```

---

## SUCCESS CRITERIA CHECKLIST

- [ ] Natural language input routes to orchestrator (no slash)
- [ ] All system commands require '/' prefix
- [ ] Invalid slash commands rejected with helpful error
- [ ] Available commands shown in error message
- [ ] Tab completion works for all slash commands
- [ ] Prompt shows `obra[orch]>`
- [ ] Bottom toolbar shows usage hint
- [ ] `/help` displays updated command syntax
- [ ] Empty input handled gracefully
- [ ] Whitespace-only input rejected
- [ ] Slash in middle of message preserved
- [ ] `/to-claude` still works correctly
- [ ] All 790+ existing tests pass
- [ ] 15+ new tests added and passing
- [ ] Test coverage ≥91% maintained
- [ ] Type checking passes (mypy)
- [ ] Linting passes (pylint)
- [ ] Documentation updated (QUICKREF, CHANGELOG)
- [ ] Manual testing completed
- [ ] Regression testing completed
- [ ] Changes committed with semantic commit message

---

## ROLLBACK PLAN

If critical issues found after deployment:

1. **Revert commit:**
   ```bash
   git revert HEAD
   ```

2. **Restore old behavior:**
   - Revert `CommandProcessor.process_command()` to old routing
   - Add back `/to-obra` command to COMMANDS dict
   - Revert help text to previous version
   - Remove `CommandValidationError` handling from CLI

3. **Test rollback:**
   ```bash
   pytest -v
   python -m src.cli interactive
   ```

4. **Document rollback:**
   - Add entry to CHANGELOG.md explaining rollback
   - Create issue for addressing original problem

---

## ESTIMATED TIME BREAKDOWN

| Step | Task | Time |
|------|------|------|
| 1 | Update CommandProcessor | 90 min |
| 2 | Update CLI interactive loop | 30 min |
| 3 | Update InputManager | 45 min |
| 4 | Write unit tests | 120 min |
| 5 | Update documentation | 45 min |
| 6 | Update CHANGELOG | 15 min |
| 7 | Final verification | 60 min |
| 8 | Commit changes | 15 min |
| **Total** | | **6.5 hours** |

---

## DEPENDENCIES GRAPH

```
STEP 1 (CommandProcessor)
  ↓
STEP 2 (CLI loop) ← depends on CommandValidationError
  ↓
STEP 3 (InputManager) ← independent, can run parallel to STEP 2
  ↓
STEP 4 (Tests) ← depends on STEP 1, 2, 3
  ↓
STEP 5 (Docs) ← depends on STEP 1-4 (validation)
  ↓
STEP 6 (CHANGELOG) ← depends on STEP 1-5
  ↓
STEP 7 (Verification) ← depends on all
  ↓
STEP 8 (Commit) ← depends on STEP 7 (all tests pass)
```

---

**Status**: ✅ Ready for execution
**Execution Mode**: Sequential (follow step order)
**Next Action**: Begin STEP 1 - Update CommandProcessor
