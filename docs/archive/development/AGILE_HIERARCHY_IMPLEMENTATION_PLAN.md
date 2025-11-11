# AGILE HIERARCHY IMPLEMENTATION PLAN

**Format**: Machine-Optimized for LLM Execution
**ADR**: ADR-013 - Adopt Agile/Scrum Work Hierarchy
**Date**: 2025-11-05
**Migration Type**: Big Bang (Complete Replacement)
**Estimated Effort**: 3-5 days
**Risk**: Low (prototype phase, comprehensive plan, good test coverage)

---

## EXECUTION INSTRUCTIONS FOR LLM

This document provides a complete, systematic plan for migrating Obra from non-standard work hierarchy to Agile/Scrum hierarchy.

**Execution Mode**: Sequential (complete each section before proceeding to next)
**Validation**: Run tests after each section
**Rollback**: Git commit after each major section for checkpoint

**Format Notes**:
- ✅ = Task to complete
- 📝 = Validation step
- ⚠️ = Critical requirement
- 🔍 = Search/verification step

---

## SECTION 1: DATABASE SCHEMA UPDATES

### TASK 1.1: Add TaskType Enum

**File**: `src/core/models.py`
**Location**: After line 26 (after `TaskStatus` enum)
**Action**: INSERT

```python
class TaskType(str, enum.Enum):
    """Task type in Agile hierarchy."""
    EPIC = 'epic'        # Large feature spanning multiple stories (formerly "milestone group")
    STORY = 'story'      # User-facing deliverable (1 orchestration session)
    TASK = 'task'        # Technical work implementing story (default)
    SUBTASK = 'subtask'  # Granular step (optional, via parent_task_id)
```

**Validation**:
- ✅ Enum added after TaskStatus
- ✅ Four values: EPIC, STORY, TASK, SUBTASK
- ✅ Docstrings explain each type

---

### TASK 1.2: Update Task Model Schema

**File**: `src/core/models.py`
**Location**: Task class (line 129-228)
**Action**: MODIFY

**Step 1**: Add imports at top of file
```python
# Line ~8 (in imports section)
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON, ForeignKey, Index, CheckConstraint, Enum
# ... existing imports ...
```

**Step 2**: Add new columns to Task model after line 161 (after `priority` column)

```python
    # Agile hierarchy (ADR-013)
    task_type = Column(
        Enum(TaskType),
        nullable=False,
        default=TaskType.TASK,
        index=True,
        comment='Task type in Agile hierarchy (Epic/Story/Task/Subtask)'
    )

    # Epic/Story tracking (for hierarchy navigation)
    epic_id = Column(
        Integer,
        ForeignKey('task.id'),
        nullable=True,
        index=True,
        comment='Parent Epic ID (if this is a Story or Task under Epic)'
    )
    story_id = Column(
        Integer,
        ForeignKey('task.id'),
        nullable=True,
        index=True,
        comment='Parent Story ID (if this is a Task under Story)'
    )

    # Note: parent_task_id (line 140) remains for Subtask hierarchy
```

**Step 3**: Update __table_args__ (line 185-188) to add new indexes

```python
    __table_args__ = (
        CheckConstraint('priority >= 1 AND priority <= 10', name='check_priority_range'),
        Index('idx_task_project_status', 'project_id', 'status'),
        Index('idx_task_type', 'task_type'),  # NEW
        Index('idx_task_epic', 'epic_id'),  # NEW
        Index('idx_task_story', 'story_id'),  # NEW
    )
```

**Step 4**: Update to_dict() method (line 200-221) to include new fields

```python
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'id': self.id,
            'project_id': self.project_id,
            'parent_task_id': self.parent_task_id,
            'task_type': self.task_type.value,  # NEW
            'epic_id': self.epic_id,  # NEW
            'story_id': self.story_id,  # NEW
            'title': self.title,
            'description': self.description,
            'status': self.status.value,
            'assigned_to': self.assigned_to.value,
            'priority': self.priority,
            'dependencies': self.dependencies,
            'context': self.context,
            'result': self.result,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'is_deleted': self.is_deleted
        }
```

**Step 5**: Add new relationships after line 195 (after existing relationships)

```python
    # Agile hierarchy relationships (ADR-013)
    epic = relationship('Task', remote_side=[id], foreign_keys=[epic_id], backref='epic_stories')
    story = relationship('Task', remote_side=[id], foreign_keys=[story_id], backref='story_tasks')
```

**Validation**:
- ✅ task_type column added with default=TASK
- ✅ epic_id, story_id columns added (nullable)
- ✅ Indexes added for new columns
- ✅ to_dict() includes new fields
- ✅ Relationships defined

---

### TASK 1.3: Create Milestone Model

**File**: `src/core/models.py`
**Location**: After Task class (line ~250, after Task class ends)
**Action**: INSERT

