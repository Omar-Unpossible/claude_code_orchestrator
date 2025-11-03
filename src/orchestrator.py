"""Main orchestration loop integrating all components.

This module implements the Orchestrator class that coordinates all components
to execute tasks autonomously with Claude Code.

Example:
    >>> config = Config.load("config/config.yaml")
    >>> orchestrator = Orchestrator(config=config)
    >>> orchestrator.initialize()
    >>> result = orchestrator.execute_task(task_id=1)
"""

import logging
import time
from datetime import datetime, UTC
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional, List
from threading import RLock

from src.core.config import Config
from src.core.state import StateManager
from src.core.models import Task, ProjectState
from src.core.exceptions import OrchestratorException

# Component imports
from src.plugins.registry import AgentRegistry, LLMRegistry
import src.agents  # Import to register agent plugins
from src.llm.local_interface import LocalLLMInterface
from src.llm.response_validator import ResponseValidator
from src.llm.prompt_generator import PromptGenerator
from src.monitoring.file_watcher import FileWatcher
from src.orchestration.task_scheduler import TaskScheduler
from src.orchestration.breakpoint_manager import BreakpointManager
from src.orchestration.decision_engine import DecisionEngine
from src.orchestration.quality_controller import QualityController
from src.utils.token_counter import TokenCounter
from src.utils.context_manager import ContextManager
from src.utils.confidence_scorer import ConfidenceScorer

logger = logging.getLogger(__name__)


class OrchestratorState(Enum):
    """Orchestrator lifecycle states."""
    UNINITIALIZED = "uninitialized"
    INITIALIZED = "initialized"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


