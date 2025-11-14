#!/usr/bin/env python3
"""Test LLM switching to ensure all components use the same LLM instance."""

import sys
sys.path.insert(0, '/home/omarwsl/projects/claude_code_orchestrator')

from src.core.config import Config
from src.orchestrator import Orchestrator

def test_llm_switching():
    """Test that LLM switching updates all component references."""
    print("=" * 80)
    print("Testing LLM Reference Management Pattern")
    print("=" * 80)
    print()

    # Load config
    config = Config.load('config/config.yaml')
    print(f"✓ Config loaded: llm.type = {config.get('llm.type')}")

    # Create and initialize orchestrator
    orchestrator = Orchestrator(config=config)
    orchestrator.initialize()
    print(f"✓ Orchestrator initialized")

    # Check initial LLM
    initial_llm = orchestrator.llm_interface
    print(f"  Initial LLM: {type(initial_llm).__name__ if initial_llm else 'None'}")

    if initial_llm:
        if hasattr(initial_llm, 'model'):
            print(f"  Initial model: {initial_llm.model}")
        if hasattr(initial_llm, 'endpoint'):
            print(f"  Initial endpoint: {initial_llm.endpoint}")

    print()

    # Check that all components have the same LLM reference
    print("Checking component LLM references...")
    components_with_llm = []

    if orchestrator.context_manager and hasattr(orchestrator.context_manager, 'llm_interface'):
        components_with_llm.append(('ContextManager', orchestrator.context_manager.llm_interface))

    if orchestrator.confidence_scorer and hasattr(orchestrator.confidence_scorer, 'llm_interface'):
        components_with_llm.append(('ConfidenceScorer', orchestrator.confidence_scorer.llm_interface))

    if orchestrator.prompt_generator and hasattr(orchestrator.prompt_generator, 'llm_interface'):
        components_with_llm.append(('PromptGenerator', orchestrator.prompt_generator.llm_interface))

    if orchestrator.complexity_estimator and hasattr(orchestrator.complexity_estimator, 'llm_interface'):
        components_with_llm.append(('ComplexityEstimator', orchestrator.complexity_estimator.llm_interface))

    print(f"  Found {len(components_with_llm)} components with LLM references:")
    all_same = True
    for name, component_llm in components_with_llm:
        is_same = component_llm is initial_llm
        status = "✓" if is_same else "✗"
        print(f"    {status} {name}: {type(component_llm).__name__ if component_llm else 'None'}")
        if not is_same:
            all_same = False

    if all_same:
        print("  ✓ All components use the same LLM instance")
    else:
        print("  ✗ WARNING: Some components have different LLM instances!")

    print()

    # Test switching LLM
    print("Testing LLM switch...")
    print("-" * 80)

    # Get initial provider
    initial_type = config.get('llm.type')
    print(f"Current provider: {initial_type}")

    # Determine target provider (switch to different one)
    if initial_type == 'ollama':
        target_type = 'openai-codex'
        target_model = None  # Use default
    else:
        target_type = 'ollama'
        target_model = 'qwen2.5-coder:32b'

    print(f"Switching to: {target_type}" + (f" ({target_model})" if target_model else ""))
    print()

    # Perform switch
    llm_config = {'model': target_model} if target_model else None
    success = orchestrator.reconnect_llm(
        llm_type=target_type,
        llm_config=llm_config
    )

    if not success:
        print("✗ LLM switch failed!")
        print("  (This is expected if target LLM service is not available)")
        print()
        return

    print("✓ LLM switch succeeded")
    print()

    # Check new LLM
    new_llm = orchestrator.llm_interface
    print(f"New LLM: {type(new_llm).__name__ if new_llm else 'None'}")

    if new_llm:
        if hasattr(new_llm, 'model'):
            print(f"  New model: {new_llm.model}")
        if hasattr(new_llm, 'endpoint'):
            print(f"  New endpoint: {new_llm.endpoint}")
        elif hasattr(new_llm, 'codex_command'):
            print(f"  Codex command: {new_llm.codex_command}")

    print()

    # Verify LLM instance changed
    if new_llm is not initial_llm:
        print("✓ LLM instance changed (as expected)")
    else:
        print("✗ WARNING: LLM instance did not change!")

    print()

    # Check that all components now have the NEW LLM reference
    print("Verifying all components updated to new LLM...")
    all_updated = True

    if orchestrator.context_manager:
        is_updated = orchestrator.context_manager.llm_interface is new_llm
        status = "✓" if is_updated else "✗"
        print(f"  {status} ContextManager")
        if not is_updated:
            all_updated = False

    if orchestrator.confidence_scorer:
        is_updated = orchestrator.confidence_scorer.llm_interface is new_llm
        status = "✓" if is_updated else "✗"
        print(f"  {status} ConfidenceScorer")
        if not is_updated:
            all_updated = False

    if orchestrator.prompt_generator:
        is_updated = orchestrator.prompt_generator.llm_interface is new_llm
        status = "✓" if is_updated else "✗"
        print(f"  {status} PromptGenerator")
        if not is_updated:
            all_updated = False

    if orchestrator.complexity_estimator:
        is_updated = orchestrator.complexity_estimator.llm_interface is new_llm
        status = "✓" if is_updated else "✗"
        print(f"  {status} ComplexityEstimator")
        if not is_updated:
            all_updated = False

    print()

    if all_updated:
        print("🎉 SUCCESS: All components updated to new LLM instance!")
        print()
        print("LLM Reference Management Pattern is working correctly:")
        print("  ✓ Single source of truth (orchestrator.llm_interface)")
        print("  ✓ Centralized updates (_update_llm_references)")
        print("  ✓ All components synchronized")
        return True
    else:
        print("❌ FAILURE: Some components not updated!")
        print()
        print("This indicates a bug in _update_llm_references() method.")
        print("Check that all components are listed in the update method.")
        return False

if __name__ == '__main__':
    try:
        success = test_llm_switching()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
