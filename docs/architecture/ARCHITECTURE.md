# Claude Code Orchestrator - System Architecture

## Overview

The Claude Code Orchestrator is a supervision system where a local LLM (Qwen 2.5 on RTX 5090) provides intelligent oversight for Claude Code CLI executing tasks in an isolated environment. This enables semi-autonomous software development with continuous validation and quality control.

**Version**: 1.7.0 (Unified Execution Architecture)
**Last Updated**: 2025-11-13

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

## Unified Execution Architecture (v1.7.0)

**Status**: ✅ IMPLEMENTED (ADR-017)
**Released**: November 13, 2025
**Stories Completed**: 0-7 (all complete)

### Problem: Parallel Execution Paths (v1.6.0)

Prior to v1.7.0, Obra had **two separate execution paths** with different quality guarantees:

**Path 1: Task Execution** → Full 8-step orchestration pipeline
**Path 2: Natural Language Commands** → Direct CRUD execution (bypassed orchestration)

**Impact**: Inconsistent quality, architectural debt, lost capabilities (retry, quality scoring, breakpoints) for NL commands.

### Solution: Unified Entry Point (v1.7.0)

All commands now route through `orchestrator.execute_task()` for consistent quality validation:

```
User Input (any interface: CLI, NL, Interactive)
    ↓
┌─────────────────────────────────────────────┐
│ Is Natural Language?                        │
├─────────────────────────────────────────────┤
│ YES → NL Parsing Pipeline (intent → task)   │
│       • IntentClassifier (COMMAND/QUESTION) │
│       • EntityExtractor (5-stage ADR-016)   │
│       • IntentToTaskConverter (NEW)         │
│       • Task object with NL context         │
│                                             │
│ NO  → Task from CLI/API                     │
│       • Direct Task object creation         │
└─────────────────────────────────────────────┘
    ↓
orchestrator.execute_task() ← UNIFIED ENTRY POINT
    ↓
┌─────────────────────────────────────────────┐
│ UNIFIED EXECUTION PIPELINE (8 steps)        │
├─────────────────────────────────────────────┤
│ 1. Context Building (ContextManager)        │
│ 2. Prompt Generation (StructuredPromptBuilder)│
│ 3. Agent Execution (Claude Code)            │
│ 4. Response Validation (ResponseValidator)  │
│ 5. Quality Control (QualityController)      │
│ 6. Confidence Scoring (ConfidenceScorer)    │
│ 7. Decision Making (DecisionEngine)         │
│ 8. Action Handling (proceed/retry/escalate) │
└─────────────────────────────────────────────┘
    ↓
Result with full quality guarantees (ALL interfaces)
```

### New Components (v1.7.0)

#### IntentToTaskConverter

**Purpose**: Convert parsed NL intent → Task object for orchestrator

**Location**: `src/orchestration/intent_to_task_converter.py`

**Methods**:
- `convert(parsed_intent: OperationContext, project_id: int) -> Task`
- `_enrich_with_nl_context(task: Task, original_message: str) -> Task`
- `_map_parameters(op_context: OperationContext) -> Dict[str, Any]`

**Operation Mapping**:
- CREATE → Task with title/description from parsed params
- UPDATE → Task with "Update X" title + update instructions
- DELETE → Task with "Delete X" title + safety context
- QUERY → Task with "Show X" title + query parameters (or NLQueryHelper)

#### NLQueryHelper (Refactored)

**Purpose**: Read-only query helper for orchestrator

**Before**: `CommandExecutor` (did everything - parse, validate, execute CRUD)
**After**: `NLQueryHelper` (provides query context for orchestrator)

**Location**: `src/nl/nl_query_helper.py` (renamed from `command_executor.py`)

**Methods**:
- `build_query_context(op_context: OperationContext) -> Dict` (renamed from `execute()`)
- Supports: SIMPLE, HIERARCHICAL, NEXT_STEPS, BACKLOG, ROADMAP queries
- Returns: Query metadata (filters, sort order, entity type)

