# CLAUDE CODE OPTIMIZATION RULES [LLM-OPTIMIZED]

**Version**: 2.0.1-LLM  
**Format**: Machine-Readable Directives  
**Last Updated**: November 15, 2025  
**Status**: Active Rules for Agentic Coding Systems

---

## TIER 1: CRITICAL RULES (ALWAYS APPLY)

### FILE STRUCTURE RULES

**RULE 1: CLAUDE.md SIZE LIMIT**
- MUST keep CLAUDE.md between 300-400 lines
- MUST NOT exceed 5,000 tokens
- Target: 3,000-5,000 tokens
- Content: Core rules ONLY

**RULE 2: PROJECT.md SIZE LIMIT**
- MUST keep .claude/PROJECT.md between 400-700 lines
- MUST NOT exceed 9,000 tokens
- Target: 5,000-9,000 tokens
- Content: Workflows, architecture, patterns

**RULE 3: RULES.md SIZE LIMIT**
- IF .claude/RULES.md exists: MUST keep 2,000-4,000 tokens
- MUST contain code style, conventions, constraints ONLY

**RULE 4: TOTAL STARTUP CONTEXT**
- MUST keep total startup context <15,000 tokens
- Formula: CLAUDE.md + PROJECT.md + RULES.md + Skills metadata + config
- Excludes: Skills content (loaded on-demand)

**RULE 5: SKILLS METADATA BUDGET**
- EACH Skill metadata: 30-50 tokens (description in SKILL.md header)
- TOTAL Skills metadata: 300-500 tokens (for 10-15 Skills)
- Full Skill content: Loaded ONLY when invoked

### CONTEXT LOADING SEQUENCE

**RULE 6: LOADING HIERARCHY**
ALWAYS load in this order:
1. Global config (~/.claude/)
2. Project config (.claude/)
3. CLAUDE.md (root)
4. .claude/PROJECT.md
5. Skills metadata (descriptions only)
6. On-demand: Skill content when invoked

**RULE 7: PROGRESSIVE DISCLOSURE PATTERN**
- Metadata: ALWAYS in context (lightweight)
- Content: NEVER load upfront
- Loading: ONLY when Claude determines relevance
- Benefit: Zero-cost documentation until needed

### INFORMATION HIERARCHY RULES

**RULE 8: 4-TIER CONTENT DISTRIBUTION**

**Tier 1 - CLAUDE.md (ALWAYS LOADED)**:
- Critical rules that affect ALL tasks
- Project identity and scope
- Absolute constraints (security, compliance)
- Forbidden operations
- Core coding standards

**Tier 2 - .claude/PROJECT.md (ALWAYS LOADED)**:
- Architecture patterns
- Module structure
- Workflows (development, testing, deployment)
- Technology stack decisions
- Integration points

**Tier 3 - Skills (ON-DEMAND)**:
- Specialized procedures
- Technology-specific guides
- Complex workflows
- Reference implementations
- Best practices for specific tasks

**Tier 4 - Source Code (ON-DEMAND)**:
- Implementation details
- Existing code for context
- Dependencies
- Generated documentation

**RULE 9: CONTENT PLACEMENT DECISION TREE**

```
IF affects every task → CLAUDE.md
ELSE IF affects multiple modules/workflows → PROJECT.md
ELSE IF specialized/infrequent → Skill
ELSE IF implementation detail → Source code comments
```

### TOKEN OPTIMIZATION RULES

**RULE 10: ELIMINATE REDUNDANCY**
- NEVER repeat information across files
- NEVER explain same concept twice
- ALWAYS use references to other sections/files
- Pattern: "See [FILENAME]:[SECTION]" instead of duplicating

**RULE 11: BULLET-FIRST FORMATTING**
- ALWAYS use bullets over prose paragraphs
- ALWAYS use imperative verbs
- NEVER use narrative exposition
- Maximum: 1-2 sentence bullets

