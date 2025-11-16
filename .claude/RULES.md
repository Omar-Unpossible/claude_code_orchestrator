# Obra Critical Rules

Quick reference for essential patterns and anti-patterns in the Obra codebase.

## Core Architecture Rules

### ✅ DO

1. **Use StateManager for ALL state access**
   ```python
   state = orchestrator.state_manager
   task = state.create_task(project_id=1, title="...")
   ```

2. **Follow validation order**
   ```
   ResponseValidator → QualityController → ConfidenceScorer → DecisionEngine
   ```

3. **Load from config (never hardcode)**
   ```python
   config = Config.load('config.yaml')
   agent = AgentRegistry.get(config.get('agent.type'))()
   ```

4. **Use fresh Claude session per iteration**
   - Eliminates session locks
   - `claude --print --dangerously-skip-permissions`

5. **Use type hints and Google-style docstrings**
   ```python
   def method(self, param: str) -> Dict[str, Any]:
       """Description.

       Args:
           param: Description

       Returns:
           Description
       """
   ```

6. **Handle exceptions with context**
   ```python
   raise AgentException(
       "Error message",
       context={'key': 'value'},
       recovery="How to fix"
   )
   ```

7. **Use correct model attributes**
   ```python
   project.project_name       # NOT project.name
   project.working_directory  # NOT project.working_dir
   task.task_id              # Primary key
   ```

8. **Check LLM availability before tasks**
   ```python
   if orchestrator.check_llm_available():
       orchestrator.execute_task(task_id=1)
   else:
       orchestrator.reconnect_llm()
   ```

9. **Save docs to proper locations**
   - Active: `docs/development/`
   - Completed: `docs/archive/` (appropriate subfolder)
   - Architecture: `docs/architecture/`
   - Decisions: `docs/decisions/`
   - Guides: `docs/guides/`
   - Testing: `docs/testing/`

10. **Update CHANGELOG.md for significant changes**
    - Add under `[Unreleased]` section
    - Use semantic versioning

### ❌ DON'T

1. **Never bypass StateManager**
   ```python
   # WRONG
   db.session.add(task)
   db.session.commit()

   # CORRECT
   state.create_task(...)
   ```

2. **Never reverse validation order**
   - Always: Response → Quality → Confidence
   - Each stage builds on previous

3. **Never hardcode implementations**
   ```python
   # WRONG
   agent = ClaudeCodeAgent()

   # CORRECT
   agent = AgentRegistry.get(config.get('agent.type'))()
   ```

4. **Never reuse sessions across iterations**
   - Causes session locks (PHASE_4 bug)
   - Always fresh session per iteration

5. **Never use `Config()` directly**
   ```python
   # WRONG
   config = Config()

   # CORRECT
   config = Config.load('config.yaml')
   ```

6. **Never skip TEST_GUIDELINES.md when writing tests**
   - WSL2 crashes are real
   - Follow resource limits

7. **Never forget thread safety**
   - Use locks for shared state
   - StateManager has built-in RLock

8. **Never assume profiles exist**
   ```python
   # CORRECT
   profiles = ProfileManager.list_profiles()
   if profile_name in profiles:
       profile = ProfileManager.load_profile(profile_name)
   ```

9. **Never save docs to project root or /tmp**
   - Always use `docs/` subfolders
   - Check `docs/archive/README.md` for existing content

10. **Never panic if LLM unavailable**
    - Obra loads gracefully
    - Reconnect when ready

## Testing Rules

### ✅ DO

1. **Read `docs/testing/TEST_GUIDELINES.md` first**
   - Critical for WSL2 stability

2. **Follow resource limits**
   - Max 0.5s sleep per test (use `fast_time` fixture)
   - Max 5 threads per test (with `timeout=` on join)
   - Max 20KB memory per test
   - Mark heavy: `@pytest.mark.slow`

3. **Use shared fixtures**
   ```python
   def test_orchestrator(test_config):
       orchestrator = Orchestrator(config=test_config)
   ```

