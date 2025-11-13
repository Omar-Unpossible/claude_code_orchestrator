# ADR-017 Migration Guide: Unified Execution Architecture

**Version**: v1.7.0
**Date**: 2025-11-13
**Status**: Complete

---

## Overview

ADR-017 introduces **Unified Execution Architecture** where ALL commands (NL and CLI) route through `orchestrator.execute_task()` for consistent quality validation.

**Key Changes**:
1. `NLCommandProcessor.process()` returns `ParsedIntent` (was `NLResponse`)
2. `CommandExecutor` renamed to `NLQueryHelper` (write operations removed)
3. All NL COMMAND intents converted to Task objects before execution

**Impact**:
- **User-Facing**: **None** - Commands work identically
- **Internal APIs**: Breaking changes (this guide helps migrate)
- **Programmatic Users**: Need to update code (rare - mostly Omar)

---

## Who Needs This Guide?

### ✅ You Need This Guide If:
- You're calling `NLCommandProcessor` programmatically
- You're using `CommandExecutor` directly in code
- You're integrating Obra into another system
- You're extending Obra with custom plugins

### ❌ You DON'T Need This Guide If:
- You're only using Obra via CLI (`obra project create`, etc.)
- You're only using interactive mode (`obra interactive`)
- You're only using natural language commands (unchanged)

---

## What's Changing?

### 1. NLCommandProcessor API Change

**Before (v1.6.0)**:
```python
from src.nl.nl_command_processor import NLCommandProcessor

nl_processor = NLCommandProcessor(llm_plugin, state_manager, config)

# process() executed command immediately
response = nl_processor.process("create epic for auth")

# response was NLResponse with execution result
assert response.success
assert response.execution_result is not None
assert len(response.execution_result.created_ids) > 0
```

**After (v1.7.0)**:
```python
from src.nl.nl_command_processor import NLCommandProcessor
from src.orchestrator import Orchestrator

nl_processor = NLCommandProcessor(llm_plugin, state_manager, config)

# process() now returns ParsedIntent (no execution)
parsed_intent = nl_processor.process("create epic for auth")

# Must route through orchestrator for execution
if parsed_intent.requires_execution:
    orchestrator = Orchestrator(config)
    result = orchestrator.execute_nl_task(parsed_intent, project_id=1)
```

**Why**: NL commands now use full orchestration pipeline for quality validation.

---

### 2. CommandExecutor → NLQueryHelper

**Before (v1.6.0)**:
```python
from src.nl.command_executor import CommandExecutor

executor = CommandExecutor(state_manager, config)

# Executed CRUD operations directly
result = executor.execute(operation_context)

# Had methods for all operations
executor._execute_create(op_context)  # Created entities
executor._execute_update(op_context)  # Updated entities
executor._execute_delete(op_context)  # Deleted entities
executor._execute_query(op_context)   # Queried entities
```

**After (v1.7.0)**:
```python
from src.nl.nl_query_helper import NLQueryHelper

query_helper = NLQueryHelper(state_manager, config)

# Only provides query context (read-only)
query_context = query_helper.build_query_context(operation_context)

# Write operations removed - use orchestrator instead
# For CREATE/UPDATE/DELETE:
orchestrator.execute_nl_task(parsed_intent, project_id)
```

**Why**: Write operations now go through orchestrator for validation.

---

### 3. New Component: IntentToTaskConverter

**Usage (v1.7.0)**:
```python
from src.orchestration.intent_to_task_converter import IntentToTaskConverter

converter = IntentToTaskConverter(state_manager)

# Convert parsed intent to Task object
task = converter.convert(
    parsed_intent=operation_context,
    project_id=1
)

# Task enriched with NL context
assert task.source == 'natural_language'
assert task.nl_context['original_message'] == "create epic for auth"
assert task.nl_context['confidence'] > 0.8

# Execute through orchestrator
orchestrator.execute_task(task_id=task.id)
```

**Why**: Bridges NL parsing → orchestration pipeline.

---

