# Bug Fix: Interactive Mode LLM Crashes

**Bug ID**: Interactive Mode LLM NoneType Errors
**Date**: November 12, 2025
**Severity**: High
**Status**: Fixed

## Related Bugs

1. `/llm switch` crashes when prompt_generator is None
2. Natural language commands crash when LLM unavailable

## Problem

When using `/llm switch` in interactive mode after Obra initialized with an unavailable LLM, the command crashed with:

```
AttributeError: 'NoneType' object has no attribute 'llm_interface'
```

**Error Traceback**:
```
File "/home/omarwsl/projects/claude_code_orchestrator/src/interactive.py", line 925
    self.orchestrator.prompt_generator.llm_interface = new_llm
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AttributeError: 'NoneType' object has no attribute 'llm_interface'
```

## Root Cause

**Two issues**:

1. **Interactive mode used manual LLM switching**: The `_llm_switch()` method manually created LLM instances and updated components, instead of using the new `orchestrator.reconnect_llm()` method.

2. **Missing component initialization**: When initial LLM initialization failed gracefully (new feature in v1.6.0), `prompt_generator` and `response_validator` were never created. When reconnection succeeded, these components were still `None`.

**Sequence**:
```
1. Obra starts with Ollama down
2. _initialize_llm() catches exception, sets llm_interface=None
3. prompt_generator is never created (still None)
4. User runs /llm switch openai-codex
5. _llm_switch() tries to access prompt_generator.llm_interface
6. CRASH: prompt_generator is None
```

## Solution

**Fixed in 2 files**:

### 1. `src/interactive.py` (lines 884-930)

**Before**:
```python
def _llm_switch(self, provider: str, model: Optional[str]) -> None:
    # Manually create LLM instance
    new_llm = llm_class()
    new_llm.initialize(llm_config)

    # Manually update components
    self.orchestrator.llm_interface = new_llm
    self.orchestrator.context_manager.llm_interface = new_llm
    self.orchestrator.confidence_scorer.llm_interface = new_llm

    # BUG: prompt_generator might be None
    if hasattr(self.orchestrator, 'prompt_generator'):
        self.orchestrator.prompt_generator.llm_interface = new_llm  # ❌ Crash
```

**After**:
```python
def _llm_switch(self, provider: str, model: Optional[str]) -> None:
    # Build LLM config
    llm_config = {}
    if model:
        llm_config['model'] = model

    # Use orchestrator's reconnect_llm method (handles all components)
    success = self.orchestrator.reconnect_llm(
        llm_type=provider,
        llm_config=llm_config if llm_config else None
    )

    if success:
        print(f"✓ Switched to {provider}")
    else:
        print(f"✗ Failed to switch to {provider}")
```

**Benefits**:
- ✅ Uses centralized `reconnect_llm()` method
- ✅ Handles all component initialization properly
- ✅ Returns success/failure status
- ✅ No manual component management

---

### 2. `src/orchestrator.py` (lines 492-538)

**Before**:
```python
except Exception as e:
    # Gracefully handle LLM initialization failures
    logger.warning(f"LLM initialization failed: {e}")

    # Set LLM interface to None
    self.llm_interface = None

    # ❌ prompt_generator and response_validator never created
```

**After**:
```python
except Exception as e:
    # Gracefully handle LLM initialization failures
    logger.warning(f"LLM initialization failed: {e}")

    # Set LLM interface to None
    self.llm_interface = None

    # ✅ Initialize prompt generator and validator with None LLM
    if not hasattr(self, 'prompt_generator') or self.prompt_generator is None:
        template_dir = self.config.get('prompt.template_dir', 'config')
        try:
            self.prompt_generator = PromptGenerator(
                template_dir=template_dir,
                llm_interface=None,  # Will be set when LLM reconnects
                state_manager=self.state_manager
            )
        except Exception as pg_error:
            logger.warning(f"Could not initialize prompt generator: {pg_error}")
            self.prompt_generator = None

    if not hasattr(self, 'response_validator') or self.response_validator is None:
        try:
            self.response_validator = ResponseValidator()
        except Exception as rv_error:
            logger.warning(f"Could not initialize response validator: {rv_error}")
            self.response_validator = None
```

**Benefits**:
- ✅ Components always initialized (even if LLM unavailable)
- ✅ `llm_interface=None` initially, set on reconnection
- ✅ No crashes when accessing components
- ✅ Graceful fallback complete

## Testing

**Manual Test**:
```bash
# 1. Start with Ollama down
$ # (Ollama not running)

# 2. Start interactive mode
$ python -m src.cli interactive
⚠ Could not connect to LLM service (ollama).
  Obra loaded but you need a working LLM to execute tasks.

orchestrator>

# 3. Try to switch to OpenAI Codex
orchestrator> /llm switch openai-codex
[Switching to openai-codex...]
✓ Switched to openai-codex
  /to-orch will now use this LLM

# ✅ SUCCESS (previously crashed)
```