```python


class Milestone(Base):
    """Milestone model - zero-duration checkpoint.

    Represents significant project checkpoints (e.g., Epic completion, phase gates).
    Milestones are NOT work items - they are binary achievement markers.

    ADR-013: Corrects previous misuse of "milestone" for "group of tasks".
    True milestones mark completion, not contain work.
    """
    __tablename__ = 'milestone'

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('project_state.id'), nullable=False, index=True)

    # Milestone details
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    target_date = Column(DateTime, nullable=True)

    # Completion tracking
    achieved = Column(Boolean, default=False, nullable=False, index=True)
    achieved_at = Column(DateTime, nullable=True)

    # Required completions (what must be done for this milestone)
    required_epic_ids = Column(
        JSON,
        default=list,
        nullable=False,
        comment='List of Epic IDs that must complete for this milestone'
    )

    # Metadata
    milestone_metadata = Column(JSON, default=dict)

    # Soft delete
    is_deleted = Column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Constraints
    __table_args__ = (
        Index('idx_milestone_project_achieved', 'project_id', 'achieved'),
    )

    # Relationships
    project = relationship('ProjectState', back_populates='milestones')

    def __repr__(self):
        status = "✓" if self.achieved else "○"
        return f"<Milestone(id={self.id}, name='{self.name}', {status})>"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
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
        """Check if all required Epics are completed.

        Args:
            state_manager: StateManager instance for querying tasks

        Returns:
            True if all required Epics completed, False otherwise
        """
        if not self.required_epic_ids:
            return False

        for epic_id in self.required_epic_ids:
            epic = state_manager.get_task(epic_id)
            if not epic or epic.status != TaskStatus.COMPLETED:
                return False

        return True
```

**Validation**:
- ✅ Milestone class added after Task
- ✅ All fields defined correctly
- ✅ Relationships to ProjectState
- ✅ to_dict() method implemented
- ✅ check_completion() helper method

---

### TASK 1.4: Update ProjectState Relationships

**File**: `src/core/models.py`
**Location**: ProjectState class (line ~71-126)
**Action**: MODIFY

**Find line ~125** (after existing relationships):
```python
    # Relationships
    tasks = relationship('Task', back_populates='project', cascade='all, delete-orphan')
    sessions = relationship('Session', back_populates='project', cascade='all, delete-orphan')
```

**Replace with**:
```python
    # Relationships
    tasks = relationship('Task', back_populates='project', cascade='all, delete-orphan')
    sessions = relationship('Session', back_populates='project', cascade='all, delete-orphan')
    milestones = relationship('Milestone', back_populates='project', cascade='all, delete-orphan')  # NEW (ADR-013)
```

**Validation**:
- ✅ milestones relationship added to ProjectState

---

### TASK 1.5: Create Database Migration Script

**File**: `migrations/versions/003_agile_hierarchy.sql` (NEW FILE)
**Action**: CREATE

```sql
-- Migration: Agile Hierarchy (ADR-013)
-- Date: 2025-11-05
-- Description: Add TaskType, Epic/Story tracking, Milestone model

-- Step 1: Add new columns to task table
ALTER TABLE task ADD COLUMN task_type TEXT DEFAULT 'task' NOT NULL;
ALTER TABLE task ADD COLUMN epic_id INTEGER;
ALTER TABLE task ADD COLUMN story_id INTEGER;

-- Step 2: Add indexes
CREATE INDEX idx_task_type ON task(task_type);
CREATE INDEX idx_task_epic ON task(epic_id);
CREATE INDEX idx_task_story ON task(story_id);
CREATE INDEX idx_task_project_status ON task(project_id, status);

-- Step 3: Add foreign keys
-- Note: SQLite requires recreation for FK constraints, but we'll add them logically
-- The SQLAlchemy model enforces these

-- Step 4: Create milestone table
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

-- Step 5: Create milestone indexes
CREATE INDEX idx_milestone_project_achieved ON milestone(project_id, achieved);

-- Step 6: Migrate existing data (all tasks default to TASK type)
-- Already done by DEFAULT 'task' in column definition

-- Verification queries
SELECT 'task table updated' as status, COUNT(*) as task_count FROM task;
SELECT 'milestone table created' as status, COUNT(*) as milestone_count FROM milestone;
```

**Validation**:
- ✅ SQL migration script created
- ✅ All schema changes captured
- ✅ Indexes added
- ✅ Verification queries included

---

## SECTION 2: CODEBASE TERMINOLOGY UPDATES

### TASK 2.1: Rename Milestone Methods in Orchestrator

**File**: `src/orchestrator.py`
**Action**: RENAME + UPDATE

**⚠️ CRITICAL**: Use search-and-replace carefully. Some "milestone" references are correct (new Milestone model), others need renaming to "epic".

**Step 1**: Rename `execute_milestone()` → `execute_epic()` (line ~667)