**Removed**: All write operations (_execute_create, _execute_update, _execute_delete)

### Benefits

1. **Consistent Quality**: All commands validated through multi-stage pipeline
2. **Simplified Architecture**: Single execution model (was 2)
3. **Enhanced Capabilities**: NL commands get retry logic, quality scoring, breakpoints
4. **Preserved Investment**: ADR-016 components (5-stage pipeline) still valuable
5. **Future-Proof**: Multi-action NL, voice input, complex workflows now possible

### Trade-offs

**Positive**:
- ✅ Consistent quality across all interfaces
- ✅ ~40% reduction in integration test surface area
- ✅ Retry logic, breakpoints, quality validation for NL

**Negative**:
- ⚠️ ~500ms additional latency for NL commands (quality > speed)
- ⚠️ Breaking changes to internal APIs (migration guide provided)

### Migration Path

**Internal API Changes** (v1.7.0):
- `NLCommandProcessor.process()` → Returns `ParsedIntent` (was `NLResponse`)
- `CommandExecutor` → Renamed to `NLQueryHelper` (write operations removed)

**User-Facing Changes**: **None** (commands work identically)

**Rollback**: Legacy mode available via config (emergency only):
```yaml
nl_commands:
  use_legacy_executor: false  # Set true for emergency rollback
```

**See**: `docs/guides/ADR017_MIGRATION_GUIDE.md` for complete migration guide

**Reference**: `docs/decisions/ADR-017-unified-execution-architecture.md`

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

## M9: Core Enhancements (v1.2) ✅ COMPLETE

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

## v1.3 Features ✅ COMPLETE

### Agile Work Hierarchy (ADR-013)
**Purpose**: Industry-standard work breakdown structure for organizing development at scale

**Components**:
- **TaskType Enum**: EPIC, STORY, TASK, SUBTASK (replaces generic "Task")
- **Epic**: Large feature spanning multiple stories (3-15 sessions)
- **Story**: User-facing deliverable (1 orchestration session)
- **Task**: Technical work implementing story (default type)
- **Subtask**: Granular step (via parent_task_id hierarchy)
- **Milestone**: Zero-duration checkpoint (not work items)

**Data Model**:
```python
Task:
  - task_type: TaskType (EPIC | STORY | TASK | SUBTASK)
  - epic_id: Optional[int]
  - story_id: Optional[int]
  - parent_task_id: Optional[int]  # For subtasks

Milestone:
  - name: str
  - description: str
  - required_epic_ids: List[int]  # JSON array
  - achieved: bool
```

**StateManager Methods**:
- `create_epic()`, `create_story()`, `get_epic_stories()`, `execute_epic()`
- `create_milestone()`, `check_milestone_completion()`, `achieve_milestone()`

**CLI Commands**:
```bash
obra epic create/list/show/execute
obra story create/list/show
obra milestone create/check/achieve
```

**Backward Compatibility**: Existing tasks default to `TaskType.TASK`. Subtask hierarchy preserved via `parent_task_id`.

---

### Interactive Streaming Interface
**Purpose**: Real-time command injection and human-in-the-loop control during orchestration

**Components**:
- **CommandProcessor** (`src/utils/command_processor.py`): Parses and executes interactive commands
- **InputManager** (`src/utils/input_manager.py`): Non-blocking input with `prompt_toolkit`
- **StreamingHandler**: Real-time output streaming from agent

**Interactive Commands** (8 commands):
```
/pause              - Pause execution after current turn
/resume             - Resume paused execution
/to-impl <msg>      - Send message to implementer (Claude Code)
/to-orch <msg>      - Send message to orchestrator (Qwen/LLM)
/override-decision  - Override Obra's current decision
/status             - Show task status, iteration, metrics
/help               - Show command help
/stop               - Stop execution gracefully
```

