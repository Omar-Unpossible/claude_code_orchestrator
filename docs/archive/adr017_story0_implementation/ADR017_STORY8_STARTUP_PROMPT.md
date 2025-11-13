# ADR-017 Story 8 Startup Prompt

**Story 8 of 9** (ADR-017 Implementation)

**Context**: You're implementing ADR-017 (Unified Execution Architecture) for Obra. Stories 0-7 are complete. Now implement Story 8.

---

## What You're Building

**Story 8**: Safety Enhancements - Destructive Operation Breakpoints (10 hours)

**Purpose**: Add human-in-the-loop confirmation for destructive NL operations (UPDATE/DELETE) to prevent accidental data loss.

**Key Objectives**:
- Trigger breakpoints before executing destructive NL operations
- Implement confirmation workflow in interactive mode
- Add override mechanism for automation (CLI flag + config)
- Audit logging for all destructive operations
- Safe defaults (abort if non-interactive)

**Part of**: v1.7.1 (follow-up release after v1.7.0)

---

## What's Already Complete

### Story 0: Testing Infrastructure ✅
- Health checks, smoke tests, integration tests framework
- THE CRITICAL TEST baseline established

### Story 1: Architecture Documentation ✅
- ADR-017 written, approved, and marked as IMPLEMENTED
- Architecture diagrams completed and updated for v1.7.0

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

### Story 7: Documentation Updates ✅
- **Updated Docs**: NL_COMMAND_GUIDE.md, ARCHITECTURE.md, CHANGELOG.md, CLAUDE.md
- **Migration Guide**: ADR017_MIGRATION_GUIDE.md created
- **ADR-017**: Marked as IMPLEMENTED
- **Version**: All docs updated to v1.7.0, dated November 13, 2025

---

## The Problem

Story 7 completed v1.7.0 core refactor. However, destructive NL operations (UPDATE/DELETE) currently lack safety checks:

1. **No confirmation prompts**: "Delete task 5" executes immediately without warning
2. **No cascade warnings**: User unaware of dependent entities affected
3. **No undo capability**: Once executed, destructive operations are permanent
4. **Non-interactive risk**: Automation could execute destructive ops without oversight

**Example Risk Scenario**:
```
User: "Delete the tetris project"
→ NL Parser: COMMAND, DELETE, entity=project, id=1
→ IntentToTaskConverter: Task("Delete project 1")
→ Orchestrator: Execute immediately (no confirmation!)
→ Result: Project + 50 child tasks deleted without warning
```

**Why This Matters**:
- **Data Loss Prevention**: Prevent accidental deletions
- **User Trust**: Confirm before destructive actions
- **Compliance**: Audit trail for sensitive operations
- **Safety Culture**: Fail-safe defaults (abort if uncertain)

---

## The Solution

**Safety Enhancement Strategy**:
```
NL Destructive Operation Detected
    ↓
BreakpointManager checks operation type
    ↓
If UPDATE or DELETE:
    ↓
Trigger "destructive_nl_operation" breakpoint
    ↓
Interactive Mode:
  - Display operation details (what will be affected)
  - Prompt: "Confirm destructive operation? (y/n/details)"
  - User confirms → Proceed
  - User declines → Abort with TaskStoppedException
    ↓
Non-Interactive Mode:
  - Log warning
  - Abort by default (safe)
  - OR use --confirm-destructive flag to auto-approve
    ↓
Audit Log:
  - Timestamp, user, operation, entity, confirmation status
  - Useful for security audits
```

**Key Design Decisions**:
1. **Fail-Safe Default**: Abort destructive operations if no confirmation
2. **Interactive First**: Rich prompts in interactive mode
3. **Automation Support**: CLI flag `--confirm-destructive` for scripts
4. **Audit Trail**: Log ALL destructive operations (approved or aborted)

---

## Implementation Plan

### Step 1: Update BreakpointManager with Destructive Operation Rule

**Action**: Add breakpoint rule for destructive NL operations

**File**: `src/orchestration/breakpoint_manager.py`

**Changes**:
```python
# Add new breakpoint rule
BREAKPOINT_RULES = {
    # ... existing rules ...

    'destructive_nl_operation': {
        'description': 'Human confirmation required for destructive NL operations',
        'severity': 'HIGH',
        'conditions': [
            lambda task: task.get('source') == 'natural_language',
            lambda task: task.get('operation_type') in ['UPDATE', 'DELETE']
        ],
        'action': 'request_confirmation',
        'auto_proceed': False  # Never auto-proceed destructive ops
    }
}
```

