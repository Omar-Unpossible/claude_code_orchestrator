# NL Command Interface - Obra Execution Kickoff Prompt

**Purpose:** This prompt can be fed to Obra to automatically create and execute the Natural Language Command Interface epic.

---

## Automated Epic Creation Prompt

```
Create an epic titled "Natural Language Command Interface" with the following specification:

EPIC DESCRIPTION:
Implement a unified natural language interface that automatically detects user intent (commands vs questions) and executes commands via LLM-based entity extraction and validation. This combines Option 1 (NL Command Parser) with Option 3 (Hybrid Auto-Detection) for optimal user experience.

TECHNICAL APPROACH:
- Plugin-agnostic LLM integration (works with Qwen, OpenAI, Claude, etc.)
- Pipeline architecture: IntentClassifier → EntityExtractor → CommandValidator → CommandExecutor → ResponseFormatter
- Schema-aware entity extraction using Obra data model
- Multi-stage validation with confidence thresholds
- Graceful degradation (asks for clarification when uncertain)

COMPLETE SPECIFICATION:
See docs/development/NL_COMMAND_INTERFACE_SPEC.json for machine-readable specification
See docs/development/NL_COMMAND_INTERFACE_IMPLEMENTATION_GUIDE.md for human-readable guide

CREATE 5 STORIES:

STORY 1: Intent Classification Engine
Title: "Intent Classification Engine"
Description: "As a user, I want Obra to automatically detect whether my message is a command or question, so I don't have to use specific syntax"
Tasks:
1. Design intent classification prompt templates (prompts/intent_classification.j2)
2. Implement IntentClassifier class (src/nl/intent_classifier.py)
3. Add confidence scoring logic with 70% threshold for CLARIFICATION_NEEDED
4. Write unit tests (tests/test_intent_classifier.py, 95% coverage)
Acceptance Criteria:
- Intent classification accuracy >90% for COMMAND
- Intent classification accuracy >90% for QUESTION
- Returns CLARIFICATION_NEEDED when confidence <70%
- Works with Qwen, OpenAI, Claude (plugin-agnostic)
- P95 latency <2s

STORY 2: Schema-Aware Entity Extraction
Title: "Schema-Aware Entity Extraction"
Description: "As a user, I want Obra to understand epic/story/task details from my natural language, so I can describe work items conversationally"
Tasks:
1. Create Obra schema representation for LLM (src/nl/schemas/obra_schema.json)
2. Design entity extraction prompt templates (prompts/entity_extraction.j2)
3. Implement EntityExtractor class (src/nl/entity_extractor.py)
4. Add multi-item extraction support (handle "create 3 stories...")
5. Write unit tests (tests/test_entity_extractor.py, 95% coverage)
Acceptance Criteria:
- Extracts epic title, description, metadata
- Extracts story details with epic_id references
- Extracts task details with story_id/epic_id references
- Handles multi-item commands
- Schema validation catches invalid references

STORY 3: Command Validation and Execution
Title: "Command Validation and Execution"
Description: "As a user, I want my natural language commands to be validated and executed safely, so I can trust Obra to create work items correctly"
Tasks:
1. Implement CommandValidator class (src/nl/command_validator.py)
2. Implement CommandExecutor class (src/nl/command_executor.py)
3. Add confirmation workflow for destructive operations
4. Add transaction safety with rollback on error
5. Write unit tests (tests/test_command_validator.py, tests/test_command_executor.py, 95% coverage)
Acceptance Criteria:
- Validates all business rules before execution
- Calls correct StateManager methods
- Returns helpful error messages with recovery suggestions
- Requires confirmation for destructive operations
- Rolls back transactions on errors

STORY 4: Response Formatting and User Feedback
Title: "Response Formatting and User Feedback"
Description: "As a user, I want clear, actionable responses from Obra after executing commands, so I know exactly what happened"
Tasks:
1. Implement ResponseFormatter class (src/nl/response_formatter.py)
2. Add response templates for all scenarios (prompts/responses/*.j2)
3. Integrate colorama for colored output
4. Write unit tests (tests/test_response_formatter.py, 95% coverage)
Acceptance Criteria:
- Success messages show created IDs and next actions
- Error messages are human-friendly with recovery suggestions
- Clarification requests are specific and actionable
- Confirmation prompts clearly state what will happen
- Color coding (green=success, red=error, yellow=warning)

STORY 5: NL Command Pipeline Integration
Title: "NL Command Pipeline Integration"
Description: "As a user, I want seamless NL command processing in interactive mode, so I can work with Obra naturally"
Tasks:
1. Implement NLCommandProcessor orchestrator (src/nl/nl_command_processor.py)
2. Integrate with CommandProcessor (update src/utils/command_processor.py)
3. Add conversation context management
4. Add configuration options for NL features
5. Write integration tests (tests/integration/test_nl_pipeline.py, 90% coverage)
6. Write user documentation (docs/guides/NL_COMMAND_GUIDE.md)
Acceptance Criteria:
- NLCommandProcessor integrates with existing CommandProcessor
- Interactive mode routes messages through NL pipeline
- Conversation context preserved across turns
- Graceful fallback to informational responses for pure questions
- P95 end-to-end latency <3s

EXECUTION ORDER:
Story 1 → Story 2 → Story 3 → Story 4 → Story 5
(Stories 1 and 2 can be done in parallel, Story 3 depends on both, Stories 4 and 5 depend on Story 3)

ESTIMATED EFFORT:
- Total Stories: 5
- Total Tasks: 24
- Estimated Hours: 120
- Estimated Sessions: 8
- Timeline: 3 weeks

SUCCESS METRICS:
- Intent classification accuracy >95%
- Entity extraction accuracy >90%
- End-to-end success rate >85%
- P95 latency <3s
- Test coverage >90%
- User satisfaction >80%

CONFIGURATION ADDITIONS:
Add to config.yml:
```yaml
nl_commands:
  enabled: true
  llm_provider: "ollama"
  confidence_threshold: 0.7
  max_context_turns: 10
  require_confirmation_for: ["delete", "update", "execute"]
  fallback_to_info: true