```python
# OLD (line ~667):
def execute_milestone(
    self,
    project_id: int,
    task_ids: List[int],
    milestone_id: Optional[int] = None,
    max_iterations_per_task: int = 10
) -> Dict[str, Any]:
    """Execute multiple tasks in a milestone with session management.

# NEW:
def execute_epic(
    self,
    project_id: int,
    epic_id: int,
    story_ids: List[int],
    max_iterations_per_story: int = 10
) -> Dict[str, Any]:
    """Execute multiple stories in an Epic with session management.

    Session lifecycle:
    1. Start new session for Epic
    2. Build Epic context (goals + previous summary)
    3. Execute all Stories in session
    4. End session and generate summary

    Args:
        project_id: Project ID
        epic_id: Epic task ID (task_type=EPIC)
        story_ids: List of Story IDs to execute (task_type=STORY)
        max_iterations_per_story: Max iterations per story (default: 10)

    Returns:
        Dictionary with execution results:
        - epic_id: int
        - session_id: str
        - stories_completed: int
        - stories_failed: int
        - results: List[Dict]

    Example:
        >>> result = orchestrator.execute_epic(
        ...     project_id=1,
        ...     epic_id=5,
        ...     story_ids=[10, 11, 12]
        ... )
    """
    logger.info(
        f"EPIC START: epic_id={epic_id}, "
        f"project_id={project_id}, num_stories={len(story_ids)}"
    )

    # Start session for Epic
    session_id = self._start_epic_session(project_id, epic_id)

    # Build Epic context
    epic_context = self._build_epic_context(project_id, epic_id)

    # Store context for story injection
    self._current_epic_context = epic_context
    self._current_epic_first_story = story_ids[0] if story_ids else None
    self._current_epic_id = epic_id

    results = []
    stories_completed = 0
    stories_failed = 0

    try:
        # Execute all stories in session
        for story_id in story_ids:
            try:
                logger.info(f"Executing story {story_id} in session {session_id[:8]}...")

                result = self.execute_task(
                    task_id=story_id,
                    max_iterations=max_iterations_per_story
                )

                results.append(result)

                if result.get('status') == 'completed':
                    stories_completed += 1
                else:
                    stories_failed += 1

            except Exception as e:
                logger.error(f"Story {story_id} failed: {e}")
                results.append({
                    'task_id': story_id,
                    'status': 'failed',
                    'error': str(e)
                })
                stories_failed += 1

        # End session
        self._end_epic_session(session_id, epic_id)

    finally:
        # Clean up context
        self._current_epic_context = None
        self._current_epic_first_story = None
        self._current_epic_id = None

    logger.info(
        f"EPIC END: epic_id={epic_id}, "
        f"completed={stories_completed}, failed={stories_failed}, "
        f"session_id={session_id[:8]}..."
    )

    return {
        'epic_id': epic_id,
        'session_id': session_id,
        'stories_completed': stories_completed,
        'stories_failed': stories_failed,
        'results': results
    }
```

**Step 2**: Rename helper methods (lines ~575-665)

Find and replace:
- `_start_milestone_session` → `_start_epic_session`
- `_end_milestone_session` → `_end_epic_session`
- `_build_milestone_context` → `_build_epic_context`
- `_current_milestone_context` → `_current_epic_context`
- `_current_milestone_first_task` → `_current_epic_first_story`
- `_current_milestone_id` → `_current_epic_id`
- `milestone_id` parameter → `epic_id` (in method signatures)

**Step 3**: Update method bodies to use new terminology

Key changes:
- Replace "milestone" logs with "epic"
- Update docstrings to reference Epic instead of milestone
- Update parameter names in method calls

**Validation**:
- ✅ execute_epic() method exists and has correct signature
- ✅ All helper methods renamed
- ✅ No references to execute_milestone() remain
- 🔍 Search codebase: `grep -r "execute_milestone" src/` returns empty

---

## SECTION 3: STATEMANAGER UPDATES

### TASK 3.1: Add Epic Creation Method

