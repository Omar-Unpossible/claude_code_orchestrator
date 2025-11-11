# Agile Workflow Guide

**Version**: 1.3.0
**Last Updated**: November 6, 2025
**Status**: Production-Ready

This guide demonstrates how to use Obra's Agile/Scrum hierarchy for organizing and executing software development projects at scale.

## Table of Contents

1. [Overview](#overview)
2. [Work Item Hierarchy](#work-item-hierarchy)
3. [Basic Workflows](#basic-workflows)
4. [Advanced Patterns](#advanced-patterns)
5. [CLI Command Reference](#cli-command-reference)
6. [Best Practices](#best-practices)
7. [Troubleshooting](#troubleshooting)

---

## Overview

Obra implements industry-standard Agile/Scrum terminology to organize work hierarchically:

```
Product (Project)
  ↓
Epic (Large feature, 3-15 sessions)
  ↓
Story (User deliverable, 1 session)
  ↓
Task (Technical work)
  ↓
Subtask (Granular steps)

Milestone → Checkpoint (zero-duration, marks completion)
```

### Key Benefits

- **Scalability**: Organize hundreds of tasks into logical features
- **Clarity**: Industry-standard terms everyone understands
- **Tracking**: Milestone-based progress monitoring
- **Flexibility**: Works with existing task dependencies (M9)
- **Compatibility**: Existing tasks still work (default to `TaskType.TASK`)

### When to Use Each Level

| Work Item | Size | Duration | Use When |
|-----------|------|----------|----------|
| **Epic** | Large feature | 3-15 sessions | Building major functionality (auth system, API, UI redesign) |
| **Story** | User deliverable | 1 session | Single user-facing feature (login form, API endpoint) |
| **Task** | Technical work | < 1 session | Implementation details (write tests, update schema) |
| **Subtask** | Granular step | Minutes | Breaking down complex tasks |
| **Milestone** | Checkpoint | Zero-duration | Release markers, sprint goals |

---

## Work Item Hierarchy

### Epic

**Definition**: Large feature spanning multiple user stories (typically 3-15 orchestration sessions).

**Example**: "User Authentication System" containing:
- Email/password login
- OAuth integration (Google, GitHub)
- Multi-factor authentication
- Session management

**Python API**:
```python
epic_id = state_manager.create_epic(
    project_id=1,
    title="User Authentication System",
    description="Complete auth with OAuth, MFA, session management",
    priority=9  # High priority
)
```

**CLI**:
```bash
obra epic create "User Authentication System" \
  --project 1 \
  --description "Complete auth with OAuth, MFA, session management" \
  --priority 9
```

### Story

**Definition**: Single user-facing deliverable completable in one orchestration session.

**Format**: "As a [user type], I want [goal] so that [benefit]"

**Example**: "As a user, I want to log in with my Google account so that I don't need to create a new password"

**Python API**:
```python
story_id = state_manager.create_story(
    project_id=1,
    epic_id=epic_id,
    title="OAuth integration",
    description="As a user, I want to log in with Google/GitHub",
    priority=8
)
```

**CLI**:
```bash
obra story create "OAuth integration" \
  --epic 1 \
  --project 1 \
  --description "As a user, I want to log in with Google/GitHub" \
  --priority 8
```

### Task

**Definition**: Technical work implementing a story (default work item type).

**Python API**:
```python
# Tasks created with create_task default to TaskType.TASK
task_data = {
    'title': 'Implement OAuth callback handler',
    'description': 'Handle OAuth redirect and token exchange',
    'story_id': story_id,  # Link to parent story
    'priority': 7
}
task = state_manager.create_task(project_id=1, task_data=task_data)
```

**CLI**:
```bash
obra task create "Implement OAuth callback handler" \
  --project 1 \
  --description "Handle OAuth redirect and token exchange"
```

### Subtask

**Definition**: Granular step within a task (via `parent_task_id` hierarchy).

**Python API**:
```python
subtask_data = {
    'title': 'Validate OAuth state parameter',
    'description': 'CSRF protection',
    'parent_task_id': task.id,
    'task_type': TaskType.SUBTASK
}
subtask = state_manager.create_task(project_id=1, task_data=subtask_data)
```

### Milestone

**Definition**: Zero-duration checkpoint marking completion of one or more epics.

**Example**: "MVP Release" achieved when Auth, Product Catalog, and Checkout epics complete.

**Python API**:
```python
milestone_id = state_manager.create_milestone(
    project_id=1,
    name="MVP Release",
    description="Core features ready for beta testing",
    required_epic_ids=[auth_epic_id, catalog_epic_id, checkout_epic_id]
)

# Check if milestone requirements met
if state_manager.check_milestone_completion(milestone_id):
    state_manager.achieve_milestone(milestone_id)
```

**CLI**:
```bash
obra milestone create "MVP Release" \
  --project 1 \
  --description "Core features ready for beta testing" \
  --epics 1,2,3

obra milestone check 1  # Check if complete
obra milestone achieve 1  # Mark as achieved
```

---

## Basic Workflows

### Workflow 1: Create and Execute an Epic

**Scenario**: Building a complete user authentication system.

```bash
# Step 1: Create project (if needed)
obra project create "E-Commerce Platform" \
  --description "Online shopping platform" \
  --working-dir /path/to/project

# Step 2: Create epic
obra epic create "User Authentication" \
  --project 1 \
  --description "Complete auth system with OAuth, MFA, session management" \
  --priority 9

# Step 3: Break down into stories
obra story create "Email/password login" \
  --epic 1 \
  --project 1 \
  --description "As a user, I want to log in with email/password"

obra story create "OAuth integration" \
  --epic 1 \
  --project 1 \
  --description "As a user, I want to log in with Google/GitHub"

obra story create "Multi-factor authentication" \
  --epic 1 \
  --project 1 \
  --description "As a user, I want 2FA for security"

# Step 4: Execute entire epic (runs all stories)
obra epic execute 1

# Output:
# Executing epic #1: User Authentication
# Executing story #2 in epic 1...
# Executing story #3 in epic 1...
# Executing story #4 in epic 1...
# ✓ Epic execution complete:
#   Stories completed: 3/3
#   Stories failed: 0
```

### Workflow 2: Track Progress with Milestones

**Scenario**: Planning a sprint with multiple epics.

```bash
# Create epics for sprint
obra epic create "User Authentication" --project 1 --priority 9
obra epic create "Product Catalog" --project 1 --priority 8
obra epic create "Shopping Cart" --project 1 --priority 7

# Create sprint milestone
obra milestone create "Sprint 1 Complete" \
  --project 1 \
  --epics 1,2,3 \
  --description "Auth, catalog, and cart features complete"

# Execute epics
obra epic execute 1
obra epic execute 2
obra epic execute 3

# Check milestone progress
obra milestone check 1

# When all epics complete, achieve milestone
obra milestone achieve 1
```

### Workflow 3: Query and Monitor

```bash
# List all epics in project
obra epic list --project 1

# Show epic details with stories
obra epic show 1

# List stories in epic
obra story list --epic 1

# List all milestones
obra milestone list --project 1

# Show milestone progress
obra milestone show 1
```

---

## Advanced Patterns

### Pattern 1: Sprint Planning

Organize work into time-boxed sprints with milestone tracking.

```python
from src.core.state import StateManager

state = StateManager('sqlite:///orchestrator.db')

# Sprint 1: Core features
auth_epic = state.create_epic(1, "User Authentication", "Auth system")
catalog_epic = state.create_epic(1, "Product Catalog", "Browse products")

sprint_1 = state.create_milestone(
    project_id=1,
    name="Sprint 1 Complete",
    required_epic_ids=[auth_epic, catalog_epic]
)

# Sprint 2: Advanced features
cart_epic = state.create_epic(1, "Shopping Cart", "Add to cart")
checkout_epic = state.create_epic(1, "Checkout Flow", "Payment processing")

sprint_2 = state.create_milestone(
    project_id=1,
    name="Sprint 2 Complete",
    required_epic_ids=[cart_epic, checkout_epic]
)

# Execute sprints sequentially
orchestrator.execute_epic(project_id=1, epic_id=auth_epic)
orchestrator.execute_epic(project_id=1, epic_id=catalog_epic)

if state.check_milestone_completion(sprint_1):
    state.achieve_milestone(sprint_1)
    print("✓ Sprint 1 complete! Starting Sprint 2...")
```

### Pattern 2: Feature Flags

Implement features behind flags for progressive rollout.

```bash
# Create epic with feature flag context
obra epic create "New Checkout Flow" \
  --project 1 \
  --description "Redesigned checkout behind feature flag 'new_checkout'" \
  --priority 6

# Stories include flag integration
obra story create "Add feature flag toggle" \
  --epic 5 \
  --project 1 \
  --description "Implement feature flag system"

obra story create "Implement new UI (behind flag)" \
  --epic 5 \
  --project 1 \
  --description "New checkout UI, only shown when flag enabled"

obra story create "A/B testing setup" \
  --epic 5 \
  --project 1 \
  --description "Track conversion rates for both flows"
```

### Pattern 3: Parallel Epic Execution

Execute independent epics concurrently (requires manual orchestration).

```bash
# Execute multiple epics in parallel (independent work)
obra epic execute 2 &  # Product Catalog
obra epic execute 4 &  # Email Templates
obra epic execute 5 &  # Analytics Dashboard
wait

echo "All parallel epics complete!"
```

### Pattern 4: Story Dependencies

Use task dependencies (M9) for ordering within epics.

```python
# Create stories with dependencies
story1_id = state.create_story(1, epic_id, "Database schema", "Setup DB")
story2_id = state.create_story(1, epic_id, "API endpoints", "REST API")
story3_id = state.create_story(1, epic_id, "Frontend UI", "React components")

# Add dependencies (story3 depends on story2, story2 depends on story1)
state.add_task_dependency(task_id=story2_id, depends_on_id=story1_id)
state.add_task_dependency(task_id=story3_id, depends_on_id=story2_id)

# execute_epic respects dependencies
orchestrator.execute_epic(project_id=1, epic_id=epic_id)
```

### Pattern 5: Technical Debt Tracking

Create epics specifically for refactoring and tech debt.

```bash
# Create tech debt epic (lower priority)
obra epic create "Payment Service Refactor" \
  --project 1 \
  --priority 4 \
  --description "Break monolith into microservices (technical debt)"

# Stories focus on non-user-facing improvements
obra story create "Extract payment logic to service" \
  --epic 6 \
  --project 1

obra story create "Add service-to-service auth" \
  --epic 6 \
  --project 1

obra story create "Migrate existing integrations" \
  --epic 6 \
  --project 1
```

---

## CLI Command Reference

### Epic Commands

```bash
# Create
obra epic create <title> --project <id> [--description <desc>] [--priority <1-10>]

# List
obra epic list [--project <id>] [--status <pending|running|completed|failed>]

# Show details
obra epic show <epic_id>

# Execute (runs all stories)
obra epic execute <epic_id>

# Update
obra epic update <epic_id> [--title <new_title>] [--priority <1-10>]

# Delete (soft delete)
obra epic delete <epic_id>
```

### Story Commands

```bash
# Create
obra story create <title> --epic <id> --project <id> [--description <desc>] [--priority <1-10>]

# List
obra story list [--epic <id>] [--status <pending|running|completed|failed>]

# Show details
obra story show <story_id>

# Update
obra story update <story_id> [--title <new_title>] [--priority <1-10>]

# Move to different epic
obra story move <story_id> --epic <new_epic_id>
```

### Milestone Commands

```bash
# Create
obra milestone create <name> --project <id> --epics <id1,id2,id3> [--description <desc>]

# List
obra milestone list [--project <id>]

# Show details
obra milestone show <milestone_id>

# Check completion
obra milestone check <milestone_id>

# Achieve (mark complete)
obra milestone achieve <milestone_id>

# Update
obra milestone update <milestone_id> [--name <new_name>] [--epics <id1,id2>]
```

---

## Best Practices

### Epic Sizing

✅ **Good**: 3-15 stories per epic
✅ **Example**: "User Authentication" (5 stories: login, signup, OAuth, MFA, session mgmt)

❌ **Too Small**: 1-2 stories (just use story directly)
❌ **Too Large**: 20+ stories (split into multiple epics or a program)

### Story Sizing

✅ **Good**: Completable in 1 orchestration session (1-2 hours)
✅ **Format**: "As a [user], I want [goal] so that [benefit]"

❌ **Too Small**: Trivial changes (use task instead)
❌ **Too Large**: Multi-day work (split into multiple stories)

### Task Breakdown

- **Stories contain tasks** (technical implementation steps)
- **Tasks can have subtasks** (granular work)
- **Use task dependencies** for ordering (M9 feature)
- **Default type is TASK** (backward compatible)

### Milestone Planning

- **Define milestones upfront** (sprint goals, releases, MVP)
- **Link related epics** to milestones
- **Auto-achieve** when all epics complete
- **Zero-duration** checkpoints (not work items)

### Iterative Development

1. **Plan**: Define epics and stories for sprint/release
2. **Execute**: Run one epic at a time
3. **Review**: Check quality and completeness
4. **Adjust**: Refine estimates and priorities
5. **Track**: Use milestones for progress visibility

---

## Troubleshooting

### Issue: Epic Not Executing

**Symptoms**: `obra epic execute` does nothing or fails

**Solutions**:
```bash
# Check epic exists and has correct type
obra epic show <epic_id>

# Verify epic has stories
obra story list --epic <epic_id>

# Check for execution errors
obra task list --project <project_id> --status failed
```

### Issue: Milestone Not Completing

**Symptoms**: `obra milestone check` returns false despite epics being done

**Solutions**:
```bash
# Check which epics are required
obra milestone show <milestone_id>

# Verify all required epics are completed
obra epic list --project <project_id>

# Complete missing epics
obra epic execute <epic_id>
```

### Issue: Story Creation Fails

**Symptoms**: Cannot create story, validation error

**Solutions**:
```bash
# Verify epic exists
obra epic show <epic_id>

# Ensure epic is correct type (not a regular task)
# Epic must be created with 'obra epic create', not 'obra task create'

# Check project ID is valid
obra project list
```

### Issue: Cannot Move Story Between Epics

**Symptoms**: `obra story move` fails

**Solutions**:
```bash
# Verify story and new epic exist
obra story show <story_id>
obra epic show <new_epic_id>

# Use correct command syntax
obra story move <story_id> --epic <new_epic_id>
```

### Issue: Orphaned Stories After Epic Deletion

**Symptoms**: Stories still exist after deleting epic

**Note**: This is by design (soft delete doesn't cascade)

**Solutions**:
```bash
# Query orphaned stories (epic_id points to deleted epic)
obra story list --project <project_id>

# Move to different epic
obra story move <story_id> --epic <new_epic_id>

# Or delete individually
obra task delete <story_id>
```

---

## Next Steps

- **Learn More**: Read [ADR-013](../decisions/ADR-013-adopt-agile-work-hierarchy.md) for architecture rationale
- **Migrate**: See [Migration Guide v1.3](MIGRATION_GUIDE_V1.3.md) for upgrading from v1.2
- **API Reference**: Check [StateManager API](../architecture/ARCHITECTURE.md#statemanager-api) for programmatic usage
- **CLI Reference**: See [CLI Documentation](CLI_REFERENCE.md) for complete command list

---

**Questions?** Open an issue: https://github.com/Omar-Unpossible/claude_code_orchestrator/issues

**Version**: 1.3.0
**Last Updated**: November 6, 2025
**Status**: Production-Ready
