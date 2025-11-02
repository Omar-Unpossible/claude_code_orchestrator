# Getting Started with Claude Code Orchestrator

## Quick Start Guide

Get up and running with the Claude Code Orchestrator in under 10 minutes.

## Prerequisites

- Python 3.10 or higher
- Git
- (Optional) Docker for containerized deployment
- (Optional) NVIDIA GPU with 24GB+ VRAM for local LLM

## Installation

### Option 1: Local Installation

1. **Clone the repository**:
```bash
git clone https://github.com/yourusername/claude_code_orchestrator.git
cd claude_code_orchestrator
```

2. **Create virtual environment**:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Initialize the orchestrator**:
```bash
python -m src.cli init
```

This creates:
- Database file (`orchestrator.db`)
- Default configuration (`config/config.yaml`)

### Option 2: Docker Installation

1. **Clone the repository**:
```bash
git clone https://github.com/yourusername/claude_code_orchestrator.git
cd claude_code_orchestrator
```

2. **Start with Docker Compose**:
```bash
docker-compose up -d
```

3. **Access the CLI**:
```bash
docker-compose exec orchestrator python -m src.cli status
```

## Configuration

Edit `config/config.yaml` to customize your setup:

```yaml
# Database configuration
database:
  url: sqlite:///orchestrator.db

# Agent configuration
agent:
  type: mock  # Options: mock, claude_code, aider
  config:
    timeout: 300
    max_retries: 3

# LLM configuration
llm:
  provider: ollama  # or openai, anthropic
  model: qwen2.5-coder:32b
  base_url: http://localhost:11434
  temperature: 0.1

# Orchestration settings
orchestration:
  breakpoints:
    confidence_threshold: 0.7
    max_retries: 3

  decision:
    high_confidence: 0.85
    medium_confidence: 0.65
    low_confidence: 0.4

  quality:
    min_quality_score: 0.7
    enable_syntax_validation: true
    enable_testing_validation: false
```

## Basic Usage

### 1. Create a Project

```bash
python -m src.cli project create "My First Project" \
  --description "Learning to use the orchestrator"
```

Output:
```
✓ Created project #1: My First Project
  Working directory: /home/user/projects/claude_code_orchestrator
```

### 2. Create a Task

```bash
python -m src.cli task create "Implement add function" \
  --project 1 \
  --description "Create a function that adds two numbers" \
  --priority 8
```

Output:
```
✓ Created task #1: Implement add function
  Project: #1
  Priority: 8
```

### 3. Execute the Task

```bash
python -m src.cli task execute 1
```

Output:
```
Executing task #1...

================================================================================
Task #1 execution result:
================================================================================
Status: completed
Iterations: 2
Quality Score: 0.87
Confidence: 0.92

✓ Task completed successfully!
```

### 4. View Status

```bash
python -m src.cli status
```

Output:
```
Orchestrator Status
================================================================================
Projects: 1
Tasks:
  Pending: 0
  In Progress: 0
  Completed: 1
  Total: 1
```

## Interactive Mode

For a more interactive experience, use the REPL:

```bash
python -m src.cli interactive
```

This starts an interactive shell:

```
================================================================================
Claude Code Orchestrator - Interactive Mode
================================================================================

Type 'help' for available commands

orchestrator> help

Available Commands:
================================================================================

General:
  help                    - Show this help message
  exit, quit              - Exit interactive mode
  history                 - Show command history
  clear                   - Clear screen

Project Management:
  project create <name>   - Create a new project
  project list            - List all projects
  project show <id>       - Show project details
  use <project_id>        - Set current project

Task Management:
  task create <title>     - Create task (requires current project)
  task list               - List tasks
  task show <id>          - Show task details

Execution:
  execute <task_id>       - Execute a single task
  run                     - Run orchestrator continuously
  stop                    - Stop continuous run
  status                  - Show orchestrator status

orchestrator> project create "Interactive Demo"
✓ Created project #2: Interactive Demo

orchestrator> use 2
✓ Using project #2: Interactive Demo

orchestrator[project:2]> task create "Write hello world"
✓ Created task #2: Write hello world

orchestrator[project:2]> execute 2
Executing task #2...
✓ Task completed successfully!

orchestrator[project:2]> exit
Goodbye!
```

## Common Workflows

### Workflow 1: Simple Task Execution

```bash
# 1. Create project
python -m src.cli project create "Simple Tasks"

# 2. Create task
python -m src.cli task create "Fix bug in login" --project 1 --priority 10

# 3. Execute task
python -m src.cli task execute 1

# 4. Check result
python -m src.cli task list --status completed
```

### Workflow 2: Continuous Mode

```bash
# Start continuous orchestration
python -m src.cli run --project 1
```

The orchestrator will:
- Continuously poll for pending tasks
- Execute them in priority order
- Handle errors gracefully
- Stop when no tasks remain

Press `Ctrl+C` to stop.

### Workflow 3: Multi-Task Project

```bash
# Create project
python -m src.cli project create "Feature Development"

# Create multiple tasks
python -m src.cli task create "Task 1: Setup" --project 1 --priority 10
python -m src.cli task create "Task 2: Implementation" --project 1 --priority 8
python -m src.cli task create "Task 3: Testing" --project 1 --priority 5

# Run all tasks
python -m src.cli run --project 1
```

## Troubleshooting

### Issue: "Orchestrator not initialized"

**Solution**: Run initialization:
```bash
python -m src.cli init
```

### Issue: "Module not found" errors

**Solution**: Install dependencies:
```bash
pip install -r requirements.txt
```

### Issue: Task stuck "in_progress"

**Solution**: Check task status:
```bash
python -m src.cli task list --status in_progress
```

Then either:
1. Wait for timeout
2. Manually update status in database
3. Restart orchestrator

### Issue: Low confidence scores

**Causes**:
- Task description too vague
- Agent producing poor quality code
- LLM validation being too strict

**Solutions**:
- Make task descriptions more specific
- Adjust `orchestration.decision.medium_confidence` threshold in config
- Check LLM is running correctly

### Issue: Tasks escalating to human

**Causes**:
- Confidence below threshold
- Max retries exceeded
- Quality score too low

**Solutions**:
- Review task in database
- Adjust confidence thresholds in config
- Improve task description clarity

## Configuration Tips

### For Development

```yaml
orchestration:
  breakpoints:
    confidence_threshold: 0.6  # Lower for development
  decision:
    high_confidence: 0.75      # Lower thresholds
    medium_confidence: 0.55
```

### For Production

```yaml
orchestration:
  breakpoints:
    confidence_threshold: 0.8  # Higher for safety
  decision:
    high_confidence: 0.90      # Stricter thresholds
    medium_confidence: 0.75
```

### For Fast Iteration

```yaml
agent:
  type: mock  # Use mock agent for testing
  config:
    timeout: 60  # Shorter timeout
```

## Next Steps

- Read [Architecture Documentation](../architecture/ARCHITECTURE.md)
- Explore [API Reference](../api/API_REFERENCE.md)
- Check [Advanced Usage Guide](ADVANCED_USAGE.md)
- Review [Configuration Reference](CONFIGURATION.md)

## Getting Help

- **Documentation**: Check `docs/` directory
- **Issues**: Report bugs on GitHub Issues
- **Discussions**: Join GitHub Discussions
- **CLI Help**: Run `python -m src.cli --help`

## Example Projects

See `examples/` directory for:
- Simple calculator implementation
- TODO app with database
- REST API development
- Test suite generation

---

**Happy Orchestrating!** 🎉
