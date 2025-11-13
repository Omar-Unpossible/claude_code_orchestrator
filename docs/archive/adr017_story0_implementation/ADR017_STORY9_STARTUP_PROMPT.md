# ADR-017 Story 9 Startup Prompt

**Story 9 of 9** (ADR-017 Implementation - FINAL STORY)

**Context**: You're implementing ADR-017 (Unified Execution Architecture) for Obra. Stories 0-8 are complete. Now implement Story 9 (FINAL).

---

## What You're Building

**Story 9**: Confirmation Workflow UI Polish (6 hours) - **FINAL STORY**

**Purpose**: Enhance the confirmation UI with rich prompts, cascade implications, dry-run simulation, and improved UX for destructive operations.

**Key Objectives**:
- Rich confirmation prompts (color-coded, structured display)
- Cascade implications display ("Will delete 5 child tasks")
- Dry-run/simulate mode (preview changes without executing)
- Enhanced help text during confirmation
- User testing and feedback integration

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

### Story 8: Safety Enhancements - Destructive Operation Breakpoints ✅
- **Component**: Confirmation workflow for destructive NL operations (UPDATE/DELETE)
- **Features**:
  - BreakpointManager rule for destructive operations
  - Interactive confirmation prompts
  - Non-interactive safe defaults (abort without override)
  - CLI flag `--confirm-destructive` for automation
  - Audit logging (JSONL format)
- **Implementation**:
  - `src/orchestration/breakpoint_manager.py`: `should_trigger_destructive_nl_breakpoint()`
  - `src/orchestrator.py`: Confirmation workflow methods
  - `src/utils/input_manager.py`: Timeout support
  - `config/default_config.yaml`: New config options
- **Integration**: Confirmation check integrated into `execute_task()`

---

## The Problem

Story 8 implemented basic confirmation workflow, but UX can be significantly improved:

1. **Plain text prompts**: No visual hierarchy or emphasis
2. **No cascade preview**: User can't see what else will be affected
3. **No dry-run option**: Can't preview changes before confirming
4. **Limited help**: No guidance on what each choice means
5. **No color coding**: Hard to distinguish critical vs informational text

**Example Current UX** (Story 8):
```
============================================================
⚠️  DESTRUCTIVE OPERATION CONFIRMATION REQUIRED
============================================================
Operation: DELETE
Entity: project (ID: 1)
Original Message: Delete the tetris project

Confirm destructive operation?
  y/yes    - Confirm and proceed
  n/no     - Abort operation
  d/details - Show full operation details
============================================================
Confirm (y/n/d)?
```

**Problems**:
- ❌ No information about cascading deletes (50 child tasks)
- ❌ No preview of what will be deleted
- ❌ No option to simulate first
- ❌ Plain text, no color emphasis
- ❌ No help on recovery options

---

## The Solution

**Enhanced Confirmation UI Strategy**:
```
Destructive Operation Detected
    ↓
Display Rich Prompt:
  - Color-coded header (red for DELETE, yellow for UPDATE)
  - Entity summary (name, description, created date)
  - Cascade implications (child entities affected)
  - Impact assessment (files changed, data deleted)
    ↓
Offer Choices:
  - [y] Confirm and proceed
  - [n] Abort operation
  - [s] Simulate/dry-run (show changes without executing)
  - [c] Show cascade details
  - [h] Help (explain options)
    ↓
If Simulate:
  - Show before/after state
  - List all affected entities
  - Estimate operation duration
  - Return to prompt (not executed)
    ↓
If Confirm:
  - Log audit entry with cascade info
  - Proceed with execution
```

**Key Design Principles**:
1. **Progressive Disclosure**: Show summary first, details on demand
2. **Visual Hierarchy**: Use color and formatting for emphasis
3. **Safe Exploration**: Allow simulation without commitment
4. **Contextual Help**: Provide guidance at decision points
5. **Undo Awareness**: Explain what can/can't be undone

---

## Implementation Plan

### Step 1: Add Color-Coded Rich Prompts

**Action**: Enhance confirmation display with color and structure

**File**: `src/orchestrator.py`

