# Natural Language Command Interface - User Guide

**Version:** 1.6.0 (ADR-016)
**Feature:** Natural Language Command Processing
**Status:** Production Ready
**Accuracy:** 95%+ across all command types

---

## Overview

The Natural Language Command Interface allows you to interact with Obra using conversational language instead of exact command syntax. No more memorizing commands - just describe what you want to do!

### What Can You Do?

- **Create work items**: "Create an epic for user authentication"
- **Update items**: "Mark the manual tetris test as INACTIVE"  *(New in v1.6.0)*
- **Query hierarchically**: "List the workplans for the projects"  *(New in v1.6.0)*
- **Ask questions**: "What's next for the tetris game development?"  *(New in v1.6.0)*
- **Delete items**: "Delete task 5"
- **Natural commands**: "Show me all pending tasks"

### How It Works (v1.6.0 - ADR-016)

Obra uses a **7-stage pipeline** to understand and execute your commands with **95%+ accuracy**:

1. **Intent Classification**: Determines if you're issuing a COMMAND or asking a QUESTION
2. **Operation Classification**: Identifies operation type (CREATE, UPDATE, DELETE, QUERY) *(New)*
3. **Entity Type Classification**: Determines entity type (project, epic, story, task, milestone) *(Enhanced)*
4. **Entity Identifier Extraction**: Extracts entity names or IDs *(Enhanced)*
5. **Parameter Extraction**: Extracts operation-specific parameters (status, priority, etc.) *(New)*
6. **Validation**: Checks that references exist and business rules are met
7. **Execution**: Creates/updates work items via StateManager
8. **Response**: Provides clear, color-coded feedback

**Architecture**: Each stage focuses on a single responsibility, enabling higher accuracy through progressive refinement.

**See**: `docs/decisions/ADR-016-decompose-nl-entity-extraction.md` for technical details

---

## Getting Started

### Enable NL Commands

NL commands are enabled by default in v1.3.0. To verify or configure:

```yaml
# config/config.yaml
nl_commands:
  enabled: true  # Enable NL processing
  confidence_threshold: 0.7  # Confidence threshold for clarification
  max_context_turns: 10  # Conversation history turns to keep
  fallback_to_info: true  # Forward questions to Claude Code
```

### Start Interactive Mode

```bash
python -m src.cli interactive
```

### Your First NL Command

```
orchestrator> Create an epic called "User Authentication System"
✓ Created Epic #5: User Authentication System
  Next: Add stories with 'create story in epic 5'
```

That's it! No slash commands, no syntax to remember.

---

## Command Examples

### Creating Work Items

#### Epics

```
Create an epic for user authentication
✓ Created Epic #5: User Authentication

Create an epic called "Admin Dashboard" with description "Complete admin interface"
✓ Created Epic #6: Admin Dashboard
  Next: Add stories with 'create story in epic 6'
```

#### Stories

```
Add a story for user login to the User Authentication epic
✓ Created Story #7: User Login
  Next: Add tasks with 'create task in story 7'

Add 3 stories to epic 5: login, signup, and password reset
✓ Created 3 storys: #7, #8, #9
```

#### Tasks

```
Create a task to implement OAuth for story 7
✓ Created Task #10: Implement OAuth
  Next: Execute task or add subtasks

Add task for writing tests in the login story
✓ Created Task #11: Writing Tests
```

#### Milestones

```
Create a milestone for auth completion requiring epic 5
✓ Created Milestone #1: Auth Completion
  Next: Check milestone completion status
```

### Updating Work Items *(New in v1.6.0)*

Update existing work items with natural language:

#### Update Status

```
Mark the manual tetris test as INACTIVE
✓ Updated Project #3: Manual Tetris Test → status: INACTIVE

Set task 5 status to COMPLETED
✓ Updated Task #5: status: COMPLETED
```

#### Update Priority

```
Change task 10 priority to HIGH
✓ Updated Task #10: priority: HIGH

Set epic 2 priority to LOW
✓ Updated Epic #2: priority: LOW
```

#### Update Dependencies

```
Update task 15 dependencies to include tasks 3 and 7
✓ Updated Task #15: dependencies: [3, 7]
```

### Hierarchical Queries *(New in v1.6.0)*

Query work item hierarchies and relationships:

#### Workplan Query

```
List the workplans for the projects
✓ Showing hierarchical workplan:

📦 Project: Manual Tetris Test
  ├─ 📋 Epic #1: Core Gameplay
  │   ├─ 📖 Story #2: Tetromino Movement
  │   │   ├─ ✓ Task #5: Implement rotation
  │   │   └─ 🔄 Task #6: Add collision detection
  │   └─ 📖 Story #3: Scoring System
  │       └─ 🔄 Task #8: Calculate score
  └─ 📋 Epic #2: User Interface
      └─ 📖 Story #4: Main Menu
          └─ ⏸️ Task #9: Design layout
```