**Automated Test** (added to `tests/test_llm_management.py`):
```python
def test_interactive_llm_switch_after_failed_init(test_config):
    """Test that /llm switch works even if initial LLM init failed."""
    # Configure with unavailable LLM
    test_config.set('llm.endpoint', 'http://invalid:99999')

    orchestrator = Orchestrator(config=test_config)
    orchestrator.initialize()

    # LLM should be None
    assert orchestrator.llm_interface is None

    # But prompt_generator should still exist
    assert orchestrator.prompt_generator is not None

    # Reconnect should work
    with patch.object(orchestrator, '_initialize_llm'):
        mock_llm = Mock()
        mock_llm.is_available.return_value = True
        orchestrator.llm_interface = mock_llm
        orchestrator.prompt_generator.llm_interface = mock_llm

        success = orchestrator.reconnect_llm()
        assert success is True
```

---

## Bug 2: Natural Language Commands Crash

**Error Message**:
```
AttributeError: 'NoneType' object has no attribute 'generate'
File "/src/nl/intent_classifier.py", line 195, in classify
    response = self.llm_plugin.generate(
               ^^^^^^^^^^^^^^^^^^^^^^^^
```

**Root Cause**:
Interactive mode initialized NLCommandProcessor even when LLM was None, causing crashes when user sent natural language messages.

**Fix** (`src/interactive.py` lines 152-192):

**Before**:
```python
def _initialize_nl_processor(self) -> None:
    # Get LLM plugin from orchestrator
    llm_plugin = self.orchestrator.llm_interface

    # Initialize NL processor (even if llm_plugin is None)
    self.nl_processor = NLCommandProcessor(
        llm_plugin=llm_plugin,  # ❌ Can be None
        state_manager=self.state_manager,
        config=self.config
    )
```

**After**:
```python
def _initialize_nl_processor(self) -> None:
    # Get LLM plugin from orchestrator
    llm_plugin = self.orchestrator.llm_interface

    # ✅ Check if LLM is available
    if llm_plugin is None:
        logger.warning("LLM not available - NL command processing disabled")
        self.nl_processor = None
        return

    # ✅ Verify LLM is responsive
    if hasattr(llm_plugin, 'is_available') and not llm_plugin.is_available():
        logger.warning("LLM not responding - NL command processing disabled")
        self.nl_processor = None
        return

    # Initialize NL processor (only if LLM available)
    self.nl_processor = NLCommandProcessor(
        llm_plugin=llm_plugin,
        state_manager=self.state_manager,
        config=self.config
    )
```

**Improved Error Message** (`src/interactive.py` lines 730-744):
```python
else:
    # Natural language processing disabled (LLM unavailable)
    print("\n⚠ Natural language commands disabled - LLM not available")
    print()
    print("Please use slash commands instead:")
    print("  /project list       - List all projects")
    print("  /task list          - List tasks")
    print("  /epic list          - List epics")
    print("  /help              - Show all commands")
    print()
    print("Or reconnect to LLM:")
    print("  /llm status        - Check LLM connection")
    print("  /llm reconnect     - Reconnect to LLM")
    print()
```

---

## Impact

**Before Fix**:
- ❌ Interactive `/llm switch` crashes after graceful LLM failure
- ❌ Natural language commands crash when LLM unavailable
- ❌ Users cannot recover from LLM connection issues in interactive mode
- ❌ Inconsistent component state (some initialized, some None)
- ❌ Confusing error messages with stack traces

**After Fix**:
- ✅ Interactive `/llm switch` works reliably
- ✅ Natural language commands gracefully disabled when LLM unavailable
- ✅ Users can switch LLMs without restarting Obra
- ✅ Consistent component state (always initialized)
- ✅ Helpful error messages with recovery instructions
- ✅ Slash commands still work without LLM

## Related Changes

- See: `docs/guides/LLM_MANAGEMENT_GUIDE.md` for complete LLM management guide
- See: `CLAUDE.md` "LLM Management" section for CLI usage
- See: `tests/test_llm_management.py` for comprehensive tests

## Lessons Learned

1. **Use centralized methods**: Interactive commands should use orchestrator's public API (`reconnect_llm()`) instead of duplicating logic
2. **Always initialize components**: Even if dependencies unavailable, create components with None/default values
3. **Test graceful failures**: Ensure features work even when dependencies fail
4. **Graceful fallback requires complete implementation**: Don't just catch exceptions - ensure dependent components handle None properly

---

**Status**: ✅ Fixed and tested
**Version**: 1.6.1