**RULE 12: DIRECTIVE LANGUAGE**
- MUST use: MUST, NEVER, ALWAYS, IF/THEN, ONLY IF, WHEN
- AVOID: "should", "consider", "it's good to", "we recommend"
- PREFER: Direct commands over suggestions
- Example: "ALWAYS validate inputs" NOT "You should validate inputs"

**RULE 13: EXAMPLE COMPACTNESS**
- IF example needed: Maximum 10 lines
- ALWAYS omit boilerplate
- ALWAYS use comments to explain, not prose
- Pattern: `// MUST: [rule]` in code

### SKILLS ARCHITECTURE RULES

**RULE 14: SKILL CREATION CRITERIA**
CREATE Skill ONLY IF:
- Content >500 tokens AND
- Used <50% of sessions AND
- Self-contained domain

DO NOT create Skill IF:
- Content <500 tokens (put in PROJECT.md)
- Used >50% of sessions (put in CLAUDE.md)
- Depends heavily on other content

**RULE 15: SKILL STRUCTURE**
```
.claude/skills/[skill-name]/
├─ SKILL.md          # MUST: Start with description (30-50 tokens)
├─ instructions.md   # OPTIONAL: Detailed procedures
├─ examples/         # OPTIONAL: Reference code
└─ scripts/          # OPTIONAL: Automation
```

**RULE 16: SKILL METADATA FORMAT**
First section of SKILL.md MUST contain:
```markdown
# [Skill Name]

**Description**: [1-2 sentence description, 30-50 tokens]
**Triggers**: [When to invoke this Skill]
**Token Cost**: [Estimated tokens when loaded]
```

**RULE 17: SKILL INVOCATION SIGNALS**
Include EXPLICIT triggers in Skill description:
- Keywords that indicate relevance
- Task types that need this Skill
- File patterns that trigger use
- Technologies that require this knowledge

### FILE LOCATION RULES

**RULE 18: CONFIGURATION FILE LOCATIONS**
```
~/.claude/config.json        # API keys, global settings
~/.claude/settings.json      # User defaults
~/.claude/skills/            # Personal Skills (always available)

.claude/settings.json        # Project settings (SHARED via git)
.claude/settings.local.json  # Local overrides (MUST git-ignore)
.claude/skills/              # Project Skills (SHARED via git)
.claude/agents/              # Subagent configs
.claude/hooks/               # Automation hooks

CLAUDE.md                    # Root file (ALWAYS loaded)
.mcp.json                    # MCP server config (root)
```

**RULE 19: GIT TRACKING**
MUST commit to git:
- .claude/settings.json
- .claude/skills/
- CLAUDE.md
- .claude/PROJECT.md

MUST git-ignore:
- .claude/settings.local.json
- .claude/.cache/
- .claude/logs/

### MODEL SELECTION RULES

**RULE 20: MODEL CHOICE DECISION TREE**
```
IF task = complex reasoning OR novel architecture → claude-sonnet-4-5-20250929
ELSE IF task = standard CRUD OR well-defined → claude-sonnet-4-20250514
ELSE IF task = simple refactor OR formatting → claude-haiku-4-5-20250919
ELSE IF task = maximum quality critical → claude-opus-4-20241113
```

**RULE 21: EXTENDED THINKING TRIGGERS**
USE --mode plan (extended thinking) ONLY IF:
- Task requires novel architectural design
- Multiple solution paths need evaluation
- Security/compliance implications complex
- Trade-offs need deep analysis

NEVER use for:
- Standard CRUD operations
- Style formatting
- Simple refactors
- Well-documented patterns

### CONTEXT MANAGEMENT RULES

**RULE 22: CONTEXT WINDOW ALLOCATION**
For 200K context window:
- Core config: 10,000-15,000 tokens
- Working context: 80,000-120,000 tokens
- Reserve buffer: 50,000-90,000 tokens

**RULE 23: SESSION REFRESH TRIGGERS**
MUST start new session IF:
- Context >80% capacity
- Task types changed significantly
- Previous task complete and new task unrelated
- Confusion signals detected

