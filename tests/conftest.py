"""Pytest configuration and shared fixtures."""

import gc
import json
import time
import threading
import pytest
from typing import Dict, Any, List
from unittest.mock import Mock, MagicMock
from src.plugins.registry import AgentRegistry, LLMRegistry
from src.core.config import Config


def pytest_addoption(parser):
    """Add custom command-line options to pytest.

    Adds --profile option to enable testing with different LLM providers.
    """
    parser.addoption(
        "--profile",
        action="store",
        default=None,
        help="Test profile to use (ollama, openai, etc.). "
             "Profiles are loaded from config/profiles/test-{profile}.yaml. "
             "If not specified, uses mock config for unit tests."
    )


@pytest.fixture
def test_config(request):
    """Create test configuration with optional profile support.

    If --profile option is provided, loads configuration from the specified
    test profile (config/profiles/test-{profile}.yaml). Otherwise, returns
    a Mock object with test data for unit tests.

    Args:
        request: pytest request fixture (provides access to CLI options)

    Returns:
        Config object (from profile) or Mock object (for unit tests)

    Example:
        # Unit tests (no profile, uses mock)
        pytest tests/unit/test_profile_loader.py

        # Integration tests with Ollama
        pytest --profile=ollama tests/integration/

        # Integration tests with OpenAI
        pytest --profile=openai tests/integration/
    """
    profile_name = request.config.getoption("--profile")

    # If profile specified, load it
    if profile_name:
        from src.testing.profile_loader import (
            load_profile,
            ProfileNotFoundError,
            ProfileValidationError
        )

        try:
            base_config = Config.load()
            return load_profile(profile_name, base_config)
        except ProfileNotFoundError as e:
            pytest.exit(
                f"\nProfile Error: {e}\n\n"
                f"Available profiles can be found in: config/profiles/\n"
                f"Usage: pytest --profile=ollama tests/integration/",
                returncode=1
            )
        except ProfileValidationError as e:
            pytest.exit(
                f"\nProfile Validation Error: {e}\n\n"
                f"Check the profile file for missing fields or environment variables.",
                returncode=1
            )

    # No profile specified, use mock config for unit tests
    mock_config = MagicMock(spec=Config)
    test_data = {
        'database': {'url': 'sqlite:///:memory:'},
        'agent': {'type': 'claude-code-local', 'config': {}},
        'llm': {
            'type': 'mock',  # LLM type for registry lookup
            'provider': 'mock',  # Legacy field for backward compatibility
            'model': 'test',
            'base_url': 'http://localhost:11434'
        },
        'orchestration': {
            'breakpoints': {'confidence_threshold': 0.7},
            'decision': {
                'high_confidence': 0.85,
                'medium_confidence': 0.65
            },
            'quality': {'min_quality_score': 0.7},
            'scheduler': {'max_concurrent_tasks': 1}
        },
        'utils': {
            'token_counter': {'default_model': 'gpt-4'},
            'context_manager': {'max_tokens': 100000},
            'confidence_scorer': {}
        },
        'context': {'max_tokens': 100000}
    }

    mock_config._config = test_data

    # Implement get method that traverses dotted keys
    def get_nested(key, default=None):
        keys = key.split('.')
        value = test_data
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    mock_config.get = get_nested

    return mock_config


@pytest.fixture
def profile_name(request):
    """Get active test profile name.

    Returns the profile name specified via --profile option,
    or None if no profile was specified.

    Returns:
        Profile name (str) or None

    Example:
        def test_uses_correct_llm(profile_name, test_config):
            if profile_name == "openai":
                assert test_config.get('llm.type') == 'openai-codex'
            elif profile_name == "ollama":
                assert test_config.get('llm.type') == 'ollama'
    """
    return request.config.getoption("--profile")


