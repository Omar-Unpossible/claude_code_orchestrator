# Claude Code Max Turns: Complete Configuration Guide

## Table of Contents

- [Understanding Turns](#understanding-turns)
- [Turn Ranges by Task Complexity](#turn-ranges-by-task-complexity)
- [Recommended Defaults by Use Case](#recommended-defaults-by-use-case)
- [Adaptive Strategy](#adaptive-strategy)
- [Best Practices](#best-practices)
- [Cost Considerations](#cost-considerations)
- [Quick Reference Table](#quick-reference-table)

---

## Understanding Turns

A **turn** is consumed each time Claude Code makes a tool call. Every time Claude uses `Read`, `Write`, `Edit`, `Bash`, `Grep`, or any other tool, it counts as one turn.

**Key Insight**: The `--max-turns` limit helps prevent agents from getting stuck in infinite loops and burning tokens unnecessarily.

---

## Turn Ranges by Task Complexity

### Simple Tasks: 1-3 Turns

**Use cases:**
- Single file reads or summaries
- Fixing a specific linting error
- Adding documentation to one function
- Reading configuration files

**Example commands:**

```bash
# Fix a single linting error
claude -p "Fix linting errors in auth.py" --max-turns 2

# Read and summarize a file
claude -p "Summarize the API endpoints in routes.py" --max-turns 1

# Generate documentation for one function
claude -p "Add docstrings to the main() function" --max-turns 2
```

**Why keep it low?** These focused, single-action tasks benefit from constraints. Lower turn limits prevent Claude from overthinking or wandering off-task.

---

### Medium Tasks: 3-8 Turns

**Use cases:**
- Debugging and fixing specific bugs
- Adding small features
- Refactoring a single module
- Implementing simple validations

**Example commands:**

```bash
# Debug and fix a specific bug
claude -p "Fix the authentication timeout issue in issue #123" --max-turns 5

# Add a small feature
claude -p "Add email validation to the signup form" --max-turns 6

# Refactor a single module
claude -p "Refactor utils.py to use async/await" --max-turns 8
```

**Why this range?** Provides enough room for Claude to:
1. Read relevant files (1-2 turns)
2. Analyze the problem (investigate with Grep/Bash)
3. Make changes (2-3 turns for edits)
4. Test and verify (1-2 turns)

**Note:** A default of **5 turns** is common for medium complexity tasks.

---

### Complex Tasks: 8-15 Turns

**Use cases:**
- Implementing complete features
- Multi-file refactoring
- Complex debugging across multiple modules
- Adding comprehensive test coverage

**Example commands:**

```bash
# Implement a complete feature
claude -p "Implement OAuth2 authentication with JWT tokens" --max-turns 12

# Multi-file refactoring
claude -p "Migrate from REST to GraphQL across all API routes" --max-turns 15

# Complex debugging
claude -p "Debug and fix the memory leak in the data processing pipeline" --max-turns 10
```

**Key insights:**
- Most plans contain about **8-12 steps**
- A typical greenfield development plan takes **30-45 minutes**
- Claude Code can work autonomously for about **10-20 minutes** before context fills up

**Why this range?** Complex tasks require multiple iterations:
- Reading multiple files
- Creating and editing several files
- Running tests
- Fixing issues discovered during testing
- Committing changes

---

### Very Complex/Autonomous Tasks: 15-30+ Turns

**Use cases:**
- Large-scale migrations
- Comprehensive features with tests and documentation
- Automated issue resolution across repository
- Architectural refactoring

**Example commands:**

```bash
# Large-scale migration
claude -p "Migrate entire codebase from Python 2 to Python 3" --max-turns 25

# Comprehensive feature with tests
claude -p "Build complete user management system with CRUD, tests, and docs" --max-turns 30

# Automated issue resolution
claude -p "Fix all issues labeled 'good-first-issue' in the repo" --max-turns 50
```

**⚠️ Warnings for higher turn counts:**
- **Higher costs** - More turns = more API calls and tokens
- **Context drift risk** - Claude may lose focus over extended sessions
- **Loop potential** - Higher chance of getting stuck in repetitive patterns

---

## Recommended Defaults by Use Case

### CI/CD Pipelines: 2-5 Turns

Fast, predictable results for automated workflows.

```bash
# Pre-commit hook
claude -p "Review and fix linting errors" --max-turns 3 --output-format json

# Code review
claude -p "Review this PR for security issues" --max-turns 2
```

**Why conservative?** Speed and predictability matter in CI/CD. If more turns are needed, trigger another run.

---

### Interactive Development: 8-12 Turns

Balanced approach for feature development during active coding sessions.

```python
# Python session manager example
response = session.query(
    "Implement the payment processing feature",
    max_turns=10,  # Good balance for most features
    allowed_tools=['Read', 'Write', 'Edit', 'Bash']
)
```

---

### Batch Processing: 3-5 Turns Per Item

Process multiple items independently with consistent turn budgets.

```bash
# Process multiple files
for file in *.py; do
    claude -p "Add type hints to $file" --max-turns 3
done
```

---

### Research/Planning: 5-10 Turns

Exploration and analysis tasks that require reading multiple files.

```bash
# Plan mode exploration
claude -p "Analyze codebase and propose architecture improvements" \
    --permission-mode plan \
    --max-turns 8
```

---

## Adaptive Strategy

### Detecting When You Need More Turns

Look for `"subtype": "error_max_turns"` in the JSON response:

```json
{
  "type": "result",
  "subtype": "error_max_turns",
  "num_turns": 5,
  "message": "Reached maximum turns limit"
}
```

### Automatic Turn Calculation

Here's a Python function to suggest `max_turns` based on task complexity:

```python
def adaptive_max_turns(task_description):
    """
    Suggest max_turns based on task complexity indicators.
    """
    # Count complexity indicators
    complex_words = ['migrate', 'refactor', 'implement', 'debug', 
                     'comprehensive', 'entire', 'all']
    file_indicators = ['all files', 'entire codebase', 'multiple', 
                       'across', 'throughout']
    
    complexity = sum(
        word in task_description.lower() 
        for word in complex_words
    )
    scope = sum(
        indicator in task_description.lower() 
        for indicator in file_indicators
    )
    
    # Determine appropriate turn count
    if complexity == 0 and scope == 0:
        return 3  # Simple task
    elif complexity <= 1 and scope == 0:
        return 6  # Medium task
    elif complexity <= 2 or scope == 1:
        return 12  # Complex task
    else:
        return 20  # Very complex task

# Usage example
task = "Implement OAuth2 authentication with JWT tokens"
max_turns = adaptive_max_turns(task)
print(f"Suggested max_turns: {max_turns}")  # Output: 12
```

---

## Best Practices

### 1. Start Conservative, Increase if Needed

```bash
# First attempt with conservative limit
claude -p "Implement new feature" --max-turns 5

# If it hits limit, continue with more turns
claude --continue -p "Finish the task" --max-turns 10
```

### 2. Use Session Continuation for Phased Work

```python
# Phase 1: Planning
response1 = session.query("Plan the refactor", max_turns=5)

# Phase 2: Execution
response2 = session.query("Execute the plan", max_turns=15)
```

### 3. Monitor Actual Usage

```python
# Check if approaching turn limit
if response['num_turns'] >= max_turns * 0.9:
    print("⚠️  Close to limit, consider increasing max_turns")
```

### 4. Use Appropriate Permission Modes

- **`--permission-mode ask`** - Good for learning and safety
- **`--permission-mode plan`** - See the plan before execution
- **`--permission-mode allow`** - Full autonomy (use with appropriate turn limits)

---

## Cost Considerations

Higher turn counts directly impact costs. Approximate costs per session:

| Turn Count | Estimated Cost Range |
|------------|---------------------|
| 3 turns    | $0.01 - $0.05       |
| 10 turns   | $0.05 - $0.15       |
| 30 turns   | $0.15 - $0.50       |

**Balance considerations:**
- **Safety**: Prevent runaway costs and infinite loops
- **Completion**: Give Claude enough turns to finish the task properly

**Tip**: Start with lower turn limits in production environments and increase based on observed needs.

---

## Quick Reference Table

| Task Type | Recommended max-turns | Example |
|-----------|----------------------|---------|
| Quick query/read | 1-2 | "Explain this function" |
| Simple edit | 2-3 | "Fix this bug" |
| Small feature | 5-8 | "Add validation" |
| Medium feature | 8-12 | "Implement auth" |
| Complex refactor | 12-20 | "Migrate to async" |
| Large automation | 20-30+ | "Fix all issues" |
| **Default (if unsure)** | **8-10** | **Most standard tasks** |

---

## Summary

**Start with 5-10 turns for most tasks** and adjust based on results. 

**Key principles:**
1. Simple tasks: Keep turn limits low to prevent overthinking
2. Complex tasks: Allow more turns but monitor for context drift
3. CI/CD: Use conservative limits for predictability
4. Interactive dev: Use moderate limits (8-12) for flexibility
5. Always monitor actual turn usage to optimize future runs

**Remember**: The `--max-turns` parameter is a safety mechanism. It's better to run multiple focused sessions than one uncontrolled session that drifts off-task or burns unnecessary tokens.

---

*Generated for Claude Code headless mode configuration. For more information, visit the [Anthropic documentation](https://docs.claude.com).*
