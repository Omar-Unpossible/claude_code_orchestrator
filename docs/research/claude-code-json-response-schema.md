# Claude Code JSON Response Schema

**Tested**: 2025-11-03
**Claude Code Version**: Latest (headless mode)
**Output Format**: `--output-format json`

---

## Executive Summary

### Context Window Tracking Decision

**❌ Claude Code does NOT provide context window usage tracking in JSON responses**

**What we have**:
- `modelUsage[model].contextWindow`: 200000 (the LIMIT, not current usage)
- Token breakdown per request (input, cache, output)

**What we DON'T have**:
- `context_window_used` - Current cumulative usage
- `context_window_limit` - Dynamic limit
- `context_window_pct` - Usage percentage

**Implementation Decision**: **Path B - Manual Token Tracking Required**

We must implement cumulative token tracking in StateManager to monitor context window usage across session.

---

## Complete Field Reference

### Top-Level Fields

| Field | Type | Always Present | Description | Example |
|-------|------|----------------|-------------|---------|
| `type` | string | ✅ | Response type | `"result"` |
| `subtype` | string | ✅ | Response subtype | `"success"`, `"error_max_turns"` |
| `is_error` | boolean | ✅ | Error flag | `false` |
| `duration_ms` | integer | ✅ | Total duration including tools | `14301` |
| `duration_api_ms` | integer | ✅ | API call duration | `27618` |
| `num_turns` | integer | ✅ | Number of turns used | `2` |
| `result` | string | ⚠️ | Actual response text (missing on error) | `"The current directory..."` |
| `session_id` | string (UUID) | ✅ | Session identifier | `"550e8400-e29b-..."` |
| `total_cost_usd` | float | ✅ | Total cost for this request | `0.013645` |
| `usage` | object | ✅ | Token usage breakdown | See below |
| `modelUsage` | object | ✅ | Per-model usage details | See below |
| `permission_denials` | array | ✅ | Denied tool uses | `[]` or list |
| `uuid` | string (UUID) | ✅ | Request UUID (different from session_id) | `"3eb1e1b4-..."` |
| `errors` | array | ✅ | Error list | `[]` |

---

### `usage` Object

Token usage summary across all models:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `input_tokens` | integer | New input tokens | `9` |
| `cache_creation_input_tokens` | integer | Tokens added to cache | `12871` |
| `cache_read_input_tokens` | integer | Tokens read from cache (cheaper!) | `36391` |
| `output_tokens` | integer | Response tokens | `510` |
| `server_tool_use` | object | Server-side tool usage | See below |
| `service_tier` | string | Service tier | `"standard"` |
| `cache_creation` | object | Cache creation details | See below |

#### `usage.server_tool_use` Object

| Field | Type | Description |
|-------|------|-------------|
| `web_search_requests` | integer | Number of web searches |
| `web_fetch_requests` | integer | Number of web fetches |

#### `usage.cache_creation` Object

| Field | Type | Description |
|-------|------|-------------|
| `ephemeral_1h_input_tokens` | integer | 1-hour cache tokens |
| `ephemeral_5m_input_tokens` | integer | 5-minute cache tokens |

---

### `modelUsage` Object

Per-model usage breakdown. Contains one entry per model used (Sonnet, Haiku, etc.):

```json
"modelUsage": {
    "claude-sonnet-4-5-20250929": { ... },
    "claude-haiku-4-5-20251001": { ... }
}
```

Each model entry contains:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `inputTokens` | integer | Input tokens for this model | `0` |
| `outputTokens` | integer | Output tokens for this model | `774` |
| `cacheReadInputTokens` | integer | Cache read tokens | `0` |
| `cacheCreationInputTokens` | integer | Cache creation tokens | `0` |
| `webSearchRequests` | integer | Web searches by this model | `0` |
| `costUSD` | float | Cost for this model | `0.01161` |
| **`contextWindow`** | **integer** | **Context window LIMIT** | **`200000`** |

**⚠️ IMPORTANT**: `contextWindow` is the LIMIT (200k tokens), NOT the current usage. This is a static value showing the model's capacity, not how much has been consumed.

---

### `permission_denials` Array

List of tools that were denied permission:

```json
"permission_denials": [
    {
        "tool_name": "Bash",
        "tool_use_id": "toolu_01W8cSRZ2WmrrQxV5j4suQ3q",
        "tool_input": {
            "command": "tree -L 3 ...",
            "description": "Show directory tree structure"
        }
    }
]
```

| Field | Type | Description |
|-------|------|-------------|
| `tool_name` | string | Tool that was denied |
| `tool_use_id` | string | Unique tool use ID |
| `tool_input` | object | Input parameters for the tool |