## Migration Examples

### Example 1: Simple NL Command Processing

**Before (v1.6.0)**:
```python
def process_user_command(user_input: str):
    """Process user's NL command."""
    response = nl_processor.process(user_input)

    if response.success:
        print(f"✓ {response.response}")
        return response.execution_result
    else:
        print(f"✗ {response.response}")
        return None
```

**After (v1.7.0)**:
```python
def process_user_command(user_input: str, project_id: int):
    """Process user's NL command."""
    # Step 1: Parse intent
    parsed_intent = nl_processor.process(user_input)

    # Step 2: Handle based on intent type
    if parsed_intent.intent_type == 'QUESTION':
        # Informational - return response directly
        print(f"ℹ️ {parsed_intent.response}")
        return None

    elif parsed_intent.intent_type == 'COMMAND':
        # Execute through orchestrator
        if parsed_intent.requires_execution:
            result = orchestrator.execute_nl_task(
                parsed_intent,
                project_id=project_id
            )
            print(f"✓ Task {result.task_id} executed")
            return result
```

---

### Example 2: Custom Integration

**Before (v1.6.0)**:
```python
def create_epic_programmatically(title: str, description: str):
    """Create epic without NL parsing."""
    # Built operation context manually
    op_context = OperationContext(
        operation_type='CREATE',
        entity_type='epic',
        parameters={'title': title, 'description': description}
    )

    # Executed directly
    result = command_executor.execute(op_context)
    return result.created_ids[0]
```

**After (v1.7.0)**:
```python
def create_epic_programmatically(title: str, description: str, project_id: int):
    """Create epic without NL parsing."""
    # Option 1: Use StateManager directly (recommended for programmatic use)
    epic_id = state_manager.create_epic(
        project_id=project_id,
        title=title,
        description=description
    )
    return epic_id

    # Option 2: Use orchestrator with task object
    task = state_manager.create_task(
        project_id=project_id,
        task_data={
            'title': f'Create epic: {title}',
            'description': description,
            'task_type': TaskType.EPIC
        }
    )
    result = orchestrator.execute_task(task_id=task.id)
    return task.id
```

**Recommendation**: For programmatic use, call StateManager directly. Orchestrator adds overhead you may not need.

---

### Example 3: Custom NL Processing Plugin

**Before (v1.6.0)**:
```python
class CustomNLHandler:
    def handle_custom_command(self, command: str):
        # Parsed with NL processor
        response = nl_processor.process(command)

        # Custom post-processing
        if response.success:
            self.log_command(command, response.execution_result)
```

**After (v1.7.0)**:
```python
class CustomNLHandler:
    def handle_custom_command(self, command: str, project_id: int):
        # Parse with NL processor
        parsed_intent = nl_processor.process(command)

        # Route to orchestrator if needed
        if parsed_intent.requires_execution:
            result = orchestrator.execute_nl_task(parsed_intent, project_id)

            # Custom post-processing
            self.log_command(command, result)
```

---

## Deprecation Timeline

### v1.7.0 (Current)
- ✅ New unified architecture active
- ⚠️ Legacy methods available with deprecation warnings
- 📖 Migration guide published (this document)

### v1.7.1 (1 week after v1.7.0)
- ⚠️ Legacy methods still available with stronger warnings
- 📢 Announcement: Legacy removal in v1.8.0

### v1.8.0 (6 months after v1.7.0)
- ❌ Legacy methods removed
- ✅ Full migration required

---

## Deprecated APIs

### Deprecated in v1.7.0

```python
# DEPRECATED: NLCommandProcessor.process() returning NLResponse
response = nl_processor.process(command)
assert isinstance(response, NLResponse)  # NO LONGER VALID

# REPLACEMENT: Returns ParsedIntent
parsed_intent = nl_processor.process(command)
assert isinstance(parsed_intent, ParsedIntent)  # NEW API

# ===

# DEPRECATED: CommandExecutor class
from src.nl.command_executor import CommandExecutor
executor = CommandExecutor(...)
executor.execute(op_context)  # NO LONGER AVAILABLE

# REPLACEMENT: NLQueryHelper (read-only)
from src.nl.nl_query_helper import NLQueryHelper
query_helper = NLQueryHelper(...)
query_context = query_helper.build_query_context(op_context)

# For write operations: Use orchestrator
orchestrator.execute_nl_task(parsed_intent, project_id)
```