**Method to Add**:
```python
def should_trigger_destructive_nl_breakpoint(self, task: Task) -> bool:
    """Check if task is a destructive NL operation requiring confirmation.

    Args:
        task: Task object to check

    Returns:
        True if task is destructive NL operation (UPDATE/DELETE from natural language)
    """
    if not task.metadata:
        return False

    source = task.metadata.get('source')
    operation = task.metadata.get('operation_type')

    return (source == 'natural_language' and
            operation in ['UPDATE', 'DELETE'])
```

**Tests to Write**:
- Test: Task with source=natural_language AND operation=DELETE → returns True
- Test: Task with source=natural_language AND operation=UPDATE → returns True
- Test: Task with source=natural_language AND operation=CREATE → returns False
- Test: Task with source=cli AND operation=DELETE → returns False (CLI operations trusted)
- Test: Task without metadata → returns False

---

### Step 2: Implement Confirmation Workflow in Orchestrator

**Action**: Add confirmation check before executing destructive tasks

**File**: `src/orchestrator.py`

**Method to Add/Update**:
```python
def _check_destructive_operation_confirmation(self, task: Task) -> bool:
    """Check for destructive operation and request confirmation if needed.

    Args:
        task: Task to check

    Returns:
        True if user confirmed or confirmation not required
        False if user declined or non-interactive mode without override

    Raises:
        TaskStoppedException: If user declines or confirmation timeout
    """
    if not self.breakpoint_manager.should_trigger_destructive_nl_breakpoint(task):
        return True  # Not destructive, proceed

    # Log destructive operation attempt
    self.logger.warning(
        f"Destructive NL operation detected: {task.metadata.get('operation_type')} "
        f"on {task.metadata.get('entity_type')} (Task ID: {task.id})"
    )

    # Check if interactive mode
    if not self.interactive_mode:
        # Non-interactive mode: Check for override flag
        if self.config.get('nl_commands.auto_confirm_destructive', False):
            self.logger.info("Auto-confirming destructive operation (override enabled)")
            self._audit_log_destructive_op(task, confirmed=True, method='auto_confirm')
            return True
        else:
            # Safe default: Abort
            self.logger.error("Aborting destructive operation (non-interactive, no override)")
            self._audit_log_destructive_op(task, confirmed=False, method='auto_abort')
            raise TaskStoppedException("Destructive operation aborted (non-interactive mode)")

    # Interactive mode: Request confirmation
    return self._request_confirmation_interactive(task)
```

**Helper Method**:
```python
def _request_confirmation_interactive(self, task: Task) -> bool:
    """Request user confirmation for destructive operation in interactive mode.

    Args:
        task: Task requiring confirmation

    Returns:
        True if user confirmed

    Raises:
        TaskStoppedException: If user declined or timeout
    """
    operation = task.metadata.get('operation_type')
    entity_type = task.metadata.get('entity_type')
    entity_id = task.metadata.get('entity_identifier')

    # Display operation details
    print("\n" + "=" * 60)
    print(f"⚠️  DESTRUCTIVE OPERATION CONFIRMATION REQUIRED")
    print("=" * 60)
    print(f"Operation: {operation}")
    print(f"Entity: {entity_type} (ID: {entity_id})")
    print(f"Original Message: {task.metadata.get('original_message')}")

    # TODO Story 9: Show cascade implications, before/after state

    print("\nConfirm destructive operation?")
    print("  y/yes    - Confirm and proceed")
    print("  n/no     - Abort operation")
    print("  d/details - Show full operation details")
    print("=" * 60)

    # Get user input with timeout
    timeout = self.config.get('breakpoints.confirmation_timeout_seconds', 60)

    try:
        response = self.input_manager.get_input_with_timeout(
            prompt="Confirm (y/n/d)? ",
            timeout=timeout
        )
    except TimeoutError:
        self.logger.warning("Confirmation timeout - aborting destructive operation")
        self._audit_log_destructive_op(task, confirmed=False, method='timeout')
        raise TaskStoppedException("Destructive operation aborted (confirmation timeout)")

    response = response.lower().strip()

    if response in ['y', 'yes']:
        self._audit_log_destructive_op(task, confirmed=True, method='interactive')
        print("✓ Confirmed. Proceeding with destructive operation...\n")
        return True
    elif response in ['d', 'details']:
        # Show full operation context
        print("\nOperation Context:")
        pprint(task.metadata)
        # Recurse to ask again after showing details
        return self._request_confirmation_interactive(task)
    else:
        self._audit_log_destructive_op(task, confirmed=False, method='user_declined')
        print("✗ Operation aborted.\n")
        raise TaskStoppedException("User declined destructive operation")
```

