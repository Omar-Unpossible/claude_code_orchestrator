# Dynamic Agent Labels and Messaging - Implementation Plan

**Date**: November 5, 2025
**Status**: ✅ APPROVED - Ready for Implementation
**Estimated Complexity**: Medium (3 phases, ~600 lines of code + ~400 lines of docs)
**Priority**: HIGH

---

## Executive Summary

This plan implements two critical improvements to Obra's interactive streaming interface:

1. **Dynamic Agent Labels**: Replace hardcoded "QWEN" labels with dynamic `[ORCH:ollama]` or `[ORCH:codex]` based on actual LLM in use
2. **Orchestrator Messaging**: Implement `/to-orch` command (currently `/to-obra` stores but doesn't use messages)
3. **Unified Terminology**: Standardize on `impl`/`implementer` and `orch`/`orchestrator` throughout codebase

---

## Background

### Current State

**Problem 1: Hardcoded Labels**
- Streaming output shows `[QWEN]` even when using OpenAI Codex
- User can't tell which LLM is actually validating responses
- Confusing for troubleshooting and debugging

**Problem 2: Incomplete `/to-obra` Command**
- Command exists but only STORES the message (`injected_context['to_obra']`)
- Message is never READ or USED anywhere
- Help text promises it "adds directive to Obra's decision logic" but doesn't actually do anything

**Problem 3: Inconsistent Terminology**
- Code uses "Obra" (legacy project name)
- Architecture uses "Orchestrator" and "Implementer" roles
- No clear, concise shorthand

### Desired State

**Labels**: `[ORCH:ollama]`, `[ORCH:codex]`, `[IMPL:claude-code]`
**Commands**: `/to-orch` (orchestrator), `/to-impl` (implementer)
**Shorthand**: `orch`/`impl` for brevity, `orchestrator`/`implementer` for formal

---

## User Answers Summary

From clarification session:

1. **Message to Orch behavior**: Multiple (A/B/C) - depends on user's prompt
   - **A**: Inject into validation prompt
   - **B**: Override decision logic
   - **C**: Orch provides feedback to Impl
2. **`/to-obra` status**: Exists but incomplete (stores, doesn't use)
3. **Terminology**: `impl`/`implementer` and `orch`/`orchestrator`
4. **Display format**: Option B with short form: `[IMPL:model]` and `[ORCH:model]`
5. **Backward compatibility**: Recommended (keep aliases for `/to-claude`, `/to-obra`)

---

## Architecture Overview

### Agent Roles

| Role | Short | Long | Description | Examples |
|------|-------|------|-------------|----------|
| **Implementer** | `impl` | `implementer` | Generates code and responses | Claude Code, Aider |
| **Orchestrator** | `orch` | `orchestrator` | Validates, scores, decides | Qwen (Ollama), Codex (OpenAI) |

### Display Label Format

**Pattern**: `[ROLE:MODEL]`

**Examples**:
- `[IMPL:claude-code]` - Claude Code generating code
- `[ORCH:ollama]` - Qwen via Ollama validating
- `[ORCH:openai-codex]` - OpenAI Codex validating

### Message Flow

**To Implementer** (`/to-impl` or `/to-claude`):
```
User: /to-impl Add unit tests for the new feature
  ↓
Stored in: injected_context['to_impl']
  ↓
Applied in: _apply_injected_context() (line 249)
  ↓
Injected into: Claude Code's next prompt as "USER GUIDANCE"
```

**To Orchestrator** (`/to-orch` or `/to-obra`) - NEW:
```
User: /to-orch Be more lenient with quality scores
  ↓
Stored in: injected_context['to_orch']
  ↓
Applied in: Multiple injection points (see below)
  ↓
Effects:
  - Validation prompt injection (quality scoring guidance)
  - Decision override hints (bypass thresholds)
  - Feedback generation (orch analyzes and suggests to impl)
```

---

## Implementation Plan

### Phase 1: Dynamic LLM Labels

**Complexity**: Low-Medium (~150 lines code, 3 files modified)
**Risk**: Low (cosmetic changes, backward compatible)

#### Task 1.1: Add `get_name()` Method to LLM Interfaces

**Files**: `src/llm/local_interface.py`, `src/llm/openai_codex_interface.py`

**Changes**:
```python
# src/llm/local_interface.py
class LocalLLMInterface:
    def get_name(self) -> str:
        """Get LLM name for display purposes.

        Returns:
            Short name (e.g., 'ollama', 'llama-cpp')
        """
        return 'ollama'  # Could also be self.provider_type if dynamic

# src/llm/openai_codex_interface.py
class OpenAICodexLLMPlugin:
    def get_name(self) -> str:
        """Get LLM name for display purposes.

        Returns:
            Short name (e.g., 'openai-codex')
        """
        return 'openai-codex'
```

**Validation**:
- Both classes implement `get_name()`
- Returns consistent format (lowercase, hyphenated)
- Matches LLM type in config.yaml

---

#### Task 1.2: Update Orchestrator Display Methods

**File**: `src/orchestrator.py`

**Changes**:

1. **Rename and enhance `_print_qwen()` → `_print_orch()`**:
```python
# OLD (line 157-164)
def _print_qwen(self, message: str) -> None:
    """Print Qwen validation output with colored [QWEN] prefix."""
    print(f"\033[33m[QWEN]\033[0m {message}")

# NEW
def _print_orch(self, message: str) -> None:
    """Print orchestrator output with dynamic [ORCH:model] prefix.

    Args:
        message: Message to display

    Example:
        >>> self._print_orch("Quality: 0.81 (PASS)")
        [ORCH:ollama] Quality: 0.81 (PASS)
    """
    llm_name = self.llm_interface.get_name() if self.llm_interface else 'unknown'
    prefix = f"[ORCH:{llm_name}]"
    # Yellow color for orchestrator output
    print(f"\033[33m{prefix}\033[0m {message}")
```

2. **Add `_print_impl()` for symmetry**:
```python
def _print_impl(self, message: str) -> None:
    """Print implementer output with dynamic [IMPL:model] prefix.

    Args:
        message: Message to display

    Example:
        >>> self._print_impl("Response received (1234 chars)")
        [IMPL:claude-code] Response received (1234 chars)
    """
    agent_name = getattr(self.agent, 'name', 'claude-code')  # Fallback
    prefix = f"[IMPL:{agent_name}]"
    # Green color for implementer output
    print(f"\033[32m{prefix}\033[0m {message}")
```

3. **Update all `_print_qwen()` calls** (found 1 occurrence):
```python
# Line 1204
# OLD
self._print_qwen(f"  Quality: {quality_result.overall_score:.2f} ({gate_status})")

# NEW
self._print_orch(f"  Quality: {quality_result.overall_score:.2f} ({gate_status})")
```

4. **Update logger calls with dynamic labels**:
```python
# Line 1203
# OLD
logger.info(f"[QWEN] Quality: {quality_result.overall_score:.2f} ({gate_status})")

# NEW
llm_name = self.llm_interface.get_name()
logger.info(f"[ORCH:{llm_name}] Quality: {quality_result.overall_score:.2f} ({gate_status})")
```

**Validation**:
- All `_print_qwen()` calls replaced with `_print_orch()`
- All `[QWEN]` logger calls use dynamic `[ORCH:{llm_name}]`
- No hardcoded LLM names remain in display logic

---

#### Task 1.3: Update Streaming Handler

**File**: `src/utils/streaming_handler.py`

**Changes**:

1. **Update COLOR_MAP** (lines 32-44):
```python
# OLD
COLOR_MAP: Dict[str, str] = {
    'OBRA→CLAUDE': colorama.Fore.BLUE,
    '[OBRA→CLAUDE]': colorama.Fore.BLUE,
    'CLAUDE→OBRA': colorama.Fore.GREEN,
    '[CLAUDE→OBRA]': colorama.Fore.GREEN,
    'QWEN': colorama.Fore.YELLOW,
    '[QWEN]': colorama.Fore.YELLOW,
    'ERROR': colorama.Fore.RED,
    # ...
}

# NEW
COLOR_MAP: Dict[str, str] = {
    'ORCH→IMPL': colorama.Fore.BLUE,
    '[ORCH→IMPL]': colorama.Fore.BLUE,
    'IMPL→ORCH': colorama.Fore.GREEN,
    '[IMPL→ORCH]': colorama.Fore.GREEN,
    '[ORCH:': colorama.Fore.YELLOW,  # Matches [ORCH:ollama], [ORCH:codex]
    '[IMPL:': colorama.Fore.GREEN,   # Matches [IMPL:claude-code]
    'ERROR': colorama.Fore.RED,
    # ...

    # Backward compatibility (deprecated but supported)
    'OBRA→CLAUDE': colorama.Fore.BLUE,
    '[OBRA→CLAUDE]': colorama.Fore.BLUE,
    'CLAUDE→OBRA': colorama.Fore.GREEN,
    '[CLAUDE→OBRA]': colorama.Fore.GREEN,
    'QWEN': colorama.Fore.YELLOW,
    '[QWEN]': colorama.Fore.YELLOW,
}
```

2. **Update format helper methods**:
```python
# Lines 84-94
# OLD
@staticmethod
def format_obra_to_claude(iteration: int, chars: int) -> str:
    """Format Obra→Claude prompt message."""
    return f"[OBRA→CLAUDE] Iteration {iteration} | Prompt: {chars:,} chars"

# NEW
@staticmethod
def format_orch_to_impl(iteration: int, chars: int, impl_name: str = 'claude-code') -> str:
    """Format Orch→Impl prompt message.

    Args:
        iteration: Current iteration number
        chars: Number of characters in prompt
        impl_name: Implementer name (e.g., 'claude-code')

    Returns:
        Formatted message string

    Example:
        >>> format_orch_to_impl(3, 1234, 'claude-code')
        '[ORCH→IMPL:claude-code] Iteration 3 | Prompt: 1,234 chars'
    """
    return f"[ORCH→IMPL:{impl_name}] Iteration {iteration} | Prompt: {chars:,} chars"

# Keep old method for backward compatibility (deprecated)
@staticmethod
def format_obra_to_claude(iteration: int, chars: int) -> str:
    """DEPRECATED: Use format_orch_to_impl() instead."""
    return StreamingHandler.format_orch_to_impl(iteration, chars)
```

3. **Update `format_qwen_validation()` → `format_orch_validation()`**:
```python
# Lines 110-121
# OLD
@staticmethod
def format_qwen_validation(quality: float, decision: str) -> str:
    """Format Qwen validation message."""
    status = "PASS" if quality >= 0.7 else "FAIL"
    return f"[QWEN] Quality: {quality:.2f} ({status}) | Decision: {decision}"

# NEW
@staticmethod
def format_orch_validation(quality: float, decision: str, llm_name: str = 'ollama') -> str:
    """Format orchestrator validation message.

    Args:
        quality: Quality score (0.0-1.0)
        decision: Decision string (PROCEED/RETRY/etc.)
        llm_name: LLM name (e.g., 'ollama', 'openai-codex')

    Returns:
        Formatted message string

    Example:
        >>> format_orch_validation(0.81, 'PROCEED', 'ollama')
        '[ORCH:ollama] Quality: 0.81 (PASS) | Decision: PROCEED'
    """
    status = "PASS" if quality >= 0.7 else "FAIL"
    return f"[ORCH:{llm_name}] Quality: {quality:.2f} ({status}) | Decision: {decision}"

# Keep old method for backward compatibility (deprecated)
@staticmethod
def format_qwen_validation(quality: float, decision: str) -> str:
    """DEPRECATED: Use format_orch_validation() instead."""
    return StreamingHandler.format_orch_validation(quality, decision, 'ollama')
```

4. **Update module docstring** (lines 1-6):
```python
# OLD
"""Streaming log handler for real-time colored output.

This module provides a custom logging handler that outputs logs in real-time
with color coding for different agent communications (Obra, Claude, Qwen).

Part of Interactive Streaming Interface (Phase 1).
"""

# NEW
"""Streaming log handler for real-time colored output.

This module provides a custom logging handler that outputs logs in real-time
with color coding for different agent communications (Orchestrator, Implementer).

Supports dynamic agent labels based on actual models in use:
- [ORCH:ollama] or [ORCH:openai-codex] for orchestrator
- [IMPL:claude-code] for implementer

Part of Interactive Streaming Interface (Phase 1-2).
"""
```

**Validation**:
- Color map recognizes `[ORCH:*]` and `[IMPL:*]` patterns
- Backward compatibility preserved (old labels still work)
- All format methods updated with dynamic parameters

---

### Phase 2: Implement `/to-orch` Command

**Complexity**: Medium-High (~350 lines code, 3 files modified)
**Risk**: Medium (new functionality, affects orchestration logic)

#### Task 2.1: Rename Commands and Add Aliases

**Files**: `src/utils/command_processor.py`, `src/utils/input_manager.py`

**Changes**:

1. **Update command registry** (`command_processor.py` lines 64-73):
```python
# OLD
self.commands: Dict[str, Callable] = {
    '/pause': self._pause,
    '/resume': self._resume,
    '/to-claude': self._to_claude,
    '/to-obra': self._to_obra,
    '/override-decision': self._override_decision,
    '/status': self._status,
    '/help': self._help,
    '/stop': self._stop,
}

# NEW
self.commands: Dict[str, Callable] = {
    '/pause': self._pause,
    '/resume': self._resume,
    '/to-impl': self._to_impl,          # Primary
    '/to-orch': self._to_orch,          # Primary
    '/to-claude': self._to_impl,        # Alias (backward compat)
    '/to-obra': self._to_orch,          # Alias (backward compat)
    '/to-implementer': self._to_impl,   # Formal alias
    '/to-orchestrator': self._to_orch,  # Formal alias
    '/override-decision': self._override_decision,
    '/status': self._status,
    '/help': self._help,
    '/stop': self._stop,
}
```

2. **Update help text** (lines 25-34):
```python
# OLD
HELP_TEXT = {
    '/pause': 'Pause execution after current turn. Resume with /resume.',
    '/resume': 'Resume paused execution.',
    '/to-claude': 'Inject guidance into Claude\'s next prompt...',
    '/to-obra': 'Add directive to Obra\'s decision logic...',
    # ...
}

# NEW
HELP_TEXT = {
    '/pause': 'Pause execution after current turn. Resume with /resume.',
    '/resume': 'Resume paused execution.',
    '/to-impl': 'Send message to implementer (Claude Code). Aliases: /to-claude, /to-implementer. Max 5000 chars. Example: /to-impl Add unit tests',
    '/to-orch': 'Send message to orchestrator (Qwen/Codex). Aliases: /to-obra, /to-orchestrator. Purpose depends on message content. Examples:\n' +
                '  - Validation guidance: /to-orch Be more lenient with quality scores\n' +
                '  - Decision override: /to-orch Accept this response even if quality is low\n' +
                '  - Feedback request: /to-orch Analyze this code and suggest improvements to implementer',
    '/override-decision': 'Override current decision. Valid: proceed, retry, clarify, escalate, checkpoint. Example: /override-decision retry',
    '/status': 'Show current task status, iteration, quality score, token usage.',
    '/help': 'Show this help message or help for specific command.',
    '/stop': 'Stop execution gracefully (completes current turn, saves state).',

    # Deprecated (show but indicate aliases)
    '/to-claude': 'DEPRECATED: Use /to-impl instead. Alias for /to-impl.',
    '/to-obra': 'DEPRECATED: Use /to-orch instead. Alias for /to-orch.',
}
```

3. **Update command list** (`input_manager.py` lines 22-31):
```python
# OLD
COMMANDS = [
    '/pause',
    '/resume',
    '/to-claude',
    '/to-obra',
    '/override-decision',
    '/status',
    '/help',
    '/stop',
]

# NEW
COMMANDS = [
    '/pause',
    '/resume',
    '/to-impl',
    '/to-orch',
    '/to-implementer',
    '/to-orchestrator',
    '/to-claude',        # Alias (show in autocomplete)
    '/to-obra',          # Alias (show in autocomplete)
    '/override-decision',
    '/status',
    '/help',
    '/stop',
]
```

4. **Update parse_command() logic** (lines 101-108):
```python
# OLD
if command in ['/to-claude', '/to-obra']:
    args['message'] = args_str

# NEW
if command in ['/to-impl', '/to-orch', '/to-implementer', '/to-orchestrator',
               '/to-claude', '/to-obra']:  # Include all aliases
    args['message'] = args_str
```

**Validation**:
- All commands accept both new and old names
- Help text clearly indicates aliases and deprecation
- Autocomplete includes all variants

---

#### Task 2.2: Rename and Enhance Message Handlers

**File**: `src/utils/command_processor.py`

**Changes**:

1. **Rename `_to_claude()` → `_to_impl()`** (lines 179-213):
```python
# OLD
def _to_claude(self, args: Dict[str, Any]) -> Dict[str, Any]:
    """Inject message into Claude's next prompt (last-wins policy)."""
    message = args.get('message', '').strip()

    if not message:
        return {'error': '/to-claude requires a message'}

    # ... validation ...

    if self.orchestrator.injected_context.get('to_claude'):
        self.logger.warning("Replacing previous /to-claude message...")

    self.orchestrator.injected_context['to_claude'] = message

    preview = message[:50] + '...' if len(message) > 50 else message
    return {
        'success': True,
        'message': f'Will send to Claude: {preview}'
    }

# NEW
def _to_impl(self, args: Dict[str, Any]) -> Dict[str, Any]:
    """Inject message into implementer's next prompt (last-wins policy).

    Args:
        args: Command arguments with 'message' key

    Returns:
        Success result or error

    Example:
        >>> processor.execute_command('/to-impl Add unit tests for validation logic')
        {'success': True, 'message': 'Will send to implementer: Add unit tests for validation logic'}
    """
    message = args.get('message', '').strip()

    # Validation
    if not message:
        return {'error': '/to-impl requires a message'}

    if len(message) > MAX_INJECTED_TEXT_LENGTH:
        return {
            'error': f'Message too long ({len(message)} chars, max {MAX_INJECTED_TEXT_LENGTH})'
        }

    # Warn if overwriting existing context
    if self.orchestrator.injected_context.get('to_impl'):
        self.logger.warning(
            "Replacing previous /to-impl message with new one (last-wins)"
        )

    # Store with both new and legacy keys (for transition period)
    self.orchestrator.injected_context['to_impl'] = message
    self.orchestrator.injected_context['to_claude'] = message  # Legacy key for compatibility

    # Show preview (first 50 chars)
    preview = message[:50] + '...' if len(message) > 50 else message

    return {
        'success': True,
        'message': f'Will send to implementer: {preview}'
    }
```

2. **Enhance `_to_obra()` → `_to_orch()` WITH ACTUAL IMPLEMENTATION** (lines 215-250):
```python
# OLD (incomplete implementation)
def _to_obra(self, args: Dict[str, Any]) -> Dict[str, Any]:
    """Add directive to Obra's decision logic."""
    message = args.get('message', '').strip()

    if not message:
        return {'error': '/to-obra requires a directive'}

    # ... validation ...

    self.orchestrator.injected_context['to_obra'] = message

    preview = message[:50] + '...' if len(message) > 50 else message
    return {
        'success': True,
        'message': f'Directive stored: {preview}'
    }

# NEW (complete implementation)
def _to_orch(self, args: Dict[str, Any]) -> Dict[str, Any]:
    """Send message to orchestrator (validation LLM).

    Message behavior depends on content:
    - Validation guidance: Injected into quality scoring prompt
    - Decision hints: Affects decision thresholds temporarily
    - Feedback requests: Orch generates feedback sent to implementer

    Args:
        args: Command arguments with 'message' key

    Returns:
        Success result or error

    Examples:
        >>> # Validation guidance
        >>> processor.execute_command('/to-orch Be more lenient with code quality')

        >>> # Decision hint
        >>> processor.execute_command('/to-orch Accept this even if quality is borderline')

        >>> # Feedback request
        >>> processor.execute_command('/to-orch Review the code and suggest 3 improvements')
    """
    message = args.get('message', '').strip()

    # Validation
    if not message:
        return {'error': '/to-orch requires a message'}

    if len(message) > MAX_INJECTED_TEXT_LENGTH:
        return {
            'error': f'Message too long ({len(message)} chars, max {MAX_INJECTED_TEXT_LENGTH})'
        }

    # Warn if overwriting existing context
    if self.orchestrator.injected_context.get('to_orch'):
        self.logger.warning(
            "Replacing previous /to-orch message with new one (last-wins)"
        )

    # Store with both new and legacy keys (for transition period)
    self.orchestrator.injected_context['to_orch'] = message
    self.orchestrator.injected_context['to_obra'] = message  # Legacy key for compatibility

    # Classify message intent (simple heuristics)
    message_lower = message.lower()
    intent = 'general'

    if any(word in message_lower for word in ['quality', 'score', 'validate', 'lenient', 'strict']):
        intent = 'validation_guidance'
    elif any(word in message_lower for word in ['accept', 'proceed', 'approve', 'override']):
        intent = 'decision_hint'
    elif any(word in message_lower for word in ['review', 'analyze', 'suggest', 'feedback', 'tell']):
        intent = 'feedback_request'

    # Store intent for downstream use
    self.orchestrator.injected_context['to_orch_intent'] = intent

    # Show preview with detected intent
    preview = message[:50] + '...' if len(message) > 50 else message
    intent_label = {
        'validation_guidance': '→ Will influence quality scoring',
        'decision_hint': '→ Will affect decision thresholds',
        'feedback_request': '→ Will generate feedback for implementer',
        'general': '→ General guidance'
    }[intent]

    return {
        'success': True,
        'message': f'Will send to orchestrator: {preview}\n{intent_label}'
    }
```

**Validation**:
- Both methods renamed and enhanced
- Legacy keys preserved for transition period
- Intent classification helps downstream routing

---

#### Task 2.3: Implement Orchestrator Message Consumption

**File**: `src/orchestrator.py`

**Changes**:

1. **Add helper method to apply orch context** (add after `_apply_injected_context()` around line 260):
```python
def _apply_orch_context(self, validation_prompt: str, context: dict) -> str:
    """Apply orchestrator-injected context to validation prompt.

    Adds user guidance to quality scoring and validation prompts.

    Args:
        validation_prompt: Base validation prompt
        context: Injected context dict

    Returns:
        Augmented validation prompt with user guidance

    Example:
        >>> context = {'to_orch': 'Be more lenient', 'to_orch_intent': 'validation_guidance'}
        >>> augmented = self._apply_orch_context(base_prompt, context)
    """
    orch_message = context.get('to_orch', '')
    if not orch_message:
        return validation_prompt

    intent = context.get('to_orch_intent', 'general')

    # Build augmented prompt based on intent
    if intent == 'validation_guidance':
        augmented = f"{validation_prompt}\n\n--- USER GUIDANCE (VALIDATION) ---\n{orch_message}\n"
    elif intent == 'decision_hint':
        augmented = f"{validation_prompt}\n\n--- USER HINT (DECISION) ---\n{orch_message}\n" + \
                    "Note: User has provided guidance on decision thresholds. Consider this when evaluating.\n"
    elif intent == 'feedback_request':
        augmented = f"{validation_prompt}\n\n--- USER REQUEST (FEEDBACK) ---\n{orch_message}\n" + \
                    "After validation, provide specific feedback addressing the user's request.\n"
    else:
        augmented = f"{validation_prompt}\n\n--- USER MESSAGE (ORCHESTRATOR) ---\n{orch_message}\n"

    # Track token impact
    base_tokens = self.context_manager.estimate_tokens(validation_prompt)
    augmented_tokens = self.context_manager.estimate_tokens(augmented)
    tokens_added = augmented_tokens - base_tokens

    logger.debug(
        f"Applied orchestrator context: +{tokens_added} tokens, intent={intent}"
    )

    return augmented
```

2. **Update quality validation to use orch context** (around line 1185, in validation section):
```python
# Find the section where quality_controller.validate() is called
# BEFORE calling validate(), apply orch context:

# [NEW] PRE-VALIDATION - Apply orch-injected context
validation_prompt = None  # Get from quality_controller or build here
if self.injected_context.get('to_orch'):
    validation_prompt = self._apply_orch_context(validation_prompt, self.injected_context)

# Then pass augmented prompt to quality controller
quality_result = self.quality_controller.validate(
    response=response,
    task=self.current_task,
    # ... other args
    custom_validation_prompt=validation_prompt  # MAY NEED NEW PARAM
)
```

**Note**: This requires investigating whether `QualityController.validate()` accepts custom prompts. If not, we may need to:
- Add `custom_validation_prompt` parameter to `validate()`
- OR: Modify internal prompt generation to check for injected context

3. **Implement decision hint logic** (around line 1240, in decision engine section):
```python
# Find where decision_engine.make_decision() is called
# BEFORE calling, apply decision hints:

# [NEW] PRE-DECISION - Apply orch decision hints
decision_threshold_adjustment = 0.0
if self.injected_context.get('to_orch_intent') == 'decision_hint':
    # User wants to override decision - lower threshold temporarily
    decision_threshold_adjustment = -0.1  # Accept slightly lower quality
    logger.info("[ORCH] User decision hint active: lowering threshold by 0.1")

# Apply adjustment (may need to pass to decision engine)
action = self.decision_engine.make_decision(
    validation_result=validation_result,
    quality_result=quality_result,
    confidence_score=confidence_score,
    # ... other args
    threshold_adjustment=decision_threshold_adjustment  # MAY NEED NEW PARAM
)
```

4. **Implement feedback request logic** (around line 1250, after decision but before action):
```python
# [NEW] POST-DECISION - Handle feedback requests
if self.injected_context.get('to_orch_intent') == 'feedback_request':
    orch_message = self.injected_context.get('to_orch', '')

    # Generate feedback using orchestrator LLM
    feedback_prompt = f"""You are the orchestrator reviewing the implementer's response.

User's Request: {orch_message}

Response to Review:
{response}

Task Context:
{self.current_task.description}

Provide specific, actionable feedback addressing the user's request. Keep it concise (max 300 words).
"""

    try:
        feedback = self.llm_interface.generate(
            prompt=feedback_prompt,
            temperature=0.5,
            max_tokens=500
        )

        # Inject feedback into next implementer prompt
        if feedback:
            self.injected_context['to_impl'] = f"ORCHESTRATOR FEEDBACK:\n{feedback}"
            logger.info(f"[ORCH] Generated feedback for implementer ({len(feedback)} chars)")
            self._print_orch(f"Generated feedback: {feedback[:100]}...")
    except Exception as e:
        logger.error(f"Failed to generate orchestrator feedback: {e}")
```

5. **Update context clearing logic** (line 1349-1350):
```python
# OLD
self.injected_context.pop('to_claude', None)
self.injected_context.pop('to_obra', None)

# NEW
self.injected_context.pop('to_impl', None)
self.injected_context.pop('to_orch', None)
self.injected_context.pop('to_orch_intent', None)
# Keep legacy keys for backward compat
self.injected_context.pop('to_claude', None)
self.injected_context.pop('to_obra', None)
```

6. **Update key usage in `_apply_injected_context()`** (line 249):
```python
# OLD
injected_text = context.get('to_claude', '')

# NEW
# Check both new and legacy keys
injected_text = context.get('to_impl', '') or context.get('to_claude', '')
```

7. **Update key check before applying** (line 1112):
```python
# OLD
if self.injected_context.get('to_claude'):
    prompt = self._apply_injected_context(prompt, self.injected_context)

# NEW
if self.injected_context.get('to_impl') or self.injected_context.get('to_claude'):
    prompt = self._apply_injected_context(prompt, self.injected_context)
```

**Validation**:
- Orch messages consumed at appropriate injection points
- Intent-based routing works correctly
- Feedback generation functional

---

### Phase 3: Documentation and Testing

**Complexity**: Medium (~100 lines test code, ~400 lines documentation updates, 5 files modified)
**Risk**: Low (validation and documentation only)

#### Task 3.1: Update Interactive Mode Documentation

**Files**:
- `docs/development/INTERACTIVE_STREAMING_QUICKREF.md`
- `docs/development/INTERACTIVE_STREAMING_IMPLEMENTATION_PLAN.md`
- `docs/decisions/ADR-011-interactive-streaming-interface.md`

**Changes**:

1. **Update command reference**:
```markdown
# OLD
- `/to-claude <message>` - Inject guidance into next prompt

# NEW
- `/to-impl <message>` - Send message to implementer (Claude Code)
  - Aliases: `/to-claude`, `/to-implementer`
  - Injects guidance into implementer's next prompt
  - Example: `/to-impl Add error handling for edge cases`

- `/to-orch <message>` - Send message to orchestrator (Qwen/Codex)
  - Aliases: `/to-obra`, `/to-orchestrator`
  - Purpose depends on message content:
    - **Validation guidance**: Influences quality scoring
    - **Decision hints**: Adjusts decision thresholds
    - **Feedback requests**: Generates analysis for implementer
  - Examples:
    - `/to-orch Be more lenient with code style issues`
    - `/to-orch Accept this response despite warnings`
    - `/to-orch Review this code and suggest 3 improvements`
```

2. **Add examples section**:
```markdown
## Example Workflows

### Scenario 1: Guide Implementation
```
[ORCH→IMPL:claude-code] Iteration 1 | Prompt: 1,234 chars
[IMPL→ORCH] Response received | Turns: 1 | 5,678 chars
[ORCH:ollama] Quality: 0.65 (FAIL) | Decision: RETRY

User: /to-impl Focus on error handling in the validation logic
User: /to-orch Be more lenient on code coverage requirements

[ORCH→IMPL:claude-code] Iteration 2 | Prompt: 1,456 chars (with guidance)
[IMPL→ORCH] Response received | Turns: 2 | 6,123 chars
[ORCH:ollama] Quality: 0.78 (PASS) | Decision: PROCEED
✓ Task completed
```

### Scenario 2: Request Orchestrator Feedback
```
[ORCH→IMPL:claude-code] Iteration 1 | Prompt: 2,345 chars
[IMPL→ORCH] Response received | Turns: 3 | 8,901 chars
[ORCH:codex] Quality: 0.81 (PASS)

User: /to-orch Review the error handling and suggest improvements
[ORCH:codex] Generated feedback: Error handling looks good, but consider...
[ORCH:codex] (feedback injected into next implementer prompt)

User: /to-impl Incorporate the orchestrator's suggestions
[ORCH→IMPL:claude-code] Iteration 2 | Prompt: 3,456 chars (with feedback)
```
```

3. **Update display label documentation**:
```markdown
## Display Labels

All messages now show **role and model** for clarity:

- `[IMPL:claude-code]` - Implementer (Claude Code)
- `[ORCH:ollama]` - Orchestrator (Qwen via Ollama)
- `[ORCH:openai-codex]` - Orchestrator (OpenAI Codex)

**Backward Compatibility**: Old labels (`[QWEN]`, `[OBRA→CLAUDE]`) still work but are deprecated.
```

**Validation**:
- All docs updated with new terminology
- Examples show real-world usage
- Backward compatibility noted

---

#### Task 3.2: Write Tests

**File**: `tests/test_interactive_agent_messaging.py` (NEW)

**Test Coverage**:

1. **Test dynamic label generation**:
```python
def test_orch_label_ollama(orchestrator_with_ollama):
    """Test [ORCH:ollama] label when using Ollama."""
    llm_name = orchestrator_with_ollama.llm_interface.get_name()
    assert llm_name == 'ollama'

def test_orch_label_codex(orchestrator_with_codex):
    """Test [ORCH:openai-codex] label when using Codex."""
    llm_name = orchestrator_with_codex.llm_interface.get_name()
    assert llm_name == 'openai-codex'
```

2. **Test command aliases**:
```python
def test_to_impl_alias_to_claude(command_processor):
    """Test /to-claude alias for /to-impl."""
    result = command_processor.execute_command('/to-claude Add tests')
    assert result['success']
    assert 'implementer' in result['message']

def test_to_orch_alias_to_obra(command_processor):
    """Test /to-obra alias for /to-orch."""
    result = command_processor.execute_command('/to-obra Be lenient')
    assert result['success']
    assert 'orchestrator' in result['message']
```

3. **Test intent classification**:
```python
def test_orch_intent_validation_guidance(command_processor):
    """Test intent classification for validation guidance."""
    result = command_processor.execute_command('/to-orch Be more lenient with quality scores')
    assert result['success']
    assert command_processor.orchestrator.injected_context['to_orch_intent'] == 'validation_guidance'

def test_orch_intent_decision_hint(command_processor):
    """Test intent classification for decision hints."""
    result = command_processor.execute_command('/to-orch Accept this response')
    assert result['success']
    assert command_processor.orchestrator.injected_context['to_orch_intent'] == 'decision_hint'

def test_orch_intent_feedback_request(command_processor):
    """Test intent classification for feedback requests."""
    result = command_processor.execute_command('/to-orch Review and suggest improvements')
    assert result['success']
    assert command_processor.orchestrator.injected_context['to_orch_intent'] == 'feedback_request'
```

4. **Test message consumption**:
```python
def test_orch_message_applied_to_validation(orchestrator, monkeypatch):
    """Test orch message applied to validation prompt."""
    orchestrator.injected_context = {
        'to_orch': 'Be lenient',
        'to_orch_intent': 'validation_guidance'
    }

    base_prompt = "Validate this response."
    augmented = orchestrator._apply_orch_context(base_prompt, orchestrator.injected_context)

    assert 'Be lenient' in augmented
    assert 'USER GUIDANCE' in augmented

def test_feedback_generation(orchestrator, mock_llm):
    """Test orchestrator generates feedback for implementer."""
    orchestrator.injected_context = {
        'to_orch': 'Review and suggest 3 improvements',
        'to_orch_intent': 'feedback_request'
    }

    # Mock LLM response
    mock_llm.generate.return_value = "Feedback: 1. Add tests 2. Improve error handling 3. Refactor"

    # Trigger feedback generation (in actual execution loop)
    # ... implementation ...

    assert 'to_impl' in orchestrator.injected_context
    assert 'ORCHESTRATOR FEEDBACK' in orchestrator.injected_context['to_impl']
```

5. **Test backward compatibility**:
```python
def test_legacy_key_to_claude_still_works(orchestrator):
    """Test legacy 'to_claude' key still injected into prompt."""
    orchestrator.injected_context = {'to_claude': 'Legacy message'}

    base_prompt = "Do something"
    augmented = orchestrator._apply_injected_context(base_prompt, orchestrator.injected_context)

    assert 'Legacy message' in augmented

def test_legacy_streaming_handler_colors(streaming_handler):
    """Test legacy labels ([QWEN], [OBRA→CLAUDE]) still colored."""
    # OLD label should still get colored
    record = logging.LogRecord('test', logging.INFO, '', 0, '[QWEN] Quality: 0.8', (), None)

    # Should not crash and should apply color
    streaming_handler.emit(record)
```

**Validation**:
- All tests pass
- Edge cases covered (empty messages, long messages, etc.)
- Backward compatibility verified

---

#### Task 3.3: Manual Testing Checklist

**Interactive Session Test**:

1. Start interactive mode with Ollama:
   ```bash
   ./venv/bin/python -m src.cli task execute 1 --stream --interactive
   ```
   - [ ] Verify displays `[ORCH:ollama]` not `[QWEN]`
   - [ ] Test `/to-impl Add tests` - check message injected
   - [ ] Test `/to-orch Be lenient` - check intent classification
   - [ ] Test `/to-claude` alias - verify works same as `/to-impl`
   - [ ] Test `/to-obra` alias - verify works same as `/to-orch`

2. Switch config to OpenAI Codex and repeat:
   ```bash
   # Update config.yaml: llm.type: openai-codex
   ./venv/bin/python -m src.cli task execute 2 --stream --interactive
   ```
   - [ ] Verify displays `[ORCH:openai-codex]` not `[QWEN]`
   - [ ] All commands work same as with Ollama

3. Test feedback generation:
   ```bash
   # In interactive session
   /to-orch Review this code and suggest 3 specific improvements
   ```
   - [ ] Verify orchestrator generates feedback
   - [ ] Verify feedback injected into next implementer prompt
   - [ ] Check implementer response incorporates feedback

4. Test validation guidance:
   ```bash
   # During low quality iteration
   /to-orch Focus on code correctness over style
   ```
   - [ ] Verify next validation considers guidance
   - [ ] Check quality scores adjusted appropriately

5. Test decision hints:
   ```bash
   # When stuck in RETRY loop
   /to-orch Accept this response even though quality is 0.68
   ```
   - [ ] Verify decision changes to PROCEED despite low quality
   - [ ] Check threshold adjustment logged

---

## Risk Assessment

### Low Risk
- ✅ Dynamic label generation (cosmetic change)
- ✅ Command aliases (additive, preserves old commands)
- ✅ Intent classification (informational, doesn't break existing logic)

### Medium Risk
- ⚠️ Orch message consumption in validation (new prompt augmentation)
  - **Mitigation**: Test thoroughly with different LLMs
  - **Rollback**: Can disable orch context injection if issues arise
- ⚠️ Decision threshold adjustment (affects orchestration logic)
  - **Mitigation**: Conservative adjustment (-0.1), logged clearly
  - **Rollback**: Remove threshold_adjustment parameter

### High Risk
- ❌ None identified

---

## Success Criteria

### Must Have (Phase 1 + 2)
- ✅ Display shows `[ORCH:ollama]` when using Ollama
- ✅ Display shows `[ORCH:openai-codex]` when using Codex
- ✅ `/to-impl` command works (replaces `/to-claude`)
- ✅ `/to-orch` command works (enhances `/to-obra`)
- ✅ Backward compatibility: `/to-claude`, `/to-obra` still work
- ✅ All tests pass

### Should Have
- ✅ Intent classification accurate (>80%)
- ✅ Feedback generation produces useful output
- ✅ Validation guidance affects quality scores
- ✅ Decision hints adjust thresholds correctly
- ✅ Documentation complete and accurate

### Nice to Have
- ✅ Formal aliases (`/to-implementer`, `/to-orchestrator`)
- ✅ Real-world examples in docs
- ✅ Deprecation warnings for old commands

---

## Implementation Sequence

### Phase 1: Dynamic LLM Labels
- [ ] Task 1.1: Add `get_name()` to LLM interfaces (~20 lines)
- [ ] Task 1.2: Update orchestrator display methods (~80 lines)
- [ ] Task 1.3: Update streaming handler (~50 lines)
- [ ] Validation: Manual test with both LLMs

### Phase 2: Implement `/to-orch` Command
- [ ] Task 2.1: Rename commands and add aliases (~60 lines)
- [ ] Task 2.2: Rename and enhance message handlers (~120 lines)
- [ ] Task 2.3: Implement orchestrator message consumption (~170 lines)
- [ ] Validation: Test all three intents

### Phase 3: Documentation and Testing
- [ ] Task 3.1: Update documentation (~400 lines)
- [ ] Task 3.2: Write tests (~100 lines)
- [ ] Task 3.3: Manual testing checklist

**Total Code**: ~600 lines (modifications + new code)
**Total Documentation**: ~400 lines (updates to 3+ files)

---

## Rollback Plan

If issues arise, rollback is straightforward:

1. **Phase 1 (Labels)**:
   - Revert `_print_orch()` back to `_print_qwen()`
   - Restore hardcoded `[QWEN]` labels
   - Low impact (cosmetic only)

2. **Phase 2 (Orch messaging)**:
   - Remove `_apply_orch_context()` calls
   - Keep aliases but don't consume messages
   - Remove feedback generation logic
   - Medium impact (new feature removed)

**Backward Compatibility**: Never broken - old commands always work

---

## Future Enhancements

**Not in this plan** (future work):

1. **Persistent Preferences**: Save user's LLM guidance between sessions
2. **Orch-to-Impl Direct Chat**: Real-time conversation between agents
3. **Multi-Turn Feedback**: Iterative refinement with orchestrator
4. **Learning from Guidance**: Track which guidance improves quality
5. **Voice Commands**: `/to-impl` via voice input (for accessibility)

---

## User Approval Summary

**Q1: Terminology OK?** ✅ YES - Use `impl`/`implementer` and `orch`/`orchestrator`

**Q2: Three behaviors OK?** ✅ YES - Validation guidance, decision hints, feedback generation

**Q3: Timeline/Estimates?** ✅ UPDATED - Removed time estimates, using complexity/code length instead

**Q4: Anything missing?** ✅ NO - Plan approved as-is

**Q5: Update documentation?** ✅ YES - Update all docs to use new terminology (impl/orch)

---

## Related Documentation

- **Original Implementation**: `docs/development/INTERACTIVE_STREAMING_IMPLEMENTATION_PLAN.md`
- **ADR**: `docs/decisions/ADR-011-interactive-streaming-interface.md`
- **Quick Reference**: `docs/development/INTERACTIVE_STREAMING_QUICKREF.md`
- **Test Guidelines**: `docs/development/TEST_GUIDELINES.md`

---

## Implementation Kickoff

**Status**: ✅ APPROVED - Ready to begin implementation

**Start With**: Phase 1, Task 1.1 (Add `get_name()` to LLM interfaces)

**Key Files to Modify**:
1. `src/llm/local_interface.py` - Add `get_name()` method
2. `src/llm/openai_codex_interface.py` - Add `get_name()` method
3. `src/orchestrator.py` - Update display methods (`_print_qwen()` → `_print_orch()`)
4. `src/utils/streaming_handler.py` - Update color maps and format methods
5. `src/utils/command_processor.py` - Rename commands, implement `/to-orch` consumption
6. `src/utils/input_manager.py` - Update command list
7. `docs/development/INTERACTIVE_STREAMING_QUICKREF.md` - Update command reference
8. `tests/test_interactive_agent_messaging.py` - New test file

**Success Criteria**:
- Display shows `[ORCH:ollama]` or `[ORCH:codex]` based on actual LLM
- `/to-impl` and `/to-orch` commands functional
- All three orch message intents work (validation, decision, feedback)
- Backward compatibility preserved (old commands still work)
- All tests pass

**Last Updated**: November 5, 2025