**Changes**:
```python
def _request_confirmation_interactive(self, task: Task) -> bool:
    """Enhanced confirmation prompt with rich formatting."""
    from colorama import Fore, Back, Style, init
    init(autoreset=True)  # Auto-reset colors

    operation = task.task_metadata.get('operation_type')
    entity_type = task.task_metadata.get('entity_type')
    entity_id = task.task_metadata.get('entity_identifier')

    # Get entity details for rich display
    entity_details = self._get_entity_details(entity_type, entity_id)

    # Color-code by operation
    if operation == 'DELETE':
        header_color = Fore.RED + Back.WHITE
        op_symbol = "🗑️"
    elif operation == 'UPDATE':
        header_color = Fore.YELLOW + Back.BLACK
        op_symbol = "✏️"
    else:
        header_color = Fore.CYAN
        op_symbol = "⚙️"

    # Display rich header
    print("\n" + "=" * 70)
    print(header_color + f"{op_symbol}  DESTRUCTIVE OPERATION CONFIRMATION" + Style.RESET_ALL)
    print("=" * 70)

    # Entity summary
    print(f"\n{Fore.CYAN}Operation:{Style.RESET_ALL} {Fore.WHITE + Style.BRIGHT}{operation}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Entity:{Style.RESET_ALL} {entity_type} (ID: {entity_id})")
    if entity_details:
        print(f"{Fore.CYAN}Name:{Style.RESET_ALL} {entity_details.get('name', 'N/A')}")
        print(f"{Fore.CYAN}Description:{Style.RESET_ALL} {entity_details.get('description', 'N/A')[:100]}")
        print(f"{Fore.CYAN}Created:{Style.RESET_ALL} {entity_details.get('created_at', 'N/A')}")

    # Cascade implications
    cascade_info = self._get_cascade_implications(entity_type, entity_id, operation)
    if cascade_info['has_cascade']:
        print(f"\n{Fore.YELLOW + Style.BRIGHT}⚠️  CASCADE WARNING{Style.RESET_ALL}")
        print(f"This operation will affect {Fore.RED + Style.BRIGHT}{cascade_info['total_affected']}{Style.RESET_ALL} additional entities:")
        for affected_type, count in cascade_info['affected_entities'].items():
            print(f"  • {count} {affected_type}(s)")

    # Impact assessment
    impact = self._assess_operation_impact(entity_type, entity_id, operation)
    if impact['estimated_changes'] > 0:
        print(f"\n{Fore.CYAN}Estimated Impact:{Style.RESET_ALL}")
        print(f"  • Files affected: {impact['files_affected']}")
        print(f"  • Data deleted: ~{impact['estimated_size']}")
        print(f"  • Duration: ~{impact['estimated_duration']}s")

    # Options
    print(f"\n{Fore.GREEN}Choose an action:{Style.RESET_ALL}")
    print(f"  {Fore.GREEN}[y]{Style.RESET_ALL} Confirm and proceed")
    print(f"  {Fore.RED}[n]{Style.RESET_ALL} Abort operation")
    print(f"  {Fore.CYAN}[s]{Style.RESET_ALL} Simulate/dry-run (preview changes)")
    print(f"  {Fore.CYAN}[c]{Style.RESET_ALL} Show cascade details")
    print(f"  {Fore.CYAN}[h]{Style.RESET_ALL} Help (explain options)")
    print("=" * 70)

    # Get input with timeout
    timeout = self.config.get('breakpoints.confirmation_timeout_seconds', 60)

    try:
        response = self.input_manager.get_input_with_timeout(
            prompt=f"{Fore.WHITE}Choice (y/n/s/c/h)? {Style.RESET_ALL}",
            timeout=timeout
        )
    except TimeoutError:
        logger.warning("Confirmation timeout - aborting destructive operation")
        self._audit_log_destructive_op(task, confirmed=False, method='timeout')
        raise TaskStoppedException("Destructive operation aborted (confirmation timeout)")

    response = response.lower().strip()

    # Handle responses
    if response in ['y', 'yes']:
        self._audit_log_destructive_op(task, confirmed=True, method='interactive', cascade_info=cascade_info)
        print(f"{Fore.GREEN}✓ Confirmed. Proceeding...{Style.RESET_ALL}\n")
        return True

    elif response in ['n', 'no']:
        self._audit_log_destructive_op(task, confirmed=False, method='user_declined')
        print(f"{Fore.RED}✗ Operation aborted.{Style.RESET_ALL}\n")
        raise TaskStoppedException("User declined destructive operation")

    elif response in ['s', 'sim', 'simulate']:
        # Show simulation
        self._simulate_destructive_operation(task, entity_type, entity_id, operation)
        # Recurse to ask again after simulation
        return self._request_confirmation_interactive(task)

    elif response in ['c', 'cascade']:
        # Show cascade details
        self._display_cascade_details(cascade_info)
        # Recurse to ask again after showing details
        return self._request_confirmation_interactive(task)

    elif response in ['h', 'help']:
        # Show help
        self._display_confirmation_help()
        # Recurse to ask again after showing help
        return self._request_confirmation_interactive(task)

    else:
        print(f"{Fore.YELLOW}Invalid choice. Please select y/n/s/c/h.{Style.RESET_ALL}")
        return self._request_confirmation_interactive(task)
```

