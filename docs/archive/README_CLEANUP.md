# Documentation Cleanup - November 13, 2025

## Summary

Cleaned up project root documentation files per user request. Only core documentation files remain in root.

## Files Kept in Root

✅ **AGENTS.md** - Repository guidelines for agents
✅ **CLAUDE.md** - Project instructions for Claude Code
✅ **CHANGELOG.md** - Version history
✅ **README.md** - Project readme

## Files Moved

### NL Performance Optimization → `docs/archive/nl_performance_optimization/`
- CLAUDE_STARTUP_PROMPT_NL_PERFORMANCE.md
- NL_PERFORMANCE_ANALYSIS.md
- NL_PERFORMANCE_COMPLETION_SUMMARY.md
- NL_PERFORMANCE_NEXT_SESSION.md
- NL_QUERY_FIX_SUMMARY.md

### Bugfix Summaries → `docs/archive/bugfixes/`
- FIX_SUMMARY.md (ParsedIntent bug fix)
- LLM_HARDENING_SUMMARY.md
- MODEL_FORCING_FIX.md

### NL Command System → `docs/archive/nl_command_system/`
- CLAUDE_STARTUP_PROMPT_BULK_OPS.md

### Operations Guides → `docs/operations/`
- START_HERE.md → STARTUP_GUIDE.md
- MIGRATION_GUIDE.md → MANUAL_MIGRATION_GUIDE.md

### Alternative Development Approaches → `docs/archive/development/`
- QUICK_START.md → ALTERNATIVE_QUICK_START.md

## Result

Root directory now contains only essential documentation:
- Core project files (AGENTS.md, CLAUDE.md, CHANGELOG.md, README.md)
- Setup scripts (setup.sh, setup.py)
- Operational scripts (obra.sh, etc.)
- Package configuration files (requirements*.txt, etc.)

All session summaries, fix reports, and startup prompts have been properly archived in `/docs/archive/` subdirectories for future reference.
