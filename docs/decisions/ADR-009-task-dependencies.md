# ADR-009: Task Dependency System with DAG Resolution

**Status:** Accepted

**Date:** 2025-11-04

**Deciders:** Obra Development Team

**Context Owner:** Omar (@Omar-Unpossible)

---

## Context

Obra's current task execution (M0-M8) treats all tasks as independent units with no relationships:

1. **No dependency tracking** - Tasks cannot depend on other tasks
2. **Sequential execution only** - No way to express "Task B needs Task A first"
3. **Manual ordering required** - Users must sequence tasks manually
4. **No parallel execution support** - Independent tasks run serially (inefficient)
5. **No failure propagation** - If Task A fails, dependent Task B still runs

These limitations prevent:
- Complex multi-phase workflows (design → implement → test → deploy)
- Parallel execution of independent tasks (efficiency gains)
- Automatic task ordering based on dependencies
- Proper failure handling (cascading failures)
- Visual workflow representations

**Real-World Impact:**
- User creates "Test feature" task before "Implement feature" task
- Test runs first, fails because feature doesn't exist
- Multi-file refactoring can't express file dependencies
- Code generation can't express "tests depend on implementation"

**Requirements:**
- ✓ Define dependencies: "Task B depends on Task A, C"
- ✓ Automatic dependency resolution and execution order
- ✓ Cycle detection prevents circular dependencies
- ✓ Cascading failure handling (block dependents on failure)
- ✓ Visual dependency graph generation
- ✓ Support for parallel execution of independent tasks
- ✓ Database persistence of dependency relationships

---

## Decision

We will implement a **Task Dependency System** using a Directed Acyclic Graph (DAG) with topological sort for execution order.

### Core Components

#### 1. Data Model

**Database Schema:**
```sql
-- Add to Task table
ALTER TABLE tasks ADD COLUMN depends_on JSON DEFAULT '[]';

-- Example: Task 4 depends on Tasks 2 and 3
UPDATE tasks SET depends_on = '[2, 3]' WHERE id = 4;

-- Indexes for performance
CREATE INDEX idx_tasks_depends_on ON tasks USING GIN (depends_on);
```

**Task Model Updates:**
```python
class Task:
    # ... existing fields ...
    
    # Dependency fields
    depends_on: List[int] = []  # List of task IDs this task depends on
    dependents: List[int] = []  # Computed: tasks that depend on this (reverse)
    is_blocked: bool = False    # Blocked by incomplete/failed dependencies
    
    # Metadata
    dependency_depth: int = 0   # Longest path to root (0 = no dependencies)
    ready_at: Optional[datetime] = None  # When all dependencies completed
```

#### 2. DependencyResolver Class

**Purpose:** Analyze dependency graph, compute execution order, detect cycles.

