# Claude Code Orchestrator - System Architecture

## Overview

The Claude Code Orchestrator is a supervision system where a local LLM (Qwen 2.5 on RTX 5090) provides intelligent oversight for Claude Code CLI executing tasks in an isolated environment. This enables semi-autonomous software development with continuous validation and quality control.

**Version**: 1.2.0 (M9 In Progress)
**Last Updated**: 2025-11-02

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         User Interface                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │     CLI      │  │ Interactive  │  │  Programmatic│      │
│  │   Commands   │  │     REPL     │  │      API     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└──────────────────────┬──────────────────────────────────────┘
                       │
           ┌───────────▼──────────────┐
           │    Orchestrator Core     │
           │  (Main Integration Loop) │
           └──────────┬───────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
┌───────▼───────┐ ┌──▼────┐ ┌─────▼──────┐
│   Components   │ │ State  │ │   Config   │
│   (M0-M5)     │ │Manager │ │  Manager   │
└───────────────┘ └────────┘ └────────────┘
```

## Component Architecture (M0-M5)

### M0: Plugin System (Architecture Foundation)

**Purpose**: Extensibility through pluggable agents and LLM providers

**Components**:
- `AgentPlugin` (ABC): Interface for code execution agents
- `LLMPlugin` (ABC): Interface for LLM providers
- `AgentRegistry`: Decorator-based agent registration
- `LLMRegistry`: Decorator-based LLM registration

**Design Pattern**: Abstract Factory + Registry

```python
@register_agent('claude_code')
class ClaudeCodeAgent(AgentPlugin):
    def send_prompt(self, prompt: str) -> str: ...
    def get_status(self) -> Dict: ...
```

### M1: Core Infrastructure

**Purpose**: State management, configuration, and data models

**Components**:
- `StateManager`: Single source of truth for all state (singleton, thread-safe)
- `Config`: Configuration management with YAML support
- SQLAlchemy Models: Project, Task, Interaction, Checkpoint, etc.
- Exception hierarchy: `OrchestratorException` with context

**Design Principles**:
- **ALL state access goes through StateManager**
- Atomic transactions for data integrity
- Thread-safe with RLock
- Rollback capability via checkpoints

### M2: LLM & Agent Interfaces

**Purpose**: Communication with local LLM and remote agents

**Components**:
- `LocalLLMInterface`: Ollama/llama.cpp integration for Qwen
- `PromptGenerator`: Creates optimized prompts with context
- `ResponseValidator`: Validates response completeness
- **Agent Implementations**:
  - `ClaudeCodeLocalAgent`: Claude Code CLI as local subprocess (recommended)
  - `ClaudeCodeSSHAgent`: Claude Code via SSH to remote VM
- `OutputMonitor`: Streams and parses agent output

**Agent Architecture**:

Two agent types support different deployment scenarios:

1. **Local Agent** (`claude-code-local`) - **Recommended for same-machine deployment**
   - Spawns Claude Code CLI as subprocess
   - Direct stdin/stdout communication
   - Lower latency, simpler setup
   - Use when: Obra and Claude Code run in same environment (e.g., WSL2)

2. **SSH Agent** (`claude-code-ssh`) - For remote deployment
   - Connects to Claude Code on remote VM via SSH
   - Network-based communication
   - Use when: Claude Code runs on different machine

**Key Separation**: Both agents communicate with **Ollama on host machine** via HTTP API for validation/quality scoring. The agent type only determines how Obra communicates with Claude Code CLI.

```
┌─────────────────────────────────────────────────────────────┐
│ HOST MACHINE                                                 │
│  Ollama + Qwen (GPU) ← HTTP API ← Both agent types          │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ WSL2                                                  │  │
│  │   Obra ─┬─→ subprocess → Claude Code (Local Agent)   │  │
│  │         └─→ SSH → Remote Claude Code (SSH Agent)     │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

**Key Features**:
- Pluggable agent system via `@register_agent` decorator
- Connection pooling and reconnection logic
- Streaming output parsing
- Completion detection heuristics
- Response format validation
- Process health monitoring and automatic recovery

### M3: File Monitoring

**Purpose**: Track all file changes for rollback capability

**Components**:
- `FileWatcher`: Watchdog-based filesystem monitoring
- Event batching with debouncing
- Change tracking in database

**Design**: Observer pattern with buffering

### M4: Orchestration Engine

**Purpose**: Task scheduling, decision making, quality control

