# Project Infrastructure Maintenance Guide

**Version:** 1.4.0
**Last Updated:** November 11, 2025
**Status:** Production Ready

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Configuration](#configuration)
4. [Event-Driven Triggers](#event-driven-triggers)
5. [Periodic Checks](#periodic-checks)
6. [Maintenance Tasks](#maintenance-tasks)
7. [Troubleshooting](#troubleshooting)
8. [FAQ](#faq)
9. [Examples](#examples)

---

## Overview

### What is Project Infrastructure Maintenance?

The Project Infrastructure Maintenance System automatically keeps your project documentation up-to-date by creating maintenance tasks at key project events and detecting stale documentation through periodic checks.

### Benefits

- **Automated Documentation Maintenance:** No more forgotten documentation updates
- **Event-Driven Updates:** Documentation tasks created when epics complete or milestones are achieved
- **Freshness Monitoring:** Periodic checks detect documentation that hasn't been updated in 30/60/90 days
- **Configurable:** Enable/disable features, customize thresholds, control task creation
- **Self-Maintaining:** Obra "eats its own dog food" by maintaining its own documentation

### When to Use

Use this system when:
- You want automated reminders to update documentation
- Your project has frequent epics/milestones that require documentation updates
- You need to ensure CHANGELOG, architecture docs, and ADRs stay current
- You want to detect stale documentation automatically

### When NOT to Use

Skip this feature when:
- Your project is small or documentation updates are infrequent
- You prefer manual documentation maintenance workflows
- You don't want automatic task creation

---

## Quick Start

### Step 1: Enable Documentation Maintenance

Edit `config/default_config.yaml`:

```yaml
documentation:
  enabled: true  # Master switch - turns on the entire system
  auto_maintain: true  # Automatically create tasks (vs notification only)
```

### Step 2: Configure Triggers

Choose which events should trigger documentation maintenance:

```yaml
documentation:
  triggers:
    # Epic completion trigger
    epic_complete:
      enabled: true
      scope: comprehensive
      auto_create_task: true

    # Milestone achievement trigger
    milestone_achieved:
      enabled: true
      scope: comprehensive
      auto_create_task: true

    # Periodic freshness checks
    periodic:
      enabled: true
      interval_days: 7
      scope: lightweight
      auto_create_task: true
```

### Step 3: Mark Epics for Documentation

When creating epics that require documentation updates:

```python
epic_id = state_manager.create_epic(
    project_id=1,
    title="User Authentication System",
    description="OAuth + MFA + session management",
    requires_adr=True,  # This epic requires an ADR
    has_architectural_changes=True,  # This epic changes architecture
    changes_summary="Integrated OAuth, added MFA, implemented session mgmt"
)
```

### Step 4: Complete Epic → Task Created

When you complete the epic:

```python
state_manager.complete_epic(epic_id)
# ✅ Maintenance task automatically created
```

That's it! The system will create a documentation maintenance task with full context about what needs updating.

---

## Configuration

### Master Configuration

**Location:** `config/default_config.yaml` under `documentation:` section

```yaml
documentation:
  enabled: true  # Master enable/disable switch
  auto_maintain: true  # Auto-create tasks vs notification only
```

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `enabled` | bool | `false` | Master switch - disables entire system if false |
| `auto_maintain` | bool | `true` | If true, creates tasks. If false, logs notifications only |

### Maintenance Targets

Documents to check for freshness:

```yaml
documentation:
  maintenance_targets:
    - 'CHANGELOG.md'
    - 'docs/architecture/ARCHITECTURE.md'
    - 'docs/README.md'
    - 'docs/decisions/'  # Directory - checks all .md files
    - 'docs/guides/'
```

**Default targets:** CHANGELOG, architecture docs, README, ADRs, guides

**Customization:** Add project-specific documentation paths

### Freshness Thresholds

How old a document can be before considered "stale":

```yaml
documentation:
  freshness_thresholds:
    critical: 30   # days (e.g., CHANGELOG, README)
    important: 60  # days (e.g., architecture docs, ADRs)
    normal: 90     # days (e.g., guides)
```

**Document Categories:**
- **Critical:** CHANGELOG.md, README.md (30-day threshold)
- **Important:** architecture/, decisions/ (60-day threshold)
- **Normal:** guides/, other docs (90-day threshold)

### Archive Configuration

Automatically archive completed implementation plans:

```yaml
documentation:
  archive:
    enabled: true
    source_dir: 'docs/development'
    archive_dir: 'docs/archive/development'
    patterns:
      - '*_IMPLEMENTATION_PLAN.md'
      - '*_COMPLETION_PLAN.md'
      - '*_GUIDE.md'
```

### Task Configuration

Control task properties:

```yaml
documentation:
  task_config:
    priority: 3  # Task priority (1-10)
    assigned_agent: 'CLAUDE_CODE'  # Who handles the task
```

---

## Event-Driven Triggers

### Epic Completion Trigger

**When:** An epic is marked as complete via `state_manager.complete_epic(epic_id)`

**Conditions for Task Creation:**
- Epic has `requires_adr=True` OR
- Epic has `has_architectural_changes=True`

**Configuration:**

```yaml
documentation:
  triggers:
    epic_complete:
      enabled: true  # Enable this trigger
      scope: comprehensive  # Maintenance scope
      auto_create_task: true  # Create task vs notification
```

**Example:**

```python
# Create epic with documentation flags
epic_id = state_manager.create_epic(
    project_id=1,
    title="Payment Processing",
    description="Stripe integration",
    requires_adr=True,  # Requires ADR
    changes_summary="Integrated Stripe API, added payment models"
)

# Complete epic → maintenance task created
state_manager.complete_epic(epic_id)

# Result: Task created with title:
# "Documentation: Update docs for Epic #1"
```

**Task Context Includes:**
- Epic ID, title, description
- Changes summary
- List of stories in epic
- Stale document list (if any)

### Milestone Achievement Trigger

**When:** A milestone is marked as achieved via `state_manager.achieve_milestone(milestone_id)`

**Conditions:** Always creates task when milestone achieved (if enabled)

**Configuration:**

```yaml
documentation:
  triggers:
    milestone_achieved:
      enabled: true
      scope: comprehensive  # Always comprehensive for milestones
      auto_create_task: true
```

**Example:**

```python
# Create milestone
milestone_id = state_manager.create_milestone(
    project_id=1,
    name="v1.4.0 Release",
    description="Project Infrastructure Maintenance complete",
    required_epic_ids=[1, 2, 3],
    version="v1.4.0"
)

# Achieve milestone → comprehensive maintenance task created
state_manager.achieve_milestone(milestone_id)

# Result: Task created with title:
# "Documentation: v1.4.0 Release milestone achieved"
```

**Task Context Includes:**
- Milestone ID, name, description
- Version number
- All completed epics in milestone
- Stale document list (if any)

### Version Bump Trigger

**When:** Project version is bumped (future feature)

**Configuration:**

```yaml
documentation:
  triggers:
    version_bump:
      enabled: true
      scope: full_review  # Comprehensive review for releases
      auto_create_task: true
```

**Note:** Version bump detection not yet implemented (planned for v1.5)

---

## Periodic Checks

### Overview

Periodic checks run at regular intervals to detect stale documentation, independent of epic/milestone events.

**Use Cases:**
- Detect documentation drift between milestones
- Catch docs that become stale due to code changes outside epic workflow
- Regular "health check" for documentation freshness

### Configuration

```yaml
documentation:
  triggers:
    periodic:
      enabled: true  # Enable periodic checks
      interval_days: 7  # Check every 7 days
      scope: lightweight  # Maintenance scope
      auto_create_task: true  # Create task if stale docs found
```

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `enabled` | bool | `false` | Enable periodic freshness checks |
| `interval_days` | int | `7` | Check interval in days |
| `scope` | str | `lightweight` | Scope: lightweight, comprehensive, full_review |
| `auto_create_task` | bool | `true` | Create task vs log notification |

### Starting Periodic Checks

**In Orchestrator initialization:**

```python
from src.utils.documentation_manager import DocumentationManager

# Initialize
state_manager = StateManager.get_instance()
config = Config.load()
doc_mgr = DocumentationManager(state_manager, config)

# Start periodic checks
doc_mgr.start_periodic_checks(project_id=1)
```

**Automatic Rescheduling:**
After each check, the system automatically schedules the next check. No manual intervention needed.

### Stopping Periodic Checks

**Graceful shutdown:**

```python
# In application shutdown
doc_mgr.stop_periodic_checks()
```

**Automatic cleanup:** Daemon threads ensure cleanup on process exit even if not explicitly stopped.

### Periodic Check Behavior

**Check Flow:**
1. System checks all `maintenance_targets` for staleness
2. Compares file modification time against thresholds (30/60/90 days)
3. If stale docs found:
   - **auto_create_task=true:** Creates maintenance task
   - **auto_create_task=false:** Logs warning with stale doc list
4. Reschedules next check

**No Stale Docs:** If all docs are fresh, no task created, just debug log

**Error Handling:** Errors logged but don't crash scheduler, next check still scheduled

---

## Maintenance Tasks

### Task Properties

**Maintenance tasks are standard Obra tasks with:**
- **Title:** Descriptive (e.g., "Documentation: Update docs for Epic #5")
- **Priority:** Configurable (default: 3)
- **Assigned To:** CLAUDE_CODE (default) or configurable agent
- **Type:** TASK (standard task)
- **Status:** PENDING (awaiting execution)

### Task Context

**Every maintenance task includes rich context:**

```python
{
    'trigger': 'epic_complete',  # or 'milestone_achieved', 'periodic'
    'scope': 'comprehensive',  # or 'lightweight', 'full_review'
    'maintenance_context': {
        'epic_id': 5,
        'epic_title': 'User Auth System',
        'changes': 'Added OAuth, MFA, session management',
        'stories': [{'id': 10, 'title': 'OAuth integration'}, ...]
    },
    'stale_docs': [
        'CHANGELOG.md',
        'docs/architecture/ARCHITECTURE.md'
    ]
}
```

### Task Description (Prompt)

**Generated automatically by `generate_maintenance_prompt()`:**

```markdown
# Documentation Maintenance Task

**Trigger**: epic_complete
**Scope**: comprehensive

## Epic Completion: #5 - User Authentication System

**Changes Summary**:
Added OAuth integration, MFA support, and session management

## Stale Documentation Detected

The following documents need updating:
- `CHANGELOG.md` (45 days old, threshold: 30 days)
- `docs/architecture/ARCHITECTURE.md` (62 days old, threshold: 60 days)

## Maintenance Instructions

Please update the following project documentation:

1. **CHANGELOG.md**: Add entry for completed work
2. **Architecture docs**: Update if architectural changes made
3. **ADRs**: Create new ADR if significant decision made
4. **Guides**: Update user/developer guides if needed
5. **README**: Update if project structure or setup changed

### Archive Completed Plans
...
```

### Executing Maintenance Tasks

**Via CLI:**

```bash
# List pending documentation tasks
obra task list --filter "Documentation:"

# Execute specific task
obra task execute <task_id>
```

**Via API:**

```python
# Execute task
orchestrator.execute_task(task_id)
```

---

## Troubleshooting

### Issue: No Tasks Being Created

**Symptoms:** Epic completed, but no documentation task created

**Check:**
1. Is `documentation.enabled: true`?
2. Is `documentation.auto_maintain: true`?
3. Is `triggers.epic_complete.enabled: true`?
4. Does epic have `requires_adr=True` or `has_architectural_changes=True`?

**Fix:**
```yaml
documentation:
  enabled: true  # Must be true
  auto_maintain: true  # Must be true
  triggers:
    epic_complete:
      enabled: true  # Must be true
```

### Issue: Periodic Checks Not Running

**Symptoms:** No periodic maintenance tasks after 7 days

**Check:**
1. Is `documentation.triggers.periodic.enabled: true`?
2. Did you call `doc_mgr.start_periodic_checks()`?
3. Check logs for "Started periodic documentation checks"

**Fix:**
```python
# In orchestrator initialization
doc_mgr.start_periodic_checks(project_id=1)
```

### Issue: Too Many Tasks Created

**Symptoms:** Too many documentation tasks, overwhelming

**Solutions:**

**Option 1: Notification Only**
```yaml
documentation:
  auto_maintain: false  # Log notifications instead of creating tasks
```

**Option 2: Disable Periodic**
```yaml
documentation:
  triggers:
    periodic:
      enabled: false  # Only event-driven (epic/milestone)
```

**Option 3: Increase Interval**
```yaml
documentation:
  triggers:
    periodic:
      interval_days: 30  # Monthly instead of weekly
```

### Issue: Incorrect Staleness Detection

**Symptoms:** Documents marked stale incorrectly

**Check thresholds:**
```yaml
documentation:
  freshness_thresholds:
    critical: 30  # CHANGELOG, README
    important: 60  # Architecture, ADRs
    normal: 90  # Guides
```

**Adjust to your project cadence**

### Issue: Archived Plans Missing

**Symptoms:** Implementation plans not archived after epic completion

**Check:**
```yaml
documentation:
  archive:
    enabled: true  # Must be true
    source_dir: 'docs/development'  # Correct source?
    patterns:
      - '*_IMPLEMENTATION_PLAN.md'  # Matches your files?
```

**Manual archive:**
```python
doc_mgr.archive_completed_plans(epic_id=5)
```

---

## FAQ

### Q: What happens if I disable `documentation.enabled`?

**A:** Entire system is disabled. No tasks created, no periodic checks run, no hooks execute.

### Q: What's the difference between `auto_maintain` and `auto_create_task`?

**A:**
- `auto_maintain` (global): Controls task creation for ALL triggers
- `auto_create_task` (per-trigger): Controls task creation for specific trigger

Both must be `true` for task creation.

### Q: Can I customize maintenance task content?

**A:** Yes, edit `generate_maintenance_prompt()` in `src/utils/documentation_manager.py` to customize prompt structure.

### Q: How do I add custom documentation targets?

**A:** Add paths to `maintenance_targets`:
```yaml
documentation:
  maintenance_targets:
    - 'CHANGELOG.md'
    - 'docs/my-custom-doc.md'  # Custom
    - 'specs/'  # Custom directory
```

### Q: Can I have different intervals for different document types?

**A:** Not yet. Currently, one global `interval_days`. Planned for v1.5 as enhancement.

### Q: What if epic doesn't have `requires_adr` or `has_architectural_changes`?

**A:** No task created for that epic. Use these flags to mark epics requiring documentation.

### Q: How do I test without creating real tasks?

**A:** Set `auto_maintain: false` to log notifications only:
```yaml
documentation:
  auto_maintain: false  # Logs warnings, no tasks
```

### Q: Can I retroactively create documentation tasks?

**A:** Yes, manually create task or call:
```python
doc_mgr.create_maintenance_task(
    trigger='epic_complete',
    scope='comprehensive',
    context={'epic_id': 5, ...}
)
```

### Q: How do periodic checks survive restarts?

**A:** They don't. Timers are in-memory only. Call `start_periodic_checks()` on startup to resume.

---

## Examples

### Example 1: Basic Epic with Documentation

```python
# Create epic
epic_id = state_manager.create_epic(
    project_id=1,
    title="API Gateway",
    description="Centralized API gateway with rate limiting",
    requires_adr=True,
    has_architectural_changes=True,
    changes_summary="Added gateway, implemented rate limiting, configured routing"
)

# Add stories
story1 = state_manager.create_story(1, epic_id, "Rate limiting", "As a user...")
story2 = state_manager.create_story(1, epic_id, "API routing", "As a user...")

# Complete stories
state_manager.update_task_status(story1, TaskStatus.COMPLETED)
state_manager.update_task_status(story2, TaskStatus.COMPLETED)

# Complete epic → documentation task created
state_manager.complete_epic(epic_id)

# Result: Maintenance task created with:
# - Title: "Documentation: Update docs for Epic #1"
# - Context: epic details, changes summary, story list
# - Instructions: Update CHANGELOG, architecture docs, create ADR
```

### Example 2: Milestone with Multiple Epics

```python
# Create and complete 3 epics
epic1 = state_manager.create_epic(1, "Auth System", "...", requires_adr=True)
epic2 = state_manager.create_epic(1, "Payment Processing", "...", requires_adr=True)
epic3 = state_manager.create_epic(1, "Notification Service", "...", requires_adr=True)

# Complete all epics
state_manager.complete_epic(epic1)  # Creates doc task for epic 1
state_manager.complete_epic(epic2)  # Creates doc task for epic 2
state_manager.complete_epic(epic3)  # Creates doc task for epic 3

# Create milestone
milestone_id = state_manager.create_milestone(
    project_id=1,
    name="v1.4.0 Release",
    required_epic_ids=[epic1, epic2, epic3],
    version="v1.4.0"
)

# Achieve milestone → comprehensive doc task created
state_manager.achieve_milestone(milestone_id)

# Result: Comprehensive task with all 3 epics' context
# Recommends: CHANGELOG entry, architecture update, version docs
```

### Example 3: Periodic Checks Only (No Event-Driven)

```yaml
# config/default_config.yaml
documentation:
  enabled: true
  auto_maintain: true
  triggers:
    epic_complete:
      enabled: false  # Disabled
    milestone_achieved:
      enabled: false  # Disabled
    periodic:
      enabled: true  # Only periodic
      interval_days: 14  # Bi-weekly
```

```python
# In main.py or orchestrator initialization
doc_mgr = DocumentationManager(state_manager, config)
doc_mgr.start_periodic_checks(project_id=1)

# System checks every 14 days, creates tasks for stale docs
```

### Example 4: Notification-Only Mode

```yaml
# Gradual rollout: Log warnings, don't create tasks yet
documentation:
  enabled: true
  auto_maintain: false  # Notification only
  triggers:
    epic_complete:
      enabled: true
```

**Result:** Logs like:
```
WARNING: Documentation maintenance recommended (trigger=epic_complete, scope=comprehensive)
but auto_maintain=false
```

---

## Best Practices

1. **Start Conservative:** Begin with `auto_maintain: false` to see notifications before tasks
2. **Mark Epics Carefully:** Only set `requires_adr=True` for significant architectural changes
3. **Customize Thresholds:** Adjust freshness thresholds to match your project cadence
4. **Use Scopes Appropriately:**
   - `lightweight`: Quick CHANGELOG updates
   - `comprehensive`: Architecture + ADRs + guides
   - `full_review`: Complete documentation audit (milestones/releases)
5. **Monitor Task Load:** If too many tasks, increase periodic interval or disable it
6. **Archive Regularly:** Keep `archive.enabled: true` to maintain clean docs/development/

---

## See Also

- **ADR-015:** Architecture decision record for this system
- **Architecture Docs:** `docs/architecture/ARCHITECTURE.md` - System architecture
- **Configuration Reference:** `config/default_config.yaml` - Full config with comments
- **Developer Guide:** `docs/development/` - Implementation details

---

**Questions or Issues?**
See [CONTRIBUTING.md](../../CONTRIBUTING.md) or open an issue on GitHub.
