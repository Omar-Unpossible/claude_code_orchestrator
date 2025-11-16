# Obra Simulation Issues - Remediation Plan

**Date**: 2025-11-15
**Version**: 1.0
**Based On**: OBRA_SIMULATION_RESULTS_2025-11-15.md
**Target Obra Version**: v1.8.1 (Bug Fix Release)

---

## Executive Summary

This plan addresses **3 critical issues** discovered during the Obra simulation test that prevent production adoption:

1. **Max_Turns Configuration Too Low** (P0) - Tasks fail despite delivering working code
2. **False Failure Detection** (P0) - Success metrics don't assess deliverable quality
3. **Production Logging Gaps** (P1) - CLI workflows not monitored

**Timeline**: 2-3 hours of focused development
**Complexity**: Medium (architectural changes + configuration)
**Risk**: Low (backward compatible, no breaking changes)

---

## Issue #1: Max_Turns Configuration Too Low

### Problem Statement

**Severity**: P0 - CRITICAL
**Component**: `src/agents/claude_code_local.py`, `config/config.yaml`

The default max_turns limit (10 turns, retry with 20 turns) is insufficient for complex stories. Story #9 consumed all 20 turns but delivered 7 working files with production-quality code.

**Impact**:
- Tasks marked as "failed" despite successful deliverable creation
- Complex stories cannot complete
- Undermines user trust in orchestration

### Root Cause

1. Fixed max_turns (10) doesn't account for task complexity
2. No dynamic turn limit adjustment
3. Max_turns exhaustion throws exception immediately
4. No assessment of work completed before failure

### Solution Design

**Approach**: Multi-tiered fix with backward compatibility

**1. Update Default Configuration**
```yaml
# config/config.yaml
agent:
  type: "claude-code-local"
  config:
    # OLD: max_turns: 10
    max_turns: 50  # NEW: Sufficient for complex stories
    max_turns_multiplier: 3  # OLD: 2, NEW: 3 (allows up to 150 turns)

    # NEW: Task-type specific limits
    max_turns_by_task_type:
      TASK: 30        # Simple tasks
      STORY: 50       # User stories (default)
      EPIC: 100       # Large epics (executed as batch)
      SUBTASK: 20     # Granular subtasks
```

**2. Add Task Complexity Estimation** (Optional, P2)
```python
# src/utils/task_complexity_estimator.py
class TaskComplexityEstimator:
    def estimate_turns(self, task: Task) -> int:
        """Estimate turns needed based on task metadata."""
        base_turns = 30

        # Adjust by description length
        desc_length = len(task.description or "")
        if desc_length > 500:
            base_turns += 20
        elif desc_length > 200:
            base_turns += 10

        # Adjust by task type
        if task.task_type == TaskType.EPIC:
            base_turns = 100
        elif task.task_type == TaskType.STORY:
            base_turns = 50
        elif task.task_type == TaskType.SUBTASK:
            base_turns = 20

        # Adjust by dependencies
        if task.dependencies:
            base_turns += len(task.dependencies) * 5

        return base_turns
```

**3. Add Turn Limit Extension Support**
```python
# src/agents/claude_code_local.py
class ClaudeCodeLocalAgent:
    def send_prompt(self, prompt: str, context: dict) -> str:
        max_turns = context.get('max_turns', self.config.get('max_turns', 50))

        # NEW: Allow context to override max_turns
        if 'estimated_turns' in context:
            max_turns = max(max_turns, context['estimated_turns'])

        # Execute with extended limit
        # ...existing code...
```

### Implementation Steps

**Step 1**: Update default configuration (5 min)
- File: `config/config.yaml`
- Change `max_turns: 10` to `max_turns: 50`
- Change `max_turns_multiplier: 2` to `max_turns_multiplier: 3`
- Add `max_turns_by_task_type` section

**Step 2**: Add task-type specific turn limits (10 min)
- File: `src/agents/claude_code_local.py`
- Method: `send_prompt()` - Add task_type lookup
- Logic: Check `config.agent.config.max_turns_by_task_type[task_type]`
- Fallback: Use default `max_turns` if task_type not specified

**Step 3**: Update retry logic (10 min)
- File: `src/orchestrator.py`
- Method: `_execute_single_task()`
- Change: Use new multiplier (3x instead of 2x)
- Add: Log turn limit increases

**Step 4**: Add turn budget to context (5 min)
- File: `src/orchestrator.py`
- Method: `_execute_single_task()`
- Add to `agent_context`:
  ```python
  agent_context['max_turns'] = max_turns
  agent_context['estimated_turns'] = self._estimate_turns(task)  # Optional
  ```

