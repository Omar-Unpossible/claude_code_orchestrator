# development-tools

**Description**: LLM-optimized development tools including tokei (code stats), ripgrep (fast search), fd (find files), bat (syntax highlighting), jq/yq (JSON/YAML parsing), hyperfine (benchmarking), and httpie (HTTP requests). Includes comparison table to traditional Unix tools.

**Triggers**: tokei, ripgrep, rg, fd, bat, jq, yq, hyperfine, httpie, code analysis, search code, find files, parse JSON, development tools

**Token Cost**: ~500 tokens when loaded

**Dependencies**: Modern CLI tools (installation optional, Skill provides fallback guidance)

---

## LLM-Optimized Development Tools

These tools are optimized for AI-assisted development and provide cleaner output than traditional Unix tools:

### Quick Reference

```bash
# Code analysis
tokei                              # Code statistics (fast, accurate)
tree -L 2 -I 'venv|*.pyc'         # Directory structure visualization
rg "pattern" -t py                 # Search code (ripgrep - 10-100x faster than grep)
fd filename -e py                  # Find files (faster than find)

# File operations
bat file.py                        # View with syntax highlighting
ll                                 # Directory listing (if aliased to eza/exa)

# Data processing
cat data.json | jq '.key'          # Parse JSON
yq '.key' config.yaml              # Parse YAML

# Automation
watchexec -e py pytest             # Auto-run tests on file changes
hyperfine 'pytest tests/'          # Benchmark commands

# API testing
http GET localhost:8000/health     # HTTP requests (httpie)

# Git workflow
lazygit                            # Git TUI (visual interface)
git diff                           # Uses delta for better diffs
```

### Tool Selection Guidelines

| Task | Instead of | Use | Why |
|------|-----------|-----|-----|
| Search code | `grep` | `rg` (ripgrep) | 10-100x faster, respects .gitignore |
| Find files | `find` | `fd` | Faster, better syntax, respects .gitignore |
| View files | `cat` | `bat` | Syntax highlighting, line numbers |
| Parse JSON | `grep`/`sed` | `jq` | Proper JSON parsing |
| Parse YAML | `grep`/`sed` | `yq` | Proper YAML parsing |
| Watch files | Manual loops | `watchexec` | Efficient, debounced file watching |
| HTTP requests | `curl` | `http` (httpie) | More readable syntax |
| Benchmark | `time` | `hyperfine` | Statistical analysis, warmup runs |
| Git operations | Manual git | `lazygit` | Visual interface, faster workflows |
