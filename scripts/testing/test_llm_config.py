#!/usr/bin/env python3
"""Test script to diagnose LLM configuration."""

import sys
sys.path.insert(0, '/home/omarwsl/projects/claude_code_orchestrator')

from src.core.config import Config
from src.plugins.registry import LLMRegistry

# Import LLM modules to trigger @register_llm decorators
import src.llm  # This registers LocalLLMInterface and OpenAICodexLLMPlugin

def main():
    print("=== LLM Configuration Diagnostic ===\n")

    # Load config
    config = Config.load('config/config.yaml')

    # Check what's in the config
    llm_type = config.get('llm.type', 'not set')
    llm_model = config.get('llm.model', 'not set')
    llm_url = config.get('llm.api_url', 'not set')

    print(f"Config file settings:")
    print(f"  llm.type: {llm_type}")
    print(f"  llm.model: {llm_model}")
    print(f"  llm.api_url: {llm_url}")
    print()

    # Check registered LLMs
    available_llms = LLMRegistry.list()
    print(f"Registered LLM providers: {available_llms}")
    print()

    # Try to get the configured LLM
    try:
        llm_class = LLMRegistry.get(llm_type)
        print(f"✓ LLM class found for '{llm_type}': {llm_class}")

        # Try to initialize it
        llm_instance = llm_class()
        llm_config = config.get('llm', {})
        if 'api_url' in llm_config and 'endpoint' not in llm_config:
            llm_config['endpoint'] = llm_config['api_url']

        llm_instance.initialize(llm_config)
        print(f"✓ LLM initialized successfully")
        print(f"  Type: {type(llm_instance).__name__}")
        print(f"  Module: {type(llm_instance).__module__}")

        # Check if it has a model attribute
        if hasattr(llm_instance, 'model'):
            print(f"  Model: {llm_instance.model}")
        if hasattr(llm_instance, 'endpoint'):
            print(f"  Endpoint: {llm_instance.endpoint}")
        if hasattr(llm_instance, 'codex_command'):
            print(f"  Codex Command: {llm_instance.codex_command}")

        # Try a test generation
        print("\nTesting generation...")
        try:
            response = llm_instance.generate("Say 'test' and nothing else", max_tokens=10, temperature=0.0)
            print(f"✓ Generation successful: {response[:100]}")
        except Exception as e:
            print(f"✗ Generation failed: {e}")

    except Exception as e:
        print(f"✗ Error getting LLM: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