**Components**:
- `TaskScheduler`: Priority-based task selection with dependency resolution
- `DecisionEngine`: Next-action decisions (PROCEED/ESCALATE/CLARIFY/RETRY)
- `QualityController`: Multi-stage validation (syntax, requirements, quality, testing)
- `BreakpointManager`: Human intervention points based on rules

**Decision Flow**:
```
Response → Validation → Quality Check → Confidence Score
    ↓
Decision Engine
    ├─ High confidence (>0.85) → PROCEED
    ├─ Medium (0.65-0.85) → CLARIFY or RETRY
    └─ Low (<0.65) → ESCALATE
```

### M5: Utility Services

**Purpose**: Cross-cutting concerns (tokens, context, confidence)

**Components**:
- `TokenCounter`: Accurate token counting with model-specific encoders
- `ContextManager`: Priority-based context building and summarization
- `ConfidenceScorer`: Multi-factor confidence assessment

**Features**:
- LRU caching for performance
- Ensemble scoring (heuristic + LLM)
- Calibration tracking

### M6: Integration & CLI

**Purpose**: Bring everything together with user interfaces

**Components**:
- `Orchestrator`: Main integration loop coordinating all M0-M5 components
- `cli.py`: Click-based CLI commands
- `interactive.py`: REPL interface

**8-Step Execution Loop**:
1. Build context from task + history + project
2. Generate optimized prompt
3. Send to agent for execution
4. Validate response format
5. Quality control checks
6. Confidence scoring
7. Decision engine evaluation
8. Handle action (proceed/escalate/clarify/retry)

## Data Flow

### Task Execution Flow

```
User creates task
    ↓
StateManager persists → Database
    ↓
Orchestrator.execute_task(task_id)
    ↓
┌─────────────────────────────────────┐
│  Execution Loop (max_iterations)    │
│                                     │
│  1. ContextManager.build_context    │
│     └─ TokenCounter (track usage)   │
│                                     │
│  2. PromptGenerator.generate        │
│                                     │
│  3. Agent.send_prompt               │
│     └─ OutputMonitor (streaming)    │
│                                     │
│  4. ResponseValidator.validate      │
│                                     │
│  5. QualityController.validate      │
│                                     │
│  6. ConfidenceScorer.score          │
│                                     │
│  7. DecisionEngine.decide           │
│     └─ BreakpointManager (check)    │
│                                     │
│  8. Handle Action:                  │
│     ├─ PROCEED → Mark complete      │
│     ├─ ESCALATE → Human needed      │
│     ├─ CLARIFY → Add feedback       │
│     └─ RETRY → Loop again           │
└─────────────────────────────────────┘
    ↓
StateManager updates task status
    ↓
FileWatcher detects changes
    ↓
Result returned to user
```

### State Management Flow

```
All Components
    ↓
StateManager (single source of truth)
    ↓
SQLAlchemy ORM
    ↓
SQLite/PostgreSQL Database
```

**Critical Rule**: NO component directly accesses database. ALL go through StateManager.

## Thread Safety

**Thread-Safe Components**:
- `StateManager`: RLock on all operations
- `ContextManager`: RLock on cache/context operations
- `ConfidenceScorer`: RLock on calibration data
- `Orchestrator`: RLock on state transitions

**Singleton Pattern**: StateManager, Config (prevent multiple instances)

## Error Handling Strategy

**Exception Hierarchy**:
```
Exception
 └─ OrchestratorException (base)
     ├─ ConfigException
     │   ├─ ConfigValidationException
     │   └─ ConfigNotFoundException
     ├─ StateException
     ├─ AgentException
     ├─ ValidationException
     └─ BreakpointException
```

**Error Context**: All exceptions include:
- Human-readable message
- Context dictionary (relevant state)
- Recovery suggestion string

**Error Recovery**:
- Agent failures: Retry with exponential backoff
- Validation failures: Accumulate feedback and retry
- Low confidence: Escalate to human
- Max retries: Escalate to human

## Configuration Architecture

**Configuration Sources** (in precedence order):
1. Environment variables (highest)
2. User config file (`config/config.yaml`)
3. Default config (`config/default_config.yaml`)

**Hot Reload**: Supports configuration reloading without restart

**Structure**:
```yaml
database:
  url: sqlite:///orchestrator.db

agent:
  type: claude_code  # or mock, aider
  config:
    ssh_host: 192.168.1.100
    timeout: 300

llm:
  provider: ollama
  model: qwen2.5-coder:32b
  base_url: http://localhost:11434

orchestration:
  breakpoints:
    confidence_threshold: 0.7
  decision:
    high_confidence: 0.85
  quality:
    min_quality_score: 0.7
  scheduler:
    max_concurrent_tasks: 1
```

