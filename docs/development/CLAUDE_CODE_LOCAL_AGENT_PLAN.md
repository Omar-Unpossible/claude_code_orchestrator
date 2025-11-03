# Claude Code Local Agent - Implementation Plan

**Status**: Ready for Implementation
**Priority**: High (Blocking real-world usage)
**Estimated Effort**: 6-8 hours
**Dependencies**: M6 (Integration) complete
**Target**: Post-M7 enhancement

---

## Executive Summary

Implement `ClaudeCodeLocalAgent` to enable Obra to execute tasks using Claude Code CLI running as a local subprocess in the same WSL2 environment. This agent will spawn Claude Code CLI, send prompts via stdin, read responses from stdout, and manage the process lifecycle.

**Key Separation**: This agent manages Claude Code CLI only. Ollama/Qwen LLM remains on the host machine and is accessed via HTTP API for validation and quality scoring.

---

## Architecture Overview

### System Context

```
┌─────────────────────────────────────────────────────────────┐
│ HOST MACHINE (Windows 11 Pro)                               │
│                                                              │
│  Ollama + Qwen 2.5 Coder (RTX 5090)                        │
│  - Validation & Quality Scoring                             │
│  - HTTP API: http://172.29.144.1:11434                     │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Hyper-V VM → WSL2                                     │  │
│  │                                                        │  │
│  │  Obra Orchestrator ←─HTTP API─→ Ollama (host)        │  │
│  │       ↓                                                │  │
│  │  subprocess.Popen(['claude'])                         │  │
│  │       ↓                                                │  │
│  │  Claude Code CLI (local subprocess)                   │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Communication Paths

1. **Obra → Ollama (LLM)**: HTTP API (unchanged)
   - Purpose: Validation, quality scoring, confidence calculation
   - Protocol: HTTP POST to http://172.29.144.1:11434/api/generate
   - Data: JSON with prompts for validation

2. **Obra → Claude Code CLI**: Subprocess (new)
   - Purpose: Task execution, code generation
   - Protocol: stdin/stdout pipes
   - Data: Text prompts and responses

---

## Milestone Breakdown

### **M8.1: Core Subprocess Management** (2-3 hours)

**Deliverables**:
- `src/agents/claude_code_local.py` (base implementation)
- Process spawning and lifecycle management
- Basic stdin/stdout communication
- Unit tests for process management

**Acceptance Criteria**:
- ✅ Can spawn Claude Code CLI subprocess
- ✅ Can send text to stdin
- ✅ Can read text from stdout
- ✅ Process terminates gracefully on cleanup
- ✅ Tests pass with 90%+ coverage

**Technical Details**:

```python
import subprocess
import threading
import queue
from typing import Optional, Dict, Any

@register_agent('claude-code-local')
class ClaudeCodeLocalAgent(AgentPlugin):
    """Claude Code CLI as local subprocess."""

    def __init__(self):
        self._process: Optional[subprocess.Popen] = None
        self._stdout_queue: queue.Queue = queue.Queue()
        self._stderr_queue: queue.Queue = queue.Queue()
        self._reader_thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
        self._running = False

    def initialize(self, config: Dict[str, Any]) -> None:
        """Start Claude Code CLI subprocess.

        Config keys:
            - workspace_path: Working directory (required)
            - claude_command: Command to run (default: 'claude')
            - timeout: Operation timeout in seconds (default: 300)
            - env: Environment variables (optional)
        """
        with self._lock:
            # Spawn process
            self._process = subprocess.Popen(
                [config.get('claude_command', 'claude')],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # Line buffered
                cwd=config['workspace_path'],
                env=config.get('env')
            )

            # Start output reader threads
            self._start_reader_threads()
            self._running = True

            # Wait for Claude to be ready
            self._wait_for_ready(timeout=30)

    def _start_reader_threads(self) -> None:
        """Start background threads to read stdout/stderr."""
        def read_stream(stream, queue_):
            """Read from stream and put in queue."""
            try:
                for line in iter(stream.readline, ''):
                    if line:
                        queue_.put(line)
            except Exception as e:
                logger.error(f"Reader thread error: {e}")
            finally:
                stream.close()

        # Stdout reader
        self._stdout_thread = threading.Thread(
            target=read_stream,
            args=(self._process.stdout, self._stdout_queue),
            daemon=True
        )
        self._stdout_thread.start()

        # Stderr reader
        self._stderr_thread = threading.Thread(
            target=read_stream,
            args=(self._process.stderr, self._stderr_queue),
            daemon=True
        )
        self._stderr_thread.start()
