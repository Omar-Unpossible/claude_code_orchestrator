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
            'clear': self.cmd_clear,
            '/to-orch': self.cmd_to_orch,
            '/to-obra': self.cmd_to_orch,  # Alias
            '/to-impl': self.cmd_to_impl,
            '/to-claude': self.cmd_to_impl,  # Alias
            'llm': self.cmd_llm,
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
        """Show welcome message (v1.5.0)."""
        print("=" * 80)
        print("Claude Code Orchestrator - Interactive Mode (v1.5.0)")
        print("=" * 80)
        print()
        print("💬 Type naturally to talk to the orchestrator")
        print("⚡ Use built-in commands: help, project, task, execute, status")
        print("🔧 Slash commands: /to-impl, /to-orch (prefix with /)")
        print()

    def _execute_command(self, user_input: str) -> None:
        """Parse and execute a command (v1.5.0: Natural language routing).

        v1.5.0 Behavior:
        - Input starting with '/' → Slash command (must be valid)
        - Input NOT starting with '/' → Check if it's a built-in command, else send to orchestrator

        Args:
            user_input: User's input string
        """
        user_input = user_input.strip()
        if not user_input:
            return

        # v1.5.0: Check if it's a slash command
        if user_input.startswith('/'):
            # Parse slash command
            try:
                parts = shlex.split(user_input)
            except ValueError:
                print("✗ Invalid command syntax")
                return

            command = parts[0].lower()
            args = parts[1:]

            # Execute slash command
            if command in self.commands:
                try:
                    self.commands[command](args)
                except Exception as e:
                    print(f"✗ Command failed: {e}")
            else:
                print(f"✗ Unknown slash command: {command}")
                print("Type /help for available slash commands")
        else:
            # Not a slash command - parse normally
            try:
                parts = shlex.split(user_input)
            except ValueError:
                print("✗ Invalid command syntax")
                return

            if not parts:
                return

            command = parts[0].lower()
            args = parts[1:]

            # Check if it's a built-in command (help, exit, project, task, etc.)
            if command in self.commands and not command.startswith('/'):
                try:
                    self.commands[command](args)
                except Exception as e:
                    print(f"✗ Command failed: {e}")
            else:
                # Not a built-in command - route to orchestrator (v1.5.0)
                print(f"→ Routing to orchestrator: {user_input}")
                self.cmd_to_orch([user_input])

    # ========================================================================
    # Built-in Commands
    # ========================================================================

    def cmd_help(self, args: List[str]) -> None:
        """Show help message (v1.5.0)."""
        print("\nAvailable Commands (v1.5.0):")
        print("=" * 80)
        print()

        print("💬 Natural Language (v1.5.0 - NEW DEFAULT!):")
        print("  <any natural text>      - Automatically sent to orchestrator for guidance")
        print("  Examples:")
        print("    Display the current project and plan")
        print("    How should I break down my authentication feature?")
        print("    What's the status of my tasks?")
        print()

        print("⚡ General Commands:")
        print("  help                    - Show this help message")
        print("  exit, quit              - Exit interactive mode")
        print("  history                 - Show command history")
        print("  clear                   - Clear screen")
        print()

        print("🔧 Slash Commands (must start with /):")
        print("  /to-orch <message>      - Explicitly send to orchestrator LLM")
        print("  /to-impl <message>      - Send task directly to Claude Code agent")
        print("  Examples:")
        print("    /to-impl Create a README.md for this project")
        print("    /to-orch Analyze the quality of the last response")
        print()

        print("🔌 LLM Management:")
        print("  llm show                - Show current LLM provider and model")
        print("  llm list                - List available LLM providers")
        print("  llm switch <provider>   - Switch LLM provider (ollama, openai-codex)")
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

        print("Interactive Task Execution Commands:")
        print("  Additional commands during 'execute <id> --interactive':")
        print("    /pause                    - Pause execution")
        print("    /resume                   - Resume paused execution")
        print("    /override-decision <dec>  - Override decision (proceed/retry/clarify/escalate)")
        print("    /stop                     - Stop execution gracefully")
        print("  Note: /to-orch and /to-impl work both in REPL and during execution!")
        print()

        print("CLI-Only Commands (exit and use CLI):")
        print("  Epic Management:")
        print("    python -m src.cli epic create/list/show/execute")
        print("  Story Management:")
        print("    python -m src.cli story create/list/show/move")
        print("  Milestone Management:")
        print("    python -m src.cli milestone create/check/achieve/list")
        print()
        print("  Tip: Run 'python -m src.cli <command> --help' for detailed usage")
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
                print(f"  #{p.id}: {p.project_name}{current}")
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

            print(f"\nProject #{project.id}: {project.project_name}")
            print("=" * 80)
            print(f"Description: {project.description}")
            print(f"Working directory: {project.working_directory}")
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
            print(f"✓ Using project #{project_id}: {project.project_name}")

        except ValueError:
            print("✗ Invalid project ID")
        except Exception as e:
            print(f"✗ Failed to set project: {e}")

    def cmd_to_orch(self, args: List[str]) -> None:
        """Send natural language message to orchestrator's LLM.

        Args:
            args: Message to send (space-separated words)
        """
        if not args:
            print("Usage: /to-orch <your message>")
            print("Example: /to-orch How should I structure my Tetris game tasks?")
            return

        try:
            message = ' '.join(args)
            print(f"\n[You → Orchestrator]: {message}")
            print("\n[Orchestrator thinking...]")

            # Send to orchestrator's LLM
            if not self.orchestrator or not hasattr(self.orchestrator, 'llm_interface'):
                print("✗ Orchestrator LLM not available")
                return

            # Create a conversational prompt
            prompt = f"""You are Obra, the Claude Code Orchestrator assistant. The user is in the interactive REPL and has asked you:

"{message}"

Provide a helpful, concise response. You can:
- Answer questions about Obra features and workflows
- Help plan work breakdown (epics, stories, tasks)
- Suggest task dependencies and execution order
- Explain best practices for orchestration
- Analyze project structure and suggest improvements

Keep responses clear and actionable. If recommending commands, show the exact syntax."""

            response = self.orchestrator.llm_interface.send_prompt(prompt)

            print(f"\n[Orchestrator]: {response}\n")

        except Exception as e:
            print(f"\n✗ Failed to communicate with orchestrator: {e}\n")
            logger.exception("Error in /to-orch command")

    def cmd_to_impl(self, args: List[str]) -> None:
        """Send natural language message to Claude Code agent.

        Args:
            args: Message to send (space-separated words)
        """
        if not args:
            print("Usage: /to-impl <your message>")
            print("Example: /to-impl Create a README for my Tetris project")
            return

        if not self.current_project:
            print("✗ No project selected. Use 'use <project_id>' first")
            return

        try:
            message = ' '.join(args)
            print(f"\n[You → Claude Code]: {message}")
            print("\n[Claude Code working...]")

            # Get project info for context
            project = self.state_manager.get_project(self.current_project)
            if not project:
                print(f"✗ Project #{self.current_project} not found")
                return

            # Send directly to agent
            if not self.orchestrator or not hasattr(self.orchestrator, 'agent'):
                print("✗ Agent not available")
                return

            # Invoke agent with the message
            agent_response = self.orchestrator.agent.send_prompt(
                prompt=message,
                context={'working_dir': project.working_directory}
            )

            print(f"\n[Claude Code]: Task started\n")
            print(agent_response)
            print()

        except Exception as e:
            print(f"\n✗ Failed to communicate with agent: {e}\n")
            logger.exception("Error in /to-impl command")

    def cmd_llm(self, args: List[str]) -> None:
        """Manage LLM provider and model selection.

        Args:
            args: Subcommand and arguments
        """
        if not args:
            print("Usage: llm <show|list|switch> [provider] [model]")
            print("\nExamples:")
            print("  llm show                        - Show current LLM info")
            print("  llm list                        - List available LLM providers")
            print("  llm switch ollama               - Switch to Ollama (keeps current model)")
            print("  llm switch ollama qwen2.5-coder:7b  - Switch to Ollama with specific model")
            print("  llm switch openai-codex gpt-4   - Switch to OpenAI Codex with GPT-4")
            return

        subcommand = args[0].lower()

        if subcommand == 'show':
            self._llm_show()
        elif subcommand == 'list':
            self._llm_list()
        elif subcommand == 'switch':
            if len(args) < 2:
                print("✗ Usage: llm switch <provider> [model]")
                return
            provider = args[1]
            model = args[2] if len(args) > 2 else None
            self._llm_switch(provider, model)
        else:
            print(f"✗ Unknown llm subcommand: {subcommand}")
            print("Valid subcommands: show, list, switch")

    def _llm_show(self) -> None:
        """Show current LLM provider and model."""
        try:
            if not self.orchestrator or not hasattr(self.orchestrator, 'llm_interface'):
                print("✗ LLM not initialized")
                return

            llm = self.orchestrator.llm_interface

            # Get provider type from config
            provider = self.config.get('llm.type', 'unknown')
            model = self.config.get('llm.model', 'unknown')

            print("\nCurrent LLM Configuration:")
            print("=" * 60)
            print(f"Provider: {provider}")
            print(f"Model: {model}")

            if provider == 'ollama':
                api_url = self.config.get('llm.api_url', 'unknown')
                temperature = self.config.get('llm.temperature', 'unknown')
                print(f"API URL: {api_url}")
                print(f"Temperature: {temperature}")
            elif provider == 'openai-codex':
                temperature = self.config.get('llm.temperature', 'unknown')
                print(f"Temperature: {temperature}")

            print()

        except Exception as e:
            print(f"✗ Failed to show LLM info: {e}")
            logger.exception("Error in llm show")

    def _llm_list(self) -> None:
        """List available LLM providers."""
        try:
            from src.plugins.registry import LLMRegistry

            providers = LLMRegistry.list()

            print("\nAvailable LLM Providers:")
            print("=" * 60)
            for provider in providers:
                print(f"  • {provider}")

            print("\nCommon Models:")
            print("  Ollama:")
            print("    - qwen2.5-coder:32b (recommended, 32B params)")
            print("    - qwen2.5-coder:7b (faster, 7B params)")
            print("    - codellama:13b")
            print("    - deepseek-coder:6.7b")
            print("  OpenAI Codex:")
            print("    - gpt-4 (most capable)")
            print("    - gpt-3.5-turbo (faster, cheaper)")
            print()

        except Exception as e:
            print(f"✗ Failed to list LLMs: {e}")
            logger.exception("Error in llm list")

    def _llm_switch(self, provider: str, model: Optional[str]) -> None:
        """Switch to a different LLM provider/model.

        Args:
            provider: LLM provider name (ollama, openai-codex)
            model: Optional model name
        """
        try:
            from src.plugins.registry import LLMRegistry
            from src.plugins.exceptions import PluginNotFoundError

            # Validate provider exists
            try:
                LLMRegistry.get(provider)
            except PluginNotFoundError:
                print(f"✗ Unknown LLM provider: {provider}")
                print(f"Available: {LLMRegistry.list()}")
                return

            # Update config
            self.config._config['llm']['type'] = provider
            if model:
                self.config._config['llm']['model'] = model

            # Reinitialize LLM
            print(f"\n[Switching to {provider}" + (f" with model {model}" if model else "") + "...]")

            llm_config = self.config.get('llm', {})
            llm_class = LLMRegistry.get(provider)

            # Create new instance
            new_llm = llm_class()
            new_llm.initialize(llm_config)

            # Replace in orchestrator
            self.orchestrator.llm_interface = new_llm
            self.orchestrator.context_manager.llm_interface = new_llm
            self.orchestrator.confidence_scorer.llm_interface = new_llm

            # Update prompt generator
            if hasattr(self.orchestrator, 'prompt_generator'):
                self.orchestrator.prompt_generator.llm_interface = new_llm

            print(f"✓ Switched to {provider}" + (f" ({model})" if model else ""))
            print(f"  /to-orch will now use this LLM")
            print()

        except Exception as e:
            print(f"\n✗ Failed to switch LLM: {e}\n")
            logger.exception("Error in llm switch")
