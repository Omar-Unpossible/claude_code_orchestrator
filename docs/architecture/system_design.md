# System Design - Claude Code Orchestrator

## Overview

The Claude Code Orchestrator is an intelligent supervision system that wraps Claude Code CLI with a local LLM (Qwen) to enable semi-autonomous software development. The local LLM validates work, generates optimized prompts, and determines when human intervention is needed.

## High-Level Architecture

```
┌─────────────────────────────────────────┐
│  Local LLM (Qwen on RTX 5090)           │
│  • Validates agent's work               │
│  • Generates optimized prompts          │
│  • Scores confidence                    │
│  • Detects breakpoints                  │
│  • Maintains project state              │
└────────────┬────────────────────────────┘
             │ LLMPlugin Interface
             ▼
┌─────────────────────────────────────────┐
│  Orchestration Engine                   │
│  • TaskScheduler                        │
│  • DecisionEngine                       │
│  • QualityController                    │
│  • BreakpointManager                    │
└────────────┬────────────────────────────┘
             │ AgentPlugin Interface
             ▼
┌─────────────────────────────────────────┐
│  Agent Plugin (Pluggable)               │
│  • ClaudeCodeSSHAgent (VM)              │
│  • ClaudeCodeDockerAgent (Container)    │
│  • AiderAgent (Alternative)             │
│  • CustomAgent (User-defined)           │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│  File System & State                    │
│  • FileWatcher tracks changes           │
│  • StateManager persists everything     │
│  • Checkpoints enable rollback          │
└─────────────────────────────────────────┘
```

## Architectural Layers

### Layer 1: Presentation Layer
**Components**: CLI, Future Web UI, Future REST API
**Responsibility**: User interaction, input validation, output formatting
**Dependencies**: Orchestration Layer

### Layer 2: Orchestration Layer
**Components**: Orchestrator, DecisionEngine, TaskScheduler, BreakpointManager
**Responsibility**: High-level workflow control, decision making, task management
**Dependencies**: Domain Layer, Infrastructure Layer

### Layer 3: Domain Layer
**Components**: StateManager, QualityController, PromptGenerator, ResponseValidator
**Responsibility**: Core business logic, validation rules, quality standards
**Dependencies**: Infrastructure Layer

### Layer 4: Infrastructure Layer
**Components**: AgentPlugins, LLMPlugins, FileWatcher, Database
**Responsibility**: External integrations, I/O, persistence
**Dependencies**: None (leaf layer)

## Technology Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **Language** | Python 3.10+ | Rich ecosystem, async support, type hints |
| **Agent Interface** | SSH (paramiko) | Isolated VM execution for safety |
| **Local LLM** | Ollama | Easy setup, good performance |
| **Database** | SQLite/PostgreSQL | Lightweight (SQLite) or robust (PostgreSQL) |
| **File Watching** | watchdog | Proven library, cross-platform |
| **CLI Framework** | Click | Simple, powerful, well-documented |
| **Testing** | pytest | Industry standard, excellent plugins |
| **Type Checking** | mypy | Static type analysis |

## Non-Functional Requirements

### Performance
- Local LLM response (p95): <10s
- Agent interaction (p95): <30s
- State operation (p95): <100ms
- File change detection: <1s
- Iteration time (p95): <60s
- Memory usage (max): <8GB
- Startup time: <30s

### Scalability
- Handle projects with 10,000+ files
- Support long-running tasks (hours/days)
- Maintain performance under concurrent operations

### Reliability
- Graceful degradation on agent failure
- State recovery after crashes
- Transaction atomicity
- Automatic reconnection with exponential backoff

### Security
- Agent runs in isolated VM/container
- No direct access to host system from agent
- SSH key-based authentication
- File permissions properly enforced
- No hardcoded credentials

## Component Responsibilities

### StateManager
- Single source of truth for all state
- Manages projects, tasks, interactions, file changes
- Provides transaction support
- Handles checkpointing and rollback
- Thread-safe operations with proper locking
- **Rule**: All components MUST access state through StateManager

### Orchestrator
- Main control loop
- Coordinates all components
- Manages task execution flow
- Handles errors and recovery
- Triggers breakpoints when needed