**RULE 24: CONTEXT COMPACTION**
WHEN context >60% full:
- ALWAYS remove outdated tool results
- ALWAYS summarize completed subtasks
- NEVER remove active context
- Use /compact command if available

### ANTI-PATTERNS (NEVER DO)

**RULE 25: FORBIDDEN PATTERNS**
NEVER:
- Duplicate content between CLAUDE.md and PROJECT.md
- Put implementation details in CLAUDE.md
- Put critical rules in Skills
- Create Skills for frequently-used content
- Exceed token budgets listed in rules above
- Use narrative prose instead of bullets
- Explain rationale unless explicitly needed for rule application
- Put sensitive credentials in committed files
- Load large files into startup context

**RULE 26: FORBIDDEN IN CLAUDE.md**
NEVER include:
- Implementation examples >10 lines
- Technology-specific tutorials
- Detailed API documentation
- Step-by-step procedures >5 steps
- Historical context or rationale
- Aspirational goals or philosophy

**RULE 27: FORBIDDEN IN SKILLS**
NEVER put in Skills:
- Rules affecting >50% of tasks
- Core project identity
- Security constraints
- Absolute prohibitions
- Basic coding standards

---

## TIER 2: PATTERNS & EXAMPLES

### PATTERN 1: CLAUDE.md TEMPLATE

```markdown
# [Project Name]

## Project Identity
- Purpose: [1 sentence]
- Tech stack: [list]
- Architecture: [pattern name]

## Absolute Rules
- NEVER [constraint]
- ALWAYS [requirement]
- MUST [critical rule]

## Code Standards
- Language: [specific rules]
- Naming: [conventions]
- Structure: [patterns]

## Forbidden Operations
- [Explicit prohibitions]

## See Also
- Architecture: .claude/PROJECT.md
- [Domain]: .claude/skills/[skill-name]
```

**Token target**: 3,000-5,000 tokens  
**Line limit**: 300-400 lines

### PATTERN 2: PROJECT.md TEMPLATE

```markdown
# Project Architecture

## System Overview
[High-level architecture diagram or description]

## Module Structure
- module-1/: [purpose]
- module-2/: [purpose]

## Development Workflow
1. [Step with command]
2. [Step with command]

## Testing Strategy
- Unit: [approach]
- Integration: [approach]

## Deployment Process
1. [Step]
2. [Step]

## Integration Points
- [System]: [how it connects]

## Technology Decisions
- [Choice]: [rationale in 1 sentence]
```

**Token target**: 5,000-9,000 tokens  
**Line limit**: 400-700 lines

### PATTERN 3: SKILL.md TEMPLATE

```markdown
# [Skill Name]

**Description**: [What this Skill does - 30-50 tokens]  
**Triggers**: [When to use: keywords, file patterns, task types]  
**Token Cost**: ~[estimated] tokens when loaded  
**Dependencies**: [Required tools/configs]

## When to Use This Skill
- WHEN [scenario]
- IF [condition]
- FOR [task type]

## Instructions
[Detailed procedures, can be longer since loaded on-demand]

## Examples
[Reference implementations]

## Related
- See also: [other Skill names]
```

### PATTERN 4: MIGRATION SEQUENCE

**STEP 1: Measure Current State**
```bash
# Count tokens in current files
wc -w CLAUDE.md  # Rough estimate: words * 1.3 = tokens
```

**STEP 2: Split Content**
```
IF section >500 tokens AND used <50% of time:
  → Move to new Skill
  
IF section affects multiple workflows:
  → Keep in PROJECT.md
  
IF section critical to all tasks:
  → Keep in CLAUDE.md
```

**STEP 3: Compress Remaining**
- Remove prose, keep bullets
- Remove examples, link to Skill
- Remove rationale, keep rules

**STEP 4: Validate**
- Check token counts
- Test session startup time
- Verify Skill invocation

### PATTERN 5: TOKEN COUNTING