---

## Testing Your Migration

### Unit Tests

**Update test assertions**:
```python
# Before
def test_nl_command():
    response = nl_processor.process("create epic")
    assert response.success
    assert response.execution_result is not None

# After
def test_nl_command():
    parsed_intent = nl_processor.process("create epic")
    assert parsed_intent.intent_type == 'COMMAND'
    assert parsed_intent.requires_execution == True
```

### Integration Tests

**Update E2E tests**:
```python
# Before
def test_e2e_nl_command():
    response = nl_processor.process("create epic for auth")
    epic_id = response.execution_result.created_ids[0]
    epic = state_manager.get_task(epic_id)
    assert epic.task_type == TaskType.EPIC

# After
def test_e2e_nl_command():
    # Parse
    parsed_intent = nl_processor.process("create epic for auth")

    # Execute through orchestrator
    result = orchestrator.execute_nl_task(parsed_intent, project_id=1)

    # Verify
    task = state_manager.get_task(result.task_id)
    assert task.task_type == TaskType.EPIC
```

---

## Rollback Procedure

### Emergency Rollback (v1.7.0 only)

If critical issues arise, enable legacy mode:

**Option 1: Configuration File**
```yaml
# config/config.yaml
nl_commands:
  use_legacy_executor: true  # Emergency rollback
```

**Option 2: Environment Variable**
```bash
export OBRA_USE_LEGACY_EXECUTOR=true
obra interactive
```

**Option 3: Programmatic**
```python
config.set('nl_commands.use_legacy_executor', True)
orchestrator = Orchestrator(config)
```

**WARNING**: Legacy mode will be **removed in v1.8.0**. Use only for emergency.

---

## Frequently Asked Questions

### Q: Do my CLI commands still work?
**A**: Yes! All CLI commands (`obra project create`, `obra task execute`, etc.) work identically.

### Q: Do my natural language commands still work?
**A**: Yes! NL commands work the same from user perspective. Internal routing changed.

### Q: Why is there ~500ms additional latency?
**A**: NL commands now go through full orchestration pipeline (8 steps) for quality validation. Trade-off: speed < quality.

### Q: Can I skip orchestration for simple commands?
**A**: For programmatic use, call StateManager directly. For NL commands, use unified pipeline (benefits outweigh latency).

### Q: What if I'm using Obra via API?
**A**: If using programmatic API (not CLI/NL), use StateManager directly for CRUD operations. Orchestrator is for task execution with validation.

### Q: How do I know if my code needs migration?
**A**: Run your code with v1.7.0. Deprecation warnings will identify affected code.

---

## Getting Help

**Questions?**
- Check ADR-017: `docs/decisions/ADR-017-unified-execution-architecture.md`
- Check Architecture: `docs/architecture/ARCHITECTURE.md` (Unified Execution section)
- Ask: Open issue on GitHub

**Found a Bug?**
- Report: `docs/issues/` or GitHub issues
- Include: Code snippet, error message, expected behavior

---

## Summary

| Change | Before (v1.6.0) | After (v1.7.0) |
|--------|-----------------|----------------|
| **NL Processing** | `process()` executes | `process()` parses only |
| **Execution** | Direct CRUD | Via orchestrator |
| **CommandExecutor** | Write + read | Renamed to NLQueryHelper (read-only) |
| **Quality Validation** | None for NL | Full pipeline for all |
| **User Commands** | Same | Same (no changes) |

**Key Takeaway**: Internal APIs changed, user experience unchanged.

---

**Last Updated**: 2025-11-13
**ADR**: ADR-017
**Version**: v1.7.0
**Status**: Complete
