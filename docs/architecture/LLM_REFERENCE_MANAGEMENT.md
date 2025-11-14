# LLM Reference Management Pattern

**Version**: v1.7.2+
**Created**: November 13, 2025
**Status**: Implemented

---

## Overview

This document describes the architectural pattern for managing LLM references across Obra's components to prevent stale references and ensure consistency when switching LLM providers.

## Problem Statement

### Before (Brittle)

Multiple components independently stored LLM references:

```python
orchestrator.llm_interface          # Orchestrator's LLM
context_manager.llm_interface       # ContextManager's LLM
confidence_scorer.llm_interface     # ConfidenceScorer's LLM
prompt_generator.llm_interface      # PromptGenerator's LLM
nl_processor.llm_plugin             # NL processor's LLM
intent_classifier.llm_plugin        # IntentClassifier's LLM
entity_extractor.llm_plugin         # EntityExtractor's LLM
# ... 12+ different references
```

**Issue**: When switching LLM providers (`/llm switch`), only orchestrator's reference was updated. All other components kept stale references to the old LLM instance.

**Symptoms**:
- Natural language commands failed after switching LLMs
- Error: "model 'qwen2.5-coder:32b' not supported when using Codex"
- Components using different LLMs simultaneously
- Inconsistent behavior across system

---

## Solution: Single Source of Truth Pattern

### Architecture

```
┌─────────────────────────────────────────┐
│         Orchestrator (OWNER)            │
│                                         │
│  self.llm_interface ← SINGLE SOURCE     │
│                                         │
│  reconnect_llm()                        │
│      ↓                                  │
│  _update_llm_references()               │
│      ↓                                  │
│  Updates all component references       │
└─────────────────────────────────────────┘
           │
           ├─→ ContextManager.llm_interface
           ├─→ ConfidenceScorer.llm_interface
           ├─→ PromptGenerator (recreated)
           ├─→ ComplexityEstimator.llm_interface
           └─→ NL Processor (via InteractiveMode)
```

### Key Principles

1. **Orchestrator Owns LLM**: Only `Orchestrator.llm_interface` is the canonical LLM instance
2. **Centralized Updates**: `_update_llm_references()` method updates all components
3. **Automatic Propagation**: Called automatically when LLM changes
4. **Easy Maintenance**: Add new components to one method

---

## Implementation

### 1. Orchestrator (Core Pattern)

```python
class Orchestrator:
    def reconnect_llm(self, llm_type=None, llm_config=None) -> bool:
        """Reconnect or switch LLM provider."""
        # Save old reference to detect changes
        old_llm = self.llm_interface

        # Initialize new LLM
        self._initialize_llm()

        # Update all component references if LLM changed
        if self.llm_interface != old_llm:
            self._update_llm_references()
            logger.info("Updated LLM references in all components")

        return True

    def _update_llm_references(self) -> None:
        """Update LLM reference in all components.

        This is the SINGLE SOURCE OF TRUTH maintenance method.
        Add any new LLM-dependent components here.
        """
        # Update existing components
        if self.context_manager:
            self.context_manager.llm_interface = self.llm_interface

        if self.confidence_scorer:
            self.confidence_scorer.llm_interface = self.llm_interface

        # Recreate components that store LLM in __init__
        if self.llm_interface:
            self.prompt_generator = PromptGenerator(
                llm_interface=self.llm_interface,
                # ... other args
            )

        # Update optional components
        if self._enable_complexity_estimation and self.complexity_estimator:
            self.complexity_estimator.llm_interface = self.llm_interface
```

### 2. InteractiveMode (NL Processor)

```python
class InteractiveMode:
    def _llm_switch(self, provider, model):
        """Switch LLM provider in interactive mode."""
        # Use orchestrator's reconnect (updates all orchestrator components)
        success = self.orchestrator.reconnect_llm(
            llm_type=provider,
            llm_config=llm_config
        )

        if success:
            # Reinitialize NL processor with new LLM
            self._initialize_nl_processor()

            if self.nl_processor:
                print("✓ Natural language processing initialized")
```

### 3. Component Best Practices

**For new components that need LLM:**