```

**Files to Create**:
- `src/agents/claude_code_local.py`

**Tests to Write**:
- `tests/test_claude_code_local.py`
  - `test_initialize_spawns_process`
  - `test_process_has_valid_pid`
  - `test_stdin_is_writable`
  - `test_stdout_is_readable`
  - `test_cleanup_terminates_process`

---

### **M8.2: Interactive Communication** (2 hours)

**Deliverables**:
- `send_prompt()` implementation
- Output buffering and collection
- Completion detection
- Response parsing

**Acceptance Criteria**:
- ✅ Can send prompt and receive response
- ✅ Detects when output is complete
- ✅ Handles multi-line responses
- ✅ Timeouts work correctly
- ✅ Tests cover edge cases

**Technical Details**:

```python
def send_prompt(
    self,
    prompt: str,
    context: Optional[Dict[str, Any]] = None
) -> str:
    """Send prompt to Claude Code and get response.

    Args:
        prompt: Text prompt to send
        context: Optional context with timeout override

    Returns:
        Complete response from Claude Code

    Raises:
        AgentException: If agent encounters error
        AgentTimeoutException: If timeout exceeded
    """
    with self._lock:
        if not self._running or not self._process:
            raise AgentException("Agent not initialized")

        timeout = context.get('timeout', self._timeout) if context else self._timeout

        logger.info(f"Sending prompt (timeout={timeout}s)")
        logger.debug(f"Prompt: {prompt[:100]}...")

        try:
            # Clear output queues
            self._clear_queues()

            # Send prompt
            self._process.stdin.write(prompt + '\n')
            self._process.stdin.flush()

            # Collect response
            response = self._read_response(timeout)

            # Check for rate limiting
            if self._is_rate_limited(response):
                raise AgentException(
                    "Rate limit detected",
                    context={'response_preview': response[:200]},
                    recovery="Wait before sending next prompt"
                )

            logger.info(f"Received response ({len(response)} chars)")
            return response

        except BrokenPipeError:
            self._running = False
            raise AgentProcessException(
                "Claude Code process terminated unexpectedly",
                agent_type='claude-code-local'
            )
        except Exception as e:
            logger.error(f"Error in send_prompt: {e}")
            raise

def _read_response(self, timeout: int) -> str:
    """Read response from stdout until completion.

    Args:
        timeout: Timeout in seconds

    Returns:
        Complete response as string
    """
    start_time = time.time()
    buffer = []
    idle_count = 0
    max_idle = 10  # 1 second of no output

    while time.time() - start_time < timeout:
        try:
            # Try to get line from queue (non-blocking)
            line = self._stdout_queue.get(timeout=0.1)
            buffer.append(line)
            idle_count = 0

            # Check for completion
            response = ''.join(buffer)
            if self._is_complete(response):
                return response

        except queue.Empty:
            idle_count += 1
            # If we have data and no new output, check completion
            if buffer and idle_count >= max_idle:
                response = ''.join(buffer)
                if self._is_complete(response):
                    return response

    # Timeout
    raise AgentTimeoutException(
        operation='read_response',
        timeout_seconds=timeout,
        agent_type='claude-code-local'
    )

def _is_complete(self, output: str) -> bool:
    """Check if output is complete.

    Args:
        output: Output buffer to check

    Returns:
        True if output appears complete
    """
    # Check for completion markers
    for marker in self.COMPLETION_MARKERS:
        if marker in output:
            return True

    # Check for error markers (also indicates completion)
    for marker in self.ERROR_MARKERS:
        if marker in output:
            return True

    return False
