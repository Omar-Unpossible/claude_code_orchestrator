# shell-enhancements

**Description**: WSL2 shell commands optimized for Claude Code workflows including context gathering (context, recent, todos), git shortcuts (gcom, gamend, gnew), and session management (save-context, diagnose). Includes 35+ commands with auto-detection for Python/Node/Rust/Go projects.

**Triggers**: WSL2, shell commands, bash, git workflow, session management, context gathering, gcom, gamend, recent, todos, save-context, diagnose, shell enhancements

**Token Cost**: ~900 tokens when loaded

**Dependencies**: WSL2 environment, bash, git, modern CLI tools (optional: fd, rg, bat)

---

## Shell Enhancements for LLM-Led Development

The WSL2 environment includes 35+ commands optimized for Claude Code workflows.

### Before Starting Claude Code Sessions

**Get Complete Context**:
```bash
context              # Complete project snapshot (location, git, files, stats)
recent 5             # Show 5 recently modified files
todos                # All TODO/FIXME/XXX comments
docs                 # List documentation files
root                 # Jump to project root
```

**MUST Follow Pre-Session Workflow**:
```bash
z obra               # Navigate to project (or use 'obra' alias)
context              # Get comprehensive overview
recent 5             # Check recent activity
todos                # Review pending TODOs
gs                   # Git status
```

### Git Workflow (Fast Iteration)

```bash
gcom <msg>           # Stage all changes and commit
gamend               # Amend last commit with current changes
gs                   # Short git status
gundo                # Undo last commit (keep changes in working dir)
gnew <branch>        # Create and switch to new branch
glog [N]             # Show last N commits in compact format
gdiff [opts]         # Pretty git diff (with delta if installed)
```

### Code Navigation

```bash
ff                   # Fuzzy file finder with preview
search <pattern>     # Grep with context and colors
es <pattern>         # Edit files containing pattern
```

### Testing & Validation (Auto-detects Project Type)

```bash
test [opts]          # Run tests (Python/Node/Rust/Go auto-detected)
lint [opts]          # Run linter (auto-detected)
fmt [opts]           # Format code (auto-detected)
check-all            # Run format + lint + test in sequence
```

**Python Projects** (auto-detected):
- Tests: `pytest` → `python -m pytest`
- Lint: `ruff check` → `pylint` → `flake8`
- Format: `ruff format` → `black`

**Node.js Projects**: `npm test`, `npm run lint`, `npm run format`
**Rust Projects**: `cargo test`, `cargo clippy`, `cargo fmt`
**Go Projects**: `go test ./...`, `go fmt ./...`

### Session Management

```bash
save-context [file]  # Save work context (git status, recent files, diff)
load-context [file]  # View saved context
diagnose             # Environment diagnostics (versions, git, disk, processes)
```

**Example**:
```bash
# End of session
save-context ~/work-context-$(date +%Y%m%d).md

# Next session
load-context ~/work-context-20251115.md
```

### Quick Reference

```bash
claude-help          # Show all commands with descriptions
ch                   # Alias for claude-help
```

**Performance**:
- Startup overhead: < 50ms
- `context` command: ~500ms
- `recent` command: ~100ms
- All commands use native tools (no Python/Node overhead)

**Full Documentation**: `~/CLAUDE_ENHANCEMENTS_README.md`
