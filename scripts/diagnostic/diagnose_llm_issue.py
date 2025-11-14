#!/usr/bin/env python3
"""Comprehensive LLM initialization diagnostic."""

import sys
import os

# Ensure venv is activated
venv_python = '/home/omarwsl/projects/claude_code_orchestrator/venv/bin/python3'
if sys.executable != venv_python:
    print(f"❌ ERROR: Not using venv Python!")
    print(f"   Current: {sys.executable}")
    print(f"   Expected: {venv_python}")
    print(f"\n   Please run: source venv/bin/activate")
    sys.exit(1)

print(f"✓ Using venv Python: {sys.executable}\n")

sys.path.insert(0, '/home/omarwsl/projects/claude_code_orchestrator')

# Monkey-patch to track LLM instantiations
print("=" * 80)
print("TRACKING ALL LLM PLUGIN INSTANTIATIONS")
print("=" * 80)

llm_instances = []

def track_llm_init(original_init):
    """Wrapper to track LLM.__init__ calls."""
    def wrapper(self, *args, **kwargs):
        instance_info = {
            'class': type(self).__name__,
            'module': type(self).__module__
        }
        llm_instances.append(instance_info)
        print(f"\n🔴 LLM Plugin instantiated: {instance_info['class']}")

        # Show call stack
        import traceback
        stack = traceback.extract_stack()
        print("   Called from:")
        for frame in stack[-6:-1]:  # Show last 5 frames
            print(f"     {frame.filename}:{frame.lineno} in {frame.name}")

        return original_init(self, *args, **kwargs)
    return wrapper

# Import and patch
import src.llm
from src.llm.local_interface import LocalLLMInterface
from src.llm.openai_codex_interface import OpenAICodexLLMPlugin

LocalLLMInterface.__init__ = track_llm_init(LocalLLMInterface.__init__)
OpenAICodexLLMPlugin.__init__ = track_llm_init(OpenAICodexLLMPlugin.__init__)

# Now run the normal initialization
print("\n" + "=" * 80)
print("INITIALIZING INTERACTIVE MODE")
print("=" * 80 + "\n")

from src.core.config import Config
from src.core.state import StateManager
from src.orchestrator import Orchestrator
from src.interactive import InteractiveMode

# Load config
config = Config.load('config/config.yaml')
print(f"\n✓ Config loaded")
print(f"   llm.type: {config.get('llm.type')}")
print(f"   llm.model: {config.get('llm.model')}")
print(f"   llm.api_url: {config.get('llm.api_url')}")

# Create orchestrator
orchestrator = Orchestrator(config=config)
print(f"\n✓ Orchestrator created")
if orchestrator.llm_interface:
    print(f"   Orchestrator LLM: {type(orchestrator.llm_interface).__name__}")
else:
    print(f"   Orchestrator LLM: None")

# Create interactive mode
interactive = InteractiveMode(orchestrator, config)
print(f"\n✓ Interactive mode created")

# Check NL processor
if interactive.nl_processor:
    print(f"   NL Processor exists: Yes")
    if hasattr(interactive.nl_processor, 'llm_plugin'):
        print(f"   NL Processor LLM: {type(interactive.nl_processor.llm_plugin).__name__}")
else:
    print(f"   NL Processor exists: No")

print("\n" + "=" * 80)
print("SUMMARY OF LLM INSTANCES CREATED")
print("=" * 80)

if llm_instances:
    for i, instance in enumerate(llm_instances, 1):
        print(f"{i}. {instance['class']} (from {instance['module']})")
else:
    print("⚠ No LLM instances were created!")

print("\n" + "=" * 80)
print("DIAGNOSTIC COMPLETE")
print("=" * 80)

# Now test a simple classification
if interactive.nl_processor:
    print("\nTesting NL command classification...")
    try:
        parsed_intent = interactive.nl_processor.process("list all current projects")
        print(f"✓ Classification succeeded: {parsed_intent.intent_type}")
    except Exception as e:
        print(f"✗ Classification failed: {e}")
        import traceback
        traceback.print_exc()