```python
# Accurate token counting (use tiktoken)
import tiktoken

def count_tokens(text: str, model: str = "claude-3-5-sonnet-20241022") -> int:
    # Claude uses similar tokenization to GPT-4
    encoding = tiktoken.encoding_for_model("gpt-4")
    return len(encoding.encode(text))

# Quick estimation
def estimate_tokens(text: str) -> int:
    words = len(text.split())
    return int(words * 1.3)  # Rough approximation
```

### PATTERN 6: REWIND USAGE

**WHEN to create checkpoints**:
```
BEFORE major refactoring
BEFORE architectural changes
BEFORE dependency updates
AFTER successful milestone
```

**HOW to use Rewind**:
```bash
# Double-tap ESC to activate Rewind UI
# OR use command:
/rewind

# Select checkpoint from list
# Claude restores conversation + file states
```

### PATTERN 7: SUBAGENT DELEGATION

**CREATE subagent IF**:
- Specialized task domain (testing, docs, deployment)
- Different tool permissions needed
- Isolated context beneficial
- Parallel work possible

**EXAMPLE subagent config**:
```json
{
  "name": "test-agent",
  "model": "claude-haiku-4-5-20250919",
  "system_prompt": ".claude/agents/test-agent/system.md",
  "tools": ["bash", "edit_file"],
  "context": ["tests/", ".claude/skills/testing/"]
}
```

### PATTERN 8: HOOK AUTOMATION

**AVAILABLE hooks** (git-style):
- `before_edit`: Runs before file modifications
- `after_edit`: Runs after file modifications
- `before_session`: Runs at session start
- `after_session`: Runs at session end

**EXAMPLE hook**:
```json
{
  "before_edit": {
    "command": "npm run lint",
    "on_failure": "warn"
  },
  "after_edit": {
    "command": "npm test -- --changed",
    "on_failure": "block"
  }
}
```

### PATTERN 9: MCP SERVER INTEGRATION

**SETUP**:
```json
// .mcp.json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN}"
      }
    }
  }
}
```

**USAGE PATTERN**:
- MCP tools available automatically
- Claude invokes when needed
- Results count toward context budget

### PATTERN 10: CONTEXT EFFICIENCY COMPARISON

**BEFORE optimization** (monolithic):
```
CLAUDE.md: 15,000 tokens (everything)
Startup: 4.2s
Tasks before refresh: 6
```

**AFTER optimization** (3-tier):
```
CLAUDE.md: 4,000 tokens
PROJECT.md: 7,000 tokens
Total startup: 11,000 tokens
Startup: 1.8s
Tasks before refresh: 12
```

**WITH Skills** (4-tier):
```
CLAUDE.md: 3,500 tokens
PROJECT.md: 6,500 tokens
Skills metadata: 400 tokens
Total startup: 10,400 tokens
Startup: 1.5s
Tasks before refresh: 15+
Skills content: Loaded only when needed
```

---

## TIER 3: OPTIONAL CONTEXT (LOW PRIORITY FOR LLMs)

### Background: Why These Rules Exist

Skills architecture introduced October 2025 enables progressive disclosure: metadata always loaded, content loaded on-demand. This achieves "zero-cost documentation" pattern.

Context windows expanded from 100K (2024) to 200K-1M (2025), but optimal loading still matters for speed and task capacity.

Token efficiency gains measured across Obra project (8 months optimization):
- Phase 1 (monolithic): 15K tokens/session
- Phase 2 (3-tier): 5K tokens/session (67% reduction)
- Phase 3 (Skills): 3.5-4K tokens/session (75% reduction, projected)

### Historical Note: Evolution from v1.0

Version 1.0 recommended 3-tier structure (CLAUDE.md, PROJECT.md, source code). Version 2.0 adds Skills as Tier 3 for on-demand content, shifting source code to Tier 4.

---

## RULE INDEX (All Enforceable Directives)