**Interactive Checkpoints** (6 injection points):
1. Before agent execution
2. After agent response
3. Before validation
4. After validation (if low confidence)
5. Before decision execution
6. On error/exception

**Architecture**:
```
User Input Thread (non-blocking)
    ↓
CommandProcessor (parse /commands)
    ↓
Orchestrator.injected_context (dict)
    ↓
Next iteration incorporates context
```

**Key Features**:
- **Last-wins policy**: New `/to-impl` replaces previous one
- **Intent classification**: `/to-orch` categorized as validation_guidance, decision_hint, or feedback_request
- **Thread-safe**: `prompt_toolkit` with proper input thread management

---

### Dynamic Agent Labels (/to-impl, /to-orch)
**Purpose**: Flexible agent terminology that adapts to actual deployment (Claude Code, Aider, Qwen, OpenAI Codex, etc.)

**Evolution**:
- **Phase 1**: Changed `/to-claude` → `/to-impl` (implementer)
- **Phase 2**: Changed `/to-obra` → `/to-orch` (orchestrator)
- **Phase 3**: Added intent detection for `/to-orch` messages

**Aliases** (backward compatibility):
- `/to-claude` → `/to-impl`
- `/to-obra` → `/to-orch`
- `/to-implementer` → `/to-impl`
- `/to-orchestrator` → `/to-orch`

**Intent Detection** (Phase 3):
```python
/to-orch "Be more lenient with quality scores"
  → Intent: validation_guidance
  → Effect: Injected into quality scoring prompt

/to-orch "Accept this even if quality is borderline"
  → Intent: decision_hint
  → Effect: Adjusts decision thresholds

/to-orch "Review code and suggest 3 improvements"
  → Intent: feedback_request
  → Effect: Generates feedback sent to implementer
```

---

### Flexible LLM Orchestrator
**Purpose**: Support multiple LLM providers (local GPU, remote CLI, API-based)

**Supported Providers**:
1. **Ollama** (Local LLM): Qwen 2.5 Coder on RTX 5090 via HTTP API
2. **OpenAI Codex CLI**: Remote subscription-based LLM via subprocess
3. **Mock LLM**: Testing and development

**LLM Plugin System**:
```python
@register_llm('ollama')
class LocalLLMInterface(LLMPlugin):
    def generate(self, prompt: str) -> str: ...

@register_llm('openai-codex')
class OpenAICodexLLMPlugin(LLMPlugin):
    def generate(self, prompt: str) -> str: ...
```

**Configuration**:
```yaml
llm:
  type: ollama  # or openai-codex, mock
  model: qwen2.5-coder:32b
  api_url: http://localhost:11434
```

**Dual Deployment Architecture**:
- **Option A**: Local GPU (Ollama + Qwen) - Hardware deployment
- **Option B**: Remote CLI (OpenAI Codex) - Subscription deployment

**Provider Selection**: `LLMRegistry.get(llm_type)()` - Dynamic at runtime

---

### Natural Language Command Interface (ADR-014) - v1.3.0 🆕
**Purpose**: Enable conversational interaction with Obra - create work items using natural language instead of exact command syntax

**Architecture**: Multi-stage LLM pipeline

```
User Input: "Create an epic for user authentication"
    ↓
IntentClassifier (95% accuracy)
    ├─ COMMAND → Entity Extraction
    ├─ QUESTION → Forward to Claude Code
    └─ CLARIFICATION_NEEDED → Ask user
    ↓
EntityExtractor (90% accuracy)
    └─ Extract: {entity_type: 'epic', title: 'User Authentication', ...}
    ↓
CommandValidator
    └─ Validate: Epic doesn't exist, no cycles, required fields present
    ↓
CommandExecutor
    └─ Execute: state_manager.create_epic(...)
    ↓
ResponseFormatter
    └─ Format: "✓ Created Epic #5: User Authentication"
```

