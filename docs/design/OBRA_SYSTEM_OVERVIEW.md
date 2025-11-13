# Obra System Overview

**Document Type**: System Architecture & Design Principles
**Audience**: Developers, Claude Code AI, Product Managers
**Last Updated**: November 13, 2025
**Version**: 1.7.0

---

## Executive Summary

**Obra** (Claude Code Orchestrator) is an AI orchestration platform that enables autonomous software development through intelligent local-remote hybrid architecture. It combines a local reasoning LLM (Qwen 2.5 Coder) with remote code generation (Claude Code) to deliver autonomous development with intelligent oversight.

**Core Value**:
- Hybrid architecture: 75% local operations (cheap, fast) + 25% remote operations (quality)
- Automated quality pipeline with multi-stage validation
- Iterative improvement with quality-based retry loops
- Interactive control at strategic checkpoints

**Terminology Note**: This document uses formal terms **Orchestrator** and **Implementer** for the two LLM agents. Shorthand **Orc** and **Imp** may be used in internal communication for efficiency but should not appear in code or user-facing documentation.

---

## System Architecture

### Two-LLM Design

**Local LLM (Qwen 2.5 Coder on RTX 5090)**:
- **Purpose**: Fast reasoning for validation, quality scoring, confidence calculation, prompt optimization
- **Operations**: ~75% of total operations
- **Advantages**:
  - Low latency (local inference)
  - No API costs
  - Data sovereignty (sensitive code never leaves local environment)
  - GPU-accelerated (32GB VRAM)

**Remote AI (Claude Code CLI)**:
- **Purpose**: High-quality code generation executing in isolated environment
- **Operations**: ~25% of total operations
- **Advantages**:
  - State-of-the-art code generation capabilities
  - Extensive training on code patterns
  - Tool use and file operations
  - Fresh sessions per iteration (100% reliability)

**Orchestration Engine**:
- **Purpose**: Coordinates both LLMs through multi-stage validation pipeline
- **Responsibilities**:
  - Task scheduling with dependency resolution
  - Context management across sessions
  - Quality-based decision making
  - State persistence and rollback capability
  - Interactive checkpoint handling

### Deployment Architecture

**Two Orchestrator Deployment Options:**

**Option A: Local LLM (Hardware)**
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

**Option B: Remote LLM (Subscription)**
```
┌─────────────────────────────────────────────────────────────┐
│ HOST MACHINE (Windows 11 Pro or WSL2)                       │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Obra ─┬─→ subprocess → Claude Code (Local)           │  │
│  │       └─→ CLI → OpenAI Codex (Validation)            │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

**Key Differences**:
- **Option A (Ollama)**: Requires GPU hardware, zero API costs, complete privacy
  - **Obra + Claude Code**: Same WSL2 environment (subprocess communication)
  - **Obra + Ollama**: Network communication via HTTP API (172.29.144.1:11434)
  - **Benefit**: Claude Code runs isolated, Ollama leverages GPU on host
- **Option B (OpenAI Codex)**: No GPU required, subscription-based, lower hardware requirements
  - **Obra + Claude Code**: Same environment (subprocess communication)
  - **Obra + OpenAI**: CLI-based API communication (codex CLI)
  - **Benefit**: Lower barrier to entry, no hardware investment

**See**: `docs/business_dev/FLEXIBLE_LLM_ORCHESTRATOR_STRATEGY.md` for complete deployment strategy

---

## Core Capabilities

### 1. Automated Quality Pipeline

**Multi-Stage Validation** (Critical Design Pattern):
```
ResponseValidator (format/completeness)
    ↓
QualityController (correctness/requirements)
    ↓
ConfidenceScorer (heuristic + LLM ensemble)
    ↓
