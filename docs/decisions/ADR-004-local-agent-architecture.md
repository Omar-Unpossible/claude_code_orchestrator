# ADR-004: Local Agent Architecture for Claude Code CLI

**Status**: Proposed
**Date**: 2025-11-02
**Deciders**: System Architect
**Tags**: architecture, agent, claude-code, subprocess

---

## Context

Obra needs to interface with Claude Code CLI to execute development tasks. The current implementation only includes `ClaudeCodeSSHAgent`, which connects to Claude Code running on a remote VM via SSH. However, the target deployment has both Obra and Claude Code CLI running in the same WSL2 environment, making SSH unnecessary and inefficient.

### Current Architecture

```
┌─────────────────────────────────────────────────┐
│ Host (Windows 11 Pro)                            │
│  ├─ Ollama + Qwen (RTX 5090, GPU-accelerated)  │
│  └─ Hyper-V                                      │
│      └─ VM (Windows 11 Pro)                     │
│          └─ WSL2 (Ubuntu)                       │
│              ├─ Obra Orchestrator               │
│              └─ Claude Code CLI                 │
└─────────────────────────────────────────────────┘
```

### Problem Statement

1. **SSH Agent Inappropriate**: The `ClaudeCodeSSHAgent` is designed for remote VMs, not local subprocess execution
2. **No Claude Code Integration**: The SSH agent opens a generic shell but doesn't actually interface with Claude Code CLI
3. **Unnecessary Overhead**: Using SSH for same-machine communication adds latency and complexity
4. **Missing Functionality**: No agent exists to spawn Claude Code CLI as a subprocess and manage its stdin/stdout

### Requirements

1. **Local Execution**: Launch Claude Code CLI as a subprocess in the same environment
2. **Interactive Communication**: Send prompts via stdin, read responses from stdout
3. **Process Management**: Handle process lifecycle, health monitoring, and graceful shutdown
4. **Output Parsing**: Detect completion markers, error markers, and rate limit indicators
5. **LLM Separation**: Continue using Ollama on host machine for validation (via HTTP)

---

## Decision

We will implement **`ClaudeCodeLocalAgent`** to manage Claude Code CLI as a local subprocess.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ HOST MACHINE (Windows 11 Pro)                               │
│                                                              │
│  ┌────────────────────────────────────┐                    │
│  │  Ollama + Qwen 2.5 Coder          │                    │
│  │  Port: 11434                       │                    │
│  │  IP: 172.29.144.1                 │                    │
│  └────────────────────────────────────┘                    │
│           ↑                                                 │
│           │ HTTP API (validation/quality checks)            │
│           │                                                 │
│  ┌────────┴───────────────────────────────────────────┐   │
│  │ Hyper-V VM (Windows 11 Pro)                        │   │
│  │                                                      │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │ WSL2 (Ubuntu)                                 │  │   │
│  │  │                                               │  │   │
│  │  │  ┌─────────────────┐                         │  │   │
│  │  │  │  Obra           │                         │  │   │
│  │  │  │  Orchestrator   │                         │  │   │
│  │  │  └────────┬────────┘                         │  │   │
│  │  │           │                                   │  │   │
│  │  │           ├─→ HTTP API                       │  │   │
│  │  │           │   to Ollama                      │  │   │
│  │  │           │                                   │  │   │
│  │  │           └─→ subprocess.Popen               │  │   │
│  │  │               ['claude']                     │  │   │
│  │  │               ↓                               │  │   │
│  │  │           ┌─────────────────┐                │  │   │
│  │  │           │ Claude Code CLI │                │  │   │
│  │  │           │  (subprocess)   │                │  │   │
│  │  │           │  stdin ← prompts│                │  │   │
│  │  │           │  stdout → output│                │  │   │
│  │  │           └─────────────────┘                │  │   │
│  │  │                                               │  │   │
│  │  └───────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Key Design Principles

1. **Subprocess Management**: Use Python's `subprocess.Popen` with persistent process
2. **Non-blocking I/O**: Use threads for reading stdout/stderr without blocking
3. **State Machine**: Track process states (starting, ready, busy, error, stopped)
4. **Graceful Shutdown**: Send Ctrl+C, wait for cleanup, then terminate if needed
5. **Error Recovery**: Detect crashes, restart process, implement exponential backoff
6. **Output Detection**: Parse Claude Code output patterns for completion/errors

---

## Implementation Details

### Agent Interface

