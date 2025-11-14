#!/usr/bin/env python3
"""Test realistic orchestration workflow with natural delays.

This test simulates Obra's actual workflow with validation,
quality checking, and decision-making between Claude calls.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.claude_code_local import ClaudeCodeLocalAgent


def simulate_validation(response: str) -> float:
    """Simulate response validation (instant in reality)."""
    time.sleep(0.1)  # Validation overhead
    return 1.0  # Valid


def simulate_quality_check(response: str) -> float:
    """Simulate quality check with local LLM (5-10s in reality)."""
    print("  [QWEN] Checking quality...")
    time.sleep(2.0)  # Simulate LLM call
    return 0.85  # Quality score


def simulate_confidence_scoring(response: str) -> float:
    """Simulate confidence scoring (2-5s in reality)."""
    print("  [OBRA] Calculating confidence...")
    time.sleep(1.0)  # Heuristic + ensemble
    return 0.75  # Confidence score


def simulate_decision(quality: float, confidence: float) -> str:
    """Simulate decision engine (instant)."""
    time.sleep(0.1)
    if quality > 0.7 and confidence > 0.5:
        return "PROCEED"
    return "RETRY"


def main():
    print("=" * 70)
    print("REALISTIC ORCHESTRATION WORKFLOW TEST")
    print("=" * 70)
    print("Simulating Obra's actual workflow with natural delays\n")

    agent = ClaudeCodeLocalAgent()
    agent.initialize({'workspace_path': '/tmp/realistic-workflow'})

    print(f"Session ID: {agent.session_id}")
    print(f"Iterations: 3")
    print()

    iterations = [
        "What is the capital of France? Just the city name.",
        "What is 15 times 8? Just the number.",
        "What color is the sky on a clear day? One word.",
    ]

    results = []

    for i, prompt in enumerate(iterations, 1):
        print("=" * 70)
        print(f"ITERATION {i}/{len(iterations)}")
        print("=" * 70)

        # Step 1: Build context (instant, but simulate)
        print(f"\n[OBRA] Building context...")
        time.sleep(0.1)

        # Step 2: Send to Claude
        print(f"[OBRA→CLAUDE] Sending prompt: {prompt}")
        start_iteration = time.time()
        start_claude = time.time()

        try:
            response = agent.send_prompt(prompt)
            claude_time = time.time() - start_claude

            print(f"[CLAUDE→OBRA] Response received ({claude_time:.1f}s): {response}")

            # Step 3: Validate response
            print("[OBRA] Validating response...")
            valid = simulate_validation(response)

            # Step 4: Quality check (expensive - local LLM)
            quality = simulate_quality_check(response)
            print(f"  Quality score: {quality:.2f}")

            # Step 5: Confidence scoring
            confidence = simulate_confidence_scoring(response)
            print(f"  Confidence: {confidence:.2f}")

            # Step 6: Decision
            print("[OBRA] Making decision...")
            decision = simulate_decision(quality, confidence)
            print(f"  Decision: {decision}")

            # Step 7: State management
            print("[OBRA] Updating state...")
            time.sleep(0.1)

            iteration_time = time.time() - start_iteration

            results.append({
                'iteration': i,
                'success': True,
                'claude_time': claude_time,
                'total_time': iteration_time,
                'decision': decision
            })

            print(f"\n✓ Iteration {i} complete ({iteration_time:.1f}s total)")
            print(f"  Time between Claude calls: {iteration_time:.1f}s")

        except Exception as e:
            iteration_time = time.time() - start_iteration

            results.append({
                'iteration': i,
                'success': False,
                'error': str(e),
                'total_time': iteration_time
            })

            print(f"\n✗ Iteration {i} failed: {e}")

        print()

    # Summary
    print("=" * 70)
    print("WORKFLOW RESULTS")
    print("=" * 70)

    successful = sum(1 for r in results if r['success'])

    print(f"\nSuccess rate: {successful}/{len(results)} ({successful/len(results)*100:.0f}%)")

    if successful > 0:
        avg_claude = sum(r.get('claude_time', 0) for r in results if r['success']) / successful
        avg_total = sum(r.get('total_time', 0) for r in results if r['success']) / successful

        print(f"Average Claude time: {avg_claude:.1f}s")
        print(f"Average iteration time: {avg_total:.1f}s")
        print(f"Average delay between calls: {avg_total:.1f}s")

    print("\n" + "=" * 70)

    if successful == len(results):
        print("✅ PERFECT - All iterations successful!")
        print("Session reuse works with realistic orchestration delays")
    else:
        print(f"⚠️ {len(results) - successful} iteration(s) failed")

    print("=" * 70)

    agent.cleanup()

    return 0 if successful == len(results) else 1


if __name__ == '__main__':
    sys.exit(main())
