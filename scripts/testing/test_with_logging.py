#!/usr/bin/env python3
"""Test with detailed logging to trace LLM usage."""

import sys
import logging

# Enable detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(name)s - %(levelname)s - %(message)s'
)

sys.path.insert(0, '/home/omarwsl/projects/claude_code_orchestrator')

# Patch the LLMPlugin.generate method to log what model is being used
from src.plugins.base import LLMPlugin
original_generate = LLMPlugin.generate

def logged_generate(self, prompt, **kwargs):
    """Log which LLM is generating."""
    print(f"\n🔴 LLM.generate() called on {type(self).__name__}")
    if hasattr(self, 'model'):
        print(f"   Model: {self.model}")
    if hasattr(self, 'endpoint'):
        print(f"   Endpoint: {self.endpoint}")
    if hasattr(self, 'codex_command'):
        print(f"   Codex command: {self.codex_command}")
    print(f"   Prompt (first 100 chars): {prompt[:100]}")
    return original_generate(self, prompt, **kwargs)

LLMPlugin.generate = logged_generate

# Now import and run
from src.core.config import Config
from src.core.state import StateManager
from src.orchestrator import Orchestrator
from src.interactive import InteractiveMode

config = Config.load('config/config.yaml')

print("\n" + "=" * 80)
print("Creating and running InteractiveMode...")
print("=" * 80)

interactive = InteractiveMode(config)

# Run() initializes everything including NL processor
# But we'll manually call the initialization to avoid entering the loop
try:
    db_url = config.get('database.url', 'sqlite:///orchestrator.db')
    interactive.state_manager = StateManager.get_instance(db_url)
    interactive.orchestrator = Orchestrator(config=config)
    interactive.orchestrator.initialize()
    interactive._initialize_nl_processor()
except Exception as e:
    print(f"Initialization error: {e}")
    import traceback
    traceback.print_exc()

if interactive.nl_processor:
    print("\n✓ NL processor initialized")
    print(f"  LLM plugin type: {type(interactive.nl_processor.llm_plugin).__name__}")

    # Try to process a command
    print("\nProcessing: 'list all current projects'")
    print("-" * 80)
    try:
        parsed_intent = interactive.nl_processor.process("list all current projects")
        print(f"\n✓ Success: {parsed_intent.intent_type}")
    except Exception as e:
        print(f"\n✗ Failed: {e}")
        import traceback
        traceback.print_exc()
else:
    print("\n✗ NL processor NOT initialized")