**Components** (6 modules in `src/nl/`):
1. **IntentClassifier**: COMMAND/QUESTION/CLARIFICATION_NEEDED detection
2. **EntityExtractor**: Schema-aware entity extraction (epic/story/task/subtask)
3. **CommandValidator**: Business rule validation (epic exists, no cycles)
4. **CommandExecutor**: StateManager integration with transaction safety
5. **ResponseFormatter**: Color-coded responses (green/red/yellow)
6. **NLCommandProcessor**: Pipeline orchestrator with conversation context

**Integration with CommandProcessor**:
```python
# Automatic routing
if input.startswith('/'):
    execute_slash_command(input)  # /pause, /to-impl, etc.
else:
    nl_processor.process(input)    # Natural language
```

**Key Features**:
- **Conversation Context**: Maintains 10-turn history for multi-turn interactions
- **Reference Resolution**: "Add story to the User Auth epic" → resolves epic name to ID
- **Multi-Item Support**: "Create 3 tasks: login, signup, MFA" → 3 tasks created
- **Confirmation Workflow**: Destructive ops (delete/update) require explicit confirmation
- **Graceful Degradation**: Low confidence (<0.7) triggers clarification request

**Configuration**:
```yaml
nl_commands:
  enabled: true
  llm_provider: ollama
  confidence_threshold: 0.7
  max_context_turns: 10
  schema_path: src/nl/schemas/obra_schema.json
  default_project_id: 1
  require_confirmation_for: [delete, update, execute]
  fallback_to_info: true
```

**Examples**:
```
> Create an epic for user authentication
✓ Created Epic #5: User Authentication
  Next: Add stories with 'create story in epic 5'

> Add 3 stories to it: login, signup, and MFA
✓ Created 3 storys under Epic #5: #6, #7, #8

> How many epics do I have?
Forwarding question to Claude Code: How many epics do I have?
[Response from Claude Code]
```

**Performance**:
- Intent classification: <2s (P95)
- End-to-end: <3s (P95)
- Accuracy: 95% intent, 90% entity extraction

**Test Coverage**: 103 tests (27 ResponseFormatter + 22 IntentClassifier + 24 EntityExtractor + 30 CommandValidator/Executor + 13 integration)

---

## v1.4 Features ✅ COMPLETE

### Project Infrastructure Maintenance System (ADR-015) - v1.4.0 🆕

**Purpose**: Automate project documentation maintenance through event-driven triggers and periodic freshness checks.

**Value**: Ensures CHANGELOG, architecture docs, ADRs, and guides stay current without manual intervention. Obra "eats its own dog food" by maintaining its own documentation.

#### Components

**1. DocumentationManager** (`src/utils/documentation_manager.py`)

Core class for documentation maintenance with 10 public methods:

```python
class DocumentationManager:
    # Core functionality
    def check_documentation_freshness() -> Dict[str, DocumentStatus]
    def create_maintenance_task(trigger, scope, context) -> int
    def generate_maintenance_prompt(stale_docs, context) -> str

    # Utility methods
    def archive_completed_plans(epic_id) -> List[str]
    def update_changelog(epic) -> None
    def suggest_adr_creation(epic) -> bool
    def check_file_freshness(path) -> DocumentStatus

    # Periodic scheduling (Story 2.1)
    def start_periodic_checks(project_id) -> bool
    def stop_periodic_checks() -> None
    def _run_periodic_check(project_id) -> None  # Internal
```

**2. StateManager Integration**

**Hooks Added**:
- `complete_epic()` → Creates maintenance task if `requires_adr=True` or `has_architectural_changes=True`
- `achieve_milestone()` → Creates comprehensive maintenance task with all epic context

