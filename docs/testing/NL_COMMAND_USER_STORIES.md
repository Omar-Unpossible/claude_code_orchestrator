# Natural Language Command System - User Stories for Testing

**Purpose:** Define expected behaviors for the NL command system to enable comprehensive automated testing and catch integration bugs before manual testing.

**Context:** The NL command system (intent classification, entity extraction, command execution) currently has **0% test coverage**, leading to runtime bugs that should be caught in testing.

**Test Target:** Create test cases covering these stories to achieve ≥85% coverage for:
- `src/nl/intent_classifier.py`
- `src/nl/entity_extractor.py`
- `src/nl/command_validator.py`
- `src/nl/command_executor.py`
- `src/nl/response_formatter.py`
- `src/nl/nl_command_processor.py`

---

## Category 1: Project-Level Queries (Information Retrieval)

### US-NL-001: Query Current Project Information
**As a** user
**I want to** ask "What is the current project?"
**So that** I can see the active project name, ID, and working directory

**Acceptance Criteria:**
- ✅ Intent classified as `COMMAND`
- ✅ Entity type recognized as `project` (not epic/story/task)
- ✅ Returns project name, ID, working directory
- ✅ Gracefully handles case when no project is active
- ✅ Response formatted with color coding

**Test Variations:**
```
"What is the current project?"
"Show me the active project"
"Which project am I working on?"
"Project info"
"Current project status"
```

**Bug Reference:** This story covers the bug where `entity_type=None` caused ValueError. System must handle project-level queries without requiring specific work item types.

**Edge Cases:**
- No active project (should return helpful message)
- Multiple projects exist (should show current one)
- Project has no work items yet

---

### US-NL-002: Query Project Statistics
**As a** user
**I want to** ask "Show me project statistics"
**So that** I can see counts of epics, stories, tasks, and completion rates

**Acceptance Criteria:**
- ✅ Intent classified as `COMMAND`
- ✅ Returns counts: total epics, stories, tasks
- ✅ Shows completion percentages per type
- ✅ Displays recent activity (last 5 updates)
- ✅ Handles empty project (0 work items)

**Test Variations:**
```
"Show project stats"
"How many tasks do I have?"
"Project summary"
"What's the overall progress?"
```

---

### US-NL-003: Query Recent Activity
**As a** user
**I want to** ask "What happened recently?"
**So that** I can see the last N updates/changes to work items

**Acceptance Criteria:**
- ✅ Intent classified as `COMMAND`
- ✅ Returns last 10 events by default
- ✅ Supports parameterization ("last 5 updates")
- ✅ Shows timestamp, work item, and action
- ✅ Handles case with no recent activity

**Test Variations:**
```
"What happened recently?"
"Show me recent activity"
"Last 5 changes"
"Recent updates"
"Activity log"
```

---

## Category 2: Work Item Hierarchy Queries

### US-NL-004: Query Current Epic/Story/Task Status
**As a** user
**I want to** ask "What is the current epic?"
**So that** I can see the active epic and its child stories/tasks

**Acceptance Criteria:**
- ✅ Intent classified as `COMMAND`
- ✅ Entity type recognized as `epic`
- ✅ Returns epic title, description, status
- ✅ Shows child stories (count and status breakdown)
- ✅ Handles case when no epic is active

**Test Variations:**
```
"What is the current epic?"
"Show me the active story"
"What task am I on?"
"Current epic status"
"Which story is in progress?"
```

**Edge Cases:**
- No active epic (should suggest creating one or list available epics)
- Multiple in-progress epics (should clarify which one)
- Epic with no stories yet

---

### US-NL-005: Query Work Item Hierarchy (Tree View)
**As a** user
**I want to** ask "Show me the epic hierarchy"
**So that** I can see the tree structure of epic → stories → tasks