```

**Constants**:

```python
# Output detection patterns
COMPLETION_MARKERS = [
    "✓",                    # Claude Code success
    "Done",                 # Completion word
    "Ready for next",       # Ready prompt
    "Task completed",       # Explicit completion
    "Successfully",         # Success indicator
]

ERROR_MARKERS = [
    "✗",                    # Claude Code error
    "Error:",               # Error prefix
    "Failed:",              # Failure indicator
    "Exception:",           # Python exceptions
    "FAILED",               # Test failures
]

RATE_LIMIT_MARKERS = [
    "rate limit",
    "too many requests",
    "try again later",
    "quota exceeded",
]
```

**Tests to Write**:
- `test_send_prompt_returns_response`
- `test_multiline_response_collected`
- `test_completion_detected_correctly`
- `test_timeout_raises_exception`
- `test_rate_limit_detected`

---

### **M8.3: Process Health & Recovery** (1.5 hours)

**Deliverables**:
- Health checking
- Crash detection
- Process restart with exponential backoff
- Graceful shutdown

**Acceptance Criteria**:
- ✅ Detects when process has crashed
- ✅ Can restart process automatically
- ✅ Implements exponential backoff for restarts
- ✅ Cleanup sends Ctrl+C before killing
- ✅ Tests verify recovery scenarios

**Technical Details**:

```python
def is_healthy(self) -> bool:
    """Check if Claude Code process is responsive.

    Returns:
        True if process is running and responsive
    """
    with self._lock:
        if not self._process or not self._running:
            return False

        # Check if process is alive
        if self._process.poll() is not None:
            logger.warning("Claude Code process has terminated")
            self._running = False
            return False

        # Try simple echo test
        try:
            self._process.stdin.write('\n')
            self._process.stdin.flush()
            return True
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            self._running = False
            return False

def _restart_process(self) -> None:
    """Restart Claude Code process with exponential backoff.

    Raises:
        AgentException: If all restart attempts fail
    """
    logger.warning("Restarting Claude Code process")

    # Cleanup old process
    self._cleanup_process()

    max_attempts = 5
    for attempt in range(1, max_attempts + 1):
        try:
            logger.info(f"Restart attempt {attempt}/{max_attempts}")

            # Reinitialize
            self.initialize(self._config)

            logger.info("Process restarted successfully")
            return

        except Exception as e:
            if attempt == max_attempts:
                raise AgentException(
                    f"Failed to restart after {max_attempts} attempts",
                    context={'last_error': str(e)},
                    recovery="Check Claude Code installation and permissions"
                )

            # Exponential backoff
            delay = min(2 ** attempt, 32)
            logger.warning(f"Restart failed: {e}. Retrying in {delay}s...")
            time.sleep(delay)

def cleanup(self) -> None:
    """Gracefully shutdown Claude Code process."""
    logger.info("Cleaning up ClaudeCodeLocalAgent")

    with self._lock:
        if not self._process:
            return

        self._running = False

        try:
            # Send Ctrl+C (SIGINT)
            self._process.send_signal(signal.SIGINT)
            logger.debug("Sent SIGINT to process")

            # Wait for graceful shutdown
            try:
                self._process.wait(timeout=5)
                logger.info("Process terminated gracefully")
                return
            except subprocess.TimeoutExpired:
                logger.warning("Process did not terminate, sending SIGTERM")

            # Force termination
            self._process.terminate()
            try:
                self._process.wait(timeout=3)
                logger.info("Process terminated via SIGTERM")
                return
            except subprocess.TimeoutExpired:
                logger.warning("Process still running, sending SIGKILL")

            # Kill if still running
            self._process.kill()
            self._process.wait()
            logger.info("Process killed")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

        finally:
            self._cleanup_process()

