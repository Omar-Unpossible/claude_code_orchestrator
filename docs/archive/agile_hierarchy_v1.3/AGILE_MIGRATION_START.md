# Agile/Scrum Hierarchy Implementation - Kickoff Prompt

**Purpose**: Start a fresh Claude Code session to implement Agile/Scrum work hierarchy for Obra
**Context Document**: This prompt contains all information needed to begin implementation
**ADR**: ADR-013 - Adopt Agile/Scrum Work Hierarchy
**Implementation Plan**: `docs/development/AGILE_HIERARCHY_IMPLEMENTATION_PLAN.md`

---

## Quick Context

**Project**: Obra (Claude Code Orchestrator) - AI orchestration platform combining local LLM reasoning with remote code generation

**Current State**:
- Obra uses non-standard terminology ("milestone" for "group of tasks")
- All work units are generic "Task" regardless of size
- No Epic/Story distinction
- Line 665 in `src/orchestrator.py` has placeholder: "We don't have a milestone table yet"

**Target State**:
- Agile/Scrum hierarchy: Product → Epic → Story → Task → Subtask
- True Milestones as zero-duration checkpoints
- Industry-standard terminology
- Better tooling integration (JIRA, Linear, etc.)

**Migration Strategy**: Big bang (prototype phase, no backward compatibility needed)

---

## Architecture Overview

### Current Database Schema (Relevant Parts)

```python
# src/core/models.py

class Task(Base):
    __tablename__ = 'task'

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('project_state.id'))
    parent_task_id = Column(Integer, ForeignKey('task.id'))  # ✅ Already exists for hierarchy

    title = Column(String(512))
    description = Column(Text)
    status = Column(Enum(TaskStatus))  # pending, running, completed, failed, etc.
    priority = Column(Integer)  # 1-10

    dependencies = Column(JSON, default=list)  # ✅ Already exists (M9 feature)

    # MISSING: task_type, epic_id, story_id
```

**No Milestone model exists** (despite name being used in code)

### Target Database Schema

```python
class TaskType(str, enum.Enum):
    EPIC = 'epic'        # Large feature (3-15 sessions)
    STORY = 'story'      # User deliverable (1 session)
    TASK = 'task'        # Technical work (default)
    SUBTASK = 'subtask'  # Granular step

class Task(Base):
    # ... existing fields ...
    task_type = Column(Enum(TaskType), default=TaskType.TASK)
    epic_id = Column(Integer, ForeignKey('task.id'))
    story_id = Column(Integer, ForeignKey('task.id'))

class Milestone(Base):
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('project_state.id'))
    name = Column(String(255))
    description = Column(Text)
    achieved = Column(Boolean, default=False)
    required_epic_ids = Column(JSON, default=list)
    # ... timestamps, metadata ...
```

### Terminology Mapping