```

DELIVERABLES:
Code:
- src/nl/ module with 6 core classes
- Updated src/utils/command_processor.py
- Prompt templates in prompts/
- Configuration schema updates

Tests:
- 6 unit test files (95% coverage)
- 4 integration test files (90% coverage)
- 1 E2E test file (80% coverage)

Documentation:
- docs/guides/NL_COMMAND_GUIDE.md (user guide)
- docs/architecture/NL_COMMAND_ARCHITECTURE.md (technical architecture)
- docs/decisions/ADR-014-natural-language-command-interface.md (decision record)

After epic creation, execute Story 1 first to establish the intent classification foundation.
```

---

## Alternative: CLI Command Sequence

If you prefer to create the epic via CLI commands instead of feeding the prompt to Obra:

```bash
# 1. Create the epic
python -m src.cli epic create \
  --title "Natural Language Command Interface" \
  --description "Implement unified NL interface with auto-detection. See docs/development/NL_COMMAND_INTERFACE_SPEC.json for complete specification."

# 2. Create Story 1
python -m src.cli story create \
  --epic-id <EPIC_ID_FROM_STEP_1> \
  --title "Intent Classification Engine" \
  --description "As a user, I want Obra to automatically detect whether my message is a command or question, so I don't have to use specific syntax"

# 3. Create Story 2
python -m src.cli story create \
  --epic-id <EPIC_ID_FROM_STEP_1> \
  --title "Schema-Aware Entity Extraction" \
  --description "As a user, I want Obra to understand epic/story/task details from my natural language, so I can describe work items conversationally"

# 4. Create Story 3
python -m src.cli story create \
  --epic-id <EPIC_ID_FROM_STEP_1> \
  --title "Command Validation and Execution" \
  --description "As a user, I want my natural language commands to be validated and executed safely, so I can trust Obra to create work items correctly"

# 5. Create Story 4
python -m src.cli story create \
  --epic-id <EPIC_ID_FROM_STEP_1> \
  --title "Response Formatting and User Feedback" \
  --description "As a user, I want clear, actionable responses from Obra after executing commands, so I know exactly what happened"

# 6. Create Story 5
python -m src.cli story create \
  --epic-id <EPIC_ID_FROM_STEP_1> \
  --title "NL Command Pipeline Integration" \
  --description "As a user, I want seamless NL command processing in interactive mode, so I can work with Obra naturally"

# 7. Execute the entire epic
python -m src.cli epic execute <EPIC_ID_FROM_STEP_1>
```

---

## Execution Notes

**Before Execution:**
1. Review `NL_COMMAND_INTERFACE_SPEC.json` for complete machine-readable specification
2. Review `NL_COMMAND_INTERFACE_IMPLEMENTATION_GUIDE.md` for human-readable guide
3. Ensure Ollama is running with Qwen 2.5 Coder model (or configure alternative LLM provider)
4. Verify test environment is set up (pytest, test database, etc.)

**During Execution:**
- Obra will create tasks from the story descriptions automatically
- Each story should be executed sequentially (dependencies enforced)
- Tests must pass before moving to next story (95% coverage requirement)
- Interactive checkpoints will allow you to review progress and provide feedback

**After Completion:**
- Create ADR-014 documenting the architectural decision
- Update CHANGELOG.md with new feature
- Create migration guide for users
- Announce feature in release notes

---

**Ready to execute?** Copy the "Automated Epic Creation Prompt" above and send it to Obra in interactive mode, or use the CLI command sequence!