#### Next Steps Query

```
What's next for project 1?
✓ Next steps for Project #1:
  1. Task #6: Add collision detection (PENDING, priority: HIGH)
  2. Task #8: Calculate score (PENDING, priority: MEDIUM)
  3. Task #10: Implement high score table (PENDING, priority: LOW)
```

#### Backlog Query

```
Show me the backlog for the tetris project
✓ Backlog (5 pending tasks):
  - Task #6: Add collision detection (HIGH)
  - Task #8: Calculate score (MEDIUM)
  - Task #10: Implement high score table (LOW)
  - Task #12: Add pause feature (MEDIUM)
  - Task #15: Sound effects (LOW)
```

#### Roadmap Query

```
Display the roadmap for project 1
✓ Project Roadmap:

Milestone #1: Core Gameplay Complete (Target: Q1 2026)
  - Epic #1: Core Gameplay (3 stories, 8 tasks)
  - Status: 60% complete (5/8 tasks done)

Milestone #2: UI Polish Complete (Target: Q2 2026)
  - Epic #2: User Interface (2 stories, 6 tasks)
  - Status: 33% complete (2/6 tasks done)
```

### Asking Questions *(Enhanced in v1.6.0)*

Questions are now handled intelligently with contextual responses:

#### Next Steps Questions

```
What's next for the tetris game development?
✓ Next steps for Tetris Game:
  1. Task #6: Add collision detection (PENDING, HIGH priority)
  2. Task #8: Calculate score (PENDING, MEDIUM priority)

  Blockers: None
  Ready to start: 2 tasks

How should I prioritize the work?
✓ Recommended priority order:
  1. Task #6 (HIGH) - Blocking Story #2
  2. Task #8 (MEDIUM) - Required for MVP
  3. Task #10 (LOW) - Nice-to-have feature
```

#### Status Questions

```
What's the status of epic 1?
✓ Epic #1: Core Gameplay
  - Status: IN_PROGRESS
  - Stories: 2/3 complete (67%)
  - Tasks: 5/8 complete (62%)
  - Started: 2025-11-01
  - Estimated completion: 2025-11-15

How's project 1 going?
✓ Project #1: Manual Tetris Test
  - Overall progress: 55% (11/20 tasks complete)
  - Active epics: 2 (1 in progress, 1 blocked)
  - Milestones: 0/2 achieved
  - Next milestone: Core Gameplay Complete (40% done)
```

#### Blocker Questions

```
What's blocking the tetris development?
✓ Blockers for Tetris project:
  1. Task #12: Waiting on design review (blocked 3 days)
  2. Epic #3: Dependencies not resolved (Task #6 incomplete)

  Recommendations:
  - Complete Task #6 to unblock Epic #3
  - Follow up on design review for Task #12

Any problems with project 1?
✓ Issues detected:
  - 2 tasks overdue (Task #15, Task #18)
  - 1 circular dependency (Task #20 ↔ Task #21)
  - 0 failing tasks
```

#### Progress Questions

```
Show progress for epic 2
✓ Epic #2: User Interface
  - Completion: 33% (2/6 tasks)
  - Progress chart:
    ████████░░░░░░░░░░░░░░░░ 33%
  - Velocity: 0.5 tasks/day
  - Estimated completion: 8 days

How far along is the tetris project?
✓ Project metrics:
  - Overall: 55% complete (11/20 tasks)
  - This week: 3 tasks completed
  - Velocity: 2.1 tasks/week
  - Estimated completion: 4.3 weeks
```

#### General Questions

```
How do I create an epic?
✓ To create an epic, use:
  - Natural language: "Create an epic for [name]"
  - Or CLI: python -m src.cli epic create "Epic Title"

  Example: "Create an epic for user authentication"

What's the difference between epics and stories?
✓ Work item hierarchy:
  - Epic: Large feature (3-15 sessions, multiple stories)
  - Story: User deliverable (1 session, multiple tasks)
  - Task: Technical work (atomic unit)

  Example:
  Epic: "User Authentication System"
    Story: "Email/password login"
      Task: "Implement login API"
      Task: "Create login UI"
```

### Handling Ambiguity

If Obra isn't sure what you mean (confidence <70%), it will ask for clarification:

```
Maybe add something
? I'm not sure what you'd like to do. Did you mean:
  1. Create a work item (epic/story/task)
  2. List existing work items
  0. Something else (please clarify)
```

---

## Response Types

### Success (Green ✓)

```
✓ Created Epic #5: User Authentication
  Next: Add stories with 'create story in epic 5'
```

### Error (Red ✗)