### DecisionEngine
- Decides next action based on current state
- Routes based on confidence scores
- Determines if task is complete
- Triggers breakpoints for uncertain situations

### TaskScheduler
- Manages task queue
- Resolves dependencies
- Prioritizes tasks
- Detects circular dependencies

### QualityController
- Multi-stage validation
- Runs after ResponseValidator
- Checks correctness and requirements
- Executes tests
- Provides quality scores

### ResponseValidator
- Runs BEFORE QualityController
- Checks completeness (format, structure)
- Fast validation (no LLM calls)
- Different failure mode than quality control

### BreakpointManager
- Evaluates breakpoint rules
- Pauses execution when triggered
- Tracks resolution
- Provides context to user

### PromptGenerator
- Creates optimized prompts with context
- Uses Jinja2 templates
- Manages token budgets
- Includes relevant context from state

### FileWatcher
- Monitors workspace for changes
- Debounces rapid changes
- Filters by patterns
- Records hashes for change detection

### LocalLLMInterface
- Connects to Ollama/llama.cpp
- Handles generation with streaming
- Estimates token counts
- Provides health checking

## Data Flow

See [`data_flow.md`](./data_flow.md) for detailed sequence diagrams.

**High-Level Flow**:
1. User initiates task via CLI
2. Orchestrator gets next task from TaskScheduler
3. PromptGenerator creates optimized prompt with context
4. Agent (via plugin) executes task
5. FileWatcher detects changes
6. ResponseValidator checks completeness
7. QualityController validates correctness
8. DecisionEngine decides next action
9. StateManager persists everything
10. Loop continues or breakpoint triggered

## Deployment Models

### Development (Local)
- Claude Code as subprocess
- No isolation (fastest iteration)
- SQLite database
- Local file watching

### Production (VM via SSH)
- Claude Code in WSL2 VM
- Full isolation (can run dangerous mode)
- SSH connection (paramiko)
- Can use PostgreSQL
- Recommended for safety

### Distribution (Docker)
- Claude Code in container
- Good isolation
- Easy deployment
- docker-compose for orchestration
- Recommended for sharing

## Extensibility Points

### Plugin System
- **AgentPlugin**: Add new coding agents
- **LLMPlugin**: Add new LLM providers
- Decorator-based registration
- Configuration-driven selection

### Breakpoint Rules
- YAML-based rule definitions
- Custom rule evaluators
- Pluggable notification systems

### Quality Gates
- Custom validation stages
- Pluggable test executors
- Configurable thresholds

### Prompt Templates
- Jinja2-based templating
- Task-specific templates
- Context injection

## Design Patterns Used

| Pattern | Usage | Location |
|---------|-------|----------|
| **Plugin** | Agent and LLM extensibility | src/plugins/ |
| **Registry** | Plugin discovery | src/plugins/registry.py |
| **Singleton** | StateManager | src/core/state.py |
| **Template Method** | Prompt generation | src/llm/prompt_generator.py |
| **Observer** | File watching | src/monitoring/ |
| **Strategy** | Decision making | src/orchestration/decision.py |
| **Command** | Task execution | src/orchestration/task.py |
| **Factory** | Plugin instantiation | src/plugins/registry.py |

## Error Handling Strategy

### Exception Hierarchy
All exceptions inherit from `OrchestratorException` with:
- Context data preservation
- Recovery suggestions
- Serialization support

### Retry Logic
- Exponential backoff for network operations
- Max retry limits
- Different strategies per operation type

### Graceful Degradation
- Agent crash → attempt reconnect → escalate to breakpoint
- LLM unavailable → use cached responses → trigger breakpoint
- State corruption → rollback to checkpoint → notify user

## Monitoring and Observability

### Logging
- Structured logging (JSON)
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Component-specific loggers
- State changes always logged

### Metrics
- Task completion rate
- Confidence scores over time
- Breakpoint frequency
- Performance metrics (timing, memory)

### Debugging
- State snapshots for debugging
- Interaction history preserved
- File change history tracked
- Decision explanations recorded

## Future Enhancements (v2.0+)

- Multi-project orchestration
- Real-time web dashboard
- Git integration (automatic commits)
- Multi-language support beyond Python
- Distributed execution
- ML-based pattern learning
- Mobile app for breakpoint resolution
