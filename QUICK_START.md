# Quick Start - Using Obra to Send Tasks to Claude

This guide shows you how to launch Obra and send your own prompts to Claude Code.

---

## Method 1: Simple One-Off Tasks (Recommended for Quick Tests)

For simple, one-off tasks, use this approach that bypasses the database layer:

### Create Your Own Script

Create a file `my_obra_task.py`:

```python
#!/usr/bin/env python3
"""
Send a custom prompt to Obra for orchestrated execution with Claude Code.
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.agents.claude_code_local import ClaudeCodeLocalAgent
from src.llm.local_interface import LocalLLMInterface


def run_obra_task(user_prompt: str, workspace_dir: str = '/tmp/obra-workspace'):
    """
    Execute a task through Obra orchestration.

    Args:
        user_prompt: Your task description
        workspace_dir: Where Claude Code should work
    """

    start_time = time.time()
    conversation = []

    print("=" * 100)
    print("OBRA ORCHESTRATION")
    print("=" * 100)
    print(f"\nYour task: {user_prompt}")
    print(f"Workspace: {workspace_dir}\n")

    # ========================================================================
    # STEP 1: Initialize Claude Code Agent (Headless + Dangerous Mode)
    # ========================================================================

    print("[1/4] Initializing Claude Code agent...")
    agent = ClaudeCodeLocalAgent()
    agent.initialize({
        'workspace_path': workspace_dir,
        'bypass_permissions': True,  # Dangerous mode - no permission prompts
        'response_timeout': 120,
        'use_session_persistence': False  # Fresh session (100% reliable)
    })
    print("✓ Claude Code agent ready (headless + dangerous mode)\n")

    conversation.append({
        'timestamp': time.time() - start_time,
        'actor': 'USER',
        'action': 'Provide Task',
        'content': user_prompt
    })

    # ========================================================================
    # STEP 2: Initialize Obra (Qwen LLM for Validation)
    # ========================================================================

    print("[2/4] Initializing Obra (Qwen LLM)...")
    qwen = LocalLLMInterface()
    qwen.initialize({
        'endpoint': 'http://172.29.144.1:11434',  # Adjust if your Ollama is elsewhere
        'model': 'qwen2.5-coder:32b',
        'temperature': 0.7,
        'timeout': 30
    })
    print(f"✓ Obra (Qwen) ready: {qwen.model}\n")

    # ========================================================================
    # STEP 3: Obra Enhances Your Prompt
    # ========================================================================

    print("[3/4] Obra analyzing and enhancing your prompt...")

    enhancement_prompt = f"""You are Obra, an AI orchestration system. A user has requested:

"{user_prompt}"

Your job is to:
1. Validate this is a reasonable task
2. Add any necessary clarifications for Claude Code
3. Make the prompt more specific and actionable

Respond with just the enhanced prompt (no preamble)."""

    qwen_start = time.time()
    try:
        enhanced_prompt = qwen.generate(enhancement_prompt)
        qwen_duration = time.time() - qwen_start

        print(f"✓ Prompt enhanced by Obra ({qwen_duration:.1f}s)")
        print(f"  Enhanced: {enhanced_prompt[:150]}...")
        print()

        conversation.append({
            'timestamp': time.time() - start_time,
            'actor': 'OBRA (Qwen)',
            'action': 'Enhance Prompt',
            'output': enhanced_prompt,
            'duration': qwen_duration
        })

    except Exception as e:
        print(f"⚠️ Qwen enhancement failed: {e}")
        print("  Using original prompt...\n")
        enhanced_prompt = user_prompt

        conversation.append({
            'timestamp': time.time() - start_time,
            'actor': 'OBRA',
            'action': 'Enhance Prompt (FAILED)',
            'error': str(e)
        })

    # ========================================================================
    # STEP 4: Claude Code Executes the Task
    # ========================================================================

    print("[4/4] Claude Code executing task...")

    claude_start = time.time()
    try:
        claude_response = agent.send_prompt(enhanced_prompt)
        claude_duration = time.time() - claude_start

        print(f"✓ Task completed by Claude Code ({claude_duration:.1f}s)")
        print(f"  Response length: {len(claude_response)} characters")
        print()

        conversation.append({
            'timestamp': time.time() - start_time,
            'actor': 'CLAUDE CODE',
            'action': 'Execute Task',
            'input': enhanced_prompt,
            'output': claude_response,
            'duration': claude_duration
        })

    except Exception as e:
        print(f"✗ Claude Code failed: {e}")
        agent.cleanup()
        return 1

    # ========================================================================
    # STEP 5: Obra Validates Claude's Response
    # ========================================================================

    print("[Validation] Obra checking Claude's work...")

    validation_prompt = f"""You are Obra, an AI orchestration system. Claude Code was asked to:

"{user_prompt}"

Claude responded with:
"{claude_response}"

Evaluate Claude's response:
1. Did Claude complete the task successfully?
2. Is the response clear and complete?
3. Quality score (0.0-1.0)
4. Any issues or concerns?

Respond in this format:
COMPLETED: [yes/no]
QUALITY: [0.0-1.0]
ISSUES: [list any issues, or "none"]
SUMMARY: [brief assessment]"""

    qwen_start = time.time()
    try:
        validation_response = qwen.generate(validation_prompt)
        qwen_duration = time.time() - qwen_start

        print(f"✓ Validation complete ({qwen_duration:.1f}s)")
        print()

        conversation.append({
            'timestamp': time.time() - start_time,
            'actor': 'OBRA (Qwen)',
            'action': 'Validate Response',
            'output': validation_response,
            'duration': qwen_duration
        })

    except Exception as e:
        print(f"⚠️ Qwen validation failed: {e}\n")

        conversation.append({
            'timestamp': time.time() - start_time,
            'actor': 'OBRA (Qwen)',
            'action': 'Validate Response (FAILED)',
            'error': str(e)
        })

    # ========================================================================
    # RESULTS
    # ========================================================================

    print("=" * 100)
    print("RESULTS")
    print("=" * 100)
    print()

    print("Claude's Response:")
    print("-" * 100)
    print(claude_response)
    print("-" * 100)
    print()

    if 'validation_response' in locals():
        print("Obra's Validation:")
        print("-" * 100)
        print(validation_response)
        print("-" * 100)
        print()

    # Check workspace files
    workspace_path = Path(workspace_dir)
    if workspace_path.exists():
        files = list(workspace_path.rglob('*'))
        files = [f for f in files if f.is_file()]

        if files:
            print(f"Files in workspace ({len(files)}):")
            for f in sorted(files)[:10]:  # Show first 10
                rel_path = f.relative_to(workspace_path)
                size = f.stat().st_size
                print(f"  - {rel_path} ({size} bytes)")
            if len(files) > 10:
                print(f"  ... and {len(files) - 10} more files")
            print()

    # Save conversation log
    total_duration = time.time() - start_time
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f'obra_task_{int(time.time())}.json'

    with open(log_file, 'w') as f:
        json.dump({
            'start_time': start_time,
            'total_duration': total_duration,
            'user_prompt': user_prompt,
            'workspace': workspace_dir,
            'conversation': conversation
        }, f, indent=2)

    print(f"📄 Conversation log: {log_file}")
    print(f"⏱️ Total time: {total_duration:.1f}s")
    print()

    print("=" * 100)
    print("✅ OBRA ORCHESTRATION COMPLETE!")
    print("=" * 100)

    # Cleanup
    agent.cleanup()

    return 0


def main():
    """Example usage."""

    # ========================================================================
    # YOUR PROMPT HERE
    # ========================================================================

    user_prompt = """
Create a Python script called 'fibonacci.py' that:
1. Defines a function to calculate Fibonacci numbers
2. Includes a recursive and iterative implementation
3. Has comprehensive docstrings
4. Includes example usage
"""

    # Optional: Specify workspace
    workspace = '/tmp/my-obra-workspace'

    # Run Obra orchestration
    return run_obra_task(user_prompt.strip(), workspace)


if __name__ == '__main__':
    sys.exit(main())
```

