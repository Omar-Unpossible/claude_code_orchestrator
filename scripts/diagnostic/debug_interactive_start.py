#!/usr/bin/env python3
"""Debug script to trace LLM initialization in interactive mode."""

import sys
import logging

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Patch LLMRegistry.get to log what's being requested
import src.llm  # Trigger registration
from src.plugins.registry import LLMRegistry

original_get = LLMRegistry.get

def logged_get(llm_type: str):
    """Wrapper to log LLM requests."""
    print(f"\n🔍 LLMRegistry.get() called with: {llm_type}")
    result = original_get(llm_type)
    print(f"   → Returned: {result}")
    return result

LLMRegistry.get = logged_get

# Now start interactive mode
print("=" * 80)
print("Starting Interactive Mode with detailed LLM tracking...")
print("=" * 80)
print()

from src.cli import main
sys.argv = ['src.cli', 'interactive']

try:
    main()
except KeyboardInterrupt:
    print("\nInterrupted by user")
except Exception as e:
    print(f"\nError: {e}")
    import traceback
    traceback.print_exc()
