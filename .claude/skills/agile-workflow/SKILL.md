# agile-workflow

**Description**: Epic, Story, Milestone management commands for Agile/Scrum workflows including creation (epic create, story create, milestone create), listing, execution, and completion tracking. Supports hierarchical task organization.

**Triggers**: epic, story, milestone, agile, scrum, task hierarchy, backlog, sprint

**Token Cost**: ~200 tokens when loaded

**Dependencies**: Obra CLI, StateManager

---

## Agile Workflow Commands

### Epic Management (Large Features)

```bash
# Create epic (3-15 sessions, large feature)
python -m src.cli epic create "User Authentication System" --project 1

# List epics
python -m src.cli epic list --project 1

# Execute epic
python -m src.cli epic execute 1
```

### Story Management (User Deliverables)

```bash
# Create story (1 session, user deliverable)
python -m src.cli story create "Email/password login" --epic 1 --project 1

# List stories in an epic
python -m src.cli story list --epic 1
```

### Milestone Tracking

```bash
# Create milestone (achievement marker)
python -m src.cli milestone create "Auth Complete" --project 1

# Check milestone progress
python -m src.cli milestone check 1

# Mark milestone as achieved
python -m src.cli milestone achieve 1
```

## Task Hierarchy

```
Product (Project)
  ↓ Epic (3-15 sessions, large feature)
    ↓ Story (1 session, user deliverable)
      ↓ Task (technical work, default)
        ↓ Subtask (via parent_task_id)

Milestone → Checkpoint (achievement marker)
```

See: `CLAUDE.md` for complete task hierarchy details (ADR-013)
