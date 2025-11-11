# Interactive Streaming Interface - Implementation Plan

**Plan ID**: `IMPL-2025-001-STREAMING`
**Created**: 2025-11-04
**Updated**: 2025-11-04 (Added Phase 0 clarifications)
**Status**: Ready for Implementation
**Estimated Effort**: 1 hour (Phase 0 clarifications), 4-6 hours (Phase 1-2), +2-3 hours (Phase 3 TUI)
**Total Effort**: 5-7 hours (Phase 0-2), +2-3 hours (Phase 3 TUI)

---

## Executive Summary

Implement a real-time streaming interface for Obra that allows users to:
1. View Obra↔Claude↔Qwen conversations in real-time
2. Inject commands and messages during execution
3. Override decisions and provide guidance mid-task

**Approach**: Start with enhanced CLI streaming (Option 2), evolve to TUI (Option 1) later.

---

## Problem Statement

**Current Limitations**:
- ❌ No visibility into Obra↔Claude conversation during execution
- ❌ Cannot interject or guide agents mid-task
- ❌ Must wait for task completion to see results
- ❌ Logs are write-only (no interactive feedback loop)

**User Requirements**:
- ✅ Real-time streaming of agent conversations
- ✅ Ability to pause/resume execution
- ✅ Inject messages to Claude or Obra
- ✅ Override decisions at breakpoints
- ✅ Terminal-based interface (no web UI)

---

## Architecture Overview

```json
{
  "components": {
    "streaming_handler": {
      "purpose": "Real-time log output with color coding",
      "location": "src/utils/streaming_handler.py",
      "dependencies": ["logging", "colorama"]
    },
    "command_processor": {
      "purpose": "Parse and execute user commands during execution",
      "location": "src/utils/command_processor.py",
      "dependencies": ["prompt_toolkit"]
    },
    "interactive_orchestrator": {
      "purpose": "Extended Orchestrator with pause/resume and injection",
      "location": "src/orchestrator.py (extend existing)",
      "dependencies": ["threading", "queue"]
    },
    "cli_extension": {
      "purpose": "New CLI flags for streaming mode",
      "location": "src/cli.py (extend existing)",
      "dependencies": ["click"]
    }
  }
}
```

---

## Phase 0: Clarifications and Specifications

**Duration**: 1 hour
**Priority**: P0 (Pre-implementation)
**Purpose**: Address design gaps and clarify implementation details

### 0.1: Integration Flow Specification

**Detailed integration points in `Orchestrator._execute_single_task()`:**

```python
def _execute_single_task(self, task: Task, session: Optional[SessionRecord] = None) -> Decision:
    """Execute single task iteration with interactive support.

    Integration Points:
    [1] START - Check for pause/commands
    [2] PRE-PROMPT - Apply injected context
    [3] SEND - Execute agent call
    [4] VALIDATION - Quality check (existing)
    [5] POST-DECISION - Allow decision override
    [6] END - Show interactive prompt
    """

    # [1] START of iteration - check for pause/commands
    if self.interactive_mode:
        self._check_interactive_commands()  # Process any queued commands
        if self.paused:
            self._wait_for_resume()  # Blocks until /resume
        if self.stop_requested:
            raise TaskStoppedException("User requested stop")  # New exception

    # [2] PRE-PROMPT - Build prompt and apply injected context
    prompt = self.prompt_generator.generate_prompt(
        task=task,
        session=session,
        iteration=self.current_iteration
    )

    # Apply user-injected context if present
    if self.injected_context.get('to_claude'):
        prompt = self._apply_injected_context(prompt, self.injected_context)
        # Track context window impact
        tokens_added = self.context_manager.estimate_tokens(
            self.injected_context.get('to_claude', '')
        )
        self.logger.info(f"Injected context added {tokens_added} tokens")

    # [3] SEND to agent (existing)
    self.logger.info(f"[OBRA→CLAUDE] Iteration {self.current_iteration}")
    response = self.agent.send_prompt(prompt, context={'task_id': task.id})
    self.logger.info(f"[CLAUDE→OBRA] Response received ({len(response)} chars)")

    # [4] VALIDATION and quality check (existing)
    validation_result = self.response_validator.validate(response)
    quality_score = self.quality_controller.assess_quality(response, task)
    self.logger.info(f"[QWEN] Quality: {quality_score:.2f}")

    # [5] POST-DECISION - Make decision, allow override
    decision = self.decision_engine.decide(
        quality_score=quality_score,
        validation_result=validation_result,
        iteration=self.current_iteration
    )

    # Allow user to override decision
    if self.injected_context.get('override_decision'):
        decision = self.injected_context.pop('override_decision')
        self.logger.info(f"[USER OVERRIDE] Decision changed to: {decision}")

    self.logger.info(f"[OBRA] Decision: {decision}")

    # Clear injected context ONLY on successful iteration
    # (preserves context if task fails and retries)
    if decision == Decision.PROCEED:
        self.injected_context.pop('to_claude', None)

    # [6] END of iteration - show interactive prompt
    if self.interactive_mode and not self.paused:
        self._show_interactive_prompt()  # Display "> " and wait for input

    return decision
```

**New methods to add:**

```json
{
  "methods": [
    {
      "name": "_check_interactive_commands",
      "purpose": "Process any queued commands from InputManager",
      "implementation": "Check queue, execute commands via CommandProcessor"
    },
    {
      "name": "_wait_for_resume",
      "purpose": "Block execution until user types /resume",
      "implementation": "Loop checking queue until resume flag is set"
    },
    {
      "name": "_show_interactive_prompt",
      "purpose": "Display prompt for user input",
      "implementation": "Show '> ' and wait for command (non-blocking)"
    }
  ]
}
```

### 0.2: Command Persistence Specification

**Behavior**: Injected context persists through retries, cleared only on success.

**Rationale**:
- User expects guidance to apply to task, not just single attempt
- Retries should preserve user intent
- Only clear context when task proceeds successfully

**Implementation**:

```python
# In _execute_single_task() after decision
if decision == Decision.PROCEED:
    # Clear context on success
    self.injected_context.pop('to_claude', None)
    self.injected_context.pop('to_obra', None)
elif decision == Decision.RETRY:
    # KEEP context for retry
    self.logger.info("[OBRA] Preserving injected context for retry")
elif decision == Decision.ESCALATE:
    # Clear context on escalation (user will re-inject if needed)
    self.injected_context.clear()
    self.logger.info("[OBRA] Cleared injected context due to escalation")
```

**Test cases**:
```json
{
  "test_scenarios": [
    {
      "name": "test_context_preserved_on_retry",
      "steps": [
        "User injects /to-claude message",
        "Task fails, decision=RETRY",
        "Next iteration should include injected message"
      ]
    },
    {
      "name": "test_context_cleared_on_success",
      "steps": [
        "User injects /to-claude message",
        "Task succeeds, decision=PROCEED",
        "Next iteration should NOT include message"
      ]
    }
  ]
}
```

### 0.3: Graceful Shutdown Specification

**Command**: `/stop`