```python
@register_agent('claude-code-local')
class ClaudeCodeLocalAgent(AgentPlugin):
    """Claude Code agent running as local subprocess.

    Spawns Claude Code CLI as a child process and communicates
    via stdin/stdout pipes.
    """

    def initialize(self, config: Dict[str, Any]) -> None:
        """Start Claude Code CLI subprocess."""

    def send_prompt(self, prompt: str, context: Optional[Dict] = None) -> str:
        """Send prompt to Claude Code stdin and read response."""

    def is_healthy(self) -> bool:
        """Check if Claude Code process is running and responsive."""

    def cleanup(self) -> None:
        """Gracefully shutdown Claude Code process."""
```

### Process Lifecycle

```
[Stopped] ──initialize()──→ [Starting] ──ready──→ [Ready]
                                │                    │
                                │                    │
                                ↓                    ↓
                            [Error] ←──error─── [Busy]
                                │                    │
                                │                    │
                                └──restart()─────────┘
```

### Communication Flow

```
1. Obra → send_prompt("Create main.py")
2. Write to process.stdin: "Create main.py\n"
3. Flush stdin
4. Read from process.stdout (non-blocking)
5. Detect completion markers
6. Return complete response
```

### Output Detection Patterns

```python
COMPLETION_MARKERS = [
    "✓",                    # Claude Code success marker
    "Done",                 # Completion word
    "Ready for next",       # Ready prompt
    "Task completed",       # Explicit completion
]

ERROR_MARKERS = [
    "✗",                    # Claude Code error marker
    "Error:",               # Error prefix
    "Failed:",              # Failure indicator
    "Exception:",           # Python exceptions
]

RATE_LIMIT_MARKERS = [
    "rate limit",           # Rate limiting
    "too many requests",    # Quota exceeded
    "try again later",      # Retry message
]
```

---

## Consequences

### Positive

1. **✅ Simpler Architecture**: No SSH overhead for local communication
2. **✅ Lower Latency**: Direct process communication is faster than network
3. **✅ Better Control**: Full control over process lifecycle
4. **✅ Easier Debugging**: Can see stdin/stdout/stderr directly
5. **✅ No Authentication**: No SSH keys or credentials needed
6. **✅ File System Access**: Direct access to workspace files
7. **✅ LLM Independence**: Ollama stays on host (GPU), separate concern

### Negative

1. **❌ Same-Machine Only**: Cannot execute on remote machines (use SSH agent for that)
2. **❌ Process Management Complexity**: Must handle crashes, restarts, zombies
3. **❌ Output Parsing Required**: Must detect Claude Code's output patterns
4. **❌ Blocking Risk**: Incorrect I/O handling could block indefinitely

### Neutral

1. **🔄 Two Agent Types**: Will have both SSH and Local agents for different use cases
2. **🔄 Agent Selection**: User must choose appropriate agent in config

---

## Alternatives Considered

### Alternative 1: Use SSH to Localhost
**Rejected because:**
- Unnecessary complexity (SSH setup, keys, authentication)
- Added latency (network stack overhead)
- No benefits over direct subprocess

### Alternative 2: Use Docker Container
**Rejected because:**
- Not in requirements (user is using WSL2, not Docker)
- More overhead than subprocess
- Complicates file system access

### Alternative 3: Extend SSH Agent to Support Local Mode
**Rejected because:**
- Violates single responsibility principle
- Different connection methods have different concerns
- Would make SSH agent more complex

---

## Migration Path

### Phase 1: Implementation (Current)
1. Create `ClaudeCodeLocalAgent` class
2. Implement subprocess management
3. Add output parsing logic
4. Write unit tests

### Phase 2: Integration
1. Register agent in plugin system
2. Add configuration examples
3. Update CLI to support local agent
4. Integration tests

### Phase 3: Documentation
1. Update architecture docs
2. Add setup guide for local agent
3. Document troubleshooting
4. Add comparison guide (SSH vs Local)

### Phase 4: Deployment
1. Set `agent.type: claude-code-local` in config
2. Test with real tasks
3. Monitor performance and errors
4. Tune timeouts and buffers

---

## Related Decisions

- **ADR-001**: Plugin System - Local agent implements `AgentPlugin` interface
- **ADR-002**: Deployment Models - Local agent is for single-machine deployment
- **ADR-003**: State Management - Local agent reports state to StateManager

---

## References

- Python `subprocess` documentation: https://docs.python.org/3/library/subprocess.html
- Claude Code CLI documentation: https://docs.claude.com/en/docs/claude-code
- AgentPlugin interface: `src/plugins/base.py`
- Existing SSH agent: `src/agents/claude_code_ssh.py`

---

## Notes

- **LLM Location**: Ollama remains on host machine (GPU), accessed via HTTP
- **Two Communication Paths**:
  - Obra ↔ Claude Code: subprocess (stdin/stdout)
  - Obra ↔ Ollama: HTTP API (validation/quality)
- **Use Cases**:
  - **Local Agent**: Obra and Claude Code on same machine
  - **SSH Agent**: Obra and Claude Code on different machines
