# ADR-015: Project Infrastructure Maintenance System

**Status**: Accepted
**Date**: 2025-11-11
**Deciders**: Development Team
**Technical Story**: Project Infrastructure Maintenance (v1.4.0)

---

## Context and Problem Statement

Obra currently requires **manual intervention** to maintain project documentation (CHANGELOG, architecture docs, ADRs, guides, README, etc.) after completing epics or milestones. This creates several problems:

**Key Problems**:
1. **Documentation Drift**: Docs become stale as code evolves (e.g., ARCHITECTURE.md was 2 versions behind)
2. **Manual Overhead**: User must manually trigger documentation updates after each milestone
3. **Inconsistent Maintenance**: No systematic process ensures all docs are updated
4. **Knowledge Loss**: Completed implementation plans accumulate in active directories instead of archive
5. **Missing Accountability**: No tracking of documentation freshness or staleness

**Example**: After completing NL Command Interface (5 stories), we manually:
- Created ADR-014
- Updated CHANGELOG.md
- Updated ARCHITECTURE.md with 5 new feature sections
- Updated docs/README.md
- Archived 10 completed implementation plans

**This manual process should be automated** - Obra should maintain its own documentation infrastructure just like it maintains the user's code.

---

## Decision Drivers

1. **Self-Maintenance**: Obra should "eat its own dog food" - maintain its own project infrastructure
2. **Consistency**: Documentation should always reflect current system state
3. **Automation**: Reduce manual overhead for users
4. **Freshness Tracking**: Know when documentation is stale
5. **Scalability**: As Obra grows, manual maintenance becomes untenable
6. **Agile Integration**: Leverage existing epic/story/milestone tracking
7. **Minimal Overhead**: Don't slow down development with excessive maintenance

---

## Considered Options

### Option 1: Event-Driven Documentation Maintenance (RECOMMENDED)

Automatically trigger documentation maintenance at key project events:
- **Epic completion** → Lightweight update (CHANGELOG, architecture if needed)
- **Milestone achievement** → Comprehensive update (all docs, ADRs, archiving)
- **Version bump** → Full documentation review

**Architecture**: Hook into StateManager epic/milestone completion methods.

**Pros**:
- ✅ Automatic - no user intervention required
- ✅ Timely - docs updated immediately after changes
- ✅ Contextual - maintenance knows what changed (epic context)
- ✅ Leverages existing Agile hierarchy
- ✅ Minimal overhead (lightweight updates most of the time)

**Cons**:
- Adds complexity to StateManager
- May create maintenance tasks user doesn't want
- Requires configuration to control behavior

---

### Option 2: Periodic Scheduled Maintenance

Run scheduled documentation checks (weekly/monthly) and create maintenance tasks if stale.

**Architecture**: Scheduled job checks document `last_modified` vs `last_code_change`.

**Pros**:
- ✅ Simple implementation (cron-style scheduler)
- ✅ User controls frequency
- ✅ Batches multiple doc updates into single task

**Cons**:
- ❌ Reactive - docs may be stale for days/weeks
- ❌ No context about what changed (just "docs are stale")
- ❌ May miss important documentation needs
- ❌ Requires external scheduler

---

### Option 3: Manual Infrastructure Tasks

Rely on user to manually create infrastructure tasks using special task type.

**Architecture**: `TaskType.INFRASTRUCTURE` for project maintenance tasks.

**Pros**:
- ✅ Simple - no automation needed
- ✅ User has full control
- ✅ No risk of unwanted maintenance tasks

**Cons**:
- ❌ **Doesn't solve the problem** - still requires manual intervention
- ❌ User may forget or deprioritize documentation
- ❌ Inconsistent maintenance patterns

---

### Option 4: Pre-Commit Hook Documentation Checks

Check documentation freshness in pre-commit hooks, warn if stale.

**Pros**:
- ✅ Catches stale docs before they're committed
- ✅ Integrates with existing Git workflow

**Cons**:
- ❌ Only works if Git integration enabled
- ❌ Blocks commits (annoying)
- ❌ No automated maintenance - just warnings

---

## Decision Outcome

**Chosen Option**: **Hybrid Event-Driven + Periodic Checks**

Combine Option 1 (event-driven) with Option 2 (periodic checks) for comprehensive coverage:

### Phase 1: Event-Driven Maintenance (v1.4.0)
- **Epic Completion Hook**: Lightweight update (CHANGELOG, affected docs)
- **Milestone Achievement Hook**: Comprehensive update (all docs, create ADRs, archive plans)
- **Version Bump Hook**: Full documentation review

### Phase 2: Periodic Freshness Checks (v1.4.0)
- **Weekly Check**: Scan for stale docs (>30 days for critical, >60 for important)
- **Notification**: Alert user if maintenance recommended
- **Optional Auto-Task**: Create maintenance task if configured

### Phase 3: Infrastructure Task Type (v1.5.0) - FUTURE
- **TaskType.INFRASTRUCTURE**: Special task type for project maintenance
- **Batching**: Multiple doc updates in single task
- **CLI Commands**: `obra infra check`, `obra infra update`, `obra infra archive`

**Rationale**:
- Event-driven ensures timely updates with full context
- Periodic checks catch anything missed
- Phased rollout reduces implementation risk
- User can disable if not wanted (`documentation.enabled: false`)

---

## Implementation Architecture

### Component: DocumentationManager

**Location**: `src/utils/documentation_manager.py`

**Responsibilities**:
1. Track documentation freshness (last modified vs last code change)
2. Detect stale documentation (threshold-based)
3. Generate maintenance tasks with context
4. Archive completed implementation plans
5. Update CHANGELOG, architecture docs, ADRs, guides

**Key Methods**:
```python
class DocumentationManager:
    def __init__(self, state_manager: StateManager, config: Config):
        """Initialize documentation manager."""

    def check_documentation_freshness(self) -> Dict[str, DocumentStatus]:
        """Check which docs are stale.

        Returns:
            Dict mapping document path to freshness status
        """

    def create_maintenance_task(
        self,
        trigger: str,
        scope: str,
        context: Dict[str, Any]
    ) -> int:
        """Create documentation maintenance task.

        Args:
            trigger: 'epic_complete' | 'milestone_achieved' | 'version_bump' | 'periodic'
            scope: 'lightweight' | 'comprehensive' | 'full_review'
            context: Dict with epic_id, milestone_id, changes, etc.

        Returns:
            Task ID of created maintenance task
        """

    def generate_maintenance_prompt(
        self,
        stale_docs: List[str],
        context: Dict[str, Any]
    ) -> str:
        """Generate detailed prompt for documentation maintenance.

        Includes:
        - List of stale documents
        - Recent changes (from epic/milestone)
        - What needs updating
        - References to documentation patterns
        """

    def archive_completed_plans(self, epic_id: int) -> List[str]:
        """Archive implementation plans for completed epic.

        Returns:
            List of archived file paths
        """

    def update_changelog(self, epic: Task) -> None:
        """Update CHANGELOG.md with epic completion."""

    def suggest_adr_creation(self, epic: Task) -> bool:
        """Check if epic requires ADR creation."""
```

### StateManager Integration

**Epic Completion Hook**:
```python
def complete_epic(self, epic_id: int) -> None:
    """Mark epic complete and trigger documentation maintenance."""
    # Mark epic complete
    epic = self.get_task(epic_id)
    epic.status = TaskStatus.COMPLETED
    epic.completed_at = datetime.utcnow()

    # Check if documentation maintenance enabled
    if self.config.get('documentation.enabled', False):
        doc_mgr = DocumentationManager(self, self.config)

        # Determine maintenance scope
        scope = 'lightweight'
        if epic.requires_adr or epic.has_architectural_changes:
            scope = 'comprehensive'

        # Create maintenance task
        maintenance_task_id = doc_mgr.create_maintenance_task(
            trigger='epic_complete',
            scope=scope,
            context={
                'epic_id': epic_id,
                'epic_title': epic.title,
                'stories': self.get_epic_stories(epic_id),
                'changes': epic.changes_summary  # New field
            }
        )

        logger.info(
            f"Created documentation maintenance task {maintenance_task_id} "
            f"for epic {epic_id}"
        )
```

**Milestone Achievement Hook**:
```python
def achieve_milestone(self, milestone: Milestone) -> None:
    """Mark milestone achieved and trigger comprehensive maintenance."""
    milestone.achieved = True
    milestone.achieved_at = datetime.utcnow()

    # Comprehensive documentation maintenance
    if self.config.get('documentation.enabled', False):
        doc_mgr = DocumentationManager(self, self.config)

        # Get all epics in milestone
        completed_epics = [
            self.get_task(epic_id)
            for epic_id in milestone.required_epic_ids
        ]

        # Create comprehensive maintenance task
        maintenance_task_id = doc_mgr.create_maintenance_task(
            trigger='milestone_achieved',
            scope='comprehensive',
            context={
                'milestone_id': milestone.id,
                'milestone_name': milestone.name,
                'epics': [e.to_dict() for e in completed_epics],
                'version': milestone.version  # e.g., "v1.4.0"
            }
        )
```