DecisionEngine (proceed/retry/clarify/escalate)
```

**Order Matters**: Always validate format BEFORE quality BEFORE confidence. Validation is fast, quality check is expensive (may use LLM).

**Quality-Based Iteration**:
- Configurable quality threshold (default: 0.75)
- Auto-retry with refined prompts when below threshold
- Maximum 3 iterations per task (configurable)
- Context from previous attempts included in retry prompts

**Failure Modes**:
- Incomplete response → Retry immediately
- Low quality → Review, refine prompt, retry
- Low confidence → Trigger breakpoint for human review
- Max iterations exceeded → Escalate to human

### 2. Hybrid Prompt Engineering (PHASE_6 - Validated)

**Format**: JSON metadata + natural language instructions

```
<METADATA>
{
  "prompt_type": "validation",
  "task_context": {...},
  "rules": [...],
  "expectations": {...}
}
</METADATA>

<INSTRUCTION>
Natural language task description with examples and constraints.
</INSTRUCTION>
```

**Validated Performance** (A/B Testing, p < 0.001):
- 35.2% token efficiency improvement
- 22.6% faster response times
- 100% parsing success rate (vs 87% baseline)
- Maintained quality scores (no degradation)

**Components**:
- `StructuredPromptBuilder`: Generates hybrid prompts with rule injection
- `StructuredResponseParser`: Parses and validates LLM responses against schemas
- `PromptRuleEngine`: Loads and applies rules from `config/prompt_rules.yaml`
- `ABTestingFramework`: Empirical comparison of prompt formats

**See**: `docs/design/LLM_FIRST_PROMPT_ENGINEERING_FRAMEWORK.md` for detailed design

### 3. Task Management & Dependencies

**Task Dependency System** (M9):
- Define dependencies: "Task B depends on Task A, C"
- Topological sort for optimal execution order
- Cycle detection prevents circular dependencies
- Automatic blocking until dependencies complete
- Cascading failure handling

**Retry Logic with Exponential Backoff** (M9):
- Gracefully handle transient failures (rate limits, timeouts, network issues)
- Exponential backoff: 1s → 2s → 4s → 8s → 16s (configurable)
- Jitter prevents thundering herd problems
- Differentiate retryable vs non-retryable errors

**Git Auto-Integration** (M9):
- Auto-commit after successful task completion
- LLM-generated semantic commit messages (via Qwen)
- Branch per task: `obra/task-{id}-{slug}`
- Optional PR creation via `gh` CLI
- Configurable commit strategy (per-task, per-milestone, manual)

**Configuration Profiles** (M9):
- Pre-configured profiles: `python_project`, `web_app`, `ml_project`, `microservice`, `minimal`, `production`
- Simplify setup with sensible defaults per project type
- Override via CLI: `--profile python_project --set key=value`

### 4. Interactive Control (Phase 1-2)

**Human-in-the-Loop Checkpoints** (6 strategic decision points):
1. Before agent execution
2. After agent response received
3. Before validation
4. After validation (if low confidence)
5. Before decision execution
6. On error/exception

**Interactive Commands** (8 commands):
- `/pause` - Pause orchestration loop
- `/resume` - Resume orchestration
- `/to-claude <message>` - Send direct message to Claude
- `/to-obra <message>` - Send message to Obra LLM
- `/override-decision <decision>` - Override DecisionEngine
- `/status` - Show current orchestration state
- `/help` - Show command help
- `/stop` - Gracefully stop orchestration

**Key Components**:
- `CommandProcessor` (376 lines): Parses and executes commands
- `InputManager` (176 lines): Non-blocking input with prompt_toolkit
- `TaskStoppedException`: Graceful shutdown signal

**See**: `docs/development/INTERACTIVE_STREAMING_QUICKREF.md` for command reference

### 5. Session Management Architecture

**Per-Iteration Fresh Sessions** (PHASE_4 Critical Fix):
- Each orchestration iteration uses a fresh Claude Code session
- Eliminates session lock conflicts (critical bug fix)
- No stale state between iterations
- Simpler error recovery (no session cleanup needed)

**Context Continuity** (Obra's Responsibility):
- Task history maintained in StateManager
- File change tracking via FileWatcher
- Metrics aggregated at task level (not session level)
- Previous iteration context included in prompts

**Configuration**:
- Context window limits: 200,000 tokens (Claude Pro)
- Refresh thresholds: 70% warning, 80% refresh, 95% critical
- Max turns: Task-type specific (3-20 turns, adaptive calculation)
- Timeout: 7200s (2 hours) default

**Why Fresh Sessions**:
- Attempted PTY for persistent sessions → Abandoned (Claude Code has known bugs)
- `subprocess.run()` with `--print` flag more reliable
- `--dangerously-skip-permissions` enables fully autonomous operation
- Trade-off: No persistent Claude session, but gains reliability and simplicity

**See**: `docs/guides/SESSION_MANAGEMENT_GUIDE.md` for complete guide

---

## Design Principles to Maintain

### 1. Hybrid Architecture Balance
**Principle**: Keep local (cheap, fast) and remote (quality) operations balanced.

**Guidelines**:
- Use local LLM for validation, scoring, prompt optimization (fast operations)
- Use remote AI for code generation (quality-critical operations)
- Target: ~75% local, ~25% remote operations
- Monitor token usage to maintain balance

**Trade-off**: Some operations could be done remotely, but cost and latency favor local.

### 2. Quality-First Validation Order
**Principle**: Always validate format → quality → confidence before proceeding.

**Sequence** (Order Matters):
1. **ResponseValidator**: Checks completeness and format (fast)
2. **QualityController**: Checks correctness and requirements (expensive, uses LLM)
3. **ConfidenceScorer**: Rates confidence using heuristic + LLM ensemble
4. **DecisionEngine**: Decides next action based on validation results

**Why Order Matters**:
- Completeness check is fast, catches obvious issues early
- Quality check is expensive (LLM call), only run if response is complete
- Confidence scoring depends on quality assessment
- Different failure modes require different actions

### 3. Fresh Sessions Prevent State Corruption
**Principle**: Per-iteration sessions eliminate lock conflicts and state corruption.

**Critical Fix** (PHASE_4):
- Previous architecture: Reused sessions → Lock conflicts, stale state
- New architecture: Fresh session per iteration → 100% reliability
- Obra provides continuity through StateManager and prompts

**Implementation**:
```python
# Each iteration uses fresh subprocess
result = subprocess.run([
    'claude',
    '--print',
    '--dangerously-skip-permissions',
    prompt
], timeout=7200)
```

**Trade-off**: ~100-200ms startup overhead per call, but eliminates entire class of bugs.

### 4. StateManager as Single Source of Truth
**Principle**: ALL state access goes through StateManager, never direct DB access.

**Rules**:
- No direct SQLAlchemy queries outside StateManager
- Use StateManager methods for all CRUD operations
- StateManager provides thread-safe access (RLock)
- Atomic transactions for data integrity
- Rollback capability via checkpoints

**Why**: Prevents inconsistencies, enables atomic operations, supports rollback.

### 5. Plugin System for Extensibility
**Principle**: Agents and LLM providers are pluggable via abstract base classes.

**Design Pattern**: Abstract Factory + Registry

**Benefits**:
- Swap agents via config (no code changes)
- Easy testing with mock agents
- Community contributions of new agents
- Multiple deployment models (SSH, local, Docker)

**Example**:
```python
@register_agent('claude-code-local')
class ClaudeCodeLocalAgent(AgentPlugin):
    def send_prompt(self, prompt: str) -> str: ...
    def is_healthy(self) -> bool: ...