```python
class DependencyResolver:
    """Resolves task dependencies using DAG analysis."""

    def __init__(self, state_manager: StateManager, config: dict):
        self.state = state_manager
        self.max_depth = config.get('task_dependencies', {}).get('max_depth', 10)
        self.allow_cycles = config.get('task_dependencies', {}).get('allow_cycles', False)
        self.cascade_failures = config.get('task_dependencies', {}).get('cascade_failures', True)

    def build_dependency_graph(self, tasks: List[Task]) -> nx.DiGraph:
        """Build directed graph of task dependencies.
        
        Args:
            tasks: List of tasks to analyze
            
        Returns:
            NetworkX directed graph with tasks as nodes, dependencies as edges
            
        Raises:
            DependencyError: If cycles detected and allow_cycles=False
        """
        graph = nx.DiGraph()
        
        # Add all tasks as nodes
        for task in tasks:
            graph.add_node(task.id, task=task)
        
        # Add dependency edges
        for task in tasks:
            for dep_id in task.depends_on:
                if dep_id not in graph:
                    raise DependencyError(
                        f"Task {task.id} depends on non-existent task {dep_id}"
                    )
                graph.add_edge(dep_id, task.id)  # dep_id -> task.id
        
        # Check for cycles
        if not self.allow_cycles:
            cycles = list(nx.simple_cycles(graph))
            if cycles:
                raise DependencyError(
                    f"Circular dependencies detected: {cycles}"
                )
        
        # Check max depth
        for task in tasks:
            depth = self._calculate_depth(graph, task.id)
            if depth > self.max_depth:
                raise DependencyError(
                    f"Task {task.id} exceeds max dependency depth "
                    f"({depth} > {self.max_depth})"
                )
        
        return graph

    def topological_sort(self, tasks: List[Task]) -> List[Task]:
        """Return tasks in optimal execution order.
        
        Args:
            tasks: List of tasks to sort
            
        Returns:
            Tasks sorted by dependency order (dependencies first)
            
        Raises:
            DependencyError: If graph has cycles
        """
        graph = self.build_dependency_graph(tasks)
        
        try:
            sorted_ids = list(nx.topological_sort(graph))
        except nx.NetworkXError as e:
            raise DependencyError(f"Cannot sort tasks: {e}")
        
        # Return tasks in sorted order
        task_map = {t.id: t for t in tasks}
        return [task_map[tid] for tid in sorted_ids]

    def get_ready_tasks(self, tasks: List[Task]) -> List[Task]:
        """Get tasks with all dependencies complete.
        
        Args:
            tasks: List of tasks to check
            
        Returns:
            Tasks that are ready to execute (all deps completed)
        """
        ready = []
        
        for task in tasks:
            # Skip if already completed/failed
            if task.status in ['completed', 'failed', 'cancelled']:
                continue
            
            # Check if all dependencies are complete
            all_deps_complete = True
            for dep_id in task.depends_on:
                dep_task = self.state.get_task(dep_id)
                if not dep_task or dep_task.status != 'completed':
                    all_deps_complete = False
                    break
            
            if all_deps_complete:
                ready.append(task)
        
        return ready

    def handle_cascading_failure(self, failed_task: Task) -> List[Task]:
        """Mark dependent tasks as blocked.
        
        Args:
            failed_task: Task that failed
            
        Returns:
            List of tasks that were blocked
        """
        if not self.cascade_failures:
            return []
        
        blocked = []
        all_tasks = self.state.get_project_tasks(failed_task.project_id)
        graph = self.build_dependency_graph(all_tasks)
        
        # Find all descendants (tasks that transitively depend on failed_task)
        descendants = nx.descendants(graph, failed_task.id)
        
        for task_id in descendants:
            task = self.state.get_task(task_id)
            if task and task.status not in ['completed', 'failed', 'cancelled']:
                self.state.update_task(
                    task_id,
                    is_blocked=True,
                    status='blocked',
                    metadata={'blocked_by': failed_task.id}
                )
                blocked.append(task)
        
        return blocked

    def get_dependency_graph_visualization(self, tasks: List[Task]) -> str:
        """Generate visual representation of dependency graph.
        
        Args:
            tasks: List of tasks to visualize
            
        Returns:
            ASCII art representation of dependency graph
        """
        graph = self.build_dependency_graph(tasks)
        
        # Use graphviz for rendering (if available)
        try:
            import pygraphviz
            agraph = nx.nx_agraph.to_agraph(graph)
            return agraph.to_string()
        except ImportError:
            # Fallback: simple text representation
            lines = []
            for task in self.topological_sort(tasks):
                deps = ", ".join(str(d) for d in task.depends_on)
                lines.append(f"Task {task.id}: [{task.title}] depends on [{deps}]")
            return "\n".join(lines)
```

#### 3. StateManager Integration