**Audit Logging Method**:
```python
def _audit_log_destructive_op(self, task: Task, confirmed: bool, method: str):
    """Log destructive operation for audit trail.

    Args:
        task: Task being executed
        confirmed: Whether operation was confirmed
        method: Confirmation method (interactive/auto_confirm/auto_abort/timeout/user_declined)
    """
    audit_entry = {
        'timestamp': datetime.now().isoformat(),
        'task_id': task.id,
        'operation': task.metadata.get('operation_type'),
        'entity_type': task.metadata.get('entity_type'),
        'entity_id': task.metadata.get('entity_identifier'),
        'confirmed': confirmed,
        'confirmation_method': method,
        'user': os.getenv('USER', 'unknown'),
        'original_message': task.metadata.get('original_message')
    }

    # Log to audit file (append mode)
    audit_file = self.config.get('audit.destructive_operations_file',
                                   'logs/destructive_operations_audit.jsonl')
    os.makedirs(os.path.dirname(audit_file), exist_ok=True)

    with open(audit_file, 'a') as f:
        f.write(json.dumps(audit_entry) + '\n')

    self.logger.info(f"Audit logged: {audit_entry}")
```

**Integration Point**:

Update `execute_task()` method to call confirmation check:
```python
def execute_task(self, task_id: int, ...) -> Dict:
    """Execute task with full orchestration pipeline."""
    # ... existing code ...

    # NEW: Check for destructive operation confirmation (before agent execution)
    self._check_destructive_operation_confirmation(task)

    # ... continue with agent execution ...
```

**Tests to Write**:
- Test: Interactive mode, user confirms (y) → returns True, audit logged
- Test: Interactive mode, user declines (n) → raises TaskStoppedException, audit logged
- Test: Interactive mode, user requests details (d) → shows context, asks again
- Test: Interactive mode, timeout → raises TaskStoppedException, audit logged
- Test: Non-interactive mode, auto_confirm=True → returns True, audit logged
- Test: Non-interactive mode, auto_confirm=False → raises TaskStoppedException, audit logged
- Test: Non-destructive operation → returns True immediately (no prompt)

---

### Step 3: Add CLI Override Flag

**Action**: Add `--confirm-destructive` flag for automation

**File**: `src/cli.py`

**Changes**:
```python
@click.command()
@click.argument('task_id', type=int)
@click.option('--confirm-destructive', is_flag=True,
              help='Auto-confirm destructive operations (use with caution)')
def task_execute(task_id: int, confirm_destructive: bool):
    """Execute a task through orchestrator."""
    config = Config.load()

    # Override config if flag provided
    if confirm_destructive:
        config.set('nl_commands.auto_confirm_destructive', True)
        click.echo("⚠️  Auto-confirming destructive operations (override enabled)")

    orchestrator = Orchestrator(config)
    result = orchestrator.execute_task(task_id)

    # ... display result ...
```

**Usage Example**:
```bash
# Normal execution (will prompt for confirmation if destructive)
obra task execute 123

# Auto-confirm (for automation, use with caution)
obra task execute 123 --confirm-destructive
```

**Tests to Write**:
- Test: CLI with --confirm-destructive flag → config updated correctly
- Test: CLI without flag → config unchanged
- Test: Integration: CLI + destructive task + flag → executes without prompt

---

### Step 4: Add Configuration Option

**Action**: Add config option for auto-confirming destructive operations

**File**: `config/default_config.yaml`

**Changes**:
```yaml
nl_commands:
  enabled: true
  # ... existing config ...

  # Auto-confirm destructive operations (UPDATE/DELETE)
  # WARNING: Setting this to true bypasses safety confirmations
  # Recommended: false (prompt user), true only for trusted automation
  auto_confirm_destructive: false

breakpoints:
  # ... existing breakpoint config ...

  # Timeout for confirmation prompts (seconds)
  confirmation_timeout_seconds: 60

audit:
  # Audit log file for destructive operations
  destructive_operations_file: logs/destructive_operations_audit.jsonl
```