## Deployment Architecture

**Supported Deployments**:

### 1. Local Development
```
┌──────────────────────────────────┐
│  Windows 11 Host                 │
│  ┌────────────────────────────┐ │
│  │  WSL2                      │ │
│  │  ├─ Orchestrator           │ │
│  │  └─ SQLite DB              │ │
│  └────────────────────────────┘ │
│  ┌────────────────────────────┐ │
│  │  NVIDIA GPU                │ │
│  │  └─ Ollama + Qwen 2.5      │ │
│  └────────────────────────────┘ │
└──────────────────────────────────┘
         │ SSH
         ▼
┌──────────────────────────────────┐
│  Isolated VM                     │
│  └─ Claude Code CLI              │
└──────────────────────────────────┘
```

### 2. Docker Deployment
```
┌──────────────────────────────────┐
│  Docker Host                     │
│  ┌────────────────────────────┐ │
│  │ orchestrator container     │ │
│  │ ├─ Python app              │ │
│  │ └─ PostgreSQL              │ │
│  └────────────────────────────┘ │
│  ┌────────────────────────────┐ │
│  │ llm container              │ │
│  │ └─ Ollama + Qwen           │ │
│  └────────────────────────────┘ │
└──────────────────────────────────┘
```

## Performance Targets

| Metric | Target | Achieved |
|--------|--------|----------|
| LLM Response (p95) | <10s | ~5s (Qwen 32B) |
| Agent Interaction (p95) | <30s | Variable (agent-dependent) |
| State Operation (p95) | <100ms | <10ms |
| Orchestrator Init | <30s | <1s |
| File Change Detection | <1s | <100ms |

## Security Considerations

**Agent Isolation**:
- Claude Code runs in isolated VM/container
- SSH with key-based authentication only
- No direct filesystem access from orchestrator

**Secrets Management**:
- SSH keys stored securely
- Config sanitization for logging
- No secrets in database

**Input Validation**:
- All user inputs validated
- SQL injection prevention via ORM
- Command injection prevention in SSH layer

## Scalability

**Current Limits**:
- Single orchestrator instance
- Single agent (serialized task execution)
- SQLite for <1000 tasks

**Future Scalability** (v2.0):
- Multi-agent parallel execution
- PostgreSQL for production
- Distributed task queue (Celery/RQ)
- Horizontal scaling with load balancer

## Monitoring & Observability

**Logging**:
- Structured logging (Python `logging`)
- Log levels: DEBUG, INFO, WARNING, ERROR
- Context in all log messages

**Metrics** (future):
- Task success rate
- Confidence calibration accuracy
- Response time percentiles
- Resource utilization

**State Tracking**:
- All task state transitions logged
- Breakpoint triggers recorded
- File changes tracked

## Testing Strategy

**Test Pyramid**:
```
        ┌────────┐
        │  E2E   │  10% (integration tests)
        └────────┘
      ┌────────────┐
      │ Integration│  20% (component integration)
      └────────────┘
    ┌──────────────────┐
    │   Unit Tests     │  70% (component isolation)
    └──────────────────┘
```

**Coverage Targets**:
- Overall: ≥85%
- Critical modules (StateManager, DecisionEngine): ≥90%

**Test Types**:
- Unit: Mock all dependencies
- Integration: Real components, mock external services
- E2E: Full workflow, mock agent for speed

## Dependencies

**Core**:
- Python 3.10+
- SQLAlchemy 2.0+
- Click 8.0+ (CLI)
- PyYAML 6.0+

**Optional**:
- Paramiko (SSH agent)
- Watchdog (file monitoring)
- Tiktoken (accurate token counting)
- Ollama (local LLM)

## M9: Core Enhancements (v1.2) 🚧 IN PROGRESS

**Purpose**: Reliability, workflow management, and usability improvements

### Components

#### 1. Retry Logic with Exponential Backoff
**Module**: `src/utils/retry_manager.py`

**Purpose**: Gracefully handle transient failures (rate limits, timeouts, network issues)

**Key Features**:
- Exponential backoff: 1s → 2s → 4s → 8s → 16s (configurable)
- Jitter prevents thundering herd
- Retryable vs non-retryable error classification
- Integration points: Agent calls, LLM calls
- Detailed retry logging

**Configuration**:
```yaml
retry:
  max_attempts: 5
  base_delay: 1.0
  max_delay: 60.0
  backoff_multiplier: 2.0
  jitter: 0.1
```