---

## Response Subtypes

### Success Response

```json
{
    "type": "result",
    "subtype": "success",
    "is_error": false,
    "result": "The actual response text...",
    ...
}
```

**Characteristics**:
- `subtype`: `"success"`
- `is_error`: `false`
- `result`: Contains the actual text response
- `errors`: Empty array

---

### error_max_turns Response

Returned when `--max-turns` limit is reached:

```json
{
    "type": "result",
    "subtype": "error_max_turns",
    "is_error": false,
    "num_turns": 2,
    "duration_ms": 207832,
    ...
}
```

**Characteristics**:
- `subtype`: `"error_max_turns"`
- `is_error`: `false` (⚠️ Note: NOT marked as error!)
- `num_turns`: Shows turns used (should equal max_turns limit)
- `result`: May still contain partial work
- Work may be incomplete

**Handling**: Obra should:
1. Detect `subtype == "error_max_turns"`
2. Retry with increased max_turns (e.g., double)
3. Use `--resume` to continue session
4. Enforce upper bound (e.g., 30 turns max)

---

### Other Error Subtypes (Expected)

Based on the headless guide, these error subtypes exist but were not tested:

- `error_permission_denied` - Tool permission denied
- `error_timeout` - Request timed out
- `error_network` - Network error
- `error_invalid_request` - Invalid request parameters

**Format** (expected):
```json
{
    "type": "result",
    "subtype": "error_...",
    "is_error": true,
    "error_message": "Description of error",
    ...
}
```

---

## Token Calculation

### How to Calculate Total Tokens

```python
total_tokens = (
    usage['input_tokens'] +
    usage['cache_creation_input_tokens'] +
    usage['cache_read_input_tokens'] +
    usage['output_tokens']
)
```

**Example**:
```python
# From Test 1:
total = 9 + 12871 + 36391 + 510 = 49,781 tokens
```

### Cache Efficiency

Calculate cache hit rate:
```python
cache_hit_rate = (
    usage['cache_read_input_tokens'] /
    (usage['input_tokens'] + usage['cache_creation_input_tokens'] + usage['cache_read_input_tokens'])
)
```

**Example**:
```python
# From Test 1:
cache_hit_rate = 36391 / (9 + 12871 + 36391) = 73.8%
```

High cache hit rate (>70%) indicates efficient session reuse.

---

## Cost Calculation

### Total Cost
Sum of all model costs:
```python
total_cost = sum(model['costUSD'] for model in modelUsage.values())
```

Should match `total_cost_usd` field.

### Cost Breakdown

**Approximate pricing** (may vary):
- Input tokens: ~$3 per million
- Cache creation: ~$3.75 per million (one-time)
- Cache read: ~$0.30 per million (90% cheaper!)
- Output tokens: ~$15 per million

**Cache read savings**:
```python
# Cache read is 90% cheaper than regular input
savings_per_token = (3.00 - 0.30) / 1_000_000 = $0.0000027
total_savings = cache_read_tokens * savings_per_token
```

---

## Session Management

### Session ID

- `session_id`: Persistent across `--resume` calls
- Format: UUID v4
- Same session = shared context and cached CLAUDE.md

**Session continuity**:
```bash
# First call - creates session
claude -p "Task 1" --session-id "550e8400-..."

# Second call - continues session
claude --resume "550e8400-..." -p "Task 2"
```

### Request UUID

- `uuid`: Unique per request
- Different from `session_id`
- Used for request tracking/logging

---

## Example Responses

### Example 1: Success Response (Simple Task)

```json
{
    "type": "result",
    "subtype": "success",
    "is_error": false,
    "duration_ms": 14301,
    "duration_api_ms": 27618,
    "num_turns": 2,
    "result": "The current directory contains...",
    "session_id": "550e8400-e29b-41d4-a716-446655440001",
    "total_cost_usd": 0.013645,
    "usage": {
        "input_tokens": 9,
        "cache_creation_input_tokens": 12871,
        "cache_read_input_tokens": 36391,
        "output_tokens": 510,
        "server_tool_use": {
            "web_search_requests": 0,
            "web_fetch_requests": 0
        },
        "service_tier": "standard",
        "cache_creation": {
            "ephemeral_1h_input_tokens": 0,
            "ephemeral_5m_input_tokens": 12871
        }
    },
    "modelUsage": {
        "claude-sonnet-4-5-20250929": {
            "inputTokens": 0,
            "outputTokens": 774,
            "cacheReadInputTokens": 0,
            "cacheCreationInputTokens": 0,
            "webSearchRequests": 0,
            "costUSD": 0.01161,
            "contextWindow": 200000
        },
        "claude-haiku-4-5-20251001": {
            "inputTokens": 0,
            "outputTokens": 407,
            "cacheReadInputTokens": 0,
            "cacheCreationInputTokens": 0,
            "webSearchRequests": 0,
            "costUSD": 0.0020350000000000004,
            "contextWindow": 200000
        }
    },
    "permission_denials": [],
    "uuid": "3eb1e1b4-106d-48ef-8127-1a1bcc6b9c3e"
}
```