**Tests to Write**:
- Test: Color codes applied correctly for DELETE (red), UPDATE (yellow)
- Test: Entity details displayed when available
- Test: Cascade warning shown when applicable
- Test: Impact assessment displayed

---

### Step 2: Implement Cascade Implications Discovery

**Action**: Analyze entity relationships to determine cascade effects

**File**: `src/orchestrator.py`

**Method to Add**:
```python
def _get_cascade_implications(
    self,
    entity_type: str,
    entity_id: any,
    operation: str
) -> Dict[str, Any]:
    """Determine what entities will be affected by this operation.

    Args:
        entity_type: Type of entity (project, epic, story, task)
        entity_id: Entity identifier
        operation: Operation type (DELETE, UPDATE)

    Returns:
        Dictionary with cascade information:
        {
            'has_cascade': bool,
            'total_affected': int,
            'affected_entities': {'task': 5, 'epic': 1},
            'details': [...]
        }
    """
    cascade_info = {
        'has_cascade': False,
        'total_affected': 0,
        'affected_entities': {},
        'details': []
    }

    # Only DELETE operations have cascades
    if operation != 'DELETE':
        return cascade_info

    try:
        if entity_type == 'project':
            # Project deletion cascades to all tasks, epics, stories
            project_id = int(entity_id)
            tasks = self.state_manager.get_tasks_by_project(project_id)
            epics = [t for t in tasks if t.task_type.value == 'epic']
            stories = [t for t in tasks if t.task_type.value == 'story']
            regular_tasks = [t for t in tasks if t.task_type.value == 'task']

            cascade_info['affected_entities'] = {
                'epics': len(epics),
                'stories': len(stories),
                'tasks': len(regular_tasks)
            }
            cascade_info['total_affected'] = len(tasks)
            cascade_info['has_cascade'] = len(tasks) > 0

        elif entity_type == 'epic':
            # Epic deletion cascades to stories and tasks
            epic_id = int(entity_id)
            stories = self.state_manager.get_story_tasks(epic_id)
            tasks = []
            for story in stories:
                tasks.extend(self.state_manager.get_story_tasks(story.id))

            cascade_info['affected_entities'] = {
                'stories': len(stories),
                'tasks': len(tasks)
            }
            cascade_info['total_affected'] = len(stories) + len(tasks)
            cascade_info['has_cascade'] = cascade_info['total_affected'] > 0

        elif entity_type == 'story':
            # Story deletion cascades to tasks
            story_id = int(entity_id)
            tasks = self.state_manager.get_story_tasks(story_id)

            cascade_info['affected_entities'] = {'tasks': len(tasks)}
            cascade_info['total_affected'] = len(tasks)
            cascade_info['has_cascade'] = len(tasks) > 0

        elif entity_type == 'task':
            # Task deletion cascades to subtasks
            task_id = int(entity_id)
            subtasks = self.state_manager.get_child_tasks(task_id)

            cascade_info['affected_entities'] = {'subtasks': len(subtasks)}
            cascade_info['total_affected'] = len(subtasks)
            cascade_info['has_cascade'] = len(subtasks) > 0

    except Exception as e:
        logger.warning(f"Failed to get cascade implications: {e}")

    return cascade_info
```

**Tests to Write**:
- Test: Project deletion shows all child tasks, epics, stories
- Test: Epic deletion shows child stories and tasks
- Test: Story deletion shows child tasks
- Test: Task deletion shows child subtasks
- Test: UPDATE operations show no cascade (not applicable)

---

### Step 3: Implement Dry-Run Simulation

**Action**: Preview changes without executing

**File**: `src/orchestrator.py`