def _cleanup_process(self) -> None:
    """Internal cleanup helper."""
    if self._process:
        try:
            self._process.stdin.close()
        except Exception:
            pass
        self._process = None

    # Clear queues
    self._clear_queues()
```

**Tests to Write**:
- `test_is_healthy_returns_true_when_running`
- `test_is_healthy_returns_false_when_crashed`
- `test_restart_process_succeeds`
- `test_restart_uses_exponential_backoff`
- `test_cleanup_sends_sigint_first`
- `test_cleanup_kills_if_necessary`

---

### **M8.4: Integration & Registration** (1 hour)

**Deliverables**:
- Register agent in plugin system
- Add configuration examples
- Update CLI to support local agent
- Integration tests

**Acceptance Criteria**:
- ✅ Agent registered and discoverable
- ✅ Can be selected via config
- ✅ CLI commands work with local agent
- ✅ Integration tests pass

**Configuration**:

```yaml
# config/config.yaml
agent:
  type: claude-code-local  # Use local subprocess agent
  timeout: 300
  max_retries: 3
  workspace_path: /home/omarwsl/obra-runtime/workspace

  # Local agent specific config
  local:
    claude_command: claude  # Command to run Claude Code CLI
    startup_timeout: 30     # Seconds to wait for startup
    env:                    # Optional environment variables
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
```

**Registration**:

```python
# src/agents/__init__.py
from src.agents.claude_code_local import ClaudeCodeLocalAgent

# Agent is auto-registered via @register_agent decorator
```

**Integration Test**:

```python
# tests/test_integration_local_agent.py
def test_local_agent_end_to_end(test_config, tmp_path):
    """Test complete workflow with local agent."""
    # Setup
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    config = test_config.copy()
    config['agent'] = {
        'type': 'claude-code-local',
        'workspace_path': str(workspace),
        'timeout': 60
    }

    # Initialize orchestrator with local agent
    orchestrator = Orchestrator(config=config)
    orchestrator.initialize()

    # Create task
    state = orchestrator.state_manager
    project = state.create_project(
        name="Test",
        description="Test project",
        working_dir=str(workspace)
    )
    task = state.create_task(project.id, {
        'title': 'Create hello.py',
        'description': 'Create a simple hello world script',
        'priority': 10,
        'status': 'pending'
    })

    # Execute task
    result = orchestrator.execute_task(task.id, max_iterations=5)

    # Verify
    assert result['status'] in ['completed', 'escalated']
    assert result['iterations'] > 0

    # Cleanup
    orchestrator.shutdown()
```

**Tests to Write**:
- `test_agent_registered_in_registry`
- `test_agent_loadable_from_config`
- `test_cli_works_with_local_agent`
- `test_orchestrator_uses_local_agent`

---

### **M8.5: Documentation & Examples** (1.5 hours)

**Deliverables**:
- Architecture documentation update
- Setup guide for local agent
- Troubleshooting guide
- Code examples

**Acceptance Criteria**:
- ✅ Architecture docs reflect local agent
- ✅ Setup guide is complete and tested
- ✅ Troubleshooting covers common issues
- ✅ Examples demonstrate usage

**Documentation Updates**:

1. **docs/architecture/ARCHITECTURE.md**
   - Add local agent section
   - Update deployment diagram
   - Explain communication paths

2. **docs/guides/LOCAL_AGENT_SETUP.md** (NEW)
   - Prerequisites (Claude Code CLI installed)
   - Configuration examples
   - Testing steps
   - Common issues

3. **CLAUDE.md**
   - Add local agent to overview
   - Update pitfalls section
   - Add configuration examples

4. **README.md**
   - Update architecture diagram
   - Add local agent to features

**Example Documentation**:

````markdown
# Local Agent Setup Guide

## Prerequisites

1. **Claude Code CLI installed**:
   ```bash
   npm install -g @anthropics/claude-code
   ```

2. **API Key configured**:
   ```bash
   export ANTHROPIC_API_KEY="your-key-here"
   ```

3. **Verify Claude Code works**:
   ```bash
   claude
   # Should start interactive session
   ```

## Configuration

Edit `config/config.yaml`:

```yaml
agent:
  type: claude-code-local
  workspace_path: /home/omarwsl/obra-runtime/workspace
  timeout: 300

  local:
    claude_command: claude
    startup_timeout: 30