#### 2. Task Dependency System
**Modules**:
- `src/orchestration/dependency_resolver.py`
- `src/core/models.py` (Task model update)
- Database migration: Add `depends_on` JSON field

**Purpose**: Enable complex workflows with task dependencies

**Key Features**:
- Define dependencies: Task B depends on Task A, C
- Topological sort for execution order
- Cycle detection (reject circular dependencies)
- Automatic blocking until dependencies complete
- Cascading failure handling
- Visual dependency graph in reports

**Database Schema**:
```sql
ALTER TABLE tasks ADD COLUMN depends_on TEXT;  -- JSON array
```

**Configuration**:
```yaml
dependencies:
  max_depth: 10
  allow_cycles: false
  fail_on_dependency_error: true
```

#### 3. Git Auto-Integration
**Module**: `src/utils/git_manager.py`

**Purpose**: Automatic version control with semantic commits

**Key Features**:
- Auto-commit after successful task completion
- LLM-generated semantic commit messages
- Branch per task: `obra/task-{id}-{slug}`
- Optional PR creation via `gh` CLI
- Rollback support via git
- Configurable commit strategy

**Commit Message Format**:
```
feat(module): Task title

Description...

- Change 1
- Change 2

Obra Task ID: #123
Confidence: 0.85
Quality Score: 0.90
```

**Configuration**:
```yaml
git:
  enabled: true
  auto_commit: true
  commit_strategy: per_task  # per_task | per_milestone | manual
  create_branch: true
  branch_prefix: obra/task-
  auto_pr: false
```

#### 4. Configuration Profiles
**Module**: `src/core/config.py` (updated)
**Profiles**: `config/profiles/*.yaml`

**Purpose**: Pre-configured settings for different project types

**Profiles**:
- `python_project.yaml` - Python development with pytest
- `web_app.yaml` - Web application (Node.js, React)
- `ml_project.yaml` - Machine learning/data science
- `microservice.yaml` - Microservice architecture
- `minimal.yaml` - Minimal overhead
- `production.yaml` - Production-ready, high quality

**Profile Loading Priority** (highest to lowest):
1. CLI arguments
2. Environment variables
3. User config
4. Project config
5. **Profile** ← NEW
6. Default config

**Usage**:
```bash
obra project create "My Python App" --profile python_project
```

### Architecture Impact

**New Modules** (3):
- `src/utils/retry_manager.py` (~100 lines)
- `src/orchestration/dependency_resolver.py` (~250 lines)
- `src/utils/git_manager.py` (~200 lines)

**Updated Modules** (5):
- `src/core/models.py` - Task model with dependencies
- `src/core/state.py` - Dependency queries
- `src/core/config.py` - Profile loading
- `src/orchestrator.py` - Git integration, dependency checking
- `src/cli.py` - New flags

**Database Changes**:
- Migration: Add `depends_on` field to tasks table

**Configuration Files** (6 profiles):
- `config/profiles/*.yaml` (~50 lines each)

**Tests** (~270 new tests):
- Retry logic: 50 tests
- Dependencies: 80 tests
- Git integration: 60 tests
- Profiles: 40 tests
- Integration: 40 tests

**Total M9 Code**:
- Production: ~650 lines
- Tests: ~800 lines
- Config/Docs: ~700 lines
- **Total: ~2,150 lines**

### Data Flow Updates

**With Retry Logic**:
```
Agent call → RetryManager wraps call → Exponential backoff on failure
LLM call → RetryManager wraps call → Exponential backoff on failure
```

**With Dependencies**:
```
Orchestrator gets task
    ↓
DependencyResolver checks dependencies
    ↓
If blocked: Skip task, log reason
If ready: Proceed with execution
    ↓
On completion: Update dependent tasks
```

**With Git Integration**:
```
Task completed successfully
    ↓
GitManager checks git status
    ↓
Generate commit message (LLM)
    ↓
Create branch (if enabled)
    ↓
Commit changes
    ↓
Optional: Create PR via gh CLI
```

## Future Architecture Enhancements

**v1.3** (After M9):
- Budget & Cost Controls (P0)
- Metrics & Reporting System (P0)
- Checkpoint System (P0)
- Prompt Template Library (P0)
- Escalation Levels (P0)

**v1.4+**:
- Web UI dashboard
- Real-time WebSocket updates
- Multi-project orchestration
- Pattern learning from successful tasks

**v2.0**:
- Distributed architecture
- Advanced ML-based pattern learning
- Multi-agent collaboration

---

**Architecture Decisions**: See `docs/decisions/ADR-*.md` for detailed rationale behind key design choices.