**Method to Add**:
```python
def _simulate_destructive_operation(
    self,
    task: Task,
    entity_type: str,
    entity_id: any,
    operation: str
) -> None:
    """Simulate destructive operation and show preview.

    Args:
        task: Task being simulated
        entity_type: Type of entity
        entity_id: Entity identifier
        operation: Operation type
    """
    from colorama import Fore, Style

    print(f"\n{Fore.CYAN + Style.BRIGHT}--- SIMULATION MODE (DRY RUN) ---{Style.RESET_ALL}\n")

    # Get current state
    entity = self._get_entity_details(entity_type, entity_id)
    cascade_info = self._get_cascade_implications(entity_type, entity_id, operation)

    print(f"{Fore.YELLOW}BEFORE:{Style.RESET_ALL}")
    print(f"  • Entity exists: {Fore.GREEN}Yes{Style.RESET_ALL}")
    print(f"  • ID: {entity_id}")
    print(f"  • Status: {entity.get('status', 'N/A')}")
    if cascade_info['has_cascade']:
        print(f"  • Child entities: {cascade_info['total_affected']}")

    print(f"\n{Fore.YELLOW}AFTER (if confirmed):{Style.RESET_ALL}")
    if operation == 'DELETE':
        print(f"  • Entity exists: {Fore.RED}No{Style.RESET_ALL} (deleted)")
        if cascade_info['has_cascade']:
            print(f"  • Child entities: {Fore.RED}0{Style.RESET_ALL} (cascade deleted)")
            for affected_type, count in cascade_info['affected_entities'].items():
                print(f"    - {count} {affected_type}(s) will be deleted")
    elif operation == 'UPDATE':
        print(f"  • Entity exists: {Fore.GREEN}Yes{Style.RESET_ALL} (modified)")
        print(f"  • Changes: {task.task_metadata.get('update_fields', 'N/A')}")

    print(f"\n{Fore.CYAN}Impact:{Style.RESET_ALL}")
    print(f"  • Reversible: {Fore.RED}No{Style.RESET_ALL} (no undo available)")
    print(f"  • Backup recommended: {Fore.YELLOW}Yes{Style.RESET_ALL}")
    print(f"  • Database transactions: {Fore.GREEN}Atomic{Style.RESET_ALL}")

    print(f"\n{Fore.CYAN + Style.BRIGHT}--- END SIMULATION ---{Style.RESET_ALL}\n")
```

