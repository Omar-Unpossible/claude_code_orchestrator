#!/usr/bin/env python3
"""
Obra Iterative Runner - Multi-turn orchestration with automatic improvement.

This version iterates up to MAX_ITERATIONS, building context from previous
attempts and using Obra (Qwen) to validate and guide improvements.

Usage:
    python run_obra_iterative.py

Edit the USER_PROMPT variable below to send your own complex task to Obra.
"""

import sys
import json
import time
from pathlib import Path
from typing import Dict, Any, List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.agents.claude_code_local import ClaudeCodeLocalAgent
from src.llm.local_interface import LocalLLMInterface


# ============================================================================
# ✏️ EDIT YOUR PROMPT HERE
# ============================================================================

USER_PROMPT = """
Build a command-line tool called 'csvtool' that processes CSV files. Requirements:

1. Core functionality:
   - Read CSV files
   - Filter rows based on column conditions
   - Sort by specified columns
   - Output results to new CSV or stdout

2. Architecture:
   - Main script: csvtool.py
   - Parser module: csv_parser.py
   - Filter module: csv_filter.py
   - Sorter module: csv_sorter.py

3. Command syntax:
   csvtool --file input.csv --filter "age>25" --sort name --output result.csv

4. Quality requirements:
   - Comprehensive error handling (file not found, invalid format, etc.)
   - Unit tests for each module (use pytest)
   - Integration test for end-to-end workflow
   - Proper docstrings and type hints
   - Handle edge cases (empty files, malformed CSV, etc.)

5. Test data:
   Create sample_data.csv with test data for demonstration
"""

WORKSPACE = '/tmp/obra-iterative-run'
MAX_ITERATIONS = 3
QUALITY_THRESHOLD = 0.75  # Minimum quality score to consider task complete

# ============================================================================


def parse_validation(validation_text: str) -> Dict[str, Any]:
    """Parse Obra's validation response into structured data.

    Args:
        validation_text: Raw validation text from Obra

    Returns:
        Dict with parsed validation data
    """
    result = {
        'completed': False,
        'quality': 0.0,
        'issues': [],
        'summary': ''
    }

    lines = validation_text.strip().split('\n')
    for line in lines:
        line = line.strip()
        if line.startswith('COMPLETED:'):
            result['completed'] = 'yes' in line.lower()
        elif line.startswith('QUALITY:'):
            try:
                quality_str = line.split(':', 1)[1].strip()
                # Handle formats like "0.75" or "[0.75]"
                quality_str = quality_str.strip('[]')
                result['quality'] = float(quality_str)
            except (ValueError, IndexError):
                result['quality'] = 0.0
        elif line.startswith('ISSUES:'):
            issues_str = line.split(':', 1)[1].strip()
            if issues_str.lower() not in ['none', '[]', '["none"]']:
                result['issues'].append(issues_str)
        elif line.startswith('SUMMARY:'):
            result['summary'] = line.split(':', 1)[1].strip()

    return result


def build_iteration_context(history: List[Dict[str, Any]]) -> str:
    """Build context string from previous iterations.

    Args:
        history: List of previous iteration results

    Returns:
        Context string to prepend to next prompt
    """
    if not history:
        return ""

    context_parts = ["=== Context from Previous Iterations ===\n"]

    for i, iteration in enumerate(history, 1):
        context_parts.append(f"\n--- Iteration {i} ---")

        if iteration.get('validation'):
            val = iteration['validation']
            context_parts.append(f"Quality: {val['quality']:.2f}")
            if val['issues']:
                context_parts.append(f"Issues identified:")
                for issue in val['issues']:
                    context_parts.append(f"  - {issue}")
            if val['summary']:
                context_parts.append(f"Assessment: {val['summary']}")

        if iteration.get('response_preview'):
            context_parts.append(f"Response preview: {iteration['response_preview'][:200]}...")

    context_parts.append("\n=== End Context ===\n")
    context_parts.append("\nPlease address the issues identified above and continue the task.\n")

    return "\n".join(context_parts)