```python
class MyNewComponent:
    def __init__(self, llm_interface):
        self.llm_interface = llm_interface

    def some_method(self):
        # Always access via self.llm_interface
        response = self.llm_interface.generate(prompt)
```

**Then add to `_update_llm_references()`:**

```python
def _update_llm_references(self):
    # ... existing updates ...

    # Add your new component
    if self.my_new_component:
        self.my_new_component.llm_interface = self.llm_interface
        logger.debug("  ✓ Updated MyNewComponent LLM reference")
```

---

## Maintenance Checklist

When adding a new component that uses LLM:

- [ ] Component stores LLM in `self.llm_interface` or `self.llm_plugin`
- [ ] Component added to `_update_llm_references()` method
- [ ] Component handles `None` LLM gracefully (before initialization)
- [ ] Logging added to track reference update
- [ ] Documentation updated (this file)

---

## Testing LLM Switching

### Manual Test

```bash
# Start Obra
./obra.sh

# Check current LLM
/llm show

# Switch to different provider
/llm switch openai-codex

# Test natural language command (should use new LLM)
list all projects

# Switch back
/llm switch ollama qwen2.5-coder:32b

# Test again (should use Ollama)
show me open tasks
```

### Verification

Check logs for:
```
INFO - Clearing old model when switching to openai-codex
DEBUG - Updating LLM references in all components...
DEBUG -   ✓ Updated ContextManager LLM reference
DEBUG -   ✓ Updated ConfidenceScorer LLM reference
DEBUG -   ✓ Recreated PromptGenerator with new LLM
INFO - ✓ All component LLM references updated
```

---

## Benefits

### Before Fix
- ❌ 12+ separate LLM references
- ❌ Manual update required for each component
- ❌ Easy to forget components when adding new ones
- ❌ Stale references after LLM switch
- ❌ Cross-provider model conflicts

### After Fix
- ✅ Single source of truth (orchestrator)
- ✅ Automatic updates via centralized method
- ✅ Clear checklist for adding components
- ✅ All references updated atomically
- ✅ Model conflicts prevented
- ✅ Extensive logging for debugging

---

## Alternative Patterns Considered

### Property-Based Access
```python
class MyComponent:
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator

    @property
    def llm(self):
        return self.orchestrator.llm_interface
```

**Pros**: Always current, no update needed
**Cons**: Tight coupling, circular dependencies

**Decision**: Rejected due to coupling concerns

### Observer Pattern (Pub/Sub)
```python
class LLMObserver:
    def on_llm_changed(self, new_llm):
        self.llm_interface = new_llm

orchestrator.register_observer(my_component)
```

**Pros**: Loose coupling, explicit contract
**Cons**: More complexity, harder to debug

**Decision**: Rejected due to added complexity

### Service Locator
```python
class LLMService:
    @classmethod
    def get_current_llm(cls):
        return cls._current_llm
```

**Pros**: Global access, simple
**Cons**: Global state, testing harder

**Decision**: Rejected due to testing concerns

---

## Future Improvements

### Option 1: Add Validation
```python
def _update_llm_references(self):
    components_updated = []

    # Update with tracking
    if self.context_manager:
        self.context_manager.llm_interface = self.llm_interface
        components_updated.append('ContextManager')

    # Validate all expected components updated
    expected = ['ContextManager', 'ConfidenceScorer', ...]
    missing = set(expected) - set(components_updated)
    if missing:
        logger.warning(f"Components not updated: {missing}")
```

### Option 2: Component Registry
```python
class Orchestrator:
    def __init__(self):
        self._llm_dependent_components = []

    def register_llm_component(self, component):
        self._llm_dependent_components.append(component)

    def _update_llm_references(self):
        for component in self._llm_dependent_components:
            component.llm_interface = self.llm_interface
```

---

## Related Documentation

- [Architecture Overview](../design/OBRA_SYSTEM_OVERVIEW.md)
- [LLM Plugin System](../../src/plugins/README.md)
- [Interactive Mode Guide](../guides/INTERACTIVE_STREAMING_QUICKREF.md)

---

**Last Updated**: November 13, 2025
**Maintained By**: Architecture Team