@pytest.fixture(autouse=True)
def reset_registries():
    """Clear plugin registries before each test.

    This ensures tests don't interfere with each other through
    shared registry state.
    """
    # Setup: Manually re-register core plugins at start of each test
    # (needed because decorators only run once on module import)
    from src.plugins.registry import register_agent, register_llm
    from src.agents.mock_agent import MockAgent
    from src.agents.claude_code_local import ClaudeCodeLocalAgent
    from src.llm.local_interface import LocalLLMInterface
    from src.llm.openai_codex_interface import OpenAICodexLLMPlugin
    from tests.mocks.mock_llm import MockLLM

    # Re-register agents
    register_agent('mock')(MockAgent)
    register_agent('claude-code-local')(ClaudeCodeLocalAgent)
    register_agent('local')(ClaudeCodeLocalAgent)  # Alias

    # Re-register LLMs
    register_llm('ollama')(LocalLLMInterface)
    register_llm('openai-codex')(OpenAICodexLLMPlugin)
    register_llm('mock')(MockLLM)

    yield

    # Teardown: clear registries after test
    AgentRegistry.clear()
    LLMRegistry.clear()


@pytest.fixture(autouse=True)
def cleanup_resources(request):
    """Clean up resources after each test to prevent leaks.

    This is critical for preventing resource accumulation that can
    crash WSL2, especially with SSH connections and file descriptors.

    OPTIMIZATION: Only performs expensive paramiko cleanup for tests
    that actually use SSH, avoiding 453 gc.get_objects() scans that
    were causing WSL2 crashes.
    """
    yield
    # Force garbage collection to clean up any lingering connections
    gc.collect()

    # Clean up watchdog observers specifically (for file_watcher tests)
    try:
        from watchdog.observers import Observer
        from watchdog.observers.polling import PollingObserver

        # Stop any lingering observers
        for obj in gc.get_objects():
            if isinstance(obj, (Observer, PollingObserver)):
                try:
                    if hasattr(obj, 'is_alive') and obj.is_alive():
                        obj.stop()
                        obj.join(timeout=1.0)
                except Exception:
                    pass
    except (ImportError, Exception):
        pass  # watchdog not available or cleanup failed

    # Clean up any active threads (except main and daemon threads we don't own)
    try:
        active_threads = threading.enumerate()
        for thread in active_threads:
            # Skip main thread and system threads
            if thread == threading.main_thread():
                continue
            # Skip threads we don't own (pytest internal, etc.)
            if not hasattr(thread, '_target'):
                continue
            # Try to join with short timeout (reduced from 0.5s to 0.1s)
            if thread.is_alive() and thread != threading.current_thread():
                thread.join(timeout=0.1)
    except Exception:
        pass

    # CRITICAL OPTIMIZATION: Only clean up paramiko for SSH tests
    # This avoids calling gc.get_objects() 453 times (was causing WSL2 crashes)
    # Only run for tests in files that actually use SSH/paramiko
    test_file = request.node.fspath.basename
    ssh_test_files = {'test_claude_code_ssh.py', 'test_core.py', 'test_plugins.py'}

    if test_file in ssh_test_files:
        try:
            import paramiko
            # Close any active transport connections
            # NOTE: gc.get_objects() is VERY expensive - only use when necessary
            for obj in gc.get_objects():
                if isinstance(obj, paramiko.Transport):
                    try:
                        obj.close()
                    except Exception:
                        pass
        except ImportError:
            pass  # paramiko not available, skip


@pytest.fixture
def fast_time(monkeypatch):
    """Mock time functions for fast test execution.

    Replaces time.sleep() with instant time advancement and time.time()
    with controlled time tracking. This eliminates blocking sleeps that
    can cause WSL2 resource exhaustion.

    Usage:
        def test_with_timing(fast_time):
            start = time.time()
            time.sleep(2.0)  # Instant, no blocking
            elapsed = time.time() - start
            assert elapsed == 2.0
    """
    current_time = [time.time()]  # Use list for mutability in closure

    def fake_sleep(duration):
        """Advance time without blocking."""
        if duration > 0:
            current_time[0] += duration

    def fake_time():
        """Return current mocked time."""
        return current_time[0]

    # Patch both time.sleep and time.time
    monkeypatch.setattr('time.sleep', fake_sleep)
    monkeypatch.setattr('time.time', fake_time)

    return Mock(advance=lambda d: fake_sleep(d), now=fake_time)