**Step 5**: Test configuration changes (10 min)
- Create test story requiring 30+ turns
- Verify new limits apply
- Verify task completes successfully

**Total Time**: 40 minutes

### Validation Criteria

✅ Story #9 (CLI Argument Parsing) completes successfully with new limits
✅ Complex stories complete without max_turns failures
✅ Simple tasks don't waste turns (task-type limits work)
✅ Backward compatibility maintained (existing configs still work)

### Rollback Plan

If issues arise:
1. Revert `config/config.yaml` to `max_turns: 10`
2. Remove `max_turns_by_task_type` section
3. Revert code changes in `claude_code_local.py` and `orchestrator.py`

---

## Issue #2: False Failure Detection

### Problem Statement

**Severity**: P0 - CRITICAL
**Component**: `src/orchestrator.py`, `src/orchestration/decision_engine.py`

Tasks are marked as "FAILED" when max_turns is exceeded, even when working deliverables are created. Story #9 was marked failed but delivered 7 working files with production-quality code.

**Impact**:
- Undermines trust in orchestration decisions
- Working code is discarded or ignored
- Quality validation never runs (short-circuited by max_turns exception)
- No partial success recognition

### Root Cause

1. Max_turns exception causes immediate failure
2. No deliverable assessment when max_turns hit
3. QualityController never invoked after max_turns
4. Binary success/failure model (no partial success)

### Solution Design

**Approach**: Decouple turn limits from success/failure, add deliverable assessment

**1. Add Partial Success States**
```python
# src/core/models.py
class TaskOutcome(Enum):
    SUCCESS = "success"                      # Completed within limits, quality good
    SUCCESS_WITH_LIMITS = "success_limits"   # Completed but hit turn/time limits
    PARTIAL = "partial"                      # Delivered value but incomplete
    FAILED = "failed"                        # No deliverables or critical errors
    BLOCKED = "blocked"                      # Cannot proceed (dependencies, etc)
```

**2. Add Deliverable Assessment**
```python
# src/orchestration/deliverable_assessor.py
class DeliverableAssessor:
    """Assess quality of deliverables independent of turn limits."""

    def __init__(self, file_watcher, quality_controller):
        self.file_watcher = file_watcher
        self.quality_controller = quality_controller

    def assess_deliverables(self, task: Task) -> DeliverableAssessment:
        """
        Assess deliverables created during task execution.

        Returns:
            DeliverableAssessment with outcome, files, and quality score
        """
        # Get files created during task
        new_files = self.file_watcher.get_changes_since(task.created_at)

        if not new_files:
            return DeliverableAssessment(
                outcome=TaskOutcome.FAILED,
                files=[],
                quality_score=0.0,
                reason="No deliverables created"
            )

        # Basic validation: syntax check
        valid_files = []
        for file_path in new_files:
            if self._is_valid_syntax(file_path):
                valid_files.append(file_path)

        if not valid_files:
            return DeliverableAssessment(
                outcome=TaskOutcome.PARTIAL,
                files=new_files,
                quality_score=0.3,
                reason="Files created but syntax errors found"
            )

        # Quality assessment (lightweight)
        quality_score = self._assess_file_quality(valid_files)

        # Determine outcome
        if quality_score >= 0.7:
            outcome = TaskOutcome.SUCCESS_WITH_LIMITS
        elif quality_score >= 0.5:
            outcome = TaskOutcome.PARTIAL
        else:
            outcome = TaskOutcome.FAILED

        return DeliverableAssessment(
            outcome=outcome,
            files=valid_files,
            quality_score=quality_score,
            reason=f"Created {len(valid_files)} files, quality={quality_score:.2f}"
        )

    def _is_valid_syntax(self, file_path: str) -> bool:
        """Check if file has valid syntax (Python, JSON, YAML, etc)."""
        if file_path.endswith('.py'):
            try:
                with open(file_path, 'r') as f:
                    compile(f.read(), file_path, 'exec')
                return True
            except SyntaxError:
                return False
        elif file_path.endswith('.json'):
            try:
                with open(file_path, 'r') as f:
                    json.load(f)
                return True
            except json.JSONDecodeError:
                return False
        else:
            # For other file types, just check if readable
            try:
                with open(file_path, 'r') as f:
                    f.read()
                return True
            except Exception:
                return False

    def _assess_file_quality(self, files: list) -> float:
        """Lightweight quality assessment of created files."""
        scores = []

        for file_path in files:
            score = 0.5  # Base score for valid syntax

            # Check file size (too small = stub, too large = may be test output)
            file_size = os.path.getsize(file_path)
            if 100 < file_size < 50000:
                score += 0.2

            # Check for documentation (Python files)
            if file_path.endswith('.py'):
                with open(file_path, 'r') as f:
                    content = f.read()
                    if '"""' in content or "'''" in content:
                        score += 0.1  # Has docstrings
                    if 'def ' in content or 'class ' in content:
                        score += 0.1  # Has functions/classes
                    if ': ' in content and '->' in content:
                        score += 0.1  # Has type hints

            scores.append(min(score, 1.0))

        return sum(scores) / len(scores) if scores else 0.0
```

