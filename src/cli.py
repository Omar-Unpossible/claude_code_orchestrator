"""CLI interface for Claude Code Orchestrator.

Provides Click-based commands for project/task management and orchestrator control.

Usage:
    $ python -m src.cli init
    $ python -m src.cli project create "My Project"
    $ python -m src.cli task create "Implement feature X"
    $ python -m src.cli run
    $ python -m src.cli interactive
"""

import sys
import logging
from pathlib import Path
from typing import Optional

import click

from src.orchestrator import Orchestrator, OrchestratorState
from src.core.config import Config
from src.core.state import StateManager
from src.core.exceptions import OrchestratorException

logger = logging.getLogger(__name__)


@click.group()
@click.option('--config', '-c', type=click.Path(exists=True), help='Path to config file')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.pass_context
def cli(ctx, config: Optional[str], verbose: bool):
    """Claude Code Orchestrator - Autonomous task execution with oversight."""
    # Setup logging
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Load config
    if config:
        config_mgr = Config.load(config)
    else:
        config_mgr = Config.load()  # FIX: Use Config.load() not Config()

    ctx.ensure_object(dict)
    ctx.obj['config'] = config_mgr
    ctx.obj['verbose'] = verbose


@cli.command()
@click.option('--db-url', default='sqlite:///orchestrator.db', help='Database URL')
@click.pass_context
def init(ctx, db_url: str):
    """Initialize orchestrator database and configuration."""
    try:
        click.echo("Initializing orchestrator...")

        # Initialize state manager
        state_manager = StateManager.get_instance(db_url)
        click.echo(f"✓ Database initialized: {db_url}")

        # Create config directory if needed
        config_dir = Path('config')
        config_dir.mkdir(exist_ok=True)

        # Create default config if not exists
        default_config = config_dir / 'config.yaml'
        if not default_config.exists():
            config_content = """# Claude Code Orchestrator Configuration

database:
  url: sqlite:///orchestrator.db

agent:
  type: claude-code-local  # Options: claude-code-local, local, claude-code-ssh, ssh, claude-code-docker, docker, aider
  config:
    timeout: 300
    max_retries: 3

llm:
  provider: ollama
  model: qwen2.5-coder:32b
  base_url: http://localhost:11434
  temperature: 0.1

orchestration:
  breakpoints:
    confidence_threshold: 0.7
    max_retries: 3

  decision:
    high_confidence: 0.85
    medium_confidence: 0.65
    low_confidence: 0.4

  quality:
    min_quality_score: 0.7
    enable_syntax_validation: true
    enable_testing_validation: false

  scheduler:
    max_concurrent_tasks: 1
    priority_weights:
      priority: 0.4
      age: 0.3
      dependencies: 0.3

utils:
  token_counter:
    default_model: qwen2.5-coder

  context_manager:
    max_tokens: 100000
    summarization_threshold: 50000
    compression_ratio: 0.3

  confidence_scorer:
    ensemble_weight_heuristic: 0.4
    ensemble_weight_llm: 0.6
"""
            default_config.write_text(config_content)
            click.echo(f"✓ Created default config: {default_config}")

        click.echo("\n✓ Orchestrator initialized successfully!")
        click.echo("\nNext steps:")
        click.echo("  1. Create a project: cli project create 'My Project'")
        click.echo("  2. Create a task: cli task create 'Implement feature'")
        click.echo("  3. Run orchestrator: cli run")

    except Exception as e:
        click.echo(f"✗ Initialization failed: {e}", err=True)
        sys.exit(1)


# ============================================================================
# Project Management Commands
# ============================================================================

@cli.group()
def project():
    """Manage projects."""
    pass


@project.command('create')
@click.argument('name')
@click.option('--description', '-d', default='', help='Project description')
@click.option('--working-dir', '-w', type=click.Path(), help='Working directory path')
@click.pass_context
def project_create(ctx, name: str, description: str, working_dir: Optional[str]):
    """Create a new project."""
    try:
        config = ctx.obj['config']
        db_url = config.get('database.url', 'sqlite:///orchestrator.db')
        state_manager = StateManager.get_instance(db_url)

        # Use current directory if not specified
        if not working_dir:
            working_dir = str(Path.cwd())

        # FIX: create_project takes positional args, not a dict
        project = state_manager.create_project(
            name=name,
            description=description,
            working_dir=working_dir
        )

        click.echo(f"✓ Created project #{project.id}: {name}")
        click.echo(f"  Working directory: {working_dir}")

    except Exception as e:
        click.echo(f"✗ Failed to create project: {e}", err=True)
        sys.exit(1)


@project.command('list')
@click.pass_context
def project_list(ctx):
    """List all projects."""
    try:
        config = ctx.obj['config']
        db_url = config.get('database.url', 'sqlite:///orchestrator.db')
        state_manager = StateManager.get_instance(db_url)

        projects = state_manager.list_projects()

        if not projects:
            click.echo("No projects found. Create one with: cli project create")
            return

        click.echo("\nProjects:")
        click.echo("-" * 80)
        for p in projects:
            click.echo(f"  #{p.id}: {p.project_name}")
            click.echo(f"       {p.description}")
            click.echo(f"       Working dir: {p.working_directory}")
            click.echo(f"       Status: {p.status}")
            click.echo()

    except Exception as e:
        click.echo(f"✗ Failed to list projects: {e}", err=True)
        sys.exit(1)