```

**See**: `docs/decisions/001_why_plugins.md` for rationale

### 6. Fail-Safe Defaults
**Principle**: When uncertain, trigger breakpoint for human input.

**Guidelines**:
- Conservative confidence thresholds (prefer false positives)
- Checkpoint before risky operations
- Auto-save state frequently
- Graceful degradation on errors

**Implementation**:
- Low confidence (< 0.65) → Breakpoint
- Medium confidence (0.65-0.85) → Log warning, proceed
- High confidence (> 0.85) → Proceed without warning

### 7. Configuration-Driven Behavior
**Principle**: Behavior controlled via YAML configuration, not hardcoded values.

**Configuration Hierarchy**:
1. Default config (`config/default_config.yaml`)
2. Profile config (`config/profiles/python_project.yaml`)
3. Project config (`config/config.yaml`)
4. CLI overrides (`--set key=value`)

**Benefits**:
- Easy customization without code changes
- Profile-based project templates
- Version-controlled configuration
- Environment-specific settings

---

## Production Status

### Battle-Tested Reliability

**Testing Coverage**:
- **770+ tests** across all modules (70 test files)
- **88% overall coverage** (exceeds 85% target)
- **96-99% coverage** on critical modules (DecisionEngine, QualityController, ContextManager)
- **100/100 tests passing** for interactive streaming

**Real-World Validation**:
- **16 critical bugs** fixed through actual orchestration testing
- **6 bugs (PHASE_4)**: Session lock conflicts, stale state, metrics race conditions
- **10 bugs (Initial)**: Hook system, headless mode, output parsing, state persistence

**Key Insight**: 88% unit test coverage did NOT catch integration bugs. Real orchestration testing revealed state management and concurrency issues only visible in production workflows.

### Validated Performance (PHASE_6)

**A/B Testing Results** (Statistical Significance: p < 0.001):
- **35.2% token efficiency improvement**
- **22.6% faster response times**
- **100% parsing success rate** (vs 87% baseline)
- **Maintained quality scores** (no degradation)

**Method**: Controlled A/B testing comparing hybrid prompts vs unstructured prompts across 100+ validation tasks.

### Deployment Ready

**Supported Platforms**:
- Windows 11 Pro + Hyper-V + WSL2 (primary)
- Linux (native)
- Docker + Docker Compose (containerized)

**Automation**:
- Automated setup script (`setup.sh`)
- Docker deployment (`docker-compose up -d`)
- Configuration profiles for different project types

**Documentation**:
- Complete setup walkthrough (`docs/guides/COMPLETE_SETUP_WALKTHROUGH.md`)
- User-facing quick start (`QUICK_START.md`)
- Developer guidelines (`CLAUDE.md`)

---

## Development Focus Areas

When working on Obra, prioritize these areas:

### 1. Reliability
**Why**: Production deployments require 100% uptime and graceful error handling.

**Key Patterns**:
- Per-iteration fresh sessions (eliminates state corruption)
- Comprehensive error handling with context
- Retry logic with exponential backoff
- Graceful degradation on failures
- Comprehensive logging (43+ log points)

### 2. Quality
**Why**: Automated development requires high-quality output without human review.

**Key Patterns**:
- Multi-stage validation pipeline (format → quality → confidence)
- Quality-based iterative improvement
- Confidence scoring with conservative thresholds
- Human-in-the-loop checkpoints at strategic points

### 3. Efficiency
**Why**: Cost and speed determine viability for production use.

**Key Patterns**:
- Hybrid architecture (75% local, 25% remote)
- LLM-first prompt engineering (35% token efficiency)
- Token tracking and context window management
- Adaptive max_turns calculation (3-20 based on complexity)

### 4. Extensibility
**Why**: Different teams need different agents, LLMs, and workflows.

**Key Patterns**:
- Plugin system for agents and LLMs
- Configuration profiles for different project types
- Clean abstractions (AgentPlugin, LLMPlugin)
- Decorator-based registration

### 5. Observability
**Why**: Debugging autonomous systems requires comprehensive visibility.

**Key Patterns**:
- Structured logging (searchable, filterable)
- Metrics tracking (tokens, time, quality scores)
- Interactive control commands (/status, /pause, etc.)
- Session transcripts and state snapshots

---

## Architecture Decisions (ADRs)

Key architectural decisions documented in `docs/decisions/`:

1. **[ADR-001: Plugin Architecture](../decisions/001_why_plugins.md)** - Why plugins from the start
2. **[ADR-004: Local Agent Architecture](../decisions/ADR-004-local-agent-architecture.md)** - Subprocess vs SSH
3. **[ADR-006: LLM-First Prompts](../decisions/ADR-006-llm-first-prompts.md)** - Hybrid prompt format
4. **[ADR-007: Headless Mode Enhancements](../decisions/ADR-007-headless-mode-enhancements.md)** - Per-iteration sessions
5. **[ADR-008: Retry Logic](../decisions/ADR-008-retry-logic.md)** - Exponential backoff
6. **[ADR-009: Task Dependencies](../decisions/ADR-009-task-dependencies.md)** - Dependency system
7. **[ADR-010: Git Integration](../decisions/ADR-010-git-integration.md)** - Auto-commit strategy
8. **[ADR-011: Interactive Streaming](../decisions/ADR-011-interactive-streaming-interface.md)** - Command injection

---

## Future Roadmap

See `docs/design/design_future.md` for detailed roadmap.

### Near-Term (v1.3)
- Budget & Cost Controls (token limits, rate limiting)
- Metrics & Reporting System (dashboards, analytics)
- Checkpoint System (save/restore orchestration state)
- Prompt Template Library (reusable prompt patterns)

### Mid-Term (v1.4)
- Web UI dashboard (real-time monitoring)
- Multi-project orchestration
- Pattern learning from successful tasks
- WebSocket updates for live status

### Long-Term (v2.0)
- Distributed architecture (multiple hosts)
- Horizontal scaling
- Advanced ML-based pattern learning
- Multi-agent collaboration
- Claude-Driven Parallelization (see ADR-005)

---

## Key Takeaways for Developers

### When Acting as Product Manager
1. **Prioritize reliability over features** - Fresh sessions, error handling, graceful degradation
2. **Validate performance claims** - Use A/B testing, measure token efficiency
3. **Design for extensibility** - Plugin system, configuration profiles
4. **Maintain design principles** - StateManager SSOT, validation order, fresh sessions

### When Acting as Engineer
1. **Follow established patterns** - Never bypass StateManager, always use fresh sessions
2. **Maintain test coverage** - ≥85% overall, ≥90% critical modules
3. **Test with real orchestration** - Unit tests don't catch integration bugs
4. **Update documentation** - Keep ADRs, guides, and CLAUDE.md in sync

### When Planning Features
1. **Check ADRs first** - Understand why current design exists
2. **Consider hybrid architecture** - Keep local/remote balance
3. **Design for observability** - Logging, metrics, interactive control
4. **Validate with testing** - Real orchestration, not just unit tests

---

## References

### Essential Documentation
- **[CLAUDE.md](../../CLAUDE.md)** - Developer guidance for Claude Code
- **[ARCHITECTURE.md](../architecture/ARCHITECTURE.md)** - Complete system architecture
- **[IMPLEMENTATION_PLAN.md](../development/IMPLEMENTATION_PLAN.md)** - M0-M9 master roadmap
- **[CHANGELOG.md](../../CHANGELOG.md)** - Version history and recent changes

### Design Documents
- **[LLM_FIRST_PROMPT_ENGINEERING_FRAMEWORK.md](LLM_FIRST_PROMPT_ENGINEERING_FRAMEWORK.md)** - PHASE_6 design
- **[design_future.md](design_future.md)** - Future roadmap

### User Guides
- **[QUICK_START.md](../../QUICK_START.md)** - User-facing quick start
- **[SESSION_MANAGEMENT_GUIDE.md](../guides/SESSION_MANAGEMENT_GUIDE.md)** - Session management
- **[CONFIGURATION_PROFILES_GUIDE.md](../guides/CONFIGURATION_PROFILES_GUIDE.md)** - Configuration profiles

### Phase Reports
- **[PHASE4_SESSION_COMPLETE_SUMMARY.md](../development/phase-reports/PHASE4_SESSION_COMPLETE_SUMMARY.md)** - 6 critical bugs
- **[PHASE6_LLM_FIRST_PROMPTS_COMPLETE.md](../development/phase-reports/PHASE6_LLM_FIRST_PROMPTS_COMPLETE.md)** - Performance validation

---

**Last Updated**: November 13, 2025
**Version**: 1.7.0 (Unified Execution Architecture)
**Status**: Production-Ready