**3. Update Orchestrator to Use Deliverable Assessment**
```python
# src/orchestrator.py
class Orchestrator:
    def _execute_single_task(self, task, max_iterations=5):
        """Execute with deliverable assessment on max_turns."""
        try:
            # Existing execution logic
            response = self.agent.send_prompt(prompt, context=agent_context)
            # ... quality validation ...
            return response

        except AgentException as e:
            if "max_turns" in str(e).lower():
                # NEW: Assess deliverables instead of immediate failure
                logger.warning(f"Max turns reached for task {task.id}, assessing deliverables...")

                deliverable_assessment = self.deliverable_assessor.assess_deliverables(task)

                if deliverable_assessment.outcome in [TaskOutcome.SUCCESS_WITH_LIMITS, TaskOutcome.PARTIAL]:
                    # Has deliverables - treat as partial success
                    logger.info(f"Task {task.id} delivered value despite max_turns: {deliverable_assessment.reason}")

                    # Update task status
                    self.state.update_task(
                        task.id,
                        status=TaskStatus.COMPLETED,
                        outcome=deliverable_assessment.outcome,
                        quality_score=deliverable_assessment.quality_score
                    )

                    # Return success with warning
                    return {
                        'outcome': deliverable_assessment.outcome,
                        'files': deliverable_assessment.files,
                        'quality_score': deliverable_assessment.quality_score,
                        'warning': 'Task completed but exceeded turn limit'
                    }
                else:
                    # No deliverables - legitimate failure
                    logger.error(f"Task {task.id} exceeded max_turns with no deliverables")
                    raise
            else:
                raise
```

**4. Update CLI Output**
```python
# src/cli.py
@click.command()
def task_execute(task_id):
    """Execute a task with improved status reporting."""
    result = orchestrator.execute_task(task_id)

    if result['outcome'] == TaskOutcome.SUCCESS:
        click.echo(click.style("✓ Task completed successfully", fg='green'))

    elif result['outcome'] == TaskOutcome.SUCCESS_WITH_LIMITS:
        click.echo(click.style("⚠ Task completed with warnings", fg='yellow'))
        click.echo(f"  Reason: {result.get('warning', 'Exceeded limits')}")
        click.echo(f"  Deliverables: {len(result.get('files', []))} files created")
        click.echo(f"  Quality: {result.get('quality_score', 0):.2f}")

    elif result['outcome'] == TaskOutcome.PARTIAL:
        click.echo(click.style("⚠ Task partially completed", fg='yellow'))
        click.echo(f"  Files created: {len(result.get('files', []))}")
        click.echo(f"  Quality: {result.get('quality_score', 0):.2f}")
        click.echo("  Review recommended before proceeding")

    else:
        click.echo(click.style("✗ Task failed", fg='red'))
```

### Implementation Steps

**Step 1**: Add TaskOutcome enum (5 min)
- File: `src/core/models.py`
- Add new enum with 5 states
- Update imports in dependent modules

**Step 2**: Create DeliverableAssessor class (30 min)
- File: `src/orchestration/deliverable_assessor.py` (new)
- Implement `assess_deliverables()` method
- Implement syntax validation helpers
- Implement lightweight quality scoring
- Add comprehensive docstrings

**Step 3**: Integrate DeliverableAssessor into Orchestrator (20 min)
- File: `src/orchestrator.py`
- Initialize `DeliverableAssessor` in `__init__()`
- Update `_execute_single_task()` exception handling
- Call `assess_deliverables()` on max_turns exception
- Update task status based on assessment

**Step 4**: Update CLI output formatting (15 min)
- File: `src/cli.py`
- Update `task_execute()` command
- Add color-coded output for each outcome state
- Display deliverable summary

