# Claude Code Orchestrator

**Intelligent supervision system for Claude Code with local LLM oversight**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)]()
[![Coverage](https://img.shields.io/badge/coverage-88%25-green.svg)]()

## Overview

The Claude Code Orchestrator is a supervision system where a local LLM (Qwen 2.5 Coder on RTX 5090) provides intelligent oversight for Claude Code CLI executing tasks in an isolated environment. This enables semi-autonomous software development with continuous validation, quality control, and human intervention points.

### Key Features

- 🤖 **Autonomous Task Execution**: Claude Code performs the heavy lifting
- 🧠 **Local LLM Supervision**: Qwen 2.5 validates and guides execution
- 🚀 **Headless Mode**: Non-interactive subprocess execution with `--print` and `--dangerously-skip-permissions`
- 🔄 **Iterative Orchestration**: Multi-turn workflows with automatic improvement (quality-based retry)
- ✅ **Multi-Stage Validation**: Response format → Quality → Confidence scoring
- 🎯 **Intelligent Decision Making**: Auto-proceed, clarify, retry, or escalate
- 📊 **State Management**: Complete history with rollback capability
- 🔌 **Plugin System**: Extensible for different agents and LLM providers
- 🖥️ **Multiple Interfaces**: CLI, Interactive REPL, Simple Scripts, and Programmatic API
- 🐳 **Easy Deployment**: Docker Compose for one-command setup
- 🚀 **LLM-First Prompt Engineering**: Hybrid format (35% token efficiency, 23% faster responses) - See [PHASE_6](#phase_6-llm-first-prompt-engineering)
- 📊 **Production Monitoring**: Structured JSON logging with quality metrics, privacy redaction, and session tracking (v1.8.0)

**📖 New to Obra? Read the [Product Overview](docs/PRODUCT_OVERVIEW.md) for a comprehensive introduction to features, architecture, and use cases.**

## Quick Start

**For detailed setup instructions and user guide, see [QUICK_START.md](QUICK_START.md)**

### Option 1: Simple Runner Scripts (Recommended for Testing)

The easiest way to test Obra with your own prompts:

```bash
# Clone and setup
git clone https://github.com/Omar-Unpossible/claude_code_orchestrator.git
cd claude_code_orchestrator
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# One-shot execution - Edit USER_PROMPT in run_obra.py
python run_obra.py

# Iterative execution (max 3 iterations with quality validation)
python run_obra_iterative.py
```

See [QUICK_START.md](QUICK_START.md) for how to customize prompts and configuration.

### Option 2: Automated Setup

```bash
git clone https://github.com/Omar-Unpossible/claude_code_orchestrator.git
cd claude_code_orchestrator
./setup.sh
```

### Option 3: Docker

```bash
git clone https://github.com/Omar-Unpossible/claude_code_orchestrator.git
cd claude_code_orchestrator
docker-compose up -d
```

### Option 4: Full CLI

```bash
# Manual setup with full CLI
git clone https://github.com/Omar-Unpossible/claude_code_orchestrator.git
cd claude_code_orchestrator

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Initialize orchestrator
python -m src.cli init
```

## Usage

### CLI Commands

```bash
# Create a project
python -m src.cli project create "My Project"

# Create a task
python -m src.cli task create "Implement feature X" --project 1 --priority 8

# Execute a single task
python -m src.cli task execute 1

# Run continuous orchestration
python -m src.cli run --project 1

# Check status
python -m src.cli status
```

### Interactive Mode

```bash
$ python -m src.cli interactive

orchestrator> project create "Demo Project"
✓ Created project #1: Demo Project

orchestrator> use 1
✓ Using project #1: Demo Project

orchestrator[project:1]> task create "Write hello world function"
✓ Created task #1: Write hello world function

orchestrator[project:1]> execute 1
Executing task #1...
✓ Task completed successfully!

orchestrator[project:1]> exit
Goodbye!
```

### Programmatic Usage

```python
from src.orchestrator import Orchestrator
from src.core.config import Config

# Load configuration
config = Config.load('config/config.yaml')

# Create and initialize orchestrator
orch = Orchestrator(config=config)
orch.initialize()

# Execute a task
result = orch.execute_task(task_id=1, max_iterations=10)
print(f"Status: {result['status']}")
print(f"Confidence: {result['confidence']:.2f}")

# Or run continuously
orch.run(project_id=1)
```

## Architecture

```
User (CLI/Interactive/API)
    ↓
Orchestrator (Integration Loop)
    ├─ ContextManager (builds context)
    ├─ PromptGenerator (creates prompts)
    ├─ Agent (executes tasks)
    ├─ ResponseValidator (validates format)
    ├─ QualityController (checks quality)
    ├─ ConfidenceScorer (scores confidence)
    ├─ DecisionEngine (decides next action)
    └─ StateManager (persists everything)
```

### Components (M0-M8) - **All Complete** ✅

- **M0**: Plugin System - Extensible architecture for agents/LLMs (95% coverage)
- **M1**: Core Infrastructure - State management, config, models (84% coverage)
- **M2**: LLM & Agent Interfaces - Communication layers (90% coverage)
- **M3**: File Monitoring - Track all changes for rollback (90% coverage)
- **M4**: Orchestration Engine - Scheduling, decisions, quality control (96-99% coverage)
- **M5**: Utility Services - Tokens, context, confidence scoring (91% coverage)
- **M6**: Integration & CLI - Main loop and user interfaces (Complete, 122 tests)
- **M7**: Testing & Deployment - Comprehensive test suite (88% overall coverage)
- **M8**: Local Agent Implementation - Headless mode for Claude Code (100% coverage, 33 tests)

**Project Status**: ✅ Production-ready (v1.1) - 433+ tests, 88% coverage

See [Architecture Documentation](docs/architecture/ARCHITECTURE.md) for details.

### PHASE_6: LLM-First Prompt Engineering

**Status**: ✅ Complete (2025-11-03)

Obra uses a **hybrid prompt engineering framework** combining JSON metadata with natural language instructions:

#### Key Improvements (Validated via A/B Testing)
- ✅ **35.2% token efficiency improvement** (p < 0.001, statistically significant)
- ✅ **22.6% faster response times** (p < 0.001, statistically significant)
- ✅ **100% parsing success rate** with schema validation
- ✅ **Maintained quality**: Same validation accuracy as unstructured prompts

#### Hybrid Prompt Format

```
<METADATA>
{
  "prompt_type": "validation",
  "rules": [...],
  "expectations": {...}
}
</METADATA>

<INSTRUCTION>
Natural language task description with examples and constraints.
</INSTRUCTION>
```

#### Migrated Templates
- ✅ **Validation prompts** - Structured format (TASK_6.1)
- ✅ **Task execution prompts** - Structured format (TASK_6.4)
- ⏳ **Error analysis, decision, planning** - Future migrations

#### Components Added
- **StructuredPromptBuilder** - Generates hybrid prompts with rule injection
- **StructuredResponseParser** - Parses and validates LLM responses against schemas
- **PromptRuleEngine** - Loads and applies rules from `config/prompt_rules.yaml`
- **ABTestingFramework** - Empirical comparison of prompt formats
- **TaskComplexityEstimator** - Estimates task complexity for parallelization suggestions

See [ADR-006](docs/decisions/ADR-006-llm-first-prompts.md) and [Prompt Engineering Guide](docs/guides/PROMPT_ENGINEERING_GUIDE.md) for details.

## How It Works

### Headless Mode (M8)

Obra uses **headless mode** to execute Claude Code non-interactively:

- **`--print` flag**: Returns output directly to STDOUT (no terminal emulation needed)
- **`--dangerously-skip-permissions`**: Bypasses all permission prompts for autonomous operation
- **Fresh sessions**: Each call uses a new session (no persistent state, 100% reliable)
- **Context continuity**: Obra provides context across fresh sessions via prompt enhancement

**Why not PTY?** Claude Code has known issues with PTY/terminal emulation (no bugfix available). Headless mode is simpler and more reliable.

### Session Management

Obra provides intelligent session management for complex, multi-task workflows:

#### Milestone-Based Sessions
- **Sessions** maintain context across related tasks within a milestone
- **Workplan context** injected on first task of milestone
- **Previous milestone summaries** included for continuity
- **Automatic session refresh** when context window reaches 80% capacity

#### Context Window Management
- **Manual token tracking**: Monitors cumulative token usage across interactions
- **Tiered thresholds**:
  - 70% (Warning): Log warning, continue normally
  - 80% (Refresh): Auto-refresh session with Qwen-generated summary
  - 95% (Critical): Emergency refresh to prevent overflow
- **Seamless continuity**: Summaries preserve key decisions and context

#### Adaptive Max Turns
- **Complexity-based calculation**: Simple tasks (3 turns) to very complex (20 turns)
- **Task type overrides**: Debugging (20), code generation (12), validation (5)
- **Auto-retry on error_max_turns**: Doubles limit and retries once if exceeded
- **Configurable bounds**: Min 3, max 30 turns

#### Extended Timeouts
- **Default: 7200s (2 hours)** - supports complex workflows without interruption
- **Configurable per deployment**: Adjust for quick tasks (1800s) or overnight jobs (14400s)
- **Separate limits**: Timeout (wall-clock) and max_turns (iterations) both enforced

**See [Session Management Guide](docs/guides/SESSION_MANAGEMENT_GUIDE.md) for detailed usage and configuration.**

### Production Monitoring (v1.8.0)

Obra includes **built-in production logging** for real-time observability and quality monitoring:

#### Features
- **JSON Lines Format**: Machine-parsable logs for easy analysis
- **I/O Boundary Logging**: Captures user input → NL processing → execution → results
- **Quality Metrics**: Confidence scores, validation status, and performance timing
- **Privacy Protection**: Automatic PII and secret redaction
- **Session Tracking**: Multi-turn conversation continuity via UUID

#### Logged Events
- `user_input`: All user commands and natural language input
- `nl_result`: NL parsing quality (confidence, validation, duration)
- `execution_result`: Task execution outcomes (success, entities affected, timing)
- `error`: Failures with stage context for debugging

#### Configuration

Production logging is **enabled by default**. To disable or customize:

```yaml
# config/config.yaml
monitoring:
  production_logging:
    enabled: true  # Set to false to disable
    path: "~/obra-runtime/logs/production.jsonl"
    events:
      user_input: true
      nl_results: true
      execution_results: true
      errors: true
    privacy:
      redact_pii: true      # Email, IP, phone, SSN
      redact_secrets: true  # API keys, tokens
```

#### Viewing Logs

```bash
# View all logs
cat ~/obra-runtime/logs/production.jsonl | jq .

# Filter by event type
cat ~/obra-runtime/logs/production.jsonl | jq 'select(.type == "error")'

# View quality metrics
cat ~/obra-runtime/logs/production.jsonl | jq 'select(.type == "nl_result") | {confidence, validation, duration_ms}'

# Track a specific session
cat ~/obra-runtime/logs/production.jsonl | jq 'select(.session == "SESSION_ID")'
```

#### When to Disable

Production logging is enabled by default for observability. Consider disabling in:
- **Privacy-sensitive environments**: Even with redaction, logging all interactions may not be acceptable
- **Disk space constraints**: Logs can grow to 1GB with default rotation settings
- **Development**: Frequent restarts generate many sessions

**See [Production Monitoring Guide](docs/guides/PRODUCTION_MONITORING_GUIDE.md) for complete documentation.**

### Iterative Orchestration Workflow

The `run_obra_iterative.py` script demonstrates multi-turn task execution:

```
1. USER provides task
   ↓
2. OBRA (Qwen) enhances prompt → makes it more directive
   ↓
3. CLAUDE CODE executes task (headless mode, 300s timeout)
   ↓
4. OBRA (Qwen) validates response:
   - Checks completeness (all files created?)
   - Scores quality (0.0-1.0)
   - Identifies specific issues
   ↓
5. DECISION:
   - Quality ≥ threshold (0.75) → ✅ PROCEED
   - Quality < threshold → 🔄 RETRY (max 3 iterations)
     - Clean workspace
     - Build context from previous attempts
     - Send improved prompt with feedback
```

**Example**: CSV tool task with 3-iteration limit:
- Iteration 1: Claude implements core modules (quality: 0.65)
- Iteration 2: Obra identifies missing tests, Claude adds them (quality: 0.80)
- Result: Task complete in 2 iterations ✅

See [QUICK_START.md](QUICK_START.md) for how to customize and run iterative workflows.

## Configuration

Edit `config/config.yaml`:

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
  temperature: 0.1

orchestration:
  breakpoints:
    confidence_threshold: 0.7
  decision:
    high_confidence: 0.85
    medium_confidence: 0.65
```

## Development

### Setup Development Environment

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# Run tests with coverage
pytest --cov=src --cov-report=term

# Run linting
pylint src/
mypy src/
black src/ tests/
```

### Shell Enhancements for Claude Code

**WSL2 development environment includes 35+ specialized commands for LLM-led development workflows.**

**Quick Reference**:
```bash
claude-help          # Show all available commands
context              # Get complete project snapshot (use BEFORE Claude Code sessions)
recent 5             # Show recently modified files
todos                # Show all TODO/FIXME comments
gcom <msg>           # Quick git commit (stage all + commit)
test                 # Auto-detecting test runner (Python/Node/Rust/Go)
save-context         # Save work context between sessions
```

**Documentation**:
- See `CLAUDE.md` → "Development Environment & Shell Enhancements" section
- Full guide: `~/CLAUDE_ENHANCEMENTS_README.md`
- Quick start: `~/CLAUDE_ENHANCEMENTS_QUICKSTART.md`

**Installed Tools**:
- Modern CLI: bat, exa, fd, ripgrep, fzf, zoxide, direnv
- Enhancement tools: git-delta, tokei, hyperfine, tree, httpie, jless, watchexec

**Recommended Workflow**:
1. Navigate to project: `z obra` or `obra`
2. Get context: `context && recent 5 && todos`
3. Start Claude Code: `claude`
4. During development: Use `ff`, `test`, `gcom`, `gamend`
5. End session: `save-context`

### Project Structure

```
claude_code_orchestrator/
├── src/
│   ├── core/           # M1: State, config, models
│   ├── plugins/        # M0: Plugin system
│   ├── llm/            # M2: LLM interface
│   ├── agents/         # M2: Agent implementations
│   ├── monitoring/     # M3: File watching
│   ├── orchestration/  # M4: Scheduling, decisions
│   ├── utils/          # M5: Utilities
│   ├── orchestrator.py # M6: Main integration
│   ├── cli.py          # M6: CLI interface
│   └── interactive.py  # M6: Interactive REPL
├── tests/              # Comprehensive test suite
├── docs/
│   ├── architecture/   # System design
│   ├── api/            # API reference
│   └── guides/         # User guides
├── config/             # Configuration files
└── docker-compose.yml  # Docker deployment
```

## Testing

**Test Coverage**: 88% overall
- M0-M1 (Core): 84%
- M2 (LLM): 90%
- M3 (Monitoring): 90%
- M4 (Orchestration): 75%
- M5 (Utilities): 91%
- M6 (Integration): 44% (in progress)

```bash
# Run all tests
pytest

# Run specific module
pytest tests/test_orchestrator.py

# Run with coverage
pytest --cov=src --cov-report=html

# Run integration tests
pytest tests/test_integration_e2e.py
```

## Performance

| Metric | Target | Achieved |
|--------|--------|----------|
| LLM Response (p95) | <10s | ~5s |
| Orchestrator Init | <5s | <1s |
| State Operation (p95) | <100ms | <10ms |
| File Change Detection | <1s | <100ms |

## Roadmap

### v1.0 (Current)
- ✅ Complete M0-M6 implementation
- ✅ CLI and Interactive interfaces
- ✅ Comprehensive testing
- ✅ Documentation
- ✅ Docker deployment

### v1.1 (Planned)
- [ ] Web UI dashboard
- [ ] Real-time WebSocket updates
- [ ] Multi-project orchestration
- [ ] Pattern learning from successful tasks

### v2.0 (Future)
- [ ] Distributed architecture
- [ ] Horizontal scaling
- [ ] Advanced ML-based pattern learning
- [ ] Git integration (automatic commits)

## Documentation

**Quick Links**:
- ⭐ **[Product Overview](docs/PRODUCT_OVERVIEW.md)** - **START HERE** - Comprehensive introduction to Obra
- 📖 [Documentation Index](docs/README.md) - Complete documentation navigation
- 🚀 [Complete Setup Walkthrough](docs/guides/COMPLETE_SETUP_WALKTHROUGH.md) - Windows 11 + Hyper-V setup
- 📘 [Getting Started Guide](docs/guides/GETTING_STARTED.md) - Quick start and basic usage
- 🏗️ [System Architecture](docs/architecture/ARCHITECTURE.md) - Complete technical design
- 🛠️ [Implementation Plan](docs/development/IMPLEMENTATION_PLAN.md) - M0-M7 roadmap
- ⚠️ [Test Guidelines](docs/development/TEST_GUIDELINES.md) - Critical testing practices

**For Developers**:
- [Project Status (M7)](docs/development/milestones/M7_COMPLETION_SUMMARY.md) - Latest completion status
- [Milestone Summaries](docs/development/milestones/) - M1-M7 completion reports
- [Architecture Decisions](docs/decisions/) - ADRs explaining design choices
- [CLAUDE.md](CLAUDE.md) - Guidance for Claude Code

## Requirements

- Python 3.10+
- SQLite or PostgreSQL
- (Optional) NVIDIA GPU with 24GB+ VRAM for local LLM
- (Optional) Docker for containerized deployment

### Dependencies

**Core**:
- SQLAlchemy 2.0+ (ORM)
- Click 8.0+ (CLI framework)
- PyYAML 6.0+ (configuration)

**Optional**:
- Paramiko (SSH agent support)
- Watchdog (file monitoring)
- Tiktoken (accurate token counting)
- Ollama (local LLM runtime)

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Troubleshooting

### Common Issues

**"Module not found" errors**:
```bash
pip install -r requirements.txt
```

**"Orchestrator not initialized"**:
```bash
python -m src.cli init
```

**Low confidence scores**:
- Make task descriptions more specific
- Adjust thresholds in `config/config.yaml`
- Check LLM is running correctly

See [Troubleshooting Guide](docs/guides/TROUBLESHOOTING.md) for more.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- **Claude Code** by Anthropic - The execution agent
- **Qwen 2.5** by Alibaba - The supervision LLM
- **Ollama** - Local LLM runtime
- **Click** - CLI framework
- **SQLAlchemy** - ORM framework

## Citation

```bibtex
@software{claude_code_orchestrator,
  title = {Claude Code Orchestrator},
  author = {Your Name},
  year = {2025},
  url = {https://github.com/yourusername/claude_code_orchestrator}
}
```

---

**Built with ❤️ for autonomous software development**
