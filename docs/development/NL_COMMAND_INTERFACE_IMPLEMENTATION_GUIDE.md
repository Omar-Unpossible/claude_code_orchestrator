# Natural Language Command Interface - Implementation Guide

**Version:** 1.0.0
**Epic ID:** nl-command-v1
**Estimated Effort:** 8 sessions / 120 hours / 3 weeks
**Machine-Readable Spec:** [NL_COMMAND_INTERFACE_SPEC.json](./NL_COMMAND_INTERFACE_SPEC.json)

---

## Executive Summary

### Problem Statement
Users must memorize exact command syntax (`task create`, `epic list`, etc.) or receive only informational responses when using natural language. There is no automatic command execution from natural language input.

### Solution
Implement a **Unified Natural Language Interface** that combines:
- **Option 1**: NL Command Parser with LLM-based intent detection and entity extraction
- **Option 3**: Hybrid auto-detection (commands vs questions) for seamless UX

### Key Benefits
1. ✅ **Natural Conversation** - No syntax memorization required
2. ✅ **Auto-Detection** - System determines if input is a command or question
3. ✅ **Plugin-Agnostic** - Works with any LLM (Qwen, OpenAI, Claude, etc.)
4. ✅ **Schema-Aware** - Understands Obra's epic/story/task/subtask model
5. ✅ **Graceful Degradation** - Asks for clarification when uncertain

---

## Architecture Overview

### Pipeline Design

```
┌─────────────────────────────────────────────────────────────────┐
│                     User Natural Language Input                  │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  IntentClassifier (LLM Plugin)                                   │
│  ├─ Input: User message + context                               │
│  ├─ Output: COMMAND | QUESTION | CLARIFICATION_NEEDED           │
│  └─ Confidence: 0.0 - 1.0                                       │
└─────────────────────────┬───────────────────────────────────────┘
                          │
           ┌──────────────┼──────────────┐
           │              │              │
           ▼              ▼              ▼
     COMMAND         QUESTION    CLARIFICATION_NEEDED
           │              │              │
           ▼              ▼              ▼
┌──────────────────┐  ┌──────────┐  ┌─────────────────┐
│ EntityExtractor  │  │ Forward  │  │ Ask User for    │
│ (LLM Plugin)     │  │ to Claude│  │ Clarification   │
│ Schema-Aware     │  │ Code     │  │                 │
└────────┬─────────┘  └──────────┘  └─────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  CommandValidator                                                │
│  ├─ Validate entities against Obra schema                       │
│  ├─ Check business rules (epic exists, no cycles, etc.)         │
│  └─ Output: Valid command or errors                             │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  CommandExecutor                                                 │
│  ├─ Map to StateManager methods                                 │
│  ├─ Execute in transaction                                      │
│  └─ Rollback on error                                           │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  ResponseFormatter                                               │
│  ├─ Generate human-friendly response                            │
│  ├─ Color code (green=success, red=error)                       │
│  └─ Suggest next actions                                        │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
                   User Receives Response
```

### Component Responsibilities

| Component | Responsibility | LLM Required? | Plugin-Agnostic? |
|-----------|---------------|---------------|------------------|
| **IntentClassifier** | Classify intent as COMMAND/QUESTION/CLARIFICATION | ✅ Yes | ✅ Yes |
| **EntityExtractor** | Extract structured entities from NL using schema | ✅ Yes | ✅ Yes |
| **CommandValidator** | Validate entities against business rules | ❌ No | N/A |
| **CommandExecutor** | Execute via StateManager methods | ❌ No | N/A |
| **ResponseFormatter** | Generate human-friendly responses | ❌ No | N/A |
| **NLCommandProcessor** | Orchestrate entire pipeline | ❌ No | N/A |

---

## Implementation Plan: 5 Stories

### Story 1: Intent Classification Engine
**User Story:** As a user, I want Obra to automatically detect whether my message is a command or question, so I don't have to use specific syntax.

**Acceptance Criteria:**
- ✅ Intent classification accuracy >90% for COMMAND
- ✅ Intent classification accuracy >90% for QUESTION
- ✅ Returns CLARIFICATION_NEEDED when confidence <70%
- ✅ Works with Qwen, OpenAI, Claude (plugin-agnostic)
- ✅ P95 latency <2s