**New Methods:**
```python
class StateManager:
    # ... existing methods ...
    
    def add_task_dependency(self, task_id: int, depends_on_id: int) -> None:
        """Add dependency relationship."""
        task = self.get_task(task_id)
        if depends_on_id not in task.depends_on:
            task.depends_on.append(depends_on_id)
            self.update_task(task_id, depends_on=task.depends_on)
    
    def get_task_dependencies(self, task_id: int) -> List[Task]:
        """Get all tasks this task depends on."""
        task = self.get_task(task_id)
        return [self.get_task(dep_id) for dep_id in task.depends_on]
    
    def get_dependent_tasks(self, task_id: int) -> List[Task]:
        """Get all tasks that depend on this task."""
        all_tasks = self.get_project_tasks(task.project_id)
        return [t for t in all_tasks if task_id in t.depends_on]
    
    def get_ready_tasks(self, project_id: int) -> List[Task]:
        """Get tasks ready to execute (dependencies complete)."""
        all_tasks = self.get_project_tasks(project_id)
        resolver = DependencyResolver(self, self.config)
        return resolver.get_ready_tasks(all_tasks)
```

#### 4. Orchestrator Integration

**Execution Loop:**
```python
class Orchestrator:
    def execute_milestone(self, milestone_id: int) -> Dict:
        """Execute all tasks in milestone respecting dependencies."""
        tasks = self.state.get_milestone_tasks(milestone_id)
        
        # Resolve dependencies and get execution order
        resolver = DependencyResolver(self.state, self.config)
        sorted_tasks = resolver.topological_sort(tasks)
        
        results = []
        for task in sorted_tasks:
            # Check if task is ready (all deps complete)
            if task.id not in [t.id for t in resolver.get_ready_tasks(tasks)]:
                logger.info(f"Task {task.id} blocked by dependencies, skipping")
                continue
            
            # Execute task
            try:
                result = self._execute_single_task(task.id)
                results.append(result)
            except Exception as e:
                # Handle cascading failure
                blocked_tasks = resolver.handle_cascading_failure(task)
                logger.error(
                    f"Task {task.id} failed, blocking {len(blocked_tasks)} dependents"
                )
                raise
        
        return {'results': results, 'total': len(sorted_tasks)}
```

#### 5. CLI Integration

**New Commands:**
```bash
# Create task with dependencies
obra task create "Implement tests" --depends-on 1,3 --project 1

# View task dependencies
obra task dependencies 4

# Visualize dependency graph
obra project graph 1

# Check which tasks are ready
obra project ready 1
```

**CLI Implementation:**
```python
@click.command('create')
@click.argument('title')
@click.option('--depends-on', default=None, help='Comma-separated task IDs')
@click.option('--project', type=int, required=True)
def task_create(title, depends_on, project):
    """Create a new task with optional dependencies."""
    depends_on_list = []
    if depends_on:
        depends_on_list = [int(x.strip()) for x in depends_on.split(',')]
    
    task_id = state.create_task(
        project_id=project,
        title=title,
        depends_on=depends_on_list
    )
    
    click.echo(f"Created task {task_id}: {title}")
    if depends_on_list:
        click.echo(f"  Depends on: {depends_on_list}")
```

#### 6. Configuration

```yaml
task_dependencies:
  enabled: true
  max_depth: 10  # Maximum dependency chain depth
  allow_cycles: false  # Strict mode: reject circular dependencies
  cascade_failures: true  # Block dependents when task fails
  
  # Visualization settings
  visualization:
    format: 'ascii'  # 'ascii', 'graphviz', 'json'
    show_completed: false  # Hide completed tasks from graph
```

---

## Alternatives Considered

### Alternative 1: Simple Ordering (No Graph)

**Option:** Use simple `depends_on` field without graph analysis.

```python
# Just check immediate dependencies
for task in tasks:
    for dep_id in task.depends_on:
        dep = state.get_task(dep_id)
        if dep.status != 'completed':
            task.is_blocked = True
```

