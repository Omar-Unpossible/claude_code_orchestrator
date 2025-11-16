# Obra Product Overview

**Version**: 1.8.0
**Last Updated**: November 15, 2025
**Status**: Production-Ready

---

## 🆕 What's New in v1.8.0

**Latest Release Highlights** (November 2025):

- ✨ **Production Monitoring**: Structured JSON logging with quality metrics, privacy redaction, and session tracking
- ⚡ **12.6x Faster NL Queries**: Fast path matcher + query cache reduce latency from 6.3s to <500ms
- 🎯 **Confidence Calibration**: Context-aware thresholds adapt to operation type and input quality
- 🔒 **Privacy Protection**: Automatic PII and secret redaction in all logs
- 🐛 **Bug Fixes**: Critical NL intent classification bug resolved (stop sequences truncating JSON)

**Performance Validated**: All improvements verified through A/B testing with statistical significance (p < 0.001).

**See**: [Version History](#version-history-highlights) for complete changelog.

---

## Executive Summary

### What is Obra?

Obra (Claude Code Orchestrator) is an **AI orchestration platform for autonomous software development**, combining local LLM reasoning with remote code generation through intelligent multi-stage validation.

### Core Value Proposition

While tools like Claude Code excel at code generation, they lack systematic oversight and quality control. Obra solves this by introducing a **hybrid local-remote architecture** where:

- A **local LLM** (Qwen 2.5 Coder on GPU or OpenAI Codex via API) provides fast validation, quality scoring, and decision-making (~75% of operations)
- A **remote AI** (Claude Code CLI) handles high-quality code generation in isolated environments (~25% of operations)
- An **orchestration engine** coordinates both through a multi-stage validation pipeline with quality-based iterative improvement

**The Result**: Autonomous development workflows that combine the speed of local inference with the quality of state-of-the-art code generation, validated through systematic checks and human-in-the-loop controls.

### Primary Use Cases

1. **Complex Feature Development**: Break down epics into stories and tasks, execute with automatic quality validation and retry logic
2. **Code Quality Assurance**: Multi-stage validation pipeline ensures generated code meets requirements before proceeding
3. **Team Development Workflows**: Agile/Scrum work hierarchy (Epics → Stories → Tasks) with automatic documentation maintenance
4. **Interactive Development**: Real-time command injection and natural language interface for conversational coding
5. **Production Deployments**: Structured monitoring, Git integration, task dependencies, and configuration profiles for different project types

### Current Maturity

- **Version**: 1.8.0 (Production-Ready)
- **Test Coverage**: 88% overall (830+ tests across 74 test files)
- **Critical Modules**: 96-99% coverage (DecisionEngine, QualityController, ContextManager)
- **Real-World Validation**: 19 critical bugs fixed through actual orchestration testing
- **Performance**: 35% token efficiency improvement, 23% faster responses (validated via A/B testing, p < 0.001)

Obra is production-ready for individual developers and small teams, with a clear roadmap for enterprise features based on user demand.

---

## Key Features & Capabilities

### Core Orchestration Capabilities

#### **Multi-Stage Validation Pipeline**
✅ **Production**

Automated quality control through systematic validation sequence:

- **Format Validation** (ResponseValidator): Check completeness before expensive quality checks
- **Quality Control** (QualityController): LLM-based correctness verification against requirements
- **Confidence Scoring** (ConfidenceScorer): Heuristic + LLM ensemble rating (0.0-1.0)
- **Decision Engine**: Automatic proceed/retry/clarify/escalate based on confidence thresholds

**User Benefit**: Eliminates manual code review for common issues, catches problems early, provides consistent quality regardless of task complexity.

**Key Implementation**: Validation order matters—fast checks before expensive ones. Different failure modes (incomplete → retry, low quality → review, low confidence → breakpoint).

---

#### **Quality-Based Iterative Improvement**
✅ **Production**

Automatic retry with refined prompts when output doesn't meet quality thresholds:

- Configurable quality threshold (default: 0.75)
- Maximum 3 iterations per task (configurable)
- Context from previous attempts included in retry prompts
- Exponential backoff with jitter (1s → 2s → 4s → 8s → 16s)

**User Benefit**: Solves the "good enough" problem—Obra automatically refines outputs until they meet standards, not just on first attempt.

**Example**: CSV tool implementation completed in 2 iterations (initial: 0.65 quality → added missing tests: 0.80 quality → complete).

---

#### **Hybrid Prompt Engineering (LLM-First)**
✅ **Production** | **Validated Performance**

Optimized prompt format combining JSON metadata with natural language:

- **35.2% token efficiency** improvement (p < 0.001, statistically significant)
- **22.6% faster response times** (p < 0.001, statistically significant)
- **100% parsing success rate** (vs 87% baseline)
- Maintained quality scores (no degradation)

**User Benefit**: Same quality output, significantly faster and cheaper. Validated through empirical A/B testing, not guesswork.

**Key Components**: StructuredPromptBuilder, StructuredResponseParser, PromptRuleEngine, ABTestingFramework.

---

#### **Task Dependency System**
✅ **Production**

Complex workflow orchestration with dependency management:

- Define dependencies: "Task B depends on Task A, C"
- Topological sort for optimal execution order
- Cycle detection prevents circular dependencies
- Automatic blocking until dependencies complete
- Cascading failure handling

**User Benefit**: Execute complex features in correct order automatically. No manual task sequencing.

**Example**: "Implement API endpoint" blocks until "Design data model" completes.

---

#### **Git Auto-Integration**
✅ **Production**

Version control with semantic commit messages:

- Auto-commit after successful task completion
- LLM-generated semantic commit messages (via local LLM)
- Branch per task: `obra/task-{id}-{slug}`
- Optional PR creation via `gh` CLI
- Configurable commit strategy (per-task, per-milestone, manual)

**User Benefit**: Perfect audit trail without manual commits. Every task execution tracked in version control.

---

### Natural Language Interface

#### **Unified NL Command Interface (v1.7.0)**
✅ **Production**

Conversational interaction with automatic intent detection and unified execution:

- **95%+ intent accuracy** (COMMAND vs QUESTION classification)
- **90%+ entity extraction accuracy** (schema-aware Obra entity parsing)
- **All NL commands route through orchestrator** for consistent quality validation
- **5-stage parsing pipeline**: Operation → Entity Type → Identifier → Parameters → Validation
- **<3s end-to-end latency** (P95)

**User Benefit**: Talk to Obra naturally instead of memorizing command syntax. "Create an epic for user authentication" just works.

**Key Examples**:
```
> Create an epic for user authentication
✅ Created Epic #5: User Authentication

> Add 3 stories to it: login, signup, and MFA
✅ Created 3 stories under Epic #5

> Mark the tetris project as INACTIVE
✅ Updated Project #1 status → INACTIVE
```

**Key Implementation** (ADR-016, ADR-017): Decomposed single EntityExtractor into 5 specialized components (OperationClassifier, EntityTypeClassifier, EntityIdentifierExtractor, ParameterExtractor, QuestionHandler). All commands validated through orchestrator for consistent quality.

---

#### **Question Handling**
✅ **Production**

Context-aware informational responses:

- **NEXT_STEPS**: "What's next for project 1?" → Actionable task list
- **STATUS**: "How's the auth epic going?" → Progress metrics and completion %
- **BLOCKERS**: "What's blocking development?" → Identifies blockers with recommendations
- **PROGRESS**: "Show progress for epic 2" → Velocity and estimated completion
- **GENERAL**: "How do I create an epic?" → Usage instructions

**User Benefit**: Natural conversation about project state, not just command execution.

---

#### **Hierarchical Query Support**
✅ **Production**

Advanced query capabilities:

- **WORKPLAN**: "List the workplans" → Epic → Story → Task hierarchy
- **NEXT_STEPS**: "What's next?" → Pending tasks prioritized
- **BACKLOG**: "Show backlog" → All pending work
- **ROADMAP**: "Display roadmap" → Milestones and epics

**User Benefit**: See the big picture, not just individual tasks. Understand project structure at a glance.

---

#### **NL Performance Optimization (v1.7.4)**
✅ **Production** | **12.6x Speedup Validated**

Dramatic performance improvements for natural language queries:

**Fast Path Matcher**:
- Regex-based pattern matching bypasses LLM for ~50% of common queries
- **126x speedup** for matched queries (6.3s → 50ms)
- Covers 12 patterns: list/show/get for projects, tasks, epics, stories, milestones
- ID extraction support (e.g., "get epic 5" → identifier=5)

**Query Response Cache**:
- LRU cache with TTL for QUERY operations only
- **630x speedup** for cache hits (6.3s → 10ms)
- MD5-based cache keys with input normalization
- Configurable TTL (default: 60s) and max entries (default: 1000)

**LLM Optimizations**:
- Keep-alive enabled (`keep_alive: -1`) eliminates cold starts
- Prompt reduction: 200+ tokens → 45 tokens (1.5x faster)
- Token limits: 500→100 max_tokens (2x faster generation)
- Stop sequences for early termination

**Combined Result**: 6.3s → <500ms average latency (12.6x improvement)

**User Benefit**: Near-instant responses for common queries. Reduced LLM load by >50%. Same accuracy, dramatically faster.

**Configuration**:
```yaml
nl_commands:
  query_cache:
    ttl_seconds: 60
    max_entries: 1000
```

**See**: 92 new tests (100% coverage), `src/nl/fast_path_matcher.py`, `src/nl/query_cache.py`

---

#### **Confidence Calibration System (v1.8.0)**
✅ **Production**

Context-aware confidence threshold adjustments:

**Operation-Specific Thresholds**:
- CREATE operations: 0.55 threshold (based on empirical 0.57 mean, 100% accuracy)
- QUERY operations: 0.58 threshold
- UPDATE/DELETE operations: 0.60 threshold (higher bar for destructive ops)

**Context-Aware Adjustments**:
- Typos detected: -0.05 confidence adjustment
- Casual language: -0.03 confidence adjustment
- Formal commands: +0.02 confidence boost

**User Benefit**: Fewer false negatives (commands incorrectly rejected). Adaptive to user input style. 15-20% improvement in variation test pass rate.

**Key Implementation**: Empirically calibrated based on Phase 3 real LLM data. 20/20 tests passing.

**See**: `src/nl/confidence_calibrator.py` (229 lines)

---

### Work Management (Agile Hierarchy)

#### **Industry-Standard Work Breakdown (v1.3.0)**
✅ **Production**

Agile/Scrum terminology for organizing development at scale:

**Hierarchy**:
```
Product (Project)
  ↓
Epic (Large feature, 3-15 sessions)
  ↓
Story (User deliverable, 1 session)
  ↓
Task (Technical work - default)
  ↓
Subtask (via parent_task_id)

Milestone → Checkpoint (zero-duration, when epics complete)
```

**User Benefit**: Familiar terminology for teams. Scales from single tasks to multi-month projects.

**Key Methods**: `create_epic()`, `execute_epic()`, `create_milestone()`, `achieve_milestone()`

**Example Workflow**:
```python
# Create epic (large feature)
epic_id = state.create_epic(
    project_id=1,
    title="User Authentication System",
    description="Complete auth with OAuth, MFA, session management"
)

# Create stories (user deliverables)
story1 = state.create_story(1, epic_id, "Email/password login")
story2 = state.create_story(1, epic_id, "OAuth integration")

# Execute entire epic (runs all stories sequentially)
orchestrator.execute_epic(project_id=1, epic_id=epic_id)
```

---

#### **Project Infrastructure Maintenance (v1.4.0)**
✅ **Production**

Automatic documentation maintenance through event-driven triggers:

- **Event Hooks**: Epic completion, milestone achievement trigger maintenance tasks
- **Periodic Checks**: Threading-based scheduler (default: 7 days)
- **Freshness Tracking**: 30/60/90 day thresholds for critical/important/normal docs
- **Automatic Updates**: CHANGELOG, ADR creation suggestions, implementation plan archiving

**User Benefit**: Documentation stays current without manual intervention. Obra "eats its own dog food" maintaining its own docs.

**Configuration**:
```yaml
documentation:
  enabled: true
  triggers:
    epic_complete: {enabled: true, scope: comprehensive}
    milestone_achieved: {enabled: true, scope: full_review}
    periodic: {enabled: true, interval_days: 7}
```

---

### Developer Experience Features

#### **Interactive Orchestration (v1.5.0)**
✅ **Production**

Real-time command injection and human-in-the-loop control:

**8 Interactive Commands**:
- **Natural text (no slash)** - Send message to orchestrator (DEFAULT)
- `/help` - Show help message
- `/status` - Current task status, iteration, quality score
- `/pause` / `/resume` - Pause/resume execution
- `/stop` - Stop execution gracefully
- `/to-impl <message>` - Send message to implementer (Claude Code)
- `/override-decision <choice>` - Override orchestrator's decision

**6 Interactive Checkpoints**:
1. Before agent execution
2. After agent response
3. Before validation
4. After validation (if low confidence)
5. Before decision execution
6. On error/exception

**User Benefit**: Intervene at strategic points without stopping entire workflow. Guide execution in real-time.

**Key UX Improvement** (v1.5.0): Natural language defaults to orchestrator. All system commands require `/` prefix. Eliminates friction for primary use case.

---

#### **Configuration Profiles**
✅ **Production**

Pre-configured settings for different project types:

**6 Built-in Profiles**:
- `python_project` - Python development with pytest
- `web_app` - Web application (Node.js, React)
- `ml_project` - Machine learning/data science
- `microservice` - Microservice architecture
- `minimal` - Minimal overhead
- `production` - Production-ready, high quality

**User Benefit**: Get started in minutes, not hours. Sensible defaults for common project types.

**Usage**:
```bash
obra project create "My Python App" --profile python_project
```

---

#### **Production Monitoring (v1.8.0)**
✅ **Production**

Structured JSON logging for observability:

- **JSON Lines Format**: Machine-parsable, grep-friendly logs
- **I/O Boundaries**: User input → NL processing → execution → result
- **Quality Metrics**: Confidence scores, validation status, performance timing
- **Privacy Protection**: Automatic PII/secret redaction
- **Session Tracking**: Multi-turn conversation continuity via UUID

**Key Events**: `user_input`, `nl_result`, `execution_result`, `error`

**User Benefit**: Real-time quality monitoring. Debug issues with complete context. Track metrics over time.

**Log Analysis Example**:
```bash
# View quality metrics
cat ~/obra-runtime/logs/production.jsonl | jq 'select(.type == "nl_result") | {confidence, validation, duration_ms}'

# Track specific session
cat ~/obra-runtime/logs/production.jsonl | jq 'select(.session == "SESSION_ID")'
```

---

#### **Flexible LLM Orchestrator**
✅ **Production**

Support for multiple LLM providers:

**Two Deployment Options**:
1. **Local GPU**: Ollama + Qwen 2.5 Coder on RTX 5090 (zero API costs, complete privacy)
2. **Remote CLI**: OpenAI Codex via subprocess (no GPU required, subscription-based)

**Plugin System**:
```python
@register_llm('ollama')
class LocalLLMInterface(LLMPlugin): ...

@register_llm('openai-codex')
class OpenAICodexLLMPlugin(LLMPlugin): ...
```

**User Benefit**: Choose deployment based on hardware availability and cost preferences. Switch providers via config, no code changes.

---

#### **Retry Logic with Exponential Backoff**
✅ **Production**

Graceful handling of transient failures:

- Exponential backoff: 1s → 2s → 4s → 8s → 16s (configurable)
- Jitter prevents thundering herd
- Retryable vs non-retryable error classification
- Detailed retry logging

**User Benefit**: Resilient to network issues, rate limits, timeouts. Don't lose work due to transient failures.

---

## Architecture Overview

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ HOST MACHINE (Windows 11 Pro)                               │
│  Ollama + Qwen (RTX 5090, GPU) ← HTTP API                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Hyper-V VM → WSL2                                     │  │
│  │   Obra ─┬─→ subprocess → Claude Code (Local)         │  │
│  │         └─→ HTTP API → Ollama (Validation)           │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

**Dual Deployment Model**:
- **Option A (Local LLM)**: Requires GPU hardware, zero API costs, complete privacy
- **Option B (Remote LLM)**: No GPU required, subscription-based, lower hardware requirements

---

### Component Inventory

#### **M0: Plugin System** (Architecture Foundation)
**Purpose**: Extensibility through pluggable agents and LLM providers

**Key Classes**:
- `AgentPlugin` (ABC): Interface for code execution agents
- `LLMPlugin` (ABC): Interface for LLM providers
- `AgentRegistry`, `LLMRegistry`: Decorator-based registration

**Design Pattern**: Abstract Factory + Registry

**Why It Matters**: Swap agents/LLMs via config. Easy testing with mocks. Community contributions. Multiple deployment models.

---

#### **M1: Core Infrastructure** (State Management)
**Purpose**: Single source of truth for all state operations

**Key Classes**:
- `StateManager`: Centralized state access (singleton, thread-safe)
- SQLAlchemy Models: Project, Task, Epic, Story, Milestone, Interaction
- `Config`: YAML configuration with profile support
- Exception hierarchy: `ObraException` with context

**Critical Rule**: ALL state access goes through StateManager. NO direct database access.

**Why It Matters**: Prevents inconsistencies. Enables atomic transactions. Supports rollback. Thread-safe.

---

#### **M2: LLM & Agent Interfaces** (Communication)
**Purpose**: Communication with local LLM and remote agents

**Key Classes**:
- `LocalLLMInterface`: Ollama/llama.cpp integration
- `OpenAICodexLLMPlugin`: Remote CLI-based LLM
- `PromptGenerator`: Creates optimized prompts with context
- `ResponseValidator`: Validates response completeness
- `ClaudeCodeLocalAgent`: Claude Code CLI as subprocess (recommended)
- `OutputMonitor`: Streams and parses agent output

**Why It Matters**: Separates local (validation) and remote (execution) operations. Pluggable architecture for different LLMs.

---

#### **M3: File Monitoring** (Change Tracking)
**Purpose**: Track all file changes for rollback capability

**Key Classes**:
- `FileWatcher`: Watchdog-based filesystem monitoring
- Event batching with debouncing
- Change tracking in database

**Why It Matters**: Enables rollback. Audit trail for all code changes. Detect unintended modifications.

---

#### **M4: Orchestration Engine** (Decision Making)
**Purpose**: Task scheduling, decision making, quality control

**Key Classes**:
- `TaskScheduler`: Priority-based task selection with dependency resolution
- `DecisionEngine`: Next-action decisions (PROCEED/ESCALATE/CLARIFY/RETRY)
- `QualityController`: Multi-stage validation (96-99% test coverage)
- `BreakpointManager`: Human intervention points

**Why It Matters**: Automated decision-making with human oversight. Systematic quality control. Intelligent task ordering.

---

#### **M5: Utility Services** (Cross-Cutting Concerns)
**Purpose**: Token counting, context management, confidence scoring

**Key Classes**:
- `TokenCounter`: Accurate token counting with model-specific encoders
- `ContextManager`: Priority-based context building (92% test coverage)
- `ConfidenceScorer`: Multi-factor confidence assessment

**Why It Matters**: Efficient context management. Prevents token limit issues. Calibrated confidence scores.

---

#### **M6: Integration & CLI** (User Interfaces)
**Purpose**: User-facing interfaces

**Key Components**:
- `Orchestrator`: Main integration loop coordinating M0-M5
- `cli.py`: Click-based CLI commands
- `interactive.py`: REPL interface with real-time input

**8-Step Execution Loop**: Build context → Generate prompt → Execute → Validate → Quality check → Score confidence → Decide → Handle action

---

#### **M9: Core Enhancements** (Production Features)
**Purpose**: Reliability, workflow management, usability

**Key Components**:
- `RetryManager`: Exponential backoff (91% test coverage)
- `DependencyResolver`: Topological sort (97% test coverage)
- `GitManager`: Semantic commits (95% test coverage)
- Configuration profiles: 6 pre-configured project types

---

### Data Flow (High-Level Request → Response)

```
User initiates task
    ↓
Orchestrator gets task from StateManager
    ↓
ContextManager builds context from history
    ↓
StructuredPromptBuilder creates optimized hybrid prompt
    ↓
[Interactive Checkpoint 1: Before agent execution]
    ↓
Agent (via plugin) executes task in fresh session
    ↓
[Interactive Checkpoint 2: After agent response]
    ↓
FileWatcher detects changes
    ↓
[Interactive Checkpoint 3: Before validation]
    ↓
ResponseValidator checks format/completeness
    ↓
QualityController validates correctness
    ↓
ConfidenceScorer rates confidence (heuristic + LLM ensemble)
    ↓
[Interactive Checkpoint 4: After validation (if low confidence)]
    ↓
DecisionEngine decides next action (proceed/retry/clarify/escalate)
    ↓
[Interactive Checkpoint 5: Before decision execution]
    ↓
StateManager persists everything (atomic transaction)
    ↓
GitManager commits changes (if enabled)
    ↓
Loop continues or breakpoint triggered
    ↓
[Interactive Checkpoint 6: On error/exception]
```

---

### Key Design Decisions (ADRs)

#### **ADR-001: Plugin Architecture**
**Decision**: Plugin system from the start, not monolithic design
**Rationale**: Extensibility, testability, community contributions
**Impact**: Swap agents/LLMs via config. Easy testing with mocks.

#### **ADR-006: LLM-First Prompt Engineering**
**Decision**: Hybrid prompt format (JSON metadata + natural language)
**Rationale**: Validated 35% token efficiency, 23% faster, 100% parse success
**Impact**: Same quality, significantly faster and cheaper.

#### **ADR-013: Agile Work Hierarchy**
**Decision**: Industry-standard terminology (Epic/Story/Task/Subtask)
**Rationale**: Familiar for teams, scales from single tasks to multi-month projects
**Impact**: Professional workflow management, not custom terminology.

#### **ADR-014: Natural Language Command Interface**
**Decision**: LLM-based conversational interaction
**Rationale**: Lower barrier to entry, intuitive for non-technical stakeholders
**Impact**: 95%+ intent accuracy, <3s latency, no command memorization.

#### **ADR-016: Decompose NL Entity Extraction**
**Decision**: 5-stage pipeline (Operation → EntityType → Identifier → Parameters → Validation)
**Rationale**: Single-responsibility components, higher accuracy (95%+ vs 80% baseline)
**Impact**: Fixed 3 critical bugs (ISSUE-001, ISSUE-002, ISSUE-003).

#### **ADR-017: Unified Execution Architecture**
**Decision**: All commands (NL and CLI) route through orchestrator
**Rationale**: Consistent quality validation, single execution model
**Impact**: NL commands get retry logic, quality scoring, breakpoints. ~40% test reduction.

---

### Performance Metrics

**Validated Improvements** (all statistically significant, p < 0.001):

| Metric | Baseline | With Obra | Improvement | Validation Method |
|--------|----------|-----------|-------------|-------------------|
| **Token Efficiency** | 100% | 65% | **35% reduction** | A/B testing (PHASE_6) |
| **Response Time** | 10s | 7.7s | **23% faster** | A/B testing (PHASE_6) |
| **Parse Success Rate** | 87% | 100% | **+13 points** | Schema validation |
| **NL Query Latency (avg)** | 6.3s | <500ms | **12.6x faster** | Performance benchmarks (v1.7.4) |
| **NL Query (fast path)** | 6.3s | 50ms | **126x faster** | Regex matching bypass |
| **NL Query (cache hit)** | 6.3s | 10ms | **630x faster** | LRU cache with TTL |
| **Test Coverage** | - | 88% | 830+ tests | Pytest with coverage.py |
| **Critical Module Coverage** | - | 96-99% | DecisionEngine, QualityController | Unit + integration tests |

**Quality Assurance Philosophy**:
- **Real-world validation**: 19 critical bugs found through actual orchestration testing
- **Empirical testing**: All performance claims validated via A/B testing, not assumptions
- **Continuous integration**: All PRs must pass 830+ test suite before merge
- **Coverage targets**: ≥85% overall, ≥90% critical modules (both exceeded)

---

### Technology Stack

**Core**:
- Python 3.10+
- SQLAlchemy 2.0+ (ORM)
- Click 8.0+ (CLI framework)
- PyYAML 6.0+ (configuration)

**LLM Integration**:
- Ollama (local LLM runtime)
- OpenAI Codex CLI (remote LLM)
- Tiktoken (token counting)

**Agent Integration**:
- Claude Code CLI (via subprocess)
- Paramiko (SSH agent support)

**Monitoring & UX**:
- Watchdog (file monitoring)
- prompt_toolkit (interactive input)
- Colorama (terminal colors)

**Deployment**:
- Docker + Docker Compose
- SQLite (development) or PostgreSQL (production)

---

## Security & Privacy

### Data Privacy

**Complete Privacy with Local LLM**:
- **No data sent to third parties** when using Ollama/Qwen deployment
- All code validation happens on your GPU
- Task history stored locally (SQLite/PostgreSQL)
- Full control over data residency

**Privacy Protection in Production Monitoring** (v1.8.0):
- **Automatic PII redaction**: Email addresses, IP addresses, phone numbers, SSNs
- **Secret redaction**: API keys, tokens, passwords
- **UUID-safe patterns**: Session IDs preserved for tracking
- **Configurable**: Enable/disable redaction per data type

### Agent Isolation

**Sandboxed Execution**:
- Claude Code runs in isolated environment (VM/container/subprocess)
- No direct filesystem access from orchestrator to agent workspace
- SSH key-based authentication only (no passwords)
- Configurable timeout limits prevent runaway processes

### Authentication & Access Control

**Secure Communication**:
- SSH keys stored securely in `~/.ssh/` (not in repository)
- Config file sanitization for logging (secrets removed)
- No credentials stored in database
- Environment variable support for sensitive configuration

### Input Validation

**Injection Prevention**:
- All user inputs validated before processing
- SQL injection prevented via SQLAlchemy ORM (no raw SQL)
- Command injection prevented in SSH layer
- Natural language sanitized before LLM processing

### Audit Trail

**Complete Traceability**:
- Every task execution logged with timestamp, user, input, output
- Git integration provides version control audit trail
- Production logs track all I/O boundaries (optional)
- File watcher records all code changes for rollback

**Security Best Practices**:
- ✅ Keep Python dependencies updated (`pip install -U -r requirements.txt`)
- ✅ Use SSH keys, not passwords
- ✅ Run Obra in isolated environment (Docker/VM recommended for production)
- ✅ Review generated code before deployment (always)
- ✅ Enable production monitoring for security incident detection

---

## Getting Started Path

### Prerequisites

**System Requirements**:

**Minimum**:
- **OS**: Ubuntu 20.04+, Windows 11 (WSL2), macOS 12+
- **Python**: 3.10 or higher
- **RAM**: 4GB available
- **Disk**: 10GB free space (database, logs, workspace)
- **Network**: Internet connection for remote LLM (if not using local GPU)

**Recommended**:
- **OS**: Ubuntu 22.04 LTS or Windows 11 Pro with Hyper-V + WSL2
- **Python**: 3.11+
- **RAM**: 8GB+ available (16GB for concurrent orchestration)
- **Disk**: 50GB+ SSD (faster database operations)
- **GPU**: NVIDIA RTX 5090 with 32GB VRAM (for local LLM deployment)
- **Network**: 100 Mbps+ for remote LLM API calls

**Required Software**:
- Python 3.10+ with pip
- Git 2.30+
- SQLite 3.35+ (included with Python) OR PostgreSQL 13+
- Claude Code CLI (latest version)

**Optional for Local LLM**:
- NVIDIA GPU with 24GB+ VRAM
- Ollama 0.1.0+ (for local LLM runtime)
- CUDA 11.8+ (for GPU acceleration)

**Optional for Deployment**:
- Docker 20.10+ and Docker Compose 2.0+ (containerized deployment)
- GitHub CLI (`gh`) 2.0+ (for automatic PR creation)

---

### Quickstart (5 Steps to "Hello World")

#### **Step 1: Clone and Install**
```bash
git clone https://github.com/Omar-Unpossible/claude_code_orchestrator.git
cd claude_code_orchestrator
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### **Step 2: Initialize**
```bash
python -m src.cli init
```

#### **Step 3: Configure LLM**
Edit `config/config.yaml`:
```yaml
llm:
  type: ollama  # or openai-codex
  model: qwen2.5-coder:32b
  api_url: http://localhost:11434
```

#### **Step 4: Create First Project**
```bash
python -m src.cli project create "Hello World Demo" --profile python_project
```

#### **Step 5: Execute First Task**
```bash
# Interactive mode (recommended)
python -m src.cli interactive

# Or CLI mode
python -m src.cli task create "Write a hello world function" --project 1
python -m src.cli task execute 1
```

**Result**: Task executed with automatic validation, quality scoring, and Git integration.

---

### Quick Wins - Before/After Comparison

**Scenario: Implementing a user authentication feature**

#### **Without Obra** (Manual Workflow)

```bash
# 1. Generate code manually with Claude Code
claude "Implement login endpoint with JWT authentication"

# 2. Review output manually
# - Check for completeness
# - Verify requirements met
# - Look for security issues
# - Test manually

# 3. If issues found, retry manually
claude "Fix the JWT token expiration issue"

# 4. Repeat validation
# - Re-review
# - Re-test
# - Re-verify

# 5. Commit manually
git add src/auth/
git commit -m "Add login endpoint"  # Write message yourself
git push

# Total time: 30-45 minutes
# Quality: Depends on your review thoroughness
# Retry logic: Manual, requires your judgment
```

#### **With Obra** (Automated Workflow)

```bash
# 1. Create and execute task
obra task create "Implement login endpoint with JWT authentication" --project 1
obra task execute 1

# Obra automatically:
# ✅ Validates response completeness (ResponseValidator)
# ✅ Checks quality against requirements (QualityController)
# ✅ Scores confidence (ConfidenceScorer: 0.82)
# ✅ Retries if quality < threshold (up to 3 iterations)
# ✅ Generates semantic commit message (via local LLM)
# ✅ Commits to Git with metadata (task ID, scores)
# ✅ Logs all interactions for audit

# Total time: 5-10 minutes (hands-off)
# Quality: Systematic validation, consistent
# Retry logic: Automatic, quality-based
```

**What You Gain**:
- ⚡ **3-5x faster** for complex tasks (automation eliminates manual review loops)
- ✅ **Consistent quality** (no "forgot to check X" mistakes)
- 📊 **Automatic metrics** (confidence scores, quality ratings)
- 🔄 **Built-in retry logic** (quality-based, not manual judgment)
- 📝 **Perfect audit trail** (every decision logged with reasoning)
- 🎯 **Semantic Git history** (LLM-generated commit messages with context)

---

#### **Natural Language Example**

**Without Obra**:
```bash
# Memorize exact CLI syntax
obra task create "Fix login bug" --project 1 --priority 8 --depends-on 5,6

# Easy to get wrong:
# - Forgot --project flag
# - Wrong priority syntax
# - Typo in --depends-on
```

**With Obra**:
```bash
# Just talk naturally
> Create a high priority task to fix the login bug, depends on tasks 5 and 6

✅ Created Task #10: "Fix login bug"
   Priority: 8 (HIGH), Depends on: [5, 6]
   Next: Execute with 'obra task execute 10' or continue with NL
```

**What You Gain**:
- 🗣️ **No syntax memorization** (95%+ intent accuracy)
- ⚡ **Faster input** (natural phrasing vs precise syntax)
- 🔍 **Forgiving** (typos, casual language handled)
- 📚 **Lower learning curve** (productive in first session)

---

### Key Configuration Points

#### **LLM Provider Selection**
```yaml
# Option 1: Local GPU (Ollama)
llm:
  type: ollama
  model: qwen2.5-coder:32b
  api_url: http://localhost:11434

# Option 2: Remote CLI (OpenAI Codex)
llm:
  type: openai-codex
  model: gpt-5-codex
  timeout: 120
```

#### **Agent Configuration**
```yaml
agent:
  type: claude_code_local  # or claude_code_ssh
  config:
    timeout: 300
    max_turns: 20
```

#### **Quality Thresholds**
```yaml
orchestration:
  decision:
    high_confidence: 0.85
    medium_confidence: 0.65
  quality:
    min_quality_score: 0.75
  breakpoints:
    confidence_threshold: 0.7
```

---

### First Meaningful Task Example

```bash
# Start interactive mode
python -m src.cli interactive

# Natural language workflow
> Create an epic for user authentication
✅ Created Epic #1: User Authentication

> Add 3 stories: login, signup, password reset
✅ Created 3 stories under Epic #1: #1, #2, #3

> Show me the workplan
Epic #1: User Authentication
  Story #1: Login
    └─ No tasks yet
  Story #2: Signup
    └─ No tasks yet
  Story #3: Password Reset
    └─ No tasks yet

> Create a task for story 1: Implement login form with email/password
✅ Created Task #1 under Story #1

> Execute task 1
[Orchestrator runs 8-step validation pipeline]
✅ Task completed successfully!
Quality: 0.82 | Confidence: 0.88 | Iterations: 1
```

---

## Comparison & Positioning

### vs. Direct Claude Code Usage

| Aspect | Claude Code Alone | Obra + Claude Code |
|--------|-------------------|-------------------|
| Code Generation | ✅ Excellent | ✅ Excellent (same engine) |
| Quality Validation | ❌ Manual | ✅ Automated multi-stage |
| Iterative Improvement | ❌ Manual retry | ✅ Automatic retry with feedback |
| Task Management | ❌ None | ✅ Epic/Story/Task hierarchy |
| Git Integration | ❌ Manual | ✅ Automatic semantic commits |
| Natural Language | ✅ Good | ✅ Excellent (95%+ accuracy) |
| Dependency Management | ❌ None | ✅ Topological sort with cycles |
| Monitoring | ❌ None | ✅ Structured JSON logs |

**When to use Claude Code alone**: Quick one-off tasks, exploration, prototyping.

**When to use Obra**: Complex features, team workflows, production deployments, quality-critical applications.

---

### vs. Other Orchestration Tools

#### **vs. Langchain**
- **Langchain**: General-purpose LLM framework, flexible but requires manual orchestration
- **Obra**: Purpose-built for code generation with systematic quality validation

**Obra Advantage**: Multi-stage validation, quality-based retry, built-in confidence scoring.
**Langchain Advantage**: Broader use cases (RAG, agents, chains).

#### **vs. AutoGPT**
- **AutoGPT**: Autonomous agent with self-prompting loops
- **Obra**: Hybrid local-remote with human-in-the-loop controls

**Obra Advantage**: Predictable workflows, systematic validation, lower token costs (75% local).
**AutoGPT Advantage**: More autonomous exploration.

#### **vs. Aider**
- **Aider**: Interactive coding assistant with Git integration
- **Obra**: Orchestration platform with multi-LLM validation

**Obra Advantage**: Separate validation LLM, quality-based retry, work hierarchy (epics/stories).
**Aider Advantage**: Simpler setup, direct interaction.

---

### Ideal User Profile

**Primary User**: Individual developers and small teams building production software

**Characteristics**:
- Values **code quality** over speed
- Works on **complex features** requiring multiple tasks
- Prefers **systematic validation** over manual review
- Familiar with **Agile/Scrum** workflows (or willing to learn)
- Has access to **GPU hardware** (local deployment) OR **API budget** (remote deployment)

**Not Ideal For**:
- Quick prototyping (use Claude Code directly)
- Non-coding tasks (use general LLM tools)
- Large teams requiring distributed orchestration (v2.0 feature)

---

## Frequently Asked Questions (FAQ)

### General Questions

**Q: How is Obra different from just using Claude Code directly?**

A: Obra adds systematic quality validation, iterative improvement, and work management on top of Claude Code. Think of Claude Code as the execution engine, and Obra as the intelligent supervisor that ensures quality, tracks progress, and manages complex workflows. Key additions: multi-stage validation pipeline, quality-based retry logic, natural language interface, Agile work hierarchy, Git integration, and production monitoring.

**Q: What happens if my LLM goes down?**

A: Obra has graceful fallback. If your local LLM (Ollama/Qwen) goes offline, Obra will load but prompt you to reconnect before executing tasks. You can switch LLMs on-the-fly using `obra llm reconnect --type openai-codex` or configure environment variables. For production deployments, we recommend using the remote LLM option (OpenAI Codex) for higher availability, or running Ollama with automatic restart policies in Docker.

**Q: Can I use Obra with GitHub Copilot or Cursor?**

A: Obra is designed to work **alongside** Copilot/Cursor, not replace them. Use Copilot for inline suggestions while coding manually. Use Obra for automated task execution with quality validation. They complement each other: Copilot for human-driven coding, Obra for autonomous orchestration.

**Q: What's the learning curve?**

A: **10 minutes to first task** (quickstart). **1-2 hours to understand core concepts** (validation pipeline, work hierarchy). **1-2 days to master advanced features** (natural language, dependencies, profiles). The natural language interface reduces memorization—just talk to Obra naturally. Most users are productive within their first session.

**Q: Can I migrate from Aider or AutoGPT?**

A: Yes. **From Aider**: Import your Git history, create tasks from commit messages, continue with Obra's enhanced validation. **From AutoGPT**: Obra provides more structured workflows—you'll need to organize tasks into epics/stories, but gain predictability and quality control. No automated migration tool yet (v1.8.0), but manual migration takes 1-2 hours for typical projects.

### Technical Questions

**Q: Does Obra support remote teams?**

A: v1.8.0 is designed for single-user or small co-located teams (shared StateManager database). Distributed orchestration (multi-host, distributed task queue) is planned for v2.0. Current workaround: Use PostgreSQL database with network access and coordinate via Git.

**Q: How much does it cost to run Obra?**

A: **Local LLM (Ollama)**: Zero API costs, one-time GPU investment (~$2,500 for RTX 5090). **Remote LLM (OpenAI Codex)**: Subscription-based (~$20-200/month depending on usage). **Infrastructure**: Minimal (runs on development machine). Obra itself is open-source (MIT license, free).

**Q: What if I don't have a GPU?**

A: Use the remote LLM deployment option (OpenAI Codex via CLI). Requires subscription but no GPU. Performance is excellent, and you get the same validation quality. See [Flexible LLM Orchestrator](#flexible-llm-orchestrator) section.

**Q: Is my code data secure?**

A: **With local LLM**: 100% private, no data sent to third parties. **With remote LLM**: Code sent to OpenAI API (subject to their privacy policy). Production monitoring redacts all PII/secrets automatically. See [Security & Privacy](#security--privacy) section for details.

**Q: How do I handle tasks that require human decisions?**

A: Use **interactive checkpoints** (`/pause`, `/to-impl`, `/override-decision` commands) during execution. Obra pauses at 6 strategic points where you can inject guidance. Alternatively, set up **confirmation workflows** for destructive operations (UPDATE/DELETE require explicit confirmation).

### Troubleshooting Questions

**Q: Why are my quality scores consistently low?**

A: Common causes: (1) Vague task descriptions—add more detail and examples. (2) Quality threshold too high—adjust in `config.yaml` (default: 0.75). (3) LLM not configured properly—verify connection with `obra llm status`. (4) Task complexity exceeds agent capability—break into smaller subtasks.

**Q: Tasks stuck in PENDING status?**

A: Check for **dependency issues**: Use `obra task show <id>` to view dependencies. Tasks block until all dependencies complete. Look for circular dependencies (Obra detects these during creation). Check parent task status for subtasks.

**Q: "Session lock conflict" errors?**

A: This bug was **fixed in v1.0.0** (per-iteration fresh sessions). If you're seeing this, upgrade to latest version (`git pull && pip install -r requirements.txt`). Legacy workaround: Stop all Obra processes, delete `~/.claude/sessions/`, restart.

---

## Troubleshooting Guide

### Quick Diagnostics

**Problem: LLM connection errors**

```bash
# Check LLM status
obra llm status

# Reconnect to LLM
obra llm reconnect

# Test with simple prompt
python -c "from src.llm.local_interface import LocalLLMInterface; llm = LocalLLMInterface(); print(llm.generate('Hello'))"
```

**Solution**:
- Verify Ollama running: `curl http://localhost:11434/api/tags`
- Check network/firewall for remote LLM
- Confirm API keys set: `echo $OPENAI_API_KEY`
- Review logs: `tail -50 ~/obra-runtime/logs/obra.log`

---

**Problem: Natural language commands rejected**

```bash
# Enable debug logging
export OBRA_LOG_LEVEL=DEBUG

# Test with simple command
> Create a task for testing

# Check confidence scores in logs
cat ~/obra-runtime/logs/production.jsonl | jq 'select(.type == "nl_result")'
```

**Solution**:
- Use more specific language: "Create a task called 'Fix login bug' in project 1"
- Check confidence thresholds in `config/config.yaml` (may be too strict)
- Verify LLM is responding: `obra llm status`
- Review Phase 3/4 test results for patterns: See `docs/testing/`

---

**Problem: Tasks failing with timeout errors**

```bash
# Check current timeout settings
grep -A5 "agent:" config/config.yaml

# Increase timeout for complex tasks
obra task execute 1 --timeout 7200  # 2 hours
```

**Solution**:
- Increase timeout in `config.yaml`: `agent.config.timeout: 7200`
- For very long tasks, use epic/story breakdown
- Check agent health: `obra health`
- Monitor resource usage: `htop` or `nvidia-smi` (GPU)

---

**Problem: Git integration not committing**

```bash
# Check Git configuration
git config --list | grep user

# Verify Git manager enabled
grep -A10 "git:" config/config.yaml

# Test Git manually
git status
git log -1
```

**Solution**:
- Enable Git integration in `config.yaml`: `git.enabled: true`
- Configure Git user: `git config --global user.name "Your Name"`
- Check for uncommitted changes blocking auto-commit
- Review Git logs: `tail -20 ~/obra-runtime/logs/obra.log | grep -i git`

---

**Problem: High memory usage**

```bash
# Check Obra processes
ps aux | grep python | grep obra

# Monitor memory
watch -n 1 'ps aux | grep obra | awk "{print \$6}"'
```

**Solution**:
- Reduce concurrent tasks: `orchestration.scheduler.max_concurrent_tasks: 1`
- Clear old sessions: `rm -rf ~/.claude/sessions/old_*`
- Optimize database: `sqlite3 orchestrator.db "VACUUM;"`
- Use PostgreSQL for production (better memory management)

---

**Problem: Tests failing after upgrade**

```bash
# Run tests with verbose output
pytest -v -x

# Check for API changes
git diff v1.7.0 v1.8.0 -- src/

# Review migration guides
cat docs/guides/ADR017_MIGRATION_GUIDE.md
```

**Solution**:
- Review CHANGELOG for breaking changes
- Update test fixtures for new APIs (e.g., `entity_type` → `entity_types`)
- Regenerate test config: `python -m src.cli init --reset`
- Check Python version: `python --version` (requires 3.10+)

---

### Common Error Messages

| Error Message | Cause | Solution |
|---------------|-------|----------|
| `ConfigNotFoundException` | Config file not found | Run `python -m src.cli init` |
| `AgentException: Cannot connect` | Claude Code not accessible | Check SSH config or subprocess permissions |
| `StateManager: database locked` | Concurrent access issue | Use `with state_manager.transaction():` |
| `ValidationException: incomplete` | Agent response truncated | Increase `max_turns` in config |
| `BreakpointException` | Low confidence triggered | Review task, provide more context |
| `DependencyResolver: cycle detected` | Circular task dependencies | Remove circular dependency |

---

**Still Stuck?**

1. **Check Logs**: `~/obra-runtime/logs/obra.log` and `production.jsonl`
2. **Search Issues**: [GitHub Issues](https://github.com/Omar-Unpossible/claude_code_orchestrator/issues)
3. **Review Docs**: [docs/README.md](README.md) for complete documentation index
4. **File Bug Report**: Include logs, config (redacted), and minimal reproduction steps

---

## Appendices

### Glossary

**Agent**: Code execution component (e.g., Claude Code CLI). Pluggable via AgentPlugin.

**Breakpoint**: Strategic checkpoint where human can intervene during orchestration.

**Confidence Score**: 0.0-1.0 rating of execution quality (heuristic + LLM ensemble).

**DecisionEngine**: Component that decides next action (proceed/retry/clarify/escalate) based on validation results.

**Epic**: Large feature spanning multiple stories (3-15 orchestration sessions).

**Implementer**: Agent responsible for code generation (Claude Code).

**LLM**: Large Language Model (Qwen, OpenAI Codex, etc.). Pluggable via LLMPlugin.

**Milestone**: Zero-duration checkpoint when epics complete. Not a work item.

**Orchestrator**: Local LLM responsible for validation, quality scoring, prompt optimization.

**Quality Score**: 0.0-1.0 rating from QualityController checking correctness and requirements.

**StateManager**: Centralized state access layer. Single source of truth. Thread-safe.

**Story**: User-facing deliverable (1 orchestration session). Part of an epic.

**Subtask**: Granular task step. Implemented via parent_task_id hierarchy.

**Task**: Technical work implementing a story. Default work item type.

---

### Version History Highlights

**v1.8.0 (Nov 15, 2025)**: Production monitoring with structured JSON logging

**v1.7.4 (Nov 13, 2025)**: NL performance optimization - 12.6x speedup (fast path + cache)

**v1.7.0 (Nov 13, 2025)**: Unified execution architecture - all commands through orchestrator

**v1.6.0 (Nov 11, 2025)**: 5-stage NL pipeline - 95%+ accuracy

**v1.5.0 (Nov 11, 2025)**: Interactive UX improvement - natural language defaults

**v1.4.0 (Nov 11, 2025)**: Project infrastructure maintenance system

**v1.3.0 (Nov 11, 2025)**: Agile work hierarchy + NL command interface

**v1.2.0 (Nov 4, 2025)**: LLM-first prompt engineering (35% efficiency, validated)

**v1.1.0 (Nov 3, 2025)**: M9 core enhancements (retry, dependencies, git, profiles)

**v1.0.0 (Nov 2, 2025)**: Production-ready - M8 local agent + headless mode

**v0.9.0 (Nov 1, 2025)**: M7 testing & deployment (88% coverage, Docker)

**v0.2.0 (Oct 26, 2025)**: M0 plugin system (architecture foundation)

**v0.1.0 (Oct 25, 2025)**: Initial setup

---

### Product Roadmap

**Current Focus: Stability & Performance** (v1.8.x series - Q4 2025)
- ✅ Production monitoring with observability
- ✅ NL performance optimization (12.6x improvement)
- ✅ Confidence calibration system
- 🔄 Bug fixes and performance tuning based on real-world usage

**Next Major Release: Enhanced Developer Experience** (v1.9.0 - Q1 2026)
- **Security Hardening**:
  - Input sanitization for prompt injection prevention
  - Enhanced secret management integration (HashiCorp Vault, AWS Secrets Manager)
  - Security audit trail with compliance reporting
  - Git operation confirmation prompts (configurable)
- **Template System**:
  - Domain-specific prompt templates (Bug Fix, Refactoring, Frontend, API, Infrastructure)
  - Auto-detection via keywords and context
  - 40% quality improvement for specialized domains (estimated)
  - Template registry with community contributions
- **Observability Enhancements**:
  - Real-time metrics dashboard (terminal UI)
  - Correlation IDs for end-to-end tracing
  - Approval gate timestamps for audit compliance
  - Pre-commit hooks for automated quality checks

**Major Version: Multi-Agent & Enterprise** (v2.0.0 - Q2-Q3 2026)
- **Multi-Agent Orchestration**:
  - Parallel task execution with multiple Claude Code instances
  - Hierarchical delegation (agent spawns sub-agents for complex epics)
  - Standard inter-agent message format
  - Circuit breaker patterns for fault tolerance
- **Enterprise Features** (if demand validated):
  - GDPR/HIPAA/SOC2 compliance frameworks
  - Web UI dashboard for team collaboration
  - Distributed orchestration (multi-cloud support)
  - Role-based access control (RBAC)
  - Advanced RAG integration for codebase context

**Long-Term Vision** (v3.0+ - 2027+)
- Pattern learning from successful task executions
- Multi-action natural language commands ("Create epic X and add 5 stories to it")
- Voice input integration (speech-to-text → NL processing)
- Autonomous documentation generation
- Cross-project knowledge sharing
- Community marketplace for templates, plugins, and configurations

**Release Cadence**:
- **Minor releases** (v1.x.0): Monthly (new features, non-breaking)
- **Patch releases** (v1.x.y): Weekly (bug fixes, performance)
- **Major releases** (v2.0.0+): Quarterly or based on feature completion

**How We Prioritize**:
1. **User-reported issues** (GitHub Issues, production logs)
2. **Real-world validation** (dogfooding Obra for Obra development)
3. **Performance metrics** (A/B testing, empirical data)
4. **Community demand** (feature requests, discussions)

**Feedback Channels**:
- [GitHub Issues](https://github.com/Omar-Unpossible/claude_code_orchestrator/issues) - Bug reports, feature requests
- [GitHub Discussions](https://github.com/Omar-Unpossible/claude_code_orchestrator/discussions) - Ideas, questions
- Production logs - Automated issue detection via monitoring

**Stability Guarantee**:
- **No breaking changes** in minor releases (v1.x.0)
- **6-month deprecation period** for breaking changes (v1.x → v2.0)
- **Migration guides** provided for all major version upgrades
- **LTS support** for previous major version (6 months after new major release)

---

### Further Reading

**Quick Start**:
- [User Quick Start Guide](../QUICK_START.md) - Get started in 10 minutes
- [Complete Setup Walkthrough](guides/COMPLETE_SETUP_WALKTHROUGH.md) - Windows 11 + Hyper-V setup

**System Understanding**:
- [OBRA System Overview](design/OBRA_SYSTEM_OVERVIEW.md) - ⭐ Complete system deep dive
- [System Architecture](../docs/architecture/ARCHITECTURE.md) - Technical architecture details
- [CLAUDE.md](../CLAUDE.md) - Developer guidance and contributing

**Feature Guides**:
- [Natural Language Command Guide](guides/NL_COMMAND_GUIDE.md) - Conversational interface usage
- [Agile Workflow Guide](guides/AGILE_WORKFLOW_GUIDE.md) - Epic/story/milestone workflows
- [Project Infrastructure Guide](guides/PROJECT_INFRASTRUCTURE_GUIDE.md) - Automatic doc maintenance
- [Configuration Profiles Guide](guides/CONFIGURATION_PROFILES_GUIDE.md) - Profile setup
- [Production Monitoring Guide](guides/PRODUCTION_MONITORING_GUIDE.md) - Structured logging
- [Session Management Guide](guides/SESSION_MANAGEMENT_GUIDE.md) - Context window management

**Architecture Decisions**:
- [ADR Index](decisions/) - All 17 architecture decision records
- [ADR-013: Agile Work Hierarchy](decisions/ADR-013-adopt-agile-work-hierarchy.md)
- [ADR-014: Natural Language Interface](decisions/ADR-014-natural-language-command-interface.md)
- [ADR-016: Decompose NL Extraction](decisions/ADR-016-decompose-nl-entity-extraction.md)
- [ADR-017: Unified Execution](decisions/ADR-017-unified-execution-architecture.md)

**Testing & Development**:
- [Test Guidelines](testing/TEST_GUIDELINES.md) - ⚠️ Critical testing practices
- [Implementation Plan](../docs/development/IMPLEMENTATION_PLAN.md) - M0-M9 roadmap

**Business & Strategy**:
- [Flexible LLM Orchestrator Strategy](business_dev/FLEXIBLE_LLM_ORCHESTRATOR_STRATEGY.md) - Dual deployment model

---

## Contact & Support

**Issues**: [GitHub Issues](https://github.com/Omar-Unpossible/claude_code_orchestrator/issues)
**Documentation**: [docs/README.md](README.md)
**License**: MIT

---

**Built for autonomous software development with systematic quality validation.**

*Last Updated: November 15, 2025 (v1.8.0)*