**Tasks:**
1. Design intent classification prompt templates (`prompts/intent_classification.j2`)
2. Implement `IntentClassifier` class (`src/nl/intent_classifier.py`)
3. Add confidence scoring with threshold logic
4. Write unit tests (`tests/test_intent_classifier.py`, 95% coverage)

**Test Cases:**
```json
{
  "input": "Create an epic called User Authentication",
  "expected_intent": "COMMAND",
  "expected_confidence": ">0.9"
}
{
  "input": "How do I create an epic?",
  "expected_intent": "QUESTION",
  "expected_confidence": ">0.9"
}
{
  "input": "Maybe add something",
  "expected_intent": "CLARIFICATION_NEEDED",
  "expected_confidence": "<0.7"
}
```

---

### Story 2: Schema-Aware Entity Extraction
**User Story:** As a user, I want Obra to understand epic/story/task details from my natural language, so I can describe work items conversationally.

**Acceptance Criteria:**
- ✅ Extracts epic title, description, metadata
- ✅ Extracts story details with epic_id references
- ✅ Extracts task details with story_id/epic_id references
- ✅ Handles multi-item commands ("create 3 stories...")
- ✅ Schema validation catches invalid references

**Tasks:**
1. Create Obra schema representation for LLM (`src/nl/schemas/obra_schema.json`)
2. Design entity extraction prompt templates (`prompts/entity_extraction.j2`)
3. Implement `EntityExtractor` class (`src/nl/entity_extractor.py`)
4. Add multi-item extraction support
5. Write unit tests (`tests/test_entity_extractor.py`, 95% coverage)

**Test Cases:**
```json
{
  "input": "Create an epic called 'User Auth' with description 'Complete authentication system'",
  "expected_entities": {
    "entity_type": "epic",
    "title": "User Auth",
    "description": "Complete authentication system"
  }
}
{
  "input": "Add 3 stories to the User Auth epic: login, signup, and MFA",
  "expected_entities": {
    "entity_type": "story",
    "count": 3,
    "epic_reference": "User Auth",
    "titles": ["login", "signup", "MFA"]
  }
}
```

---

### Story 3: Command Validation and Execution
**User Story:** As a user, I want my natural language commands to be validated and executed safely, so I can trust Obra to create work items correctly.

**Acceptance Criteria:**
- ✅ Validates all business rules before execution
- ✅ Calls correct StateManager methods
- ✅ Returns helpful error messages with recovery suggestions
- ✅ Requires confirmation for destructive operations
- ✅ Rolls back transactions on errors

**Tasks:**
1. Implement `CommandValidator` class (`src/nl/command_validator.py`)
2. Implement `CommandExecutor` class (`src/nl/command_executor.py`)
3. Add confirmation workflow for destructive ops
4. Add transaction safety with rollback
5. Write unit tests (`tests/test_command_validator.py`, `tests/test_command_executor.py`, 95% coverage)

**Validation Rules:**
- epic_id must exist if story references epic
- story_id must exist if task references story
- No circular dependencies in task dependencies
- Required fields must be present (title, description)
- Field types match schema (e.g., priority is int)

**Test Cases:**
```json
{
  "scenario": "Valid epic creation",
  "input": {"entity_type": "epic", "title": "New Feature"},
  "expected_result": "Epic created successfully"
}
{
  "scenario": "Invalid story reference",
  "input": {"entity_type": "story", "epic_id": 9999, "title": "Story"},
  "expected_result": "Validation error: Epic 9999 not found"
}
{
  "scenario": "Circular dependency",
  "input": {"entity_type": "task", "dependencies": [1, 2], "id": 1},
  "expected_result": "Validation error: Circular dependency detected"
}
```

---

### Story 4: Response Formatting and User Feedback
**User Story:** As a user, I want clear, actionable responses from Obra after executing commands, so I know exactly what happened.

**Acceptance Criteria:**
- ✅ Success messages show created IDs and next actions
- ✅ Error messages are human-friendly with recovery suggestions
- ✅ Clarification requests are specific and actionable
- ✅ Confirmation prompts clearly state what will happen
- ✅ Color coding (green=success, red=error, yellow=warning)

