"""Interactive REPL mode for Claude Code Orchestrator.

Provides a continuous interactive shell for managing projects, tasks,
and orchestrator operations.

Usage:
    >>> from src.interactive import InteractiveMode
    >>> mode = InteractiveMode(config)
    >>> mode.run()
"""

import logging
import shlex
from typing import Optional, List, Dict, Any
from datetime import datetime

from src.orchestrator import Orchestrator
from src.core.config import Config
from src.core.state import StateManager
from src.core.exceptions import OrchestratorException

logger = logging.getLogger(__name__)


class InteractiveMode:
    """Interactive REPL for orchestrator control.

    Provides a command-line shell for continuous interaction with the orchestrator.

    Example:
        >>> mode = InteractiveMode(config)
        >>> mode.run()
        orchestrator> help
        orchestrator> project create "My Project"
        orchestrator> task create "Implement X"
        orchestrator> execute 1
        orchestrator> exit
    """

    def __init__(self, config: Config):
        """Initialize interactive mode.

        Args:
            config: Configuration instance
        """
        self.config = config
        self.orchestrator: Optional[Orchestrator] = None
        self.state_manager: Optional[StateManager] = None
        self.current_project: Optional[int] = None
        self.running = False

        # Command history
        self.history: List[str] = []

        # Command mapping
        self.commands = {
            'help': self.cmd_help,
            'exit': self.cmd_exit,
            'quit': self.cmd_exit,
            'project': self.cmd_project,
            'task': self.cmd_task,
            'execute': self.cmd_execute,
            'run': self.cmd_run,
            'stop': self.cmd_stop,
            'status': self.cmd_status,
            'use': self.cmd_use,
            'history': self.cmd_history,
            'clear': self.cmd_clear
        }

    def run(self) -> None:
        """Run the interactive REPL loop."""
        self.running = True

        # Initialize components
        try:
            db_url = self.config.get('database.url', 'sqlite:///orchestrator.db')
            self.state_manager = StateManager.get_instance(db_url)

            self.orchestrator = Orchestrator(config=self.config)
            self.orchestrator.initialize()

            print("✓ Orchestrator initialized")
            print()
            self._show_welcome()

        except Exception as e:
            print(f"✗ Failed to initialize: {e}")
            return

        # Main REPL loop
        while self.running:
            try:
                # Show prompt
                if self.current_project:
                    prompt = f"orchestrator[project:{self.current_project}]> "
                else:
                    prompt = "orchestrator> "

                # Get input
                user_input = input(prompt).strip()

                if not user_input:
                    continue

                # Add to history
                self.history.append(user_input)

                # Parse and execute command
                self._execute_command(user_input)

            except KeyboardInterrupt:
                print("\nUse 'exit' to quit")
                continue
            except EOFError:
                print()
                break
            except Exception as e:
                logger.error(f"Command error: {e}", exc_info=True)
                print(f"✗ Error: {e}")

        # Cleanup
        if self.orchestrator:
            self.orchestrator.shutdown()

        print("Goodbye!")

    def _show_welcome(self) -> None:
        """Show welcome message."""
        print("=" * 80)
        print("Claude Code Orchestrator - Interactive Mode")
        print("=" * 80)
        print()
        print("Type 'help' for available commands")
        print()

    def _execute_command(self, user_input: str) -> None:
        """Parse and execute a command.

        Args:
            user_input: User's input string
        """
        # Parse command
        try:
            parts = shlex.split(user_input)
        except ValueError:
            print("✗ Invalid command syntax")
            return

        if not parts:
            return

        command = parts[0].lower()
        args = parts[1:]

        # Execute command
        if command in self.commands:
            try:
                self.commands[command](args)
            except Exception as e:
                print(f"✗ Command failed: {e}")
        else:
            print(f"✗ Unknown command: {command}")
            print("Type 'help' for available commands")

    # ========================================================================
    # Built-in Commands
    # ========================================================================

    def cmd_help(self, args: List[str]) -> None:
        """Show help message."""
        print("\nAvailable Commands:")
        print("=" * 80)
        print()

        print("General:")
        print("  help                    - Show this help message")
        print("  exit, quit              - Exit interactive mode")
        print("  history                 - Show command history")
        print("  clear                   - Clear screen")
        print()

        print("Project Management:")
        print("  project create <name>   - Create a new project")
        print("  project list            - List all projects")
        print("  project show <id>       - Show project details")
        print("  use <project_id>        - Set current project")
        print()

        print("Task Management:")
        print("  task create <title>     - Create task (requires current project)")
        print("  task list               - List tasks")
        print("  task show <id>          - Show task details")
        print()

        print("Execution:")
        print("  execute <task_id>       - Execute a single task")
        print("  run                     - Run orchestrator continuously")
        print("  stop                    - Stop continuous run")
        print("  status                  - Show orchestrator status")
        print()

    def cmd_exit(self, args: List[str]) -> None:
        """Exit interactive mode."""
        self.running = False

    def cmd_history(self, args: List[str]) -> None:
        """Show command history."""
        if not self.history:
            print("No command history")
            return

        print("\nCommand History:")
        for i, cmd in enumerate(self.history, 1):
            print(f"  {i}: {cmd}")

    def cmd_clear(self, args: List[str]) -> None:
        """Clear screen."""
        import os
        os.system('clear' if os.name != 'nt' else 'cls')

    # ========================================================================
    # Project Commands
    # ========================================================================

    def cmd_project(self, args: List[str]) -> None:
        """Handle project subcommands.

        Args:
            args: Subcommand and arguments
        """
        if not args:
            print("Usage: project <create|list|show> [args]")
            return

        subcommand = args[0].lower()

        if subcommand == 'create':
            self._project_create(args[1:])
        elif subcommand == 'list':
            self._project_list()
        elif subcommand == 'show':
            self._project_show(args[1:])
        else:
            print(f"✗ Unknown project subcommand: {subcommand}")

    def _project_create(self, args: List[str]) -> None:
        """Create a new project."""
        if not args:
            print("Usage: project create <name>")
            return

        name = args[0]
        description = ' '.join(args[1:]) if len(args) > 1 else ''

        try:
            from pathlib import Path
            project_data = {
                'name': name,
                'description': description,
                'working_dir': str(Path.cwd())
            }

            project = self.state_manager.create_project(project_data)
            print(f"✓ Created project #{project.id}: {name}")

            # Auto-select new project
            self.current_project = project.id

        except Exception as e:
            print(f"✗ Failed to create project: {e}")

    def _project_list(self) -> None:
        """List all projects."""
        try:
            projects = self.state_manager.list_projects()

            if not projects:
                print("No projects found")
                return

            print("\nProjects:")
            print("-" * 80)
            for p in projects:
                current = " (current)" if p.id == self.current_project else ""
                print(f"  #{p.id}: {p.name}{current}")
                print(f"       {p.description}")
                print(f"       Status: {p.status}")
                print()

        except Exception as e:
            print(f"✗ Failed to list projects: {e}")

    def _project_show(self, args: List[str]) -> None:
        """Show project details."""
        if not args:
            print("Usage: project show <id>")
            return

        try:
            project_id = int(args[0])
            project = self.state_manager.get_project(project_id)

            if not project:
                print(f"✗ Project #{project_id} not found")
                return

            print(f"\nProject #{project.id}: {project.name}")
            print("=" * 80)
            print(f"Description: {project.description}")
            print(f"Working directory: {project.working_dir}")
            print(f"Status: {project.status}")
            print(f"Created: {project.created_at}")
            print(f"Updated: {project.updated_at}")

            # Show tasks
            tasks = self.state_manager.get_project_tasks(project_id)
            print(f"\nTasks ({len(tasks)}):")
            for task in tasks:
                print(f"  #{task.id}: {task.title} [{task.status}]")

        except ValueError:
            print("✗ Invalid project ID")
        except Exception as e:
            print(f"✗ Failed to show project: {e}")

    # ========================================================================
    # Task Commands
    # ========================================================================

    def cmd_task(self, args: List[str]) -> None:
        """Handle task subcommands.

        Args:
            args: Subcommand and arguments
        """
        if not args:
            print("Usage: task <create|list|show> [args]")
            return

        subcommand = args[0].lower()

        if subcommand == 'create':
            self._task_create(args[1:])
        elif subcommand == 'list':
            self._task_list()
        elif subcommand == 'show':
            self._task_show(args[1:])
        else:
            print(f"✗ Unknown task subcommand: {subcommand}")

    def _task_create(self, args: List[str]) -> None:
        """Create a new task."""
        if not self.current_project:
            print("✗ No project selected. Use 'use <project_id>' first")
            return

        if not args:
            print("Usage: task create <title>")
            return

        title = ' '.join(args)

        try:
            task_data = {
                'title': title,
                'description': '',
                'priority': 5,
                'status': 'pending'
            }

            task = self.state_manager.create_task(self.current_project, task_data)
            print(f"✓ Created task #{task.id}: {title}")

        except Exception as e:
            print(f"✗ Failed to create task: {e}")

    def _task_list(self) -> None:
        """List tasks."""
        try:
            if self.current_project:
                tasks = self.state_manager.get_project_tasks(self.current_project)
            else:
                tasks = self.state_manager.list_tasks()

            if not tasks:
                print("No tasks found")
                return

            print("\nTasks:")
            print("-" * 80)
            for t in tasks:
                print(f"  #{t.id}: {t.title} [{t.status}]")
                print(f"       Project: #{t.project_id} | Priority: {t.priority}")
                print()

        except Exception as e:
            print(f"✗ Failed to list tasks: {e}")

    def _task_show(self, args: List[str]) -> None:
        """Show task details."""
        if not args:
            print("Usage: task show <id>")
            return

        try:
            task_id = int(args[0])
            task = self.state_manager.get_task(task_id)

            if not task:
                print(f"✗ Task #{task_id} not found")
                return

            print(f"\nTask #{task.id}: {task.title}")
            print("=" * 80)
            print(f"Description: {task.description}")
            print(f"Project: #{task.project_id}")
            print(f"Status: {task.status}")
            print(f"Priority: {task.priority}")
            print(f"Created: {task.created_at}")
            print(f"Updated: {task.updated_at}")

        except ValueError:
            print("✗ Invalid task ID")
        except Exception as e:
            print(f"✗ Failed to show task: {e}")

    # ========================================================================
    # Execution Commands
    # ========================================================================

    def cmd_execute(self, args: List[str]) -> None:
        """Execute a single task.

        Args:
            args: Task ID
        """
        if not args:
            print("Usage: execute <task_id>")
            return

        try:
            task_id = int(args[0])

            print(f"Executing task #{task_id}...")

            result = self.orchestrator.execute_task(task_id, max_iterations=10)

            # Display results
            print("\n" + "=" * 80)
            print(f"Task #{task_id} execution result:")
            print("=" * 80)
            print(f"Status: {result['status']}")
            print(f"Iterations: {result['iterations']}")

            if 'quality_score' in result:
                print(f"Quality Score: {result['quality_score']:.2f}")
            if 'confidence' in result:
                print(f"Confidence: {result['confidence']:.2f}")

            if result['status'] == 'completed':
                print("\n✓ Task completed successfully!")
            elif result['status'] == 'escalated':
                print(f"\n⚠ Task escalated: {result.get('reason', 'Unknown')}")
            else:
                print(f"\n✗ Task did not complete: {result.get('message', '')}")

        except ValueError:
            print("✗ Invalid task ID")
        except OrchestratorException as e:
            print(f"✗ Orchestration error: {e}")
            if e.recovery:
                print(f"  Recovery: {e.recovery}")
        except Exception as e:
            print(f"✗ Failed to execute task: {e}")

    def cmd_run(self, args: List[str]) -> None:
        """Run orchestrator in continuous mode."""
        print("Starting continuous run...")
        print("Press Ctrl+C to stop")
        print()

        try:
            self.orchestrator.run(project_id=self.current_project)
        except KeyboardInterrupt:
            print("\nStopped by user")

    def cmd_stop(self, args: List[str]) -> None:
        """Stop continuous run."""
        if self.orchestrator:
            self.orchestrator.stop()
            print("✓ Stopped")

    def cmd_status(self, args: List[str]) -> None:
        """Show orchestrator status."""
        try:
            # Get orchestrator status
            if self.orchestrator:
                status = self.orchestrator.get_status()

                print("\nOrchestrator Status:")
                print("=" * 80)
                print(f"State: {status['state']}")
                print(f"Current Task: {status['current_task']}")
                print(f"Current Project: {status['current_project']}")
                print(f"Iteration Count: {status['iteration_count']}")

                if status['uptime_seconds']:
                    uptime_min = status['uptime_seconds'] / 60
                    print(f"Uptime: {uptime_min:.1f} minutes")

                print("\nComponents:")
                for name, available in status['components'].items():
                    status_str = "✓" if available else "✗"
                    print(f"  {status_str} {name}")

            # Get task statistics
            tasks = self.state_manager.list_tasks()
            pending = len([t for t in tasks if t.status == 'pending'])
            in_progress = len([t for t in tasks if t.status == 'in_progress'])
            completed = len([t for t in tasks if t.status == 'completed'])

            print("\nTasks:")
            print(f"  Pending: {pending}")
            print(f"  In Progress: {in_progress}")
            print(f"  Completed: {completed}")
            print(f"  Total: {len(tasks)}")

        except Exception as e:
            print(f"✗ Failed to get status: {e}")

    def cmd_use(self, args: List[str]) -> None:
        """Set current project.

        Args:
            args: Project ID
        """
        if not args:
            print("Usage: use <project_id>")
            return

        try:
            project_id = int(args[0])
            project = self.state_manager.get_project(project_id)

            if not project:
                print(f"✗ Project #{project_id} not found")
                return

            self.current_project = project_id
            print(f"✓ Using project #{project_id}: {project.name}")

        except ValueError:
            print("✗ Invalid project ID")
        except Exception as e:
            print(f"✗ Failed to set project: {e}")
