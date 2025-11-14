#!/usr/bin/env python3
"""Test the exact flow that happens in interactive mode."""

import sys
sys.path.insert(0, '/home/omarwsl/projects/claude_code_orchestrator')

from src.core.config import Config
from src.core.state import StateManager
from src.orchestrator import Orchestrator
from src.interactive import InteractiveMode

# Load config
config = Config.load('config/config.yaml')
print(f"✓ Config loaded: llm.type = {config.get('llm.type')}\n")

# Create orchestrator (exactly like InteractiveMode does)
orchestrator = Orchestrator(config=config)
print(f"✓ Orchestrator created")
print(f"  Before initialize: llm_interface = {orchestrator.llm_interface}")

orchestrator.initialize()
print(f"  After initialize: llm_interface = {type(orchestrator.llm_interface).__name__ if orchestrator.llm_interface else 'None'}")

if orchestrator.llm_interface:
    print(f"  LLM type: {type(orchestrator.llm_interface).__name__}")
    if hasattr(orchestrator.llm_interface, 'model'):
        print(f"  LLM model: {orchestrator.llm_interface.model}")
    if hasattr(orchestrator.llm_interface, 'endpoint'):
        print(f"  LLM endpoint: {orchestrator.llm_interface.endpoint}")
print()

# Create interactive mode (exactly like CLI does)
interactive = InteractiveMode(orchestrator)
print(f"✓ InteractiveMode created")

# Check if NL processor was initialized
if interactive.nl_processor:
    print(f"  NL processor exists: Yes")
    if hasattr(interactive.nl_processor, 'llm_plugin'):
        nl_llm = interactive.nl_processor.llm_plugin
        print(f"  NL processor LLM: {type(nl_llm).__name__}")
        if hasattr(nl_llm, 'model'):
            print(f"  NL LLM model: {nl_llm.model}")
        if hasattr(nl_llm, 'endpoint'):
            print(f"  NL LLM endpoint: {nl_llm.endpoint}")
else:
    print(f"  NL processor exists: No")
print()

# Now try to process a natural language command
if interactive.nl_processor:
    print("Testing natural language command: 'list all current projects'")
    print("-" * 80)

    try:
        parsed_intent = interactive.nl_processor.process("list all current projects")
        print(f"✓ Processing succeeded!")
        print(f"  Intent type: {parsed_intent.intent_type}")
        print(f"  Confidence: {parsed_intent.confidence:.2f}")
        if parsed_intent.operation_context:
            print(f"  Operation: {parsed_intent.operation_context.operation}")
    except Exception as e:
        print(f"✗ Processing failed: {e}")
        import traceback
        traceback.print_exc()
else:
    print("⚠ Cannot test - NL processor not initialized")