**Tasks:**
1. Implement `ResponseFormatter` class (`src/nl/response_formatter.py`)
2. Add response templates for all scenarios (`prompts/responses/*.j2`)
3. Integrate colorama for colored output
4. Write unit tests (`tests/test_response_formatter.py`, 95% coverage)

**Response Examples:**
```
✓ Created Epic #5: User Auth
  Next: Add stories with 'add story to epic 5'

✗ Error: Epic not found
  Try listing epics with 'show epics'

⚠ This will delete Epic #5 and all 12 stories. Confirm? (y/n)

? Did you mean:
  1. Create epic 'User Dashboard'
  2. List existing epics
  3. Something else (please clarify)
```

---

### Story 5: NL Command Pipeline Integration
**User Story:** As a user, I want seamless NL command processing in interactive mode, so I can work with Obra naturally.

**Acceptance Criteria:**
- ✅ NLCommandProcessor integrates with existing CommandProcessor
- ✅ Interactive mode routes messages through NL pipeline
- ✅ Conversation context preserved across turns
- ✅ Graceful fallback to informational responses for pure questions
- ✅ P95 end-to-end latency <3s

**Tasks:**
1. Implement `NLCommandProcessor` orchestrator (`src/nl/nl_command_processor.py`)
2. Integrate with `CommandProcessor` (`src/utils/command_processor.py`)
3. Add conversation context management
4. Add configuration options for NL features
5. Write integration tests (`tests/integration/test_nl_pipeline.py`, 90% coverage)
6. Write user documentation (`docs/guides/NL_COMMAND_GUIDE.md`)

**E2E Scenarios:**
```
Scenario: Create epic + stories in conversation
Turn 1:
  User: "Create an epic for user authentication"
  Obra: "✓ Created Epic #5: User Authentication"

Turn 2:
  User: "Add 3 stories: login, signup, MFA"
  Obra: "✓ Created 3 stories under Epic #5:
         - Story #6: Login
         - Story #7: Signup
         - Story #8: MFA"

Scenario: Question + command mixed
Turn 1:
  User: "How many epics do I have?"
  Obra: "You have 2 epics:
         - Epic #4: Admin Dashboard (3 stories)
         - Epic #5: User Authentication (3 stories)"

Turn 2:
  User: "Create one more epic for reporting"
  Obra: "✓ Created Epic #6: Reporting"
```

---

## Technical Specifications

### File Structure
```
src/nl/
├── __init__.py
├── intent_classifier.py       # Story 1
├── entity_extractor.py        # Story 2
├── command_validator.py       # Story 3
├── command_executor.py        # Story 3
├── response_formatter.py      # Story 4
├── nl_command_processor.py    # Story 5
└── schemas/
    └── obra_schema.json       # Story 2

prompts/
├── intent_classification.j2   # Story 1
├── entity_extraction.j2       # Story 2
└── responses/
    ├── success.j2             # Story 4
    ├── error.j2               # Story 4
    ├── confirmation.j2        # Story 4
    └── clarification.j2       # Story 4

tests/
├── test_intent_classifier.py
├── test_entity_extractor.py
├── test_command_validator.py
├── test_command_executor.py
├── test_response_formatter.py
├── test_nl_command_processor.py
└── integration/
    ├── test_nl_pipeline.py
    ├── test_nl_intent.py
    ├── test_nl_extraction.py
    └── test_nl_execution.py

docs/guides/
└── NL_COMMAND_GUIDE.md        # Story 5
```

### API Contracts

#### IntentClassifier
```python
class IntentClassifier:
    def __init__(self, llm_plugin: LLMPlugin, confidence_threshold: float = 0.7):
        """Initialize intent classifier with LLM plugin."""

    def classify(self, message: str, context: dict = None) -> IntentResult:
        """Classify user intent.

        Returns:
            IntentResult(
                intent='COMMAND' | 'QUESTION' | 'CLARIFICATION_NEEDED',
                confidence=0.0-1.0,
                detected_entities={}
            )
        """
```