@pytest.fixture
def monitor_with_cleanup():
    """Create OutputMonitor with guaranteed cleanup.

    Ensures the monitor is properly stopped and threads are cleaned up,
    preventing resource leaks that cause WSL2 crashes.

    Usage:
        def test_monitor(monitor_with_cleanup):
            monitor = monitor_with_cleanup(completion_timeout=0.1)
            # ... use monitor ...
            # Cleanup happens automatically
    """
    monitors = []

    def create_monitor(**kwargs):
        from src.agents.output_monitor import OutputMonitor
        # Use fast timeouts by default
        if 'completion_timeout' not in kwargs:
            kwargs['completion_timeout'] = 0.1
        monitor = OutputMonitor(**kwargs)
        monitors.append(monitor)
        return monitor

    yield create_monitor

    # Cleanup all created monitors
    for monitor in monitors:
        try:
            if monitor.is_monitoring:
                monitor.stop_monitoring()
            # Give thread minimal time to exit (reduced from 0.01s)
            time.sleep(0.001)
        except Exception:
            pass


# ============================================================================
# Agile Hierarchy Fixtures (ADR-013)
# ============================================================================

@pytest.fixture
def state_manager(test_config):
    """Create StateManager with in-memory database for testing.

    Uses test_config fixture to create a properly configured
    StateManager instance for Agile hierarchy tests.
    """
    from src.core.state import StateManager

    db_url = test_config.get('database.url', 'sqlite:///:memory:')
    state = StateManager(db_url)

    yield state

    # Cleanup
    try:
        state.close()
    except Exception:
        pass


@pytest.fixture
def sample_project(state_manager):
    """Create a sample project for testing.

    Creates a basic project that can be used for testing
    epic/story/milestone creation.
    """
    project = state_manager.create_project(
        name="Test Project",
        description="Test project for Agile hierarchy tests",
        working_dir="/tmp/test"
    )

    return project


# ============================================================================
# Mock LLM Response Fixtures (Valid Obra Schema)
# ============================================================================

@pytest.fixture
def mock_llm_responses() -> Dict[str, str]:
    """
    Valid JSON responses matching Obra entity schema.

    Used by mock LLMs to return realistic, parseable responses.
    Each response matches the schema in src/nl/schemas/obra_schema.json.

    Returns:
        Dictionary mapping entity_type -> valid JSON response
    """
    return {
        # Epic creation
        "epic": json.dumps({
            "entity_type": "epic",
            "entities": [{
                "title": "User Authentication System",
                "description": "Complete auth with OAuth, MFA, session management",
                "priority": 3
            }],
            "confidence": 0.92,
            "reasoning": "Clear epic with title, description, and priority"
        }),

        # Story creation
        "story": json.dumps({
            "entity_type": "story",
            "entities": [{
                "title": "Password Reset Flow",
                "description": "As a user, I want to reset my password so I can regain access",
                "epic_id": 1
            }],
            "confidence": 0.88,
            "reasoning": "User story format with epic reference"
        }),

        # Task creation
        "task": json.dumps({
            "entity_type": "task",
            "entities": [{
                "title": "Implement password hashing",
                "description": "Use bcrypt for secure password storage",
                "story_id": 1,
                "dependencies": []
            }],
            "confidence": 0.90,
            "reasoning": "Technical task with clear title and story reference"
        }),

        # Subtask creation
        "subtask": json.dumps({
            "entity_type": "subtask",
            "entities": [{
                "title": "Write unit tests for password validation",
                "parent_task_id": 1
            }],
            "confidence": 0.93,
            "reasoning": "Clear subtask with parent reference"
        }),

        # Milestone creation
        "milestone": json.dumps({
            "entity_type": "milestone",
            "entities": [{
                "name": "Auth Complete",
                "description": "All authentication features implemented",
                "required_epic_ids": [1, 2]
            }],
            "confidence": 0.94,
            "reasoning": "Milestone with epic dependencies"
        }),

        # Project query
        "project": json.dumps({
            "entity_type": "project",
            "entities": [],
            "confidence": 0.85,
            "reasoning": "Project-level information request"
        }),

        # Multi-entity (batch creation)
        "multi_task": json.dumps({
            "entity_type": "task",
            "entities": [
                {"title": "Task 1", "description": "First task"},
                {"title": "Task 2", "description": "Second task"},
                {"title": "Task 3", "description": "Third task"}
            ],
            "confidence": 0.87,
            "reasoning": "Batch task creation with 3 items"
        }),

        # Intent classification - COMMAND
        "intent_command": json.dumps({
            "intent": "COMMAND",
            "confidence": 0.95,
            "reasoning": "Clear action verb 'create' indicates command intent"
        }),

        # Intent classification - QUESTION
        "intent_question": json.dumps({
            "intent": "QUESTION",
            "confidence": 0.92,
            "reasoning": "Question word 'what' and query pattern indicate information request"
        }),

        # Invalid responses for error testing
        "invalid_null_entity_type": json.dumps({
            "entity_type": None,
            "entities": [{"title": "Test"}],
            "confidence": 0.8,
            "reasoning": "Test case"
        }),

        "invalid_missing_entity_type": json.dumps({
            "entities": [{"title": "Test"}],
            "confidence": 0.8,
            "reasoning": "Test case"
        })
    }