@project.command('show')
@click.argument('project_id', type=int)
@click.pass_context
def project_show(ctx, project_id: int):
    """Show detailed project information."""
    try:
        config = ctx.obj['config']
        db_url = config.get('database.url', 'sqlite:///orchestrator.db')
        state_manager = StateManager.get_instance(db_url)

        project = state_manager.get_project(project_id)

        if not project:
            click.echo(f"✗ Project #{project_id} not found", err=True)
            sys.exit(1)

        click.echo(f"\nProject #{project.id}: {project.project_name}")
        click.echo("=" * 80)
        click.echo(f"Description: {project.description}")
        click.echo(f"Working directory: {project.working_directory}")
        click.echo(f"Status: {project.status}")
        click.echo(f"Created: {project.created_at}")
        click.echo(f"Updated: {project.updated_at}")

        # Show tasks
        tasks = state_manager.get_project_tasks(project_id)
        click.echo(f"\nTasks ({len(tasks)}):")
        for task in tasks:
            click.echo(f"  #{task.id}: {task.title} [{task.status}]")

    except Exception as e:
        click.echo(f"✗ Failed to show project: {e}", err=True)
        sys.exit(1)


# ============================================================================
# Task Management Commands
# ============================================================================

@cli.group()
def task():
    """Manage tasks."""
    pass


@task.command('create')
@click.argument('title')
@click.option('--project', '-p', type=int, required=True, help='Project ID')
@click.option('--description', '-d', default='', help='Task description')
@click.option('--priority', type=int, default=5, help='Priority (1-10)')
@click.pass_context
def task_create(ctx, title: str, project: int, description: str, priority: int):
    """Create a new task."""
    try:
        config = ctx.obj['config']
        db_url = config.get('database.url', 'sqlite:///orchestrator.db')
        state_manager = StateManager.get_instance(db_url)

        task_data = {
            'title': title,
            'description': description,
            'priority': priority,
            'status': 'pending'
        }

        task = state_manager.create_task(project, task_data)

        click.echo(f"✓ Created task #{task.id}: {title}")
        click.echo(f"  Project: #{project}")
        click.echo(f"  Priority: {priority}")

    except Exception as e:
        click.echo(f"✗ Failed to create task: {e}", err=True)
        sys.exit(1)


@task.command('list')
@click.option('--project', '-p', type=int, help='Filter by project ID')
@click.option('--status', '-s', help='Filter by status')
@click.pass_context
def task_list(ctx, project: Optional[int], status: Optional[str]):
    """List tasks."""
    try:
        config = ctx.obj['config']
        db_url = config.get('database.url', 'sqlite:///orchestrator.db')
        state_manager = StateManager.get_instance(db_url)

        if project:
            tasks = state_manager.get_project_tasks(project)
        else:
            tasks = state_manager.list_tasks()

        # Filter by status if specified
        if status:
            tasks = [t for t in tasks if t.status == status]

        if not tasks:
            click.echo("No tasks found.")
            return

        click.echo("\nTasks:")
        click.echo("-" * 80)
        for t in tasks:
            click.echo(f"  #{t.id}: {t.title} [{t.status}]")
            click.echo(f"       Project: #{t.project_id} | Priority: {t.priority}")
            if t.description:
                click.echo(f"       {t.description[:60]}...")
            click.echo()

    except Exception as e:
        click.echo(f"✗ Failed to list tasks: {e}", err=True)
        sys.exit(1)