```

## Testing

```bash
# Create test project
python -m src.cli project create "Test Project"

# Create test task
python -m src.cli task create "Create hello.py" --project 1

# Execute task
python -m src.cli task execute 1
```

## Troubleshooting

### Claude Code not found
```
Error: [Errno 2] No such file or directory: 'claude'
```
**Solution**: Install Claude Code CLI or update `claude_command` in config

### Process hangs
**Solution**: Check Claude Code is not waiting for input, increase timeout

### Rate limit errors
**Solution**: Wait between tasks, check API key quotas
````

---

## Testing Strategy

### Unit Tests
- Mock subprocess for deterministic testing
- Test each method in isolation
- Edge cases: timeouts, crashes, empty output
- Target: 90%+ coverage

### Integration Tests
- Use real Claude Code CLI (if available) or mock
- Test complete workflows
- Verify state transitions
- Test error recovery

### Manual Testing
- Real tasks with Claude Code CLI
- Monitor process health
- Test various prompts
- Verify file operations

---

## Success Criteria

### Functional Requirements
- ✅ Spawns Claude Code CLI subprocess
- ✅ Sends prompts via stdin
- ✅ Reads responses from stdout
- ✅ Detects completion/errors
- ✅ Handles timeouts
- ✅ Detects rate limits
- ✅ Restarts on crash
- ✅ Graceful shutdown

### Non-Functional Requirements
- ✅ 90%+ test coverage
- ✅ No memory leaks
- ✅ Response time <500ms (excluding Claude processing)
- ✅ Clean resource cleanup
- ✅ Thread-safe operations

### Documentation Requirements
- ✅ ADR created
- ✅ Architecture updated
- ✅ Setup guide complete
- ✅ Code examples provided
- ✅ API documented

---

## Deployment Checklist

- [ ] Code implemented and reviewed
- [ ] Unit tests pass (90%+ coverage)
- [ ] Integration tests pass
- [ ] Manual testing complete
- [ ] Documentation updated
- [ ] Configuration examples added
- [ ] ADR approved
- [ ] Merged to main branch
- [ ] Deployed to test environment
- [ ] User acceptance testing
- [ ] Deployed to production

---

## Timeline

| Milestone | Estimated Hours | Dependencies |
|-----------|----------------|--------------|
| M8.1: Core Subprocess | 2-3 | None |
| M8.2: Communication | 2 | M8.1 |
| M8.3: Health & Recovery | 1.5 | M8.1, M8.2 |
| M8.4: Integration | 1 | M8.1, M8.2, M8.3 |
| M8.5: Documentation | 1.5 | All above |
| **Total** | **8 hours** | |

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Claude Code CLI not installed | High | Check in initialize(), clear error message |
| Process hangs indefinitely | Medium | Implement timeouts, health checks |
| Memory leaks from threads | Medium | Proper cleanup, daemon threads |
| Output parsing fails | Medium | Flexible markers, fallback detection |
| Rate limiting | Low | Detect and report clearly |

---

## Future Enhancements

1. **Streaming Support**: Real-time output streaming to user
2. **Multiple Sessions**: Parallel Claude Code processes
3. **Session Persistence**: Resume interrupted sessions
4. **Enhanced Parsing**: Better Claude Code output analysis
5. **Metrics**: Process stats, response times, success rates

---

## References

- ADR-004: Local Agent Architecture
- Python subprocess: https://docs.python.org/3/library/subprocess.html
- Claude Code CLI: https://docs.claude.com/en/docs/claude-code
- AgentPlugin base: `src/plugins/base.py`
- SSH agent reference: `src/agents/claude_code_ssh.py`

---

**Status**: Ready for implementation
**Next Steps**: Begin M8.1 - Core Subprocess Management
