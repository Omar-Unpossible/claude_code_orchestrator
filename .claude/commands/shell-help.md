---
description: Show available shell enhancement commands for LLM-led development
---

Show the user a concise reference of the shell enhancement commands available in this development environment.

The WSL2 environment includes 35+ specialized commands for Claude Code workflows. Here are the most important ones:

**PROJECT CONTEXT** (use BEFORE Claude Code sessions):
- `context` - Complete project snapshot (location, git status, files, stats)
- `recent [N]` - Show N recently modified files
- `todos` - Show all TODO/FIXME/XXX comments
- `docs [file]` - List or view documentation files

**GIT WORKFLOW** (fast iteration):
- `gcom <msg>` - Stage all and commit
- `gamend` - Amend last commit
- `gs` - Short git status
- `gundo` - Undo commit (keep changes)
- `gnew <branch>` - Create branch

**CODE NAVIGATION**:
- `ff` - Fuzzy file finder
- `search <pattern>` - Grep with context
- `es <pattern>` - Edit files with pattern

**TESTING** (auto-detects Python/Node/Rust/Go):
- `test` - Run tests
- `lint` - Run linter
- `fmt` - Format code
- `check-all` - Run all checks

**SESSION MANAGEMENT**:
- `save-context` - Save work state
- `load-context` - View saved context
- `diagnose` - Environment diagnostics

**QUICK REFERENCE**:
- `claude-help` or `ch` - Show all commands

**DOCUMENTATION**:
- See CLAUDE.md → "Development Environment & Shell Enhancements" section
- Full guide: ~/CLAUDE_ENHANCEMENTS_README.md

Format the output in a clear, readable way that helps the user understand these commands are available in their shell, not within Claude Code itself.