### File Structure Rules
1. **CLAUDE.md SIZE LIMIT**: 300-400 lines, 3K-5K tokens, core rules only
2. **PROJECT.md SIZE LIMIT**: 400-700 lines, 5K-9K tokens, workflows/architecture
3. **RULES.md SIZE LIMIT**: 2K-4K tokens if exists, code style only
4. **TOTAL STARTUP CONTEXT**: <15K tokens (excluding Skills content)
5. **SKILLS METADATA BUDGET**: 30-50 tokens/Skill, 300-500 total for 10-15 Skills

### Context Loading Rules
6. **LOADING HIERARCHY**: Global → Project → CLAUDE.md → PROJECT.md → Skills metadata → On-demand
7. **PROGRESSIVE DISCLOSURE**: Metadata always loaded, content never upfront, only when relevant

### Information Hierarchy Rules
8. **4-TIER DISTRIBUTION**: CLAUDE.md (critical) → PROJECT.md (workflows) → Skills (specialized) → Source (implementation)
9. **PLACEMENT DECISION TREE**: Every task → CLAUDE.md; Multiple workflows → PROJECT.md; Specialized → Skill; Implementation → Code

### Token Optimization Rules
10. **ELIMINATE REDUNDANCY**: Never repeat, always reference other files
11. **BULLET-FIRST FORMAT**: Bullets over prose, imperative verbs, no narrative
12. **DIRECTIVE LANGUAGE**: MUST/NEVER/ALWAYS/IF-THEN, avoid "should"/"consider"
13. **EXAMPLE COMPACTNESS**: Max 10 lines, no boilerplate, comments not prose

### Skills Architecture Rules
14. **SKILL CREATION CRITERIA**: >500 tokens AND <50% usage AND self-contained
15. **SKILL STRUCTURE**: SKILL.md + optional (instructions.md, examples/, scripts/)
16. **SKILL METADATA FORMAT**: Description (30-50 tokens) + Triggers + Token cost
17. **SKILL INVOCATION SIGNALS**: Keywords, task types, file patterns, technologies

### File Location Rules
18. **CONFIG LOCATIONS**: ~/.claude/ (global), .claude/ (project), root (CLAUDE.md)
19. **GIT TRACKING**: Commit settings.json and Skills, ignore settings.local.json

### Model Selection Rules
20. **MODEL CHOICE**: Complex → Sonnet 4.5; Standard → Sonnet 4; Simple → Haiku 4.5; Critical → Opus 4
21. **EXTENDED THINKING**: Novel architecture/security/trade-offs only, never for standard tasks

### Context Management Rules
22. **WINDOW ALLOCATION**: 10-15K config, 80-120K working, 50-90K reserve (200K total)
23. **SESSION REFRESH**: When >80% capacity OR task type change OR confusion signals
24. **CONTEXT COMPACTION**: At >60% full, remove old results, summarize completed tasks

### Anti-Pattern Rules
25. **FORBIDDEN PATTERNS**: No duplication, no implementation in CLAUDE.md, no critical rules in Skills, etc.
26. **FORBIDDEN IN CLAUDE.md**: No >10 line examples, no tutorials, no detailed docs, no >5 step procedures
27. **FORBIDDEN IN SKILLS**: No rules for >50% tasks, no core identity, no security constraints

---

## WHEN TO APPLY (Situation → Rule Mapping)

### During Initial Project Setup
- Apply: RULE 1, 2, 18, 19
- Create CLAUDE.md (300-400 lines)
- Create .claude/PROJECT.md (400-700 lines)
- Set up file locations correctly
- Configure git tracking

### When Creating New Documentation
- Apply: RULE 8, 9, 14
- Use placement decision tree
- Check if Skill needed (>500 tokens, <50% usage)
- Validate tier assignment

### When Optimizing Existing Project
- Apply: RULE 4, 10, 11, 12
- Measure total startup tokens (<15K target)
- Remove redundancy across files
- Convert prose to bullets
- Change "should" to "MUST"

### When Creating a Skill
- Apply: RULE 14, 15, 16, 17
- Verify creation criteria
- Use standard structure
- Write 30-50 token description
- Include invocation triggers