def main():
    """Execute Obra iterative orchestration with user prompt."""

    start_time = time.time()
    conversation = []
    iteration_history = []

    print("\n" + "=" * 100)
    print("OBRA ITERATIVE ORCHESTRATION")
    print("=" * 100)
    print(f"\n📋 Your Task:\n{USER_PROMPT.strip()}")
    print(f"\n📁 Workspace: {WORKSPACE}")
    print(f"🔄 Max Iterations: {MAX_ITERATIONS}")
    print(f"🎯 Quality Threshold: {QUALITY_THRESHOLD}")
    print()

    # Initialize Claude Code Agent
    print("[INIT] Initializing Claude Code agent (headless + dangerous mode)...")
    agent = ClaudeCodeLocalAgent()
    agent.initialize({
        'workspace_path': WORKSPACE,
        'bypass_permissions': True,
        'response_timeout': 180,  # Longer timeout for complex tasks
        'use_session_persistence': False
    })
    print("✓ Claude Code ready\n")

    conversation.append({
        'timestamp': time.time() - start_time,
        'actor': 'USER',
        'content': USER_PROMPT.strip()
    })

    # Initialize Qwen
    print("[INIT] Initializing Obra (Qwen LLM)...")
    qwen = LocalLLMInterface()
    qwen.initialize({
        'endpoint': 'http://172.29.144.1:11434',
        'model': 'qwen2.5-coder:32b',
        'temperature': 0.7,
        'timeout': 30
    })
    print(f"✓ Obra ready: {qwen.model}\n")

    # ========================================================================
    # ITERATION LOOP
    # ========================================================================

    current_prompt = USER_PROMPT.strip()
    task_completed = False

    for iteration in range(1, MAX_ITERATIONS + 1):
        print("\n" + "=" * 100)
        print(f"ITERATION {iteration}/{MAX_ITERATIONS}")
        print("=" * 100)
        print()

        iteration_start = time.time()

        # Build context from previous iterations
        if iteration_history:
            context = build_iteration_context(iteration_history)
            full_prompt = context + "\n" + current_prompt
            print(f"[{iteration}/5] Context built from {len(iteration_history)} previous iteration(s)")
        else:
            full_prompt = current_prompt
            print(f"[{iteration}/5] First iteration - no context yet")

        # Enhance prompt (first iteration only, or if significant changes)
        if iteration == 1:
            print(f"[{iteration}/5] Obra enhancing your prompt...")
            enhancement_prompt = f"""You are Obra, an AI orchestration system. A user requested:

"{current_prompt}"

This is iteration {iteration} of {MAX_ITERATIONS}. Validate this is reasonable and add any clarifications needed.
Respond with just the enhanced prompt (no preamble)."""

            start = time.time()
            try:
                enhanced = qwen.generate(enhancement_prompt)
                duration = time.time() - start
                print(f"✓ Enhanced ({duration:.1f}s)\n")
                full_prompt = enhanced
                conversation.append({
                    'timestamp': time.time() - start_time,
                    'iteration': iteration,
                    'actor': 'OBRA',
                    'action': 'enhance',
                    'output': enhanced,
                    'duration': duration
                })
            except Exception as e:
                print(f"⚠️ Enhancement failed: {e}, using original\n")
                conversation.append({
                    'timestamp': time.time() - start_time,
                    'iteration': iteration,
                    'actor': 'OBRA',
                    'action': 'enhance_failed',
                    'error': str(e)
                })

        # Execute with Claude
        print(f"[{iteration}/5] Claude Code executing task...")
        start = time.time()
        try:
            response = agent.send_prompt(full_prompt)
            duration = time.time() - start
            print(f"✓ Response received ({duration:.1f}s, {len(response)} chars)\n")
            conversation.append({
                'timestamp': time.time() - start_time,
                'iteration': iteration,
                'actor': 'CLAUDE',
                'action': 'execute',
                'output': response,
                'duration': duration
            })
        except Exception as e:
            print(f"✗ Claude failed: {e}")
            conversation.append({
                'timestamp': time.time() - start_time,
                'iteration': iteration,
                'actor': 'CLAUDE',
                'action': 'execute_failed',
                'error': str(e)
            })
            break

        # Validate with Obra
        print(f"[{iteration}/5] Obra validating results...")
        validation_prompt = f"""You are Obra, an AI orchestration system. This is iteration {iteration}/{MAX_ITERATIONS}.

Original task:
"{USER_PROMPT.strip()}"

Claude's response:
"{response[:2000]}..." (truncated)

Evaluate Claude's work:
1. Is the task fully completed? (all requirements met)
2. Quality score 0.0-1.0 based on:
   - Completeness (all files/modules created)
   - Code quality (error handling, tests, docstrings)
   - Correctness (logic appears sound)
3. Specific issues remaining (be specific about what's missing)

Respond in this exact format:
COMPLETED: [yes/no]
QUALITY: [0.0-1.0]
ISSUES: [list specific missing items or "none"]
SUMMARY: [brief assessment]"""

        start = time.time()
        try:
            validation_text = qwen.generate(validation_prompt)
            duration = time.time() - start
            validation = parse_validation(validation_text)

            print(f"✓ Validated ({duration:.1f}s)")
            print(f"  Completed: {validation['completed']}")
            print(f"  Quality: {validation['quality']:.2f}")
            if validation['issues']:
                print(f"  Issues: {', '.join(validation['issues'][:3])}")
            print()

            conversation.append({
                'timestamp': time.time() - start_time,
                'iteration': iteration,
                'actor': 'OBRA',
                'action': 'validate',
                'output': validation_text,
                'parsed': validation,
                'duration': duration
            })
        except Exception as e:
            print(f"⚠️ Validation failed: {e}\n")
            validation = {
                'completed': False,
                'quality': 0.0,
                'issues': [str(e)],
                'summary': 'Validation error'
            }
            conversation.append({
                'timestamp': time.time() - start_time,
                'iteration': iteration,
                'actor': 'OBRA',
                'action': 'validate_failed',
                'error': str(e)
            })

        # Save iteration result
        iteration_result = {
            'iteration': iteration,
            'prompt': full_prompt[:500] + '...',
            'response_preview': response[:300] + '...',
            'validation': validation,
            'duration': time.time() - iteration_start
        }
        iteration_history.append(iteration_result)

        # Decision making
        print(f"[{iteration}/5] Decision making...")

        if validation['quality'] >= QUALITY_THRESHOLD and validation['completed']:
            print(f"✓ PROCEED - Quality threshold met ({validation['quality']:.2f} >= {QUALITY_THRESHOLD})")
            print(f"✓ Task marked as completed!\n")
            task_completed = True
            break

        elif iteration < MAX_ITERATIONS:
            print(f"⚠️ RETRY - Quality {validation['quality']:.2f} < {QUALITY_THRESHOLD} or incomplete")
            print(f"  Continuing to iteration {iteration + 1}...\n")

            # Build feedback for next iteration
            feedback_parts = ["Previous attempt had issues:"]
            if validation['issues']:
                for issue in validation['issues']:
                    feedback_parts.append(f"- {issue}")
            else:
                feedback_parts.append(f"- Quality score {validation['quality']:.2f} is below threshold {QUALITY_THRESHOLD}")

            current_prompt = "\n".join(feedback_parts) + f"\n\nPlease address these issues and continue the task."

        else:
            print(f"⚠️ Max iterations reached - Quality {validation['quality']:.2f}")
            print(f"  Task incomplete but stopping.\n")

    # ========================================================================
    # RESULTS
    # ========================================================================

    print("\n" + "=" * 100)
    print("FINAL RESULTS")
    print("=" * 100)
    print()

    print(f"Status: {'✅ COMPLETED' if task_completed else '⚠️ INCOMPLETE'}")
    print(f"Iterations: {len(iteration_history)}/{MAX_ITERATIONS}")

    if iteration_history:
        final = iteration_history[-1]['validation']
        print(f"Final Quality: {final['quality']:.2f}")
        print(f"Final Completed: {final['completed']}")

    print()

    # Show iteration progression
    if len(iteration_history) > 1:
        print("Quality Progression:")
        for i, it in enumerate(iteration_history, 1):
            quality = it['validation']['quality']
            bar_length = int(quality * 40)
            bar = '█' * bar_length + '░' * (40 - bar_length)
            print(f"  Iteration {i}: [{bar}] {quality:.2f}")
        print()

    # Show latest response
    if iteration_history:
        print("Latest Claude Response:")
        print("-" * 100)
        print(response[:1000])
        if len(response) > 1000:
            print(f"\n... ({len(response) - 1000} more characters)")
        print("-" * 100)
        print()

    # Show workspace files
    workspace_path = Path(WORKSPACE)
    if workspace_path.exists():
        files = [f for f in workspace_path.rglob('*') if f.is_file()]
        if files:
            print(f"Files Created ({len(files)}):")
            for f in sorted(files):
                rel = f.relative_to(workspace_path)
                size = f.stat().st_size
                print(f"  - {rel} ({size} bytes)")
        print()

    # Save log
    total = time.time() - start_time
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f'obra_iterative_{int(time.time())}.json'

    with open(log_file, 'w') as f:
        json.dump({
            'start_time': start_time,
            'total_duration': total,
            'user_prompt': USER_PROMPT.strip(),
            'workspace': WORKSPACE,
            'max_iterations': MAX_ITERATIONS,
            'quality_threshold': QUALITY_THRESHOLD,
            'task_completed': task_completed,
            'iterations': iteration_history,
            'conversation': conversation
        }, f, indent=2)

    print(f"📄 Log: {log_file}")
    print(f"⏱️ Total: {total:.1f}s ({total/60:.1f} minutes)")

    print("\n" + "=" * 100)
    if task_completed:
        print("✅ OBRA ITERATIVE ORCHESTRATION COMPLETE - TASK FINISHED!")
    else:
        print("⚠️ OBRA ITERATIVE ORCHESTRATION COMPLETE - TASK INCOMPLETE")
        print(f"   (Reached {len(iteration_history)} iterations, quality: {iteration_history[-1]['validation']['quality']:.2f})")
    print("=" * 100)
    print()

    agent.cleanup()
    return 0 if task_completed else 1


if __name__ == '__main__':
    sys.exit(main())