**Documentation**:
Update `docs/guides/CONFIGURATION_PROFILES_GUIDE.md` with new options

---

### Step 5: Update InputManager with Timeout Support

**Action**: Add timeout support to input manager for confirmation prompts

**File**: `src/utils/input_manager.py` (if not already present)

**Method to Add**:
```python
def get_input_with_timeout(self, prompt: str, timeout: int = 60) -> str:
    """Get user input with timeout.

    Args:
        prompt: Prompt to display
        timeout: Timeout in seconds

    Returns:
        User input string

    Raises:
        TimeoutError: If user doesn't respond within timeout
    """
    import signal

    def timeout_handler(signum, frame):
        raise TimeoutError("Input timeout")

    # Set timeout
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout)

    try:
        user_input = input(prompt)
        signal.alarm(0)  # Cancel alarm
        return user_input
    except TimeoutError:
        signal.alarm(0)  # Cancel alarm
        raise
```

**Note**: For Windows compatibility, may need alternative timeout implementation (threading-based)

**Tests to Write**:
- Test: User responds within timeout → returns input
- Test: User doesn't respond → raises TimeoutError after timeout
- Test: Timeout=0 → no timeout (wait indefinitely)

---

### Step 6: Integration with IntentToTaskConverter

**Action**: Ensure destructive operation metadata is included in Task objects

**File**: `src/orchestration/intent_to_task_converter.py`

**Verify/Update**:
```python
def convert(self, parsed_intent: OperationContext, project_id: int,
            original_message: str) -> Task:
    """Convert parsed NL intent to Task object."""
    # ... existing code ...

    task_data = {
        'title': self._generate_title(parsed_intent),
        'description': self._generate_description(parsed_intent),
        'metadata': {
            'source': 'natural_language',
            'original_message': original_message,
            'operation_type': parsed_intent.operation,  # CREATE/UPDATE/DELETE/QUERY
            'entity_type': parsed_intent.entity_type,   # project/epic/story/task
            'entity_identifier': parsed_intent.identifier,
            'confidence': parsed_intent.confidence,
            'parsed_parameters': parsed_intent.parameters
        }
    }

    # ... create task ...
```

**Tests to Verify**:
- Test: DELETE operation → metadata includes operation_type='DELETE'
- Test: UPDATE operation → metadata includes operation_type='UPDATE'
- Test: CREATE operation → metadata includes operation_type='CREATE'
- Test: All tasks include source='natural_language'

---

## Acceptance Criteria

✅ **BreakpointManager Rule**:
- [ ] `destructive_nl_operation` rule added to BreakpointManager
- [ ] Rule triggers on UPDATE/DELETE operations from natural language source
- [ ] Rule severity set to HIGH, auto_proceed=False

✅ **Confirmation Workflow**:
- [ ] Confirmation check integrated into `orchestrator.execute_task()`
- [ ] Interactive mode displays operation details and prompts user
- [ ] User can confirm (y), decline (n), or request details (d)
- [ ] Timeout handling (default: 60 seconds) with safe abort

✅ **Non-Interactive Mode**:
- [ ] Safe default: Abort destructive operations without confirmation
- [ ] Override via `auto_confirm_destructive` config option
- [ ] Warning logged when auto-confirming

✅ **CLI Override**:
- [ ] `--confirm-destructive` flag added to `obra task execute` command
- [ ] Flag enables auto-confirmation for automation scripts
- [ ] Warning displayed when flag used

✅ **Audit Logging**:
- [ ] All destructive operations logged to audit file
- [ ] Audit includes: timestamp, task, operation, entity, confirmation status, method
- [ ] Audit file: `logs/destructive_operations_audit.jsonl` (JSONL format)

✅ **Configuration**:
- [ ] `nl_commands.auto_confirm_destructive` config option added (default: false)
- [ ] `breakpoints.confirmation_timeout_seconds` config option added (default: 60)
- [ ] `audit.destructive_operations_file` config option added
- [ ] Configuration documented in CONFIGURATION_PROFILES_GUIDE.md

✅ **Testing**:
- [ ] **Unit tests**: 15+ tests covering all confirmation scenarios
- [ ] **Integration tests**:
  - DELETE operation → confirmation prompt → user confirms → executed
  - DELETE operation → confirmation prompt → user declines → aborted
  - UPDATE operation → confirmation prompt → user confirms → executed
  - Non-interactive + auto_confirm=true → executes without prompt
  - Non-interactive + auto_confirm=false → aborts
  - Timeout scenario → aborts after timeout