4. **Mock time for long sleeps**
   ```python
   def test_completion(fast_time):
       time.sleep(2.0)  # Instant with fast_time
   ```

5. **Use mandatory timeouts on threads**
   ```python
   threads = [Thread(target=work) for _ in range(3)]
   for t in threads: t.start()
   for t in threads: t.join(timeout=5.0)  # MANDATORY
   ```

### ❌ DON'T

1. **Never exceed resource limits**
   - Causes WSL2 crashes (proven in M2)

2. **Never skip cleanup of background threads**
   - Always join with timeout

3. **Never assume unit tests catch everything**
   - 88% coverage missed 6 bugs in PHASE_4
   - Integration tests required

## Code Pattern Quick Reference

### StateManager Operations
```python
# Tasks
task = state.create_task(project_id=1, title="...", description="...")
task = state.get_task(task_id=1)
state.update_task(task_id=1, status=TaskStatus.COMPLETED)

# Epics (Agile)
epic = state.create_epic(project_id=1, title="...", description="...")
stories = state.get_epic_stories(epic_id=1)

# Stories
story = state.create_story(project_id=1, epic_id=1, title="...", description="...")

# Milestones
milestone = state.create_milestone(project_id=1, title="...", required_epic_ids=[1,2])
if state.check_milestone_completion(milestone):
    state.achieve_milestone(milestone)
```

### Plugin Registration
```python
@register_agent('agent-name')
class MyAgent(AgentPlugin):
    def execute(self, prompt: str, context: dict) -> str:
        pass

@register_llm('llm-name')
class MyLLM(LLMPlugin):
    def send_prompt(self, prompt: str) -> str:
        pass
```

### Configuration
```python
# Load config
config = Config.load('config/config.yaml')

# Access nested values
agent_type = config.get('agent.type')
llm_model = config.get('llm.model')

# Environment variable override
export ORCHESTRATOR_LLM_TYPE=ollama
```

### Interactive Commands
```
# Natural language (no slash) - defaults to orchestrator
"Create an epic for user authentication"

# System commands (require /)
/help                    - Show help
/status                  - Current status
/pause, /resume, /stop   - Control execution
/to-impl <msg>          - Message implementer
/override-decision      - Override choice
```

## Common Errors and Fixes

### Error: "StateManager not initialized"
**Fix**: Use `Config.load()` not `Config()`

### Error: "Agent not found in registry"
**Fix**: Check `config.agent.type` matches registered agent name

