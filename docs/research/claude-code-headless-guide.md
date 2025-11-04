# Claude Code Headless Mode: Complete Implementation Guide

## Table of Contents
- [Why Use Headless Mode](#why-use-headless-mode)
- [Recommended Implementation Approach](#recommended-implementation-approach)
- [Function Reference](#function-reference)
- [JSON Response Structure](#json-response-structure)
- [Output Format Examples](#output-format-examples)
- [Best Practices](#best-practices)

---

## Why Use Headless Mode

### The PTY Problem
When using Claude Code programmatically through a PTY (pseudo-terminal), the interactive mode fails because:
- Interactive mode uses Ink (React-based terminal UI) which requires "raw mode" on stdin
- PTY with piped input triggers: `Error: Raw mode is not supported on the current process.stdin`
- This is a known issue (GitHub Issue #1072) without a fix as of October 2025

### The Headless Solution
Headless mode (`-p` flag) solves this by:
- **Bypassing the TUI**: No terminal UI components that require raw mode
- **Structured Output**: Returns JSON that's easy to parse programmatically
- **Session Persistence**: Can continue conversations using session IDs
- **Full Capabilities**: Retains all Claude Code features (tools, MCP, hooks)

### What You Lose vs. Gain

**Lost in Headless Mode:**
- Interactive keyboard shortcuts (Escape, Shift+Tab, Ctrl+R)
- Slash commands (`/help`, `/model`, `/clear`, `/rewind`)
- Visual progress indicators and status line
- Real-time interrupt capability
- `#` shortcut for adding to CLAUDE.md on the fly

**Kept in Headless Mode:**
- ✅ Full conversation context via session IDs
- ✅ All tools (Read, Write, Bash, Grep, etc.)
- ✅ CLAUDE.md files and project memory
- ✅ MCP server integrations
- ✅ Hooks and automation
- ✅ Permission management
- ✅ Token/cost tracking in JSON output

**Bottom Line**: For programmatic/PTY use, headless mode is actually *better* because you can build your own UI layer and have predictable, parseable output.

---

## Recommended Implementation Approach

### The Complete Session Manager

This implementation provides:
1. **Session Persistence**: Automatically saves and restores session IDs
2. **Token Tracking**: Monitors cumulative token usage across queries
3. **Cost Management**: Tracks spending per session
4. **Limit Detection**: Warns when approaching context/usage limits
5. **Error Handling**: Gracefully handles timeouts and failures

```python
import subprocess
import json
import os
from datetime import datetime
from pathlib import Path

class ClaudeCodeSession:
    """
    Manages Claude Code headless sessions with automatic session persistence,
    token tracking, and cost monitoring.
    
    This class handles the complexity of:
    - Maintaining conversation context across multiple queries
    - Tracking cumulative costs and token usage
    - Warning when approaching limits
    - Persisting session state to disk
    """
    
    def __init__(self, project_dir=None):
        """
        Initialize a session manager for a specific project.
        
        Args:
            project_dir: Path to project directory. Defaults to current directory.
                        Session state is saved per-project to maintain separate contexts.
        """
        self.project_dir = project_dir or os.getcwd()
        self.session_id = None
        self.total_cost = 0.0
        self.total_tokens = 0
        
        # Create session file path: ~/.claude_sessions/{project_name}.json
        self.session_file = Path.home() / '.claude_sessions' / f"{Path(self.project_dir).name}.json"
        
        # Load existing session if available
        self.load_session()
    
    def load_session(self):
        """
        Load existing session state from disk.
        
        If a session file exists for this project, restore:
        - session_id: For resuming the conversation
        - total_cost: Cumulative spending
        - total_tokens: Cumulative token usage
        
        This allows continuing work after restarts without losing context.
        """
        if self.session_file.exists():
            with open(self.session_file, 'r') as f:
                data = json.load(f)
                self.session_id = data.get('session_id')
                self.total_cost = data.get('total_cost', 0.0)
                self.total_tokens = data.get('total_tokens', 0)
    
    def save_session(self):
        """
        Persist session state to disk.
        
        Saves:
        - session_id: For future resumption
        - total_cost: Running total of costs
        - total_tokens: Running total of tokens used
        - last_updated: Timestamp for debugging
        
        Creates parent directory if it doesn't exist.
        """
        self.session_file.parent.mkdir(exist_ok=True)
        with open(self.session_file, 'w') as f:
            json.dump({
                'session_id': self.session_id,
                'total_cost': self.total_cost,
                'total_tokens': self.total_tokens,
                'last_updated': datetime.now().isoformat()
            }, f, indent=2)
    
    def query(self, prompt, max_turns=None, allowed_tools=None, permission_mode='acceptEdits'):
        """
        Execute a query in headless mode with automatic session management.
        
        This is the main method you'll use. It:
        1. Constructs the claude command with appropriate flags
        2. Resumes existing session or starts new one
        3. Executes the query and captures JSON output
        4. Updates session state and tracks costs/tokens
        5. Checks for limit warnings
        6. Persists session state for next time
        
        Args:
            prompt: The question or instruction to send to Claude
            max_turns: Optional limit on conversation turns (helps control costs)
                      Example: max_turns=3 means Claude can do up to 3 back-and-forth exchanges
            allowed_tools: List of tools Claude can use without asking permission
                          Example: ['Read', 'Write', 'Bash']
            permission_mode: How to handle permissions:
                           - 'acceptEdits': Auto-accept file edits (review bash commands)
                           - 'plan': Plan mode (read-only, asks before executing)
                           - 'accept': Accept everything (use with caution!)
        
        Returns:
            dict: Parsed JSON response containing:
                - result: Claude's response
                - session_id: For resuming later
                - usage: Token breakdown
                - total_cost_usd: Cost for this query
                - error: True if something went wrong
        """
        # Build the command
        cmd = ['claude', '-p', prompt, '--output-format', 'json']
        
        # Resume existing session if we have one
        if self.session_id:
            cmd.extend(['--resume', self.session_id])
        
        # Add optional parameters
        if max_turns:
            cmd.extend(['--max-turns', str(max_turns)])
        
        if allowed_tools:
            cmd.extend(['--allowedTools', ','.join(allowed_tools)])
        
        cmd.extend(['--permission-mode', permission_mode])
        
        # Set environment variables to disable update checks and telemetry
        env = os.environ.copy()
        env['DISABLE_AUTOUPDATER'] = '1'
        env['CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC'] = 'true'
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                env=env,
                timeout=300  # 5 minute timeout (adjust as needed)
            )
            
            # Check for command failure
            if result.returncode != 0:
                return {
                    'error': True,
                    'stderr': result.stderr,
                    'returncode': result.returncode
                }
            
            # Parse JSON response
            response = json.loads(result.stdout)
            
            # Extract and save session ID
            self.session_id = response.get('session_id', self.session_id)
            
            # Update token tracking
            if 'usage' in response:
                usage = response['usage']
                # Sum all token types
                current_tokens = (
                    usage.get('input_tokens', 0) +
                    usage.get('cache_creation_input_tokens', 0) +
                    usage.get('cache_read_input_tokens', 0) +
                    usage.get('output_tokens', 0)
                )
                self.total_tokens += current_tokens
            
            # Update cost tracking
            if 'total_cost_usd' in response:
                self.total_cost += response['total_cost_usd']
            
            # Persist state to disk
            self.save_session()
            
            # Check for warnings (limits, errors, etc.)
            self._check_limits(response)
            
            return response
            
        except subprocess.TimeoutExpired:
            return {'error': True, 'message': 'Query timeout after 5 minutes'}
        except json.JSONDecodeError as e:
            return {
                'error': True,
                'message': f'Failed to parse JSON: {e}',
                'raw': result.stdout
            }
    
    def _check_limits(self, response):
        """
        Check response for limit-related warnings and display alerts.
        
        Monitors:
        1. Error subtypes (max_turns, usage limits)
        2. Total token usage (warns at 80% of typical Pro plan limit)
        3. Cumulative costs (warns at configurable threshold)
        
        This is internal - called automatically after each query.
        """
        # Check for error subtypes
        subtype = response.get('subtype', '')
        if 'error' in subtype:
            print(f"⚠️  Warning: {subtype}")
            if 'max_turns' in subtype:
                print("   Max turns reached. Consider starting new session or increasing --max-turns")
        
        # Check token usage (warn at 80% of 28M Pro limit)
        if self.total_tokens > 22_400_000:
            print(f"⚠️  High token usage: {self.total_tokens:,} tokens used")
            print("   Consider using /compact or starting a new session")
        
        # Check cost (adjust threshold as needed)
        if self.total_cost > 0.50:
            print(f"💰 Cost alert: ${self.total_cost:.3f} spent in this session")
    
    def get_session_info(self):
        """
        Get current session statistics.
        
        Returns:
            dict: Session information including:
                - session_id: Current session identifier
                - total_cost_usd: Cumulative cost
                - total_tokens: Cumulative tokens used
                - project_dir: Project directory path
        
        Useful for monitoring and logging.
        """
        return {
            'session_id': self.session_id,
            'total_cost_usd': self.total_cost,
            'total_tokens': self.total_tokens,
            'project_dir': self.project_dir
        }
    
    def reset_session(self):
        """
        Start a fresh session (equivalent to /clear in interactive mode).
        
        This:
        1. Clears the session_id (next query starts new conversation)
        2. Resets cost and token counters
        3. Deletes the session file
        
        Use when:
        - Starting work on a completely different topic
        - Context has gotten too cluttered
        - You want to save tokens by starting fresh
        """
        self.session_id = None
        self.total_cost = 0.0
        self.total_tokens = 0
        if self.session_file.exists():
            self.session_file.unlink()
        print("✓ Session reset")
```

---

## Function Reference

### Core Methods

#### `__init__(project_dir=None)`
**Purpose**: Initialize the session manager

**Why**: Creates a session manager tied to a specific project directory. Session state is saved per-project so you can maintain separate contexts for different codebases.

**Parameters**:
- `project_dir`: Path to project (defaults to current directory)

**What it does**:
1. Sets up paths for session storage
2. Attempts to load existing session from disk
3. Initializes token and cost tracking

---

#### `query(prompt, max_turns=None, allowed_tools=None, permission_mode='acceptEdits')`
**Purpose**: Execute a Claude Code query in headless mode

**Why**: This is the main interface - it handles all the complexity of constructing commands, managing sessions, and tracking resources.

**Parameters**:
- `prompt`: Your question or instruction
- `max_turns`: Limits conversation length (controls costs)
- `allowed_tools`: Which tools Claude can use (e.g., `['Read', 'Write']`)
- `permission_mode`: How to handle permissions:
  - `'acceptEdits'`: Auto-accept file edits
  - `'plan'`: Plan mode (read-only)
  - `'accept'`: Accept everything

**Returns**: JSON response dict with result, session_id, usage, cost

**What it does**:
1. Builds the `claude` command with all flags
2. Adds `--resume` if session exists (maintains context)
3. Disables update checks via environment variables
4. Executes command and captures output
5. Parses JSON response
6. Updates session_id for next time
7. Tracks cumulative tokens and cost
8. Saves state to disk
9. Checks for limit warnings
10. Returns parsed response

---

#### `load_session()`
**Purpose**: Restore session state from disk

**Why**: Allows continuing work after terminal closes or system restarts. Session context is preserved.

**What it does**:
1. Checks if session file exists for this project
2. Loads session_id, total_cost, and total_tokens
3. Restores state so next query continues the conversation

---

#### `save_session()`
**Purpose**: Persist session state to disk

**Why**: Ensures session state survives between script runs. Called automatically after each query.

**What it does**:
1. Creates session directory if needed
2. Writes JSON file with session data
3. Includes timestamp for debugging

---

#### `_check_limits(response)`
**Purpose**: Monitor for limit warnings

**Why**: Claude Code has token and usage limits. This warns you before you hit them unexpectedly.

**What it does**:
1. Checks response subtype for errors
2. Monitors cumulative token usage (warns at 80% of 28M limit)
3. Tracks cumulative costs (warns at $0.50 by default)
4. Prints warnings to console

---

#### `get_session_info()`
**Purpose**: Get current session statistics

**Why**: Useful for logging, monitoring, or displaying to users.

**Returns**: Dict with session_id, total_cost_usd, total_tokens, project_dir

---

#### `reset_session()`
**Purpose**: Start fresh conversation

**Why**: Sometimes context gets cluttered or you're switching topics. This is equivalent to `/clear` in interactive mode.

**What it does**:
1. Clears session_id
2. Resets cost/token counters
3. Deletes session file

---

## JSON Response Structure

### Standard JSON Response (`--output-format json`)

When a query completes successfully:

```json
{
  "type": "result",
  "subtype": "success",
  "is_error": false,
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "num_turns": 3,
  "duration_ms": 15448,
  "duration_api_ms": 15268,
  "total_cost_usd": 0.0234,
  "usage": {
    "input_tokens": 1250,
    "cache_creation_input_tokens": 5000,
    "cache_read_input_tokens": 12000,
    "output_tokens": 450,
    "server_tool_use": {
      "web_search_requests": 0
    },
    "service_tier": "standard"
  },
  "result": {
    "content": [
      {
        "type": "text",
        "text": "I've analyzed the codebase and found 3 issues..."
      }
    ]
  }
}
```

### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Always `"result"` for completed queries |
| `subtype` | string | `"success"` or error type like `"error_max_turns"` |
| `is_error` | boolean | `true` if query failed |
| `session_id` | string | UUID for resuming this conversation |
| `num_turns` | integer | Number of back-and-forth exchanges |
| `duration_ms` | integer | Total time including tool execution |
| `duration_api_ms` | integer | Time spent in API calls |
| `total_cost_usd` | float | Cost for this specific query |
| `usage` | object | Token breakdown (see below) |
| `result.content` | array | Claude's actual response |

### Usage Object Breakdown

```json
{
  "input_tokens": 1250,              // New tokens sent to Claude
  "cache_creation_input_tokens": 5000,  // Tokens cached for future use
  "cache_read_input_tokens": 12000,     // Tokens read from cache (cheaper!)
  "output_tokens": 450,                 // Tokens in Claude's response
  "server_tool_use": {
    "web_search_requests": 0           // Number of web searches
  }
}
```

**Token Costs** (approximate):
- Input tokens: ~$3 per million
- Cache creation: ~$3.75 per million (one-time)
- Cache read: ~$0.30 per million (90% cheaper!)
- Output tokens: ~$15 per million

### Error Response

When `is_error: true`:

```json
{
  "type": "result",
  "subtype": "error_max_turns",
  "is_error": true,
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "total_cost_usd": 0.0569,
  "usage": { ... },
  "error_message": "Maximum turns limit reached"
}
```

Common `subtype` errors:
- `error_max_turns`: Hit the `--max-turns` limit
- `error_permission_denied`: Tool permission not granted
- `error_timeout`: Query took too long

---

## Output Format Examples

### Example 1: Basic Usage

```python
# Initialize session
session = ClaudeCodeSession()

# First query - creates new session
response = session.query(
    "Analyze the structure of this codebase",
    max_turns=5,
    allowed_tools=['Read', 'Grep', 'Glob']
)

if not response.get('error'):
    # Extract the actual text response
    result_text = response['result']['content'][0]['text']
    print(f"Claude says: {result_text[:200]}...")
    
    # Show session info
    print(f"\nSession ID: {response['session_id']}")
    print(f"Cost: ${response['total_cost_usd']:.4f}")
    print(f"Tokens used: {response['usage']['output_tokens']}")
```

### Example 2: Continuing a Session

```python
# The session_id is automatically saved and reused
response2 = session.query(
    "Now add error handling to the main module",
    max_turns=3,
    allowed_tools=['Read', 'Write', 'Edit']
)

# Check cumulative stats
info = session.get_session_info()
print(f"\nSession Stats:")
print(f"  Total Cost: ${info['total_cost_usd']:.4f}")
print(f"  Total Tokens: {info['total_tokens']:,}")
```

### Example 3: CI/CD Integration

```bash
#!/bin/bash
# Pre-commit hook with JSON parsing

changed_files=$(git diff --cached --name-only)

result=$(claude -p "Review these files: $changed_files" \
    --output-format json \
    --allowedTools "Read,Grep" \
    --max-turns 2)

# Extract specific fields with jq
issues=$(echo "$result" | jq -r '.result.content[0].text')
cost=$(echo "$result" | jq -r '.total_cost_usd')
session=$(echo "$result" | jq -r '.session_id')

echo "Review complete!"
echo "Cost: \$$cost"
echo "Session: $session"
echo ""
echo "$issues"

# Block commit if critical issues found
if echo "$issues" | grep -qi "critical"; then
    echo "❌ Critical issues found. Commit blocked."
    exit 1
fi
```

### Example 4: Batch Processing with Cost Tracking

```python
import subprocess
import json

def analyze_file(filepath):
    """Analyze a single file"""
    result = subprocess.run(
        ['claude', '-p', f'Find bugs in {filepath}',
         '--output-format', 'json',
         '--allowedTools', 'Read',
         '--max-turns', '2'],
        capture_output=True,
        text=True
    )
    return json.loads(result.stdout)

# Process multiple files
files = ['api/auth.py', 'api/users.py', 'api/payments.py']
results = []
total_cost = 0.0

for file in files:
    print(f"Analyzing {file}...")
    response = analyze_file(file)
    
    results.append({
        'file': file,
        'issues': response['result']['content'][0]['text'],
        'cost': response['total_cost_usd']
    })
    
    total_cost += response['total_cost_usd']

print(f"\n✓ Complete. Total: ${total_cost:.4f}")
```

### Example 5: Stream JSON for Real-time Updates

```bash
# Use stream-json for large operations
claude -p "Analyze this 10,000 line file" \
    --output-format stream-json \
    --allowedTools "Read" \
    | while IFS= read -r line; do
        # Each line is a JSON object
        type=$(echo "$line" | jq -r '.type // empty')
        
        if [ "$type" = "assistant" ]; then
            # Extract and display progress
            text=$(echo "$line" | jq -r '.message.content[]?.text // empty')
            [ -n "$text" ] && echo "📝 $text"
        fi
    done
```

### Example 6: Database Logging

```python
import sqlite3
from datetime import datetime

def log_query_to_db(session, prompt, response):
    """Log each query for auditing/analysis"""
    conn = sqlite3.connect('claude_logs.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO queries (
            timestamp, project, session_id, prompt,
            result, cost, tokens, duration_ms
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        datetime.now(),
        session.project_dir,
        response['session_id'],
        prompt,
        response['result']['content'][0]['text'],
        response['total_cost_usd'],
        response['usage']['output_tokens'],
        response['duration_ms']
    ))
    
    conn.commit()
    conn.close()

# Usage
session = ClaudeCodeSession()
response = session.query("Analyze error logs")
log_query_to_db(session, "Analyze error logs", response)
```

---

## Best Practices

### 1. Always Use Session Management
```python
# ✅ Good: Session context preserved
session = ClaudeCodeSession()
response1 = session.query("Analyze code")
response2 = session.query("Now add tests")  # Remembers context

# ❌ Bad: Each call starts fresh, wastes tokens
subprocess.run(['claude', '-p', "Analyze code", ...])
subprocess.run(['claude', '-p', "Now add tests", ...])  # No context!
```

### 2. Control Costs with `max_turns`
```python
# Limit how much Claude can do
response = session.query(
    "Review and fix all issues",
    max_turns=5  # Prevents runaway costs
)
```

### 3. Monitor Token Usage
```python
# Check before running expensive operations
info = session.get_session_info()
if info['total_tokens'] > 20_000_000:
    print("⚠️  High token usage, consider resetting session")
    session.reset_session()
```

### 4. Use Appropriate Permission Modes
```python
# For code exploration (safe, read-only)
response = session.query(
    "Explain this codebase",
    permission_mode='plan',
    allowed_tools=['Read', 'Grep']
)

# For making changes (review bash commands)
response = session.query(
    "Fix all linting issues",
    permission_mode='acceptEdits',
    allowed_tools=['Read', 'Write', 'Edit', 'Bash']
)
```

### 5. Handle Errors Gracefully
```python
response = session.query("Analyze code")

if response.get('error'):
    print(f"Error: {response.get('message', 'Unknown error')}")
    print(f"Details: {response.get('stderr', 'N/A')}")
else:
    # Process successful response
    result = response['result']['content'][0]['text']
```

### 6. Reset Session When Switching Topics
```python
# Working on authentication
session.query("Add JWT authentication")
session.query("Write tests for auth")

# Now switching to database work
session.reset_session()  # Start fresh
session.query("Design user schema")
```

### 7. Use Stream JSON for Long Operations
```bash
# For operations that take a while, see progress in real-time
claude -p "Analyze 100 files" \
    --output-format stream-json \
    | jq -r 'select(.message.content) | .message.content[]?.text // empty'
```

---

## Additional Resources

- **Official Docs**: https://docs.claude.com/en/docs/claude-code
- **Best Practices**: https://www.anthropic.com/engineering/claude-code-best-practices
- **GitHub Issues**: https://github.com/anthropics/claude-code/issues
- **Community**: r/ClaudeAI on Reddit

---

## Quick Reference

### Common Commands

```bash
# Start headless query with JSON output
claude -p "your prompt" --output-format json

# Continue most recent session
claude -c -p "continue the work" --output-format json

# Resume specific session
claude --resume <session-id> -p "next task" --output-format json

# Limit turns to control costs
claude -p "task" --max-turns 3 --output-format json

# Specify allowed tools
claude -p "task" --allowedTools "Read,Write,Edit" --output-format json

# Stream JSON for real-time updates
claude -p "large task" --output-format stream-json
```

### Quick Python Usage

```python
from claude_code_session import ClaudeCodeSession

# Initialize
session = ClaudeCodeSession()

# Query
response = session.query(
    "Your prompt here",
    max_turns=5,
    allowed_tools=['Read', 'Write']
)

# Check result
if not response.get('error'):
    print(response['result']['content'][0]['text'])
    print(f"Cost: ${response['total_cost_usd']:.4f}")
```

---

*Last updated: November 2025*
