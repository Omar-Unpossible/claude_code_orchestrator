---
description: Get comprehensive project context from shell commands
---

Help the user gather complete project context using the available shell commands.

The user should run these commands in their terminal (NOT in Claude Code):

```bash
# Get complete project context
context

# Check recent activity
recent 5

# Show pending TODOs
todos

# Check git status
gs
```

Explain to the user that:
1. These commands are available in their WSL2 shell
2. They should run these BEFORE starting a Claude Code session
3. The output will give Claude Code full understanding of the project

After the user runs these commands, they should share the output with you (Claude Code) to get the best context for the current session.

**Alternative**: The user can save context to a file:
```bash
save-context ~/current-context.md
```

Then share that file's contents with you.