**File**: `src/core/state.py`
**Location**: After existing task methods (around line 400+)
**Action**: INSERT

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
            **kwargs: Additional task fields (priority, assigned_to, etc.)

        Returns:
            Epic task ID

        Example:
            >>> epic_id = state.create_epic(
            ...     project_id=1,
            ...     title="User Authentication System",
            ...     description="Complete auth with OAuth, MFA, session management",
            ...     priority=8
            ... )
        """
        from src.core.models import TaskType

        kwargs['task_type'] = TaskType.EPIC
        return self.create_task(
            project_id=project_id,
            title=title,
            description=description,
            **kwargs
        )
```

**Validation**:
- ✅ create_epic() method added
- ✅ Sets task_type=EPIC
- ✅ Delegates to create_task()
- ✅ Proper docstring with example

---

### TASK 3.2: Add Story Creation Method

**File**: `src/core/state.py`
**Location**: After create_epic() method
**Action**: INSERT

```python
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

        Example:
            >>> story_id = state.create_story(
            ...     project_id=1,
            ...     epic_id=5,
            ...     title="Email/password login",
            ...     description="As a user, I want to log in with email and password"
            ... )
        """
        from src.core.models import TaskType

        # Validate epic exists and is type EPIC
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
```

**Validation**:
- ✅ create_story() method added
- ✅ Validates epic exists and is correct type
- ✅ Sets task_type=STORY and epic_id
- ✅ Raises clear errors for invalid epic

---

### TASK 3.3: Add Epic/Story Query Methods

**File**: `src/core/state.py`
**Location**: After create_story() method
**Action**: INSERT

```python
    def get_epic_stories(self, epic_id: int) -> List[Task]:
        """Get all stories belonging to an epic.

        Args:
            epic_id: Epic task ID

        Returns:
            List of Story tasks

        Example:
            >>> stories = state.get_epic_stories(epic_id=5)
            >>> print(f"Epic has {len(stories)} stories")
        """
        from src.core.models import Task, TaskType

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

        Example:
            >>> tasks = state.get_story_tasks(story_id=10)
            >>> print(f"Story has {len(tasks)} implementation tasks")
        """
        from src.core.models import Task, TaskType

        with self._session_scope() as session:
            tasks = session.query(Task).filter(
                Task.story_id == story_id,
                Task.task_type == TaskType.TASK,
                Task.is_deleted == False
            ).all()
            return [self._detach_task(t) for t in tasks]
```

**Validation**:
- ✅ get_epic_stories() returns filtered stories
- ✅ get_story_tasks() returns filtered tasks
- ✅ Both use TaskType enum for filtering
- ✅ Both use _detach_task() for session safety

---

### TASK 3.4: Add Milestone CRUD Methods

**File**: `src/core/state.py`
**Location**: After get_story_tasks() method
**Action**: INSERT

```python
    def create_milestone(
        self,
        project_id: int,
        name: str,
        description: Optional[str] = None,
        required_epic_ids: Optional[List[int]] = None,
        target_date: Optional[datetime] = None
    ) -> int:
        """Create a milestone checkpoint.

        Milestone: Zero-duration checkpoint marking epic/phase completion.

        Args:
            project_id: Project ID
            name: Milestone name
            description: Optional description
            required_epic_ids: Epics that must complete
            target_date: Optional target date

        Returns:
            Milestone ID

        Example:
            >>> milestone_id = state.create_milestone(
            ...     project_id=1,
            ...     name="Authentication System Complete",
            ...     required_epic_ids=[5],
            ...     target_date=datetime(2025, 12, 31)
            ... )
        """
        from src.core.models import Milestone

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
        """Get milestone by ID.

        Args:
            milestone_id: Milestone ID

        Returns:
            Milestone object or None
        """
        from src.core.models import Milestone

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
        """Check if milestone requirements are met.

        Args:
            milestone_id: Milestone ID

        Returns:
            True if all required tasks are complete

        Example:
            >>> if state.check_milestone_completion(milestone_id=3):
            ...     state.achieve_milestone(milestone_id=3)
        """
        milestone = self.get_milestone(milestone_id)
        if not milestone:
            return False

        return milestone.check_completion(self)

    def achieve_milestone(self, milestone_id: int) -> None:
        """Mark milestone as achieved.

        Args:
            milestone_id: Milestone ID

        Example:
            >>> state.achieve_milestone(milestone_id=3)
        """
        from src.core.models import Milestone
        from datetime import datetime

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
- ✅ create_milestone() creates Milestone records
- ✅ get_milestone() retrieves with expunge (session safety)
- ✅ check_milestone_completion() uses Milestone.check_completion()
- ✅ achieve_milestone() updates achieved status

---

## SECTION 4: CLI COMMAND UPDATES

### TASK 4.1: Add Epic Command Group

**File**: `src/cli.py`
**Location**: After project commands (around line 200+)
**Action**: INSERT

```python
# ============================================================================
# Epic Commands (ADR-013)
# ============================================================================

@cli.group()
def epic():
    """Manage epics (large features spanning multiple stories)."""
    pass


@epic.command('create')
@click.argument('title')
@click.option('--project', '-p', type=int, required=True, help='Project ID')
@click.option('--description', '-d', default='', help='Epic description')
@click.option('--priority', type=int, default=5, help='Priority (1-10)')
def epic_create(title, project, description, priority):
    """Create a new epic.

    Example:
        obra epic create "User Authentication System" -p 1 -d "Complete auth with OAuth, MFA"
    """
    config = Config.load()
    state = StateManager(config)

    epic_id = state.create_epic(
        project_id=project,
        title=title,
        description=description,
        priority=priority
    )

    click.echo(f"✓ Created epic {epic_id}: {title}")
    click.echo(f"  Project: {project}")
    click.echo(f"  Type: EPIC")


@epic.command('list')
@click.option('--project', '-p', type=int, required=True, help='Project ID')
@click.option('--status', '-s', help='Filter by status')
def epic_list(project, status):
    """List all epics in project.

    Example:
        obra epic list -p 1
        obra epic list -p 1 --status completed
    """
    from src.core.models import Task, TaskType

    config = Config.load()
    state = StateManager(config)

    with state._session_scope() as session:
        query = session.query(Task).filter(
            Task.project_id == project,
            Task.task_type == TaskType.EPIC,
            Task.is_deleted == False
        )

        if status:
            query = query.filter(Task.status == status)

        epics = query.all()

    if not epics:
        click.echo("No epics found")
        return

    click.echo(f"\nEpics for project {project}:\n")
    for epic in epics:
        stories = state.get_epic_stories(epic.id)
        click.echo(f"  [{epic.id}] {epic.title}")
        click.echo(f"      Status: {epic.status.value}")
        click.echo(f"      Stories: {len(stories)}")
        click.echo(f"      Priority: {epic.priority}")
        click.echo()


@epic.command('execute')
@click.argument('epic_id', type=int)
@click.option('--max-iterations', type=int, default=10, help='Max iterations per story')
def epic_execute(epic_id, max_iterations):
    """Execute all stories in an epic.

    Example:
        obra epic execute 5 --max-iterations 10
    """
    config = Config.load()
    orchestrator = Orchestrator(config)

    click.echo(f"Executing epic {epic_id}...\n")

    try:
        epic = orchestrator.state.get_task(epic_id)
        stories = orchestrator.state.get_epic_stories(epic_id)

        result = orchestrator.execute_epic(
            project_id=epic.project_id,
            epic_id=epic_id,
            story_ids=[s.id for s in stories],
            max_iterations_per_story=max_iterations
        )

        click.echo(f"\n✓ Epic {epic_id} execution complete")
        click.echo(f"  Stories completed: {result['stories_completed']}/{len(stories)}")
        click.echo(f"  Stories failed: {result['stories_failed']}")

    except Exception as e:
        click.echo(f"\n✗ Epic execution failed: {e}", err=True)
        raise
```

**Validation**:
- ✅ epic create works
- ✅ epic list works
- ✅ epic execute works

---

### TASK 4.2: Add Story Command Group

**File**: `src/cli.py`
**Location**: After epic commands
**Action**: INSERT

```python
# ============================================================================
# Story Commands (ADR-013)
# ============================================================================

@cli.group()
def story():
    """Manage stories (user-facing deliverables)."""
    pass


@story.command('create')
@click.argument('title')
@click.option('--epic', '-e', type=int, required=True, help='Epic ID')
@click.option('--project', '-p', type=int, required=True, help='Project ID')
@click.option('--description', '-d', default='', help='Story description')
@click.option('--priority', type=int, default=5, help='Priority (1-10)')
@click.option('--depends-on', help='Comma-separated task IDs this story depends on')
def story_create(title, epic, project, description, priority, depends_on):
    """Create a new story under an epic.

    Example:
        obra story create "Email/password login" -e 5 -p 1 -d "As a user, I want to log in"
    """
    config = Config.load()
    state = StateManager(config)

    # Parse dependencies
    dependencies = []
    if depends_on:
        dependencies = [int(x.strip()) for x in depends_on.split(',')]

    story_id = state.create_story(
        project_id=project,
        epic_id=epic,
        title=title,
        description=description,
        priority=priority
    )

    # Add dependencies
    if dependencies:
        task = state.get_task(story_id)
        for dep_id in dependencies:
            task.add_dependency(dep_id)
        state.update_task(story_id, dependencies=task.dependencies)

    click.echo(f"✓ Created story {story_id}: {title}")
    click.echo(f"  Epic: {epic}")
    click.echo(f"  Project: {project}")
    click.echo(f"  Type: STORY")
    if dependencies:
        click.echo(f"  Dependencies: {dependencies}")


@story.command('list')
@click.option('--epic', '-e', type=int, help='Filter by epic ID')
@click.option('--project', '-p', type=int, help='Filter by project ID')
@click.option('--status', '-s', help='Filter by status')
def story_list(epic, project, status):
    """List stories.

    Example:
        obra story list -e 5
        obra story list -p 1 --status pending
    """
    from src.core.models import Task, TaskType

    config = Config.load()
    state = StateManager(config)

    with state._session_scope() as session:
        query = session.query(Task).filter(
            Task.task_type == TaskType.STORY,
            Task.is_deleted == False
        )

        if epic:
            query = query.filter(Task.epic_id == epic)
        if project:
            query = query.filter(Task.project_id == project)
        if status:
            query = query.filter(Task.status == status)

        stories = query.all()

    if not stories:
        click.echo("No stories found")
        return

    click.echo(f"\nStories:\n")
    for story in stories:
        tasks = state.get_story_tasks(story.id)
        click.echo(f"  [{story.id}] {story.title}")
        click.echo(f"      Epic: {story.epic_id}")
        click.echo(f"      Status: {story.status.value}")
        click.echo(f"      Tasks: {len(tasks)}")
        if story.dependencies:
            click.echo(f"      Dependencies: {story.dependencies}")
        click.echo()
```

**Validation**:
- ✅ story create works with --epic
- ✅ story list filters work
- ✅ Dependencies can be added to stories

---

### TASK 4.3: Add Milestone Command Group

**File**: `src/cli.py`
**Location**: After story commands
**Action**: INSERT

```python
# ============================================================================
# Milestone Commands (ADR-013)
# ============================================================================

@cli.group()
def milestone():
    """Manage milestones (zero-duration checkpoints)."""
    pass


@milestone.command('create')
@click.argument('name')
@click.option('--project', '-p', type=int, required=True, help='Project ID')
@click.option('--description', '-d', help='Milestone description')
@click.option('--epics', help='Comma-separated epic IDs required for completion')
@click.option('--target-date', help='Target date (YYYY-MM-DD)')
def milestone_create(name, project, description, epics, target_date):
    """Create a milestone checkpoint.

    Example:
        obra milestone create "Auth System Complete" -p 1 --epics 5 --target-date 2025-12-31
    """
    from datetime import datetime

    config = Config.load()
    state = StateManager(config)

    # Parse requirements
    required_epic_ids = []
    if epics:
        required_epic_ids = [int(x.strip()) for x in epics.split(',')]

    # Parse target date
    target_dt = None
    if target_date:
        target_dt = datetime.strptime(target_date, '%Y-%m-%d')

    milestone_id = state.create_milestone(
        project_id=project,
        name=name,
        description=description,
        required_epic_ids=required_epic_ids,
        target_date=target_dt
    )

    click.echo(f"✓ Created milestone {milestone_id}: {name}")
    click.echo(f"  Project: {project}")
    if required_epic_ids:
        click.echo(f"  Required epics: {required_epic_ids}")
    if target_date:
        click.echo(f"  Target date: {target_date}")


@milestone.command('check')
@click.argument('milestone_id', type=int)
def milestone_check(milestone_id):
    """Check if milestone requirements are met.

    Example:
        obra milestone check 3
    """
    from src.core.models import TaskStatus

    config = Config.load()
    state = StateManager(config)

    milestone = state.get_milestone(milestone_id)
    if not milestone:
        click.echo(f"✗ Milestone {milestone_id} not found", err=True)
        return

    is_complete = state.check_milestone_completion(milestone_id)

    if is_complete:
        click.echo(f"✓ Milestone {milestone_id} requirements are met!")
        click.echo(f"  Run 'obra milestone achieve {milestone_id}' to mark as achieved")
    else:
        click.echo(f"○ Milestone {milestone_id} requirements NOT met")

        # Show what's incomplete
        for epic_id in milestone.required_epic_ids:
            epic = state.get_task(epic_id)
            if epic:
                status_icon = "✓" if epic.status == TaskStatus.COMPLETED else "✗"
                click.echo(f"  {status_icon} Epic {epic_id}: {epic.title} [{epic.status.value}]")


@milestone.command('achieve')
@click.argument('milestone_id', type=int)
def milestone_achieve(milestone_id):
    """Mark milestone as achieved.

    Example:
        obra milestone achieve 3
    """
    config = Config.load()
    state = StateManager(config)

    if not state.check_milestone_completion(milestone_id):
        click.echo(f"✗ Cannot achieve milestone {milestone_id}: requirements not met", err=True)
        click.echo(f"  Run 'obra milestone check {milestone_id}' to see what's incomplete")
        return

    state.achieve_milestone(milestone_id)
    click.echo(f"✓ Milestone {milestone_id} achieved!")
```

**Validation**:
- ✅ milestone create works
- ✅ milestone check validates requirements
- ✅ milestone achieve marks as complete

---

### TASK 4.4: Update Task Commands

**File**: `src/cli.py`
**Location**: Existing task create command (around line 150+)
**Action**: MODIFY

```python
@task.command('create')
@click.argument('title')
@click.option('--project', '-p', type=int, required=True, help='Project ID')
@click.option('--description', '-d', default='', help='Task description')
@click.option('--story', '-s', type=int, help='Story ID this task implements')  # NEW
@click.option('--priority', type=int, default=5, help='Priority (1-10)')
@click.option('--depends-on', help='Comma-separated task IDs this task depends on')
@click.option('--assigned-to', type=click.Choice(['human', 'local_llm', 'claude_code']), default='claude_code')
def task_create(title, project, description, story, priority, depends_on, assigned_to):
    """Create a new task.

    Example:
        obra task create "Implement login API" -p 1 -s 12 -d "Create /api/login endpoint"
    """
    from src.core.models import TaskType, TaskAssignee

    config = Config.load()
    state = StateManager(config)

    # Parse dependencies
    dependencies = []
    if depends_on:
        dependencies = [int(x.strip()) for x in depends_on.split(',')]

    # Validate story if provided
    if story:
        story_obj = state.get_task(story)
        if not story_obj:
            click.echo(f"✗ Story {story} not found", err=True)
            return
        if story_obj.task_type != TaskType.STORY:
            click.echo(f"✗ Task {story} is not a Story (type={story_obj.task_type})", err=True)
            return

    task_id = state.create_task(
        project_id=project,
        title=title,
        description=description,
        story_id=story,  # NEW
        priority=priority,
        assigned_to=TaskAssignee(assigned_to),
        dependencies=dependencies
    )

    click.echo(f"✓ Created task {task_id}: {title}")
    click.echo(f"  Project: {project}")
    if story:
        click.echo(f"  Story: {story}")
    click.echo(f"  Type: TASK")
    if dependencies:
        click.echo(f"  Dependencies: {dependencies}")
```

**Validation**:
- ✅ task create accepts --story option
- ✅ Validates story exists and is correct type
- ✅ Sets story_id on task

---

## SECTION 5: TEST UPDATES

### TASK 5.1: Create Test Fixtures

**File**: `tests/conftest.py`
**Location**: Add after existing fixtures
**Action**: INSERT

```python
# ============================================================================
# Agile Hierarchy Test Fixtures (ADR-013)
# ============================================================================

@pytest.fixture
def sample_epic(state_manager, sample_project):
    """Create a sample epic for testing."""
    from src.core.models import TaskType

    epic_id = state_manager.create_epic(
        project_id=sample_project.id,
        title="User Authentication System",
        description="Complete authentication with OAuth, MFA, session management",
        priority=8
    )
    return state_manager.get_task(epic_id)


@pytest.fixture
def sample_story(state_manager, sample_epic):
    """Create a sample story for testing."""
    from src.core.models import TaskType

    story_id = state_manager.create_story(
        project_id=sample_epic.project_id,
        epic_id=sample_epic.id,
        title="Email/password login",
        description="As a user, I want to log in with email and password",
        priority=7
    )
    return state_manager.get_task(story_id)


@pytest.fixture
def sample_milestone(state_manager, sample_project, sample_epic):
    """Create a sample milestone for testing."""
    milestone_id = state_manager.create_milestone(
        project_id=sample_project.id,
        name="Authentication Complete",
        description="Authentication system ready for production",
        required_epic_ids=[sample_epic.id]
    )
    return state_manager.get_milestone(milestone_id)
```

**Validation**:
- ✅ sample_epic fixture works
- ✅ sample_story fixture works
- ✅ sample_milestone fixture works

---

### TASK 5.2: Create Agile Hierarchy Tests

**File**: `tests/test_agile_hierarchy.py` (NEW FILE)
**Action**: CREATE

Create comprehensive tests (150+ tests) for:
- TaskType enum
- Epic creation and retrieval
- Story creation and epic association
- Task-story association
- Hierarchy validation
- Milestone creation and completion checking

See AGILE_MIGRATION_START.md for complete test examples.

**Validation**:
- ✅ All 150+ tests pass
- ✅ Coverage ≥90% for new code

---

### TASK 5.3: Update Existing Tests

**Files to Update**:

1. **tests/test_state.py**:
   - Update create_task() tests to include task_type
   - Add tests for create_epic(), create_story()
   - Add tests for milestone CRUD

2. **tests/test_orchestrator.py**:
   - Rename test_execute_milestone → test_execute_epic
   - Update all execute_milestone() calls
   - Add tests for epic execution

3. **tests/test_models.py**:
   - Add TaskType enum tests
   - Add Milestone model tests
   - Test Task.to_dict() includes new fields

**Validation**:
- ✅ All existing tests pass with modifications
- ✅ No test failures
- ✅ Coverage maintained ≥85%

---

## SECTION 6: DOCUMENTATION UPDATES

### TASK 6.1: Update User Guides

**Files to Update**:

1. **docs/guides/GETTING_STARTED.md**:
   - Replace "milestone" with "epic/story"
   - Add epic/story creation examples
   - Add milestone checkpoint examples

2. **docs/guides/CLI_REFERENCE.md**:
   - Add `obra epic` section
   - Add `obra story` section
   - Add `obra milestone` section
   - Update `obra task` with --story option

**Validation**:
- ✅ No references to old "milestone as task group" concept
- ✅ All examples use Agile terminology

---

### TASK 6.2: Update Technical Documentation

**Files to Update**:

1. **docs/architecture/ARCHITECTURE.md**:
   - Update data model diagrams
   - Add TaskType, epic_id, story_id to Task schema
   - Add Milestone model to schema
   - Update terminology throughout

2. **docs/design/OBRA_SYSTEM_OVERVIEW.md**:
   - Update work hierarchy section
   - Replace milestone examples with epic/story
   - Add true milestone checkpoint examples

3. **CLAUDE.md**:
   - Update Architecture Principles section
   - Update Common Pitfalls section
   - Update data flow diagram
   - Update example commands

**Validation**:
- ✅ All docs use consistent Agile terminology
- ✅ Schema diagrams accurate
- ✅ No contradictions with ADR-013

---

### TASK 6.3: Update CHANGELOG.md

**File**: `CHANGELOG.md`
**Location**: Under [Unreleased] or new [1.3.0] section
**Action**: ADD

```markdown
## [1.3.0] - 2025-11-XX

### Added
- **Agile/Scrum Work Hierarchy** (ADR-013):
  - TaskType enum (EPIC, STORY, TASK, SUBTASK)
  - Epic creation and management (`obra epic create`, `epic execute`)
  - Story creation under epics (`obra story create`)
  - True Milestone model for zero-duration checkpoints (`obra milestone create`)
  - CLI commands: `epic`, `story`, `milestone` command groups

### Changed
- **BREAKING**: Renamed `execute_milestone()` to `execute_epic()`
- **BREAKING**: "Milestone" now means zero-duration checkpoint (not task group)
- Task model: Added `task_type`, `epic_id`, `story_id` fields
- All documentation updated with Agile terminology

### Migration
- Database schema migration required:
  ```bash
  sqlite3 obra.db < migrations/versions/003_agile_hierarchy.sql
  ```
- No backward compatibility with old "milestone" concept
- All existing tasks default to `task_type='task'`

### Fixed
- Corrected terminology misuse of "milestone" for task groups
```

**Validation**:
- ✅ CHANGELOG entry added
- ✅ Breaking changes clearly marked
- ✅ Migration instructions included

---

## SECTION 7: VALIDATION & EXECUTION

### TASK 7.1: Pre-Migration Checklist

Before running migration:

- [ ] Database backed up
- [ ] All code changes committed to Git
- [ ] Tests run successfully on current code
- [ ] Migration script reviewed
- [ ] Rollback plan documented

### TASK 7.2: Migration Execution

**Steps**:

1. **Backup database**:
   ```bash
   cp obra.db obra.db.backup_$(date +%Y%m%d_%H%M%S)
   ```

2. **Run migration**:
   ```bash
   sqlite3 obra.db < migrations/versions/003_agile_hierarchy.sql
   ```

3. **Verify schema**:
   ```bash
   sqlite3 obra.db ".schema task"
   sqlite3 obra.db ".schema milestone"
   ```

4. **Test basic operations**:
   ```bash
   python -c "from src.core.models import TaskType, Milestone; print('✓ Imports successful')"
   ```

**Validation**:
- ✅ Migration runs without errors
- ✅ Schema matches models
- ✅ No data lost

---

### TASK 7.3: Post-Migration Testing

**Test Suite**:

```bash
# Run all tests
pytest tests/ -v

# Check coverage
pytest --cov=src --cov-report=term

# Run specific new tests
pytest tests/test_agile_hierarchy.py -v
pytest tests/test_epic_execution.py -v
pytest tests/test_milestone_management.py -v
```

**Validation**:
- ✅ All tests pass (700+ tests)
- ✅ Coverage ≥85% maintained
- ✅ No regressions

---

### TASK 7.4: Manual Testing

**CLI Testing**:

```bash
# Test epic creation
obra epic create "Test Epic" -p 1 -d "Testing epic creation"

# Test story creation
obra story create "Test Story" -e 1 -p 1 -d "Testing story creation"

# Test milestone creation
obra milestone create "Test Milestone" -p 1 --epics 1

# Test milestone check
obra milestone check 1

# Test epic execution
obra epic execute 1
```

**Validation**:
- ✅ All CLI commands work
- ✅ No errors in logs
- ✅ Data persists correctly

---

### TASK 7.5: Rollback Plan

If migration fails:

1. **Stop all processes**
2. **Restore database backup**:
   ```bash
   cp obra.db.backup_YYYYMMDD_HHMMSS obra.db
   ```
3. **Revert code changes**:
   ```bash
   git reset --hard HEAD~1
   ```
4. **Document issues encountered**
5. **Fix issues and retry**

---

## APPENDIX A: Complete File Modification Summary

### Files Modified

| File | Lines Added | Lines Removed | Action |
|------|-------------|---------------|--------|
| src/core/models.py | +200 | 0 | Add TaskType, update Task, add Milestone |
| src/core/state.py | +250 | 0 | Add epic/story/milestone methods |
| src/orchestrator.py | +100 | -50 | Rename execute_milestone → execute_epic |
| src/cli.py | +400 | 0 | Add epic, story, milestone commands |
| tests/conftest.py | +50 | 0 | Add test fixtures |
| tests/test_agile_hierarchy.py | +400 | 0 | NEW: Comprehensive hierarchy tests |
| tests/test_state.py | +100 | 0 | Add epic/story/milestone tests |
| tests/test_orchestrator.py | +50 | -20 | Update execute_milestone → execute_epic |
| migrations/versions/003_agile_hierarchy.sql | +50 | 0 | NEW: Database migration |
| docs/*.md | +300 | -100 | Update all documentation |

**Total**: ~1,900 lines added, ~170 lines removed

---

## APPENDIX B: Quick Reference Commands

### Database Migration
```bash
sqlite3 obra.db < migrations/versions/003_agile_hierarchy.sql
```

### Testing
```bash
pytest tests/test_agile_hierarchy.py -v
pytest --cov=src --cov-report=term
```

### CLI Usage
```bash
# Epic workflow
obra epic create "Auth System" -p 1
obra story create "Login" -e 1 -p 1
obra epic execute 1

# Milestone workflow
obra milestone create "Auth Complete" -p 1 --epics 1
obra milestone check 1
obra milestone achieve 1
```

---

**END OF IMPLEMENTATION PLAN**

**Status**: ✅ COMPLETE
**Version**: 1.0 (Enhanced)
**Last Updated**: November 5, 2025
**Next Action**: Execute SECTION 1 (Database Schema Updates)