**Analysis**:
- Total tokens: 49,781
- Cache hit rate: 73.8%
- Models used: Sonnet (planning) + Haiku (execution)
- Cost: $0.0136 (reasonable for simple task)

---

### Example 2: Session Continuation

```json
{
    "type": "result",
    "subtype": "success",
    "is_error": false,
    "duration_ms": 19015,
    "duration_api_ms": 20951,
    "num_turns": 3,
    "result": "There are **40 test files** in the tests directory...",
    "session_id": "550e8400-e29b-41d4-a716-446655440001",
    "total_cost_usd": 0.01481,
    "usage": {
        "input_tokens": 10,
        "cache_creation_input_tokens": 1067,
        "cache_read_input_tokens": 51013,
        "output_tokens": 895,
        "server_tool_use": {
            "web_search_requests": 0,
            "web_fetch_requests": 0
        },
        "service_tier": "standard",
        "cache_creation": {
            "ephemeral_1h_input_tokens": 0,
            "ephemeral_5m_input_tokens": 1067
        }
    },
    "modelUsage": {
        "claude-haiku-4-5-20251001": {
            "inputTokens": 0,
            "outputTokens": 277,
            "cacheReadInputTokens": 0,
            "cacheCreationInputTokens": 0,
            "webSearchRequests": 0,
            "costUSD": 0.001385,
            "contextWindow": 200000
        },
        "claude-sonnet-4-5-20250929": {
            "inputTokens": 0,
            "outputTokens": 895,
            "cacheReadInputTokens": 0,
            "cacheCreationInputTokens": 0,
            "webSearchRequests": 0,
            "costUSD": 0.013425,
            "contextWindow": 200000
        }
    },
    "permission_denials": [],
    "uuid": "26bb00ae-f4d6-4146-8484-bc59e3b685a6"
}
```

**Analysis**:
- Total tokens: 52,985
- Cache hit rate: 96.3% (excellent! Session reuse working)
- Same session_id as Example 1 (continued session)
- More cache reads, fewer cache creations (efficient)

---

### Example 3: error_max_turns

```json
{
    "type": "result",
    "subtype": "error_max_turns",
    "duration_ms": 207832,
    "duration_api_ms": 222532,
    "is_error": false,
    "num_turns": 2,
    "session_id": "550e8400-e29b-41d4-a716-446655440002",
    "total_cost_usd": 0.16741,
    "usage": {
        "input_tokens": 3,
        "cache_creation_input_tokens": 8999,
        "cache_read_input_tokens": 14981,
        "output_tokens": 456,
        "server_tool_use": {
            "web_search_requests": 0,
            "web_fetch_requests": 0
        },
        "service_tier": "standard",
        "cache_creation": {
            "ephemeral_1h_input_tokens": 0,
            "ephemeral_5m_input_tokens": 8999
        }
    },
    "modelUsage": {
        "claude-haiku-4-5-20251001": {
            "inputTokens": 0,
            "outputTokens": 353,
            "cacheReadInputTokens": 0,
            "cacheCreationInputTokens": 0,
            "webSearchRequests": 0,
            "costUSD": 0.001765,
            "contextWindow": 200000
        },
        "claude-sonnet-4-5-20250929": {
            "inputTokens": 0,
            "outputTokens": 11043,
            "cacheReadInputTokens": 0,
            "cacheCreationInputTokens": 0,
            "webSearchRequests": 0,
            "costUSD": 0.165645,
            "contextWindow": 200000
        }
    },
    "permission_denials": [
        {
            "tool_name": "Bash",
            "tool_use_id": "toolu_01W8cSRZ2WmrrQxV5j4suQ3q",
            "tool_input": {
                "command": "tree -L 3 /home/omarwsl/projects/claude_code_orchestrator/src -I '__pycache__|*.pyc'",
                "description": "Show directory tree structure"
            }
        }
    ],
    "uuid": "eeb6ebee-680d-45cf-91a2-b47836364924",
    "errors": []
}
```

