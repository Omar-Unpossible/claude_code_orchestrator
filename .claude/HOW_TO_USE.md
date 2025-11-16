# How to Use the Optimized Claude Configuration

The Claude configuration has been optimized and distributed across multiple focused files for better efficiency.

## File Structure

```
.claude/
├── PROJECT.md          # Daily commands, workflows, practical usage
├── RULES.md           # Quick DO/DON'T reference, common patterns
├── HOW_TO_USE.md      # This file - usage guide
└── commands/
    ├── get-context.md # Slash command for project context
    └── shell-help.md  # Slash command for shell commands

CLAUDE.md              # Core rules, architecture principles (at repo root)
```

## When to Read Each File

### Starting a New Claude Code Session

**Read in this order:**
1. **CLAUDE.md** (335 lines) - Core rules and architecture principles
2. **.claude/PROJECT.md** (651 lines) - Commands and daily workflows
3. **CHANGELOG.md** - Recent changes (if relevant to your task)

### During Development

**Quick Reference:**
- **.claude/RULES.md** - Fast lookup for DO/DON'T patterns
- **.claude/PROJECT.md** - Command syntax and examples
- **CLAUDE.md** - Architecture rule clarification

### Before Writing Tests
- **Read:** `docs/testing/TEST_GUIDELINES.md` (⚠️ CRITICAL)
- **Quick ref:** `.claude/RULES.md` → Testing Rules section

### When Stuck
- **System understanding:** `docs/design/OBRA_SYSTEM_OVERVIEW.md`
- **Architecture details:** `docs/architecture/ARCHITECTURE.md`
- **Decisions:** `docs/decisions/` (17 ADRs)
- **Quick patterns:** `.claude/RULES.md`

## Using Slash Commands

From within Claude Code, use:
```
/get-context    # Get comprehensive project context
/shell-help     # Show shell enhancement commands
```

These commands guide you to run shell commands in your terminal (not in Claude Code).

## Typical Workflows

### Starting a Coding Session
1. **In terminal** (before Claude Code):
   ```bash
   context      # Get project snapshot
   recent 5     # Check recent changes
   todos        # Review pending items
   ```

2. **Start Claude Code:**
   ```bash
   claude
   ```

3. **Claude reads** (automatically):
   - CLAUDE.md (core rules)
   - .claude/PROJECT.md (commands)

### During Development
- **Need command syntax?** Check `.claude/PROJECT.md`
- **Need pattern example?** Check `.claude/RULES.md`
- **Need architecture detail?** Claude will read `docs/` as needed
- **Common error?** Check `.claude/RULES.md` → "Common Errors and Fixes"

### Before Committing
```bash
# In terminal
check-all        # Run format + lint + test
gcom "message"   # Stage all and commit
```

## What Changed from Old Structure

### OLD (1048 lines in CLAUDE.md):
- Everything in one massive file
- Lots of duplication
- Verbose explanations
- Wall-of-text syndrome
- Loaded entirely on every session

### NEW (335 + 651 + 300 lines distributed):
- **CLAUDE.md**: Focused core rules only
- **.claude/PROJECT.md**: Practical daily usage
- **.claude/RULES.md**: Quick reference patterns
- **docs/**: Detailed explanations (read when needed)
- Claude loads less upfront, reads more on-demand

## Benefits for Claude Code

1. **Faster session start**: 68% less text to process initially
2. **Better focus**: Core rules first, details when needed
3. **Scannable structure**: Clear hierarchies and bullet points
4. **Quick lookup**: Dedicated RULES.md for fast reference
5. **Less duplication**: Information lives in one place
6. **Better organization**: Files serve specific purposes

## Tips for Humans Maintaining This

### Adding New Rules
- **Architecture principle?** → Add to CLAUDE.md (keep concise)
- **Code pattern?** → Add to .claude/RULES.md
- **Command/workflow?** → Add to .claude/PROJECT.md
- **Detailed explanation?** → Add to `docs/guides/`

### Keeping It Efficient
- **CLAUDE.md**: Target 300-400 lines max
- **Bullet points** over paragraphs
- **References** over duplication
- **Examples** only for critical patterns

### When in Doubt
Ask: "Does Claude need this upfront, or can it read the detailed doc when needed?"
- **Upfront**: Core rules, critical warnings, common pitfalls
- **On-demand**: Detailed explanations, historical context, examples

## Verification

All critical information remains accessible:
✅ StateManager rule in CLAUDE.md
✅ Validation order in CLAUDE.md
✅ Test guidelines warning in CLAUDE.md
✅ Shell commands in PROJECT.md
✅ Quick patterns in RULES.md
✅ Slash commands in .claude/commands/
✅ Detailed docs in docs/

---

**Remember**: This structure optimizes for Claude Code's operation patterns while maintaining all essential information.