### Error: "Session lock conflict"
**Fix**: Ensure fresh session per iteration (don't reuse)

### Error: "WSL2 crash during tests"
**Fix**: Follow resource limits in TEST_GUIDELINES.md

### Error: "Profile not found"
**Fix**: Validate profile exists before loading

### Error: "LLM connection failed"
**Fix**: Use `orchestrator.reconnect_llm()` - graceful fallback supported

## Version-Specific Notes

### v1.8.0 (Production Monitoring)
- Production logging enabled by default
- Auto-redacts PII and secrets
- JSON Lines format at `~/obra-runtime/logs/production.jsonl`

### v1.7.0 (Unified Execution)
- All NL commands route through orchestrator
- Use `execute_nl_command()` for consistency

### v1.5.0 (Interactive UX)
- Natural language defaults to orchestrator (no slash)
- System commands require `/` prefix

### v1.4.0 (Project Infrastructure)
- Automatic doc maintenance
- `requires_adr`, `has_architectural_changes` task fields

### v1.3.0 (Agile/NL Interface)
- Epic/Story/Task/Subtask hierarchy
- Natural language command interface

## When to Read Full Documentation

**Read CLAUDE.md**: Core rules and architecture overview
**Read PROJECT.md**: Daily commands and workflows
**Read OBRA_SYSTEM_OVERVIEW.md**: Complete system architecture
**Read TEST_GUIDELINES.md**: Before writing ANY tests
**Read CHANGELOG.md**: Recent changes and version history
**Read ADRs**: Architecture decision rationale

## Advanced StateManager Patterns

### Atomic Operations
```python
# CORRECT: Single transaction
with state.transaction():
    task = state.create_task(project_id=1, title="...")
    state.update_task(task_id=task.task_id, status=TaskStatus.IN_PROGRESS)

# WRONG: Multiple commits (race conditions)
task = state.create_task(...)  # commit 1
state.update_task(...)  # commit 2
```

### Bulk Operations
```python
# Efficient: Batch updates
tasks = state.get_tasks(project_id=1)
updates = [{'task_id': t.task_id, 'status': TaskStatus.COMPLETED} for t in tasks]
state.bulk_update_tasks(updates)

# Inefficient: Loop commits
for task in tasks:
    state.update_task(task.task_id, status=TaskStatus.COMPLETED)
```

### Query Optimization
```python
# CORRECT: Single query with filters
active_tasks = state.get_tasks(
    project_id=1,
    status=TaskStatus.IN_PROGRESS,
    order_by='created_at DESC'
)

# WRONG: Multiple queries
all_tasks = state.get_tasks(project_id=1)
active_tasks = [t for t in all_tasks if t.status == TaskStatus.IN_PROGRESS]
```

## Common Errors Quick Fix

| Error | Cause | Fix |
|-------|-------|-----|
| `StateManager not initialized` | Used `Config()` not `Config.load()` | `config = Config.load('config.yaml')` |
| `Agent not found in registry` | Typo in config.agent.type | Check `@register_agent()` decorator name |
| `Session lock conflict` | Reused session across iterations | Fresh session per iteration |
| `WSL2 kernel panic` | Test resource limits exceeded | Follow TEST_GUIDELINES.md limits |
| `LLM connection timeout` | Network/Ollama down | `orchestrator.reconnect_llm()` |
| `Profile not found` | Profile doesn't exist | Validate: `if profile in ProfileManager.list_profiles()` |
| `AttributeError: 'NoneType'` | LLM unavailable | Check `orchestrator.check_llm_available()` first |
| `ValidationError: quality too low` | Response incomplete/malformed | Review prompt clarity, check agent logs |
| `ConfidenceScoreError: below threshold` | Uncertain response | Trigger breakpoint, get human input |

## Debug Checklist

### When Task Fails
- [ ] Check LLM connection: `orchestrator.check_llm_available()`
- [ ] Review logs: `tail -f ~/obra-runtime/logs/production.jsonl`
- [ ] Verify StateManager state: `state.get_task(task_id)`
- [ ] Check validation pipeline stages: ResponseValidator → QualityController → ConfidenceScorer
- [ ] Inspect agent output: Look for parse errors, incomplete responses
- [ ] Review prompt: Too vague? Missing context?

### When Tests Fail
- [ ] Resource limits OK? (0.5s sleep, 5 threads, 20KB)
- [ ] Fixtures loaded? (test_config, fast_time)
- [ ] Thread cleanup? (join with timeout)
- [ ] Integration vs unit? (88% unit coverage missed 6 bugs)
- [ ] Mocks realistic? (Match production behavior)
- [ ] Test isolation? (No shared state between tests)

### When LLM Connection Fails
- [ ] Ollama running? `curl http://10.0.75.1:11434/api/tags`
- [ ] Model loaded? Check Ollama logs
- [ ] Network route? `ping 10.0.75.1`
- [ ] Config correct? `config.get('llm.api_url')`
- [ ] Timeout adequate? Increase for large responses

### When Git Operations Fail
- [ ] Working directory clean? `git status`
- [ ] GitManager initialized? Check orchestrator setup
- [ ] Permissions OK? Write access to repo
- [ ] Branch exists? `git branch -a`
- [ ] Remote configured? `git remote -v`

---

**Keep this file open during development for quick reference!**