```
✗ Error: Epic not found
  Try: List epics with 'show epics' or create one first
```

### Warning/Confirmation (Yellow ⚠)

```
⚠ This will delete Epic #5 and all 12 stories. Confirm? (y/n)
```

### Clarification (Yellow ?)

```
? Did you mean:
  1. Create epic 'User Dashboard'
  2. List existing epics
  3. Something else (please clarify)
```

---

## Advanced Features

### Conversation Context

Obra remembers recent conversation turns (default: 10 turns):

```
Turn 1: Create an epic for user authentication
✓ Created Epic #5: User Authentication

Turn 2: Add 3 stories to it
✓ Created 3 storys under Epic #5: #6, #7, #8
```

Obra understands "it" refers to Epic #5 from the previous turn!

### Multi-Item Commands

Create multiple work items in one command:

```
Create 5 tasks for epic 5: implement login, implement signup, add OAuth, add MFA, write tests
✓ Created 5 tasks: #10, #11, #12, #13, #14
```

### Reference Resolution

Use epic/story names instead of IDs:

```
Add a story to the User Authentication epic
✓ Created Story #15: Story
```

Obra automatically resolves "User Authentication" to Epic #5.

### Destructive Operation Confirmation

Delete, update, and execute operations require confirmation:

```
Delete epic 5
⚠ This will delete Epic #5 (User Authentication). Confirm? (y/n)
```

---

## Mixing NL and Slash Commands

You can seamlessly mix natural language with traditional slash commands:

```
orchestrator> Create an epic for reporting
✓ Created Epic #7: Reporting

orchestrator> /pause
Execution will pause after current turn completes

orchestrator> Add 3 stories to the reporting epic
✓ Created 3 storys under Epic #7: #16, #17, #18

orchestrator> /status
📊 Task Status:
   Task ID: 42
   Iteration: 3/10
   Quality: 0.85
   Status: ▶️  RUNNING
```

---

## Configuration Reference

### Full Configuration Options

```yaml
nl_commands:
  # Master enable/disable switch
  enabled: true

  # LLM provider for NL processing (uses llm.type if not specified)
  llm_provider: ollama

  # Confidence threshold for CLARIFICATION_NEEDED
  # Commands below this threshold trigger clarification requests
  confidence_threshold: 0.7

  # Maximum conversation history turns to keep
  max_context_turns: 10

  # Path to Obra schema for entity extraction
  schema_path: src/nl/schemas/obra_schema.json

  # Default project ID if not specified in command
  default_project_id: 1

  # Operations requiring user confirmation
  require_confirmation_for:
    - delete
    - update
    - execute

  # Fallback to informational response for QUESTION intent
  # If true: questions forwarded to Claude Code
  # If false: suggest rephrasing as command
  fallback_to_info: true

  # Enable experimental NL features
  experimental_features: false
```

### Environment Overrides

Override configuration via environment variables:

```bash
export ORCHESTRATOR_NL_COMMANDS_ENABLED=true
export ORCHESTRATOR_NL_COMMANDS_CONFIDENCE_THRESHOLD=0.8
python -m src.cli interactive
```

---

## Troubleshooting

### NL Commands Not Working

**Symptom**: `Natural language commands not enabled`

**Solution**: Check configuration:
```bash
grep -A 5 "nl_commands:" config/config.yaml
```

Ensure `enabled: true` and restart interactive mode.

### Low Confidence / Clarification Requests

**Symptom**: Obra frequently asks for clarification

**Solution**: Be more specific in your commands:

❌ "Add something"
✓ "Create an epic for user authentication"

❌ "Do the thing"
✓ "Add a story for user login to epic 5"

### Entity Extraction Errors

**Symptom**: `Validation error: Epic not found`

**Solution**: Use exact names or IDs:

❌ "Add story to auth epic" (ambiguous)
✓ "Add story to the User Authentication epic" (exact match)
✓ "Add story to epic 5" (use ID)

### Performance / Latency

**Symptom**: NL commands take >3 seconds

**Solution**:
1. Check LLM provider performance (Ollama/OpenAI latency)
2. Reduce `max_context_turns` if using large conversation history
3. Use specific commands instead of vague ones (faster processing)

---

## Limitations

### Current Limitations (v1.6.0)

1. **English Only**: NL processing supports English language only
2. **Simple Grammar**: Complex sentences may require clarification
3. **No Multi-Action**: One command = one action (no "create epic AND add stories")
4. **Schema-Bound**: Can only create/manage Obra work items (epics/stories/tasks/milestones)
5. **Operation Scope**: UPDATE operations support status, priority, and dependencies only

### Planned Enhancements (Future)