**Behavior**:
1. Set `stop_requested` flag
2. Finish current iteration (don't interrupt agent mid-call)
3. Skip remaining iterations
4. Run cleanup and save state
5. Exit with status code 0 (normal exit)

**Implementation**:

```python
# In Orchestrator.__init__
self.stop_requested = False  # New attribute

# In CommandProcessor._stop
def _stop(self, args: Dict) -> Dict:
    """Stop execution gracefully."""
    self.orchestrator.stop_requested = True
    return {
        'success': True,
        'message': 'Stopping after current turn completes...'
    }

# In Orchestrator._execute_single_task (at START checkpoint)
if self.stop_requested:
    self.logger.info("Stop requested by user")
    raise TaskStoppedException("User requested stop")

# In Orchestrator.execute_task (catch exception)
try:
    while not done:
        decision = self._execute_single_task(task, session)
        # ... process decision
except TaskStoppedException as e:
    self.logger.info(f"Task stopped by user: {e}")
    self.state_manager.update_task_status(
        task_id=task.id,
        status=TaskStatus.PAUSED,  # Use PAUSED, not FAILED
        result={'stopped_by_user': True, 'iterations_completed': iteration}
    )
    return {'status': 'stopped', 'iterations': iteration}
```

**New exception**:

```python
# In src/core/exceptions.py
class TaskStoppedException(OrchestratorException):
    """Raised when user requests task stop via /stop command."""
    pass
```

### 0.4: Multi-Session Testing Specification

**Concern**: Multiple `--interactive` sessions running simultaneously.

**Design Decision**: Each Orchestrator instance has isolated state.

**Testing**:

```python
# tests/test_orchestrator_interactive.py

def test_multi_session_isolation():
    """Test that multiple interactive sessions don't interfere."""
    orchestrator1 = Orchestrator(config=test_config)
    orchestrator2 = Orchestrator(config=test_config)

    orchestrator1.interactive_mode = True
    orchestrator2.interactive_mode = True

    # Each has own InputManager
    assert orchestrator1.input_manager is not orchestrator2.input_manager

    # Commands to one don't affect the other
    orchestrator1.injected_context['to_claude'] = 'Message for session 1'
    assert 'to_claude' not in orchestrator2.injected_context

    # Each has own pause state
    orchestrator1.paused = True
    assert orchestrator2.paused == False
```

**Documentation note**: Add to user guide that each terminal session is isolated.

### 0.5: Context Window Impact Tracking

**Implementation**: Track token usage of injected context.

```python
# In Orchestrator._apply_injected_context
def _apply_injected_context(self, base_prompt: str, context: Dict[str, Any]) -> str:
    """Merge user-injected context into prompt.

    Tracks token impact on context window.
    """
    injected_text = context.get('to_claude', '')
    if not injected_text:
        return base_prompt

    # Build augmented prompt
    augmented = f"{base_prompt}\n\n--- USER GUIDANCE ---\n{injected_text}\n"

    # Track token impact
    base_tokens = self.context_manager.estimate_tokens(base_prompt)
    augmented_tokens = self.context_manager.estimate_tokens(augmented)
    tokens_added = augmented_tokens - base_tokens

    self.logger.info(f"Injected context added {tokens_added} tokens")

    # Warn if approaching context window limit
    session = self.state_manager.get_current_session(task_id=self.current_task_id)
    if session:
        total_tokens = session.total_tokens + tokens_added
        limit = self.context_manager.limit
        usage_pct = (total_tokens / limit) * 100

        if usage_pct > 70:
            self.logger.warning(
                f"Context window usage: {usage_pct:.1f}% ({total_tokens}/{limit} tokens). "
                f"Injected context may trigger refresh soon."
            )

    return augmented
```

### 0.6: Future Enhancement - Undo Command (P2)

**Priority**: P2 (defer to Phase 3 or later)

**Specification**:

```json
{
  "command": "/undo",
  "syntax": "/undo",
  "description": "Undo last command",
  "implementation": {
    "approach": "Maintain command history stack with reversible operations",
    "state_tracking": "Track last command type and modified state",
    "limitations": [
      "Can only undo context injection, not agent actions",
      "Cannot undo decisions already executed",
      "Command history limited to current session"
    ]
  },
  "example_usage": [
    "> /to-claude Add comprehensive tests",
    "> /undo",
    "✓ Undid: /to-claude context injection"
  ]
}
```

**Note**: Defer implementation to Phase 3 after gathering user feedback on core features.

### 0.7: Error Handling & Signal Management

**Priority**: P1 (Critical for robustness)

**1. InputManager Failure Handling**

```python
# In Orchestrator.__init__ or execute_task
def _initialize_interactive_mode(self):
    """Initialize interactive mode with error handling."""
    try:
        self.input_manager = InputManager()
        self.input_manager.start_listening()
        self.logger.info("Interactive mode enabled")
        return True
    except (OSError, IOError) as e:
        self.logger.error(f"Cannot start interactive mode: {e}")
        self.logger.warning("Falling back to non-interactive mode")
        self.interactive_mode = False
        return False
```

**Error scenarios**:
- Terminal not available (running in background)
- stdin closed or redirected
- Insufficient permissions
- Resource limits (too many threads)

**2. SIGINT (Ctrl+C) Handling**

```python
# In Orchestrator or CLI
import signal
import sys

def _setup_signal_handlers(self):
    """Setup signal handlers for graceful shutdown."""
    def sigint_handler(sig, frame):
        self.logger.info("Received SIGINT (Ctrl+C)")

        if self.interactive_mode:
            # First Ctrl+C: graceful stop
            if not self.stop_requested:
                self.stop_requested = True
                print("\n⚠️  Stopping after current turn. Press Ctrl+C again to force quit.")
            # Second Ctrl+C: immediate exit
            else:
                print("\n⚠️  Force quit!")
                self._cleanup()
                sys.exit(130)  # Standard exit code for SIGINT
        else:
            # Non-interactive: immediate exit
            self._cleanup()
            sys.exit(130)

    signal.signal(signal.SIGINT, sigint_handler)

    # Also handle SIGTERM for graceful container shutdown
    signal.signal(signal.SIGTERM, sigint_handler)
```

**Behavior**:
- **Interactive mode**:
  - First Ctrl+C: Sets `stop_requested` flag (graceful)
  - Second Ctrl+C: Immediate exit with cleanup
- **Non-interactive mode**:
  - Ctrl+C: Immediate exit with cleanup

**3. Command Accumulation Behavior**

**Policy**: Last-wins (simpler implementation)

```python
# In CommandProcessor._to_claude
def _to_claude(self, args: Dict) -> Dict:
    """Inject message into Claude's next prompt (last-wins policy)."""
    message = args.get('message', '').strip()

    # Validation
    if not message:
        return {'error': '/to-claude requires a message'}

    # Warn if overwriting existing context
    if self.orchestrator.injected_context.get('to_claude'):
        self.logger.warning(
            "Replacing previous /to-claude message with new one (last-wins)"
        )

    self.orchestrator.injected_context['to_claude'] = message
    return {'success': f'Will send to Claude: {message[:50]}...'}
```

**Alternative** (accumulation - defer to future):
```python
# For future enhancement (P3)
# self.orchestrator.injected_context['to_claude'] = \
#     self.orchestrator.injected_context.get('to_claude', '') + '\n' + message
```

**4. State Persistence Limitation**

**Documented limitation** (acceptable for v1):

```json
{
  "limitation": "Injected context is not persisted to database",
  "impact": "Lost on crash, restart, or power loss",
  "workaround": "User must re-inject commands after restart",
  "future_enhancement": {
    "priority": "P3",
    "approach": "Store injected_context in SessionRecord metadata",
    "implementation": "Add metadata JSON column to sessions table"
  }
}
```

**User guide note**: Document this limitation clearly.

---

## Phase 1: Real-Time Streaming Output

**Duration**: 1-2 hours
**Priority**: P0 (Foundation)

### Objectives

```json
{
  "objectives": [
    "Stream Obra→Claude prompts to console in real-time",
    "Stream Claude→Obra responses to console in real-time",
    "Stream Qwen validation results to console in real-time",
    "Color-code different agent outputs for clarity",
    "Show iteration count, turn count, quality scores inline"
  ]
}
```

### Implementation Steps

**Step 1.1: Create StreamingHandler**

```json
{
  "file": "src/utils/streaming_handler.py",
  "classes": [
    {
      "name": "StreamingHandler",
      "parent": "logging.Handler",
      "purpose": "Custom log handler for real-time colored output",
      "implementation_notes": [
        "CRITICAL: Use flush=True on print() for unbuffered output",
        "Ensures < 100ms latency for streaming",
        "Python stdout is line-buffered by default - may cause delays"
      ],
      "methods": [
        {
          "name": "emit",
          "params": ["record: LogRecord"],
          "returns": "None",
          "description": "Format and output log records with color coding",
          "implementation": "print(colored_msg, flush=True)  # ← flush=True is CRITICAL"
        },
        {
          "name": "format_obra_to_claude",
          "params": ["message: str", "iteration: int", "chars: int"],
          "returns": "str",
          "description": "Format Obra→Claude prompts with blue color"
        },
        {
          "name": "format_claude_to_obra",
          "params": ["message: str", "turns: int", "chars: int"],
          "returns": "str",
          "description": "Format Claude→Obra responses with green color"
        },
        {
          "name": "format_qwen_validation",
          "params": ["quality: float", "decision: str"],
          "returns": "str",
          "description": "Format Qwen validation with yellow/red color"
        }
      ]
    }
  ],
  "color_scheme": {
    "obra_prompt": "blue",
    "claude_response": "green",
    "qwen_validation": "yellow",
    "errors": "red",
    "decisions": "cyan",
    "metadata": "dim_white"
  }
}
```

**Step 1.2: Add CLI Flag**

```json
{
  "file": "src/cli.py",
  "function": "task.execute",
  "new_options": [
    {
      "flag": "--stream",
      "type": "bool",
      "default": false,
      "help": "Enable real-time streaming output"
    }
  ],
  "changes": [
    "Pass stream=True to orchestrator.execute_task()",
    "Configure logging to use StreamingHandler when stream=True"
  ]
}
```

**Step 1.3: Modify Orchestrator**

```json
{
  "file": "src/orchestrator.py",
  "method": "execute_task",
  "changes": [
    {
      "location": "function signature",
      "before": "def execute_task(self, task_id: int, project_id: Optional[int] = None) -> Dict[str, Any]",
      "after": "def execute_task(self, task_id: int, project_id: Optional[int] = None, stream: bool = False) -> Dict[str, Any]"
    },
    {
      "location": "initialization",
      "action": "Add conditional logging handler",
      "code_snippet": "if stream:\n    from src.utils.streaming_handler import StreamingHandler\n    handler = StreamingHandler()\n    self.logger.addHandler(handler)"
    },
    {
      "location": "_execute_single_task",
      "action": "Add streaming log calls",
      "points": [
        "Before agent.send_prompt(): Log 'OBRA→CLAUDE' with prompt preview",
        "After agent.send_prompt(): Log 'CLAUDE→OBRA' with response preview",
        "After quality validation: Log 'QWEN' with quality score",
        "After decision: Log 'OBRA' with decision and reasoning"
      ]
    }
  ]
}
```

### Testing Criteria

**⚠️ IMPORTANT: All tests must comply with TEST_GUIDELINES.md**

Reference: [`docs/development/TEST_GUIDELINES.md`](TEST_GUIDELINES.md)

**Critical limits:**
- ⚠️ Max sleep per test: 0.5s (use `fast_time` fixture for longer waits)
- ⚠️ Max threads per test: 5
- ⚠️ Mandatory timeout on `thread.join()`: Always use `timeout=` parameter
- ⚠️ Mark resource-intensive tests with `@pytest.mark.slow`

```json
{
  "tests": [
    {
      "name": "test_streaming_handler_output",
      "file": "tests/test_streaming_handler.py",
      "compliance": {
        "threads": 0,
        "max_sleep": 0,
        "memory": "< 10KB"
      },
      "checks": [
        "StreamingHandler formats Obra→Claude correctly",
        "StreamingHandler formats Claude→Obra correctly",
        "StreamingHandler applies correct color codes",
        "StreamingHandler handles long messages (truncation)"
      ],
      "example": "def test_streaming_handler_output():\n    handler = StreamingHandler()\n    record = logging.LogRecord(...)\n    # No sleeps, no threads - instant execution\n    handler.emit(record)\n    assert output_captured"
    },
    {
      "name": "test_cli_stream_flag",
      "file": "tests/test_cli.py",
      "compliance": {
        "threads": 0,
        "max_sleep": 0,
        "memory": "< 10KB"
      },
      "checks": [
        "CLI accepts --stream flag",
        "StreamingHandler is added when stream=True",
        "Logs appear in real-time during execution"
      ],
      "example": "def test_cli_stream_flag():\n    # Use mocks, not real execution\n    result = runner.invoke(cli, ['task', 'execute', '3', '--stream'])\n    assert result.exit_code == 0"
    },
    {
      "name": "manual_test_streaming",
      "type": "manual",
      "command": "./venv/bin/python -m src.cli task execute 3 --stream",
      "expected": "See colored output streaming in real-time"
    }
  ]
}
```

### Success Metrics

```json
{
  "metrics": {
    "output_latency": "< 100ms from log event to console",
    "readability": "Clear visual separation between agents",
    "performance_impact": "< 5% overhead vs non-streaming mode"
  }
}
```

---

## Phase 2: Interactive Command Injection

**Duration**: 2-3 hours
**Priority**: P0 (Core Feature)

### Objectives

```json
{
  "objectives": [
    "Allow user to pause execution at decision points",
    "Allow user to inject context into Claude's next prompt",
    "Allow user to override Obra's decision (PROCEED → CLARIFY)",
    "Allow user to resume execution after injection",
    "Provide command help and autocomplete"
  ]
}
```

### Implementation Steps

**Step 2.1: Create CommandProcessor**

```json
{
  "file": "src/utils/command_processor.py",
  "constants": [
    {
      "name": "MAX_INJECTED_TEXT_LENGTH",
      "value": 5000,
      "description": "Maximum length for /to-claude and /to-obra messages (~1250 tokens)"
    },
    {
      "name": "HELP_TEXT",
      "type": "Dict[str, str]",
      "description": "Help text for all commands (see Section 0.7)"
    }
  ],
  "classes": [
    {
      "name": "CommandProcessor",
      "purpose": "Parse and execute user commands during execution",
      "attributes": [
        {
          "name": "commands",
          "type": "Dict[str, Callable]",
          "description": "Registry of available commands"
        },
        {
          "name": "command_queue",
          "type": "Queue",
          "description": "Thread-safe queue for command passing"
        }
      ],
      "methods": [
        {
          "name": "register_command",
          "params": ["name: str", "handler: Callable", "help_text: str"],
          "returns": "None"
        },
        {
          "name": "parse_command",
          "params": ["input: str"],
          "returns": "Tuple[str, Dict[str, Any]]",
          "description": "Parse command and extract arguments"
        },
        {
          "name": "execute_command",
          "params": ["command: str", "args: Dict[str, Any]"],
          "returns": "Dict[str, Any]"
        }
      ]
    }
  ],
  "commands": [
    {
      "name": "/pause",
      "args": [],
      "description": "Pause execution after current turn",
      "example": "/pause"
    },
    {
      "name": "/resume",
      "args": [],
      "description": "Resume paused execution",
      "example": "/resume"
    },
    {
      "name": "/to-claude",
      "args": ["message: str"],
      "description": "Inject context into Claude's next prompt",
      "example": "/to-claude Add unit tests for the Grid class",
      "validation": {
        "max_length": 5000,
        "error_if_empty": true,
        "warn_if_duplicate": true
      }
    },
    {
      "name": "/to-obra",
      "args": ["directive: str"],
      "description": "Override Obra's next decision or add directive",
      "example": "/to-obra Force PROCEED decision"
    },
    {
      "name": "/override-decision",
      "args": ["decision: str"],
      "description": "Override current decision (PROCEED/RETRY/CLARIFY/ESCALATE)",
      "example": "/override-decision RETRY"
    },
    {
      "name": "/status",
      "args": [],
      "description": "Show current task status and metrics",
      "example": "/status"
    },
    {
      "name": "/help",
      "args": [],
      "description": "Show available commands",
      "example": "/help"
    },
    {
      "name": "/stop",
      "args": [],
      "description": "Stop execution gracefully",
      "example": "/stop"
    }
  ]
}
```

**Step 2.2: Extend Orchestrator with Interactive Mode**

```json
{
  "file": "src/orchestrator.py",
  "changes": [
    {
      "attribute": "interactive_mode",
      "type": "bool",
      "default": false,
      "description": "Enable interactive command processing"
    },
    {
      "attribute": "command_processor",
      "type": "Optional[CommandProcessor]",
      "default": null,
      "description": "Command processor instance for interactive mode"
    },
    {
      "attribute": "paused",
      "type": "bool",
      "default": false,
      "description": "Execution pause flag"
    },
    {
      "attribute": "injected_context",
      "type": "Dict[str, Any]",
      "default": {},
      "description": "User-injected context for next prompt"
    },
    {
      "method": "_wait_for_user_input",
      "params": ["prompt_text: str"],
      "returns": "Optional[Dict[str, Any]]",
      "description": "Block and wait for user command input",
      "implementation_notes": [
        "Use prompt_toolkit for better UX (history, autocomplete)",
        "Run in separate thread to avoid blocking",
        "Return parsed command or None if user presses Enter"
      ]
    },
    {
      "method": "_apply_injected_context",
      "params": ["base_prompt: str", "context: Dict[str, Any]"],
      "returns": "str",
      "description": "Merge user-injected context into prompt",
      "implementation_notes": [
        "Append user messages to prompt",
        "Format clearly as 'USER GUIDANCE:' section"
      ]
    },
    {
      "method": "_handle_pause",
      "params": [],
      "returns": "None",
      "description": "Pause execution and wait for resume command"
    }
  ],
  "integration_points": [
    {
      "location": "After each iteration",
      "action": "Check for pause flag and wait for user input",
      "pseudocode": "if self.interactive_mode:\n    cmd = self._wait_for_user_input('> ')\n    if cmd:\n        self.command_processor.execute_command(cmd)"
    },
    {
      "location": "Before agent.send_prompt()",
      "action": "Apply injected context to prompt",
      "pseudocode": "if self.injected_context:\n    prompt = self._apply_injected_context(prompt, self.injected_context)\n    self.injected_context = {}"
    },
    {
      "location": "After DecisionEngine.decide()",
      "action": "Allow decision override if user specified",
      "pseudocode": "if 'override_decision' in self.injected_context:\n    decision = self.injected_context['override_decision']"
    }
  ]
}
```

**Step 2.3: Add CLI Flag for Interactive Mode**

```json
{
  "file": "src/cli.py",
  "function": "task.execute",
  "new_options": [
    {
      "flag": "--interactive",
      "type": "bool",
      "default": false,
      "help": "Enable interactive mode with command injection"
    }
  ],
  "validation": [
    "If --interactive is set, --stream is automatically enabled",
    "Warn user if running in background (won't work)"
  ]
}
```

**Step 2.4: Input Thread Management**

```json
{
  "file": "src/utils/input_manager.py",
  "classes": [
    {
      "name": "InputManager",
      "purpose": "Manage non-blocking user input in separate thread",
      "methods": [
        {
          "name": "start_listening",
          "params": [],
          "returns": "None",
          "description": "Start input listener thread"
        },
        {
          "name": "get_command",
          "params": ["timeout: float"],
          "returns": "Optional[str]",
          "description": "Get user command from queue (non-blocking with timeout)"
        },
        {
          "name": "stop_listening",
          "params": [],
          "returns": "None",
          "description": "Stop input listener thread"
        }
      ],
      "implementation_notes": [
        "Use prompt_toolkit for rich input (history, autocomplete)",
        "Run input loop in daemon thread",
        "Use thread-safe queue to pass commands to main thread"
      ]
    }
  ]
}
```

### Testing Criteria

**⚠️ IMPORTANT: All tests must comply with TEST_GUIDELINES.md**

Reference: [`docs/development/TEST_GUIDELINES.md`](TEST_GUIDELINES.md)

```json
{
  "tests": [
    {
      "name": "test_command_processor_parsing",
      "file": "tests/test_command_processor.py",
      "compliance": {
        "threads": 0,
        "max_sleep": 0,
        "memory": "< 5KB"
      },
      "checks": [
        "Correctly parses /to-claude with quoted message",
        "Correctly parses /override-decision with enum value",
        "Rejects invalid commands with helpful error"
      ],
      "example": "def test_command_processor_parsing():\n    processor = CommandProcessor(mock_orchestrator)\n    cmd, args = processor.parse_command('/to-claude Test message')\n    assert cmd == '/to-claude'\n    assert args['message'] == 'Test message'"
    },
    {
      "name": "test_interactive_pause_resume",
      "file": "tests/test_orchestrator_interactive.py",
      "compliance": {
        "threads": 0,
        "max_sleep": 0,
        "memory": "< 10KB"
      },
      "checks": [
        "/pause sets paused flag",
        "/resume clears paused flag and continues execution",
        "Execution blocks while paused"
      ],
      "example": "def test_interactive_pause_resume():\n    orchestrator.paused = False\n    # Simulate /pause\n    orchestrator.paused = True\n    assert orchestrator.paused == True\n    # Simulate /resume\n    orchestrator.paused = False\n    assert orchestrator.paused == False"
    },
    {
      "name": "test_context_injection",
      "file": "tests/test_orchestrator_interactive.py",
      "compliance": {
        "threads": 0,
        "max_sleep": 0,
        "memory": "< 10KB"
      },
      "checks": [
        "/to-claude message appears in next prompt",
        "Injected context is cleared after use (on PROCEED)",
        "Injected context is preserved on RETRY (Phase 0 spec)",
        "Multiple injections accumulate correctly"
      ],
      "example": "def test_context_injection():\n    orchestrator.injected_context['to_claude'] = 'Test message'\n    prompt = orchestrator._apply_injected_context('Base', orchestrator.injected_context)\n    assert 'Test message' in prompt\n    # Test persistence\n    orchestrator._clear_injected_context(Decision.PROCEED)\n    assert 'to_claude' not in orchestrator.injected_context"
    },
    {
      "name": "test_context_persistence_on_retry",
      "file": "tests/test_orchestrator_interactive.py",
      "compliance": {
        "threads": 0,
        "max_sleep": 0,
        "memory": "< 10KB"
      },
      "checks": [
        "Injected context persists through RETRY",
        "Injected context cleared on PROCEED",
        "Injected context cleared on ESCALATE"
      ],
      "example": "# From Phase 0.2 specification\ndef test_context_persistence_on_retry():\n    orchestrator.injected_context['to_claude'] = 'Test'\n    # Simulate RETRY decision\n    orchestrator._handle_decision_context(Decision.RETRY)\n    assert orchestrator.injected_context['to_claude'] == 'Test'\n    # Simulate PROCEED decision\n    orchestrator._handle_decision_context(Decision.PROCEED)\n    assert 'to_claude' not in orchestrator.injected_context"
    },
    {
      "name": "test_decision_override",
      "file": "tests/test_orchestrator_interactive.py",
      "compliance": {
        "threads": 0,
        "max_sleep": 0,
        "memory": "< 10KB"
      },
      "checks": [
        "/override-decision changes DecisionEngine output",
        "Override only applies to current iteration",
        "Invalid decisions are rejected"
      ]
    },
    {
      "name": "test_input_manager_threading",
      "file": "tests/test_input_manager.py",
      "compliance": {
        "threads": 1,
        "max_sleep": 0.1,
        "memory": "< 10KB",
        "marker": "@pytest.mark.slow"
      },
      "checks": [
        "InputManager starts/stops thread correctly",
        "Thread terminates within timeout",
        "Queue operations are thread-safe"
      ],
      "example": "@pytest.mark.slow\ndef test_input_manager_threading():\n    manager = InputManager()\n    manager.start_listening()\n    time.sleep(0.1)  # Under 0.5s limit ✓\n    manager.stop_listening()\n    # MANDATORY timeout on join\n    if manager.thread:\n        manager.thread.join(timeout=2.0)  # ✓\n    assert not manager.thread.is_alive()"
    },
    {
      "name": "test_multi_session_isolation",
      "file": "tests/test_orchestrator_interactive.py",
      "compliance": {
        "threads": 0,
        "max_sleep": 0,
        "memory": "< 20KB"
      },
      "checks": [
        "Multiple Orchestrator instances have isolated state",
        "Commands to one instance don't affect another",
        "Each has independent InputManager"
      ],
      "example": "# From Phase 0.4 specification\ndef test_multi_session_isolation():\n    orch1 = Orchestrator(config=test_config)\n    orch2 = Orchestrator(config=test_config)\n    orch1.interactive_mode = True\n    orch2.interactive_mode = True\n    assert orch1.input_manager is not orch2.input_manager"
    },
    {
      "name": "test_graceful_stop",
      "file": "tests/test_orchestrator_interactive.py",
      "compliance": {
        "threads": 0,
        "max_sleep": 0,
        "memory": "< 10KB"
      },
      "checks": [
        "/stop sets stop_requested flag",
        "TaskStoppedException is raised",
        "Task status set to PAUSED (not FAILED)",
        "State is saved before exit"
      ],
      "example": "# From Phase 0.3 specification\ndef test_graceful_stop():\n    orchestrator.stop_requested = False\n    # Simulate /stop command\n    orchestrator.stop_requested = True\n    with pytest.raises(TaskStoppedException):\n        orchestrator._check_stop_requested()"
    },
    {
      "name": "test_context_window_tracking",
      "file": "tests/test_orchestrator_interactive.py",
      "compliance": {
        "threads": 0,
        "max_sleep": 0,
        "memory": "< 10KB"
      },
      "checks": [
        "Token count tracked for injected context",
        "Warning logged if approaching context limit",
        "Token estimate accuracy within 10%"
      ],
      "example": "# From Phase 0.5 specification\ndef test_context_window_tracking():\n    orchestrator.injected_context['to_claude'] = 'A' * 1000  # ~250 tokens\n    prompt = orchestrator._apply_injected_context('Base', orchestrator.injected_context)\n    # Should log token count\n    assert 'tokens' in caplog.text.lower()"
    },
    {
      "name": "manual_test_interactive",
      "type": "manual",
      "steps": [
        "Run: ./venv/bin/python -m src.cli task execute 3 --stream --interactive",
        "Wait for prompt after first iteration",
        "Type: /to-claude Create a sample test file",
        "Press Enter to continue",
        "Verify message appears in next Claude prompt",
        "Type: /pause",
        "Verify execution pauses",
        "Type: /resume",
        "Verify execution continues",
        "Type: /stop",
        "Verify execution stops gracefully"
      ]
    }
  ]
}
```

### Success Metrics

```json
{
  "metrics": {
    "command_latency": "< 50ms from user input to execution",
    "thread_safety": "No race conditions in 100 test runs",
    "user_experience": "Commands feel responsive and intuitive"
  }
}
```

---

## Phase 3: Enhanced Formatting & UX

**Duration**: 1 hour
**Priority**: P1 (Nice-to-have for Phase 2)

### Objectives

```json
{
  "objectives": [
    "Improve output formatting with separators",
    "Add progress indicators (spinner, progress bar)",
    "Show token usage and context window % inline",
    "Add keyboard shortcuts (Ctrl+C for pause, Ctrl+D for stop)",
    "Save session transcript to file"
  ]
}
```

### Implementation Details

```json
{
  "enhancements": [
    {
      "feature": "Separators between iterations",
      "implementation": "Print '─' * 80 between iterations for visual clarity"
    },
    {
      "feature": "Progress spinner during Claude execution",
      "library": "rich.spinner",
      "implementation": "Show spinner with 'Claude thinking...' while waiting"
    },
    {
      "feature": "Token usage display",
      "format": "[Tokens: 45,234 | Context: 22.6% | Cache: 86.8%]",
      "location": "After each Claude response"
    },
    {
      "feature": "Keyboard shortcuts",
      "shortcuts": {
        "Ctrl+P": "Pause execution",
        "Ctrl+R": "Resume execution",
        "Ctrl+D": "Stop gracefully",
        "Ctrl+C": "Emergency stop (SIGINT)"
      }
    },
    {
      "feature": "Session transcript",
      "format": "markdown",
      "location": "logs/transcripts/task_{id}_{timestamp}.md",
      "content": [
        "Full conversation history",
        "Decisions and reasoning",
        "User commands",
        "Final metrics"
      ]
    }
  ]
}
```

---

## Testing Strategy

### Unit Tests

```json
{
  "unit_tests": [
    "test_streaming_handler.py: Test log formatting and color codes",
    "test_command_processor.py: Test command parsing and execution",
    "test_input_manager.py: Test non-blocking input with threads",
    "test_orchestrator_interactive.py: Test pause/resume/injection logic"
  ],
  "coverage_target": "≥ 90% for new code"
}
```

### Integration Tests

```json
{
  "integration_tests": [
    {
      "name": "test_end_to_end_streaming",
      "description": "Execute task with --stream and verify output appears",
      "duration": "30s"
    },
    {
      "name": "test_end_to_end_interactive",
      "description": "Execute task with --interactive, inject commands, verify behavior",
      "duration": "60s",
      "note": "Requires mocking user input"
    }
  ]
}
```

### Manual Testing Checklist

```json
{
  "manual_tests": [
    {
      "test": "Streaming output appears in real-time",
      "command": "./venv/bin/python -m src.cli task execute 3 --stream",
      "expected": "See colored logs streaming during execution"
    },
    {
      "test": "Interactive commands work",
      "command": "./venv/bin/python -m src.cli task execute 3 --stream --interactive",
      "steps": [
        "Wait for prompt after iteration",
        "Type /to-claude message",
        "Verify message in next prompt"
      ]
    },
    {
      "test": "Pause/resume works",
      "command": "./venv/bin/python -m src.cli task execute 3 --interactive",
      "steps": [
        "Type /pause after iteration 1",
        "Verify execution stops",
        "Type /resume",
        "Verify execution continues"
      ]
    },
    {
      "test": "Decision override works",
      "command": "./venv/bin/python -m src.cli task execute 3 --interactive",
      "steps": [
        "Wait for PROCEED decision",
        "Type /override-decision RETRY",
        "Verify task retries instead of proceeding"
      ]
    }
  ]
}
```

---

## Dependencies

```json
{
  "new_dependencies": [
    {
      "package": "prompt_toolkit",
      "version": ">=3.0.0",
      "purpose": "Rich interactive input with history and autocomplete",
      "license": "BSD-3-Clause"
    },
    {
      "package": "colorama",
      "version": ">=0.4.6",
      "purpose": "Cross-platform colored terminal output",
      "license": "BSD-3-Clause"
    },
    {
      "package": "rich",
      "version": ">=13.0.0",
      "purpose": "Progress indicators and formatting (Phase 3)",
      "license": "MIT",
      "optional": true
    }
  ],
  "update_requirements": true
}
```

---

## Risks and Mitigations

```json
{
  "risks": [
    {
      "risk": "Thread safety issues with command injection",
      "probability": "Medium",
      "impact": "High",
      "mitigation": "Use thread-safe queues, thorough testing, locks around shared state"
    },
    {
      "risk": "Input blocking causes hangs",
      "probability": "Low",
      "impact": "High",
      "mitigation": "Always use timeout on input operations, daemon threads"
    },
    {
      "risk": "Performance overhead from streaming",
      "probability": "Low",
      "impact": "Low",
      "mitigation": "Make streaming optional, benchmark before/after"
    },
    {
      "risk": "Commands break mid-execution",
      "probability": "Medium",
      "impact": "Medium",
      "mitigation": "Try/except around command execution, graceful error handling"
    }
  ]
}
```

---

## Evolution Path: TUI (Option 1)

**Status**: Future Enhancement
**Estimated Effort**: 2-3 hours
**Priority**: P2 (After Option 2 is stable)

### High-Level Plan

```json
{
  "approach": "Build TUI on top of streaming infrastructure",
  "library": "textual (recommended) or rich.console",
  "architecture": {
    "components": [
      {
        "name": "ObraTUI",
        "type": "Textual App",
        "file": "src/cli_tui.py",
        "description": "Main TUI application"
      },
      {
        "name": "AgentPanel",
        "type": "Textual Widget",
        "description": "Scrollable panel for agent output"
      },
      {
        "name": "CommandInput",
        "type": "Textual Input",
        "description": "Command input with autocomplete"
      },
      {
        "name": "StatusBar",
        "type": "Textual Footer",
        "description": "Show iteration, quality, tokens"
      }
    ]
  },
  "layout": {
    "top": "Header (task info)",
    "middle_split": [
      {
        "left_panel": "Obra → Claude prompts (40%)",
        "right_panel": "Claude → Obra responses (40%)"
      }
    ],
    "bottom_panel": "Qwen validation (20%)",
    "footer": "Command input + status bar"
  }
}
```

### Migration from Option 2

```json
{
  "migration_steps": [
    {
      "step": 1,
      "action": "Reuse StreamingHandler output as TUI data source",
      "description": "Instead of printing to console, send to TUI panels"
    },
    {
      "step": 2,
      "action": "Reuse CommandProcessor for TUI input",
      "description": "Same commands, but triggered from TUI input widget"
    },
    {
      "step": 3,
      "action": "Add TUI-specific features",
      "features": [
        "Scrollback through conversation history",
        "Split-panel synchronized scrolling",
        "Command autocomplete dropdown",
        "Keyboard shortcuts (F1 = help, Esc = pause)"
      ]
    },
    {
      "step": 4,
      "action": "Add CLI flag for TUI mode",
      "flag": "--tui",
      "behavior": "Launch TUI instead of streaming to console"
    }
  ]
}
```

### TUI-Specific Features

```json
{
  "features": [
    {
      "name": "Collapsible sections",
      "description": "Collapse long Claude responses to save space",
      "hotkey": "Space"
    },
    {
      "name": "Search",
      "description": "Search through conversation history",
      "hotkey": "Ctrl+F"
    },
    {
      "name": "Export",
      "description": "Export current view to markdown file",
      "hotkey": "Ctrl+E"
    },
    {
      "name": "Panel resize",
      "description": "Drag dividers to resize panels",
      "hotkey": "Mouse drag"
    },
    {
      "name": "Syntax highlighting",
      "description": "Highlight code blocks in responses",
      "library": "pygments"
    }
  ]
}
```

### Dependencies for TUI

```json
{
  "additional_dependencies": [
    {
      "package": "textual",
      "version": ">=0.40.0",
      "purpose": "Modern TUI framework",
      "license": "MIT"
    },
    {
      "package": "pygments",
      "version": ">=2.16.0",
      "purpose": "Syntax highlighting in TUI",
      "license": "BSD-2-Clause"
    }
  ]
}
```

---

## Acceptance Criteria

### Phase 1 (Streaming)

```json
{
  "criteria": [
    "✅ ./venv/bin/python -m src.cli task execute --stream shows colored real-time output",
    "✅ Obra→Claude prompts are blue and prefixed with [OBRA→CLAUDE]",
    "✅ Claude→Obra responses are green and prefixed with [CLAUDE→OBRA]",
    "✅ Qwen validation is yellow and shows quality score",
    "✅ Decisions are cyan and show reasoning",
    "✅ Output appears within 100ms of log event",
    "✅ No visual artifacts or formatting issues"
  ]
}
```

### Phase 2 (Interactive)

```json
{
  "criteria": [
    "✅ ./venv/bin/python -m src.cli task execute --interactive prompts for commands after each iteration",
    "✅ /to-claude message appears in next prompt to Claude",
    "✅ /to-obra directive modifies Obra's next decision",
    "✅ /pause stops execution until /resume",
    "✅ /override-decision changes current decision",
    "✅ /status shows current task metrics",
    "✅ /help shows all available commands",
    "✅ /stop gracefully terminates execution",
    "✅ Invalid commands show helpful error messages",
    "✅ Command history works (up/down arrows)",
    "✅ Tab autocomplete works for commands"
  ]
}
```

### Phase 3 (TUI - Future)

```json
{
  "criteria": [
    "✅ ./venv/bin/python -m src.cli task execute --tui launches TUI interface",
    "✅ Split panels show Obra/Claude/Qwen simultaneously",
    "✅ Panels scroll independently",
    "✅ Command input at bottom with autocomplete",
    "✅ Status bar shows live metrics",
    "✅ All Phase 2 commands work in TUI",
    "✅ TUI handles terminal resize gracefully",
    "✅ Syntax highlighting works for code blocks"
  ]
}
```

---

## Rollout Plan

```json
{
  "phases": [
    {
      "phase": "Phase 0: Clarifications",
      "duration": "1 hour",
      "tasks": [
        "Review Phase 0 specifications",
        "Update Orchestrator integration flow diagram",
        "Define command persistence behavior",
        "Specify graceful shutdown mechanism",
        "Document context window tracking approach"
      ]
    },
    {
      "phase": "Development",
      "duration": "4-6 hours",
      "tasks": [
        "Implement Phase 1 (streaming)",
        "Implement Phase 2 (interactive)",
        "Write unit tests (with TEST_GUIDELINES compliance)",
        "Write integration tests"
      ]
    },
    {
      "phase": "Testing",
      "duration": "1-2 hours",
      "tasks": [
        "Run unit tests",
        "Run integration tests",
        "Manual testing with Tetris project",
        "Performance benchmarking"
      ]
    },
    {
      "phase": "Documentation",
      "duration": "1 hour",
      "tasks": [
        "Update README with --stream and --interactive flags",
        "Add interactive mode guide to docs/guides/",
        "Update CLAUDE.md with interactive mode info",
        "Create command reference card"
      ]
    },
    {
      "phase": "Deployment",
      "duration": "30 minutes",
      "tasks": [
        "Update requirements.txt",
        "Test in clean environment",
        "Merge to main branch",
        "Update CHANGELOG.md"
      ]
    }
  ]
}
```

---

## Success Metrics

```json
{
  "metrics": {
    "user_experience": {
      "time_to_first_output": "< 1s after task start",
      "command_response_time": "< 50ms",
      "perceived_responsiveness": "No lag or stuttering"
    },
    "reliability": {
      "crash_rate": "0% in 100 test runs",
      "thread_deadlocks": "0 occurrences",
      "command_failures": "< 1% due to bugs"
    },
    "adoption": {
      "default_usage": "--stream flag becomes default in future",
      "interactive_usage": "Used in >50% of long-running tasks"
    }
  }
}
```

---

## Future Enhancements (Beyond TUI)

```json
{
  "enhancements": [
    {
      "name": "Web UI Dashboard",
      "description": "Browser-based interface for remote monitoring",
      "priority": "P3",
      "effort": "8-12 hours",
      "tech_stack": ["FastAPI", "WebSockets", "React"]
    },
    {
      "name": "Multi-session monitoring",
      "description": "Monitor multiple Obra tasks simultaneously",
      "priority": "P3",
      "effort": "4-6 hours"
    },
    {
      "name": "Voice commands",
      "description": "Control Obra via voice (pause, resume, inject)",
      "priority": "P4",
      "effort": "6-8 hours",
      "library": "SpeechRecognition"
    },
    {
      "name": "Mobile app notifications",
      "description": "Push notifications on task completion",
      "priority": "P4",
      "effort": "12-16 hours"
    }
  ]
}
```

---

## Appendix A: Command Reference

```json
{
  "commands": [
    {
      "command": "/pause",
      "syntax": "/pause",
      "description": "Pause execution after current turn completes",
      "examples": ["/pause"]
    },
    {
      "command": "/resume",
      "syntax": "/resume",
      "description": "Resume paused execution",
      "examples": ["/resume"]
    },
    {
      "command": "/to-claude",
      "syntax": "/to-claude <message>",
      "description": "Inject user guidance into Claude's next prompt",
      "examples": [
        "/to-claude Add comprehensive unit tests",
        "/to-claude Focus on error handling in the Grid class"
      ]
    },
    {
      "command": "/to-obra",
      "syntax": "/to-obra <directive>",
      "description": "Add directive to Obra's next decision logic",
      "examples": [
        "/to-obra Lower quality threshold to 0.5",
        "/to-obra Increase max_turns to 30"
      ]
    },
    {
      "command": "/override-decision",
      "syntax": "/override-decision <PROCEED|RETRY|CLARIFY|ESCALATE>",
      "description": "Override Obra's current decision",
      "examples": [
        "/override-decision RETRY",
        "/override-decision PROCEED"
      ]
    },
    {
      "command": "/status",
      "syntax": "/status",
      "description": "Show current task status, metrics, and progress",
      "examples": ["/status"]
    },
    {
      "command": "/help",
      "syntax": "/help [command]",
      "description": "Show help for all commands or specific command",
      "examples": [
        "/help",
        "/help to-claude"
      ],
      "help_text": {
        "/pause": "Pause execution after current turn. Resume with /resume.",
        "/resume": "Resume paused execution.",
        "/to-claude <message>": "Inject guidance into Claude's next prompt. Max 5000 chars. Example: /to-claude Add unit tests",
        "/to-obra <directive>": "Add directive to Obra's decision logic. Example: /to-obra Lower quality threshold",
        "/override-decision <PROCEED|RETRY|CLARIFY|ESCALATE>": "Override current decision. Example: /override-decision RETRY",
        "/status": "Show current task status, iteration, quality score, token usage.",
        "/help [command]": "Show this help message or help for specific command.",
        "/stop": "Stop execution gracefully (completes current turn, saves state).",
        "/undo": "[P2 - Future] Undo last command."
      }
    },
    {
      "command": "/stop",
      "syntax": "/stop",
      "description": "Stop execution gracefully (finish current turn)",
      "examples": ["/stop"],
      "behavior": {
        "sets_flag": "stop_requested = True",
        "completes_current_turn": true,
        "task_status": "PAUSED (not FAILED)",
        "cleanup": "Runs cleanup and saves state",
        "exit_code": 0
      }
    },
    {
      "command": "/undo",
      "syntax": "/undo",
      "description": "[P2 - Future] Undo last command",
      "examples": ["/undo"],
      "status": "Not implemented in Phase 1-2",
      "priority": "P2",
      "note": "Defer to Phase 3 or later based on user feedback"
    }
  ]
}
```

---

## Appendix B: File Structure

```json
{
  "new_files": [
    "src/utils/streaming_handler.py",
    "src/utils/command_processor.py",
    "src/utils/input_manager.py",
    "tests/test_streaming_handler.py",
    "tests/test_command_processor.py",
    "tests/test_input_manager.py",
    "tests/test_orchestrator_interactive.py",
    "docs/guides/INTERACTIVE_MODE_GUIDE.md",
    "docs/development/INTERACTIVE_STREAMING_IMPLEMENTATION_PLAN.md"
  ],
  "modified_files": [
    "src/orchestrator.py",
    "src/cli.py",
    "src/core/exceptions.py",
    "requirements.txt",
    "CLAUDE.md",
    "README.md"
  ],
  "new_exceptions": [
    "TaskStoppedException (in src/core/exceptions.py)"
  ],
  "future_files": [
    "src/cli_tui.py",
    "tests/test_cli_tui.py",
    "docs/guides/TUI_MODE_GUIDE.md"
  ]
}
```

---

## Revision History

| Date | Version | Changes |
|------|---------|---------|
| 2025-11-04 | 1.0 | Initial plan created |
| 2025-11-04 | 1.1 | Added Phase 0 clarifications:<br>- Integration flow specification<br>- Command persistence behavior<br>- Graceful shutdown mechanism<br>- Multi-session testing<br>- Context window tracking<br>- TEST_GUIDELINES.md compliance<br>- Future /undo command spec |
| 2025-11-04 | 1.2 | Added quick wins (P1 items):<br>- Section 0.7: Error handling & signal management<br>- Help text content in Appendix A<br>- Output buffering notes in Phase 1<br>- Input validation limits in Phase 2<br>- User guide outline in Appendix C |

---

## Appendix C: User Guide Outline

**File**: `docs/guides/INTERACTIVE_MODE_GUIDE.md`

```markdown
# Interactive Mode User Guide

## Table of Contents
1. Quick Start
2. Commands Reference
3. Use Cases & Examples
4. Limitations & Known Issues
5. Troubleshooting
6. Advanced Usage

## 1. Quick Start

### Enabling Interactive Mode

```bash
# Streaming only (view conversation)
./venv/bin/python -m src.cli task execute <task_id> --stream

# Interactive mode (view + control)
./venv/bin/python -m src.cli task execute <task_id> --stream --interactive
```

### Basic Workflow

1. Start task with `--interactive`
2. Watch streaming output in real-time
3. After each iteration, see `> ` prompt
4. Type commands or press Enter to continue
5. Use `/help` to see available commands

## 2. Commands Reference

[Include HELP_TEXT from Appendix A]

## 3. Use Cases & Examples

### Use Case 1: Guiding Task Mid-Execution

**Scenario**: Claude is implementing a feature, but you want to add specific requirements.

```
[OBRA→CLAUDE] Iteration 2/10
[CLAUDE→OBRA] Response received (3493 chars)
[QWEN] Quality: 0.76 (PASS)
[OBRA] Decision: PROCEED

> /to-claude Also add comprehensive unit tests with edge cases
✓ Will send to Claude: Also add comprehensive unit tests with edge cases

[OBRA→CLAUDE] Iteration 3/10
[OBRA→CLAUDE] --- USER GUIDANCE ---
Also add comprehensive unit tests with edge cases
```

### Use Case 2: Debugging Failed Tasks

**Scenario**: Task quality is low, but you want to force proceed.

```
[QWEN] Quality: 0.45 (FAIL)
[OBRA] Decision: RETRY

> /override-decision PROCEED
✓ Decision overridden: PROCEED

[OBRA] Decision: PROCEED (user override)
```

### Use Case 3: Emergency Stop

**Scenario**: Task is going in wrong direction, need to stop.

```
[CLAUDE] Turn 5/10: Refactoring database layer...

> /stop
✓ Stopping after current turn completes...

[OBRA] Task stopped by user
Task status: PAUSED (can resume later)
```

### Use Case 4: Checking Progress

**Scenario**: Want to see current status mid-execution.

```
> /status
📊 Task Status:
   Task ID: 3
   Iteration: 4/10
   Quality: 0.76
   Confidence: 0.82
   Turns used: 12/20
   Tokens: 45,234 (22.6%)
   Files created: 8
   Files modified: 15
```

## 4. Limitations & Known Issues

### Known Limitations

1. **No State Persistence**: Injected context is lost on crash/restart
   - **Workaround**: Re-inject commands after restart

2. **Single Session**: Each terminal session is isolated
   - **Impact**: Cannot control task from multiple terminals
   - **Design**: Intentional for simplicity

3. **Cannot Undo Agent Actions**: `/undo` only undoes commands, not code changes
   - **Workaround**: Use git to revert code changes

4. **Command Accumulation**: Multiple `/to-claude` before iteration → only last message used
   - **Design**: "Last-wins" policy (simpler than accumulation)
   - **Workaround**: Combine messages manually in single command

5. **No Background Mode**: Interactive mode requires attached terminal
   - **Impact**: Cannot run in background or via cron
   - **Workaround**: Use non-interactive mode for background tasks

### Performance Considerations

- **Streaming overhead**: < 5% performance impact
- **Command latency**: < 50ms from input to execution
- **Context window**: Injected text counts toward 200K token limit

## 5. Troubleshooting

### Problem: "Cannot start interactive mode"

**Cause**: Terminal not available, stdin closed, or running in background

**Solution**:
```bash
# Check if terminal is attached
tty
# If "not a tty", interactive mode won't work

# Run in foreground with attached terminal
./venv/bin/python -m src.cli task execute 3 --interactive
```

### Problem: Colors not showing (Windows)

**Cause**: Windows terminal needs colorama initialization

**Solution**:
```bash
# Install colorama
pip install colorama>=0.4.6

# Should work automatically - colorama.init() called in StreamingHandler
```

### Problem: Ctrl+C doesn't work

**Cause**: Signal handler not set up correctly

**Solution**:
- First Ctrl+C: Graceful stop (completes current turn)
- Second Ctrl+C: Force quit (immediate exit)

### Problem: Commands not recognized

**Cause**: Typo in command name or missing `/` prefix

**Solution**:
```bash
# CORRECT
> /to-claude Add tests

# INCORRECT
> to-claude Add tests  # Missing /
> /toclaude Add tests  # Typo (no dash)
```

### Problem: Output delayed or buffered

**Cause**: Python stdout buffering

**Solution**: Already handled in StreamingHandler with `flush=True`

## 6. Advanced Usage

### Keyboard Shortcuts (Future - Phase 3)

- `Ctrl+P`: Pause execution
- `Ctrl+R`: Resume execution
- `Ctrl+D`: Stop gracefully
- `Ctrl+C`: Emergency stop (first time graceful, second time force)

### Session Transcripts

**Location**: `logs/transcripts/task_<id>_<timestamp>.md`

**Contents**:
- Full conversation history
- Decisions and reasoning
- User commands
- Final metrics

**Access**:
```bash
# View latest transcript
cat logs/transcripts/task_3_*.md | less

# Search for specific command
grep "/to-claude" logs/transcripts/task_3_*.md
```

### Multi-Session Monitoring (Future - Phase 3)

**Not yet implemented** - Each session is currently isolated

## Getting Help

- In-app: `/help` or `/help <command>`
- Documentation: `docs/development/INTERACTIVE_STREAMING_IMPLEMENTATION_PLAN.md`
- Issues: https://github.com/Omar-Unpossible/claude_code_orchestrator/issues
```

---

**Status**: ✅ **Ready for Implementation (v1.2)**
**Next Step**: Review Phase 0 specifications → Begin Phase 1 implementation → Test → Deploy

**Addressed Concerns**:
- ✅ TEST_GUIDELINES.md compliance explicitly documented
- ✅ Orchestrator integration flow fully specified
- ✅ Command persistence behavior defined (persists through RETRY)
- ✅ Graceful shutdown mechanism specified (`/stop` → TaskStoppedException)
- ✅ Multi-session isolation tested
- ✅ Context window impact tracking added
- ✅ Future /undo command planned (P2)
- ✅ Error handling & signal management (Section 0.7)
- ✅ Help text content specified (Appendix A)
- ✅ Output buffering addressed (flush=True)
- ✅ Input validation limits defined (Phase 2)
- ✅ User guide outline created (Appendix C)

**Completeness**: 98% (ready for implementation)