**Tests to Write**:
- Test: Simulation shows before/after state
- Test: Simulation displays cascade effects
- Test: Simulation returns to prompt (doesn't execute)
- Test: Simulation shows undo/backup recommendations

---

### Step 4: Add Contextual Help System

**Action**: Provide guidance on options and recovery

**File**: `src/orchestrator.py`

**Method to Add**:
```python
def _display_confirmation_help(self) -> None:
    """Display help text for confirmation options."""
    from colorama import Fore, Style

    print(f"\n{Fore.CYAN + Style.BRIGHT}=== CONFIRMATION HELP ==={Style.RESET_ALL}\n")

    print(f"{Fore.GREEN}[y] Confirm and proceed{Style.RESET_ALL}")
    print("    Execute the destructive operation immediately.")
    print("    This action CANNOT be undone.")
    print("    Use this when you're certain about the operation.\n")

    print(f"{Fore.RED}[n] Abort operation{Style.RESET_ALL}")
    print("    Cancel the operation safely.")
    print("    No changes will be made to the database.")
    print("    Use this if you're unsure or want to reconsider.\n")

    print(f"{Fore.CYAN}[s] Simulate/dry-run{Style.RESET_ALL}")
    print("    Preview what will happen without executing.")
    print("    Shows before/after state and cascade effects.")
    print("    Safe to use - returns to this prompt afterward.\n")

    print(f"{Fore.CYAN}[c] Show cascade details{Style.RESET_ALL}")
    print("    Display detailed list of all affected entities.")
    print("    Shows exact tasks, epics, stories that will be changed.")
    print("    Helps understand full impact of operation.\n")

    print(f"{Fore.CYAN}[h] Help{Style.RESET_ALL}")
    print("    Display this help message.\n")

    print(f"{Fore.YELLOW}Recovery Options:{Style.RESET_ALL}")
    print("  • Backup: Create database backup before confirming")
    print("  • Alternative: Consider UPDATE instead of DELETE")
    print("  • Archive: Use soft-delete (status='archived') when possible\n")

    print(f"{Fore.CYAN + Style.BRIGHT}=== END HELP ==={Style.RESET_ALL}\n")
```

---

### Step 5: Add Dependencies

**Action**: Install colorama for cross-platform color support

**File**: `requirements.txt`

**Add**:
```
colorama>=0.4.6  # Cross-platform color terminal output
```

**Installation**:
```bash
pip install colorama
```

---

## Acceptance Criteria

✅ **Rich Confirmation Prompts**:
- [ ] Color-coded headers (red DELETE, yellow UPDATE)
- [ ] Structured entity display (name, description, dates)
- [ ] Visual hierarchy with colors and symbols
- [ ] Cross-platform color support (colorama)

✅ **Cascade Implications**:
- [ ] Cascade warning displayed when applicable
- [ ] Total affected entities count shown
- [ ] Breakdown by entity type (tasks, epics, stories)
- [ ] Accurate cascade calculation for all entity types

✅ **Dry-Run Simulation**:
- [ ] [s] option added to confirmation prompt
- [ ] Before/after state preview displayed
- [ ] Cascade effects shown in simulation
- [ ] Returns to prompt after simulation (not executed)
- [ ] Undo/backup recommendations included

✅ **Cascade Details**:
- [ ] [c] option added to show detailed cascade list
- [ ] Displays exact entities affected (with IDs)
- [ ] Grouped by entity type
- [ ] Readable format

✅ **Contextual Help**:
- [ ] [h] option added to display help
- [ ] Explains each option clearly
- [ ] Provides recovery recommendations
- [ ] Suggests alternatives (UPDATE vs DELETE)

✅ **Testing**:
- [ ] **Unit tests**: 10+ tests covering all new methods
- [ ] **Integration tests**:
  - Rich prompt displays correctly
  - Cascade calculation accurate
  - Simulation mode works
  - Help system displays
- [ ] **Code coverage**: ≥90% on new code

✅ **Documentation**:
- [ ] Updated NL_COMMAND_GUIDE.md with new options
- [ ] Screenshots/examples of rich prompts
- [ ] Recovery recommendations documented

---

## Validation Commands

**Test rich confirmation UI**:
```bash
# Start interactive mode
python -m src.cli interactive

# Try destructive NL command (creates prompt)
orchestrator> Delete epic 5

# Should see:
# - Color-coded header
# - Entity details
# - Cascade warning (if applicable)
# - Rich options (y/n/s/c/h)
```

**Test simulation**:
```bash
orchestrator> Delete project 1
# Choose [s] for simulate
# Should see before/after state, cascade effects
# Returns to prompt (not executed)
```

**Test cascade details**:
```bash
orchestrator> Delete epic 3
# Choose [c] for cascade
# Should see detailed list of affected stories/tasks
```

**Test help system**:
```bash
orchestrator> Update task 10
# Choose [h] for help
# Should see explanation of all options
```

---

## Common Pitfalls to Avoid

1. ❌ **Don't break existing confirmation workflow**: Ensure Story 8 functionality still works
2. ❌ **Don't assume colorama available**: Add to requirements.txt, graceful fallback if missing
3. ❌ **Don't execute in simulate mode**: Simulation must be read-only
4. ❌ **Don't overcomplicate cascade logic**: Handle cycles, missing entities gracefully
5. ❌ **Don't ignore color-blind users**: Use symbols (🗑️, ✏️) in addition to colors
6. ❌ **Don't make prompts too verbose**: Balance detail with readability

---

## References

**Key Files**:
- `src/orchestrator.py` - Confirmation workflow (Story 8 base)
- `src/orchestration/breakpoint_manager.py` - Destructive rule
- `src/core/state.py` - StateManager methods for cascade discovery
- `config/default_config.yaml` - Configuration
- `requirements.txt` - Add colorama dependency

**Related ADRs**:
- **ADR-017**: Unified Execution Architecture (this epic)
- **ADR-014**: Natural Language Command Interface
- **ADR-013**: Agile Work Hierarchy (cascade implications)

**Test Files**:
- `tests/test_orchestrator.py` - Unit tests for confirmation UI
- `tests/integration/test_destructive_confirmation.py` - Integration tests (from Story 8)

**Documentation**:
- `docs/guides/NL_COMMAND_GUIDE.md` - User guide (update with new options)

---

## Upon Completion of Story 9

**Status**: Story 9 of 9 COMPLETE! 🎉

After Story 9, you will have:
- ✅ Rich, color-coded confirmation prompts
- ✅ Cascade implications discovery and display
- ✅ Dry-run simulation mode
- ✅ Contextual help system
- ✅ Enhanced user experience for destructive operations
- ✅ ADR-017 fully implemented (all 9 stories complete!)

**Next Steps**:
1. User acceptance testing with real workflows
2. Performance optimization if needed
3. Gather feedback for future enhancements
4. Update CHANGELOG.md for v1.7.1 release
5. Create release notes

**ADR-017 Implementation Complete!** ✅

This completes the Unified Execution Architecture, providing:
- Consistent validation for all NL commands
- Safety checks for destructive operations
- Rich, user-friendly confirmation workflow
- Comprehensive audit logging
- Production-ready safety features

---

**Ready to start? Implement Story 9: Confirmation Workflow UI Polish (FINAL).**

Remember:
- Use colorama for cross-platform color support
- Add graceful fallbacks if colorama unavailable
- Test cascade logic thoroughly (handle cycles, missing entities)
- Balance detail with readability in prompts
- Ensure simulation is truly read-only (no side effects)
