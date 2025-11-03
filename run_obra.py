#!/usr/bin/env python3
"""
Obra Quick Runner - Send your own prompt to Claude Code via Obra orchestration.

Usage:
    python run_obra.py

Edit the USER_PROMPT variable below to send your own task to Obra.
"""

import sys
import json
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.agents.claude_code_local import ClaudeCodeLocalAgent
from src.llm.local_interface import LocalLLMInterface


# ============================================================================
# ✏️ EDIT YOUR PROMPT HERE
# ============================================================================

USER_PROMPT = """
Create a Python file called 'hello.py' that:
1. Defines a function greet(name) that returns a greeting
2. Includes a main block that demonstrates the function
3. Has proper docstrings
"""

WORKSPACE = '/tmp/obra-quick-run'

# ============================================================================


def main():
    """Execute Obra orchestration with user prompt."""

    start_time = time.time()
    conversation = []

    print("\n" + "=" * 100)
    print("OBRA ORCHESTRATION - QUICK RUN")
    print("=" * 100)
    print(f"\n📋 Your Task:\n{USER_PROMPT.strip()}")
    print(f"\n📁 Workspace: {WORKSPACE}\n")

    # Initialize Claude Code Agent
    print("[1/5] Initializing Claude Code agent (headless + dangerous mode)...")
    agent = ClaudeCodeLocalAgent()
    agent.initialize({
        'workspace_path': WORKSPACE,
        'bypass_permissions': True,
        'response_timeout': 120,
        'use_session_persistence': False
    })
    print("✓ Claude Code ready\n")

    conversation.append({
        'timestamp': time.time() - start_time,
        'actor': 'USER',
        'content': USER_PROMPT.strip()
    })

    # Initialize Qwen
    print("[2/5] Initializing Obra (Qwen LLM)...")
    qwen = LocalLLMInterface()
    qwen.initialize({
        'endpoint': 'http://172.29.144.1:11434',
        'model': 'qwen2.5-coder:32b',
        'temperature': 0.7,
        'timeout': 30
    })
    print(f"✓ Obra ready: {qwen.model}\n")

    # Enhance prompt
    print("[3/5] Obra enhancing your prompt...")
    enhancement_prompt = f"""You are Obra, an AI orchestration system. A user requested:

"{USER_PROMPT.strip()}"

Validate this is reasonable and add any clarifications needed for Claude Code.
Respond with just the enhanced prompt (no preamble)."""

    start = time.time()
    try:
        enhanced = qwen.generate(enhancement_prompt)
        duration = time.time() - start
        print(f"✓ Enhanced ({duration:.1f}s): {enhanced[:100]}...\n")
        conversation.append({
            'timestamp': time.time() - start_time,
            'actor': 'OBRA',
            'action': 'enhance',
            'output': enhanced,
            'duration': duration
        })
    except Exception as e:
        print(f"⚠️ Enhancement failed: {e}, using original\n")
        enhanced = USER_PROMPT.strip()
        conversation.append({
            'timestamp': time.time() - start_time,
            'actor': 'OBRA',
            'action': 'enhance_failed',
            'error': str(e)
        })

    # Execute with Claude
    print("[4/5] Claude Code executing task...")
    start = time.time()
    try:
        response = agent.send_prompt(enhanced)
        duration = time.time() - start
        print(f"✓ Task complete ({duration:.1f}s)\n")
        conversation.append({
            'timestamp': time.time() - start_time,
            'actor': 'CLAUDE',
            'action': 'execute',
            'output': response,
            'duration': duration
        })
    except Exception as e:
        print(f"✗ Claude failed: {e}")
        agent.cleanup()
        return 1

    # Validate
    print("[5/5] Obra validating results...")
    validation_prompt = f"""You are Obra. Claude was asked to:
"{USER_PROMPT.strip()}"

Claude responded:
"{response}"

Evaluate:
COMPLETED: [yes/no]
QUALITY: [0.0-1.0]
ISSUES: [list or "none"]
SUMMARY: [brief assessment]"""

    start = time.time()
    try:
        validation = qwen.generate(validation_prompt)
        duration = time.time() - start
        print(f"✓ Validated ({duration:.1f}s)\n")
        conversation.append({
            'timestamp': time.time() - start_time,
            'actor': 'OBRA',
            'action': 'validate',
            'output': validation,
            'duration': duration
        })
    except Exception as e:
        print(f"⚠️ Validation failed: {e}\n")
        validation = None
        conversation.append({
            'timestamp': time.time() - start_time,
            'actor': 'OBRA',
            'action': 'validate_failed',
            'error': str(e)
        })

    # Display results
    print("=" * 100)
    print("RESULTS")
    print("=" * 100)
    print("\n📝 Claude's Response:")
    print("-" * 100)
    print(response)
    print("-" * 100)

    if validation:
        print("\n✅ Obra's Validation:")
        print("-" * 100)
        print(validation)
        print("-" * 100)

    # Show workspace files
    workspace_path = Path(WORKSPACE)
    if workspace_path.exists():
        files = [f for f in workspace_path.rglob('*') if f.is_file()]
        if files:
            print(f"\n📂 Files Created ({len(files)}):")
            for f in sorted(files):
                rel = f.relative_to(workspace_path)
                size = f.stat().st_size
                print(f"  - {rel} ({size} bytes)")

    # Save log
    total = time.time() - start_time
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f'obra_quick_{int(time.time())}.json'

    with open(log_file, 'w') as f:
        json.dump({
            'start_time': start_time,
            'total_duration': total,
            'user_prompt': USER_PROMPT.strip(),
            'workspace': WORKSPACE,
            'conversation': conversation
        }, f, indent=2)

    print(f"\n📄 Log: {log_file}")
    print(f"⏱️ Total: {total:.1f}s")

    print("\n" + "=" * 100)
    print("✅ OBRA ORCHESTRATION COMPLETE!")
    print("=" * 100)
    print("\n💡 Tip: Edit USER_PROMPT in this file to send your own tasks\n")

    agent.cleanup()
    return 0


if __name__ == '__main__':
    sys.exit(main())