#### EntityExtractor
```python
class EntityExtractor:
    def __init__(self, llm_plugin: LLMPlugin, schema_path: str):
        """Initialize with LLM plugin and Obra schema."""

    def extract(self, message: str, intent: str) -> ExtractedEntities:
        """Extract entities from NL using schema awareness.

        Returns:
            ExtractedEntities(
                entity_type='epic' | 'story' | 'task' | 'subtask' | 'milestone',
                entities=[{...}],
                confidence=0.0-1.0
            )
        """
```

#### CommandValidator
```python
class CommandValidator:
    def __init__(self, state_manager: StateManager):
        """Initialize with StateManager for validation lookups."""

    def validate(self, entities: ExtractedEntities) -> ValidationResult:
        """Validate extracted entities against business rules.

        Returns:
            ValidationResult(
                valid=True/False,
                errors=[...],
                warnings=[...],
                validated_command={...}
            )
        """
```

#### CommandExecutor
```python
class CommandExecutor:
    def __init__(self, state_manager: StateManager):
        """Initialize with StateManager for execution."""

    def execute(self, validated_command: dict) -> ExecutionResult:
        """Execute validated command via StateManager.

        Returns:
            ExecutionResult(
                success=True/False,
                created_ids=[...],
                errors=[...],
                results={...}
            )
        """
```

#### ResponseFormatter
```python
class ResponseFormatter:
    def format(self, execution_result: ExecutionResult, intent: str) -> str:
        """Format execution result as human-friendly response with colors."""
```

#### NLCommandProcessor
```python
class NLCommandProcessor:
    def __init__(self, llm_plugin: LLMPlugin, state_manager: StateManager, config: Config):
        """Initialize NL command processor with all dependencies."""

    def process(self, message: str, context: dict = None) -> NLResponse:
        """Process NL message through entire pipeline.

        Returns:
            NLResponse(
                response=str,
                intent=str,
                success=bool,
                updated_context=dict
            )
        """
```

### Configuration Schema

Add to `config.yml`:
```yaml
nl_commands:
  enabled: true                    # Master kill switch
  llm_provider: "ollama"          # LLM provider for NL processing
  confidence_threshold: 0.7       # Threshold for CLARIFICATION_NEEDED
  max_context_turns: 10           # Max conversation history
  require_confirmation_for:       # Operations requiring confirmation
    - delete
    - update
    - execute
  fallback_to_info: true         # Fallback to Claude Code for questions
```

---

## Testing Strategy

### Test Levels

| Level | Coverage Target | Mock Strategy |
|-------|----------------|---------------|
| **Unit** | 95% | Mock LLMPlugin and StateManager |
| **Integration** | 90% | Real LLMPlugin, mock StateManager DB |
| **E2E** | 80% | Full stack with test DB and real LLM |

### Test Data Requirements
- **Intent classification samples:** 50 diverse messages
- **Entity extraction samples:** 100 varied NL inputs
- **Validation edge cases:** 30 scenarios
- **Execution scenarios:** 40 test cases

### Performance Benchmarks
- **Intent classification P95 latency:** <2s
- **Entity extraction P95 latency:** <2.5s
- **End-to-end P95 latency:** <3s
- **Intent classification accuracy:** >95%
- **Entity extraction accuracy:** >90%

---

## Recommendation: Unified Hybrid Approach

### Decision: Implement Option 1 + Option 3

