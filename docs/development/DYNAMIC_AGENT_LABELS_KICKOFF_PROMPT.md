# Dynamic Agent Labels and Messaging - Implementation Kickoff Prompt

**Purpose**: Copy-paste this prompt to start a fresh Claude session for implementation

---

## 📋 Kickoff Prompt (Copy Everything Below)

```
I need you to implement a feature for the Obra (Claude Code Orchestrator) project. This is an AI orchestration platform that uses local LLM reasoning (Qwen/Codex) with remote code generation (Claude Code CLI).

## Context Documents to Read

**CRITICAL - Read these first (in order)**:
1. `/home/omarwsl/projects/claude_code_orchestrator/CLAUDE.md` - Project overview and architecture
2. `/home/omarwsl/projects/claude_code_orchestrator/docs/development/DYNAMIC_AGENT_LABELS_AND_MESSAGING_PLAN.md` - Complete implementation plan (1246 lines)

## What We're Implementing

**Feature**: Dynamic Agent Labels and Orchestrator Messaging

**Two main improvements**:

### 1. Dynamic LLM Labels (Phase 1)
**Problem**: Display shows hardcoded `[QWEN]` even when using OpenAI Codex
**Solution**: Show actual LLM being used: `[ORCH:ollama]` or `[ORCH:codex]`

### 2. Orchestrator Messaging (Phase 2)
**Problem**: `/to-obra` command exists but doesn't work (stores messages but never uses them)
**Solution**: Implement three message behaviors:
- **Validation guidance**: Influences quality scoring
- **Decision hints**: Adjusts decision thresholds
- **Feedback requests**: Generates analysis for implementer

**Terminology**:
- `impl`/`implementer` = Claude Code (generates code)
- `orch`/`orchestrator` = Qwen/Codex (validates, scores, decides)

**Display format**: `[IMPL:claude-code]` and `[ORCH:ollama]` or `[ORCH:codex]`

## Start With Phase 1

**Implement these tasks in order**:

### Task 1.1: Add `get_name()` Method to LLM Interfaces (~20 lines)

**Files to modify**:
- `src/llm/local_interface.py`
- `src/llm/openai_codex_interface.py`

**What to add**:
```python
def get_name(self) -> str:
    """Get LLM name for display purposes.

    Returns:
        Short name (e.g., 'ollama', 'openai-codex')
    """
    return 'ollama'  # or 'openai-codex' for Codex
```

**Validation**: Both classes have `get_name()` method returning correct string

---

### Task 1.2: Update Orchestrator Display Methods (~80 lines)

**File to modify**: `src/orchestrator.py`

**Changes needed**:

1. **Rename `_print_qwen()` → `_print_orch()`** (line ~157-164):
   - Make it use `self.llm_interface.get_name()` dynamically
   - Output format: `[ORCH:ollama]` or `[ORCH:codex]`

2. **Add `_print_impl()` for symmetry**:
   - Similar to `_print_orch()` but for implementer
   - Output format: `[IMPL:claude-code]`

3. **Update all `_print_qwen()` calls** → `_print_orch()`

4. **Update logger calls** with dynamic labels (line ~1203):
   - Replace `[QWEN]` with `[ORCH:{llm_name}]`

**Validation**: All display methods use dynamic labels based on actual LLM

---

### Task 1.3: Update Streaming Handler (~50 lines)

**File to modify**: `src/utils/streaming_handler.py`

**Changes needed**:

1. **Update COLOR_MAP** (lines 32-44):
   - Add: `'[ORCH:': colorama.Fore.YELLOW` (pattern matching)
   - Add: `'[IMPL:': colorama.Fore.GREEN`
   - Keep old entries for backward compatibility

2. **Rename format methods**:
   - `format_qwen_validation()` → `format_orch_validation()` (add `llm_name` param)
   - `format_obra_to_claude()` → `format_orch_to_impl()` (add `impl_name` param)
   - Keep old methods as deprecated aliases

3. **Update module docstring** (lines 1-6):
   - Replace "Obra, Claude, Qwen" with "Orchestrator, Implementer"
   - Note dynamic labels

**Validation**: Color map recognizes new patterns, old labels still work

---

## After Phase 1

Run these validation steps:
1. Start Obra with Ollama config → should see `[ORCH:ollama]`
2. Switch to Codex config → should see `[ORCH:openai-codex]`
3. Old logs with `[QWEN]` should still display correctly

Then ask me: "Phase 1 complete. Should I proceed with Phase 2 (Implement `/to-orch` command)?"

## Important Notes

1. **Backward Compatibility**: Keep all old labels/commands working (aliases)
2. **Test as you go**: Validate each task before moving to next
3. **Follow the plan**: The implementation plan has complete code examples
4. **Code length estimates**: Phase 1 = ~150 lines, Phase 2 = ~350 lines, Phase 3 = ~500 lines
5. **Read CLAUDE.md**: Critical architecture principles (StateManager, validation order, etc.)

## Success Criteria for Phase 1

- ✅ `get_name()` methods added to both LLM interfaces
- ✅ `_print_orch()` and `_print_impl()` methods work with dynamic labels
- ✅ Streaming handler recognizes `[ORCH:*]` and `[IMPL:*]` patterns
- ✅ Backward compatibility: old labels still colored correctly
- ✅ No hardcoded "QWEN" or "Obra" in display logic

---

Please start with Task 1.1 and work through Phase 1 systematically. Let me know if you have questions about the architecture or implementation details.
```

---

**How to Use This Prompt**:

1. Copy everything between the triple backticks above
2. Open a fresh Claude Code session (or `/clear` to reset context)
3. Paste the entire prompt
4. Claude will read the docs and begin Phase 1 implementation

**Estimated Token Usage**: ~50k tokens after reading CLAUDE.md + implementation plan

**Last Updated**: November 5, 2025
