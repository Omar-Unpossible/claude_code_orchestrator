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
import uuid
from datetime import datetime, UTC
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from threading import RLock

from src.core.config import Config
from src.core.state import StateManager
from src.core.models import Task, ProjectState, TaskStatus, TaskType
from src.core.exceptions import OrchestratorException, TaskStoppedException

# Component imports
from src.plugins.registry import AgentRegistry, LLMRegistry
from src.plugins.exceptions import AgentException, PluginNotFoundError
import src.agents  # Import to register agent plugins
import src.llm  # Import to register LLM plugins
from src.llm.local_interface import LocalLLMInterface
from src.llm.response_validator import ResponseValidator
from src.llm.prompt_generator import PromptGenerator
from src.monitoring.file_watcher import FileWatcher
from src.orchestration.task_scheduler import TaskScheduler
from src.orchestration.breakpoint_manager import BreakpointManager
from src.orchestration.decision_engine import DecisionEngine
from src.orchestration.quality_controller import QualityController
from src.orchestration.complexity_estimator import TaskComplexityEstimator
from src.orchestration.max_turns_calculator import MaxTurnsCalculator  # Phase 4, Task 4.2
from src.orchestration.complexity_estimate import ComplexityEstimate
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
        self.complexity_estimator: Optional[TaskComplexityEstimator] = None
        self.max_turns_calculator = None  # Phase 4, Task 4.2: Adaptive max_turns

        # Runtime state
        self.current_project: Optional[ProjectState] = None
        self.current_task: Optional[Task] = None
        self._iteration_count = 0
        self._start_time: Optional[datetime] = None
        self._current_epic_id: Optional[int] = None

        # Complexity estimation config
        self._enable_complexity_estimation = self.config.get('enable_complexity_estimation', False)

        # Interactive mode attributes (Phase 2)
        self.interactive_mode: bool = False
        self.command_processor = None  # Initialized when interactive mode enabled
        self.input_manager = None  # Initialized when interactive mode enabled
        self.paused: bool = False
        self.injected_context: Dict[str, Any] = {}
        self.stop_requested: bool = False

        # Status tracking for interactive /status command
        self.current_task_id: Optional[int] = None
        self.current_iteration: int = 0
        self.latest_quality_score: float = 0.0
        self.latest_confidence: float = 0.0
        self.max_turns: int = 10

        logger.info("Orchestrator created")

    def _print_obra(self, message: str, prefix: str = "[OBRA]") -> None:
        """Print Obra action/status with colored prefix.

        Args:
            message: Message to display
            prefix: Prefix to use (default: [OBRA], can be [OBRA→CLAUDE])
        """
        # Blue color for Obra output
        print(f"\033[34m{prefix}\033[0m {message}")

    def _print_orch(self, message: str) -> None:
        """Print orchestrator output with dynamic [ORCH:model] prefix.

        Args:
            message: Message to display

        Example:
            >>> self._print_orch("Quality: 0.81 (PASS)")
            [ORCH:ollama] Quality: 0.81 (PASS)
        """
        llm_name = self.llm_interface.get_name() if self.llm_interface else 'unknown'
        prefix = f"[ORCH:{llm_name}]"
        # Yellow color for orchestrator output
        print(f"\033[33m{prefix}\033[0m {message}")

    def _print_impl(self, message: str) -> None:
        """Print implementer output with dynamic [IMPL:model] prefix.

        Args:
            message: Message to display

        Example:
            >>> self._print_impl("Response received (1234 chars)")
            [IMPL:claude-code] Response received (1234 chars)
        """
        agent_name = getattr(self.agent, 'name', 'claude-code')  # Fallback
        prefix = f"[IMPL:{agent_name}]"
        # Green color for implementer output
        print(f"\033[32m{prefix}\033[0m {message}")

    # Interactive Mode Helper Methods (Phase 2)

    def _initialize_interactive_mode(self) -> None:
        """Initialize interactive mode components.

        Creates CommandProcessor and InputManager for interactive command injection.
        """
        try:
            from src.utils.command_processor import CommandProcessor
            from src.utils.input_manager import InputManager

            self.interactive_mode = True
            self.command_processor = CommandProcessor(self)
            self.input_manager = InputManager()
            self.input_manager.start_listening()

            logger.info("Interactive mode initialized successfully")
        except (OSError, IOError) as e:
            logger.error(f"Cannot start interactive mode: {e}")
            logger.warning("Falling back to non-interactive mode")
            self.interactive_mode = False

    def _check_interactive_commands(self) -> None:
        """Check and process any queued commands from user input.

        Called at the start of each iteration to handle user commands.
        """
        if not self.interactive_mode or not self.input_manager:
            return

        # Get command from queue (non-blocking)
        command = self.input_manager.get_command(timeout=0.1)
        if command:
            try:
                result = self.command_processor.execute_command(command)

                # Display result
                if 'success' in result:
                    print(f"\033[32m✓\033[0m {result['message']}")
                elif 'error' in result:
                    print(f"\033[31m✗\033[0m {result['error']}")
                    if 'message' in result:
                        print(f"  {result['message']}")

            except Exception as e:
                # Catch CommandValidationError and other exceptions
                from src.utils.command_processor import CommandValidationError

                if isinstance(e, CommandValidationError):
                    print(f"\033[31m✗ Error:\033[0m {e.message}")
                    print(f"\033[33mAvailable commands:\033[0m {', '.join(e.available_commands)}")
                    print("\033[2mType /help for usage information\033[0m")
                else:
                    print(f"\033[31m✗ Unexpected error:\033[0m {e}")
                    logger.exception("Error processing interactive command")

    def _wait_for_resume(self) -> None:
        """Block execution until user types /resume.

        Called when paused flag is set.
        """
        logger.info("[INTERACTIVE] Execution paused. Type /resume to continue.")
        print(f"\n\033[33m⏸️  PAUSED\033[0m - Type /resume to continue")

        while self.paused and not self.stop_requested:
            # Check for commands
            command = self.input_manager.get_command(timeout=0.5)
            if command:
                try:
                    result = self.command_processor.execute_command(command)

                    # Display result
                    if 'success' in result:
                        print(f"\033[32m✓\033[0m {result['message']}")
                    elif 'error' in result:
                        print(f"\033[31m✗\033[0m {result['error']}")
                        if 'message' in result:
                            print(f"  {result['message']}")

                except Exception as e:
                    # Catch CommandValidationError and other exceptions
                    from src.utils.command_processor import CommandValidationError

                    if isinstance(e, CommandValidationError):
                        print(f"\033[31m✗ Error:\033[0m {e.message}")
                        print(f"\033[33mAvailable commands:\033[0m {', '.join(e.available_commands)}")
                        print("\033[2mType /help for usage information\033[0m")
                    else:
                        print(f"\033[31m✗ Unexpected error:\033[0m {e}")
                        logger.exception("Error processing interactive command")

                # Check if we should continue
                if not self.paused:
                    logger.info("[INTERACTIVE] Execution resumed")
                    print(f"\033[32m▶️  RESUMED\033[0m")
                    break

    def _apply_injected_context(self, base_prompt: str, context: Dict[str, Any]) -> str:
        """Merge user-injected context into prompt.

        Tracks token impact on context window.

        Args:
            base_prompt: Base prompt from PromptGenerator
            context: Injected context dict

        Returns:
            Augmented prompt with user guidance
        """
        # Check both new and legacy keys (to_impl takes precedence)
        injected_text = context.get('to_impl', '') or context.get('to_claude', '')
        if not injected_text:
            return base_prompt

        # Build augmented prompt
        augmented = f"{base_prompt}\n\n--- USER GUIDANCE ---\n{injected_text}\n"

        # Track token impact
        base_tokens = self.context_manager.estimate_tokens(base_prompt)
        augmented_tokens = self.context_manager.estimate_tokens(augmented)
        tokens_added = augmented_tokens - base_tokens

        logger.info(f"Injected context added {tokens_added} tokens")

        # Warn if approaching context window limit
        if hasattr(self, 'current_session_id') and self.current_session_id:
            session = self.state_manager.get_session_record(self.current_session_id)
            if session:
                total_tokens = session.total_tokens + tokens_added
                limit = self.context_manager.limit
                usage_pct = (total_tokens / limit) * 100

                if usage_pct > 70:
                    logger.warning(
                        f"Context window usage: {usage_pct:.1f}% ({total_tokens}/{limit} tokens). "
                        f"Injected context may trigger refresh soon."
                    )

        return augmented

    def _apply_orch_context(self, validation_prompt: str, context: Dict[str, Any]) -> str:
        """Apply orchestrator-injected context to validation prompt.

        Adds user guidance to quality scoring and validation prompts based on intent.

        Args:
            validation_prompt: Base validation prompt
            context: Injected context dict

        Returns:
            Augmented validation prompt with user guidance

        Note:
            This is a placeholder for future enhancement (Phase 2 full implementation).
            Currently, the intent classification is done but not fully utilized.
            Future work: Integrate with QualityController.validate() custom prompts.

        Example:
            >>> context = {'to_orch': 'Be more lenient', 'to_orch_intent': 'validation_guidance'}
            >>> augmented = self._apply_orch_context(base_prompt, context)
        """
        orch_message = context.get('to_orch', '')
        if not orch_message:
            return validation_prompt

        intent = context.get('to_orch_intent', 'general')

        # Build augmented prompt based on intent
        if intent == 'validation_guidance':
            augmented = f"{validation_prompt}\n\n--- USER GUIDANCE (VALIDATION) ---\n{orch_message}\n"
        elif intent == 'decision_hint':
            augmented = f"{validation_prompt}\n\n--- USER HINT (DECISION) ---\n{orch_message}\n" + \
                        "Note: User has provided guidance on decision thresholds. Consider this when evaluating.\n"
        elif intent == 'feedback_request':
            augmented = f"{validation_prompt}\n\n--- USER REQUEST (FEEDBACK) ---\n{orch_message}\n" + \
                        "After validation, provide specific feedback addressing the user's request.\n"
        else:
            augmented = f"{validation_prompt}\n\n--- USER MESSAGE (ORCHESTRATOR) ---\n{orch_message}\n"

        # Track token impact
        base_tokens = self.context_manager.estimate_tokens(validation_prompt)
        augmented_tokens = self.context_manager.estimate_tokens(augmented)
        tokens_added = augmented_tokens - base_tokens

        logger.debug(
            f"Applied orchestrator context: +{tokens_added} tokens, intent={intent}"
        )

        return augmented

    def _cleanup_interactive_mode(self) -> None:
        """Cleanup interactive mode components.

        Stops InputManager thread and cleans up resources.
        """
        if self.input_manager:
            self.input_manager.stop_listening()
            logger.info("Interactive mode cleaned up")

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
                self._initialize_complexity_estimator()
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
        """Initialize LLM interface from registry.

        Gracefully handles connection failures - Obra will still load
        but prompt user to configure LLM before executing tasks.
        """
        llm_type = self.config.get('llm.type', 'ollama')  # Default to ollama
        llm_config = self.config.get('llm', {})

        # Map api_url to endpoint for backward compatibility
        if 'api_url' in llm_config and 'endpoint' not in llm_config:
            llm_config['endpoint'] = llm_config['api_url']

        try:
            # Get LLM class from registry
            try:
                llm_class = LLMRegistry.get(llm_type)
            except PluginNotFoundError as e:
                available_llms = LLMRegistry.list()
                logger.warning(
                    f"LLM type '{llm_type}' not found in registry. "
                    f"Available: {available_llms}"
                )
                self._print_obra(
                    f"⚠ LLM type '{llm_type}' not registered. Available: {available_llms}",
                    prefix="[OBRA WARNING]"
                )
                self.llm_interface = None
                return

            # Create instance and initialize
            self.llm_interface = llm_class()
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

            logger.info(f"LLM components initialized: {llm_type}")

        except Exception as e:
            # Gracefully handle LLM initialization failures (connection errors, etc.)
            logger.warning(f"LLM initialization failed: {e}")
            self._print_obra(
                f"⚠ Could not connect to LLM service ({llm_type}). "
                f"Obra loaded but you need a working LLM to execute tasks.",
                prefix="[OBRA WARNING]"
            )
            self._print_obra(
                f"To fix: Configure a valid LLM in config/config.yaml or use environment variables:",
                prefix="[OBRA WARNING]"
            )
            self._print_obra(
                f"  Option 1 (Local): llm.type=ollama, llm.api_url=http://localhost:11434",
                prefix="[OBRA WARNING]"
            )
            self._print_obra(
                f"  Option 2 (Remote): llm.type=openai-codex, llm.model=gpt-5-codex",
                prefix="[OBRA WARNING]"
            )
            self._print_obra(
                f"Then reconnect: orchestrator.reconnect_llm()",
                prefix="[OBRA WARNING]"
            )

            # Set LLM interface to None - tasks will check before execution
            self.llm_interface = None

            # Initialize prompt generator and validator with None LLM (will be set on reconnect)
            if not hasattr(self, 'prompt_generator') or self.prompt_generator is None:
                template_dir = self.config.get('prompt.template_dir', 'config')
                try:
                    self.prompt_generator = PromptGenerator(
                        template_dir=template_dir,
                        llm_interface=None,  # Will be set when LLM reconnects
                        state_manager=self.state_manager
                    )
                except Exception as pg_error:
                    logger.warning(f"Could not initialize prompt generator: {pg_error}")
                    self.prompt_generator = None

            if not hasattr(self, 'response_validator') or self.response_validator is None:
                try:
                    self.response_validator = ResponseValidator()
                except Exception as rv_error:
                    logger.warning(f"Could not initialize response validator: {rv_error}")
                    self.response_validator = None

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

    def _initialize_complexity_estimator(self) -> None:
        """Initialize TaskComplexityEstimator if enabled."""
        if not self._enable_complexity_estimation:
            logger.info("Complexity estimation disabled")
            return

        try:
            config_path = self.config.get('orchestration.complexity_config_path', 'config/complexity_thresholds.yaml')
            self.complexity_estimator = TaskComplexityEstimator(
                llm_interface=self.llm_interface,
                state_manager=self.state_manager,
                config_path=config_path
            )
            logger.info("TaskComplexityEstimator initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize complexity estimator: {e}")
            self.complexity_estimator = None

        # Phase 4, Task 4.2: Initialize MaxTurnsCalculator
        try:
            max_turns_config = self.config.get('orchestration.max_turns', {})
            self.max_turns_calculator = MaxTurnsCalculator(config=max_turns_config)
            logger.info("MaxTurnsCalculator initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize max_turns calculator: {e}")
            self.max_turns_calculator = None

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

    # =========================================================================
    # LLM RECONNECTION & CONFIGURATION
    # =========================================================================

    def reconnect_llm(
        self,
        llm_type: Optional[str] = None,
        llm_config: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Reconnect or reconfigure LLM after initialization.

        Allows switching LLM providers or reconnecting after connection
        failure without restarting Obra.

        Args:
            llm_type: Optional new LLM type (e.g., 'ollama', 'openai-codex').
                     If None, uses current config.
            llm_config: Optional new LLM configuration dict.
                       If None, uses current config.

        Returns:
            True if connection successful, False otherwise

        Example:
            >>> # Reconnect to Ollama after it comes online
            >>> orchestrator.reconnect_llm()
            >>>
            >>> # Switch to OpenAI Codex
            >>> orchestrator.reconnect_llm(
            ...     llm_type='openai-codex',
            ...     llm_config={'model': 'gpt-5-codex', 'timeout': 120}
            ... )
        """
        # Update config if new values provided
        if llm_type:
            self.config.set('llm.type', llm_type)

        if llm_config:
            # Merge new config with existing
            current_llm_config = self.config.get('llm', {})
            merged_config = {**current_llm_config, **llm_config}
            for key, value in merged_config.items():
                self.config.set(f'llm.{key}', value)

        # Attempt initialization
        try:
            self._initialize_llm()

            if self.llm_interface is None:
                self._print_obra(
                    "Failed to connect to LLM. Check configuration and try again.",
                    prefix="[OBRA ERROR]"
                )
                return False

            # Check if LLM is actually available
            if not self.llm_interface.is_available():
                self._print_obra(
                    f"LLM service not responding. Check that the service is running.",
                    prefix="[OBRA ERROR]"
                )
                self.llm_interface = None
                return False

            llm_name = llm_type or self.config.get('llm.type', 'unknown')
            self._print_obra(
                f"✓ Successfully connected to LLM: {llm_name}",
                prefix="[OBRA SUCCESS]"
            )
            return True

        except Exception as e:
            logger.error(f"LLM reconnection failed: {e}", exc_info=True)
            self._print_obra(
                f"Failed to reconnect LLM: {e}",
                prefix="[OBRA ERROR]"
            )
            self.llm_interface = None
            return False

    def check_llm_available(self) -> bool:
        """Check if LLM is connected and available.

        Returns:
            True if LLM is ready for use, False otherwise
        """
        if self.llm_interface is None:
            return False

        try:
            return self.llm_interface.is_available()
        except Exception as e:
            logger.warning(f"LLM health check failed: {e}")
            return False

    # =========================================================================
    # SESSION MANAGEMENT (Phase 2, Task 2.4)
    # =========================================================================

    def _start_epic_session(self, project_id: int, milestone_id: Optional[int] = None) -> str:
        """Start new session for epic execution.

        Args:
            project_id: Project ID
            milestone_id: Optional epic ID (DB column still named milestone_id)

        Returns:
            str: New session_id (UUID)

        Example:
            >>> session_id = orchestrator._start_epic_session(
            ...     project_id=1,
            ...     milestone_id=5
            ... )
        """
        # Generate new session ID
        session_id = str(uuid.uuid4())

        # Create session record in database
        self.state_manager.create_session_record(
            session_id=session_id,
            project_id=project_id,
            milestone_id=milestone_id
        )

        # Update agent to use this session
        if hasattr(self.agent, 'session_id'):
            self.agent.session_id = session_id
            self.agent.use_session_persistence = True
            logger.info(f"Agent configured with session {session_id[:8]}...")

        context_type = f"milestone {milestone_id}" if milestone_id else "ad-hoc work"
        logger.info(
            f"SESSION START: session_id={session_id[:8]}..., "
            f"project_id={project_id}, context={context_type}"
        )

        return session_id

    def _end_epic_session(self, session_id: str, milestone_id: Optional[int] = None) -> None:
        """End session and save summary.

        Args:
            session_id: Session to end
            milestone_id: Optional epic ID for summary context (DB column still named milestone_id)

        Example:
            >>> orchestrator._end_epic_session(
            ...     session_id="550e8400-e29b-41d4-a716-446655440001",
            ...     milestone_id=5
            ... )
        """
        try:
            logger.info(f"SESSION END: Ending session {session_id[:8]}...")

            # Generate session summary using Qwen
            summary = self._generate_session_summary(session_id, milestone_id)

            # Save summary to session record
            self.state_manager.save_session_summary(session_id, summary)

            # Mark session as completed
            self.state_manager.complete_session_record(
                session_id=session_id,
                ended_at=datetime.now(UTC)
            )

            logger.info(
                f"SESSION END: session_id={session_id[:8]}..., "
                f"summary_chars={len(summary):,}, milestone={milestone_id}"
            )

        except Exception as e:
            logger.error(f"SESSION END ERROR: Failed to end session {session_id[:8]}...: {e}")
            # Mark as abandoned but don't raise
            try:
                session = self.state_manager.get_session_record(session_id)
                if session:
                    session.status = 'abandoned'
                    session.ended_at = datetime.now(UTC)
                logger.warning(f"SESSION ABANDONED: session_id={session_id[:8]}...")
            except:
                pass

    def _build_epic_context(self, project_id: int, milestone_id: Optional[int] = None) -> str:
        """Build context for epic including workplan and previous summary.

        Args:
            project_id: Project ID
            milestone_id: Optional epic ID (DB column still named milestone_id)

        Returns:
            str: Formatted context for epic execution

        Example:
            >>> context = orchestrator._build_epic_context(
            ...     project_id=1,
            ...     milestone_id=5
            ... )
        """
        context_parts = []

        # Project context
        project = self.state_manager.get_project(project_id)
        context_parts.append(f"# Project: {project.project_name}")
        if project.description:
            context_parts.append(f"Description: {project.description}")
        context_parts.append(f"Working Directory: {project.working_directory}")
        context_parts.append("")

        # Previous milestone summary (if available)
        if milestone_id and milestone_id > 1:
            prev_session = self.state_manager.get_latest_session_for_milestone(milestone_id - 1)
            if prev_session and prev_session.summary:
                context_parts.append("## Previous Milestone Summary")
                context_parts.append(prev_session.summary)
                context_parts.append("")

        # Current milestone info (if available)
        if milestone_id:
            context_parts.append(f"## Current Milestone: {milestone_id}")
            # Note: We don't have a milestone table yet, but placeholder for future
            context_parts.append("Tasks will be executed sequentially within this session.")
            context_parts.append("")

        return "\n".join(context_parts)

    def execute_epic(
        self,
        project_id: int,
        epic_id: int,
        max_iterations_per_story: int = 10
    ) -> Dict[str, Any]:
        """Execute all stories in an Epic with session management (ADR-013).

        Epic: Large feature spanning multiple stories (3-15 sessions).
        This method orchestrates the execution of all stories within an epic.

        Session lifecycle:
        1. Validate epic exists and is type EPIC
        2. Get all stories for this epic
        3. Start epic session
        4. Build epic context (workplan + previous summary)
        5. Execute all stories in session
        6. End session and generate summary

        Args:
            project_id: Project ID
            epic_id: Epic task ID (must be TaskType.EPIC)
            max_iterations_per_story: Max iterations per story

        Returns:
            Dictionary with execution results:
            - epic_id: int
            - session_id: str
            - stories_completed: int
            - stories_failed: int
            - total_stories: int
            - results: List[Dict]

        Raises:
            ValueError: If epic doesn't exist or is not type EPIC

        Example:
            >>> result = orchestrator.execute_epic(
            ...     project_id=1,
            ...     epic_id=5
            ... )
        """
        # Validate epic
        epic = self.state_manager.get_task(epic_id)
        if not epic:
            raise ValueError(f"Epic {epic_id} does not exist")
        if epic.task_type != TaskType.EPIC:
            raise ValueError(f"Task {epic_id} is not an Epic (type={epic.task_type.value})")

        # Get all stories in epic
        stories = self.state_manager.get_epic_stories(epic_id)
        story_ids = [s.id for s in stories]

        logger.info(
            f"EPIC START: epic_id={epic_id}, "
            f"project_id={project_id}, num_stories={len(stories)}"
        )

        # Start session
        session_id = self._start_epic_session(project_id, epic_id)

        # Build epic context
        epic_context = self._build_epic_context(project_id, epic_id)

        # Store context for task injection
        self._current_epic_context = epic_context
        self._current_epic_first_task = story_ids[0] if story_ids else None
        self._current_epic_id = epic_id

        results = []
        stories_completed = 0
        stories_failed = 0

        try:
            # Execute all stories in session
            for story_id in story_ids:
                try:
                    logger.info(f"Executing story {story_id} in epic {epic_id}...")

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
            self._current_epic_first_task = None
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
            'total_stories': len(stories),
            'results': results
        }

    def execute_task(self, task_id: int, max_iterations: int = 10, context: Optional[Dict[str, Any]] = None, stream: bool = False, interactive: bool = False) -> Dict[str, Any]:
        """Execute a single task with optional complexity estimation.

        Automatically creates temporary session for tracking if not in milestone context.
        This enables standalone task execution while maintaining session usage tracking.

        Process:
        1. Create temporary session if needed (for tracking)
        2. Get task from StateManager
        3. Estimate complexity (if enabled) - suggestions only
        4. Log complexity estimate
        5. Execute task (Claude handles parallelization if needed)
        6. Clean up temporary session if created
        7. Return results

        Args:
            task_id: Task ID to execute
            max_iterations: Maximum iterations before giving up
            context: Optional execution context
            stream: Enable real-time streaming output (Phase 1)
            interactive: Enable interactive mode with command injection (Phase 2)

        Returns:
            Dictionary with execution results:
            - task_id: int
            - status: str
            - result: Any
            - complexity_estimate: Optional[Dict]
            - parallel_metadata: Dict (parsed from Claude's response)

        Raises:
            OrchestratorException: If execution fails
            TaskStoppedException: If user requests stop via /stop command
        """
        with self._lock:
            if self._state not in [OrchestratorState.INITIALIZED, OrchestratorState.RUNNING]:
                raise OrchestratorException(
                    "Orchestrator not ready",
                    context={'state': self._state.value},
                    recovery="Call initialize() first"
                )

            # Check if LLM is available before executing task
            if not self.check_llm_available():
                error_msg = (
                    "Cannot execute task: LLM service not available. "
                    "Configure and connect to an LLM first."
                )
                logger.error(error_msg)
                self._print_obra(
                    "❌ LLM service required but not connected.",
                    prefix="[OBRA ERROR]"
                )
                self._print_obra(
                    "Fix: Run orchestrator.reconnect_llm() or orchestrator.reconnect_llm("
                    "llm_type='openai-codex', llm_config={'model': 'gpt-5-codex'})",
                    prefix="[OBRA ERROR]"
                )
                raise OrchestratorException(
                    error_msg,
                    context={'llm_interface': str(self.llm_interface)},
                    recovery="Call orchestrator.reconnect_llm() to connect to LLM service"
                )

            # BUG-PHASE4-002 FIX: Create temporary session for standalone execution
            # Check if we're already in an epic session
            in_epic_session = hasattr(self, 'current_session_id') and self.current_session_id is not None
            temp_session_id = None
            old_agent_session_id = None
            cleanup_temp_session = False

            # BUG FIX: Initialize streaming_handler before try block to avoid UnboundLocalError
            streaming_handler = None

            try:
                # Get task first to get project_id for session creation
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

                # Initialize streaming handler if stream=True (Phase 1)
                if stream:
                    from src.utils.streaming_handler import StreamingHandler
                    streaming_handler = StreamingHandler()
                    logger.addHandler(streaming_handler)
                    logger.info("[STREAMING] Real-time output enabled")

                # Initialize interactive mode if interactive=True (Phase 2)
                if interactive:
                    # Interactive mode requires streaming
                    if not stream:
                        logger.warning("Interactive mode requires streaming, enabling automatically")
                        if not streaming_handler:
                            from src.utils.streaming_handler import StreamingHandler
                            streaming_handler = StreamingHandler()
                            logger.addHandler(streaming_handler)

                    self._initialize_interactive_mode()
                    logger.info("[INTERACTIVE] Interactive mode enabled")

                # Create temporary session if not in epic context
                if not in_epic_session:
                    # Generate temporary session UUID
                    temp_session_id = str(uuid.uuid4())

                    # Create session record in database
                    self.state_manager.create_session_record(
                        session_id=temp_session_id,
                        project_id=self.current_project.id,
                        milestone_id=None  # Temporary session, not milestone-bound
                    )

                    # Configure agent to use this session_id for tracking
                    if hasattr(self.agent, 'session_id'):
                        old_agent_session_id = self.agent.session_id
                        self.agent.session_id = temp_session_id

                    # Set as current session for this execution
                    self.current_session_id = temp_session_id
                    cleanup_temp_session = True

                    logger.info(
                        f"TEMP_SESSION: session_id={temp_session_id[:8]}..., "
                        f"task_id={task_id}, project_id={self.current_project.id}, "
                        f"mode=standalone"
                    )

                logger.info(f"TASK START: task_id={task_id}, title='{self.current_task.title}'")

                # Estimate complexity if enabled (suggestions only, not commands)
                complexity_estimate = None
                if self.complexity_estimator:
                    complexity_estimate = self._estimate_task_complexity(self.current_task, context)
                    logger.info(
                        f"COMPLEXITY: task_id={task_id}, score={complexity_estimate.complexity_score:.0f}/100, "
                        f"category={complexity_estimate.get_complexity_category()}, "
                        f"decompose={complexity_estimate.should_decompose}, "
                        f"subtasks={len(complexity_estimate.decomposition_suggestions)}, "
                        f"parallel_groups={len(complexity_estimate.parallelization_opportunities)}"
                    )

                # Phase 4, Task 4.2: Calculate adaptive max_turns
                task_dict = self.current_task.to_dict()
                if complexity_estimate:
                    # Add complexity metadata for calculator
                    task_dict['estimated_files'] = len(complexity_estimate.files_to_create) + len(complexity_estimate.files_to_modify)
                    task_dict['estimated_loc'] = sum(f.get('estimated_loc', 0) for f in complexity_estimate.files_to_create + complexity_estimate.files_to_modify)

                max_turns = 10  # Default fallback
                max_turns_reason = "default"
                if self.max_turns_calculator:
                    max_turns = self.max_turns_calculator.calculate(task_dict)
                    max_turns_reason = "calculated"
                    logger.info(
                        f"MAX_TURNS: task_id={task_id}, max_turns={max_turns}, "
                        f"reason={max_turns_reason}, "
                        f"estimated_files={task_dict.get('estimated_files', 0)}, "
                        f"estimated_loc={task_dict.get('estimated_loc', 0):,}"
                    )

                # Phase 4, Task 4.2: Retry logic for error_max_turns
                retry_count = 0
                max_retries = self.config.get('orchestration.max_turns.max_retries', 1)
                retry_multiplier = self.config.get('orchestration.max_turns.retry_multiplier', 2)
                auto_retry = self.config.get('orchestration.max_turns.auto_retry', True)

                # Ensure context dict exists
                if context is None:
                    context = {}

                while retry_count <= max_retries:
                    try:
                        # Add max_turns to context for agent
                        context['max_turns'] = max_turns

                        # Execute with single agent (Claude may use Task tool internally)
                        result = self._execute_single_task(
                            self.current_task,
                            max_iterations,
                            context,
                            complexity_estimate=complexity_estimate
                        )

                        # Success - break out of retry loop
                        break

                    except AgentException as e:
                        # Check if it's error_max_turns
                        if e.context_data.get('subtype') == 'error_max_turns' and auto_retry:
                            num_turns = e.context_data.get('num_turns', max_turns)

                            logger.warning(
                                f"ERROR_MAX_TURNS: task_id={task_id}, "
                                f"turns_used={num_turns}, max_turns={max_turns}, "
                                f"attempt={retry_count + 1}/{max_retries + 1}"
                            )

                            if retry_count < max_retries:
                                # Retry with increased limit
                                retry_count += 1
                                old_max_turns = max_turns
                                max_turns = max_turns * retry_multiplier

                                # Enforce upper bound
                                if self.max_turns_calculator:
                                    max_turns = min(max_turns, self.max_turns_calculator.max_turns)

                                logger.info(
                                    f"MAX_TURNS RETRY: task_id={task_id}, "
                                    f"attempt={retry_count + 1}/{max_retries + 1}, "
                                    f"max_turns={old_max_turns} → {max_turns} "
                                    f"(multiplier={retry_multiplier}x)"
                                )

                                # Continue to next iteration of retry loop
                                continue
                            else:
                                # Max retries reached
                                logger.error(
                                    f"MAX_TURNS EXHAUSTED: task_id={task_id}, "
                                    f"attempts={max_retries + 1}, final_max_turns={max_turns}, "
                                    f"last_turns_used={num_turns}"
                                )
                                raise
                        else:
                            # Not error_max_turns, or auto_retry disabled - don't retry
                            raise

                # Add complexity estimate to result if available
                if complexity_estimate:
                    result['complexity_estimate'] = complexity_estimate.to_dict()

                logger.info(
                    f"TASK END: task_id={task_id}, status={result['status']}, "
                    f"iterations={result.get('iterations', 0)}, max_iterations={max_iterations}"
                )
                return result

            except TaskStoppedException as e:
                # Phase 2: Handle user-requested stop gracefully
                logger.info(f"Task stopped by user: {e}")
                self.state_manager.update_task_status(
                    task_id=task_id,
                    status=TaskStatus.PAUSED
                )
                return {
                    'status': 'stopped',
                    'iterations': e.context_data.get('iterations_completed', 0),
                    'message': 'Task stopped by user'
                }

            except Exception as e:
                logger.error(f"TASK ERROR: task_id={task_id}, error={e}", exc_info=True)
                raise

            finally:
                # Phase 2: Clean up interactive mode (if enabled)
                if interactive:
                    self._cleanup_interactive_mode()

                # Clean up streaming handler (Phase 1)
                if streaming_handler:
                    logger.removeHandler(streaming_handler)
                    logger.debug("[STREAMING] Handler removed")

                # Clean up temporary session if we created one
                if cleanup_temp_session and temp_session_id:
                    try:
                        # Mark temporary session as completed
                        self.state_manager.complete_session_record(
                            session_id=temp_session_id,
                            ended_at=datetime.now(UTC)
                        )
                        logger.info(f"TEMP_SESSION_END: session_id={temp_session_id[:8]}...")
                    except Exception as e:
                        logger.warning(f"Failed to clean up temp session {temp_session_id[:8]}...: {e}")

                    # Restore agent's previous session_id (even if None, to clear temp session)
                    # BUG-PHASE4-005 FIX: Always reset to prevent session reuse across tasks
                    if hasattr(self.agent, 'session_id'):
                        self.agent.session_id = old_agent_session_id

                    # Clear current session if it was temporary
                    if hasattr(self, 'current_session_id') and self.current_session_id == temp_session_id:
                        self.current_session_id = None

    def _execute_single_task(
        self,
        task: Task,
        max_iterations: int,
        context: Optional[Dict[str, Any]] = None,
        complexity_estimate: Optional[ComplexityEstimate] = None
    ) -> Dict[str, Any]:
        """Execute a single task (Claude handles parallelization if needed).

        Args:
            task: Task to execute
            max_iterations: Maximum iterations
            context: Optional execution context
            complexity_estimate: Optional complexity estimate to include in prompt

        Returns:
            Execution results including parallel_metadata
        """
        iteration = 0
        accumulated_context = []

        while iteration < max_iterations:
            iteration += 1
            self._iteration_count += 1

            logger.debug(f"ITERATION START: task_id={self.current_task.id}, iteration={iteration}/{max_iterations}")
            self._print_obra(f"Starting iteration {iteration}/{max_iterations}")

            # BUG-PHASE4-006 FIX: Create fresh session per iteration to avoid lock errors
            # Generate unique session_id for this iteration
            iteration_session_id = str(uuid.uuid4())
            old_agent_session_id = getattr(self.agent, 'session_id', None)
            session_created = False

            try:
                # Create session record for this iteration (linked to task for aggregation)
                self.state_manager.create_session_record(
                    session_id=iteration_session_id,
                    project_id=task.project_id,
                    task_id=task.id,  # Link to task for metrics aggregation
                    milestone_id=None,
                    metadata={'iteration': iteration}
                )
                session_created = True
                logger.debug(
                    f"ITERATION_SESSION: session_id={iteration_session_id[:8]}..., "
                    f"task_id={task.id}, iteration={iteration}/{max_iterations}"
                )

                # Assign session_id to agent for this iteration
                if hasattr(self.agent, 'session_id'):
                    self.agent.session_id = iteration_session_id
                # 1. Build context (text from accumulated context)
                context_text = self._build_context(accumulated_context)
                logger.debug(f"CONTEXT BUILT: iteration={iteration}, context_chars={len(context_text):,}")
                self._print_obra(f"Built context ({len(context_text)} chars)")

                # 2. Generate prompt (include complexity estimate if available)
                # BUG-TETRIS-001 FIX: Flatten task object into template variables
                prompt_context = {
                    # Task attributes (flattened from self.current_task)
                    'task_id': self.current_task.id,
                    'task_title': self.current_task.title,
                    'task_description': self.current_task.description,
                    'task_priority': self.current_task.priority,
                    'task_status': self.current_task.status.value if hasattr(self.current_task.status, 'value') else str(self.current_task.status),
                    'task_dependencies': self.current_task.dependencies if self.current_task.dependencies else [],

                    # Project attributes (flattened from self.current_project)
                    'project_name': self.current_project.project_name if self.current_project else 'Unknown',
                    'project_id': self.current_project.id if self.current_project else None,
                    'working_directory': self.current_project.working_directory if self.current_project else './workspace',
                    'project_goals': self.current_project.description if self.current_project and self.current_project.description else None,

                    # Context text
                    'context': context_text,

                    # Instructions (BUG-TETRIS-004 FIX: explicit working directory)
                    'instructions': f"Work in the directory: {self.current_project.working_directory if self.current_project else './workspace'}. All project files should be created there."
                }
                if complexity_estimate:
                    prompt_context['complexity_estimate'] = complexity_estimate

                prompt = self.prompt_generator.generate_prompt(
                    'task_execution',
                    prompt_context
                )

                # Phase 2, Task 2.4: Inject epic context on first task, first iteration
                if (iteration == 1 and
                    hasattr(self, '_current_epic_context') and
                    hasattr(self, '_current_epic_first_task') and
                    self._current_epic_first_task == task.id):

                    prompt = f"""[EPIC CONTEXT]
{self._current_epic_context}

[CURRENT TASK]
{prompt}
"""
                    logger.info("Injected epic context into first task")

                # Phase 3, Task 3.2: Check context window before execution
                if self.agent.use_session_persistence and hasattr(self.agent, 'session_id'):
                    session_id = self.agent.session_id
                    if session_id:
                        context_summary = self._check_context_window_manual(session_id)
                        if context_summary:
                            # Session was refreshed, prepend summary to prompt
                            prompt = f"""[CONTEXT FROM PREVIOUS SESSION]
{context_summary}

[CURRENT TASK]
{prompt}
"""
                            logger.info(f"SESSION REFRESH: session_id={session_id[:8]}..., summary_chars={len(context_summary):,}")

                # Phase 2: Interactive mode integration - Check for stop/pause/commands
                if self.interactive_mode:
                    # Update status tracking for /status command
                    self.current_task_id = task.id
                    self.current_iteration = iteration
                    self.max_turns = max_turns

                    # [1] START - Check for stop/pause/commands
                    self._check_interactive_commands()

                    if self.stop_requested:
                        raise TaskStoppedException(
                            "User requested stop",
                            context={'task_id': task.id, 'iterations_completed': iteration - 1}
                        )

                    if self.paused:
                        self._wait_for_resume()

                    # [2] PRE-PROMPT - Apply injected context
                    if self.injected_context.get('to_impl') or self.injected_context.get('to_claude'):
                        prompt = self._apply_injected_context(prompt, self.injected_context)

                # 3. Send to agent
                logger.info(f"AGENT SEND: task_id={self.current_task.id}, iteration={iteration}, prompt_chars={len(prompt):,}")
                # Phase 1: Streaming log for Obra→Claude
                logger.info(f"[OBRA→CLAUDE] Iteration {iteration}/{max_iterations} | Prompt: {len(prompt):,} chars")
                self._print_obra(f"Sending prompt to Claude Code...", "[OBRA→CLAUDE]")
                # Phase 4, Task 4.2: Pass context with max_turns (if present) and task_id
                agent_context = context.copy() if context else {}
                agent_context['task_id'] = self.current_task.id
                response = self.agent.send_prompt(prompt, context=agent_context)
                # Phase 1: Streaming log for Claude→Obra
                logger.info(f"[CLAUDE→OBRA] Response received | {len(response):,} chars")
                self._print_obra(f"Response received ({len(response)} chars)")

                # Phase 2, Task 2.4: Update session usage tracking
                # Phase 3, Task 3.2: Add token tracking for context window management
                if hasattr(self.agent, 'get_last_metadata'):
                    metadata = self.agent.get_last_metadata()
                    if metadata and metadata.get('session_id'):
                        try:
                            # Extract and log metadata
                            total_tokens = metadata.get('total_tokens', 0)
                            input_tokens = metadata.get('input_tokens', 0)
                            cache_read_tokens = metadata.get('cache_read_tokens', 0)
                            output_tokens = metadata.get('output_tokens', 0)
                            num_turns = metadata.get('num_turns', 0)
                            duration_ms = metadata.get('duration_ms', 0)
                            cache_hit_rate = metadata.get('cache_hit_rate', 0.0)

                            logger.info(
                                f"RESPONSE METADATA: iteration={iteration}, "
                                f"tokens={total_tokens:,} "
                                f"(input={input_tokens:,}, cache_read={cache_read_tokens:,}, output={output_tokens:,}), "
                                f"turns={num_turns}, duration={duration_ms}ms, "
                                f"cache_efficiency={cache_hit_rate:.1%}"
                            )

                            # Update session-level metrics (total tokens, turns, cost)
                            self.state_manager.update_session_usage(
                                session_id=metadata['session_id'],
                                tokens=metadata.get('total_tokens', 0),
                                turns=metadata.get('num_turns', 0),
                                cost=metadata.get('cost_usd', 0.0)
                            )

                            # Add tokens to cumulative tracking for context window management
                            tokens_dict = {
                                'input_tokens': metadata.get('input_tokens', 0),
                                'cache_creation_tokens': metadata.get('cache_creation_tokens', 0),
                                'cache_read_tokens': metadata.get('cache_read_tokens', 0),
                                'output_tokens': metadata.get('output_tokens', 0)
                            }
                            # Calculate total from breakdown
                            tokens_dict['total_tokens'] = sum(tokens_dict.values())

                            self.state_manager.add_session_tokens(
                                session_id=metadata['session_id'],
                                task_id=task.id,
                                tokens_dict=tokens_dict
                            )
                            logger.debug(f"CONTEXT_WINDOW: session_id={metadata['session_id'][:8]}..., tracked={tokens_dict['total_tokens']:,} tokens")
                        except Exception as e:
                            logger.debug(f"Failed to update session usage: {e}")

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
                self._print_orch("Validating response...")
                quality_result = self.quality_controller.validate_output(
                    response,
                    self.current_task,
                    {'language': 'python'}
                )
                gate_status = "PASS" if quality_result.passes_gate else "FAIL"
                # Phase 1: Streaming log for orchestrator validation
                llm_name = self.llm_interface.get_name() if self.llm_interface else 'unknown'
                logger.info(f"[ORCH:{llm_name}] Quality: {quality_result.overall_score:.2f} ({gate_status})")
                self._print_orch(f"  Quality: {quality_result.overall_score:.2f} ({gate_status})")

                # [PHASE 2.3] Log validation guidance if user provided it
                if self.interactive_mode and self.injected_context.get('to_orch_intent') == 'validation_guidance':
                    orch_message = self.injected_context.get('to_orch', '')
                    logger.info(f"[ORCH_GUIDANCE] User validation guidance: \"{orch_message}\"")
                    self._print_orch(f"  Note: User guidance active: {orch_message[:50]}...")
                    # Note: This guidance is logged for human awareness but doesn't modify
                    # quality scoring (which uses complex rule-based heuristics, not LLM prompts)

                # 6. Confidence scoring
                confidence = self.confidence_scorer.score_response(
                    response,
                    self.current_task,
                    {'validation': is_valid, 'quality': quality_result}
                )

                # Phase 2: Update tracking variables for /status command
                if self.interactive_mode:
                    self.latest_quality_score = quality_result.overall_score
                    self.latest_confidence = confidence

                self._print_orch(f"  Confidence: {confidence:.2f}")

                # BUG-TETRIS-002 FIX: Record interaction to database
                try:
                    # Get metadata from agent if available
                    interaction_metadata = {}
                    if hasattr(self.agent, 'get_last_metadata'):
                        agent_metadata = self.agent.get_last_metadata()
                        if agent_metadata:
                            interaction_metadata = {
                                'input_tokens': agent_metadata.get('input_tokens', 0),
                                'cache_creation_input_tokens': agent_metadata.get('cache_creation_tokens', 0),
                                'cache_read_input_tokens': agent_metadata.get('cache_read_tokens', 0),
                                'output_tokens': agent_metadata.get('output_tokens', 0),
                                'total_tokens': agent_metadata.get('total_tokens', 0),
                                'duration_ms': agent_metadata.get('duration_ms', 0),
                                'num_turns': agent_metadata.get('num_turns', 0),
                                'agent_session_id': agent_metadata.get('session_id')
                            }

                    # Record interaction
                    self.state_manager.record_interaction(
                        project_id=self.current_project.id,
                        task_id=self.current_task.id,
                        interaction_data={
                            'source': InteractionSource.CLAUDE_CODE,
                            'prompt': prompt,
                            'response': response,
                            'confidence_score': confidence,
                            'quality_score': quality_result.overall_score,
                            'validation_passed': is_valid,
                            'context': {'iteration': iteration},
                            **interaction_metadata
                        }
                    )
                    logger.debug(f"Recorded interaction for task {self.current_task.id}, iteration {iteration}")
                except Exception as e:
                    logger.warning(f"Failed to record interaction: {e}")

                # BUG-TETRIS-003 FIX: Detect "no work done" scenarios before decision
                # These heuristics prevent false positives where agent just asks questions or expresses confusion
                no_work_indicators = []
                response_lower = response.lower()

                # Heuristic 1: Response too short for real work (first iteration only)
                if iteration == 1 and len(response) < 500:
                    no_work_indicators.append("response_too_short")

                # Heuristic 2: Contains confusion/question phrases
                confusion_phrases = [
                    ('empty', 'directory'),
                    ('not sure', ''),
                    ('confused', ''),
                    ("don't know", ''),
                    ('unclear', ''),
                    ('what should', '')
                ]
                for phrase1, phrase2 in confusion_phrases:
                    if phrase1 in response_lower and (not phrase2 or phrase2 in response_lower):
                        no_work_indicators.append(f"confusion_phrase:{phrase1}")
                        break

                # Heuristic 3: No files modified (if file watcher available and first iteration)
                if iteration == 1 and hasattr(self, 'file_watcher') and self.file_watcher:
                    try:
                        file_changes = self.file_watcher.get_changes()
                        if len(file_changes) == 0:
                            no_work_indicators.append("no_files_modified")
                    except Exception:
                        pass  # Ignore file watcher errors

                # Heuristic 4: Response is mostly questions (contains many ? without deliverables)
                question_count = response.count('?')
                if question_count > 3 and 'created' not in response_lower and 'implemented' not in response_lower:
                    no_work_indicators.append("mostly_questions")

                # If we detect "no work done" on first iteration, force CLARIFY
                if no_work_indicators and iteration == 1:
                    logger.warning(f"No work done detected: {', '.join(no_work_indicators)}")
                    logger.info("Forcing CLARIFY decision to request actual work")
                    accumulated_context.append({
                        'type': 'feedback',
                        'content': f"Previous response did not contain actionable work. Please actually perform the requested task instead of just describing or asking questions. Create files, write code, generate documentation as specified in the requirements.",
                        'timestamp': datetime.now(UTC)
                    })
                    continue  # Skip to next iteration

                # 7. Decision making
                decision_context = {
                    'task': self.current_task,
                    'response': response,
                    'validation_result': {'valid': is_valid, 'complete': True},
                    'quality_score': quality_result.overall_score,
                    'confidence_score': confidence
                }

                # [PHASE 2.3] Apply decision hint if user provided guidance
                threshold_adjustment = 0.0
                if self.interactive_mode and self.injected_context.get('to_orch_intent') == 'decision_hint':
                    # User wants to override decision - lower threshold temporarily
                    threshold_adjustment = 0.15  # Make decision more lenient
                    orch_message = self.injected_context.get('to_orch', '')
                    logger.info(f"[ORCH_HINT] User decision hint active: \"{orch_message}\" "
                               f"(adjusting thresholds by +{threshold_adjustment})")
                    self._print_orch(f"  Applying decision hint: {orch_message[:50]}...")

                action = self.decision_engine.decide_next_action(decision_context, threshold_adjustment)

                # Phase 2: Allow user to override decision
                if self.interactive_mode and self.injected_context.get('override_decision'):
                    override_str = self.injected_context.pop('override_decision')
                    # Map command strings to DecisionEngine action types
                    decision_map = {
                        'proceed': DecisionEngine.ACTION_PROCEED,
                        'retry': DecisionEngine.ACTION_RETRY,
                        'clarify': DecisionEngine.ACTION_CLARIFY,
                        'escalate': DecisionEngine.ACTION_ESCALATE,
                        'checkpoint': DecisionEngine.ACTION_CHECKPOINT,
                    }

                    if override_str in decision_map:
                        # Create new action with overridden type
                        from src.orchestration.decision_engine import Action
                        action = Action(
                            type=decision_map[override_str],
                            confidence=1.0,  # User override has full confidence
                            explanation=f"User override: {override_str}",
                            metadata={'user_override': True},
                            timestamp=datetime.now(UTC)
                        )
                        logger.info(f"[USER OVERRIDE] Decision changed to: {action.type}")

                # Phase 1: Streaming log for decision
                logger.info(f"[OBRA] Decision: {action.type} | Confidence: {action.confidence:.2f}")
                logger.info(f"Decision: {action.type} (confidence: {action.confidence:.2f})")
                self._print_obra(f"Decision: {action.type}")

                # [PHASE 2.3] Generate feedback if user requested analysis
                if self.interactive_mode and self.injected_context.get('to_orch_intent') == 'feedback_request':
                    orch_message = self.injected_context.get('to_orch', '')
                    logger.info(f"[ORCH_FEEDBACK] Generating feedback based on user request: \"{orch_message}\"")
                    self._print_orch(f"  Generating feedback: {orch_message[:50]}...")

                    try:
                        # Build feedback prompt for orchestrator LLM
                        feedback_prompt = f"""Analyze the following code implementation and provide feedback.

User Request: {orch_message}

Task Description:
{self.current_task.description}

Implementation (Response):
{response[:2000]}...

Provide concise, actionable feedback focusing on what the user requested. Be specific."""

                        # Generate feedback using orchestrator LLM
                        feedback = self.llm_interface.generate(
                            feedback_prompt,
                            max_tokens=500,
                            temperature=0.3
                        )

                        # Inject feedback into next implementer prompt
                        feedback_message = f"ORCHESTRATOR FEEDBACK:\n{feedback}\n\nPlease address this feedback in your next iteration."
                        self.injected_context['to_impl'] = feedback_message
                        self.injected_context['to_claude'] = feedback_message  # Legacy key

                        logger.info(f"[ORCH_FEEDBACK] Generated {len(feedback)} chars of feedback, injected for next iteration")
                        self._print_orch(f"  Feedback generated ({len(feedback)} chars) → will be sent to implementer")

                    except Exception as e:
                        logger.error(f"[ORCH_FEEDBACK] Failed to generate feedback: {e}")
                        self._print_orch(f"  Error generating feedback: {str(e)}")

                # Phase 2: Clear injected context based on decision (persist through RETRY)
                if self.interactive_mode:
                    if action.type == DecisionEngine.ACTION_PROCEED:
                        # Clear context on success
                        # Clear both new and legacy keys
                        self.injected_context.pop('to_impl', None)
                        self.injected_context.pop('to_orch', None)
                        self.injected_context.pop('to_orch_intent', None)
                        # Keep legacy keys for backward compat
                        self.injected_context.pop('to_claude', None)
                        self.injected_context.pop('to_obra', None)
                    elif action.type == DecisionEngine.ACTION_ESCALATE:
                        # Clear context on escalation (user will re-inject if needed)
                        self.injected_context.clear()
                    # For RETRY and CLARIFY, preserve context for next attempt

                # 8. Handle decision
                if action.type == DecisionEngine.ACTION_PROCEED:
                    # Task completed successfully
                    self.state_manager.update_task_status(
                        self.current_task.id,
                        TaskStatus.COMPLETED
                    )

                    # Parse parallel metadata from Claude's response
                    parallel_metadata = self._parse_parallel_metadata(response)

                    return {
                        'status': 'completed',
                        'response': response,
                        'iterations': iteration,
                        'quality_score': quality_result.overall_score,
                        'confidence': confidence,
                        'parallel_metadata': parallel_metadata
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

            except AgentException as e:
                # Phase 4, Task 4.2: Let error_max_turns propagate to retry loop
                if e.context_data.get('subtype') == 'error_max_turns':
                    logger.debug(f"Propagating error_max_turns exception to retry loop")
                    raise
                # Other agent errors - log and continue
                logger.error(f"Iteration {iteration} failed: {e}", exc_info=True)
                accumulated_context.append({
                    'type': 'error',
                    'content': f"Error: {str(e)}",
                    'timestamp': datetime.now(UTC)
                })
            except Exception as e:
                logger.error(f"Iteration {iteration} failed: {e}", exc_info=True)
                accumulated_context.append({
                    'type': 'error',
                    'content': f"Error: {str(e)}",
                    'timestamp': datetime.now(UTC)
                })
            finally:
                # BUG-PHASE4-006 FIX: Always complete session and restore agent state
                if session_created:
                    try:
                        # Complete session record for this iteration
                        self.state_manager.complete_session_record(
                            session_id=iteration_session_id,
                            ended_at=datetime.now(UTC)
                        )
                        logger.debug(f"ITERATION_SESSION_END: session_id={iteration_session_id[:8]}...")
                    except Exception as e:
                        logger.warning(f"Failed to complete iteration session {iteration_session_id[:8]}...: {e}")

                # Restore agent's previous session_id
                if hasattr(self.agent, 'session_id'):
                    self.agent.session_id = old_agent_session_id

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

    def _parse_parallel_metadata(self, agent_response: str) -> Dict[str, Any]:
        """Parse parallel execution metadata from Claude's response.

        Claude may use Task tool to deploy agents. This parses whether
        Claude chose to parallelize and what tasks were executed.

        Args:
            agent_response: Response from agent

        Returns:
            Dict with: parallel_execution_used, parallel_decision_rationale, tasks_parallelized
        """
        from src.utils.json_extractor import extract_json

        try:
            response_json = extract_json(agent_response)

            if response_json:
                return {
                    'parallel_execution_used': response_json.get('parallel_execution_used', False),
                    'parallel_decision_rationale': response_json.get('parallel_decision_rationale', ''),
                    'tasks_parallelized': response_json.get('tasks_parallelized', [])
                }
        except Exception as e:
            logger.debug(f"Could not parse parallel metadata: {e}")

        return {
            'parallel_execution_used': False,
            'parallel_decision_rationale': 'Could not parse response',
            'tasks_parallelized': []
        }

    def _estimate_task_complexity(
        self,
        task: Task,
        context: Optional[Dict[str, Any]] = None
    ) -> ComplexityEstimate:
        """Estimate task complexity and log to StateManager.

        Args:
            task: Task to estimate
            context: Optional execution context

        Returns:
            ComplexityEstimate with all fields populated
        """
        try:
            logger.info(f"Estimating complexity for task {task.id}")

            estimate = self.complexity_estimator.estimate_complexity(
                task=task,
                context=context
            )

            # Update task_id if not set (ComplexityEstimator sets it, but verify)
            if estimate.task_id == 0:
                estimate = ComplexityEstimate(
                    task_id=task.id,
                    estimated_tokens=estimate.estimated_tokens,
                    estimated_loc=estimate.estimated_loc,
                    estimated_files=estimate.estimated_files,
                    complexity_score=estimate.complexity_score,
                    should_decompose=estimate.should_decompose,
                    decomposition_suggestions=estimate.decomposition_suggestions,
                    parallelization_opportunities=estimate.parallelization_opportunities,
                    estimated_duration_minutes=estimate.estimated_duration_minutes,
                    confidence=estimate.confidence,
                    timestamp=estimate.timestamp
                )

            logger.info(
                f"Task {task.id} complexity: {estimate.complexity_score}/100 "
                f"({estimate.get_complexity_category()}), "
                f"should_decompose={estimate.should_decompose}"
            )

            return estimate

        except Exception as e:
            logger.error(f"Failed to estimate complexity: {e}")
            # Return a default estimate
            return ComplexityEstimate(
                task_id=task.id,
                estimated_tokens=4000,
                estimated_loc=100,
                estimated_files=1,
                complexity_score=50.0,
                should_decompose=False,
                decomposition_suggestions=[],
                parallelization_opportunities=[],
                estimated_duration_minutes=60,
                confidence=0.5,
                timestamp=datetime.now()
            )

    def _generate_session_summary(self, session_id: str, milestone_id: Optional[int] = None) -> str:
        """Generate summary of session using Qwen (local LLM).

        Creates a concise summary of what was accomplished in a Claude Code session,
        focusing on implementation decisions, codebase state, and next steps.

        Args:
            session_id: Session ID to summarize
            milestone_id: Optional milestone ID for context

        Returns:
            str: Concise summary (target <5000 tokens)

        Raises:
            OrchestratorException: If summary generation fails
        """
        try:
            logger.info(f"Generating summary for session {session_id}")

            # TODO: Get session-specific interactions once StateManager.get_session_interactions() is implemented
            # For now, we'll use project interactions and filter by session_id in metadata

            # Get session record to find project_id
            session_record = None
            try:
                # Get session record using StateManager method (implemented in Phase 2, Task 2.1)
                session_record = self.state_manager.get_session_record(session_id)
            except Exception as e:
                logger.warning(f"Could not retrieve session record: {e}")

            if not session_record:
                # Fallback: use current project if available
                if not self.current_project:
                    raise OrchestratorException(
                        "Cannot generate summary without session or project context",
                        context={'session_id': session_id},
                        recovery="Ensure orchestrator has active project"
                    )
                project_id = self.current_project.id
            else:
                project_id = session_record.project_id

            # Get interactions for the project
            interactions = self.state_manager.get_interactions(
                project_id=project_id,
                limit=100  # Get up to 100 recent interactions
            )

            # Filter interactions by session_id if available in metadata
            session_interactions = []
            for interaction in interactions:
                metadata = interaction.metadata or {}
                if metadata.get('session_id') == session_id:
                    session_interactions.append(interaction)

            # If no session-specific interactions found, use all recent interactions
            if not session_interactions:
                logger.warning(f"No session-specific interactions found for {session_id}, using all recent")
                session_interactions = interactions

            # Build context for summarization
            context_parts = []

            # Add milestone info if provided
            if milestone_id:
                context_parts.append(f"## Milestone Context\n")
                context_parts.append(f"Milestone ID: {milestone_id}\n")
                context_parts.append(f"This session was working toward milestone {milestone_id} objectives.\n\n")

            # Add interaction history
            context_parts.append(f"## Session Interactions ({len(session_interactions)} total)\n\n")

            for i, interaction in enumerate(session_interactions[:20], 1):  # Limit to 20 most recent
                context_parts.append(f"### Interaction {i}\n")
                context_parts.append(f"**Source**: {interaction.source}\n")
                context_parts.append(f"**Timestamp**: {interaction.timestamp}\n\n")

                # Add prompt (truncated if too long)
                prompt_preview = interaction.prompt[:500] + "..." if len(interaction.prompt) > 500 else interaction.prompt
                context_parts.append(f"**Prompt**:\n```\n{prompt_preview}\n```\n\n")

                # Add response (truncated if too long)
                if interaction.response:
                    response_preview = interaction.response[:1000] + "..." if len(interaction.response) > 1000 else interaction.response
                    context_parts.append(f"**Response**:\n```\n{response_preview}\n```\n\n")

            context_text = "".join(context_parts)

            # Generate summary prompt
            summary_prompt = f"""You are analyzing a Claude Code development session. Generate a concise summary focusing on:

1. **What was accomplished**: Key features/fixes implemented
2. **Implementation decisions**: Important technical choices made
3. **Current codebase state**: What's working, what's in progress
4. **Issues encountered**: Problems faced and how they were resolved
5. **Next steps**: What should be done next to continue progress

## Session Data

{context_text}

## Instructions

Provide a concise summary (target 500-1000 tokens, MAX 1200 tokens). Focus on actionable information for the next session.
Use clear section headers and bullet points for readability.

DO NOT repeat the raw interaction data - synthesize and summarize it.
"""

            # Generate summary using Qwen
            logger.info("Calling Qwen to generate summary...")
            summary = self.llm_interface.generate(
                prompt=summary_prompt,
                temperature=0.3,  # Low temperature for consistent, factual summaries
                max_tokens=1500   # Allow enough tokens for comprehensive summary
            )

            logger.info(f"Generated summary ({len(summary)} chars) for session {session_id}")
            return summary

        except Exception as e:
            logger.error(f"Failed to generate session summary: {e}", exc_info=True)
            raise OrchestratorException(
                f"Session summary generation failed: {e}",
                context={'session_id': session_id, 'milestone_id': milestone_id},
                recovery="Check LLM availability and session data"
            ) from e

    def _refresh_session_with_summary(self) -> Tuple[str, str]:
        """Refresh session before hitting context limit.

        Creates a new session, generates a summary of the old session,
        and transfers context to continue work seamlessly.

        Args:
            None (uses self.agent.session_id internally)

        Returns:
            Tuple[str, str]: (new_session_id, context_summary)

        Raises:
            OrchestratorException: If refresh fails

        Example:
            >>> new_session_id, summary = orchestrator._refresh_session_with_summary()
            >>> # Continue work with new session
        """
        try:
            # Get old session ID from agent
            old_session_id = self.agent.session_id if hasattr(self.agent, 'session_id') else None
            if not old_session_id:
                raise OrchestratorException(
                    "Cannot refresh session: no active session_id in agent",
                    recovery="Ensure agent has session_id attribute set"
                )

            # Get current epic_id (if exists, else None) - DB column still named milestone_id
            milestone_id = self._current_epic_id

            # Generate summary using existing method
            summary = self._generate_session_summary(old_session_id, milestone_id)

            # Create new session ID
            new_session_id = str(uuid.uuid4())

            # Update agent with new session
            self.agent.session_id = new_session_id

            # Create new session record in database
            # Get project_id from old session or current project
            old_session = self.state_manager.get_session_record(old_session_id)
            project_id = old_session.project_id if old_session else (
                self.current_project.id if self.current_project else None
            )

            if not project_id:
                raise OrchestratorException(
                    "Cannot create new session: no project_id available",
                    context={'old_session_id': old_session_id},
                    recovery="Ensure session has project_id or current_project is set"
                )

            self.state_manager.create_session_record(
                session_id=new_session_id,
                project_id=project_id,
                milestone_id=milestone_id
            )

            # Mark old session as 'refreshed'
            if old_session:
                old_session.status = 'refreshed'
                old_session.ended_at = datetime.now(UTC)
                old_session.summary = summary

            # Log info message with both session IDs
            logger.info(
                f"Session refreshed: {old_session_id[:8]}... → {new_session_id[:8]}... "
                f"(summary: {len(summary)} chars)"
            )

            return (new_session_id, summary)

        except Exception as e:
            logger.error(f"Session refresh failed: {e}", exc_info=True)
            raise OrchestratorException(
                f"Failed to refresh session: {e}",
                context={
                    'old_session_id': old_session_id if 'old_session_id' in locals() else None,
                    'error': str(e)
                },
                recovery="Check session state and LLM availability"
            ) from e

    # =========================================================================
    # CONTEXT WINDOW MANAGEMENT (Phase 3, Tasks 3B.3 + 3.2)
    # =========================================================================

    def _check_context_window_manual(self, session_id: str) -> Optional[str]:
        """Check context window using manual token tracking.

        Monitors cumulative token usage and triggers appropriate actions
        based on configured thresholds:
        - Warning (70%): Log warning
        - Refresh (80%): Auto-refresh session with summary
        - Critical (95%): Emergency handling

        Args:
            session_id: Session to check

        Returns:
            Optional[str]: Context summary if session was refreshed, None otherwise

        Example:
            >>> summary = orchestrator._check_context_window_manual(session_id)
            >>> if summary:
            ...     # Prepend summary to next prompt
            ...     prompt = f"[CONTEXT]\\n{summary}\\n\\n{prompt}"
        """
        try:
            # Get configuration
            config = self.config.get('session', {}).get('context_window', {})
            limit = config.get('limit', 200000)  # Claude Pro default
            thresholds = config.get('thresholds', {})

            warning_pct = thresholds.get('warning', 0.70)
            refresh_pct = thresholds.get('refresh', 0.80)
            critical_pct = thresholds.get('critical', 0.95)

            # Get current usage
            current_tokens = self.state_manager.get_session_token_usage(session_id)
            pct = current_tokens / limit if limit > 0 else 0

            # Check thresholds
            if pct >= critical_pct:
                # CRITICAL: Emergency handling
                logger.error(
                    f"CONTEXT_WINDOW CRITICAL: session_id={session_id[:8]}..., "
                    f"usage={pct:.1%} ({current_tokens:,}/{limit:,}) - forcing refresh"
                )
                new_session_id, summary = self._refresh_session_with_summary()
                logger.info(f"CONTEXT_WINDOW REFRESH: emergency refresh completed, new_session={new_session_id[:8]}...")
                return summary

            elif pct >= refresh_pct:
                # REFRESH: Auto-refresh session
                logger.info(
                    f"CONTEXT_WINDOW REFRESH: session_id={session_id[:8]}..., "
                    f"usage={pct:.1%} ({current_tokens:,}/{limit:,}) "
                    f"- auto-refreshing (threshold={refresh_pct:.0%})"
                )
                new_session_id, summary = self._refresh_session_with_summary()
                logger.info(f"CONTEXT_WINDOW REFRESH: new_session={new_session_id[:8]}..., summary_chars={len(summary):,}")
                return summary

            elif pct >= warning_pct:
                # WARNING: Just log
                logger.warning(
                    f"CONTEXT_WINDOW WARNING: session_id={session_id[:8]}..., "
                    f"usage={pct:.1%} ({current_tokens:,}/{limit:,}) "
                    f"- approaching refresh threshold ({refresh_pct:.0%})"
                )

            return None

        except Exception as e:
            logger.error(f"CONTEXT_WINDOW CHECK ERROR: {e}", exc_info=True)
            # Don't raise - allow execution to continue
            return None

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
                self.file_watcher.stop_watching()

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
