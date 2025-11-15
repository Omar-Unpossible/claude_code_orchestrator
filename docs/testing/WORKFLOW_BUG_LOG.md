# Workflow Testing Bug Log

**Date:** November 15, 2025
**Test:** Delete all projects via interactive REPL
**LLM:** OpenAI Codex
**Tag:** v1.7.3-pre-workflow-test

---

## Test Objective

Test real-world workflow:
1. Start Obra in interactive REPL mode
2. Use natural language command: "delete all projects"
3. Document any bugs encountered
4. Fix bugs and retry
5. Verify successful deletion

## Pre-Test State

**Projects in database:** 15 total
- Project 1-15: Various CLI smoke tests and manual tests
- All are test projects that can be safely deleted

**Environment:**
- LLM: OpenAI Codex (via ORCHESTRATOR_LLM_TYPE env var)
- Database: ~/obra-runtime/data/orchestrator.db
- Venv: Activated

---

## Test Execution Log

### Attempt 1: Initial Test

**Time:** 14:44:21

**Command:** `python -m src.cli interactive` with Ollama/Qwen LLM

**Expected Result:**
- Interactive REPL starts  - Natural language command "delete all projects" is processed
- All 15 projects are deleted
- Confirmation of deletion

**Actual Result:**
- ✅ Interactive REPL started successfully
- ✅ Command "list all projects" worked (validated NL pipeline)
- ❌ Command "delete all projects" FAILED with JSON parsing error

**Error:**
```
ValueError: Invalid JSON in LLM response: substring not found
  File "src/nl/intent_classifier.py", line 294, in _parse_llm_response
    end = response.rindex('}') + 1
```

**Issues Found:** Bug #1 - LLM response parsing failure

---

## Bugs Discovered

### Bug #1: JSON Parsing Failure in IntentClassifier

**Description:**
The IntentClassifier fails to parse LLM responses that don't contain proper JSON formatting. The `_parse_llm_response()` method assumes the response contains a closing `}` bracket, causing a ValueError when it doesn't.

**Root Cause:**
- `intent_classifier.py:294` uses `response.rindex('}')` without error handling
- LLM (Ollama/Qwen) sometimes returns incomplete or malformed JSON
- No fallback mechanism when JSON extraction fails

**Location:** `src/nl/intent_classifier.py:294`

**Fix Strategy:**
1. Add robust JSON extraction with multiple fallback strategies
2. Handle edge cases: no brackets, incomplete JSON, plain text responses
3. Add logging of malformed responses for debugging
4. Consider retry logic or prompt refinement

**Fix Applied:**
1. Improved error logging in `intent_classifier.py:290-311` to show actual LLM response
2. Updated prompt template `prompts/intent_classification.j2`:
   - Changed instruction from "no markdown" to "no markdown code fences"
   - Removed all ```json``` code fences from examples
3. **CRITICAL**: Removed stop sequences from `intent_classifier.py:204`
   - Old: `stop=["\n```", "}\n", "}\r\n"]`
   - Problem: `}\n` was matching closing braces of nested objects
   - New: No stop sequences (let LLM complete naturally)
   - Increased max_tokens from 100 to 200

**Status:** ✅ FIXED - Intent classification now works correctly

---

### Bug #2: Bulk DELETE Not Implemented

**Description:**
After successful NL parsing of "delete all projects", execution fails with:
```
⚠ No project selected. Use /project list to see projects or /project create to create one
```

**Root Cause:**
- NL pipeline correctly identifies bulk DELETE operation (identifier=`__ALL__`)
- Command validation passes
- But execution layer doesn't handle bulk deletion
- Likely missing implementation in command executor or orchestrator

**NL Processing Success:**
- ✅ Intent: COMMAND (0.94)
- ✅ Operation: DELETE (1.00)
- ✅ Entity: project (0.90)
- ✅ Identifier: __ALL__ (0.95, bulk operation)
- ✅ Validation: Passed

**Location:** Command execution layer (src/nl/command_executor.py or src/orchestrator.py)

**Status:** IDENTIFIED - Fix needed

---

## Final Status

**Status:** IN PROGRESS

**Projects Deleted:** 0/15

**Bugs Fixed:** 0

**Retry Attempts:** 0
