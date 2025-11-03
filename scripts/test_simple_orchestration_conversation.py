#!/usr/bin/env python3
"""Simple demonstration of Obra ↔ Claude conversation cycle.

This shows the full conversation between Obra (using Qwen) and Claude Code.
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.claude_code_local import ClaudeCodeLocalAgent
from src.llm.local_interface import LocalLLMInterface


def print_header(text):
    """Print a nice header."""
    print("\n" + "=" * 100)
    print(f"{text}")
    print("=" * 100)


def save_conversation(conversation, filepath):
    """Save conversation to JSON file."""
    with open(filepath, 'w') as f:
        json.dump(conversation, f, indent=2)
    print(f"\n✓ Full conversation saved to: {filepath}")


def main():
    """Run simple orchestration conversation test."""

    conversation_log = []
    start_time = time.time()

    print_header("OBRA ↔ CLAUDE CONVERSATION DEMONSTRATION")

    print("\nThis test shows the full conversation cycle:")
    print("  1. USER provides a task")
    print("  2. OBRA (Qwen LLM) enhances/validates the prompt")
    print("  3. CLAUDE CODE executes the task")
    print("  4. OBRA (Qwen LLM) validates Claude's response")
    print("  5. Full conversation history is logged")

    # Initialize components
    print_header("INITIALIZING COMPONENTS")

    # 1. Initialize Claude Code agent (headless + dangerous mode)
    agent = ClaudeCodeLocalAgent()
    agent.initialize({
        'workspace_path': '/tmp/obra_conversation_test',
        'bypass_permissions': True,
        'response_timeout': 120,
        'use_session_persistence': False
    })
    print("✓ Claude Code Agent initialized (headless + dangerous mode)")

    # 2. Initialize Qwen LLM
    qwen = LocalLLMInterface()
    qwen.initialize({
        'endpoint': 'http://172.29.144.1:11434',
        'model': 'qwen2.5-coder:32b',
        'temperature': 0.7,
        'timeout': 30
    })
    print(f"✓ Qwen LLM initialized: {qwen.endpoint}")
    print(f"  Model: {qwen.model}")

    # ========================================================================
    # ITERATION 1: Simple Python file creation
    # ========================================================================

    print_header("ITERATION 1: Create Python File")

    # Step 1: User provides task
    user_task = "Create a Python file called 'demo.py' that defines a function 'greet(name)' which returns a greeting message."

    entry = {
        'timestamp': time.time() - start_time,
        'step': 1,
        'actor': 'USER',
        'action': 'Provide Task',
        'content': user_task
    }
    conversation_log.append(entry)

    print(f"\n[USER → OBRA] Task:")
    print(f"  {user_task}")

    # Step 2: Obra (Qwen) enhances the prompt
    print(f"\n[OBRA] Using Qwen to validate/enhance prompt...")

    enhancement_prompt = f"""You are Obra, an AI orchestration system. A user has requested:

"{user_task}"

Your job is to:
1. Validate this is a reasonable task
2. Add any necessary clarifications for Claude Code
3. Return an enhanced prompt with clear instructions

Respond with just the enhanced prompt (no preamble)."""

    qwen_start = time.time()
    try:
        enhanced_prompt = qwen.generate(enhancement_prompt)
        qwen_duration = time.time() - qwen_start

        entry = {
            'timestamp': time.time() - start_time,
            'step': 2,
            'actor': 'OBRA (Qwen)',
            'action': 'Enhance Prompt',
            'input': enhancement_prompt[:200] + '...',
            'output': enhanced_prompt,
            'duration': qwen_duration
        }
        conversation_log.append(entry)

        print(f"\n[OBRA (Qwen)] Enhanced prompt ({qwen_duration:.1f}s):")
        print(f"  {enhanced_prompt[:200]}...")

    except Exception as e:
        print(f"\n⚠️ Qwen enhancement failed: {e}")
        print("  Using original prompt...")
        enhanced_prompt = user_task
        entry = {
            'timestamp': time.time() - start_time,
            'step': 2,
            'actor': 'OBRA',
            'action': 'Enhance Prompt (FAILED)',
            'error': str(e)
        }
        conversation_log.append(entry)

    # Step 3: Send to Claude Code
    print(f"\n[OBRA → CLAUDE] Sending enhanced prompt...")

    # No need to add permission instructions - dangerous mode handles this at CLI level
    final_prompt = enhanced_prompt

    claude_start = time.time()
    try:
        claude_response = agent.send_prompt(final_prompt)
        claude_duration = time.time() - claude_start

        entry = {
            'timestamp': time.time() - start_time,
            'step': 3,
            'actor': 'CLAUDE CODE',
            'action': 'Execute Task',
            'input': final_prompt,
            'output': claude_response,
            'duration': claude_duration
        }
        conversation_log.append(entry)

        print(f"\n[CLAUDE → OBRA] Response received ({claude_duration:.1f}s):")
        print(f"  Length: {len(claude_response)} characters")
        print(f"  Preview: {claude_response[:300]}...")

    except Exception as e:
        print(f"\n✗ Claude Code failed: {e}")
        entry = {
            'timestamp': time.time() - start_time,
            'step': 3,
            'actor': 'CLAUDE CODE',
            'action': 'Execute Task (FAILED)',
            'error': str(e)
        }
        conversation_log.append(entry)
        agent.cleanup()
        return 1

    # Step 4: Obra (Qwen) validates the response
    print(f"\n[OBRA] Using Qwen to validate Claude's response...")

    validation_prompt = f"""You are Obra, an AI orchestration system. Claude Code was asked to:

"{user_task}"

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

        entry = {
            'timestamp': time.time() - start_time,
            'step': 4,
            'actor': 'OBRA (Qwen)',
            'action': 'Validate Response',
            'input': validation_prompt[:200] + '...',
            'output': validation_response,
            'duration': qwen_duration
        }
        conversation_log.append(entry)

        print(f"\n[OBRA (Qwen)] Validation result ({qwen_duration:.1f}s):")
        print(f"  {validation_response}")

    except Exception as e:
        print(f"\n⚠️ Qwen validation failed: {e}")
        entry = {
            'timestamp': time.time() - start_time,
            'step': 4,
            'actor': 'OBRA (Qwen)',
            'action': 'Validate Response (FAILED)',
            'error': str(e)
        }
        conversation_log.append(entry)

    # Verify the file was created
    print_header("VERIFYING RESULTS")

    workspace = Path('/tmp/obra_conversation_test')
    demo_file = workspace / 'demo.py'

    if demo_file.exists():
        content = demo_file.read_text()
        print(f"\n✓ File created: {demo_file}")
        print(f"  Size: {len(content)} bytes")
        print(f"\nContent:")
        print("-" * 80)
        print(content)
        print("-" * 80)

        entry = {
            'timestamp': time.time() - start_time,
            'step': 5,
            'actor': 'SYSTEM',
            'action': 'Verify File',
            'result': 'SUCCESS',
            'file': str(demo_file),
            'size': len(content)
        }
        conversation_log.append(entry)
    else:
        print(f"\n✗ File not found: {demo_file}")

        entry = {
            'timestamp': time.time() - start_time,
            'step': 5,
            'actor': 'SYSTEM',
            'action': 'Verify File',
            'result': 'FAILED',
            'file': str(demo_file)
        }
        conversation_log.append(entry)

    # Save conversation log
    print_header("CONVERSATION SUMMARY")

    total_duration = time.time() - start_time

    print(f"\nTotal duration: {total_duration:.1f}s")
    print(f"Total conversation steps: {len(conversation_log)}")

    print("\n\nConversation Flow:")
    for entry in conversation_log:
        step = entry.get('step', '?')
        actor = entry['actor']
        action = entry['action']
        duration = entry.get('duration', '')
        duration_str = f" ({duration:.1f}s)" if duration else ""

        print(f"  {step}. [{entry['timestamp']:5.1f}s] {actor:20s} → {action}{duration_str}")

    # Save to file
    log_file = Path(__file__).parent.parent / 'logs' / f'conversation_{int(time.time())}.json'
    log_file.parent.mkdir(exist_ok=True)
    save_conversation({
        'start_time': start_time,
        'total_duration': total_duration,
        'conversation': conversation_log
    }, log_file)

    print("\n" + "=" * 100)
    print("✅ OBRA ↔ CLAUDE CONVERSATION CYCLE COMPLETE!")
    print("=" * 100)

    print("\nThis demonstrates:")
    print("  ✓ Obra (Qwen) generating/enhancing prompts")
    print("  ✓ Claude Code executing tasks")
    print("  ✓ Obra (Qwen) validating responses")
    print("  ✓ Full conversation history logged")

    print(f"\n📄 Full conversation JSON: {log_file}")

    # Cleanup
    agent.cleanup()

    return 0


if __name__ == '__main__':
    sys.exit(main())