**Step 5**: Add tests for DeliverableAssessor (20 min)
- File: `tests/test_deliverable_assessor.py` (new)
- Test successful deliverable detection
- Test syntax validation
- Test quality scoring
- Test different outcome states

**Step 6**: Update StateManager for new outcomes (10 min)
- File: `src/core/state.py`
- Update `update_task()` to accept new outcome values
- Add database migration if needed (outcome column type)

**Total Time**: 100 minutes (1h 40min)

### Validation Criteria

✅ Story #9 marked as SUCCESS_WITH_LIMITS instead of FAILED
✅ 7 created files detected and assessed
✅ Quality score ≥ 0.7 (estimated 0.85 for actual deliverables)
✅ CLI shows deliverable summary, not just "failed"
✅ Task status correctly reflects partial success
✅ Backward compatibility maintained

### Rollback Plan

If issues arise:
1. Revert `orchestrator.py` exception handling to original
2. Remove `deliverable_assessor.py`
3. Revert `models.py` enum changes
4. Remove tests

---

## Issue #3: Production Logging Gaps

### Problem Statement

**Severity**: P1 - HIGH
**Component**: `src/cli.py`, `src/monitoring/production_logger.py`

Production logs (`~/obra-runtime/logs/production.jsonl`) captured **zero events** during CLI-based workflows:
- `obra project create`
- `obra epic create`
- `obra story create`
- `obra task execute`

Only NL commands through interactive mode trigger production logging.

**Impact**:
- Cannot monitor orchestration in production
- No quality metrics captured
- No debugging data for failures
- Incomplete observability

### Root Cause

`ProductionLogger` is only initialized in:
- `src/interactive.py` (for NL command flow)
- `src/nl/nl_command_processor.py` (for NL execution)

But **not** in:
- `src/cli.py` (CLI commands)
- `src/orchestrator.py` direct task execution

### Solution Design

**Approach**: Add production logging to all entry points

**1. Make ProductionLogger Globally Available**
```python
# src/monitoring/production_logger.py
_production_logger_instance = None

def get_production_logger() -> Optional[ProductionLogger]:
    """Get global production logger instance."""
    global _production_logger_instance
    return _production_logger_instance

def initialize_production_logger(config: Config) -> ProductionLogger:
    """Initialize global production logger."""
    global _production_logger_instance

    if config.get('monitoring.production_logging.enabled', True):
        _production_logger_instance = ProductionLogger(config)
        logger.info("Production logger initialized globally")
    else:
        logger.info("Production logging disabled in config")
        _production_logger_instance = None

    return _production_logger_instance
```

**2. Add Logging to CLI Commands**
```python
# src/cli.py
@click.group()
@click.pass_context
def cli(ctx):
    """Obra command-line interface."""
    # Load config
    config = Config.load()

    # Initialize production logger
    prod_logger = initialize_production_logger(config)

    # Store in context for subcommands
    ctx.obj = {
        'config': config,
        'production_logger': prod_logger
    }

@cli.command()
@click.argument('task_id', type=int)
@click.pass_context
def task_execute(ctx, task_id):
    """Execute a task with production logging."""
    prod_logger = ctx.obj.get('production_logger')

    # Log execution start
    if prod_logger:
        prod_logger.log_execution_start(task_id)

    try:
        # Execute task
        orchestrator = Orchestrator(config=ctx.obj['config'])
        result = orchestrator.execute_task(task_id)

        # Log execution result
        if prod_logger:
            prod_logger.log_execution_result(
                task_id=task_id,
                outcome=result.get('outcome', 'success'),
                quality_score=result.get('quality_score'),
                duration_ms=result.get('duration_ms'),
                entities_affected=[f"task:{task_id}"]
            )

        click.echo(f"✓ Task {task_id} completed")

    except Exception as e:
        # Log error
        if prod_logger:
            prod_logger.log_error(
                stage="execution",
                error_type=type(e).__name__,
                error_message=str(e),
                context={'task_id': task_id}
            )
        raise
```