@pytest.fixture
def mock_llm_smart(mock_llm_responses):
    """
    Smart mock LLM that returns valid responses based on input.

    Analyzes the prompt to determine entity type and returns
    appropriate valid JSON from mock_llm_responses fixture.

    Usage:
        mock = mock_llm_smart
        llm_interface.llm = mock
    """
    mock = MagicMock()

    def smart_generate(prompt: str, **kwargs) -> str:
        """Return appropriate response based on prompt content"""
        prompt_lower = prompt.lower()

        # Intent classification
        if '"intent":' in prompt_lower or 'classify' in prompt_lower:
            # Extract the actual user message for more accurate classification
            user_msg_marker = "## user message"
            if user_msg_marker in prompt_lower:
                msg_start = prompt_lower.find(user_msg_marker) + len(user_msg_marker)
                user_msg = prompt_lower[msg_start:].strip()
            else:
                user_msg = prompt_lower

            # Check for Obra-specific work item entities
            obra_work_items = ['project', 'epic', 'story', 'task', 'subtask', 'milestone']
            has_obra_work_items = any(item in user_msg for item in obra_work_items)

            # Check for Obra command verbs (when used with work items)
            obra_commands = ['create', 'update', 'delete', 'show', 'list', 'add']
            has_obra_command = any(cmd in user_msg for cmd in obra_commands)

            # Question words
            has_question_word = any(word in user_msg for word in ['what', 'how', 'why', 'when', 'where', 'which'])

            # Logic:
            # 1. If mentions Obra work items -> COMMAND (even with question words like "What is the current project?")
            # 2. If mentions "current project/epic/etc" -> COMMAND
            # 3. If has Obra commands AND work items -> COMMAND
            # 4. General programming questions (no work items) -> QUESTION
            if has_obra_work_items:
                return mock_llm_responses["intent_command"]
            elif 'current' in user_msg and has_obra_command:
                return mock_llm_responses["intent_command"]
            elif has_question_word and not has_obra_work_items:
                return mock_llm_responses["intent_question"]
            else:
                return mock_llm_responses["intent_command"]

        # Entity extraction - detect entity type from prompt
        # Look for the user message section (after "## User Message to Extract")
        user_message_marker = "## user message to extract"
        if user_message_marker in prompt_lower:
            # Extract just the user message part
            user_msg_start = prompt_lower.find(user_message_marker) + len(user_message_marker)
            user_message = prompt_lower[user_msg_start:].strip()
        else:
            user_message = prompt_lower

        # Check user message for entity type keywords (most specific first)
        if 'current project' in user_message or 'show me the active project' in user_message or \
           'which project' in user_message or user_message.strip().startswith('show project') or \
           user_message.strip().startswith('project'):
            return mock_llm_responses["project"]
        elif 'subtask' in user_message:
            return mock_llm_responses["subtask"]
        elif 'milestone' in user_message:
            return mock_llm_responses["milestone"]
        elif 'user story' in user_message or (('story' in user_message or 'stories' in user_message) and 'epic' not in user_message):
            return mock_llm_responses["story"]
        elif 'epic' in user_message:
            return mock_llm_responses["epic"]
        elif 'task' in user_message or 'tasks' in user_message:
            # Check for batch creation
            if any(num in user_message for num in ['3 tasks', 'three tasks', 'multiple']):
                return mock_llm_responses["multi_task"]
            else:
                return mock_llm_responses["task"]

        # Default to task if unclear
        return mock_llm_responses["task"]

    mock.generate.side_effect = smart_generate
    return mock


