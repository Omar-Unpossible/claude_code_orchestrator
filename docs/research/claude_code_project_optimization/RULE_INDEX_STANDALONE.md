# RULE INDEX: Claude Code Optimization
## Machine-Readable Directives for LLM Systems

**Version**: 2.0.1-LLM  
**Last Updated**: November 15, 2025  
**Format**: Numbered, enforceable rules with zero ambiguity

---

## FILE STRUCTURE RULES

### RULE 1: CLAUDE.md SIZE LIMIT
**Directive**: MUST keep CLAUDE.md between 300-400 lines  
**Token Limit**: MUST NOT exceed 5,000 tokens  
**Target**: 3,000-5,000 tokens  
**Content Type**: Core rules ONLY  
**Enforcement**: Validate before git commit

### RULE 2: PROJECT.md SIZE LIMIT
**Directive**: MUST keep .claude/PROJECT.md between 400-700 lines  
**Token Limit**: MUST NOT exceed 9,000 tokens  
**Target**: 5,000-9,000 tokens  
**Content Type**: Workflows, architecture, patterns  
**Enforcement**: Validate before git commit

### RULE 3: RULES.md SIZE LIMIT
**Condition**: IF .claude/RULES.md exists  
**Directive**: MUST keep 2,000-4,000 tokens  
**Content Type**: Code style, conventions, constraints ONLY  
**Enforcement**: Validate before git commit

### RULE 4: TOTAL STARTUP CONTEXT
**Directive**: MUST keep total startup context <15,000 tokens  
**Formula**: CLAUDE.md + PROJECT.md + RULES.md + Skills metadata + config  
**Excludes**: Skills content (loaded on-demand)  
**Enforcement**: Measure at session start, optimize if exceeded

### RULE 5: SKILLS METADATA BUDGET
**Per-Skill**: 30-50 tokens (description in SKILL.md header)  
**Total Limit**: 300-500 tokens (for 10-15 Skills)  
**Content**: Skill descriptions only, NOT full content  
**Loading**: Full Skill content loaded ONLY when invoked  
**Enforcement**: Validate Skill metadata token count

---

## CONTEXT LOADING RULES

### RULE 6: LOADING HIERARCHY
**Directive**: ALWAYS load in this exact order:
1. Global config (~/.claude/)
2. Project config (.claude/)
3. CLAUDE.md (repository root)
4. .claude/PROJECT.md
5. Skills metadata (descriptions only)
6. On-demand: Skill content when invoked

**Enforcement**: Understanding only (system-controlled)

### RULE 7: PROGRESSIVE DISCLOSURE PATTERN
**Metadata**: ALWAYS in context (lightweight)  
**Content**: NEVER load upfront  
**Loading**: ONLY when Claude determines relevance  
**Benefit**: Zero-cost documentation until needed  
**Application**: Design Skills with this pattern in mind

---

## INFORMATION HIERARCHY RULES

### RULE 8: 4-TIER CONTENT DISTRIBUTION

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

**Enforcement**: Validate content placement against tier definitions

### RULE 9: CONTENT PLACEMENT DECISION TREE
```
IF affects every task → CLAUDE.md
ELSE IF affects multiple modules/workflows → PROJECT.md
ELSE IF specialized/infrequent → Skill
ELSE IF implementation detail → Source code comments
```

**Enforcement**: Apply decision tree for all new documentation

---

## TOKEN OPTIMIZATION RULES

### RULE 10: ELIMINATE REDUNDANCY
**Directive**: NEVER repeat information across files  
**Directive**: NEVER explain same concept twice  
**Directive**: ALWAYS use references to other sections/files  
**Pattern**: "See [FILENAME]:[SECTION]" instead of duplicating  
**Enforcement**: Review for duplication before commit

### RULE 11: BULLET-FIRST FORMATTING
**Directive**: ALWAYS use bullets over prose paragraphs  
**Directive**: ALWAYS use imperative verbs  
**Directive**: NEVER use narrative exposition  
**Maximum**: 1-2 sentence bullets  
**Enforcement**: Convert prose to bullets in all documentation