**3. Add Logging to Orchestrator Direct Execution**
```python
# src/orchestrator.py
class Orchestrator:
    def __init__(self, config: Config):
        # ... existing init ...

        # Get production logger (global instance)
        self.production_logger = get_production_logger()
        if self.production_logger:
            logger.info("Orchestrator using production logger")

    def execute_task(self, task_id, **kwargs):
        """Execute task with production logging."""
        # Log task start
        if self.production_logger:
            self.production_logger.log_execution_start(task_id)

        start_time = time.time()

        try:
            # Execute task
            result = self._execute_single_task(task, max_iterations)

            # Log success
            duration_ms = int((time.time() - start_time) * 1000)
            if self.production_logger:
                self.production_logger.log_execution_result(
                    task_id=task_id,
                    outcome=result.get('outcome', 'success'),
                    quality_score=result.get('quality_score'),
                    confidence=result.get('confidence'),
                    duration_ms=duration_ms,
                    entities_affected=[f"task:{task_id}"]
                )

            return result

        except Exception as e:
            # Log error
            duration_ms = int((time.time() - start_time) * 1000)
            if self.production_logger:
                self.production_logger.log_error(
                    stage="execution",
                    error_type=type(e).__name__,
                    error_message=str(e),
                    context={'task_id': task_id, 'duration_ms': duration_ms}
                )
            raise
```

**4. Add CLI Entity Creation Logging**
```python
# src/cli.py
@cli.command()
@click.argument('title')
@click.option('--project', '-p', type=int, required=True)
@click.pass_context
def epic_create(ctx, title, project, **kwargs):
    """Create an epic with production logging."""
    prod_logger = ctx.obj.get('production_logger')

    # Log user input
    if prod_logger:
        prod_logger.log_user_input(
            user_text=f"epic create {title}",
            session_id=None,  # CLI has no session
            context={'project': project}
        )

    # Create epic
    state = StateManager(ctx.obj['config'])
    epic_id = state.create_epic(
        project_id=project,
        title=title,
        description=kwargs.get('description')
    )

    # Log execution result
    if prod_logger:
        prod_logger.log_execution_result(
            outcome="success",
            entities_affected=[f"epic:{epic_id}"],
            context={'project': project}
        )

    click.echo(f"✓ Created epic #{epic_id}: {title}")
```

### Implementation Steps

**Step 1**: Add global ProductionLogger pattern (15 min)
- File: `src/monitoring/production_logger.py`
- Add `get_production_logger()` function
- Add `initialize_production_logger()` function
- Update module-level singleton

**Step 2**: Update CLI main group (10 min)
- File: `src/cli.py`
- Update `cli()` group to initialize logger
- Pass logger in click context

**Step 3**: Add logging to task_execute command (15 min)
- File: `src/cli.py`
- Update `task_execute()` command
- Log execution start, result, errors
- Handle exceptions properly

**Step 4**: Add logging to entity creation commands (20 min)
- File: `src/cli.py`
- Update `project_create()`, `epic_create()`, `story_create()`
- Log user input and execution results
- Maintain backward compatibility

**Step 5**: Integrate ProductionLogger into Orchestrator (15 min)
- File: `src/orchestrator.py`
- Get global logger in `__init__()`
- Log task execution events
- Log errors and quality metrics

**Step 6**: Test logging coverage (15 min)
- Run CLI commands
- Verify events appear in production.jsonl
- Verify event schema matches NL command events
- Check for edge cases

**Total Time**: 90 minutes (1h 30min)

### Validation Criteria

✅ `obra project create` logs user_input and execution_result events
✅ `obra epic create` logs user_input and execution_result events
✅ `obra task execute` logs execution_start, execution_result, and quality metrics
✅ Production log events match NL command format
✅ Errors are logged with proper context
✅ Backward compatibility maintained (NL commands still log)

### Rollback Plan

If issues arise:
1. Revert `production_logger.py` global pattern changes
2. Remove logging calls from `cli.py`
3. Revert `orchestrator.py` logger integration
4. Production logging will fall back to NL-only mode

---

## Implementation Priority

### Phase 1: Critical Fixes (P0)
**Timeline**: 2 hours
**Order**:
1. **Issue #1: Max_Turns Configuration** (40 min)
2. **Issue #2: Deliverable Assessment** (1h 40min)

### Phase 2: High Priority (P1)
**Timeline**: 1.5 hours
**Order**:
1. **Issue #3: Production Logging** (1h 30min)

### Total Implementation Time
**Estimated**: 3.5 hours focused development
**Recommended**: 4-5 hours with testing and documentation

---

## Testing Strategy

### Unit Tests
- `test_deliverable_assessor.py` - Deliverable assessment logic
- `test_production_logger_global.py` - Global logger pattern
- `test_max_turns_config.py` - Max turns configuration loading

### Integration Tests
- Rerun Story #9 with new max_turns configuration
- Verify deliverable assessment on max_turns
- Verify production logs captured for CLI workflows

### Regression Tests
- Ensure existing NL command logging still works
- Ensure backward compatibility with old configs
- Ensure no performance degradation

