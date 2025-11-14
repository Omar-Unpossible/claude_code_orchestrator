#!/usr/bin/env python3
"""Test real orchestration with Claude Code and Ollama.

This script tests the complete Obra orchestration system with:
- Real ClaudeCodeLocalAgent (subprocess to Claude Code CLI)
- Real Ollama/Qwen LLM for validation
- Real task execution end-to-end

Usage:
    python scripts/test_real_orchestration.py [--task-type simple|calculator|complex]
"""

import argparse
import sys
import logging
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.config import Config
from src.orchestrator import Orchestrator

# Create logs directory if it doesn't exist
(Path.home() / 'obra-runtime' / 'logs').mkdir(parents=True, exist_ok=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(str(Path.home() / 'obra-runtime' / 'logs' / 'real_agent_test.log')),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


# Task definitions
TASKS = {
    'simple': {
        'title': 'Create Hello World',
        'description': 'Create a Python script that prints "Hello, World!" to the console.'
    },
    'calculator': {
        'title': 'Create Python Calculator',
        'description': '''Create a Python calculator with the following:

1. Functions: add, subtract, multiply, divide
2. Error handling for division by zero
3. Unit tests using pytest
4. Docstrings for all functions

Create two files:
- calculator.py (implementation)
- test_calculator.py (tests)

Make sure all tests pass.
'''
    },
    'complex': {
        'title': 'Create Todo List CLI',
        'description': '''Create a command-line todo list application with:

1. Add tasks (title, description, priority)
2. List all tasks
3. Mark tasks as complete
4. Delete tasks
5. Persist data to JSON file

Create:
- todo.py (main application)
- test_todo.py (unit tests)
- README.md (usage instructions)

Use argparse for CLI interface.
'''
    }
}


def check_prerequisites():
    """Check that all prerequisites are available."""
    import subprocess
    import urllib.request

    logger.info("Checking prerequisites...")

    issues = []

    # Check Ollama (try both localhost and Windows host IP for WSL2)
    ollama_urls = ['http://localhost:11434/api/tags', 'http://172.29.144.1:11434/api/tags']
    ollama_working = False
    ollama_url = None

    for url in ollama_urls:
        try:
            response = urllib.request.urlopen(url, timeout=5)
            if response.status == 200:
                logger.info(f"✓ Ollama is running at {url.replace('/api/tags', '')}")
                ollama_working = True
                ollama_url = url.replace('/api/tags', '')
                break
        except Exception:
            continue

    if not ollama_working:
        issues.append("Ollama not accessible at localhost:11434 or 172.29.144.1:11434")

    # Check Claude Code CLI
    try:
        result = subprocess.run(['claude', '--version'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            logger.info(f"✓ Claude Code CLI: {result.stdout.strip()}")
        else:
            issues.append("Claude Code CLI not working")
    except FileNotFoundError:
        issues.append("Claude Code CLI not found (install with: npm install -g @anthropics/claude-code)")
    except Exception as e:
        issues.append(f"Claude Code CLI error: {e}")

    # Check Claude Code authentication (no API key needed!)
    # Claude Code CLI uses session-based auth from 'claude login'
    logger.info("✓ Claude Code uses session authentication (no API key needed)")

    # Check workspace directory
    workspace = Path('/tmp/obra_real_test/workspace')
    workspace.mkdir(parents=True, exist_ok=True)
    logger.info(f"✓ Workspace directory: {workspace}")

    if issues:
        logger.error("\n❌ Prerequisites check failed:")
        for issue in issues:
            logger.error(f"   - {issue}")
        return False

    logger.info("\n✅ All prerequisites met!\n")
    return True


def main():
    parser = argparse.ArgumentParser(description='Test real Obra orchestration')
    parser.add_argument(
        '--task-type',
        choices=['simple', 'calculator', 'complex'],
        default='simple',
        help='Type of task to test (default: simple)'
    )
    parser.add_argument(
        '--max-iterations',
        type=int,
        default=5,
        help='Maximum iterations (default: 5)'
    )
    parser.add_argument(
        '--skip-prereq-check',
        action='store_true',
        help='Skip prerequisite check'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info("="*80)
    logger.info("OBRA REAL ORCHESTRATION TEST")
    logger.info("="*80)
    logger.info(f"Task Type: {args.task_type}")
    logger.info(f"Max Iterations: {args.max_iterations}")
    logger.info(f"Time: {datetime.now().isoformat()}")
    logger.info("="*80)
    logger.info("")

    # Check prerequisites
    if not args.skip_prereq_check:
        if not check_prerequisites():
            logger.error("Please fix prerequisites before running test")
            return 1

    # Load configuration
    logger.info("Loading configuration...")
    config_path = 'config/real_agent_config.yaml'

    if not Path(config_path).exists():
        logger.error(f"Configuration file not found: {config_path}")
        logger.info("Creating configuration file...")

        # Create configuration
        # Use Windows host IP for WSL2, localhost otherwise
        import urllib.request
        ollama_url = "http://localhost:11434"
        try:
            urllib.request.urlopen('http://172.29.144.1:11434/api/tags', timeout=2)
            ollama_url = "http://172.29.144.1:11434"
        except:
            pass

        config_content = f"""llm:
  type: ollama
  model: qwen2.5-coder:32b
  api_url: {ollama_url}
  temperature: 0.7
  timeout: 30
  max_tokens: 4096

agent:
  type: claude_code_local
  timeout: 120
  max_retries: 3

  local:
    command: claude
    workspace_dir: /tmp/obra_real_test/workspace
    timeout_ready: 30
    timeout_response: 120

database:
  url: sqlite:///data/orchestrator_real_test.db
  echo: false

orchestration:
  max_iterations: 10
  iteration_timeout: 300

breakpoints:
  enabled: true
  triggers:
    low_confidence:
      enabled: true
      threshold: 30
    quality_too_low:
      enabled: true
      threshold: 50

validation:
  quality:
    enabled: true
    threshold: 70

confidence:
  threshold: 50

logging:
  level: INFO
  file: logs/real_agent_test.log
"""
        Path(config_path).parent.mkdir(parents=True, exist_ok=True)
        Path(config_path).write_text(config_content)
        logger.info(f"✓ Created: {config_path}")

    try:
        config = Config.load(config_path)
        logger.info("✓ Configuration loaded")
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        return 1

    # Create orchestrator
    logger.info("\n" + "="*80)
    logger.info("INITIALIZING ORCHESTRATOR")
    logger.info("="*80)

    try:
        orch = Orchestrator(config=config)
        logger.info("✓ Orchestrator created")

        logger.info("Initializing components...")
        orch.initialize()
        logger.info("✓ All components initialized")

    except Exception as e:
        logger.error(f"❌ Orchestrator initialization failed: {e}", exc_info=True)
        return 1

    # Create project
    logger.info("\n" + "="*80)
    logger.info("CREATING PROJECT AND TASK")
    logger.info("="*80)

    try:
        project = orch.state_manager.create_project(
            name="Real Orchestration Test",
            description=f"Testing real orchestration with {args.task_type} task",
            working_dir="/tmp/obra_real_test/workspace"
        )
        logger.info(f"✓ Project created: ID={project.id}, Name='{project.project_name}'")

        # Get task definition
        task_def = TASKS[args.task_type]

        task = orch.state_manager.create_task(
            project_id=project.id,
            task_data={
                'title': task_def['title'],
                'description': task_def['description']
            }
        )
        logger.info(f"✓ Task created: ID={task.id}, Title='{task.title}'")

    except Exception as e:
        logger.error(f"❌ Project/task creation failed: {e}", exc_info=True)
        return 1

    # Execute task
    logger.info("\n" + "="*80)
    logger.info("EXECUTING TASK")
    logger.info("="*80)
    logger.info(f"Task ID: {task.id}")
    logger.info(f"Title: {task.title}")
    logger.info(f"Max Iterations: {args.max_iterations}")
    logger.info("="*80)
    logger.info("")

    try:
        logger.info("Starting task execution...")
        logger.info("(This may take several minutes depending on task complexity)")
        logger.info("")

        result = orch.execute_task(task.id, max_iterations=args.max_iterations)

        logger.info("\n" + "="*80)
        logger.info("EXECUTION RESULTS")
        logger.info("="*80)
        logger.info(f"Status: {result['status']}")
        logger.info(f"Iterations: {result['iterations']}")

        if 'quality_score' in result:
            logger.info(f"Quality Score: {result['quality_score']:.2f}/100")
        if 'confidence' in result:
            logger.info(f"Confidence: {result['confidence']:.2f}/100")
        if 'response' in result:
            logger.info(f"Response Length: {len(result['response'])} characters")

        # Show generated files
        workspace = Path('/tmp/obra_real_test/workspace')
        files = list(workspace.glob('**/*.py'))
        if files:
            logger.info("\nGenerated Files:")
            for f in files:
                logger.info(f"  - {f.relative_to(workspace)}")

        logger.info("="*80)

        # Determine success
        if result['status'] == 'completed':
            logger.info("\n✅ TEST PASSED - Task completed successfully!")

            # Run tests if they exist
            test_files = list(workspace.glob('test_*.py'))
            if test_files:
                logger.info("\nRunning generated tests...")
                import subprocess
                for test_file in test_files:
                    logger.info(f"Testing: {test_file.name}")
                    result = subprocess.run(
                        ['python', '-m', 'pytest', str(test_file), '-v'],
                        cwd=str(workspace),
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    if result.returncode == 0:
                        logger.info(f"  ✓ Tests passed!")
                    else:
                        logger.warning(f"  ⚠ Tests failed")
                        logger.debug(result.stdout)

            return 0

        elif result['status'] == 'escalated':
            logger.warning("\n⚠️ TEST INCOMPLETE - Task escalated for human review")
            logger.info(f"Reason: {result.get('reason', 'Unknown')}")
            return 1

        else:
            logger.warning(f"\n⚠️ TEST INCOMPLETE - Status: {result['status']}")
            return 1

    except KeyboardInterrupt:
        logger.info("\n\n⚠️ Test interrupted by user")
        return 130

    except Exception as e:
        logger.error(f"\n❌ TEST FAILED: {e}", exc_info=True)
        return 1

    finally:
        # Cleanup
        logger.info("\nCleaning up...")
        if hasattr(orch, 'agent') and orch.agent:
            try:
                orch.agent.cleanup()
                logger.info("✓ Agent cleaned up")
            except Exception as e:
                logger.warning(f"Agent cleanup error: {e}")


if __name__ == '__main__':
    sys.exit(main())