**Rejected because:**
- ❌ No cycle detection (can create infinite loops)
- ❌ No transitive dependency checking (A→B→C not handled)
- ❌ No optimal execution order (inefficient sequencing)
- ❌ No cascading failure support

**Outcome:** Full DAG provides robustness and optimization.

---

### Alternative 2: Parallel Execution by Default

**Option:** Execute all ready tasks in parallel threads/processes.

```python
# Execute all ready tasks simultaneously
ready_tasks = resolver.get_ready_tasks(tasks)
with ThreadPoolExecutor() as executor:
    futures = [executor.submit(execute_task, t) for t in ready_tasks]
    results = [f.result() for f in futures]
```

**Rejected because:**
- ❌ Conflicts with headless mode (single Claude session)
- ❌ Requires multiple Claude Code instances (licensing issues)
- ❌ Complex state synchronization
- ❌ File conflicts between parallel tasks

**Outcome:** Sequential execution with dependency order (parallel in future if needed).

---

### Alternative 3: Dependency Groups Instead of DAG

**Option:** Group tasks into stages rather than individual dependencies.

```yaml
milestone:
  stage_1: [task_1, task_2]  # All execute in parallel
  stage_2: [task_3, task_4]  # After stage_1 completes
  stage_3: [task_5]          # After stage_2 completes
```

