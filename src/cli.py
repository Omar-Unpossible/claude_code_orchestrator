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
@click.pass_context
def task_execute(ctx, task_id: int, max_iterations: int):
    """Execute a single task."""
    try:
        config = ctx.obj['config']

        # Initialize orchestrator
        orchestrator = Orchestrator(config=config)
        orchestrator.initialize()

        click.echo(f"Executing task #{task_id}...")

        # Execute task
        result = orchestrator.execute_task(task_id, max_iterations=max_iterations)

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


if __name__ == '__main__':
    cli()
