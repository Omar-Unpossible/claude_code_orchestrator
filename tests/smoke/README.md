# Smoke Tests

**Purpose**: Fast validation of core user workflows
**Speed**: <1 minute total
**Run**: Every commit, before merge

## Tests

- `test_create_project_smoke` - Create project works
- `test_create_epic_smoke` - Create epic via NL works
- `test_list_tasks_smoke` - Query tasks works
- `test_cli_project_create_smoke` - CLI commands work
- `test_help_command_smoke` - Help system works
- `test_confirmation_workflow_smoke` - Confirmation works
- `test_llm_reconnect_smoke` - LLM management works
- `test_state_manager_crud_smoke` - CRUD operations work
- `test_agile_hierarchy_smoke` - Epic/Story/Task works
- `test_error_recovery_smoke` - Error messages helpful

## Usage

```bash
# Run all smoke tests
pytest tests/smoke/ -v --timeout=60

# Run specific workflow
pytest tests/smoke/ -v -k "create_project"
```