**Database Fields Added** (Migration 004):
```sql
-- Task model
ALTER TABLE tasks ADD COLUMN requires_adr BOOLEAN DEFAULT FALSE;
ALTER TABLE tasks ADD COLUMN has_architectural_changes BOOLEAN DEFAULT FALSE;
ALTER TABLE tasks ADD COLUMN changes_summary TEXT NULL;
ALTER TABLE tasks ADD COLUMN documentation_status VARCHAR(20) DEFAULT 'pending';

-- Milestone model
ALTER TABLE milestones ADD COLUMN version VARCHAR(20) NULL;

-- Indexes
CREATE INDEX idx_tasks_documentation_status ON tasks(documentation_status);
CREATE INDEX idx_tasks_requires_adr ON tasks(requires_adr) WHERE requires_adr = TRUE;
```

**3. Configuration Schema**

```yaml
documentation:
  enabled: true  # Master switch
  auto_maintain: true  # Create tasks vs notification only

  maintenance_targets:
    - 'CHANGELOG.md'
    - 'docs/architecture/ARCHITECTURE.md'
    - 'docs/README.md'
    - 'docs/decisions/'
    - 'docs/guides/'

  freshness_thresholds:
    critical: 30   # days (CHANGELOG, README)
    important: 60  # days (architecture, ADRs)
    normal: 90     # days (guides)

  archive:
    enabled: true
    source_dir: 'docs/development'
    archive_dir: 'docs/archive/development'
    patterns: ['*_IMPLEMENTATION_PLAN.md', '*_COMPLETION_PLAN.md']

  triggers:
    epic_complete:
      enabled: true
      scope: comprehensive
      auto_create_task: true

    milestone_achieved:
      enabled: true
      scope: comprehensive
      auto_create_task: true

    periodic:
      enabled: true
      interval_days: 7
      scope: lightweight
      auto_create_task: true

  task_config:
    priority: 3
    assigned_agent: 'CLAUDE_CODE'
```

#### Architecture Design

**Threading Model (Periodic Checks)**:
- Uses `threading.Timer` for scheduling
- Daemon threads for automatic cleanup
- Thread-safe with `threading.Lock`
- Auto-rescheduling after each check
- Graceful shutdown via `stop_periodic_checks()`

**Data Flow**:

```
Epic Completion
    ↓
StateManager.complete_epic()
    ↓
Check requires_adr or has_architectural_changes
    ↓
If True → DocumentationManager.create_maintenance_task()
    ↓
Check freshness → Detect stale docs
    ↓
Generate prompt with epic context
    ↓
Create Task (priority=3, type=TASK)
    ↓
Task includes: epic details, changes, stale doc list
```

**Periodic Check Flow**:

```
start_periodic_checks(project_id)
    ↓
Timer starts (interval_days * 24 * 60 * 60 seconds)
    ↓
[After interval expires]
    ↓
_run_periodic_check()
    ↓
check_documentation_freshness()
    ↓
If stale docs found:
    - auto_create_task=true → Create task
    - auto_create_task=false → Log warning
    ↓
Reschedule next check (new Timer)
    ↓
Repeat...
```

#### Document Categorization

**Critical** (30-day threshold):
- CHANGELOG.md
- README.md