### Configuration Schema

```yaml
# Project Infrastructure Maintenance Configuration
documentation:
  # Master enable/disable switch
  enabled: true

  # Automatically create maintenance tasks (vs just notify)
  auto_maintain: true

  # Event-driven triggers
  triggers:
    epic_complete:
      enabled: true
      scope: lightweight  # 'lightweight' | 'comprehensive'
      auto_create_task: true

    milestone_achieved:
      enabled: true
      scope: comprehensive
      auto_create_task: true

    version_bump:
      enabled: true
      scope: full_review
      auto_create_task: true

    periodic:
      enabled: true
      interval: weekly  # 'daily' | 'weekly' | 'monthly'
      scope: freshness_check
      day_of_week: friday  # For weekly
      auto_create_task: false  # Just notify

  # Documents to maintain
  maintenance_targets:
    - CHANGELOG.md
    - docs/architecture/ARCHITECTURE.md
    - docs/README.md
    - docs/decisions/  # ADRs
    - docs/guides/      # User guides

  # Freshness thresholds (days since last update)
  freshness_thresholds:
    critical: 30   # CHANGELOG, README
    important: 60  # Architecture, ADRs
    normal: 90     # Guides, design docs

  # Archive settings
  archive:
    enabled: true
    source_dir: docs/development
    archive_dir: docs/archive/development
    patterns:
      - "*_IMPLEMENTATION_PLAN.md"
      - "*_COMPLETION_PLAN.md"
      - "*_GUIDE.md"  # Implementation guides

  # Maintenance task settings
  task_config:
    priority: 3  # Lower than feature work (1-2)
    assigned_agent: null  # null = use default agent
    assigned_llm: null    # null = use default LLM
    auto_execute: false   # Require manual approval before execution
```

### Task Model Updates

**Add Fields to Task Model**:
```python
class Task(Base):
    # ... existing fields ...

    # Documentation metadata (NEW)
    requires_adr: Optional[bool] = Column(Boolean, default=False)
    has_architectural_changes: Optional[bool] = Column(Boolean, default=False)
    changes_summary: Optional[str] = Column(Text, nullable=True)
    documentation_status: Optional[str] = Column(String, default='pending')  # 'pending' | 'updated' | 'skipped'
```

**Add Fields to Milestone Model**:
```python
class Milestone(Base):
    # ... existing fields ...

    # Version tracking (NEW)
    version: Optional[str] = Column(String, nullable=True)  # e.g., "v1.4.0"
```

---

## Consequences

### Positive

1. **Automatic Documentation Maintenance**: Docs stay fresh without manual intervention
2. **Contextual Updates**: Maintenance tasks know what changed (epic/milestone context)
3. **Systematic Process**: Consistent pattern for all documentation updates
4. **Freshness Tracking**: Know which docs are stale at any time
5. **Reduced Cognitive Load**: User doesn't need to remember to update docs
6. **Scalability**: As project grows, documentation scales automatically
7. **Self-Maintaining**: Obra maintains its own infrastructure ("eat your own dog food")
8. **Configurable**: User can disable or customize behavior

### Negative

1. **Increased Complexity**: New component (DocumentationManager), StateManager hooks
2. **Potential Noise**: May create maintenance tasks user doesn't want
3. **Configuration Overhead**: Requires thoughtful configuration
4. **Storage**: Additional task entries for maintenance
5. **Execution Time**: Maintenance tasks consume orchestration cycles
6. **False Positives**: May flag docs as stale when they're actually fine

### Neutral

1. **Phased Rollout**: Can be implemented incrementally (Phase 1 → Phase 2 → Phase 3)
2. **User Control**: Can be disabled via `documentation.enabled: false`
3. **Opt-In Auto-Execute**: Requires manual approval by default (`auto_execute: false`)

---

## Validation Metrics

### Success Criteria (v1.4.0)