### RULE 12: DIRECTIVE LANGUAGE
**MUST use**: MUST, NEVER, ALWAYS, IF/THEN, ONLY IF, WHEN  
**AVOID**: "should", "consider", "it's good to", "we recommend"  
**PREFER**: Direct commands over suggestions  
**Example**: "ALWAYS validate inputs" NOT "You should validate inputs"  
**Enforcement**: Replace soft language with imperatives

### RULE 13: EXAMPLE COMPACTNESS
**Directive**: IF example needed: Maximum 10 lines  
**Directive**: ALWAYS omit boilerplate  
**Directive**: ALWAYS use comments to explain, not prose  
**Pattern**: `// MUST: [rule]` in code  
**Enforcement**: Compress all examples to ≤10 lines

---

## SKILLS ARCHITECTURE RULES

### RULE 14: SKILL CREATION CRITERIA

**CREATE Skill ONLY IF**:
- Content >500 tokens AND
- Used <50% of sessions AND
- Self-contained domain

**DO NOT create Skill IF**:
- Content <500 tokens (put in PROJECT.md)
- Used >50% of sessions (put in CLAUDE.md)
- Depends heavily on other content

**Enforcement**: Evaluate against criteria before creating Skill

### RULE 15: SKILL STRUCTURE
```
.claude/skills/[skill-name]/
├─ SKILL.md          # MUST: Start with description (30-50 tokens)
├─ instructions.md   # OPTIONAL: Detailed procedures
├─ examples/         # OPTIONAL: Reference code
└─ scripts/          # OPTIONAL: Automation
```

**Enforcement**: Follow structure for all new Skills

### RULE 16: SKILL METADATA FORMAT
**Directive**: First section of SKILL.md MUST contain:
```markdown
# [Skill Name]

**Description**: [1-2 sentence description, 30-50 tokens]
**Triggers**: [When to invoke this Skill]
**Token Cost**: [Estimated tokens when loaded]
```

**Enforcement**: Validate metadata presence and token count

### RULE 17: SKILL INVOCATION SIGNALS
**Directive**: Include EXPLICIT triggers in Skill description:
- Keywords that indicate relevance
- Task types that need this Skill
- File patterns that trigger use
- Technologies that require this knowledge

**Purpose**: Help Claude determine when to load Skill  
**Enforcement**: Review triggers for clarity and completeness

---

## FILE LOCATION RULES

### RULE 18: CONFIGURATION FILE LOCATIONS
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

**Enforcement**: Place files in correct locations

### RULE 19: GIT TRACKING

**MUST commit to git**:
- .claude/settings.json
- .claude/skills/
- CLAUDE.md
- .claude/PROJECT.md

**MUST git-ignore**:
- .claude/settings.local.json
- .claude/.cache/
- .claude/logs/

**Enforcement**: Configure .gitignore correctly, validate before first commit

---

## MODEL SELECTION RULES

### RULE 20: MODEL CHOICE DECISION TREE
```
IF task = complex reasoning OR novel architecture
  → claude-sonnet-4-5-20250929

ELSE IF task = standard CRUD OR well-defined
  → claude-sonnet-4-20250514

ELSE IF task = simple refactor OR formatting
  → claude-haiku-4-5-20250919

ELSE IF task = maximum quality critical
  → claude-opus-4-20241113
```

**Enforcement**: Select model based on task complexity

### RULE 21: EXTENDED THINKING TRIGGERS

**USE --mode plan (extended thinking) ONLY IF**:
- Task requires novel architectural design
- Multiple solution paths need evaluation
- Security/compliance implications complex
- Trade-offs need deep analysis

**NEVER use for**:
- Standard CRUD operations
- Style formatting
- Simple refactors
- Well-documented patterns

**Enforcement**: Evaluate task complexity before enabling extended thinking

---

## CONTEXT MANAGEMENT RULES

### RULE 22: CONTEXT WINDOW ALLOCATION

**For 200K context window**:
- Core config: 10,000-15,000 tokens
- Working context: 80,000-120,000 tokens
- Reserve buffer: 50,000-90,000 tokens

**Formula**: Config + Working + Reserve ≤ 200,000 tokens  
**Enforcement**: Monitor context usage, optimize when approaching limits

### RULE 23: SESSION REFRESH TRIGGERS

**MUST start new session IF**:
- Context >80% capacity
- Task types changed significantly
- Previous task complete AND new task unrelated
- Confusion signals detected