- [ ] **Code coverage**: ≥90% on new code

✅ **Documentation**:
- [ ] CONFIGURATION_PROFILES_GUIDE.md updated with new config options
- [ ] Comments in code explaining confirmation workflow
- [ ] Audit log format documented

---

## Validation Commands

**Test confirmation workflow (interactive)**:
```bash
# Start interactive mode
python -m src.cli interactive

# Try destructive NL command
orchestrator> Delete task 5

# Should see confirmation prompt:
# ⚠️  DESTRUCTIVE OPERATION CONFIRMATION REQUIRED
# Operation: DELETE
# Entity: task (ID: 5)
# ...
# Confirm (y/n/d)?
```

**Test auto-confirm (CLI)**:
```bash
# Create test task
python -m src.cli task create "Test delete" --project 1

# Execute destructive operation with auto-confirm
python -m src.cli task execute <task_id> --confirm-destructive

# Should execute without prompt, audit log created
```

**Test non-interactive abort**:
```bash
# Set non-interactive mode (no terminal input available)
# Should abort destructive operations by default
```

**Check audit log**:
```bash
# View audit log
cat logs/destructive_operations_audit.jsonl

# Should contain JSONL entries for all destructive operations
```

---

## Common Pitfalls to Avoid

1. ❌ **Don't skip timeout handling**: Always timeout confirmation prompts (prevent hanging)
2. ❌ **Don't auto-confirm by default**: Safe default is abort (user must explicitly enable)
3. ❌ **Don't forget audit logging**: Log BOTH confirmed and declined operations
4. ❌ **Don't mix confirmation methods**: Keep interactive and non-interactive paths separate
5. ❌ **Don't assume UPDATE is safe**: Even updates can have destructive consequences
6. ❌ **Don't forget CLI operations**: Only NL operations should trigger confirmations (CLI trusted)
7. ❌ **Don't block on input in tests**: Mock `get_input_with_timeout()` in tests

---

## References

**Key Files**:
- `src/orchestration/breakpoint_manager.py` - Breakpoint rules
- `src/orchestrator.py` - Confirmation workflow integration
- `src/orchestration/intent_to_task_converter.py` - Metadata inclusion
- `src/utils/input_manager.py` - Timeout input support
- `src/cli.py` - CLI override flag
- `config/default_config.yaml` - Configuration options

**Related ADRs**:
- **ADR-017**: Unified Execution Architecture (this epic)
- **ADR-014**: Natural Language Command Interface
- **ADR-011**: Interactive Streaming Interface

**Test Files**:
- `tests/test_breakpoint_manager.py` - Unit tests for destructive rule
- `tests/test_orchestrator.py` - Unit tests for confirmation workflow
- `tests/integration/test_destructive_confirmation.py` - Integration tests (NEW)

**Documentation**:
- `docs/guides/CONFIGURATION_PROFILES_GUIDE.md` - Config documentation
- `docs/guides/NL_COMMAND_GUIDE.md` - User guide (update in Story 9)

---

## Upon Completion of Story 8

**Status**: Story 8 of 9 COMPLETE!

After Story 8, you will have:
- ✅ Destructive operation breakpoints implemented
- ✅ Confirmation workflow (interactive + non-interactive)
- ✅ Audit logging for security compliance
- ✅ CLI override for automation
- ✅ 15+ new tests (all passing)
- ✅ Safe defaults (abort if uncertain)

**Next Steps**: Generate startup prompt for Story 9 (Confirmation Workflow UI Polish)

**IMPORTANT - Durable Pattern**:
Upon completing Story 8, you MUST generate the startup prompt for Story 9 following the same format as this document. Continue this pattern for all remaining stories.

---

## Story 9 Preview

**Story 9**: Confirmation Workflow UI Polish (6 hours)
- Rich confirmation prompts (color-coded, before/after state)
- Cascade implications display ("Will delete 5 child tasks")
- Simulate mode (dry-run)
- Enhanced help text during confirmation
- User testing and feedback

**Estimate**: 6 hours (UX enhancement, builds on Story 8)

---

**Ready to start? Implement Story 8: Destructive Operation Breakpoints.**

Remember:
- Safe defaults: abort if uncertain
- Audit everything: both confirmed and declined operations
- Timeout confirmations: don't hang indefinitely
- Test both interactive and non-interactive modes
- Upon completion, generate Story 9 startup prompt