@task.command('execute')
@click.argument('task_id', type=int)
@click.option('--max-iterations', '-i', type=int, default=10, help='Max iterations')
@click.option('--stream', is_flag=True, help='Enable real-time streaming output')
@click.option('--interactive', is_flag=True, help='Enable interactive mode with command injection')
@click.pass_context
def task_execute(ctx, task_id: int, max_iterations: int, stream: bool, interactive: bool):
    """Execute a single task."""
    try:
        config = ctx.obj['config']

        # Initialize orchestrator
        orchestrator = Orchestrator(config=config)
        orchestrator.initialize()

        click.echo(f"Executing task #{task_id}...")

        # Execute task (Phase 2: added interactive parameter)
        result = orchestrator.execute_task(
            task_id,
            max_iterations=max_iterations,
            stream=stream,
            interactive=interactive
        )

        # Display results
        click.echo("\n" + "=" * 80)
        click.echo(f"Task #{task_id} execution result:")
        click.echo("=" * 80)
        click.echo(f"Status: {result['status']}")
        click.echo(f"Iterations: {result['iterations']}")

        if 'quality_score' in result:
            click.echo(f"Quality Score: {result['quality_score']:.2f}")
        if 'confidence' in result:
            click.echo(f"Confidence: {result['confidence']:.2f}")

        if result['status'] == 'completed':
            click.echo("\n✓ Task completed successfully!")
        elif result['status'] == 'escalated':
            click.echo(f"\n⚠ Task escalated: {result.get('reason', 'Unknown')}")
        else:
            click.echo(f"\n✗ Task did not complete: {result.get('message', '')}")

        # Cleanup
        orchestrator.shutdown()

    except OrchestratorException as e:
        click.echo(f"✗ Orchestration error: {e}", err=True)
        click.echo(f"  Context: {e.context}", err=True)
        if e.recovery:
            click.echo(f"  Recovery: {e.recovery}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"✗ Failed to execute task: {e}", err=True)
        sys.exit(1)


# ============================================================================
# Epic Management Commands (ADR-013)
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
@click.pass_context
def epic_create(ctx, title: str, project: int, description: str, priority: int):
    """Create a new epic."""
    try:
        config = ctx.obj['config']
        db_url = config.get('database.url', 'sqlite:///orchestrator.db')
        state_manager = StateManager.get_instance(db_url)

        epic_id = state_manager.create_epic(
            project_id=project,
            title=title,
            description=description,
            priority=priority
        )

        click.echo(f"✓ Created epic #{epic_id}: {title}")
        click.echo(f"  Project: #{project}")
        click.echo(f"  Priority: {priority}")

    except Exception as e:
        click.echo(f"✗ Failed to create epic: {e}", err=True)
        sys.exit(1)


@epic.command('execute')
@click.argument('epic_id', type=int)
@click.pass_context
def epic_execute(ctx, epic_id: int):
    """Execute all stories in an epic."""
    try:
        config = ctx.obj['config']
        orchestrator = Orchestrator(config=config)
        orchestrator.initialize()

        # Get epic to find project_id
        db_url = config.get('database.url', 'sqlite:///orchestrator.db')
        state_manager = StateManager.get_instance(db_url)
        epic = state_manager.get_task(epic_id)

        if not epic:
            click.echo(f"✗ Epic {epic_id} not found", err=True)
            sys.exit(1)

        click.echo(f"Executing epic #{epic_id}: {epic.title}")

        result = orchestrator.execute_epic(
            project_id=epic.project_id,
            epic_id=epic_id
        )

        click.echo(f"✓ Epic execution complete:")
        click.echo(f"  Stories completed: {result['stories_completed']}/{result['total_stories']}")
        click.echo(f"  Stories failed: {result['stories_failed']}")

    except Exception as e:
        click.echo(f"✗ Failed to execute epic: {e}", err=True)
        sys.exit(1)


@epic.command('list')
@click.option('--project', '-p', type=int, help='Filter by project ID')
@click.option('--status', '-s', help='Filter by status (pending, running, completed, failed)')
@click.pass_context
def epic_list(ctx, project: Optional[int], status: Optional[str]):
    """List all epics."""
    try:
        config = ctx.obj['config']
        db_url = config.get('database.url', 'sqlite:///orchestrator.db')
        state_manager = StateManager.get_instance(db_url)

        # Import models
        from src.core.models import TaskType, TaskStatus
        from sqlalchemy import desc

        # Get all epics
        with state_manager._session_scope() as session:
            query = session.query(Task).filter(
                Task.task_type == TaskType.EPIC,
                Task.is_deleted == False
            )

            if project:
                query = query.filter(Task.project_id == project)
            if status:
                try:
                    query = query.filter(Task.status == TaskStatus[status.upper()])
                except KeyError:
                    click.echo(f"✗ Invalid status: {status}", err=True)
                    sys.exit(1)

            epics = query.order_by(desc(Task.created_at)).all()

        if not epics:
            click.echo("No epics found")
            return

        click.echo(f"\nFound {len(epics)} epic(s):\n")
        for epic in epics:
            stories = state_manager.get_epic_stories(epic.id)
            status_icon = "✓" if epic.status == TaskStatus.COMPLETED else "○"
            click.echo(f"{status_icon} Epic #{epic.id}: {epic.title}")
            click.echo(f"   Status: {epic.status.value} | Priority: {epic.priority}")
            click.echo(f"   Stories: {len(stories)} | Project: #{epic.project_id}")
            click.echo()

    except Exception as e:
        click.echo(f"✗ Failed to list epics: {e}", err=True)
        sys.exit(1)


@epic.command('show')
@click.argument('epic_id', type=int)
@click.pass_context
def epic_show(ctx, epic_id: int):
    """Show detailed epic information."""
    try:
        config = ctx.obj['config']
        db_url = config.get('database.url', 'sqlite:///orchestrator.db')
        state_manager = StateManager.get_instance(db_url)

        from src.core.models import TaskType, TaskStatus

        epic = state_manager.get_task(epic_id)
        if not epic or epic.task_type != TaskType.EPIC:
            click.echo(f"✗ Epic {epic_id} not found", err=True)
            sys.exit(1)

        stories = state_manager.get_epic_stories(epic_id)

        click.echo(f"\n{'='*60}")
        click.echo(f"Epic #{epic.id}: {epic.title}")
        click.echo(f"{'='*60}")
        click.echo(f"Status: {epic.status.value}")
        click.echo(f"Priority: {epic.priority}/10")
        click.echo(f"Project: #{epic.project_id}")
        click.echo(f"Created: {epic.created_at.strftime('%Y-%m-%d %H:%M')}")
        if epic.description:
            click.echo(f"\nDescription:\n{epic.description}")

        click.echo(f"\n{'─'*60}")
        click.echo(f"Stories ({len(stories)}):")
        click.echo(f"{'─'*60}")

        if stories:
            completed = sum(1 for s in stories if s.status == TaskStatus.COMPLETED)
            click.echo(f"Progress: {completed}/{len(stories)} completed\n")

            for story in stories:
                status_icon = "✓" if story.status == TaskStatus.COMPLETED else "○"
                click.echo(f"  {status_icon} Story #{story.id}: {story.title}")
                click.echo(f"     Status: {story.status.value}")
        else:
            click.echo("  No stories yet")

        click.echo()

    except Exception as e:
        click.echo(f"✗ Failed to show epic: {e}", err=True)
        sys.exit(1)


@epic.command('update')
@click.argument('epic_id', type=int)
@click.option('--title', '-t', help='New title')
@click.option('--description', '-d', help='New description')
@click.option('--priority', '-p', type=int, help='New priority (1-10)')
@click.pass_context
def epic_update(ctx, epic_id: int, title: Optional[str], description: Optional[str], priority: Optional[int]):
    """Update an epic."""
    try:
        config = ctx.obj['config']
        db_url = config.get('database.url', 'sqlite:///orchestrator.db')
        state_manager = StateManager.get_instance(db_url)

        from src.core.models import TaskType

        # Verify epic exists
        epic = state_manager.get_task(epic_id)
        if not epic or epic.task_type != TaskType.EPIC:
            click.echo(f"✗ Epic {epic_id} not found", err=True)
            sys.exit(1)

        # Update fields
        updates = {}
        if title:
            updates['title'] = title
        if description is not None:
            updates['description'] = description
        if priority is not None:
            if priority < 1 or priority > 10:
                click.echo("✗ Priority must be between 1 and 10", err=True)
                sys.exit(1)
            updates['priority'] = priority

        if not updates:
            click.echo("✗ No updates specified", err=True)
            sys.exit(1)

        # Update epic
        with state_manager._session_scope() as session:
            for key, value in updates.items():
                setattr(epic, key, value)
            session.commit()

        click.echo(f"✓ Updated epic #{epic_id}")
        for key, value in updates.items():
            click.echo(f"  {key}: {value}")

    except Exception as e:
        click.echo(f"✗ Failed to update epic: {e}", err=True)
        sys.exit(1)


@epic.command('delete')
@click.argument('epic_id', type=int)
@click.option('--hard', is_flag=True, help='Permanently delete (default is soft delete)')
@click.pass_context
def epic_delete(ctx, epic_id: int, hard: bool):
    """Delete an epic."""
    try:
        config = ctx.obj['config']
        db_url = config.get('database.url', 'sqlite:///orchestrator.db')
        state_manager = StateManager.get_instance(db_url)

        from src.core.models import TaskType

        # Verify epic exists
        epic = state_manager.get_task(epic_id)
        if not epic or epic.task_type != TaskType.EPIC:
            click.echo(f"✗ Epic {epic_id} not found", err=True)
            sys.exit(1)

        # Delete epic
        state_manager.delete_task(epic_id, soft=not hard)

        delete_type = "permanently deleted" if hard else "soft deleted"
        click.echo(f"✓ Epic #{epic_id} {delete_type}")

    except Exception as e:
        click.echo(f"✗ Failed to delete epic: {e}", err=True)
        sys.exit(1)


# ============================================================================
# Story Management Commands (ADR-013)
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
@click.pass_context
def story_create(ctx, title: str, epic: int, project: int, description: str):
    """Create a new story under an epic."""
    try:
        config = ctx.obj['config']
        db_url = config.get('database.url', 'sqlite:///orchestrator.db')
        state_manager = StateManager.get_instance(db_url)

        story_id = state_manager.create_story(
            project_id=project,
            epic_id=epic,
            title=title,
            description=description
        )

        click.echo(f"✓ Created story #{story_id}: {title}")
        click.echo(f"  Epic: #{epic}")
        click.echo(f"  Project: #{project}")

    except Exception as e:
        click.echo(f"✗ Failed to create story: {e}", err=True)
        sys.exit(1)


@story.command('list')
@click.option('--epic', '-e', type=int, help='Filter by epic ID')
@click.option('--project', '-p', type=int, help='Filter by project ID')
@click.option('--status', '-s', help='Filter by status (pending, running, completed, failed)')
@click.pass_context
def story_list(ctx, epic: Optional[int], project: Optional[int], status: Optional[str]):
    """List all stories."""
    try:
        config = ctx.obj['config']
        db_url = config.get('database.url', 'sqlite:///orchestrator.db')
        state_manager = StateManager.get_instance(db_url)

        from src.core.models import TaskType, TaskStatus
        from sqlalchemy import desc

        # Get stories
        with state_manager._session_scope() as session:
            query = session.query(Task).filter(
                Task.task_type == TaskType.STORY,
                Task.is_deleted == False
            )

            if epic:
                query = query.filter(Task.epic_id == epic)
            if project:
                query = query.filter(Task.project_id == project)
            if status:
                try:
                    query = query.filter(Task.status == TaskStatus[status.upper()])
                except KeyError:
                    click.echo(f"✗ Invalid status: {status}", err=True)
                    sys.exit(1)

            stories = query.order_by(desc(Task.created_at)).all()

        if not stories:
            click.echo("No stories found")
            return

        click.echo(f"\nFound {len(stories)} story/stories:\n")
        for story in stories:
            status_icon = "✓" if story.status == TaskStatus.COMPLETED else "○"
            click.echo(f"{status_icon} Story #{story.id}: {story.title}")
            click.echo(f"   Status: {story.status.value} | Epic: #{story.epic_id} | Project: #{story.project_id}")
            click.echo()

    except Exception as e:
        click.echo(f"✗ Failed to list stories: {e}", err=True)
        sys.exit(1)


@story.command('show')
@click.argument('story_id', type=int)
@click.pass_context
def story_show(ctx, story_id: int):
    """Show detailed story information."""
    try:
        config = ctx.obj['config']
        db_url = config.get('database.url', 'sqlite:///orchestrator.db')
        state_manager = StateManager.get_instance(db_url)

        from src.core.models import TaskType, TaskStatus

        story = state_manager.get_task(story_id)
        if not story or story.task_type != TaskType.STORY:
            click.echo(f"✗ Story {story_id} not found", err=True)
            sys.exit(1)

        # Get tasks under this story
        tasks = state_manager.get_story_tasks(story_id)

        click.echo(f"\n{'='*60}")
        click.echo(f"Story #{story.id}: {story.title}")
        click.echo(f"{'='*60}")
        click.echo(f"Status: {story.status.value}")
        click.echo(f"Epic: #{story.epic_id}")
        click.echo(f"Project: #{story.project_id}")
        click.echo(f"Created: {story.created_at.strftime('%Y-%m-%d %H:%M')}")
        if story.description:
            click.echo(f"\nDescription:\n{story.description}")

        click.echo(f"\n{'─'*60}")
        click.echo(f"Tasks ({len(tasks)}):")
        click.echo(f"{'─'*60}")

        if tasks:
            completed = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
            click.echo(f"Progress: {completed}/{len(tasks)} completed\n")

            for task in tasks:
                status_icon = "✓" if task.status == TaskStatus.COMPLETED else "○"
                click.echo(f"  {status_icon} Task #{task.id}: {task.title}")
                click.echo(f"     Status: {task.status.value}")
        else:
            click.echo("  No tasks yet")

        click.echo()

    except Exception as e:
        click.echo(f"✗ Failed to show story: {e}", err=True)
        sys.exit(1)


@story.command('update')
@click.argument('story_id', type=int)
@click.option('--title', '-t', help='New title')
@click.option('--description', '-d', help='New description')
@click.pass_context
def story_update(ctx, story_id: int, title: Optional[str], description: Optional[str]):
    """Update a story."""
    try:
        config = ctx.obj['config']
        db_url = config.get('database.url', 'sqlite:///orchestrator.db')
        state_manager = StateManager.get_instance(db_url)

        from src.core.models import TaskType

        # Verify story exists
        story = state_manager.get_task(story_id)
        if not story or story.task_type != TaskType.STORY:
            click.echo(f"✗ Story {story_id} not found", err=True)
            sys.exit(1)

        # Update fields
        updates = {}
        if title:
            updates['title'] = title
        if description is not None:
            updates['description'] = description

        if not updates:
            click.echo("✗ No updates specified", err=True)
            sys.exit(1)

        # Update story
        with state_manager._session_scope() as session:
            for key, value in updates.items():
                setattr(story, key, value)
            session.commit()

        click.echo(f"✓ Updated story #{story_id}")
        for key, value in updates.items():
            click.echo(f"  {key}: {value}")

    except Exception as e:
        click.echo(f"✗ Failed to update story: {e}", err=True)
        sys.exit(1)


@story.command('move')
@click.argument('story_id', type=int)
@click.option('--epic', '-e', type=int, required=True, help='New epic ID')
@click.pass_context
def story_move(ctx, story_id: int, epic: int):
    """Move a story to a different epic."""
    try:
        config = ctx.obj['config']
        db_url = config.get('database.url', 'sqlite:///orchestrator.db')
        state_manager = StateManager.get_instance(db_url)

        from src.core.models import TaskType

        # Verify story exists
        story = state_manager.get_task(story_id)
        if not story or story.task_type != TaskType.STORY:
            click.echo(f"✗ Story {story_id} not found", err=True)
            sys.exit(1)

        # Verify new epic exists
        new_epic = state_manager.get_task(epic)
        if not new_epic or new_epic.task_type != TaskType.EPIC:
            click.echo(f"✗ Epic {epic} not found", err=True)
            sys.exit(1)

        old_epic_id = story.epic_id

        # Move story
        with state_manager._session_scope() as session:
            story.epic_id = epic
            session.commit()

        click.echo(f"✓ Moved story #{story_id} from epic #{old_epic_id} to epic #{epic}")

    except Exception as e:
        click.echo(f"✗ Failed to move story: {e}", err=True)
        sys.exit(1)


# ============================================================================
# Milestone Management Commands (ADR-013)
# ============================================================================

@cli.group()
def milestone():
    """Manage milestones (zero-duration checkpoints)."""
    pass


@milestone.command('create')
@click.argument('name')
@click.option('--project', '-p', type=int, required=True, help='Project ID')
@click.option('--description', '-d', default='', help='Milestone description')
@click.option('--epics', help='Comma-separated epic IDs required for completion')
@click.pass_context
def milestone_create(ctx, name: str, project: int, description: str, epics: Optional[str]):
    """Create a milestone checkpoint."""
    try:
        config = ctx.obj['config']
        db_url = config.get('database.url', 'sqlite:///orchestrator.db')
        state_manager = StateManager.get_instance(db_url)

        required_epic_ids = []
        if epics:
            required_epic_ids = [int(x.strip()) for x in epics.split(',')]

        milestone_id = state_manager.create_milestone(
            project_id=project,
            name=name,
            description=description,
            required_epic_ids=required_epic_ids
        )

        click.echo(f"✓ Created milestone #{milestone_id}: {name}")
        click.echo(f"  Project: #{project}")
        if required_epic_ids:
            click.echo(f"  Required epics: {required_epic_ids}")

    except Exception as e:
        click.echo(f"✗ Failed to create milestone: {e}", err=True)
        sys.exit(1)


@milestone.command('check')
@click.argument('milestone_id', type=int)
@click.pass_context
def milestone_check(ctx, milestone_id: int):
    """Check if milestone requirements are met."""
    try:
        config = ctx.obj['config']
        db_url = config.get('database.url', 'sqlite:///orchestrator.db')
        state_manager = StateManager.get_instance(db_url)

        milestone = state_manager.get_milestone(milestone_id)
        if not milestone:
            click.echo(f"✗ Milestone {milestone_id} not found", err=True)
            sys.exit(1)

        is_complete = state_manager.check_milestone_completion(milestone_id)

        click.echo(f"Milestone #{milestone_id}: {milestone.name}")
        click.echo(f"  Status: {'✓ Complete' if is_complete else '○ Incomplete'}")
        click.echo(f"  Required epics: {milestone.required_epic_ids}")

        if is_complete and not milestone.achieved:
            click.echo("\n  Ready to achieve! Run: obra milestone achieve " + str(milestone_id))

    except Exception as e:
        click.echo(f"✗ Failed to check milestone: {e}", err=True)
        sys.exit(1)


@milestone.command('achieve')
@click.argument('milestone_id', type=int)
@click.pass_context
def milestone_achieve(ctx, milestone_id: int):
    """Mark milestone as achieved."""
    try:
        config = ctx.obj['config']
        db_url = config.get('database.url', 'sqlite:///orchestrator.db')
        state_manager = StateManager.get_instance(db_url)

        # Check completion first
        if not state_manager.check_milestone_completion(milestone_id):
            click.echo(f"✗ Cannot achieve milestone: requirements not met", err=True)
            sys.exit(1)

        state_manager.achieve_milestone(milestone_id)
        click.echo(f"✓ Milestone #{milestone_id} achieved!")

    except Exception as e:
        click.echo(f"✗ Failed to achieve milestone: {e}", err=True)
        sys.exit(1)


@milestone.command('list')
@click.option('--project', '-p', type=int, help='Filter by project ID')
@click.option('--achieved', is_flag=True, help='Show only achieved milestones')
@click.pass_context
def milestone_list(ctx, project: Optional[int], achieved: bool):
    """List all milestones."""
    try:
        config = ctx.obj['config']
        db_url = config.get('database.url', 'sqlite:///orchestrator.db')
        state_manager = StateManager.get_instance(db_url)

        from src.core.models import Milestone
        from sqlalchemy import desc

        # Get milestones
        with state_manager._session_scope() as session:
            query = session.query(Milestone)

            if project:
                query = query.filter(Milestone.project_id == project)
            if achieved:
                query = query.filter(Milestone.achieved_at.isnot(None))

            milestones = query.order_by(desc(Milestone.created_at)).all()

        if not milestones:
            click.echo("No milestones found")
            return

        click.echo(f"\nFound {len(milestones)} milestone(s):\n")
        for ms in milestones:
            status_icon = "✓" if ms.achieved_at else "○"
            click.echo(f"{status_icon} Milestone #{ms.id}: {ms.name}")
            click.echo(f"   Project: #{ms.project_id}")
            if ms.achieved_at:
                click.echo(f"   Achieved: {ms.achieved_at.strftime('%Y-%m-%d %H:%M')}")
            else:
                click.echo(f"   Status: Not achieved")
            click.echo()

    except Exception as e:
        click.echo(f"✗ Failed to list milestones: {e}", err=True)
        sys.exit(1)


@milestone.command('show')
@click.argument('milestone_id', type=int)
@click.pass_context
def milestone_show(ctx, milestone_id: int):
    """Show detailed milestone information."""
    try:
        config = ctx.obj['config']
        db_url = config.get('database.url', 'sqlite:///orchestrator.db')
        state_manager = StateManager.get_instance(db_url)

        from src.core.models import Milestone, TaskStatus

        # Get milestone
        with state_manager._session_scope() as session:
            ms = session.query(Milestone).filter(Milestone.id == milestone_id).first()

        if not ms:
            click.echo(f"✗ Milestone {milestone_id} not found", err=True)
            sys.exit(1)

        click.echo(f"\n{'='*60}")
        click.echo(f"Milestone #{ms.id}: {ms.name}")
        click.echo(f"{'='*60}")
        click.echo(f"Project: #{ms.project_id}")
        click.echo(f"Created: {ms.created_at.strftime('%Y-%m-%d %H:%M')}")
        if ms.achieved_at:
            click.echo(f"Achieved: {ms.achieved_at.strftime('%Y-%m-%d %H:%M')}")
        else:
            click.echo(f"Status: Not achieved")

        if ms.description:
            click.echo(f"\nDescription:\n{ms.description}")

        # Show required epics
        if ms.required_epic_ids:
            click.echo(f"\n{'─'*60}")
            click.echo(f"Required Epics ({len(ms.required_epic_ids)}):")
            click.echo(f"{'─'*60}")

            completed_epics = 0
            for epic_id in ms.required_epic_ids:
                epic = state_manager.get_task(epic_id)
                if epic:
                    status_icon = "✓" if epic.status == TaskStatus.COMPLETED else "○"
                    click.echo(f"  {status_icon} Epic #{epic.id}: {epic.title}")
                    click.echo(f"     Status: {epic.status.value}")
                    if epic.status == TaskStatus.COMPLETED:
                        completed_epics += 1
                else:
                    click.echo(f"  ✗ Epic #{epic_id}: Not found")

            click.echo(f"\nProgress: {completed_epics}/{len(ms.required_epic_ids)} epics completed")
        else:
            click.echo("\nNo required epics")

        click.echo()

    except Exception as e:
        click.echo(f"✗ Failed to show milestone: {e}", err=True)
        sys.exit(1)


@milestone.command('update')
@click.argument('milestone_id', type=int)
@click.option('--name', '-n', help='New name')
@click.option('--description', '-d', help='New description')
@click.pass_context
def milestone_update(ctx, milestone_id: int, name: Optional[str], description: Optional[str]):
    """Update a milestone."""
    try:
        config = ctx.obj['config']
        db_url = config.get('database.url', 'sqlite:///orchestrator.db')
        state_manager = StateManager.get_instance(db_url)

        from src.core.models import Milestone

        # Get milestone
        with state_manager._session_scope() as session:
            ms = session.query(Milestone).filter(Milestone.id == milestone_id).first()

            if not ms:
                click.echo(f"✗ Milestone {milestone_id} not found", err=True)
                sys.exit(1)

            # Update fields
            updates = {}
            if name:
                ms.name = name
                updates['name'] = name
            if description is not None:
                ms.description = description
                updates['description'] = description

            if not updates:
                click.echo("✗ No updates specified", err=True)
                sys.exit(1)

            session.commit()

        click.echo(f"✓ Updated milestone #{milestone_id}")
        for key, value in updates.items():
            click.echo(f"  {key}: {value}")

    except Exception as e:
        click.echo(f"✗ Failed to update milestone: {e}", err=True)
        sys.exit(1)


# ============================================================================
# Orchestrator Control Commands
# ============================================================================

@cli.command()
@click.option('--project', '-p', type=int, help='Run tasks for specific project')
@click.pass_context
def run(ctx, project: Optional[int]):
    """Run orchestrator in continuous mode."""
    try:
        config = ctx.obj['config']

        # Initialize orchestrator
        orchestrator = Orchestrator(config=config)
        orchestrator.initialize()

        click.echo("Starting orchestrator...")
        click.echo("Press Ctrl+C to stop")
        click.echo()

        # Run continuous loop
        try:
            orchestrator.run(project_id=project)
        except KeyboardInterrupt:
            click.echo("\nStopping orchestrator...")

        # Cleanup
        orchestrator.shutdown()
        click.echo("✓ Orchestrator stopped")

    except OrchestratorException as e:
        click.echo(f"✗ Orchestration error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"✗ Failed to run orchestrator: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
def status(ctx):
    """Show orchestrator status."""
    try:
        config = ctx.obj['config']
        db_url = config.get('database.url', 'sqlite:///orchestrator.db')
        state_manager = StateManager.get_instance(db_url)

        # Get basic statistics
        projects = state_manager.list_projects()
        tasks = state_manager.list_tasks()

        pending_tasks = [t for t in tasks if t.status == 'pending']
        in_progress_tasks = [t for t in tasks if t.status == 'in_progress']
        completed_tasks = [t for t in tasks if t.status == 'completed']

        click.echo("\nOrchestrator Status")
        click.echo("=" * 80)
        click.echo(f"Projects: {len(projects)}")
        click.echo(f"Tasks:")
        click.echo(f"  Pending: {len(pending_tasks)}")
        click.echo(f"  In Progress: {len(in_progress_tasks)}")
        click.echo(f"  Completed: {len(completed_tasks)}")
        click.echo(f"  Total: {len(tasks)}")

    except Exception as e:
        click.echo(f"✗ Failed to get status: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
def interactive(ctx):
    """Start interactive REPL mode."""
    try:
        config = ctx.obj['config']

        click.echo("Starting interactive mode...")
        click.echo("Type 'help' for available commands, 'exit' to quit")
        click.echo()

        # Import and run interactive mode
        from src.interactive import InteractiveMode

        interactive_mode = InteractiveMode(config)
        interactive_mode.run()

    except ImportError:
        click.echo("✗ Interactive mode not yet implemented (deliverable 6.3)", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"✗ Failed to start interactive mode: {e}", err=True)
        sys.exit(1)


# ============================================================================
# Configuration Commands
# ============================================================================

@cli.group()
def config():
    """Manage configuration."""
    pass


@config.command('show')
@click.pass_context
def config_show(ctx):
    """Show current configuration."""
    config_mgr = ctx.obj['config']

    click.echo("\nCurrent Configuration:")
    click.echo("=" * 80)

    import yaml
    click.echo(yaml.dump(config_mgr._config, default_flow_style=False))


@config.command('validate')
@click.pass_context
def config_validate(ctx):
    """Validate configuration."""
    try:
        config_mgr = ctx.obj['config']

        # Check required settings
        required = [
            'database.url',
            'agent.type',
            'llm.provider'
        ]

        missing = []
        for key in required:
            if config_mgr.get(key) is None:
                missing.append(key)

        if missing:
            click.echo("✗ Configuration validation failed:", err=True)
            for key in missing:
                click.echo(f"  Missing: {key}", err=True)
            sys.exit(1)

        click.echo("✓ Configuration is valid")

    except Exception as e:
        click.echo(f"✗ Validation failed: {e}", err=True)
        sys.exit(1)


# ============================================================================
# LLM Management Commands
# ============================================================================

@cli.group()
def llm():
    """Manage LLM (Language Model) connections."""
    pass


@llm.command('status')
@click.pass_context
def llm_status(ctx):
    """Check LLM connection status."""
    try:
        config = ctx.obj['config']

        # Get current LLM configuration
        llm_type = config.get('llm.type', 'not configured')
        llm_model = config.get('llm.model', 'not configured')
        llm_endpoint = config.get('llm.api_url') or config.get('llm.endpoint', 'not configured')

        click.echo("\n🔌 LLM Connection Status")
        click.echo("=" * 80)
        click.echo(f"  Type:     {llm_type}")
        click.echo(f"  Model:    {llm_model}")
        click.echo(f"  Endpoint: {llm_endpoint}")
        click.echo()

        # Try to check if LLM is available
        try:
            from src.plugins.registry import LLMRegistry

            llm_class = LLMRegistry.get(llm_type)
            llm_instance = llm_class()

            llm_config = config.get('llm', {})
            if 'api_url' in llm_config and 'endpoint' not in llm_config:
                llm_config['endpoint'] = llm_config['api_url']

            llm_instance.initialize(llm_config)

            if llm_instance.is_available():
                click.echo("✓ Status:   CONNECTED")
                click.echo("✓ LLM is responding and ready to use")
            else:
                click.echo("✗ Status:   UNREACHABLE")
                click.echo("✗ LLM service is not responding")
                click.echo("\nTroubleshooting:")
                click.echo("  - Check that the LLM service is running")
                click.echo(f"  - Verify endpoint is correct: {llm_endpoint}")
                click.echo("  - Check network connectivity")

        except Exception as e:
            click.echo("✗ Status:   ERROR")
            click.echo(f"✗ {e}")
            click.echo("\nTo fix:")
            click.echo("  1. Check configuration: obra config show")
            click.echo("  2. List available LLMs: obra llm list")
            click.echo("  3. Reconnect: obra llm reconnect")

        click.echo()

    except Exception as e:
        click.echo(f"✗ Failed to check status: {e}", err=True)
        sys.exit(1)


@llm.command('list')
@click.pass_context
def llm_list(ctx):
    """List available LLM providers."""
    try:
        from src.plugins.registry import LLMRegistry

        available_llms = LLMRegistry.list()

        click.echo("\n📋 Available LLM Providers")
        click.echo("=" * 80)

        if not available_llms:
            click.echo("  No LLM providers registered")
            click.echo()
            return

        config = ctx.obj['config']
        current_llm = config.get('llm.type', None)

        for llm_name in available_llms:
            is_current = "✓ ACTIVE" if llm_name == current_llm else ""
            click.echo(f"  • {llm_name:20s} {is_current}")

        click.echo()
        click.echo("Configuration examples:")
        click.echo()
        click.echo("  Ollama (local):")
        click.echo("    llm.type: ollama")
        click.echo("    llm.model: qwen2.5-coder:32b")
        click.echo("    llm.api_url: http://localhost:11434")
        click.echo()
        click.echo("  OpenAI Codex (remote):")
        click.echo("    llm.type: openai-codex")
        click.echo("    llm.model: gpt-5-codex")
        click.echo("    llm.timeout: 120")
        click.echo()

    except Exception as e:
        click.echo(f"✗ Failed to list LLMs: {e}", err=True)
        sys.exit(1)


@llm.command('reconnect')
@click.option('--type', '-t', help='LLM type (e.g., ollama, openai-codex)')
@click.option('--model', '-m', help='Model name')
@click.option('--endpoint', '-e', help='API endpoint URL (for ollama)')
@click.option('--timeout', type=int, help='Timeout in seconds')
@click.pass_context
def llm_reconnect(ctx, type: Optional[str], model: Optional[str],
                  endpoint: Optional[str], timeout: Optional[int]):
    """Reconnect to LLM or switch to different provider.

    Examples:

        # Reconnect to current LLM (after it comes online)
        $ obra llm reconnect

        # Switch to OpenAI Codex
        $ obra llm reconnect --type openai-codex --model gpt-5-codex

        # Switch to Ollama
        $ obra llm reconnect --type ollama --endpoint http://localhost:11434
    """
    try:
        config = ctx.obj['config']

        # Build LLM config from options
        llm_config = {}

        if model:
            llm_config['model'] = model
        if endpoint:
            llm_config['endpoint'] = endpoint
            llm_config['api_url'] = endpoint  # Backward compatibility
        if timeout:
            llm_config['timeout'] = timeout

        # Display what we're doing
        if type:
            click.echo(f"\n🔄 Switching to LLM: {type}")
        else:
            current_type = config.get('llm.type', 'unknown')
            click.echo(f"\n🔄 Reconnecting to LLM: {current_type}")

        if llm_config:
            click.echo(f"   Configuration: {llm_config}")

        click.echo()

        # Initialize orchestrator and reconnect
        orchestrator = Orchestrator(config=config)
        orchestrator.initialize()

        # Reconnect with new settings
        success = orchestrator.reconnect_llm(
            llm_type=type,
            llm_config=llm_config if llm_config else None
        )

        if success:
            llm_name = type or config.get('llm.type', 'unknown')
            click.echo(f"✓ Successfully connected to LLM: {llm_name}")
            click.echo()
            click.echo("You can now execute tasks:")
            click.echo("  $ obra task execute <task_id>")
            click.echo("  $ obra run")
            click.echo()
        else:
            click.echo("✗ Failed to connect to LLM", err=True)
            click.echo()
            click.echo("Troubleshooting:")
            click.echo("  1. Check LLM service is running: obra llm status")
            click.echo("  2. List available providers: obra llm list")
            click.echo("  3. Check configuration: obra config show")
            click.echo()
            sys.exit(1)

    except Exception as e:
        click.echo(f"✗ Reconnection failed: {e}", err=True)
        import traceback
        if ctx.obj.get('verbose'):
            traceback.print_exc()
        sys.exit(1)


@llm.command('switch')
@click.argument('llm_type', type=click.Choice(['ollama', 'openai-codex'], case_sensitive=False))
@click.option('--model', '-m', help='Model name')
@click.pass_context
def llm_switch(ctx, llm_type: str, model: Optional[str]):
    """Quick switch between LLM providers (shortcut for reconnect).

    Examples:

        # Switch to Ollama
        $ obra llm switch ollama

        # Switch to OpenAI Codex with specific model
        $ obra llm switch openai-codex --model gpt-5-codex
    """
    try:
        config = ctx.obj['config']

        click.echo(f"\n🔄 Switching to {llm_type}")
        if model:
            click.echo(f"   Model: {model}")
        else:
            click.echo(f"   Using plugin's default model")
        click.echo()

        # Build config - only add model if explicitly specified
        # Otherwise, let the plugin use its own DEFAULT_CONFIG
        llm_config = {}
        if model:
            llm_config['model'] = model

        # Add default endpoints
        if llm_type == 'ollama':
            llm_config['endpoint'] = config.get('llm.api_url', 'http://localhost:11434')
            llm_config['api_url'] = llm_config['endpoint']

        # Initialize orchestrator and reconnect
        orchestrator = Orchestrator(config=config)
        orchestrator.initialize()

        success = orchestrator.reconnect_llm(
            llm_type=llm_type,
            llm_config=llm_config
        )

        if success:
            click.echo(f"✓ Successfully switched to {llm_type}")
            click.echo()
        else:
            click.echo(f"✗ Failed to switch to {llm_type}", err=True)
            sys.exit(1)

    except Exception as e:
        click.echo(f"✗ Switch failed: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    cli()
