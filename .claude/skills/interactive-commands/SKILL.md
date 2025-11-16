# interactive-commands

**Description**: Interactive mode command reference including natural language defaults (no / prefix), system commands (/help, /status, /pause, /resume, /stop, /to-impl, /override-decision), and command injection points during execution.

**Triggers**: interactive mode, /help, /status, /pause, /to-impl, command injection, interactive, /commands

**Token Cost**: ~250 tokens when loaded

**Dependencies**: Interactive CLI mode (python -m src.cli interactive)

---

## Interactive Mode (v1.5.0 UX)

When running `python -m src.cli interactive`:

### Command Syntax

- **Natural text** (no `/`) → Defaults to orchestrator
- **System commands** → Require `/` prefix

### Natural Language Examples

```bash
# These go directly to the orchestrator (no / prefix needed)
"Create a new feature for user authentication"
"What's the current task status?"
"Pause execution and show me the logs"
```

### System Commands

```bash
/help                           # Show help message
/status                         # Show current task status
/pause                          # Pause execution
/resume                         # Resume execution
/stop                           # Stop gracefully
/to-impl <message>             # Send message to implementer (Claude Code)
/override-decision <choice>    # Override orchestrator's decision
```

## Command Injection Points

Interactive commands can be injected at 6 checkpoints during execution:
1. Before NL processing
2. After intent classification
3. Before orchestrator execution
4. After validation
5. Before decision
6. After task completion

**See**: `docs/architecture/data_flow.md` for detailed checkpoint descriptions

## Usage Notes

- Natural language commands are processed through NL pipeline (IntentClassifier, EntityExtractor)
- System commands bypass NL processing for immediate action
- Use `/pause` to inspect state, then `/resume` to continue
- Use `/to-impl` to send instructions directly to Claude Code agent
- Use `/override-decision` when orchestrator's choice needs manual override

**Full Documentation**: `CLAUDE.md` - Interactive Mode section