**Rationale:**
1. **Better UX:** Users shouldn't have to think about "command mode" vs "question mode"
2. **Single Intent Classification:** One LLM call determines routing (COMMAND vs QUESTION)
3. **Graceful Degradation:** Uncertain intent → ask for clarification (don't guess)
4. **No Additional Complexity:** Same architecture handles both use cases

### Option 3 Features Included

| Feature | Reason | Implementation |
|---------|--------|----------------|
| **Automatic intent detection** | Seamless UX | IntentClassifier outputs COMMAND/QUESTION/CLARIFICATION |
| **Context-aware disambiguation** | Multi-turn conversations | Conversation history in context parameter |
| **Confirmation for destructive ops** | Safety | CommandExecutor checks operation type |
| **Graceful degradation** | Don't guess | Confidence <70% → ask for clarification |

### LLM Optimization (Optional Future Enhancement)

**Recommendation:** Use separate LLM models for intent vs extraction
- **Intent classification:** Simpler, faster model (e.g., llama-3.2-3b)
- **Entity extraction:** More capable model (e.g., Qwen 2.5 Coder 32B)

**Rationale:** Intent is simple 3-way classification, extraction is complex schema-aware generation

**Configuration:**
```yaml
nl_commands:
  intent_llm_provider: "ollama"
  intent_model: "llama3.2:3b"      # Fast classification
  extraction_llm_provider: "ollama"
  extraction_model: "qwen2.5-coder:32b"  # Accurate extraction
```

---

## Risks and Mitigations

| Risk | Severity | Mitigation | Fallback |
|------|----------|------------|----------|
| **LLM hallucinations creating incorrect entities** | High | Multi-stage validation, confidence thresholds, confirmations | If confidence <70%, ask clarification |
| **Latency exceeds tolerance (>5s)** | Medium | Optimize prompts, cache schema, parallel calls | Show loading indicator, allow cancel |
| **Plugin compatibility across LLM providers** | Medium | Test with Qwen, OpenAI, Claude early | Provider-specific prompt templates |
| **User confusion between modes** | Low | Clear feedback on actions, undo option | User can disable NL via config |

---

## Success Metrics

### Quantitative Metrics
- ✅ Intent classification accuracy >95%
- ✅ Entity extraction accuracy >90%
- ✅ End-to-end success rate >85%
- ✅ P95 latency <3s
- ✅ Test coverage >90%

### Qualitative Metrics
- ✅ User satisfaction: Positive feedback from 80%+ users
- ✅ Reduced syntax errors: 50% reduction in command syntax errors
- ✅ Adoption rate: 60%+ users prefer NL over slash commands

---

## Migration and Rollout

### Backward Compatibility
- ✅ **Existing slash commands:** No changes - continue to work
- ✅ **Existing conversational mode:** Enhanced with NL execution, fallback to info
- ✅ **Config migration:** Add `nl_commands` section, optional for users

### Rollout Phases

| Phase | Name | Features | Users | Success Criteria |
|-------|------|----------|-------|------------------|
| **1** | Alpha - Internal Testing | Intent + basic extraction | Dev team only | 90% intent accuracy |
| **2** | Beta - Limited Release | Full NL pipeline | Opt-in via config | No critical bugs, 85% satisfaction |
| **3** | GA - General Availability | All NL commands | All users (enabled by default) | 95% uptime, <3s p95 latency |

### Feature Flags
```yaml
nl_commands:
  enabled: true                    # Master kill switch
  experimental_features: false    # For testing new capabilities
```

---

## Getting Started (After Implementation)

### For Users
```bash
# Enable NL commands (will be enabled by default in GA)
obra config set nl_commands.enabled true

# Start interactive mode
python -m src.cli interactive

# Use natural language!
orchestrator> Create an epic for user authentication with 3 stories: login, signup, and password reset
```

### For Developers
```bash
# Run unit tests
pytest tests/test_intent_classifier.py -v
pytest tests/test_entity_extractor.py -v

# Run integration tests
pytest tests/integration/test_nl_pipeline.py -v

# Test with different LLM providers
OBRA_LLM_PROVIDER=openai pytest tests/test_intent_classifier.py
OBRA_LLM_PROVIDER=claude pytest tests/test_intent_classifier.py
```

---

## Next Steps

1. **Review this specification** with stakeholders
2. **Create Epic in Obra** using this plan:
   ```bash
   python -m src.cli epic create "Natural Language Command Interface" \
     --description "Implement unified NL interface with auto-detection"
   ```
3. **Create 5 Stories** from this plan (one per story above)
4. **Execute Story 1** (Intent Classification Engine) first
5. **Iterate** through stories sequentially (dependencies enforced)

---

**Questions or feedback?** Update this document or create issues in the repository.

**Ready to execute?** Feed `NL_COMMAND_INTERFACE_SPEC.json` to Obra for automated orchestration! 🚀