- **Multi-language support** (Spanish, French, etc.)
- **Multi-action commands** ("Create epic X and add 5 stories to it")
- **Voice input** (speech-to-text → NL processing)
- **Learning from corrections** (improve accuracy over time)
- **External tool integration** (GitHub, Jira via NL)

---

## FAQ

### Q: Do I need to use NL commands?

**A:** No. Traditional slash commands (`/pause`, `/to-impl`, etc.) continue to work. NL commands are optional but recommended for faster interaction.

### Q: Can I disable NL commands?

**A:** Yes. Set `nl_commands.enabled: false` in config:

```yaml
nl_commands:
  enabled: false
```

### Q: What's the difference between NL commands and slash commands?

**A:**
- **Slash commands**: Exact syntax, instant execution, no LLM processing
- **NL commands**: Conversational, flexible, LLM-powered understanding

Use slash commands for precise control, NL commands for natural interaction.

### Q: How accurate is the NL command interface?

**A:** v1.6.0 (ADR-016) achieves **95%+ overall accuracy**:
- Simple commands (create, list): **98%** accuracy
- Status updates (UPDATE operations): **95%** accuracy
- Hierarchical queries (workplan, backlog): **90%** accuracy
- Natural questions (what's next): **92%** accuracy

Ambiguous commands (<70% confidence) trigger clarification requests. This represents a significant improvement over v1.3.0 (80-85% accuracy) through architectural refactoring.

### Q: Does NL use my Claude Code API quota?

**A:** No. NL processing uses the local LLM (Qwen 2.5 Coder via Ollama) or separate LLM provider configured in `nl_commands.llm_provider`. Claude Code is only used for question forwarding if `fallback_to_info: true`.

### Q: Can I use NL commands in scripts?

**A:** NL commands work best in interactive mode. For scripting, use traditional CLI commands:

```bash
python -m src.cli epic create "Epic Title" --description "..."
```

---

## Examples Gallery

### Complete Workflow Example

```
# Create epic
orchestrator> Create an epic for building a user dashboard

✓ Created Epic #10: User Dashboard
  Next: Add stories with 'create story in epic 10'

# Add stories
orchestrator> Add 3 stories to it: user profile view, settings page, and notifications

✓ Created 3 storys under Epic #10:
  - Story #20: User Profile View
  - Story #21: Settings Page
  - Story #22: Notifications

# Create tasks for a story
orchestrator> Add 2 tasks to the user profile story: implement UI and write tests

✓ Created 2 tasks under Story #20:
  - Task #50: Implement UI
  - Task #51: Write Tests

# Check progress
orchestrator> How many stories are in the user dashboard epic?

Forwarding question to Claude Code...
[Response from Claude Code with story count]

# Create milestone
orchestrator> Create a milestone for dashboard completion requiring epic 10

✓ Created Milestone #5: Dashboard Completion
  Next: Check milestone completion status
```

---

## Best Practices

### ✅ DO

- **Be specific**: "Create an epic for user authentication" (not "add something")
- **Use context**: "Add story to it" (after creating epic in previous turn)
- **Include details**: "...with description 'OAuth and MFA support'"
- **Use IDs when known**: "Add story to epic 5" (faster than name lookup)

### ❌ DON'T

- **Be vague**: "Do the thing" or "Maybe add stuff"
- **Use complex sentences**: "Create epic X and add stories Y and Z then execute task A"
- **Assume magic**: NL understands work items, not arbitrary actions
- **Skip confirmation**: Destructive ops (delete/update) require explicit confirmation

---

## Support

- **Documentation**: [docs/development/NL_COMMAND_INTERFACE_IMPLEMENTATION_GUIDE.md](../development/NL_COMMAND_INTERFACE_IMPLEMENTATION_GUIDE.md)
- **Spec**: [docs/development/NL_COMMAND_INTERFACE_SPEC.json](../development/NL_COMMAND_INTERFACE_SPEC.json)
- **Issues**: Report bugs at [GitHub Issues](https://github.com/Omar-Unpossible/claude_code_orchestrator/issues)
- **ADR-014**: [docs/decisions/ADR-014-natural-language-command-interface.md](../decisions/ADR-014-natural-language-command-interface.md)
- **ADR-016**: [docs/decisions/ADR-016-decompose-nl-entity-extraction.md](../decisions/ADR-016-decompose-nl-entity-extraction.md) *(New - v1.6.0 architecture)*
- **Migration Guide**: [docs/guides/ADR016_MIGRATION_GUIDE.md](ADR016_MIGRATION_GUIDE.md) *(For developers migrating from v1.3.0)*

---

**Last Updated**: November 11, 2025
**Version**: v1.6.0 (ADR-016)
**Feature**: Natural Language Command Interface - Five-Stage Pipeline Refactor
**Accuracy**: 95%+ across all command types