**Functional**:
- ✅ Epic completion creates maintenance task (if `requires_adr` or `has_architectural_changes`)
- ✅ Milestone achievement creates comprehensive maintenance task
- ✅ Periodic check detects stale docs correctly (>30/60/90 days)
- ✅ Maintenance tasks include full context (epic details, changes)
- ✅ Archived plans moved to correct directory

**Quality**:
- ✅ Test coverage >90% for DocumentationManager
- ✅ Integration tests for epic/milestone hooks
- ✅ Configuration validation (invalid config rejected)

**Usability**:
- ✅ User can disable feature entirely
- ✅ User can customize thresholds and triggers
- ✅ Maintenance tasks clearly describe what needs updating

### Performance Targets

| Operation | Target | Rationale |
|-----------|--------|-----------|
| Freshness check | <1s | Fast scan of file timestamps |
| Create maintenance task | <100ms | Simple database insert |
| Epic completion hook | <500ms | Minimal overhead to epic completion |
| Archive plans | <2s | File copy operations |

---

## Migration Strategy

### Phase 1: Core Implementation (v1.4.0 - Week 1-2)

**Story 1.1: DocumentationManager Foundation**
- Implement `DocumentationManager` class
- Freshness checking logic
- Task creation methods
- 20 unit tests (>90% coverage)

**Story 1.2: StateManager Integration**
- Add epic completion hook
- Add milestone achievement hook
- Add Task model fields (`requires_adr`, `has_architectural_changes`, `changes_summary`)
- 15 unit tests

**Story 1.3: Configuration System**
- Add `documentation` config section
- Configuration validation
- Default configuration in `default_config.yaml`
- 10 unit tests

**Story 1.4: Integration Testing**
- E2E test: Epic complete → maintenance task created
- E2E test: Milestone achieve → comprehensive maintenance
- E2E test: Configuration variations
- 8 integration tests

### Phase 2: Periodic Checks (v1.4.0 - Week 3)

**Story 2.1: Scheduled Freshness Checks**
- Implement periodic scanning (weekly/monthly)
- Notification system (log warnings)
- Optional auto-task creation
- 12 unit tests

**Story 2.2: Documentation**
- User guide: `docs/guides/PROJECT_INFRASTRUCTURE_GUIDE.md`
- Update ARCHITECTURE.md with new component
- ADR-015 (this document)
- CHANGELOG.md entry

### Phase 3: Infrastructure Task Type (v1.5.0 - FUTURE)

**Story 3.1: TaskType.INFRASTRUCTURE**
- Add new task type enum value
- Special handling (batching, priority)
- Update StateManager queries

**Story 3.2: CLI Commands**
- `obra infra check` - Check documentation freshness
- `obra infra update` - Create maintenance task
- `obra infra archive` - Archive completed plans

---

## Example Usage

### Scenario 1: Epic Completion (Automatic)

```python
# User completes epic (via CLI or API)
obra epic execute 5

# Internally, Obra:
# 1. Executes all stories in epic
# 2. Marks epic complete
# 3. Epic completion hook triggers:
if epic.requires_adr:
    doc_mgr.create_maintenance_task(
        trigger='epic_complete',
        scope='comprehensive',
        context={'epic_id': 5, 'epic_title': 'API Gateway'}
    )

# 4. Maintenance task created (Task #123)
# 5. User sees: "Created documentation maintenance task #123 for epic 5"
```

### Scenario 2: Milestone Achievement (Automatic)

```python
# User achieves milestone
obra milestone achieve 3

# Internally, Obra:
# 1. Checks all required epics complete
# 2. Marks milestone achieved
# 3. Milestone hook triggers:
doc_mgr.create_maintenance_task(
    trigger='milestone_achieved',
    scope='comprehensive',
    context={
        'milestone_id': 3,
        'milestone_name': 'API Gateway Complete',
        'epics': [5, 6, 7],
        'version': 'v1.5.0'
    }
)

# 4. Comprehensive maintenance task created (Task #124)
# 5. Prompt includes: "Update docs for v1.5.0 milestone with 3 epics..."
```

### Scenario 3: Periodic Check (Weekly)

```bash
# Friday 5pm, Obra runs scheduled check
# Internally:
stale_docs = doc_mgr.check_documentation_freshness()

if stale_docs:
    logger.warning(
        f"Stale documentation detected: {list(stale_docs.keys())}\n"
        f"Run 'obra infra update' to create maintenance task"
    )

    if config.get('documentation.triggers.periodic.auto_create_task'):
        doc_mgr.create_maintenance_task(
            trigger='periodic',
            scope='freshness_check',
            context={'stale_docs': stale_docs}
        )
```

