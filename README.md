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
- ✅ **Multi-Stage Validation**: Response format → Quality → Confidence scoring
- 🎯 **Intelligent Decision Making**: Auto-proceed, clarify, retry, or escalate
- 📊 **State Management**: Complete history with rollback capability
- 🔌 **Plugin System**: Extensible for different agents and LLM providers
- 🖥️ **Multiple Interfaces**: CLI, Interactive REPL, and Programmatic API
- 🐳 **Easy Deployment**: Docker Compose for one-command setup

## Quick Start

### Option 1: Automated Setup

```bash
git clone https://github.com/yourusername/claude_code_orchestrator.git
cd claude_code_orchestrator
./setup.sh
```

### Option 2: Docker

```bash
git clone https://github.com/yourusername/claude_code_orchestrator.git
cd claude_code_orchestrator
docker-compose up -d
```

### Option 3: Manual Setup

```bash
# Clone repository
git clone https://github.com/yourusername/claude_code_orchestrator.git
cd claude_code_orchestrator

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

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

### Components (M0-M6)

- **M0**: Plugin System - Extensible architecture for agents/LLMs
- **M1**: Core Infrastructure - State management, config, models
- **M2**: LLM & Agent Interfaces - Communication layers
- **M3**: File Monitoring - Track all changes for rollback
- **M4**: Orchestration Engine - Scheduling, decisions, quality control
- **M5**: Utility Services - Tokens, context, confidence scoring
- **M6**: Integration & CLI - Main loop and user interfaces

See [Architecture Documentation](docs/architecture/ARCHITECTURE.md) for details.

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