### Usage

```bash
# Activate your environment
source venv/bin/activate

# Run your custom task
python my_obra_task.py
```

**To modify**: Just change the `user_prompt` variable in the `main()` function!

---

## Method 2: Full CLI with Database (For Complex Projects)

For multi-task projects with state management, use the full CLI:

### Step 1: Initialize Obra

```bash
source venv/bin/activate
python -m src.cli init
```

This creates:
- Database at `~/obra-runtime/data/orchestrator.db`
- Default config at `config/config.yaml`

### Step 2: Create a Project

```bash
python -m src.cli project create "My Project" \
  --description "Building a web scraper" \
  --working-dir /tmp/my-project
```

This returns a project ID (e.g., `#1`).

### Step 3: Create Tasks

```bash
# Create your first task
python -m src.cli task create "Create HTML parser module" \
  --project 1 \
  --description "Build a module that parses HTML and extracts links" \
  --priority 8

# Create more tasks
python -m src.cli task create "Add error handling" \
  --project 1 \
  --priority 5

python -m src.cli task create "Write unit tests" \
  --project 1 \
  --priority 6
```

### Step 4: Execute Tasks

**Execute a single task:**
```bash
python -m src.cli task execute 1 --max-iterations 10
```

**Or run all pending tasks continuously:**
```bash
python -m src.cli run --project 1
```