@pytest.fixture
def mock_llm_simple(mock_llm_responses):
    """
    Simple mock LLM that always returns task entity.

    Use when you need a basic mock and don't care about
    specific entity types (e.g., testing error handling).
    """
    mock = MagicMock()
    mock.generate.return_value = mock_llm_responses["task"]
    return mock


# ============================================================================
# Integration Test Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def integration_llm():
    """Real LLM for integration tests (session-scoped for performance)."""
    from src.llm.local_interface import LocalLLMInterface

    llm = LocalLLMInterface()
    llm.initialize({
        'model': 'qwen2.5-coder:32b',
        'endpoint': 'http://10.0.75.1:11434',
        'timeout': 60.0,
        'temperature': 0.1
    })
    return llm


@pytest.fixture
def integration_state_manager():
    """StateManager for integration tests (in-memory DB)."""
    from src.core.state import StateManager

    state = StateManager(database_url='sqlite:///:memory:')
    yield state
    state.close()


@pytest.fixture
def integration_workspace():
    """Temporary workspace for integration tests."""
    import tempfile
    import shutil
    import os

    workspace = tempfile.mkdtemp(prefix='integration_test_')
    yield workspace

    # Cleanup
    if os.path.exists(workspace):
        shutil.rmtree(workspace)


# ============================================================================
# PHASE 1: Real Component Fixtures (Integrated NL Testing)
# ============================================================================

@pytest.fixture
def real_state_manager():
    """REAL StateManager with in-memory SQLite.

    Use this instead of mocks for integration tests.
    Provides actual database operations with zero persistence.
    """
    from src.core.state import StateManager

    state = StateManager(database_url='sqlite:///:memory:')
    yield state
    state.close()


@pytest.fixture
def real_nl_processor(real_state_manager, mock_llm_realistic):
    """REAL NLCommandProcessor with realistic mock LLM.

    Uses REAL StateManager and REAL processing logic.
    Only LLM responses are mocked (but realistic).
    """
    from src.nl.nl_command_processor import NLCommandProcessor

    return NLCommandProcessor(
        llm_plugin=mock_llm_realistic,
        state_manager=real_state_manager,
        config={'nl_commands': {'enabled': True}}
    )