### Scenario 4: Manual Maintenance (User-Initiated)

```bash
# User manually checks freshness
obra infra check

# Output:
# Documentation Freshness Report:
#   CRITICAL (>30 days):
#     - CHANGELOG.md (42 days)
#   IMPORTANT (>60 days):
#     - docs/architecture/ARCHITECTURE.md (65 days)
#   NORMAL (>90 days):
#     None
#
# Run 'obra infra update' to create maintenance task

# User creates maintenance task
obra infra update

# Output:
# Created documentation maintenance task #125
# Priority: 3 (LOW)
# Scope: COMPREHENSIVE
# Stale docs: CHANGELOG.md, ARCHITECTURE.md
```

---

## Alternatives Considered and Rejected

### Alternative 1: Git Pre-Commit Hooks

Use Git pre-commit hooks to check documentation freshness and block commits if stale.

**Rejected because**:
- ❌ Blocks commits (frustrating for users)
- ❌ Only works if Git integration enabled
- ❌ No automated maintenance - just warnings
- ❌ Can't provide context about what changed

### Alternative 2: External Documentation Generator

Use tools like Sphinx, MkDocs to auto-generate documentation from code.

**Rejected because**:
- ❌ Only handles API docs, not architecture/guides/ADRs
- ❌ Doesn't solve the "what changed" problem
- ❌ Requires separate tooling/dependencies
- ❌ Not integrated with Obra's Agile workflow

### Alternative 3: Manual Reminders Only

Just remind user to update docs, don't create tasks.

**Rejected because**:
- ❌ Doesn't reduce manual overhead
- ❌ Easy to ignore reminders
- ❌ No systematic process

---

## Future Enhancements (v1.5+)

### v1.5: Infrastructure Task Type
- `TaskType.INFRASTRUCTURE` for project maintenance
- Special handling (batching, priority)
- CLI commands: `obra infra check/update/archive`

### v1.6: Intelligent Maintenance
- **LLM-Powered Freshness Detection**: Use LLM to determine if doc is actually stale (semantic analysis)
- **Automatic Minor Updates**: LLM can make trivial updates without creating task (e.g., update test count)
- **Documentation Diff Summary**: Show user what changed since last update

### v2.0: Advanced Maintenance
- **Multi-Project Documentation**: Maintain docs across multiple projects
- **Documentation Quality Scoring**: Score documentation completeness/freshness
- **Template-Based Generation**: Auto-generate boilerplate (ADR templates, guide skeletons)
- **Documentation Search**: Semantic search across all project docs

---

## References

- **Implementation Plan**: [docs/development/PROJECT_INFRASTRUCTURE_IMPLEMENTATION_PLAN.md](../development/PROJECT_INFRASTRUCTURE_IMPLEMENTATION_PLAN.md)
- **Machine-Optimized Plan**: [docs/development/PROJECT_INFRASTRUCTURE_IMPLEMENTATION_PLAN.yaml](../development/PROJECT_INFRASTRUCTURE_IMPLEMENTATION_PLAN.yaml)
- **Epic Breakdown**: [docs/development/PROJECT_INFRASTRUCTURE_EPIC_BREAKDOWN.md](../development/PROJECT_INFRASTRUCTURE_EPIC_BREAKDOWN.md)
- **Related ADRs**:
  - [ADR-013: Agile Work Hierarchy](ADR-013-adopt-agile-work-hierarchy.md) - Leverages epic/milestone tracking
  - [ADR-009: Git Auto-Integration](ADR-009-git-auto-integration.md) - Similar automation pattern

---

## Decision Review

**Review Date**: 2025-11-11
**Status**: ✅ **Accepted**
**Implementation Target**: v1.4.0 (Phase 1-2), v1.5.0 (Phase 3)

**Next Steps**:
1. Create detailed implementation plan (human-readable)
2. Create machine-optimized plan (LLM-consumable YAML)
3. Create epic/story breakdown
4. Update CHANGELOG.md with v1.4 "Unreleased" section
5. Implement Phase 1 (Stories 1.1-1.4)

---

**Last Updated**: 2025-11-11
**Author**: Development Team
**Reviewers**: N/A (Initial Decision)