### Step 5: Check Status

```bash
# View overall status
python -m src.cli status

# List all projects
python -m src.cli project list

# List tasks for a project
python -m src.cli task list --project 1

# List only pending tasks
python -m src.cli task list --status pending
```

---

## Configuration

The configuration file is at `config/config.yaml`. Key settings:

```yaml
# Agent Configuration (Claude Code)
agent:
  type: claude-code-local  # Headless mode
  local:
    claude_command: claude
    response_timeout: 120
    bypass_permissions: true  # Dangerous mode (no prompts)
    use_session_persistence: false  # Fresh sessions (reliable)

# LLM Configuration (Obra/Qwen)
llm:
  type: ollama
  model: qwen2.5-coder:32b
  api_url: http://172.29.144.1:11434  # ⚠️ Adjust if needed
  temperature: 0.7
  timeout: 30

# Database
database:
  url: sqlite:////home/omarwsl/obra-runtime/data/orchestrator.db

# Orchestration Settings
orchestration:
  max_iterations: 50
  iteration_timeout: 300
  task_timeout: 3600
```

**⚠️ Important**: Adjust `llm.api_url` if your Ollama is running elsewhere.

---

## Troubleshooting

### Qwen Connection Issues

If Obra can't connect to Qwen:

```bash
# Test Ollama is running
curl http://172.29.144.1:11434/api/tags

# If not running, start Ollama
ollama serve

# Verify Qwen model is available
ollama list | grep qwen
```

### Claude Code Permission Issues

If Claude asks for permissions:

1. Check `config/config.yaml` has `bypass_permissions: true`
2. Or manually add `--dangerously-skip-permissions` when testing

### Session Locking Issues

If you see "Session ID already in use":

1. Check `config/config.yaml` has `use_session_persistence: false`
2. This uses fresh sessions per call (100% reliable)

---

## Example Workflows

### Quick Code Generation

```python
# In my_obra_task.py, change user_prompt to:
user_prompt = """
Create a REST API server in Python using Flask that:
- Has endpoints for CRUD operations on a 'users' resource
- Includes input validation
- Returns JSON responses
- Has proper error handling
"""
```

### Multi-File Project

```bash
# Method 2 (CLI) is better for this
python -m src.cli project create "REST API Project" --working-dir /tmp/api-project

python -m src.cli task create "Create Flask app structure" --project 1 --priority 10
python -m src.cli task create "Implement user model" --project 1 --priority 9
python -m src.cli task create "Add CRUD endpoints" --project 1 --priority 8
python -m src.cli task create "Write integration tests" --project 1 --priority 7

python -m src.cli run --project 1
```

### Code Review/Analysis

```python
user_prompt = """
Review the code in /path/to/my/code and:
1. Identify potential bugs
2. Suggest performance improvements
3. Check for security vulnerabilities
4. Recommend refactoring opportunities

Provide a detailed report with code examples.
"""
```

---

## Logs and History

All Obra orchestration sessions are logged:

- **Conversation logs**: `logs/obra_task_<timestamp>.json` (Method 1)
- **Conversation logs**: `logs/conversation_<timestamp>.json` (test scripts)
- **Application logs**: `~/obra-runtime/logs/orchestrator.log` (Method 2)

Each log includes:
- Full conversation history (USER → OBRA → CLAUDE → OBRA)
- Timestamps and durations
- Prompts and responses
- Validation results

---

## Next Steps

1. **Start Simple**: Try Method 1 with a simple prompt
2. **Review Logs**: Check `logs/` to see the full Obra ↔ Claude conversation
3. **Tune Configuration**: Adjust `config/config.yaml` for your needs
4. **Scale Up**: Use Method 2 for larger projects with multiple tasks

**Need Help?**
- Check `POST_CLEANUP_VALIDATION.md` for test results
- Review `scripts/test_simple_orchestration_conversation.py` for examples
- See `docs/guides/GETTING_STARTED.md` for more details

---

**Happy Orchestrating! 🤖**