@pytest.fixture
def mock_llm_realistic():
    """Mock LLM with REALISTIC responses matching Qwen 2.5 Coder output.

    Responses match actual LLM output format for controlled testing.
    """
    from unittest.mock import MagicMock
    import re

    llm = MagicMock()

    # Response templates matching Qwen 2.5 Coder output format
    def generate_realistic(prompt, **kwargs):
        prompt_lower = prompt.lower()

        # Intent classification
        if "intent" in prompt_lower and "classify" in prompt_lower:
            if any(word in prompt_lower for word in ["create", "add", "make", "update", "delete", "remove"]):
                return '{"intent": "COMMAND", "confidence": 0.95}'
            elif any(word in prompt_lower for word in ["show", "list", "display", "query"]):
                return '{"intent": "COMMAND", "confidence": 0.93}'
            else:
                return '{"intent": "QUESTION", "confidence": 0.93}'

        # Operation classification - check user message directly
        if "operation" in prompt_lower and "classify" in prompt_lower:
            # Extract user message for more accurate classification
            user_msg = prompt_lower
            if "user message" in prompt_lower:
                idx = prompt_lower.find("user message")
                user_msg = prompt_lower[idx:]

            # More sophisticated matching
            if any(word in user_msg for word in ["delete", "remove"]):
                return '{"operation_type": "DELETE", "confidence": 0.94}'
            elif any(word in user_msg for word in ["update", "change", "modify", "mark", "set"]):
                return '{"operation_type": "UPDATE", "confidence": 0.93}'
            elif any(word in user_msg for word in ["show", "list", "display", "query", "find", "get", "view", "how many"]):
                return '{"operation_type": "QUERY", "confidence": 0.96}'
            elif any(word in user_msg for word in ["create", "add", "make", "new"]):
                return '{"operation_type": "CREATE", "confidence": 0.94}'
            else:
                # Default to CREATE if unclear
                return '{"operation_type": "CREATE", "confidence": 0.70}'

        # Entity type classification
        if "entity" in prompt_lower and "type" in prompt_lower:
            if "epic" in prompt_lower:
                return '{"entity_types": ["EPIC"], "confidence": 0.96}'
            elif "story" in prompt_lower or "stories" in prompt_lower:
                return '{"entity_types": ["STORY"], "confidence": 0.94}'
            elif "task" in prompt_lower:
                return '{"entity_types": ["TASK"], "confidence": 0.95}'
            elif "project" in prompt_lower:
                return '{"entity_types": ["PROJECT"], "confidence": 0.97}'
            elif "milestone" in prompt_lower:
                return '{"entity_types": ["MILESTONE"], "confidence": 0.93}'

        # Entity identifier extraction
        if "identifier" in prompt_lower or "extract" in prompt_lower:
            match = re.search(r'\b(\d+)\b', prompt)
            if match:
                return f'{{"identifier": {match.group(1)}, "confidence": 0.98}}'
            return '{"identifier": null, "confidence": 0.92}'

        # Parameter extraction
        if "parameter" in prompt_lower or "extract" in prompt_lower:
            params = {}
            # Try to extract title from quotes
            title_match = re.search(r'["\']([^"\']+)["\']', prompt)
            if title_match:
                params["title"] = title_match.group(1)
            return f'{{"parameters": {params}, "confidence": 0.90}}'

        return '{"result": "unknown", "confidence": 0.5}'

    llm.generate.side_effect = generate_realistic
    return llm


# ============================================================================
# PHASE 2: Real LLM Fixtures (Integrated NL Testing)
# ============================================================================

@pytest.fixture
def real_llm():
    """REAL LLM using OpenAI Codex (default for testing).

    This is the TRUE test - uses actual LLM via OpenAI Codex.
    Skips test gracefully if API unavailable (for CI).

    Environment:
        OPENAI_API_KEY: Required for OpenAI Codex
    """
    import os
    from src.llm.openai_codex_interface import OpenAICodexLLMPlugin

    try:
        llm = OpenAICodexLLMPlugin()
        llm.initialize({
            'model': 'gpt-5-codex',  # Explicitly use gpt-5-codex (ChatGPT account model)
            'temperature': 0.1,  # Deterministic for testing
            'timeout': 60.0
        })

        # Health check
        llm.generate("test", max_tokens=5)
        return llm

    except Exception as e:
        pytest.skip(f"OpenAI Codex unavailable: {e}")