**Enforcement**: Monitor context percentage, refresh proactively

### RULE 24: CONTEXT COMPACTION

**WHEN context >60% full**:
- ALWAYS remove outdated tool results
- ALWAYS summarize completed subtasks
- NEVER remove active context
- Use /compact command if available

**Enforcement**: Compact regularly to maintain efficiency

---

## ANTI-PATTERN RULES

### RULE 25: FORBIDDEN PATTERNS

**NEVER**:
- Duplicate content between CLAUDE.md and PROJECT.md
- Put implementation details in CLAUDE.md
- Put critical rules in Skills
- Create Skills for frequently-used content
- Exceed token budgets listed in rules above
- Use narrative prose instead of bullets
- Explain rationale unless explicitly needed for rule application
- Put sensitive credentials in committed files
- Load large files into startup context

**Enforcement**: Review against forbidden patterns checklist

### RULE 26: FORBIDDEN IN CLAUDE.md

**NEVER include**:
- Implementation examples >10 lines
- Technology-specific tutorials
- Detailed API documentation
- Step-by-step procedures >5 steps
- Historical context or rationale
- Aspirational goals or philosophy

**Enforcement**: Validate CLAUDE.md against forbidden content list

### RULE 27: FORBIDDEN IN SKILLS

**NEVER put in Skills**:
- Rules affecting >50% of tasks
- Core project identity
- Security constraints
- Absolute prohibitions
- Basic coding standards

**Enforcement**: Validate Skill content against forbidden items

---

## QUICK RULE LOOKUP BY NUMBER

1. CLAUDE.md: 300-400 lines, 3K-5K tokens
2. PROJECT.md: 400-700 lines, 5K-9K tokens
3. RULES.md: 2K-4K tokens (if exists)
4. Total startup: <15K tokens
5. Skills metadata: 30-50 tokens each, 300-500 total
6. Loading order: Global → Project → CLAUDE.md → PROJECT.md → Skills metadata
7. Progressive disclosure: Metadata always, content on-demand
8. 4-tier distribution: CLAUDE.md → PROJECT.md → Skills → Code
9. Placement: Every task → CLAUDE.md; Multiple → PROJECT.md; Specialized → Skill
10. No redundancy across files
11. Bullets over prose
12. MUST/NEVER/ALWAYS language
13. Examples ≤10 lines
14. Skill creation: >500 tokens, <50% usage, self-contained
15. Skill structure: SKILL.md + optional extras
16. Skill metadata: Description + Triggers + Token cost
17. Skill triggers: Keywords, tasks, files, technologies
18. File locations: ~/.claude/ vs .claude/
19. Git: Commit settings.json and Skills, ignore settings.local.json
20. Model: Complex → Sonnet 4.5; Standard → Sonnet 4; Simple → Haiku 4.5
21. Extended thinking: Novel/complex only
22. Context: 10-15K config, 80-120K working, 50-90K reserve
23. Refresh: >80% capacity OR task change
24. Compact: >60% full
25. No forbidden patterns
26. No forbidden content in CLAUDE.md
27. No forbidden content in Skills

---

## ENFORCEMENT METHODS

### Pre-Commit Validation
- Run token counting script
- Check against size limits (RULE 1-5)
- Scan for redundancy (RULE 10)
- Validate directive language (RULE 12)

### Session Start Validation
- Measure total startup tokens (RULE 4)
- Verify loading hierarchy (RULE 6)
- Check context allocation (RULE 22)

### Continuous Monitoring
- Track context usage percentage (RULE 23, 24)
- Monitor Skill invocation patterns (RULE 14, 17)
- Watch for confusion signals (RULE 23)

### Code Review Checklist
- Content placement correct? (RULE 8, 9)
- Examples compressed? (RULE 13)
- Anti-patterns avoided? (RULE 25-27)
- Git tracking configured? (RULE 19)

---

## DOCUMENT METADATA

**Version**: 2.0.1-LLM  
**Format**: Numbered Rule Index  
**Total Rules**: 27 core rules + enforcement guidelines  
**Usage**: Load into LLM context for rule-based decision making  
**References**: See CLAUDE_CODE_OPTIMIZATION_LLM_OPTIMIZED.md for patterns and examples