**Important** (60-day threshold):
- docs/architecture/ARCHITECTURE.md
- docs/decisions/*.md (ADRs)

**Normal** (90-day threshold):
- docs/guides/*.md
- Other documentation

#### Maintenance Scopes

1. **Lightweight**: Quick CHANGELOG updates
2. **Comprehensive**: CHANGELOG + architecture + ADRs + guides
3. **Full Review**: Complete documentation audit (for milestones/releases)

#### Task Context Structure

```python
{
    'trigger': 'epic_complete',  # or 'milestone_achieved', 'periodic'
    'scope': 'comprehensive',
    'maintenance_context': {
        'epic_id': 5,
        'epic_title': 'User Authentication System',
        'epic_description': '...',
        'changes': 'Added OAuth, MFA, session management',
        'stories': [
            {'id': 10, 'title': 'OAuth integration', 'description': '...'},
            {'id': 11, 'title': 'MFA support', 'description': '...'}
        ],
        'project_id': 1
    },
    'stale_docs': {
        'CHANGELOG.md': {
            'path': 'CHANGELOG.md',
            'age_days': 45,
            'category': 'critical',
            'is_stale': True,
            'threshold_days': 30
        }
    }
}
```

#### Test Coverage

**Total Tests**: 50 (42 unit + 8 integration)
- **Story 1.1**: 30 unit tests (DocumentationManager core)
- **Story 2.1**: 12 unit tests (Periodic scheduler)
- **Story 1.4**: 8 integration tests (E2E workflows)

**Coverage**: 91% (exceeds >90% target)

**Integration Tests Verify**:
1. Epic completion → maintenance task creation
2. Milestone achievement → comprehensive task
3. Epic without flags → no task created
4. documentation.enabled=false → no tasks
5. Freshness check detects stale docs correctly
6. archive_completed_plans() moves files correctly
7. Full workflow: create epic → complete → verify task
8. StateManager hooks integrate properly

#### Performance

**Hook Execution**:
- Epic completion hook: <100ms (P95)
- Milestone achievement hook: <200ms (P95)
- Freshness check (50 docs): <500ms

**Periodic Checks**:
- Timer overhead: <2KB memory
- Thread count: 1 daemon thread per instance
- CPU idle: ~0% when not checking
- Check execution: <500ms (depends on doc count)

#### Usage Example

```python
# Create epic with documentation flags
epic_id = state_manager.create_epic(
    project_id=1,
    title="Payment Processing",
    description="Stripe integration",
    requires_adr=True,  # Requires ADR
    has_architectural_changes=True,  # Architectural changes
    changes_summary="Integrated Stripe API, added payment models, webhooks"
)

# Complete epic → maintenance task auto-created
state_manager.complete_epic(epic_id)

# Result: Task created with:
# - Title: "Documentation: Update docs for Epic #1"
# - Context: Full epic details, changes, stale docs
# - Prompt: Detailed instructions with references
```

**Enable Periodic Checks**:

```python
# In orchestrator initialization
doc_mgr = DocumentationManager(state_manager, config)
doc_mgr.start_periodic_checks(project_id=1)
# Checks run every 7 days, auto-reschedules
```

#### Benefits

1. **Automated Reminders**: No more forgotten documentation updates
2. **Event-Driven**: Documentation tasks created at natural project milestones
3. **Freshness Monitoring**: Periodic checks detect drift between milestones
4. **Configurable**: Enable/disable features, customize thresholds
5. **Self-Maintaining**: Obra maintains its own documentation using this system

#### References

- **ADR-015**: `docs/decisions/ADR-015-project-infrastructure-maintenance-system.md`
- **User Guide**: `docs/guides/PROJECT_INFRASTRUCTURE_GUIDE.md`
- **Implementation Plan**: `docs/development/PROJECT_INFRASTRUCTURE_IMPLEMENTATION_PLAN.yaml`

---

## Future Architecture Enhancements

**v1.5** (Next):
- Budget & Cost Controls (P0)
- Metrics & Reporting System (P0)
- Checkpoint System (P0)
- Prompt Template Library (P0)
- Escalation Levels (P0)
- Cron-Style Periodic Scheduling (enhancement to v1.4)
- NL Command Multi-language Support (Spanish, French, German)
- Voice Input (speech-to-text → NL processing)

**v1.5+**:
- Web UI dashboard
- Real-time WebSocket updates
- Multi-project orchestration
- Pattern learning from successful tasks
- NL Multi-action Commands ("Create epic X and add 5 stories to it")

**v2.0**:
- Distributed architecture
- Advanced ML-based pattern learning
- Multi-agent collaboration
- Claude-Driven Parallelization

---

**Architecture Decisions**: See `docs/decisions/ADR-*.md` for detailed rationale behind key design choices (14 ADRs total).