### Validation Test
- **Full Simulation Retest**: Run OBRA_SIMULATION_TEST.md again with fixes applied
- **Expected**: All P0 criteria met, no false failures, production logs populated

---

## Documentation Updates

### Files to Update

1. **CHANGELOG.md**
   - Add v1.8.1 section
   - Document all 3 bug fixes
   - Note backward compatibility

2. **config/config.yaml**
   - Update max_turns default and comments
   - Add max_turns_by_task_type section with examples

3. **docs/guides/CONFIGURATION_PROFILES_GUIDE.md**
   - Document new max_turns settings
   - Document task-type specific limits

4. **docs/guides/PRODUCTION_MONITORING_GUIDE.md**
   - Update to reflect CLI logging support
   - Add examples of CLI event logs

5. **docs/testing/TEST_GUIDELINES.md**
   - Document new partial success states
   - Update expected outcomes for tests

---

## Risk Assessment

### Low Risk Changes
- ✅ Config file updates (easily reverted)
- ✅ Adding new classes (no existing code broken)
- ✅ CLI output improvements (cosmetic)

### Medium Risk Changes
- ⚠️ Exception handling in Orchestrator (affects execution flow)
- ⚠️ Global ProductionLogger pattern (affects all entry points)

### Mitigation Strategies
- ✅ Comprehensive unit tests for new components
- ✅ Integration tests for changed workflows
- ✅ Backward compatibility checks
- ✅ Clear rollback procedures documented

### Rollback Triggers
- Critical bug discovered in deliverable assessment
- Production logging causes performance issues
- Backward compatibility broken
- Tests fail after implementation

---

## Success Metrics

### Code Quality
- ✅ All new code has type hints
- ✅ All new code has docstrings
- ✅ All new code has unit tests (≥90% coverage)
- ✅ No pylint/mypy errors

### Functional Success
- ✅ Story #9 completes with SUCCESS_WITH_LIMITS (not FAILED)
- ✅ Production logs show task execution events
- ✅ Deliverable assessment detects 7 files created
- ✅ Quality score ≥ 0.7 for Story #9 deliverables

### Performance
- ✅ No significant latency increase (< 5% overhead)
- ✅ Production logging overhead < 50ms per event
- ✅ Deliverable assessment < 1s for typical tasks

### User Experience
- ✅ CLI output clearly shows partial success vs failure
- ✅ Production logs provide actionable debugging data
- ✅ Error messages are clear and actionable

---

## Post-Implementation

### Validation
1. Run full simulation test again
2. Compare results to original simulation
3. Verify all critical issues resolved
4. Generate updated simulation report

### Documentation
1. Update CHANGELOG.md with v1.8.1 release notes
2. Update affected guides and references
3. Archive this remediation plan to `docs/archive/`

### Communication
1. Document lessons learned
2. Update system overview with new capabilities
3. Consider blog post on debugging AI orchestration

---

## Appendix: Code Snippets

### A1: Updated config/config.yaml
```yaml
agent:
  type: "claude-code-local"
  config:
    workspace_dir: "workspace"
    headless: true
    dangerous_mode: true
    max_turns: 50  # Increased from 10 for complex stories
    max_turns_multiplier: 3  # Increased from 2 (allows up to 150 turns)

    # Task-type specific turn limits
    max_turns_by_task_type:
      TASK: 30        # Simple technical tasks
      STORY: 50       # User stories (default)
      EPIC: 100       # Large epics
      SUBTASK: 20     # Granular subtasks
```

### A2: TaskOutcome Enum
```python
# src/core/models.py
class TaskOutcome(str, Enum):
    """Task execution outcomes."""
    SUCCESS = "success"                      # Completed successfully
    SUCCESS_WITH_LIMITS = "success_limits"   # Completed but hit limits
    PARTIAL = "partial"                      # Partial completion
    FAILED = "failed"                        # Failed to deliver
    BLOCKED = "blocked"                      # Cannot proceed
```

### A3: DeliverableAssessment Dataclass
```python
# src/orchestration/deliverable_assessor.py
from dataclasses import dataclass
from typing import List

@dataclass
class DeliverableAssessment:
    """Assessment of deliverables created during task execution."""
    outcome: TaskOutcome
    files: List[str]
    quality_score: float
    reason: str
    syntax_valid: bool = True
    estimated_completeness: float = 1.0
```

---

**Plan Version**: 1.0
**Last Updated**: 2025-11-15
**Status**: Ready for Implementation