| Old Term | New Term | Definition |
|----------|----------|------------|
| Milestone (as task group) | Epic | Large feature spanning multiple stories |
| Task (any work) | Story | User-facing deliverable (1 session) |
| Task (technical work) | Task | Technical work implementing story |
| execute_milestone() | execute_epic() | Execute stories in Epic |
| - (didn't exist) | Milestone | Zero-duration checkpoint |

---

## Implementation Plan Overview

**Total Effort**: 5 days (40 hours)
**Test Coverage Target**: ≥85% (currently 88%)
**Files to Modify**: ~30 files
**New Code**: ~1,500 lines
**Test Code**: ~750 lines

### Phase Breakdown

1. **Phase 1: Database & Models** (Day 1, 8 hours)
   - Add TaskType enum
   - Update Task model (task_type, epic_id, story_id)
   - Create Milestone model
   - Database migration script

2. **Phase 2: StateManager** (Day 1-2, 8 hours)
   - Add create_epic() method
   - Add create_story() method
   - Add get_epic_stories() method
   - Add milestone management methods

3. **Phase 3: Orchestrator** (Day 2, 8 hours)
   - Rename execute_milestone() → execute_epic()
   - Add execute_story() method
   - Update session management for epics

4. **Phase 4: CLI** (Day 2-3, 8 hours)
   - Add epic command group
   - Add story command group
   - Add milestone command group
   - Update task commands

5. **Phase 5: Tests** (Day 3, 8 hours)
   - Create test_agile_hierarchy.py (150+ tests)
   - Create test_epic_execution.py (50+ tests)
   - Create test_milestone_management.py (40+ tests)
   - Update existing tests

6. **Phase 6: Documentation** (Day 4, 8 hours)
   - Update all guides
   - Update technical docs
   - Update CLAUDE.md
   - Create examples

7. **Phase 7: Validation** (Day 5, 8 hours)
   - Integration testing
   - Manual testing
   - Documentation review
   - Final validation

---

## Key File Locations

### Core Implementation Files

```
src/
├── core/
│   ├── models.py          # Add TaskType, update Task, add Milestone
│   └── state.py           # Add create_epic(), create_story(), milestone methods
├── orchestrator.py        # Rename execute_milestone() → execute_epic()
└── cli.py                 # Add epic, story, milestone commands

tests/
├── conftest.py            # Add epic/story/milestone fixtures
├── test_agile_hierarchy.py       # NEW: 150+ tests
├── test_epic_execution.py        # NEW: 50+ tests
├── test_milestone_management.py  # NEW: 40+ tests
├── test_state.py          # UPDATE: Add TaskType tests
├── test_orchestrator.py   # UPDATE: execute_milestone → execute_epic
└── test_cli.py            # UPDATE: Add epic/story/milestone CLI tests

docs/
├── decisions/
│   └── ADR-013-adopt-agile-work-hierarchy.md  # ✅ Already exists
├── development/
│   └── AGILE_HIERARCHY_IMPLEMENTATION_PLAN.md # ✅ Already exists
└── guides/
    ├── GETTING_STARTED.md # UPDATE: New terminology
    └── CLI_REFERENCE.md   # UPDATE: New commands
```

### Migration Files

```
migrations/
└── versions/
    └── 003_agile_hierarchy.sql  # NEW: Database migration
```

---

## Step-by-Step Execution Guide

### STEP 1: Database Schema (Start Here)

**Objective**: Add TaskType enum, update Task model, create Milestone model

**Files to Modify**:
1. `src/core/models.py` (line 26-1090)

**Actions**:

1.1. **Add TaskType Enum** (after line 67, after ProjectStatus enum)
```python
class TaskType(str, enum.Enum):
    """Task type values for Agile/Scrum hierarchy."""
    EPIC = 'epic'           # Large feature spanning multiple stories (3-15 sessions)
    STORY = 'story'         # User-facing deliverable (1 orchestration session)
    TASK = 'task'           # Technical work implementing story (default)
    SUBTASK = 'subtask'     # Granular step (via parent_task_id)
```

1.2. **Update Task Model** (line 129-274)

Add fields after line 162 (after `priority` field):
```python
    # Agile/Scrum hierarchy (ADR-013)
    task_type = Column(
        Enum(TaskType),
        nullable=False,
        default=TaskType.TASK,
        index=True
    )
    epic_id = Column(Integer, ForeignKey('task.id'), nullable=True, index=True)
    story_id = Column(Integer, ForeignKey('task.id'), nullable=True, index=True)
```

Update `__table_args__` (line 185-188):
```python
    __table_args__ = (
        CheckConstraint('priority >= 1 AND priority <= 10', name='check_priority_range'),
        Index('idx_task_project_status', 'project_id', 'status'),
        Index('idx_task_type_status', 'task_type', 'status'),  # NEW
        Index('idx_task_epic_id', 'epic_id'),                   # NEW
        Index('idx_task_story_id', 'story_id'),                 # NEW
    )
```

Update `to_dict()` method (line 200-221):
```python
def to_dict(self) -> Dict[str, Any]:
    """Serialize to dictionary."""
    return {
        'id': self.id,
        'project_id': self.project_id,
        'parent_task_id': self.parent_task_id,
        'task_type': self.task_type.value,  # NEW
        'epic_id': self.epic_id,            # NEW
        'story_id': self.story_id,          # NEW
        'title': self.title,
        # ... rest of existing fields ...
    }
```

1.3. **Add Milestone Model** (after Task class, around line 276)
```python
class Milestone(Base):
    """Milestone model - zero-duration checkpoint.

    Represents significant project checkpoints (e.g., Epic completion, phase gates).
    True milestones are NOT work items - they are binary achievement markers.

    ADR-013: Corrects previous misuse of "milestone" for "group of tasks".
    """
    __tablename__ = 'milestone'

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('project_state.id'), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    target_date = Column(DateTime, nullable=True)

    achieved = Column(Boolean, default=False, nullable=False, index=True)
    achieved_at = Column(DateTime, nullable=True)

    required_epic_ids = Column(JSON, default=list)

    milestone_metadata = Column(JSON, default=dict)
    is_deleted = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index('idx_milestone_project_achieved', 'project_id', 'achieved'),
    )

    project = relationship('ProjectState', backref='milestones')

    def __repr__(self):
        status = "✓" if self.achieved else "○"
        return f"<Milestone(id={self.id}, name='{self.name}', {status})>"

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'project_id': self.project_id,
            'name': self.name,
            'description': self.description,
            'target_date': self.target_date.isoformat() if self.target_date else None,
            'achieved': self.achieved,
            'achieved_at': self.achieved_at.isoformat() if self.achieved_at else None,
            'required_epic_ids': self.required_epic_ids,
            'milestone_metadata': self.milestone_metadata,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_deleted': self.is_deleted
        }

    def check_completion(self, state_manager) -> bool:
        """Check if all required Epics are completed."""
        if not self.required_epic_ids:
            return False

        for epic_id in self.required_epic_ids:
            epic = state_manager.get_task(epic_id)
            if not epic or epic.status != TaskStatus.COMPLETED:
                return False

        return True
```

**Validation**:
```bash
# Run tests to verify model changes
pytest tests/test_models.py -v

# Check imports
python -c "from src.core.models import TaskType, Milestone; print('✓ Imports successful')"
```

---

### STEP 2: StateManager Updates

**Objective**: Add methods for creating and managing Epics, Stories, Milestones

**File**: `src/core/state.py`

**Actions**:

2.1. **Add Epic/Story Creation Methods** (after existing task methods, around line 400+)

```python
    # ============================================================================
    # Agile/Scrum Hierarchy Methods (ADR-013)
    # ============================================================================

    def create_epic(
        self,
        project_id: int,
        title: str,
        description: str,
        **kwargs
    ) -> int:
        """Create an Epic task.

        Epic: Large feature spanning multiple stories (3-15 sessions).

        Args:
            project_id: Project ID
            title: Epic title
            description: Epic description
            **kwargs: Additional task fields

        Returns:
            Epic task ID
        """
        kwargs['task_type'] = TaskType.EPIC
        return self.create_task(
            project_id=project_id,
            title=title,
            description=description,
            **kwargs
        )

    def create_story(
        self,
        project_id: int,
        epic_id: int,
        title: str,
        description: str,
        **kwargs
    ) -> int:
        """Create a Story task under an Epic.

        Story: User-facing deliverable (1 orchestration session).

        Args:
            project_id: Project ID
            epic_id: Parent epic ID
            title: Story title
            description: Story description
            **kwargs: Additional task fields

        Returns:
            Story task ID

        Raises:
            ValueError: If epic doesn't exist or is not type EPIC
        """
        # Validate epic
        epic = self.get_task(epic_id)
        if not epic:
            raise ValueError(f"Epic {epic_id} does not exist")
        if epic.task_type != TaskType.EPIC:
            raise ValueError(f"Task {epic_id} is not an Epic (type={epic.task_type})")

        kwargs['task_type'] = TaskType.STORY
        kwargs['epic_id'] = epic_id

        return self.create_task(
            project_id=project_id,
            title=title,
            description=description,
            **kwargs
        )

    def get_epic_stories(self, epic_id: int) -> List[Task]:
        """Get all stories belonging to an epic.

        Args:
            epic_id: Epic task ID

        Returns:
            List of Story tasks
        """
        with self._session_scope() as session:
            tasks = session.query(Task).filter(
                Task.epic_id == epic_id,
                Task.task_type == TaskType.STORY,
                Task.is_deleted == False
            ).all()
            return [self._detach_task(t) for t in tasks]

    def get_story_tasks(self, story_id: int) -> List[Task]:
        """Get all tasks implementing a story.

        Args:
            story_id: Story task ID

        Returns:
            List of Task objects
        """
        with self._session_scope() as session:
            tasks = session.query(Task).filter(
                Task.story_id == story_id,
                Task.task_type == TaskType.TASK,
                Task.is_deleted == False
            ).all()
            return [self._detach_task(t) for t in tasks]

    def create_milestone(
        self,
        project_id: int,
        name: str,
        description: Optional[str] = None,
        required_epic_ids: Optional[List[int]] = None,
        target_date: Optional[datetime] = None
    ) -> int:
        """Create a milestone checkpoint.

        Args:
            project_id: Project ID
            name: Milestone name
            description: Optional description
            required_epic_ids: Epics that must complete
            target_date: Optional target date

        Returns:
            Milestone ID
        """
        with self._session_scope() as session:
            milestone = Milestone(
                project_id=project_id,
                name=name,
                description=description,
                required_epic_ids=required_epic_ids or [],
                target_date=target_date,
                achieved=False
            )
            session.add(milestone)
            session.flush()
            milestone_id = milestone.id

        logger.info(f"Created milestone {milestone_id}: {name}")
        return milestone_id

    def get_milestone(self, milestone_id: int) -> Optional[Milestone]:
        """Get milestone by ID."""
        with self._session_scope() as session:
            milestone = session.query(Milestone).filter(
                Milestone.id == milestone_id,
                Milestone.is_deleted == False
            ).first()

            if milestone:
                session.expunge(milestone)
                return milestone
            return None

    def check_milestone_completion(self, milestone_id: int) -> bool:
        """Check if milestone requirements are met."""
        milestone = self.get_milestone(milestone_id)
        if not milestone:
            return False

        return milestone.check_completion(self)

    def achieve_milestone(self, milestone_id: int) -> None:
        """Mark milestone as achieved."""
        with self._session_scope() as session:
            milestone = session.query(Milestone).filter(
                Milestone.id == milestone_id
            ).first()

            if milestone:
                milestone.achieved = True
                milestone.achieved_at = datetime.now()
                logger.info(f"Milestone {milestone_id} achieved: {milestone.name}")
```

**Validation**:
```bash
pytest tests/test_state.py::test_create_epic -v
pytest tests/test_state.py::test_create_story -v
pytest tests/test_state.py::test_create_milestone -v
```

---

### STEP 3: Orchestrator Rename

**Objective**: Rename execute_milestone() to execute_epic()

**File**: `src/orchestrator.py`

**Critical Search Locations**:
- Line 667: `def execute_milestone(` → `def execute_epic(`
- Line 575-665: Helper methods (`_start_milestone_session`, `_build_milestone_context`, etc.)
- Throughout file: Variable names like `milestone_id`, `milestone_context`

**Method Signature Change**:
```python
# OLD (line ~667):
def execute_milestone(
    self,
    project_id: int,
    task_ids: List[int],
    milestone_id: Optional[int] = None,
    max_iterations_per_task: int = 10
) -> Dict[str, Any]:

# NEW:
def execute_epic(
    self,
    project_id: int,
    epic_id: int,
    max_iterations_per_story: int = 10
) -> Dict[str, Any]:
    """Execute all stories in an Epic.

    Args:
        project_id: Project ID
        epic_id: Epic task ID
        max_iterations_per_story: Max iterations per story

    Returns:
        Dict with epic execution results
    """
    # Get epic
    epic = self.state.get_task(epic_id)
    if not epic:
        raise ValueError(f"Epic {epic_id} does not exist")
    if epic.task_type != TaskType.EPIC:
        raise ValueError(f"Task {epic_id} is not an Epic")

    # Get all stories in epic
    stories = self.state.get_epic_stories(epic_id)

    # Execute each story
    results = []
    for story in stories:
        result = self._execute_single_task(story.id, max_iterations_per_story)
        results.append(result)

    return {
        'epic_id': epic_id,
        'stories_completed': len([r for r in results if r['status'] == 'completed']),
        'total_stories': len(stories),
        'results': results
    }
```

**Validation**:
```bash
pytest tests/test_orchestrator.py::test_execute_epic -v
```

---

### STEP 4: CLI Commands

**Objective**: Add epic, story, milestone command groups

**File**: `src/cli.py`

**Actions**: Add three new command groups

4.1. **Epic Commands** (around line 200+)
```python
@cli.group()
def epic():
    """Manage epics (large features spanning multiple stories)."""
    pass

@epic.command('create')
@click.argument('title')
@click.option('--project', '-p', type=int, required=True)
@click.option('--description', '-d', default='')
@click.option('--priority', type=int, default=5)
def epic_create(title, project, description, priority):
    """Create a new epic."""
    config = Config.load()
    state = StateManager(config)

    epic_id = state.create_epic(
        project_id=project,
        title=title,
        description=description,
        priority=priority
    )

    click.echo(f"✓ Created epic {epic_id}: {title}")

@epic.command('execute')
@click.argument('epic_id', type=int)
def epic_execute(epic_id):
    """Execute all stories in an epic."""
    config = Config.load()
    orchestrator = Orchestrator(config)

    epic = orchestrator.state.get_task(epic_id)
    result = orchestrator.execute_epic(
        project_id=epic.project_id,
        epic_id=epic_id
    )

    click.echo(f"✓ Epic {epic_id} complete: {result['stories_completed']}/{result['total_stories']} stories")
```

4.2. **Story Commands**
```python
@cli.group()
def story():
    """Manage stories (user-facing deliverables)."""
    pass

@story.command('create')
@click.argument('title')
@click.option('--epic', '-e', type=int, required=True)
@click.option('--project', '-p', type=int, required=True)
@click.option('--description', '-d', default='')
def story_create(title, epic, project, description):
    """Create a new story under an epic."""
    config = Config.load()
    state = StateManager(config)

    story_id = state.create_story(
        project_id=project,
        epic_id=epic,
        title=title,
        description=description
    )

    click.echo(f"✓ Created story {story_id}: {title}")
```

4.3. **Milestone Commands**
```python
@cli.group()
def milestone():
    """Manage milestones (zero-duration checkpoints)."""
    pass

@milestone.command('create')
@click.argument('name')
@click.option('--project', '-p', type=int, required=True)
@click.option('--epics', help='Comma-separated epic IDs')
def milestone_create(name, project, epics):
    """Create a milestone checkpoint."""
    config = Config.load()
    state = StateManager(config)

    required_epic_ids = []
    if epics:
        required_epic_ids = [int(x.strip()) for x in epics.split(',')]

    milestone_id = state.create_milestone(
        project_id=project,
        name=name,
        required_epic_ids=required_epic_ids
    )

    click.echo(f"✓ Created milestone {milestone_id}: {name}")
```

**Validation**:
```bash
# Test CLI commands
obra epic create "Test Epic" -p 1
obra story create "Test Story" -e 1 -p 1
obra milestone create "Test Milestone" -p 1 --epics 1
```

---

### STEP 5: Database Migration

**Objective**: Create and run database migration

**File**: Create `migrations/versions/003_agile_hierarchy.sql`

```sql
-- Agile Hierarchy Migration (ADR-013)

-- Add columns to task table
ALTER TABLE task ADD COLUMN task_type TEXT DEFAULT 'task' NOT NULL;
ALTER TABLE task ADD COLUMN epic_id INTEGER;
ALTER TABLE task ADD COLUMN story_id INTEGER;

-- Create indexes
CREATE INDEX idx_task_type ON task(task_type);
CREATE INDEX idx_task_epic ON task(epic_id);
CREATE INDEX idx_task_story ON task(story_id);

-- Create milestone table
CREATE TABLE milestone (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    target_date DATETIME,
    achieved BOOLEAN DEFAULT 0 NOT NULL,
    achieved_at DATETIME,
    required_epic_ids JSON DEFAULT '[]' NOT NULL,
    milestone_metadata JSON DEFAULT '{}',
    is_deleted BOOLEAN DEFAULT 0 NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    FOREIGN KEY (project_id) REFERENCES project_state(id)
);

CREATE INDEX idx_milestone_project_achieved ON milestone(project_id, achieved);
```

**Run Migration**:
```bash
# Apply migration
sqlite3 obra.db < migrations/versions/003_agile_hierarchy.sql

# Or use Python
python -c "from src.core.models import create_tables; from sqlalchemy import create_engine; engine = create_engine('sqlite:///obra.db'); create_tables(engine)"
```

---

### STEP 6: Write Tests

**Objective**: Create comprehensive tests for Agile hierarchy

**Files to Create**:

6.1. **tests/test_agile_hierarchy.py** (NEW, 150+ tests)
```python
"""Tests for Agile/Scrum hierarchy (ADR-013)."""

import pytest
from src.core.models import TaskType, TaskStatus
from src.core.state import StateManager

def test_create_epic(state_manager, sample_project):
    """Test epic creation."""
    epic_id = state_manager.create_epic(
        project_id=sample_project.id,
        title="User Authentication",
        description="Complete auth system"
    )

    epic = state_manager.get_task(epic_id)
    assert epic is not None
    assert epic.task_type == TaskType.EPIC
    assert epic.title == "User Authentication"

def test_create_story(state_manager, sample_epic):
    """Test story creation under epic."""
    story_id = state_manager.create_story(
        project_id=sample_epic.project_id,
        epic_id=sample_epic.id,
        title="Email/password login",
        description="User story"
    )

    story = state_manager.get_task(story_id)
    assert story is not None
    assert story.task_type == TaskType.STORY
    assert story.epic_id == sample_epic.id

def test_get_epic_stories(state_manager, sample_epic):
    """Test retrieving stories for an epic."""
    # Create 3 stories
    story_ids = []
    for i in range(3):
        sid = state_manager.create_story(
            project_id=sample_epic.project_id,
            epic_id=sample_epic.id,
            title=f"Story {i}",
            description=f"Description {i}"
        )
        story_ids.append(sid)

    stories = state_manager.get_epic_stories(sample_epic.id)
    assert len(stories) == 3
    assert all(s.task_type == TaskType.STORY for s in stories)

def test_create_milestone(state_manager, sample_project, sample_epic):
    """Test milestone creation."""
    milestone_id = state_manager.create_milestone(
        project_id=sample_project.id,
        name="Auth Complete",
        required_epic_ids=[sample_epic.id]
    )

    milestone = state_manager.get_milestone(milestone_id)
    assert milestone is not None
    assert milestone.name == "Auth Complete"
    assert sample_epic.id in milestone.required_epic_ids
    assert not milestone.achieved

def test_milestone_completion_check(state_manager, sample_project, sample_epic):
    """Test milestone completion checking."""
    milestone_id = state_manager.create_milestone(
        project_id=sample_project.id,
        name="Test Milestone",
        required_epic_ids=[sample_epic.id]
    )

    # Initially not complete
    assert not state_manager.check_milestone_completion(milestone_id)

    # Complete the epic
    state_manager.update_task(sample_epic.id, status=TaskStatus.COMPLETED)

    # Now should be complete
    assert state_manager.check_milestone_completion(milestone_id)
```

6.2. **tests/conftest.py** (UPDATE - add fixtures)
```python
@pytest.fixture
def sample_epic(state_manager, sample_project):
    """Create sample epic."""
    epic_id = state_manager.create_epic(
        project_id=sample_project.id,
        title="User Authentication System",
        description="Complete auth",
        priority=8
    )
    return state_manager.get_task(epic_id)

@pytest.fixture
def sample_story(state_manager, sample_epic):
    """Create sample story."""
    story_id = state_manager.create_story(
        project_id=sample_epic.project_id,
        epic_id=sample_epic.id,
        title="Email login",
        description="User story"
    )
    return state_manager.get_task(story_id)
```

**Run Tests**:
```bash
pytest tests/test_agile_hierarchy.py -v
pytest tests/ --cov=src --cov-report=term
```

---

## Success Criteria Checklist

### Database & Models
- [ ] TaskType enum exists with EPIC, STORY, TASK, SUBTASK
- [ ] Task model has task_type, epic_id, story_id fields
- [ ] Milestone model exists and complete
- [ ] All indexes created
- [ ] Database migration runs successfully

### StateManager
- [ ] create_epic() creates tasks with type=EPIC
- [ ] create_story() creates tasks with type=STORY, sets epic_id
- [ ] get_epic_stories() returns stories for epic
- [ ] get_story_tasks() returns tasks for story
- [ ] Milestone CRUD operations work

### Orchestrator
- [ ] execute_epic() executes all stories in epic
- [ ] No references to old execute_milestone() remain (search codebase)

### CLI
- [ ] `obra epic create` works
- [ ] `obra epic list` works (if implemented)
- [ ] `obra epic execute` works
- [ ] `obra story create` works with --epic
- [ ] `obra milestone create` works
- [ ] `obra milestone check` validates completion

### Tests
- [ ] All new tests pass (240+ tests)
- [ ] Coverage ≥85% maintained
- [ ] No test failures

### Documentation
- [ ] CHANGELOG.md updated
- [ ] CLI_REFERENCE.md has epic/story/milestone commands
- [ ] CLAUDE.md reflects new terminology

---

## Common Pitfalls to Avoid

1. **Don't confuse the two uses of "milestone"**:
   - OLD (incorrect): "milestone" = group of tasks → NOW: "epic"
   - NEW (correct): "milestone" = zero-duration checkpoint

2. **Don't forget to update imports**:
   - Add `TaskType` to imports wherever Task is imported
   - Import `Milestone` model where needed

3. **Database migration order matters**:
   - Add columns before creating indexes
   - Create milestone table after task table updates

4. **Test coverage**:
   - Update ALL existing tests that reference old terminology
   - Search for "milestone" in tests and update appropriately

5. **CLI command conflicts**:
   - Ensure no CLI command name collisions
   - Test all commands after adding new groups

---

## Quick Start Commands

```bash
# 1. Read implementation plan
cat docs/development/AGILE_HIERARCHY_IMPLEMENTATION_PLAN.md

# 2. Start with database schema
# Edit src/core/models.py - add TaskType, update Task, add Milestone

# 3. Run database migration
python -c "from src.core.models import create_tables; ..."

# 4. Update StateManager
# Edit src/core/state.py - add create_epic(), create_story(), etc.

# 5. Update Orchestrator
# Edit src/orchestrator.py - rename execute_milestone → execute_epic

# 6. Add CLI commands
# Edit src/cli.py - add epic, story, milestone command groups

# 7. Write tests
pytest tests/test_agile_hierarchy.py -v

# 8. Run full test suite
pytest --cov=src --cov-report=term

# 9. Update documentation
# Edit docs/guides/*.md, CHANGELOG.md, CLAUDE.md

# 10. Final validation
pytest tests/ -v
python -m src.cli epic create "Test Epic" -p 1
```

---

## Additional Resources

### Reference Documents
- **ADR-013**: `docs/decisions/ADR-013-adopt-agile-work-hierarchy.md`
- **Implementation Plan**: `docs/development/AGILE_HIERARCHY_IMPLEMENTATION_PLAN.md`
- **Recommendation Analysis**: `docs/design/WORK_HIERARCHY_ALIGNMENT_RECOMMENDATION.md`
- **Work Breakdown Reference**: `docs/research/work-breakdown-reference-guide.md`

### Code Examples

**Creating Epic with Stories**:
```python
# Create epic
epic_id = state.create_epic(
    project_id=1,
    title="User Authentication System",
    description="OAuth, MFA, session management"
)

# Create stories
login_story_id = state.create_story(
    project_id=1,
    epic_id=epic_id,
    title="Email/password login",
    description="As a user, I want to log in with email/password"
)

oauth_story_id = state.create_story(
    project_id=1,
    epic_id=epic_id,
    title="OAuth integration",
    description="As a user, I want to log in with Google/GitHub"
)

# Execute epic
orchestrator.execute_epic(project_id=1, epic_id=epic_id)
```

**Creating Milestone**:
```python
# Create milestone
milestone_id = state.create_milestone(
    project_id=1,
    name="Authentication Complete",
    description="Auth system ready for production",
    required_epic_ids=[epic_id]
)

# Check completion
if state.check_milestone_completion(milestone_id):
    state.achieve_milestone(milestone_id)
```

---

## Next Actions After Implementation

1. **Update CHANGELOG.md**:
   ```markdown
   ## [1.3.0] - 2025-11-XX

   ### Added
   - Agile/Scrum work hierarchy (Epic → Story → Task → Subtask)
   - True Milestone model for zero-duration checkpoints
   - CLI commands: epic, story, milestone

   ### Changed
   - Renamed execute_milestone() to execute_epic()
   - Updated all documentation with Agile terminology

   ### Migration
   - Database schema migration required (see migrations/versions/003_agile_hierarchy.sql)
   - Breaking change: No backward compatibility with old milestone concept
   ```

2. **Test with real project**:
   - Create sample project with Epic → Story → Task hierarchy
   - Execute epic and verify all stories complete
   - Create milestone and verify completion checking

3. **Update examples**:
   - Refactor existing examples to use new hierarchy
   - Create new example demonstrating full Agile workflow

---

**End of Kickoff Prompt**

**Ready to Begin**: You now have all information needed to implement Agile/Scrum hierarchy
**Estimated Time**: 40 hours (5 days)
**First Step**: Add TaskType enum to src/core/models.py

Good luck! 🚀