**Rejected because:**
- ❌ Less flexible than DAG (can't express Task 3 depends only on Task 1)
- ❌ Requires stage management (additional complexity)
- ❌ No automatic stage calculation
- ❌ User must manually assign stages

**Outcome:** DAG is more expressive and automatic.

---

### Alternative 4: Allow Cycles with Retry

**Option:** Allow circular dependencies but detect and break them at runtime.

```python
# Detect cycle, execute one task to break it
if cycle_detected:
    break_task = choose_task_to_break(cycle)
    execute_task(break_task)  # This unblocks the cycle
```

**Rejected because:**
- ❌ Circular dependencies usually indicate design error
- ❌ Breaking cycles is non-deterministic (which task to break?)
- ❌ Adds unnecessary complexity
- ❌ Better to reject cycles and force user to fix design

**Outcome:** Strict mode (allow_cycles=false) by default.

---

## Consequences

### Positive Consequences

1. **Express Complex Workflows**
   - ✅ Multi-phase workflows: design → implement → test → deploy
   - ✅ Explicit dependencies: "tests depend on implementation"
   - ✅ Automatic ordering: no manual sequencing needed
   - ✅ Clear workflow visualization

2. **Robust Execution**
   - ✅ Cycle detection prevents infinite loops
   - ✅ Depth limiting prevents excessive complexity
   - ✅ Cascading failures prevent wasted work
   - ✅ Ready task detection ensures prerequisites met

3. **Optimization Opportunities**
   - ✅ Topological sort finds optimal order
   - ✅ Ready task detection enables future parallelization
   - ✅ Dependency graph identifies bottlenecks
   - ✅ Depth calculation helps with planning

4. **Better Error Handling**
   - ✅ Failed task blocks dependents automatically
   - ✅ Clear error messages for dependency issues
   - ✅ Transitive dependency checking
   - ✅ Validation at task creation time

5. **Visual Understanding**
   - ✅ Dependency graph visualization
   - ✅ ASCII art for simple cases
   - ✅ Graphviz for complex graphs
   - ✅ Helps with debugging and planning

### Negative Consequences

1. **Increased Complexity**
   - ⚠️ DAG analysis adds computational overhead
   - ⚠️ NetworkX dependency added
   - ⚠️ More complex task creation (dependencies)
   - ✅ **Mitigation:** Caching, lazy evaluation, sensible defaults

2. **Learning Curve**
   - ⚠️ Users must understand dependencies
   - ⚠️ Cycle errors may be confusing
   - ⚠️ Requires planning ahead
   - ✅ **Mitigation:** Clear documentation, examples, helpful errors

3. **Sequential Execution Limitation**
   - ⚠️ Independent tasks still run sequentially
   - ⚠️ No performance gain from parallelization
   - ⚠️ Future work required for parallel execution
   - ✅ **Mitigation:** Foundation in place, parallel in v2.0

4. **Database Changes**
   - ⚠️ Schema migration required
   - ⚠️ Existing tasks need depends_on=[] default
   - ⚠️ Index creation may be slow on large databases
   - ✅ **Mitigation:** Alembic migration handles it

5. **Cascading Failures Can Be Aggressive**
   - ⚠️ One failure blocks many tasks
   - ⚠️ May want some dependents to still run
   - ⚠️ All-or-nothing approach
   - ✅ **Mitigation:** cascade_failures config option

### Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Cycle creation by user | Medium | High | Strict validation, clear errors |
| Performance with large graphs | Low | Medium | Caching, lazy evaluation, max_depth |
| Database migration issues | Low | High | Alembic migration, rollback support |
| User confusion | Medium | Low | Documentation, examples, helpful CLI |
| Over-blocking from failures | Medium | Medium | cascade_failures=false option |

---

## Implementation Details

### Phase 5: Task Dependencies (Days 6-10 of M9)

**Database Migration:**
```python
# alembic/versions/xxx_add_task_dependencies.py
def upgrade():
    op.add_column('tasks', sa.Column('depends_on', sa.JSON(), nullable=True))
    op.execute("UPDATE tasks SET depends_on = '[]' WHERE depends_on IS NULL")
    op.create_index('idx_tasks_depends_on', 'tasks', ['depends_on'], postgresql_using='gin')

def downgrade():
    op.drop_index('idx_tasks_depends_on')
    op.drop_column('tasks', 'depends_on')
```

**Files to Create:**
- `src/orchestration/dependency_resolver.py` (200 lines)
- `tests/test_dependency_resolver.py` (100 tests)
- `tests/integration/test_dependency_integration.py` (40 tests)
- `alembic/versions/xxx_add_task_dependencies.py` (30 lines)

**Files to Modify:**
- `src/core/models.py` (+20 lines, Task model)
- `src/core/state.py` (+100 lines, dependency methods)
- `src/orchestrator.py` (+100 lines, dependency integration)
- `src/cli.py` (+50 lines, dependency commands)
- `config/default_config.yaml` (+10 lines)
- `requirements.txt` (+1 line, networkx)

**Test Coverage:** ≥90%

**Key Commits:**
- `feat: Add depends_on field to Task model (migration)`
- `feat: Implement DependencyResolver with DAG analysis`
- `feat: Add cycle detection and max depth validation`
- `feat: Implement cascading failure handling`
- `feat: Add CLI commands for task dependencies`
- `test: Add comprehensive dependency tests (100+ tests)`

---

## Example Usage

### Scenario 1: Multi-Phase Feature Development

```bash
# Create tasks with dependencies
obra task create "Design user authentication" --project 1
# Created task 1

obra task create "Implement auth backend" --depends-on 1 --project 1
# Created task 2, depends on [1]

obra task create "Implement auth frontend" --depends-on 1 --project 1
# Created task 3, depends on [1]

obra task create "Write integration tests" --depends-on 2,3 --project 1
# Created task 4, depends on [2, 3]

obra task create "Deploy to staging" --depends-on 4 --project 1
# Created task 5, depends on [4]

# Visualize
obra project graph 1
# Output:
# Task 1: [Design] (no dependencies)
#   ├─> Task 2: [Backend]
#   └─> Task 3: [Frontend]
#        └─> Task 4: [Tests]
#             └─> Task 5: [Deploy]

# Execute - automatic ordering
obra milestone execute 1
# Executes: 1 → 2,3 → 4 → 5 (in dependency order)
```

### Scenario 2: Cycle Detection

```bash
obra task create "Task A" --project 1
# Created task 1

obra task create "Task B" --depends-on 1 --project 1
# Created task 2, depends on [1]

obra task modify 1 --add-dependency 2
# ERROR: Circular dependency detected: [1 → 2 → 1]
```

### Scenario 3: Cascading Failure

```bash
# Tasks: 1 → 2 → 3 → 4
obra task execute 1  # ✓ Success
obra task execute 2  # ✗ Failure

# Output:
# Task 2 failed
# Blocking dependent tasks: [3, 4]
# Tasks 3 and 4 marked as 'blocked'
```

---

## Monitoring and Observability

### Metrics to Track

```python
# Dependency metrics
total_dependencies = sum(len(t.depends_on) for t in tasks)
avg_dependencies_per_task = total_dependencies / len(tasks)
max_depth = max(t.dependency_depth for t in tasks)
blocked_tasks = len([t for t in tasks if t.is_blocked])

# Execution metrics
execution_order = resolver.topological_sort(tasks)
parallelization_potential = len(ready_tasks)  # If we had parallel execution
```

### Log Format

```
DEPENDENCY_CHECK: task_id=4, depends_on=[2,3], all_complete=True, ready=True
DEPENDENCY_BLOCKED: task_id=5, blocked_by=4, reason=dependency_incomplete
CASCADING_FAILURE: failed_task=2, blocked_tasks=[3,4,5], count=3
CYCLE_DETECTED: cycle=[1,2,3,1], rejected=True
```

---

## References

### Internal Documentation
- [M9_IMPLEMENTATION_PLAN.md](../development/M9_IMPLEMENTATION_PLAN.md)
- [ARCHITECTURE.md](../architecture/ARCHITECTURE.md)

### External References
- [NetworkX Documentation](https://networkx.org/documentation/)
- [Topological Sorting](https://en.wikipedia.org/wiki/Topological_sorting)
- [Directed Acyclic Graph](https://en.wikipedia.org/wiki/Directed_acyclic_graph)

### Code Locations
- **DependencyResolver:** `src/orchestration/dependency_resolver.py`
- **Task Model:** `src/core/models.py` (Task class)
- **State Methods:** `src/core/state.py` (dependency methods)
- **Orchestrator:** `src/orchestrator.py` (execution loop)

---

## Related ADRs

- [ADR-007: Headless Mode Enhancements](ADR-007-headless-mode-enhancements.md)
- [ADR-008: Retry Logic](ADR-008-retry-logic.md)
- [003: State Management](003_state_management.md)

---

## Future Considerations

### Potential Improvements (v2.0+)

1. **Parallel Execution of Independent Tasks**
   - Execute ready tasks simultaneously
   - Requires multiple Claude Code instances
   - Complex state synchronization
   - Significant performance gains

2. **Conditional Dependencies**
   - "Task B depends on Task A only if condition X"
   - Dynamic dependency resolution
   - More expressive workflows

3. **Soft vs Hard Dependencies**
   - Soft: Task can run if dependency fails
   - Hard: Task blocked if dependency fails
   - More flexible failure handling

4. **Dependency Templates**
   - Pre-defined dependency patterns
   - "Feature development" template (design → implement → test)
   - Reusable workflow definitions

5. **Visual Dependency Editor**
   - Web UI for building dependency graphs
   - Drag-and-drop task ordering
   - Real-time cycle detection

### Open Questions

1. **Should we support OR dependencies?**
   - "Task C depends on (Task A OR Task B)"
   - More complex but more expressive

2. **Should we support weighted dependencies?**
   - Some dependencies more important than others
   - Affects execution priority

3. **How to handle long-running dependencies?**
   - Task B waits hours for Task A
   - Timeout? Notification? Suspension?

4. **Should cascading failures be configurable per task?**
   - Some tasks may want to run despite failures
   - Task-level cascade_failures flag

---

**Last Updated:** 2025-11-04
**Version:** 1.0
**Status:** Accepted
**Implementation:** Planned for M9 Phase 5 (Days 6-10)