class Orchestrator:
    """Main orchestration loop coordinating all components.

    Integrates all M0-M5 components to execute tasks autonomously.
    Handles the complete lifecycle: prompt generation, agent execution,
    validation, quality control, and decision making.

    Thread-safe for concurrent access.

    Example:
        >>> config = Config.load("config.yaml")
        >>> orch = Orchestrator(config)
        >>> orch.initialize()
        >>>
        >>> # Execute a task
        >>> result = orch.execute_task(task_id=1)
        >>>
        >>> # Or run continuous loop
        >>> orch.run()
    """

    def __init__(
        self,
        config: Optional[Config] = None,
        config_path: Optional[str] = None
    ):
        """Initialize orchestrator.

        Args:
            config: Optional Config instance
            config_path: Optional path to config file
        """
        # Load configuration
        if config:
            self.config = config
        elif config_path:
            self.config = Config.load(config_path)
        else:
            self.config = Config()

        self._state = OrchestratorState.UNINITIALIZED
        self._lock = RLock()

        # Components (initialized in initialize())
        self.state_manager: Optional[StateManager] = None
        self.agent = None
        self.llm_interface: Optional[LocalLLMInterface] = None
        self.prompt_generator: Optional[PromptGenerator] = None
        self.response_validator: Optional[ResponseValidator] = None
        self.file_watcher: Optional[FileWatcher] = None
        self.task_scheduler: Optional[TaskScheduler] = None
        self.breakpoint_manager: Optional[BreakpointManager] = None
        self.decision_engine: Optional[DecisionEngine] = None
        self.quality_controller: Optional[QualityController] = None
        self.token_counter: Optional[TokenCounter] = None
        self.context_manager: Optional[ContextManager] = None
        self.confidence_scorer: Optional[ConfidenceScorer] = None

        # Runtime state
        self.current_project: Optional[ProjectState] = None
        self.current_task: Optional[Task] = None
        self._iteration_count = 0
        self._start_time: Optional[datetime] = None

        logger.info("Orchestrator created")

    def _print_obra(self, message: str, prefix: str = "[OBRA]") -> None:
        """Print Obra action/status with colored prefix.

        Args:
            message: Message to display
            prefix: Prefix to use (default: [OBRA], can be [OBRA→CLAUDE])
        """
        # Blue color for Obra output
        print(f"\033[34m{prefix}\033[0m {message}")

    def _print_qwen(self, message: str) -> None:
        """Print Qwen validation output with colored [QWEN] prefix.

        Args:
            message: Message to display
        """
        # Yellow color for Qwen output
        print(f"\033[33m[QWEN]\033[0m {message}")

    def initialize(self) -> None:
        """Initialize all components.

        Must be called before execute_task() or run().

        Raises:
            OrchestratorException: If initialization fails
        """
        with self._lock:
            if self._state != OrchestratorState.UNINITIALIZED:
                logger.warning(f"Already initialized (state: {self._state})")
                return

            try:
                logger.info("Initializing orchestrator...")

                # Initialize core components
                self._initialize_state_manager()
                self._initialize_utilities()
                self._initialize_llm()
                self._initialize_agent()
                self._initialize_orchestration()
                self._initialize_monitoring()

                self._state = OrchestratorState.INITIALIZED
                logger.info("Orchestrator initialized successfully")

            except Exception as e:
                self._state = OrchestratorState.ERROR
                logger.error(f"Initialization failed: {e}", exc_info=True)
                raise OrchestratorException(
                    f"Failed to initialize orchestrator: {e}",
                    context={'error': str(e)},
                    recovery="Check configuration and dependencies"
                )

    def _initialize_state_manager(self) -> None:
        """Initialize state manager."""
        db_url = self.config.get('database.url', 'sqlite:///orchestrator.db')
        self.state_manager = StateManager.get_instance(db_url)
        logger.info(f"StateManager initialized: {db_url}")

    def _initialize_utilities(self) -> None:
        """Initialize utility components."""
        self.token_counter = TokenCounter(
            config=self.config.get('utils.token_counter', {})
        )
        self.context_manager = ContextManager(
            self.token_counter,
            config=self.config.get('utils.context_manager', {})
        )
        self.confidence_scorer = ConfidenceScorer(
            config=self.config.get('utils.confidence_scorer', {})
        )
        logger.info("Utilities initialized")

    def _initialize_llm(self) -> None:
        """Initialize LLM interface."""
        llm_config = self.config.get('llm', {})

        # Map api_url to endpoint for LocalLLMInterface compatibility
        if 'api_url' in llm_config and 'endpoint' not in llm_config:
            llm_config['endpoint'] = llm_config['api_url']

        # Create instance then initialize with config
        self.llm_interface = LocalLLMInterface()
        self.llm_interface.initialize(llm_config)

        # Set LLM for components that need it
        self.context_manager.llm_interface = self.llm_interface
        self.confidence_scorer.llm_interface = self.llm_interface

        # Initialize prompt generator and validator
        template_dir = self.config.get('prompt.template_dir', 'config')
        self.prompt_generator = PromptGenerator(
            template_dir=template_dir,
            llm_interface=self.llm_interface,
            state_manager=self.state_manager
        )
        self.response_validator = ResponseValidator()

        logger.info("LLM components initialized")

    def _initialize_agent(self) -> None:
        """Initialize agent from registry."""
        agent_type = self.config.get('agent.type', 'mock')

        # Get agent config - try agent.config first (nested), then entire agent dict
        agent_config = self.config.get('agent.config')
        if agent_config is None:
            # Fall back to entire agent section (excluding 'type')
            agent_config = self.config.get('agent', {}).copy()
            agent_config.pop('type', None)  # Remove type field

        try:
            agent_class = AgentRegistry.get(agent_type)
            self.agent = agent_class()
            self.agent.initialize(agent_config)
            logger.info(f"Agent initialized: {agent_type}")
        except Exception as e:
            logger.warning(f"Agent initialization failed: {e}, using mock")
            from src.agents.mock_agent import MockAgent
            self.agent = MockAgent()
            self.agent.initialize({})

    def _initialize_orchestration(self) -> None:
        """Initialize orchestration components."""
        self.breakpoint_manager = BreakpointManager(
            self.state_manager,
            config=self.config.get('orchestration.breakpoints', {})
        )
        self.decision_engine = DecisionEngine(
            self.state_manager,
            self.breakpoint_manager,
            config=self.config.get('orchestration.decision', {})
        )
        self.quality_controller = QualityController(
            self.state_manager,
            config=self.config.get('orchestration.quality', {})
        )
        self.task_scheduler = TaskScheduler(
            self.state_manager
        )
        logger.info("Orchestration components initialized")

    def _initialize_monitoring(self) -> None:
        """Initialize monitoring components."""
        if self.current_project:
            self.file_watcher = FileWatcher(
                self.state_manager,
                project_id=self.current_project.id,
                project_root=self.current_project.working_directory,
                task_id=self.current_task.id if self.current_task else None
            )
            self.file_watcher.start_watching()
            logger.info("File monitoring started")

    def execute_task(self, task_id: int, max_iterations: int = 10) -> Dict[str, Any]:
        """Execute a single task.

        Args:
            task_id: Task ID to execute
            max_iterations: Maximum iterations before giving up

        Returns:
            Dictionary with execution results

        Raises:
            OrchestratorException: If execution fails
        """
        with self._lock:
            if self._state not in [OrchestratorState.INITIALIZED, OrchestratorState.RUNNING]:
                raise OrchestratorException(
                    "Orchestrator not ready",
                    context={'state': self._state.value},
                    recovery="Call initialize() first"
                )

            try:
                # Get task
                self.current_task = self.state_manager.get_task(task_id)
                if not self.current_task:
                    raise OrchestratorException(
                        f"Task not found: {task_id}",
                        recovery="Check task ID"
                    )

                # Get project
                self.current_project = self.state_manager.get_project(
                    self.current_task.project_id
                )

                # Initialize file watcher if needed
                if not self.file_watcher:
                    self._initialize_monitoring()

                logger.info(f"Executing task {task_id}: {self.current_task.title}")

                # Main execution loop
                result = self._execution_loop(max_iterations)

                logger.info(f"Task {task_id} completed: {result['status']}")
                return result

            except Exception as e:
                logger.error(f"Task execution failed: {e}", exc_info=True)
                raise

    def _execution_loop(self, max_iterations: int) -> Dict[str, Any]:
        """Main execution loop for a task.

        Args:
            max_iterations: Maximum iterations

        Returns:
            Execution results
        """
        iteration = 0
        accumulated_context = []

        while iteration < max_iterations:
            iteration += 1
            self._iteration_count += 1

            logger.info(f"Iteration {iteration}/{max_iterations}")
            self._print_obra(f"Starting iteration {iteration}/{max_iterations}")

            try:
                # 1. Build context
                context = self._build_context(accumulated_context)
                self._print_obra(f"Built context ({len(context)} chars)")

                # 2. Generate prompt
                prompt = self.prompt_generator.generate_prompt(
                    'task_execution',
                    {'task': self.current_task, 'context': context}
                )

                # 3. Send to agent
                logger.info("Sending prompt to agent...")
                self._print_obra(f"Sending prompt to Claude Code...", "[OBRA→CLAUDE]")
                response = self.agent.send_prompt(prompt, context={'task_id': self.current_task.id})
                self._print_obra(f"Response received ({len(response)} chars)")

                # 4. Validate response
                is_valid = self.response_validator.validate_format(
                    response,
                    expected_format='markdown'
                )
                self._print_obra(f"Validation: {'✓' if is_valid else '✗'}")

                if not is_valid:
                    logger.warning(f"Invalid response format")
                    accumulated_context.append({
                        'type': 'error',
                        'content': f"Previous response format was invalid (expected markdown)",
                        'timestamp': datetime.now(UTC)
                    })
                    continue

                # 5. Quality control
                self._print_qwen("Validating response...")
                quality_result = self.quality_controller.validate_output(
                    response,
                    self.current_task,
                    {'language': 'python'}
                )
                self._print_qwen(f"  Quality: {quality_result.overall_score:.2f} ({quality_result.gate.name})")

                # 6. Confidence scoring
                confidence = self.confidence_scorer.score_response(
                    response,
                    self.current_task,
                    {'validation': is_valid, 'quality': quality_result}
                )
                self._print_qwen(f"  Confidence: {confidence:.2f}")

                # 7. Decision making
                decision_context = {
                    'task': self.current_task,
                    'response': response,
                    'validation_result': validation_result,
                    'quality_score': quality_result.overall_score,
                    'confidence_score': confidence
                }

                action = self.decision_engine.decide_next_action(decision_context)

                logger.info(f"Decision: {action.type} (confidence: {action.confidence:.2f})")
                self._print_obra(f"Decision: {action.type}")

                # 8. Handle decision
                if action.type == DecisionEngine.ACTION_PROCEED:
                    # Task completed successfully
                    self.state_manager.update_task_status(
                        self.current_task.id,
                        'completed'
                    )
                    return {
                        'status': 'completed',
                        'response': response,
                        'iterations': iteration,
                        'quality_score': quality_result.overall_score,
                        'confidence': confidence
                    }

                elif action.type == DecisionEngine.ACTION_ESCALATE:
                    # Need human intervention
                    logger.warning("Escalating to human")
                    return {
                        'status': 'escalated',
                        'reason': action.explanation,
                        'response': response,
                        'iterations': iteration
                    }

                elif action.type == DecisionEngine.ACTION_CLARIFY:
                    # Need more information
                    logger.info("Requesting clarification")
                    accumulated_context.append({
                        'type': 'feedback',
                        'content': f"Issues to address: {action.metadata.get('issues', [])}",
                        'timestamp': datetime.now(UTC)
                    })

                elif action.type == DecisionEngine.ACTION_RETRY:
                    # Try again with updated context
                    logger.info("Retrying with updated context")
                    accumulated_context.append({
                        'type': 'previous_attempt',
                        'content': response,
                        'timestamp': datetime.now(UTC)
                    })

            except Exception as e:
                logger.error(f"Iteration {iteration} failed: {e}", exc_info=True)
                accumulated_context.append({
                    'type': 'error',
                    'content': f"Error: {str(e)}",
                    'timestamp': datetime.now(UTC)
                })

        # Max iterations reached
        logger.warning(f"Max iterations ({max_iterations}) reached")
        return {
            'status': 'max_iterations',
            'iterations': iteration,
            'message': 'Task did not complete within iteration limit'
        }

    def _build_context(self, accumulated_context: List[Dict[str, Any]]) -> str:
        """Build context for prompt generation.

        Args:
            accumulated_context: Accumulated context from previous iterations

        Returns:
            Context string
        """
        # Add task description
        items = [{
            'type': 'current_task_description',
            'content': self.current_task.description,
            'priority': 10,
            'timestamp': datetime.now(UTC)
        }]

        # Add accumulated context
        items.extend(accumulated_context)

        # Add project info if available
        if self.current_project:
            items.append({
                'type': 'project_goals',
                'content': self.current_project.description,
                'priority': 5,
                'timestamp': datetime.now(UTC)
            })

        # Build context within token limit
        max_tokens = self.config.get('context.max_tokens', 100000)
        context = self.context_manager.build_context(items, max_tokens)

        return context

    def run(self, project_id: Optional[int] = None) -> None:
        """Run continuous orchestration loop.

        Args:
            project_id: Optional project ID to work on

        Raises:
            OrchestratorException: If run fails
        """
        with self._lock:
            if self._state != OrchestratorState.INITIALIZED:
                raise OrchestratorException(
                    "Cannot run: not initialized",
                    recovery="Call initialize() first"
                )

            self._state = OrchestratorState.RUNNING
            self._start_time = datetime.now(UTC)

        logger.info("Starting orchestration loop...")

        try:
            while self._state == OrchestratorState.RUNNING:
                # Get next task from scheduler
                next_task = self.task_scheduler.get_next_task(project_id)

                if not next_task:
                    logger.info("No tasks available, waiting...")
                    time.sleep(5)
                    continue

                # Execute task
                try:
                    result = self.execute_task(next_task.id)
                    logger.info(f"Task {next_task.id} result: {result['status']}")
                except Exception as e:
                    logger.error(f"Task {next_task.id} failed: {e}")

        except KeyboardInterrupt:
            logger.info("Orchestration interrupted by user")
        finally:
            self.stop()

    def stop(self) -> None:
        """Stop orchestration loop."""
        with self._lock:
            logger.info("Stopping orchestrator...")
            self._state = OrchestratorState.STOPPED

            # Stop file watcher
            if self.file_watcher:
                self.file_watcher.stop()

            # Cleanup agent
            if self.agent:
                self.agent.cleanup()

            logger.info("Orchestrator stopped")

    def pause(self) -> None:
        """Pause orchestration loop."""
        with self._lock:
            if self._state == OrchestratorState.RUNNING:
                self._state = OrchestratorState.PAUSED
                logger.info("Orchestrator paused")

    def resume(self) -> None:
        """Resume orchestration loop."""
        with self._lock:
            if self._state == OrchestratorState.PAUSED:
                self._state = OrchestratorState.RUNNING
                logger.info("Orchestrator resumed")

    def get_status(self) -> Dict[str, Any]:
        """Get orchestrator status.

        Returns:
            Status dictionary
        """
        with self._lock:
            uptime = None
            if self._start_time:
                uptime = (datetime.now(UTC) - self._start_time).total_seconds()

            return {
                'state': self._state.value,
                'current_task': self.current_task.id if self.current_task else None,
                'current_project': self.current_project.id if self.current_project else None,
                'iteration_count': self._iteration_count,
                'uptime_seconds': uptime,
                'components': {
                    'state_manager': self.state_manager is not None,
                    'agent': self.agent is not None,
                    'llm': self.llm_interface is not None,
                    'file_watcher': self.file_watcher is not None
                }
            }

    def shutdown(self) -> None:
        """Gracefully shutdown orchestrator."""
        logger.info("Shutting down orchestrator...")
        self.stop()

        # Close state manager
        if self.state_manager:
            self.state_manager.close()

        logger.info("Orchestrator shutdown complete")
