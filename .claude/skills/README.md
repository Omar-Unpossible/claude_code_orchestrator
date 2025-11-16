# Obra Skills

Skills are specialized content loaded on-demand by Claude Code for specific tasks.

## Available Skills

1. **shell-enhancements** - WSL2 shell commands (35+) for Claude workflows
2. **development-tools** - LLM-optimized tools (tokei, ripgrep, fd, bat, etc.)
3. **testing-guidelines** - Pytest patterns and WSL2 crash prevention
4. **agile-workflow** - Epic/Story/Milestone management commands
5. **interactive-commands** - Interactive mode command reference

## Structure

Each Skill follows this structure:
```
.claude/skills/{skill-name}/
├─ SKILL.md           # Description + instructions
├─ examples/          # Code examples (optional)
└─ scripts/           # Automation scripts (optional)
```

## Metadata Format

SKILL.md MUST start with:
```markdown
# {Skill Name}

**Description**: [30-50 token description]
**Triggers**: [Keywords for invocation]
**Token Cost**: ~X tokens when loaded
**Dependencies**: [Required tools/configs]
```

## When Skills Load

- **ALWAYS**: Metadata (description, triggers) in startup context
- **ON-DEMAND**: Full content when user task matches triggers
- **NEVER**: Skills not relevant to current task

## Creating New Skills

MUST create Skill ONLY IF:
- Content >500 tokens AND
- Used <50% of sessions AND
- Self-contained domain

See: `docs/research/claude_code_project_optimization/CLAUDE_CODE_OPTIMIZATION_LLM_OPTIMIZED.md` (RULE 14-17)