### When Starting a Session
- Apply: RULE 6, 7, 22
- Understand loading sequence
- Know what's in context vs. on-demand
- Monitor context allocation

### When Choosing a Model
- Apply: RULE 20, 21
- Match task complexity to model
- Use extended thinking sparingly
- Consider cost vs. quality trade-offs

### During Long Sessions
- Apply: RULE 23, 24
- Watch for >60% context usage
- Compact when needed
- Refresh if >80% or confusion detected

### When Refactoring Documentation
- Apply: RULE 25, 26, 27
- Check against forbidden patterns
- Ensure no CLAUDE.md violations
- Validate Skill content appropriateness

### When Files Grow Too Large
- Apply: RULE 1, 2, 3, 4, 8
- Check against line/token limits
- Split into appropriate tier
- Move specialized content to Skills
- Validate total startup context

### When Experiencing Performance Issues
- Apply: RULE 4, 10, 13, 22, 23
- Measure startup tokens
- Eliminate redundancy
- Compact examples
- Check context allocation
- Consider session refresh

### When Setting Up Automation
- Apply: PATTERN 7, 8, 9
- Evaluate subagent needs
- Configure hooks appropriately
- Integrate MCP servers

### When Migrating from Old Structure
- Apply: PATTERN 4
- Measure current state
- Split content by tier
- Compress remaining content
- Validate token counts

---

## VERIFICATION CHECKLIST

**Before Committing Documentation Changes**:
- [ ] CLAUDE.md: 300-400 lines, 3K-5K tokens
- [ ] PROJECT.md: 400-700 lines, 5K-9K tokens
- [ ] Total startup: <15K tokens (excluding Skills content)
- [ ] No content duplication between files
- [ ] All prose converted to bullets
- [ ] All "should" changed to "MUST/NEVER/ALWAYS"
- [ ] Examples ≤10 lines each
- [ ] Skills have 30-50 token descriptions
- [ ] .claude/settings.local.json in .gitignore

**Before Creating New Skill**:
- [ ] Content >500 tokens
- [ ] Used in <50% of sessions
- [ ] Self-contained domain
- [ ] SKILL.md has description, triggers, token cost
- [ ] Clear invocation signals included

**Before Session Refresh**:
- [ ] Context usage >80% OR
- [ ] Task type changed significantly OR
- [ ] Confusion signals detected OR
- [ ] Previous task complete and new task unrelated

**Performance Targets**:
- [ ] Session startup: <2 seconds
- [ ] Tasks before refresh: >10 (200K window) or >30 (1M window)
- [ ] Context confusion: <5% of sessions

---

## QUICK REFERENCE: CRITICAL NUMBERS

```
CLAUDE.md:              3,000-5,000 tokens | 300-400 lines
PROJECT.md:             5,000-9,000 tokens | 400-700 lines
RULES.md:               2,000-4,000 tokens
Skill metadata (each):  30-50 tokens
Total Skills metadata:  300-500 tokens (10-15 Skills)
Skill content (each):   500-2,000 tokens (ideal)
Total startup:          <15,000 tokens
Session startup:        <2 seconds
Tasks before refresh:   >10 (200K) | >30 (1M)
```

---

## DOCUMENT METADATA

**Version**: 2.0.1-LLM  
**Source**: CLAUDE_CODE_OPTIMIZATION_BEST_PRACTICES_V2_0_1.md  
**Optimization Type**: LLM-Machine-Readable  
**Format Changes**:
- Removed: Narrative exposition, case studies, historical context, persuasion
- Added: RULE INDEX, WHEN TO APPLY mappings, verification checklists
- Transformed: All advice → enforceable directives
- Structured: 3-tier hierarchy (Critical → Patterns → Optional)
- Compressed: ~60% token reduction from source document

**Usage**: Load this document into Claude Code context or use as reference when configuring agentic coding systems.

**Next Steps**: Apply RULE INDEX to your project, validate against VERIFICATION CHECKLIST.