**Acceptance Criteria:**
- ✅ Intent classified as `COMMAND`
- ✅ Displays tree structure with indentation
- ✅ Shows status indicators (✓, ⏳, ✗) per item
- ✅ Supports filtering by status (e.g., "show pending tasks")
- ✅ Handles deep nesting (subtasks)

**Test Variations:**
```
"Show epic hierarchy"
"Task tree for epic 5"
"What are the child tasks of story 12?"
"Show me all pending work items"
```

---

### US-NL-006: Query Specific Work Item by ID
**As a** user
**I want to** ask "Show me task 42"
**So that** I can see detailed info about a specific work item

**Acceptance Criteria:**
- ✅ Intent classified as `COMMAND`
- ✅ Entity extraction identifies ID: 42
- ✅ Returns full details (title, description, status, dependencies)
- ✅ Shows parent/child relationships
- ✅ Handles invalid ID (graceful error)

**Test Variations:**
```
"Show task 42"
"Details for epic 3"
"Info about story 15"
"Task #42 status"
"What is epic 7?"
```

**Edge Cases:**
- ID doesn't exist (suggest similar IDs or list all)
- Ambiguous reference ("task 5" when there are multiple projects)

---

### US-NL-007: Query Work Item by Name/Title
**As a** user
**I want to** ask "Show me the authentication epic"
**So that** I can find work items by fuzzy name matching

**Acceptance Criteria:**
- ✅ Intent classified as `COMMAND`
- ✅ Entity extraction identifies name: "authentication"
- ✅ Performs fuzzy matching (handles typos/partial matches)
- ✅ Returns best match or top 3 candidates
- ✅ Asks for clarification if multiple matches

**Test Variations:**
```
"Show authentication epic"
"Find task about database migration"
"Where is the login story?"
"Task called unit tests"
```

**Edge Cases:**
- No matches (suggest creating new work item)
- Multiple exact matches (clarify by ID or parent)
- Very generic names ("test", "fix bug")

---

## Category 3: Work Item Creation & Modification

### US-NL-008: Create New Work Items
**As a** user
**I want to** say "Create an epic for user authentication"
**So that** Obra creates the work item and returns its ID

**Acceptance Criteria:**
- ✅ Intent classified as `COMMAND`
- ✅ Entity extraction identifies: type=epic, title="user authentication"
- ✅ Creates work item in database
- ✅ Returns confirmation with new ID
- ✅ Validates required fields (prompts if missing)

**Test Variations:**
```
"Create an epic for user authentication"
"Add a story: implement OAuth login"
"New task: write unit tests for auth module"
"Make a subtask to refactor login function"
```