**Analysis**:
- `subtype`: "error_max_turns" (hit max_turns=2)
- `is_error`: false (⚠️ not marked as error)
- `num_turns`: 2 (confirmed limit reached)
- `permission_denials`: Bash command was denied
- Total tokens: 24,439
- Cost: $0.1674 (higher due to large Sonnet output)
- Work incomplete - needs retry with more turns

---

## Implementation Guidance

### Extracting Metadata in Obra

```python
def _extract_metadata(self, response: Dict[str, Any]) -> Dict[str, Any]:
    """Extract metadata from Claude Code JSON response."""
    usage = response.get('usage', {})

    return {
        'session_id': response.get('session_id'),
        'num_turns': response.get('num_turns', 0),
        'duration_ms': response.get('duration_ms', 0),
        'duration_api_ms': response.get('duration_api_ms', 0),
        'cost_usd': response.get('total_cost_usd', 0.0),
        'error_subtype': response.get('subtype') if response.get('subtype') != 'success' else None,

        # Token usage
        'input_tokens': usage.get('input_tokens', 0),
        'cache_creation_tokens': usage.get('cache_creation_input_tokens', 0),
        'cache_read_tokens': usage.get('cache_read_input_tokens', 0),
        'output_tokens': usage.get('output_tokens', 0),
        'total_tokens': (
            usage.get('input_tokens', 0) +
            usage.get('cache_creation_input_tokens', 0) +
            usage.get('cache_read_input_tokens', 0) +
            usage.get('output_tokens', 0)
        ),

        # Context window (static limit only)
        'context_window_limit': self._get_context_window_limit(response),

        # NO context_window_used or context_window_pct available!
    }

def _get_context_window_limit(self, response: Dict[str, Any]) -> Optional[int]:
    """Extract context window limit from modelUsage."""
    model_usage = response.get('modelUsage', {})

    # Get first model's context window (should be same for all)
    for model, usage in model_usage.items():
        return usage.get('contextWindow')

    return None  # Default: 200000
```

### Error Detection

```python
def _check_for_errors(self, response: Dict[str, Any]) -> None:
    """Check response for errors."""
    subtype = response.get('subtype', '')

    # Check for error subtypes
    if subtype == 'error_max_turns':
        raise MaxTurnsError(
            f"Max turns limit reached ({response.get('num_turns')})",
            response=response
        )
    elif subtype.startswith('error_'):
        raise AgentException(
            f"Claude Code error: {subtype}",
            context={'subtype': subtype, 'response': response}
        )

    # Also check is_error flag (though error_max_turns has is_error=false)
    if response.get('is_error'):
        error_msg = response.get('error_message', 'Unknown error')
        raise AgentException(
            f"Claude Code failed: {error_msg}",
            context={'response': response}
        )
```

### Context Window Tracking (Manual - Required!)

Since Claude Code doesn't provide current context usage, we must track manually:

```python
# In StateManager
def add_session_tokens(self, session_id: str, task_id: int, tokens: Dict[str, int]) -> None:
    """Add tokens to session cumulative total."""
    current = self.get_session_token_usage(session_id)
    new_cumulative = current + tokens['total_tokens']

    # Store in database
    usage = ContextWindowUsage(
        session_id=session_id,
        task_id=task_id,
        cumulative_tokens=new_cumulative,
        **tokens
    )
    self.session.add(usage)
    self.session.commit()

def get_session_token_usage(self, session_id: str) -> int:
    """Get cumulative token usage for session."""
    latest = self.session.query(ContextWindowUsage)\
        .filter_by(session_id=session_id)\
        .order_by(ContextWindowUsage.timestamp.desc())\
        .first()

    return latest.cumulative_tokens if latest else 0
```

---

## Key Findings Summary

### ✅ What We Have
- Complete token usage breakdown per request
- Session ID for continuity
- Cost tracking
- Duration metrics
- Error subtypes
- Permission denials
- Per-model usage details
- Context window LIMIT (200k)

### ❌ What We DON'T Have
- Current context window usage
- Context window percentage
- Cumulative token tracking across session

### 📋 Implementation Decision

**We MUST implement Path B: Manual Token Tracking**

This means:
1. Create `ContextWindowUsage` model/table
2. Track cumulative tokens in StateManager
3. Calculate percentage manually: `tokens / 200000`
4. Implement threshold checks in Orchestrator
5. Handle session refresh when approaching limit

**Estimated effort**: 30-36 hours (Phase 3, Path B)

---

**Document Status**: Complete
**Testing Date**: 2025-11-03
**Decision**: Path B (Manual Tracking) Required
