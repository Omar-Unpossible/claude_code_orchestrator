# Natural Language Command Interface - User Guide

**Version:** 1.3.0
**Feature:** Natural Language Command Processing
**Status:** Production Ready

---

## Overview

The Natural Language Command Interface allows you to interact with Obra using conversational language instead of exact command syntax. No more memorizing commands - just describe what you want to do!

### What Can You Do?

- **Create work items**: "Create an epic for user authentication"
- **Add stories**: "Add 3 stories to the User Auth epic: login, signup, and MFA"
- **Ask questions**: "How many epics do I have?"
- **Natural commands**: "Show me all pending tasks"

### How It Works

Obra uses a multi-stage pipeline to understand and execute your commands:

1. **Intent Classification**: Determines if you're issuing a command or asking a question
2. **Entity Extraction**: Extracts work item details (titles, descriptions, references)
3. **Validation**: Checks that references exist and business rules are met
4. **Execution**: Creates/updates work items via StateManager
5. **Response**: Provides clear, color-coded feedback

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

### Asking Questions

Questions are automatically forwarded to Claude Code's conversational interface:

```
How do I create an epic?
Forwarding question to Claude Code: How do I create an epic?

Show me all my epics
Forwarding question to Claude Code: Show me all my epics
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

### Current Limitations (v1.3.0)

1. **English Only**: NL processing supports English language only
2. **Simple Grammar**: Complex sentences may require clarification
3. **No Multi-Action**: One command = one action (no "create epic AND add stories")
4. **Schema-Bound**: Can only create/manage Obra work items (epics/stories/tasks/milestones)

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

### Q: How accurate is intent classification?

**A:** >95% accuracy on clear commands ("Create an epic..."), >90% on questions ("How do I...?"). Ambiguous commands (<70% confidence) trigger clarification requests.

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
- **ADR**: [docs/decisions/ADR-014-natural-language-command-interface.md](../decisions/ADR-014-natural-language-command-interface.md) *(to be created)*

---

**Last Updated**: November 2025
**Version**: v1.3.0
**Feature**: Natural Language Command Interface (Story 5 Complete)