@pytest.fixture
def real_orchestrator(real_llm, test_config):
    """REAL Orchestrator with REAL LLM and NL processing.

    This is the complete production stack for acceptance testing.
    Includes convenience method for executing NL commands directly.
    """
    from src.orchestrator import Orchestrator
    from src.core.state import StateManager
    from src.nl.nl_command_processor import NLCommandProcessor

    orchestrator = Orchestrator(config=test_config)
    orchestrator.llm_provider = real_llm

    # Initialize state manager if not already initialized
    if orchestrator.state_manager is None:
        orchestrator.state_manager = StateManager(database_url='sqlite:///:memory:')
        # Re-initialize NL components now that state_manager is set
        orchestrator._initialize_nl_components()

    # Create NL processor with real LLM
    nl_processor = NLCommandProcessor(
        llm_plugin=real_llm,
        state_manager=orchestrator.state_manager,
        config={'nl_commands': {'enabled': True}}
    )

    # Add convenience method for direct NL execution
    def execute_nl_string(nl_command: str, project_id: int, interactive: bool = False):
        """Execute NL command from string (convenience wrapper)."""
        parsed_intent = nl_processor.process(nl_command, context={'project_id': project_id})
        return orchestrator.execute_nl_command(parsed_intent, project_id, interactive)

    orchestrator.execute_nl_string = execute_nl_string
    orchestrator.nl_processor = nl_processor

    yield orchestrator

    # Cleanup
    if orchestrator.state_manager:
        orchestrator.state_manager.close()


@pytest.fixture
def real_nl_processor_with_llm(real_state_manager, real_llm):
    """REAL NLCommandProcessor with REAL LLM."""
    from src.nl.nl_command_processor import NLCommandProcessor

    return NLCommandProcessor(
        llm_plugin=real_llm,
        state_manager=real_state_manager,
        config={'nl_commands': {'enabled': True}}
    )


@pytest.fixture
def real_nl_orchestrator(real_state_manager, real_llm, test_config):
    """REAL NL orchestrator with REAL LLM - for end-to-end testing.

    This fixture provides the complete ADR-017 pipeline:
    - NLCommandProcessor: Parses commands → ParsedIntent
    - CommandExecutor: Executes ParsedIntent → ExecutionResult

    Use this for tests that need command execution results (entity IDs, etc.).
    Tests are updated to use this fixture instead of real_nl_processor_with_llm.

    Returns:
        Object with execute_nl() method for running NL commands through full pipeline
    """
    from src.nl.nl_command_processor import NLCommandProcessor
    from src.nl.command_executor import CommandExecutor

    # Create NL processor
    nl_processor = NLCommandProcessor(
        llm_plugin=real_llm,
        state_manager=real_state_manager,
        config={'nl_commands': {'enabled': True}}
    )

    # Create command executor
    command_executor = CommandExecutor(state_manager=real_state_manager)

    # Create wrapper class with execute_nl method
    class NLOrchestrator:
        def __init__(self, nl_processor, command_executor):
            self.nl_processor = nl_processor
            self.command_executor = command_executor

        def execute_nl(self, command: str, context: dict = None):
            """Execute NL command and return result with execution_result.

            Args:
                command: Natural language command to execute
                context: Optional context dict with project_id, etc.

            Returns:
                Object with:
                    - confidence: float
                    - operation_context: OperationContext
                    - execution_result: ExecutionResult (with created_ids)
                    - intent: IntentType
                    - success: bool
            """
            # Parse command
            parsed_intent = self.nl_processor.process(command, context=context or {})

            # Execute via command executor
            if parsed_intent.requires_execution:
                exec_result = self.command_executor.execute(
                    parsed_intent.operation_context,
                    project_id=context.get('project_id') if context else None
                )
            else:
                exec_result = None

            # Return unified result object
            class NLResult:
                def __init__(self, parsed_intent, execution_result):
                    self.confidence = parsed_intent.confidence
                    self.operation_context = parsed_intent.operation_context
                    self.execution_result = execution_result
                    self.intent = parsed_intent.intent_type
                    self.success = execution_result.success if execution_result else False

            return NLResult(parsed_intent, exec_result)

    return NLOrchestrator(nl_processor, command_executor)