**Edge Cases:**
- Missing required fields (project_id, title)
- Invalid parent references (epic_id for story doesn't exist)
- Duplicate titles (warn and ask to confirm)

---

### US-NL-009: Update/Modify Existing Work Items
**As a** user
**I want to** say "Update task 42 status to completed"
**So that** Obra modifies the work item and confirms the change

**Acceptance Criteria:**
- ✅ Intent classified as `COMMAND`
- ✅ Entity extraction identifies: ID=42, field=status, value=completed
- ✅ Updates database record
- ✅ Returns confirmation with updated values
- ✅ Validates field names and values

**Test Variations:**
```
"Mark task 42 as completed"
"Change epic 5 title to User Management"
"Update story 12 description: Add OAuth support"
"Set task 8 priority to high"
```

**Edge Cases:**
- Invalid status transitions (pending → completed skipping in-progress)
- Read-only fields (e.g., created_at)
- Type mismatches (setting status to numeric value)

---

### US-NL-010: Amend/Adjust the Plan
**As a** user
**I want to** say "Add dependency: task 15 depends on task 12"
**So that** Obra updates task relationships and validates no cycles

**Acceptance Criteria:**
- ✅ Intent classified as `COMMAND`
- ✅ Entity extraction identifies: task_id=15, depends_on=[12]
- ✅ Updates task dependencies
- ✅ Validates no circular dependencies (uses DependencyResolver)
- ✅ Returns confirmation with updated dependency graph

**Test Variations:**
```
"Task 15 depends on task 12"
"Add dependency between epic 3 and epic 1"
"Remove dependency from task 8"
"Show dependencies for task 20"
```

**Edge Cases:**
- Circular dependencies (A→B→C→A)
- Invalid task IDs
- Self-dependency (task depends on itself)

---

## Category 4: Orchestration Control (Hybrid Communication)

### US-NL-011: Send Direct Message to Implementor AI (Pass-Through)
**As a** user
**I want to** say "Send to Claude: Implement OAuth login with Google provider"
**So that** the message is forwarded to Claude Code without Orchestrator processing

**Acceptance Criteria:**
- ✅ Intent classified as `QUESTION` (forwarded, not executed)
- ✅ Message sent directly to Claude Code via agent
- ✅ Response returned verbatim from Claude
- ✅ Obra logs interaction (for context history)
- ✅ No validation or processing by Orchestrator

**Test Variations:**
```
"Send to Claude: Implement OAuth login"
"Ask Claude: What testing framework should we use?"
"To implementor: Review the authentication module"
"Forward to AI: Explain the state manager pattern"
```

**Edge Cases:**
- Claude Code not initialized (error message)
- Network timeout (retry with exponential backoff)
- Response too long (truncation with warning)

---

### US-NL-012: Ask Orchestrator to Optimize Prompt (Review Before Sending)
**As a** user
**I want to** say "Optimize this prompt: Add user login feature"
**So that** Orchestrator enhances the prompt using `StructuredPromptBuilder` and shows me the result for approval

**Acceptance Criteria:**
- ✅ Intent classified as `COMMAND` (Orchestrator action)
- ✅ Uses StructuredPromptBuilder to optimize
- ✅ Returns optimized prompt for user review
- ✅ **Does not send to Claude** until approved
- ✅ User can edit/approve/reject optimized prompt

**Test Variations:**
```
"Optimize this prompt: Add login feature"
"Improve my task description: Write unit tests"
"Enhance this request: Refactor authentication module"
"Help me write a better prompt for OAuth integration"
```

**Workflow:**
1. User provides rough prompt
2. Orchestrator generates optimized version (hybrid JSON + NL)
3. User sees side-by-side comparison
4. User approves/edits/rejects
5. Only after approval, send to Claude

**Edge Cases:**
- Prompt too short (ask for more details)
- Prompt already optimal (minor tweaks only)
- User rejects optimization (use original)

---

### US-NL-013: Pause/Resume Orchestration
**As a** user
**I want to** say "Pause orchestration"
**So that** Obra pauses execution and waits for my input

**Acceptance Criteria:**
- ✅ Intent classified as `COMMAND`
- ✅ Sets orchestration state to PAUSED
- ✅ Current task checkpoint saved
- ✅ Returns confirmation and instructions to resume
- ✅ Resume command restores state and continues

**Test Variations:**
```
"Pause orchestration"
"Stop execution"
"Wait for my input"
"Resume"
"Continue orchestration"
```

**Edge Cases:**
- Pause when already paused (idempotent)
- Resume when not paused (no-op)
- Pause during agent execution (waits for current iteration to complete)

---

### US-NL-014: Override Decision Engine
**As a** user
**I want to** say "Override decision: retry task 42"
**So that** Obra bypasses the decision engine and executes my command

**Acceptance Criteria:**
- ✅ Intent classified as `COMMAND`
- ✅ Entity extraction identifies: action=retry, task_id=42
- ✅ Overrides DecisionEngine recommendation
- ✅ Logs override reason (user requested)
- ✅ Executes specified action

**Test Variations:**
```
"Override decision: retry task 42"
"Force proceed with task 15"
"Skip validation and continue"
"Escalate task 8 to human review"
```

**Edge Cases:**
- Invalid action (not in DecisionAction enum)
- Task not in valid state for action
- Override conflicts with safety rules (warn but allow)

---

## Category 5: Error Handling & Edge Cases

### US-NL-015: Graceful Handling of Ambiguous Queries
**As a** user
**I want to** say "Show me the status"
**So that** Obra asks clarifying questions instead of guessing

**Acceptance Criteria:**
- ✅ Intent classified as `CLARIFICATION_NEEDED`
- ✅ Identifies ambiguity: "status" of what? (project, epic, task?)
- ✅ Asks user to clarify scope
- ✅ Suggests common interpretations
- ✅ Handles follow-up response

**Test Variations:**
```
"Show status"  → "Status of what? Project, epic, or specific task?"
"What's next?" → "Next task, story, or epic?"
"How's it going?" → "Overall project progress or specific work item?"
```

**Edge Cases:**
- User provides ambiguous clarification (iterative refinement)
- User says "nevermind" (cancel gracefully)

---

### US-NL-016: Graceful Handling of Invalid Entity Types
**As a** user
**I want to** type an invalid query
**So that** Obra explains what went wrong and suggests corrections

**Acceptance Criteria:**
- ✅ Detects when LLM returns `entity_type=None`
- ✅ Detects when `entity_type` is invalid (not in schema)
- ✅ Returns helpful error message (not Python traceback)
- ✅ Suggests valid entity types
- ✅ Logs error for debugging

**Test Scenarios:**
```python
# LLM returns entity_type=None
response = {"entity_type": None, "entities": []}
# Should return: "I couldn't determine what you're asking about.
# Are you asking about a project, epic, story, task, or milestone?"

# LLM returns invalid entity_type
response = {"entity_type": "feature", "entities": []}  # "feature" not valid
# Should return: "I don't recognize 'feature' as a work item type.
# Valid types are: project, epic, story, task, subtask, milestone."
```

**Bug Reference:** This story directly addresses the bug in the log where `entity_type=None` caused an unhandled ValueError.

---

### US-NL-017: Graceful Handling of Missing Context
**As a** user
**I want to** ask "What's the current epic?" when no project is active
**So that** Obra explains the problem and guides me to create a project first

**Acceptance Criteria:**
- ✅ Detects missing required context (no active project)
- ✅ Returns friendly error (not technical error)
- ✅ Suggests next action ("Create a project first")
- ✅ Optionally starts workflow (e.g., project creation wizard)

**Test Scenarios:**
```
User: "What's the current epic?"
Context: No project exists
Response: "You don't have an active project yet. Would you like to create one?"

User: "Show me task 42"
Context: Task 42 doesn't exist
Response: "I couldn't find task 42. Here are the available tasks: [list]"
```

---

### US-NL-018: Handling LLM Timeouts and Retries
**As a** user
**I want to** interact with the NL system even if the LLM is slow or fails
**So that** Obra retries with exponential backoff and eventually falls back to rule-based parsing

**Acceptance Criteria:**
- ✅ Detects LLM timeout (>30s)
- ✅ Retries with exponential backoff (1s, 2s, 4s)
- ✅ Falls back to regex/rule-based parsing after 3 failures
- ✅ Logs LLM performance metrics
- ✅ Returns partial results if possible

**Test Scenarios:**
- Mock LLM timeout (simulate network delay)
- Mock LLM rate limit (429 error)
- Mock LLM invalid response (malformed JSON)

---

### US-NL-019: Handling Special Characters and Formatting
**As a** user
**I want to** type queries with special characters, markdown, or code
**So that** Obra parses them correctly without breaking

**Acceptance Criteria:**
- ✅ Handles quotes: `Create task "Implement 'login' feature"`
- ✅ Handles newlines: Multi-line descriptions
- ✅ Handles code blocks: ```python code here```
- ✅ Handles emojis: "Update task ✅"
- ✅ Sanitizes SQL injection attempts

**Test Variations:**
```
"Create task \"Fix the 'auth' bug\""
"Update description:\nLine 1\nLine 2"
"Add task: ```python\ndef login():\n  pass\n```"
"Task with emoji: Add ✅ validation"
"Malicious: '; DROP TABLE tasks; --"
```

---

### US-NL-020: Multi-Turn Conversation Context
**As a** user
**I want to** have multi-turn conversations with context retention
**So that** I can say "And for epic 5?" after asking about epic 3

**Acceptance Criteria:**
- ✅ Maintains conversation history (last 5 turns)
- ✅ Resolves pronouns (it, that, this, the epic)
- ✅ Resolves implicit references ("and for epic 5")
- ✅ Allows context reset ("start over")

**Test Conversation:**
```
User: "What is epic 3?"
Bot: [Shows epic 3 details]
User: "And epic 5?"          ← Implicit reference to previous query type
Bot: [Shows epic 5 details]
User: "Mark it as completed" ← "it" = epic 5 from previous turn
Bot: [Updates epic 5 status]
```

**Edge Cases:**
- Ambiguous pronoun ("it" could refer to multiple things)
- Context expired (after 10 minutes of inactivity)
- User switches topics mid-conversation

---

## Testing Implementation Plan

### Phase 1: Core Pipeline Tests (Priority 1)
**Target:** US-NL-001, US-NL-004, US-NL-008, US-NL-011, US-NL-016

**Files to create:**
```
tests/test_nl_intent_classifier.py
tests/test_nl_entity_extractor.py
tests/test_nl_command_processor.py
```

**Coverage goal:** 70% for all `src/nl/*.py` files

**Estimated effort:** 3-5 hours (100-150 test cases)

---

### Phase 2: Advanced Features (Priority 2)
**Target:** US-NL-005, US-NL-007, US-NL-009, US-NL-012, US-NL-014

**Additional files:**
```
tests/test_nl_command_validator.py
tests/test_nl_command_executor.py
tests/test_nl_response_formatter.py
```

**Coverage goal:** 85% for all `src/nl/*.py` files

**Estimated effort:** 4-6 hours (120-180 test cases)

---

### Phase 3: Edge Cases & Error Handling (Priority 3)
**Target:** US-NL-015, US-NL-017, US-NL-018, US-NL-019, US-NL-020

**Integration tests:**
```
tests/test_nl_integration_e2e.py
tests/test_nl_error_scenarios.py
tests/test_nl_conversation_context.py
```

**Coverage goal:** 90% for all `src/nl/*.py` files

**Estimated effort:** 3-4 hours (80-100 test cases)

---

## Test Guidelines Compliance

All NL tests MUST follow `docs/development/TEST_GUIDELINES.md`:

### Resource Limits
- ⚠️ Max sleep per test: 0.5s (use `fast_time` fixture for LLM waits)
- ⚠️ Max threads per test: 5 (with mandatory timeout)
- ⚠️ Max memory per test: 20KB
- ✅ Mark slow tests: `@pytest.mark.slow`

### Mocking Strategy
```python
# Mock LLM responses (don't call real Ollama in tests)
@pytest.fixture
def mock_llm():
    llm = MagicMock(spec=LLMPlugin)
    llm.send_prompt.return_value = '{"entity_type": "epic", "entities": [...]}'
    return llm

# Mock StateManager (use in-memory SQLite)
@pytest.fixture
def mock_state(tmp_path):
    db_path = tmp_path / "test.db"
    state = StateManager(f"sqlite:///{db_path}")
    state.initialize()
    return state
```

### Test Structure
```python
class TestIntentClassifier:
    """Test intent classification with various input types."""

    def test_classify_command_intent(self, mock_llm):
        """Should classify 'Create epic' as COMMAND."""
        classifier = IntentClassifier(mock_llm)
        result = classifier.classify("Create an epic for auth")
        assert result.intent == "COMMAND"
        assert result.confidence >= 0.8

    def test_classify_question_intent(self, mock_llm):
        """Should classify 'What is...' as QUESTION."""
        classifier = IntentClassifier(mock_llm)
        result = classifier.classify("What is the current project?")
        assert result.intent == "QUESTION"
        assert result.confidence >= 0.8

    def test_classify_ambiguous_intent(self, mock_llm):
        """Should request clarification for ambiguous input."""
        classifier = IntentClassifier(mock_llm)
        result = classifier.classify("status")
        assert result.intent == "CLARIFICATION_NEEDED"
```

---

## Success Metrics

### Coverage Targets
- ✅ Overall NL module coverage: ≥85%
- ✅ Critical paths (entity extraction): ≥90%
- ✅ Error handling: ≥80%

### Bug Prevention
- ✅ All 20 user stories have automated tests
- ✅ The specific bug from the log (entity_type=None) is covered
- ✅ Edge cases have dedicated test scenarios

### Regression Prevention
- ✅ CI/CD pipeline runs NL tests on every commit
- ✅ Coverage reports track changes over time
- ✅ Failed tests block merges to main

---

## Appendix: Example Test Case (US-NL-001)

```python
# tests/test_nl_command_processor.py

import pytest
from unittest.mock import MagicMock
from src.nl.nl_command_processor import NLCommandProcessor
from src.core.state import StateManager

class TestProjectQueries:
    """Test project-level query handling (US-NL-001)."""

    @pytest.fixture
    def processor(self, mock_llm, mock_state):
        """Create NL processor with mocked dependencies."""
        config = Config.load()
        return NLCommandProcessor(mock_llm, mock_state, config)

    def test_query_current_project_success(self, processor, mock_state):
        """Should return current project info when project exists."""
        # Setup: Create a project
        project = mock_state.create_project(
            name="Test Project",
            working_directory="/tmp/test"
        )
        mock_state.set_current_project(project.id)

        # Execute: Query current project
        response = processor.process("What is the current project?")

        # Assert
        assert response.success is True
        assert response.intent == "COMMAND"
        assert "Test Project" in response.response
        assert project.id in response.response or str(project.id) in response.response

    def test_query_current_project_no_active(self, processor, mock_state):
        """Should return helpful message when no project is active."""
        # Execute: Query with no active project
        response = processor.process("What is the current project?")

        # Assert
        assert response.success is True  # Not an error, just empty state
        assert "no active project" in response.response.lower()
        assert "create" in response.response.lower()  # Suggest creating one

    def test_query_current_project_entity_type_none(self, processor, mock_llm):
        """Should handle gracefully when LLM returns entity_type=None.

        Bug reference: This is the exact bug from the log.
        """
        # Setup: Mock LLM to return entity_type=None
        mock_llm.send_prompt.return_value = '{"entity_type": null, "entities": []}'

        # Execute
        response = processor.process("What is the current project?")

        # Assert: Should not raise ValueError, should return helpful message
        assert response.success is False
        assert "couldn't determine" in response.response.lower()
        assert "project, epic, story, task" in response.response.lower()
        # Should NOT contain Python traceback
        assert "ValueError" not in response.response
        assert "Traceback" not in response.response

    def test_query_variations(self, processor, mock_state):
        """Should handle various phrasings of project query."""
        # Setup
        project = mock_state.create_project("My Project", "/tmp")
        mock_state.set_current_project(project.id)

        queries = [
            "What is the current project?",
            "Show me the active project",
            "Which project am I working on?",
            "Project info",
            "Current project status"
        ]

        for query in queries:
            response = processor.process(query)
            assert response.success is True, f"Failed for query: {query}"
            assert "My Project" in response.response
```

---

**Last Updated:** November 11, 2025
**Status:** Ready for implementation
**Next Step:** Create test files in `tests/test_nl_*.py` following Phase 1-3 plan
